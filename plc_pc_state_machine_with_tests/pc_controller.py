"""
PC controller for the PC <-> PLC state-machine prototype.

Run the PLC simulator first:
    python plc_sim.py --host 127.0.0.1 --port 15000

Then run one of:
    python pc_controller.py --mode manual
    python pc_controller.py --mode semi-auto

The camera is simulated by writing JSON capture records. Replace SimulatedCamera
with the real IDS capture worker later.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from shared_protocol import (
    AckStatus,
    ErrorCode,
    EventCode,
    ModeCode,
    PcEventMailbox,
    PcState,
    PlcAckError,
    PlcEvent,
    Slmp3eClient,
    SlmpConfig,
    decode_xy_mm,
    encode_xy_mm,
    error_name,
    event_name,
)


@dataclass
class CaptureRecord:
    timestamp: float
    mode: str
    image_index: int
    step_index: Optional[int]
    x_mm: Optional[float]
    y_mm: Optional[float]
    plc_event_sequence: Optional[int]
    note: str


class SimulatedCamera:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.running = False
        self.image_index = 0
        self.last_frame_time = 0.0

    def start(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.running = True
        self.last_frame_time = time.time()
        print("[CAM] simulated camera started")

    def stop(self) -> None:
        self.running = False
        print("[CAM] simulated camera stopped")

    def update_live_frame(self) -> None:
        if self.running:
            self.last_frame_time = time.time()

    def ready(self) -> bool:
        self.update_live_frame()
        return self.running

    def latest_frame_fresh(self, max_age_sec: float = 1.0) -> bool:
        self.update_live_frame()
        return self.running and (time.time() - self.last_frame_time) <= max_age_sec

    def save_latest(
        self,
        *,
        mode: str,
        step_index: Optional[int],
        x_mm: Optional[float],
        y_mm: Optional[float],
        plc_event_sequence: Optional[int],
        note: str,
    ) -> Path:
        if not self.ready():
            raise RuntimeError("camera not ready")
        self.image_index += 1
        record = CaptureRecord(
            timestamp=time.time(),
            mode=mode,
            image_index=self.image_index,
            step_index=step_index,
            x_mm=x_mm,
            y_mm=y_mm,
            plc_event_sequence=plc_event_sequence,
            note=note,
        )
        path = self.output_dir / f"capture_{self.image_index:04d}.json"
        path.write_text(json.dumps(asdict(record), indent=2), encoding="utf-8")
        print(f"[CAM] saved {path}")
        return path


class PcController:
    def __init__(self, host: str, port: int, mode: str, capture_dir: Path):
        self.host = host
        self.port = port
        self.requested_mode = mode
        self.state = PcState.STARTUP
        self.client = Slmp3eClient(SlmpConfig(host=host, port=port))
        self.mailbox = PcEventMailbox(self.client)
        self.camera = SimulatedCamera(capture_dir)
        self.active_error_code = ErrorCode.ERR_NONE
        self.selected_mode = ModeCode.NONE
        self.current_step: Optional[int] = None
        self.expected_step: Optional[int] = None
        self.current_position: Optional[tuple[float, float]] = None
        self.requested_step: Optional[int] = None
        self.manual_command: Optional[tuple[EventCode, list[int], tuple[float, float] | None]] = None
        self.manual_points = [(20.0, 15.0), (40.0, 15.0), (40.0, 35.0)]
        self.manual_index = 0

    def transition(self, new_state: PcState) -> None:
        if new_state != self.state:
            print(f"[PC] {self.state.value} -> {new_state.value}")
            self.state = new_state

    def run(self) -> None:
        try:
            while self.state != PcState.SHUTDOWN:
                self.run_state()
                time.sleep(0.02)
        finally:
            self.shutdown_resources()

    def run_state(self) -> None:
        if self.state == PcState.STARTUP:
            self.transition(PcState.INIT_CAMERA)

        elif self.state == PcState.INIT_CAMERA:
            self.camera.start()
            self.transition(PcState.CONNECT_PLC)

        elif self.state == PcState.CONNECT_PLC:
            try:
                self.client.connect()
                print(f"[PC] connected to PLC at {self.host}:{self.port}")
                self.mailbox.publish_pc_event(EventCode.PC_READY)
                self.transition(PcState.WAIT_PLC_READY)
            except Exception as exc:
                print(f"[PC] connection error: {exc}")
                self.active_error_code = ErrorCode.ERR_COMM_CONNECT_FAILED
                self.transition(PcState.ERROR)

        elif self.state == PcState.WAIT_PLC_READY:
            event = self.wait_event(EventCode.PLC_READY, timeout_sec=5.0)
            if event is None:
                return
            self.ack(event)
            self.transition(PcState.IDLE)

        elif self.state == PcState.IDLE:
            if self.requested_mode == "manual":
                self.transition(PcState.MANUAL_SELECT)
            elif self.requested_mode == "semi-auto":
                self.transition(PcState.SEMI_SELECT)
            else:
                self.transition(PcState.SHUTDOWN)

        elif self.state == PcState.MANUAL_SELECT:
            self.send_or_error(EventCode.SET_MODE_MANUAL)
            event = self.wait_event(EventCode.MODE_CHANGED, timeout_sec=5.0)
            if event is None:
                return
            if event.payload[0] == int(ModeCode.MANUAL):
                self.selected_mode = ModeCode.MANUAL
                self.ack(event)
                self.transition(PcState.MANUAL_IDLE)
            else:
                self.active_error_code = ErrorCode.ERR_PC_INVALID_MODE
                self.transition(PcState.ERROR)

        elif self.state == PcState.MANUAL_IDLE:
            if self.manual_index >= len(self.manual_points):
                print("[PC] manual demo complete")
                self.transition(PcState.SHUTDOWN)
                return
            x_mm, y_mm = self.manual_points[self.manual_index]
            payload = encode_xy_mm(x_mm, y_mm)
            self.manual_command = (EventCode.MANUAL_MOVE_REQUEST, payload, (x_mm, y_mm))
            self.transition(PcState.MANUAL_SEND_COMMAND)

        elif self.state == PcState.MANUAL_SEND_COMMAND:
            assert self.manual_command is not None
            event_type, payload, _ = self.manual_command
            self.send_or_error(event_type, payload)
            if self.state != PcState.ERROR:
                self.transition(PcState.MANUAL_WAIT_STARTED)

        elif self.state == PcState.MANUAL_WAIT_STARTED:
            event = self.wait_event(timeout_sec=5.0)
            if event is None:
                return
            if event.event_type == int(EventCode.MANUAL_COMMAND_STARTED):
                self.ack(event)
                self.transition(PcState.MANUAL_WAIT_RESULT)
            elif event.event_type == int(EventCode.MANUAL_COMMAND_ERROR):
                self.ack(event, AckStatus.REJECTED)
                self.active_error_code = self.payload_error(event)
                self.transition(PcState.ERROR)
            else:
                self.handle_unexpected_event(event)

        elif self.state == PcState.MANUAL_WAIT_RESULT:
            event = self.wait_event(timeout_sec=10.0)
            if event is None:
                return
            if event.event_type == int(EventCode.MANUAL_COMMAND_DONE):
                self.ack(event)
                self.transition(PcState.MANUAL_CAPTURE)
            elif event.event_type == int(EventCode.MANUAL_COMMAND_ERROR):
                self.ack(event, AckStatus.REJECTED)
                self.active_error_code = self.payload_error(event)
                self.transition(PcState.ERROR)
            else:
                self.handle_unexpected_event(event)

        elif self.state == PcState.MANUAL_CAPTURE:
            if not self.camera.ready():
                self.active_error_code = ErrorCode.ERR_CAMERA_ACQUISITION_NOT_RUNNING
                self.transition(PcState.ERROR)
                return
            _, _, target = self.manual_command or (None, None, None)
            x_mm, y_mm = target if target else (None, None)
            self.camera.save_latest(
                mode="manual",
                step_index=self.manual_index,
                x_mm=x_mm,
                y_mm=y_mm,
                plc_event_sequence=None,
                note="manual command complete",
            )
            self.transition(PcState.MANUAL_REPORT_CAPTURE_DONE)

        elif self.state == PcState.MANUAL_REPORT_CAPTURE_DONE:
            self.send_or_error(EventCode.MANUAL_CAPTURE_DONE, [self.manual_index, self.camera.image_index])
            if self.state != PcState.ERROR:
                self.manual_index += 1
                self.transition(PcState.MANUAL_IDLE)

        elif self.state == PcState.SEMI_SELECT:
            self.send_or_error(EventCode.SET_MODE_SEMI_AUTO)
            event = self.wait_event(EventCode.MODE_CHANGED, timeout_sec=5.0)
            if event is None:
                return
            if event.payload[0] == int(ModeCode.SEMI_AUTO):
                self.selected_mode = ModeCode.SEMI_AUTO
                self.ack(event)
                self.transition(PcState.SEMI_START_RUN)
            else:
                self.active_error_code = ErrorCode.ERR_PC_INVALID_MODE
                self.transition(PcState.ERROR)

        elif self.state == PcState.SEMI_START_RUN:
            if not self.camera.ready():
                self.active_error_code = ErrorCode.ERR_CAMERA_ACQUISITION_NOT_RUNNING
                self.transition(PcState.ERROR)
                return
            self.send_or_error(EventCode.START_RUN)
            if self.state != PcState.ERROR:
                self.transition(PcState.SEMI_MONITOR_RUN)

        elif self.state == PcState.SEMI_MONITOR_RUN:
            event = self.wait_event(timeout_sec=15.0)
            if event is None:
                return
            self.handle_semi_event(event)

        elif self.state == PcState.SEMI_CHECK_CAPTURE_READY:
            if self.requested_step != self.expected_step:
                self.reject_capture(ErrorCode.ERR_PC_SEQUENCE_MISMATCH)
            elif not self.camera.ready():
                self.reject_capture(ErrorCode.ERR_CAMERA_ACQUISITION_NOT_RUNNING)
            elif not self.camera.latest_frame_fresh():
                self.reject_capture(ErrorCode.ERR_CAMERA_STALE_FRAME)
            else:
                self.transition(PcState.SEMI_AUTHORIZE_CAPTURE)

        elif self.state == PcState.SEMI_AUTHORIZE_CAPTURE:
            self.send_or_error(EventCode.CAPTURE_AUTHORIZED, [self.requested_step or 0])
            if self.state != PcState.ERROR:
                self.transition(PcState.SEMI_WAIT_CAPTURE_WINDOW)

        elif self.state == PcState.SEMI_WAIT_CAPTURE_WINDOW:
            event = self.wait_event(EventCode.CAPTURE_WINDOW_OPEN, timeout_sec=5.0)
            if event is None:
                return
            if event.event_type == int(EventCode.CAPTURE_WINDOW_OPEN):
                self.ack(event)
                self.transition(PcState.SEMI_CAPTURE_IMAGE)
            else:
                self.handle_unexpected_event(event)

        elif self.state == PcState.SEMI_CAPTURE_IMAGE:
            x_mm, y_mm = self.current_position if self.current_position else (None, None)
            self.camera.save_latest(
                mode="semi-auto",
                step_index=self.requested_step,
                x_mm=x_mm,
                y_mm=y_mm,
                plc_event_sequence=None,
                note="semi-auto capture window open",
            )
            self.transition(PcState.SEMI_REPORT_CAPTURE_DONE)

        elif self.state == PcState.SEMI_REPORT_CAPTURE_DONE:
            self.send_or_error(EventCode.CAPTURE_DONE, [self.requested_step or 0, self.camera.image_index])
            if self.state != PcState.ERROR:
                self.transition(PcState.SEMI_MONITOR_RUN)

        elif self.state == PcState.ERROR:
            print(f"[PC] ERROR {int(self.active_error_code)} {error_name(int(self.active_error_code))}")
            try:
                self.mailbox.publish_pc_event(EventCode.STOP_RUN, [int(self.active_error_code)], timeout_sec=1.0)
            except Exception:
                pass
            self.transition(PcState.SHUTDOWN)

    def handle_semi_event(self, event: PlcEvent) -> None:
        print(f"[PC] PLC event {event.name} seq={event.sequence} payload={event.payload}")
        et = event.event_type
        if et == int(EventCode.RUN_STARTED):
            self.ack(event)
        elif et == int(EventCode.SEMI_AUTO_STEP_STARTED):
            self.current_step = event.payload[0]
            self.expected_step = self.current_step
            self.ack(event)
        elif et == int(EventCode.POSITION_REACHED):
            self.current_step = event.payload[0]
            self.current_position = decode_xy_mm(event.payload[1:5])
            self.ack(event)
        elif et == int(EventCode.CAPTURE_AUTH_REQUEST):
            self.requested_step = event.payload[0]
            self.ack(event)
            self.transition(PcState.SEMI_CHECK_CAPTURE_READY)
        elif et == int(EventCode.CAPTURE_WINDOW_OPEN):
            self.ack(event)
            self.transition(PcState.SEMI_CAPTURE_IMAGE)
        elif et == int(EventCode.CAPTURE_WINDOW_CLOSED):
            self.ack(event)
        elif et == int(EventCode.STEP_COMPLETE):
            self.ack(event)
        elif et == int(EventCode.RUN_COMPLETE):
            self.ack(event)
            print("[PC] semi-auto run complete")
            self.transition(PcState.SHUTDOWN)
        elif et >= 900:
            self.ack(event, AckStatus.REJECTED)
            self.active_error_code = self.payload_error(event)
            self.transition(PcState.ERROR)
        else:
            self.handle_unexpected_event(event)

    def send_or_error(self, event_type: EventCode, payload: Optional[list[int]] = None) -> None:
        try:
            print(f"[PC] send {event_type.name} payload={payload or []}")
            self.mailbox.publish_pc_event(event_type, payload or [], timeout_sec=3.0)
        except PlcAckError as exc:
            print(f"[PC] ACK error: {exc}")
            self.active_error_code = ErrorCode.ERR_PLC_INVALID_STATE
            self.transition(PcState.ERROR)
        except Exception as exc:
            print(f"[PC] communication error while sending {event_type.name}: {exc}")
            self.active_error_code = ErrorCode.ERR_COMM_ACK_TIMEOUT
            self.transition(PcState.ERROR)

    def wait_event(self, expected: Optional[EventCode] = None, timeout_sec: float = 10.0) -> Optional[PlcEvent]:
        try:
            return self.mailbox.wait_for_plc_event(expected=expected, timeout_sec=timeout_sec)
        except TimeoutError as exc:
            print(f"[PC] timeout: {exc}")
            self.active_error_code = ErrorCode.ERR_COMM_PLC_EVENT_TIMEOUT
            self.transition(PcState.ERROR)
            return None
        except Exception as exc:
            print(f"[PC] communication error while waiting for event: {exc}")
            self.active_error_code = ErrorCode.ERR_COMM_READ_FAILED
            self.transition(PcState.ERROR)
            return None

    def ack(self, event: PlcEvent, status: AckStatus = AckStatus.OK) -> None:
        print(f"[PC] ACK PLC event {event.name} seq={event.sequence} status={status.name}")
        self.mailbox.acknowledge_plc_event(event, status)

    def payload_error(self, event: PlcEvent) -> ErrorCode:
        code = event.payload[0] if event.payload else int(ErrorCode.ERR_UNKNOWN)
        return ErrorCode(code) if code in ErrorCode._value2member_map_ else ErrorCode.ERR_UNKNOWN

    def handle_unexpected_event(self, event: PlcEvent) -> None:
        print(f"[PC] unexpected PLC event {event.name}")
        self.ack(event, AckStatus.REJECTED)
        if event.event_type >= 900:
            self.active_error_code = self.payload_error(event)
        else:
            self.active_error_code = ErrorCode.ERR_PLC_INVALID_STATE
        self.transition(PcState.ERROR)

    def reject_capture(self, code: ErrorCode) -> None:
        self.mailbox.publish_pc_event(EventCode.CAPTURE_REJECTED, [int(code), self.requested_step or 0])
        self.active_error_code = code
        self.transition(PcState.ERROR)

    def shutdown_resources(self) -> None:
        try:
            self.camera.stop()
        finally:
            self.client.close()
        print("[PC] shutdown complete")


def main() -> None:
    parser = argparse.ArgumentParser(description="PC controller for the PLC state-machine prototype")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=15000)
    parser.add_argument("--mode", choices=["manual", "semi-auto"], required=True)
    parser.add_argument("--capture-dir", default="captures_simulated")
    args = parser.parse_args()

    controller = PcController(args.host, args.port, args.mode, Path(args.capture_dir))
    controller.run()


if __name__ == "__main__":
    main()
