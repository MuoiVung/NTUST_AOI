"""
PLC simulator for the PC <-> PLC state-machine prototype.

Run:
    python plc_sim.py --host 127.0.0.1 --port 15000

Then run the PC controller in a second terminal:
    python pc_controller.py --mode manual
    python pc_controller.py --mode semi-auto

The simulator exposes a minimal SLMP 3E binary D-register interface and runs
an event-driven PLC state machine.
"""

from __future__ import annotations

import argparse
import socketserver
import struct
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional

from shared_protocol import (
    AckStatus,
    ErrorCode,
    EventCode,
    EVENT_WORDS,
    ModeCode,
    PAYLOAD_WORDS,
    PC_ACK_BASE,
    PC_EVENT_BASE,
    PLC_ACK_BASE,
    PLC_EVENT_BASE,
    PlcState,
    decode_xy_mm,
    encode_xy_mm,
    event_name,
    error_name,
)

DEVICE_D = 0xA8


class RegisterMemory:
    def __init__(self, d_size: int = 10000):
        self._lock = threading.RLock()
        self.d = [0] * d_size

    def read_d(self, start: int, count: int) -> list[int]:
        with self._lock:
            return list(self.d[start:start + count])

    def write_d(self, start: int, values: list[int]) -> None:
        with self._lock:
            for i, value in enumerate(values):
                self.d[start + i] = int(value) & 0xFFFF


class SlmpRequestHandler(socketserver.BaseRequestHandler):
    memory: RegisterMemory

    def _recv_exact(self, count: int) -> bytes:
        chunks: list[bytes] = []
        remaining = count
        while remaining > 0:
            chunk = self.request.recv(remaining)
            if not chunk:
                raise ConnectionError("client disconnected")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def _send_response(self, data: bytes = b"", end_code: int = 0) -> None:
        response_data = struct.pack("<H", end_code) + data
        header = (
            b"\xD0\x00"
            + b"\x00"
            + b"\xFF"
            + b"\xFF\x03"
            + b"\x00"
            + struct.pack("<H", len(response_data))
        )
        self.request.sendall(header + response_data)

    def handle(self) -> None:
        print(f"[SLMP] client connected: {self.client_address}")
        while True:
            try:
                header = self._recv_exact(9)
            except ConnectionError:
                print(f"[SLMP] client disconnected: {self.client_address}")
                return

            if header[:2] != b"\x50\x00":
                self._send_response(end_code=0xC059)
                return

            length = struct.unpack("<H", header[7:9])[0]
            request_data = self._recv_exact(length)
            if len(request_data) < 6:
                self._send_response(end_code=0xC05B)
                continue

            command = struct.unpack("<H", request_data[2:4])[0]
            subcommand = struct.unpack("<H", request_data[4:6])[0]
            payload = request_data[6:]

            if subcommand != 0:
                self._send_response(end_code=0xC05C)
                continue

            try:
                if command == 0x0401:
                    self._handle_read(payload)
                elif command == 0x1401:
                    self._handle_write(payload)
                else:
                    self._send_response(end_code=0xC059)
            except Exception as exc:
                print(f"[SLMP] request error: {exc}")
                self._send_response(end_code=0xC05B)

    @staticmethod
    def _decode_device(payload: bytes) -> tuple[int, int]:
        if len(payload) < 6:
            raise ValueError("device payload too short")
        head = int.from_bytes(payload[0:3], "little", signed=False)
        device_code = payload[3]
        count = struct.unpack("<H", payload[4:6])[0]
        if device_code != DEVICE_D:
            raise ValueError("only D registers are supported")
        return head, count

    def _handle_read(self, payload: bytes) -> None:
        head, count = self._decode_device(payload)
        values = self.memory.read_d(head, count)
        data = struct.pack("<" + "H" * count, *values)
        self._send_response(data=data)

    def _handle_write(self, payload: bytes) -> None:
        head, count = self._decode_device(payload)
        expected_len = 6 + count * 2
        if len(payload) < expected_len:
            raise ValueError("write payload too short")
        values = list(struct.unpack("<" + "H" * count, payload[6:expected_len]))
        self.memory.write_d(head, values)
        self._send_response()


class ThreadedSlmpServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


@dataclass
class QueuedPlcEvent:
    event_type: EventCode
    payload: list[int]


class PlcStateMachine(threading.Thread):
    def __init__(self, memory: RegisterMemory, scan_points: list[tuple[float, float]]):
        super().__init__(name="PlcStateMachine", daemon=True)
        self.memory = memory
        self.scan_points = scan_points
        self.stop_event = threading.Event()

        self.state = PlcState.BOOT
        self.mode = ModeCode.NONE
        self.last_pc_sequence_handled = 0
        self.plc_sequence = 0
        self.waiting_for_pc_ack = False
        self.active_plc_event_sequence = 0
        self.plc_event_queue: deque[QueuedPlcEvent] = deque()

        self.current_step = 0
        self.target_position = (0.0, 0.0)
        self.actual_position = (0.0, 0.0)
        self.active_error_code = ErrorCode.ERR_NONE
        self.motion_done_at: Optional[float] = None
        self.capture_auth_deadline: Optional[float] = None
        self.capture_done_deadline: Optional[float] = None
        self.stored_manual_event: Optional[tuple[EventCode, list[int]]] = None

        # Recipe download support. The PLC simulator starts with a default recipe
        # for backwards-compatible tests, but the PC can replace it before START_RUN.
        self.recipe_loaded = bool(scan_points)
        self.expected_recipe_steps = len(scan_points)
        self.pending_recipe_points: list[Optional[tuple[float, float]]] = []
        self.recipe_rows = 0
        self.recipe_cols = 0

    def run(self) -> None:
        print("[PLC] state machine started")
        while not self.stop_event.is_set():
            self.check_pc_ack_for_plc_event()
            self.try_publish_next_plc_event()
            self.check_new_pc_event()
            self.run_state()
            time.sleep(0.02)
        print("[PLC] state machine stopped")

    def stop(self) -> None:
        self.stop_event.set()

    def transition(self, new_state: PlcState) -> None:
        if new_state != self.state:
            print(f"[PLC] {self.state.value} -> {new_state.value}")
            self.state = new_state

    def read_pc_event_mailbox(self) -> tuple[int, int, list[int]]:
        words = self.memory.read_d(PC_EVENT_BASE, EVENT_WORDS)
        return words[0], words[1], words[2:]

    def acknowledge_pc_event(self, sequence: int, status: AckStatus) -> None:
        self.memory.write_d(PLC_ACK_BASE, [sequence, int(status)])
        print(f"[PLC] ACK PC seq={sequence} status={status.name}")

    def queue_plc_event(self, event_type: EventCode, payload: Optional[list[int]] = None) -> None:
        data = (payload or [])[:PAYLOAD_WORDS]
        data = data + [0] * (PAYLOAD_WORDS - len(data))
        self.plc_event_queue.append(QueuedPlcEvent(event_type, data))
        print(f"[PLC] queue {event_type.name} payload={data}")

    def try_publish_next_plc_event(self) -> None:
        if self.waiting_for_pc_ack or not self.plc_event_queue:
            return
        event = self.plc_event_queue.popleft()
        self.plc_sequence += 1
        if self.plc_sequence > 32767:
            self.plc_sequence = 1
        self.memory.write_d(PLC_EVENT_BASE, [int(event.event_type), self.plc_sequence] + event.payload)
        self.active_plc_event_sequence = self.plc_sequence
        self.waiting_for_pc_ack = True
        print(f"[PLC] publish {event.event_type.name} seq={self.plc_sequence}")

    def check_pc_ack_for_plc_event(self) -> None:
        if not self.waiting_for_pc_ack:
            return
        ack_seq, ack_status = self.memory.read_d(PC_ACK_BASE, 2)
        if ack_seq == self.active_plc_event_sequence:
            print(f"[PLC] PC ACK seq={ack_seq} status={ack_status}")
            self.waiting_for_pc_ack = False

    def check_new_pc_event(self) -> None:
        event_type_raw, sequence, payload = self.read_pc_event_mailbox()
        if event_type_raw == int(EventCode.NONE) or sequence == 0:
            return
        if sequence == self.last_pc_sequence_handled:
            return
        self.last_pc_sequence_handled = sequence
        try:
            event_type = EventCode(event_type_raw)
        except ValueError:
            self.acknowledge_pc_event(sequence, AckStatus.UNKNOWN_EVENT)
            return
        print(f"[PLC] PC event {event_type.name} seq={sequence} payload={payload}")
        self.handle_pc_event(event_type, sequence, payload)

    def handle_pc_event(self, event_type: EventCode, sequence: int, payload: list[int]) -> None:
        if event_type == EventCode.PC_READY:
            self.acknowledge_pc_event(sequence, AckStatus.OK)
            # Reset transmission state because PC reconnected
            self.waiting_for_pc_ack = False
            self.plc_event_queue.clear()
            if self.state in {PlcState.BOOT, PlcState.WAIT_PC_READY, PlcState.IDLE}:
                self.queue_plc_event(EventCode.PLC_READY)
                self.transition(PlcState.IDLE)
            return

        if event_type == EventCode.SET_MODE_MANUAL:
            if self.state in {PlcState.IDLE, PlcState.MANUAL_IDLE}:
                self.mode = ModeCode.MANUAL
                self.transition(PlcState.MANUAL_IDLE)
                self.acknowledge_pc_event(sequence, AckStatus.OK)
                self.queue_plc_event(EventCode.MODE_CHANGED, [int(ModeCode.MANUAL)])
            else:
                self.acknowledge_pc_event(sequence, AckStatus.BUSY)
            return

        if event_type == EventCode.SET_MODE_SEMI_AUTO:
            if self.state in {PlcState.IDLE, PlcState.SEMI_IDLE}:
                self.mode = ModeCode.SEMI_AUTO
                self.transition(PlcState.SEMI_IDLE)
                self.acknowledge_pc_event(sequence, AckStatus.OK)
                self.queue_plc_event(EventCode.MODE_CHANGED, [int(ModeCode.SEMI_AUTO)])
            else:
                self.acknowledge_pc_event(sequence, AckStatus.BUSY)
            return

        if event_type == EventCode.RECIPE_DOWNLOAD_START:
            if self.mode == ModeCode.SEMI_AUTO and self.state == PlcState.SEMI_IDLE:
                step_count = int(payload[0]) if len(payload) > 0 else 0
                rows = int(payload[1]) if len(payload) > 1 else 0
                cols = int(payload[2]) if len(payload) > 2 else 0
                if step_count <= 0 or step_count > 500 or rows <= 0 or cols <= 0:
                    self.acknowledge_pc_event(sequence, AckStatus.INVALID_PAYLOAD)
                    return
                self.expected_recipe_steps = step_count
                self.recipe_rows = rows
                self.recipe_cols = cols
                self.pending_recipe_points = [None] * step_count
                self.recipe_loaded = False
                self.acknowledge_pc_event(sequence, AckStatus.OK)
                print(f"[PLC] recipe download start: {step_count} steps, {rows}x{cols}")
            else:
                self.acknowledge_pc_event(sequence, AckStatus.INVALID_STATE)
            return

        if event_type == EventCode.RECIPE_STEP_DATA:
            if self.mode == ModeCode.SEMI_AUTO and self.state == PlcState.SEMI_IDLE and self.pending_recipe_points:
                step_index = int(payload[0]) if len(payload) > 0 else -1
                try:
                    x_mm, y_mm = decode_xy_mm(payload[3:7])
                except Exception:
                    self.acknowledge_pc_event(sequence, AckStatus.INVALID_PAYLOAD)
                    return
                if step_index < 0 or step_index >= len(self.pending_recipe_points):
                    self.acknowledge_pc_event(sequence, AckStatus.INVALID_PAYLOAD)
                    return
                if not self.target_in_range(x_mm, y_mm):
                    self.acknowledge_pc_event(sequence, AckStatus.SAFETY_NOT_OK)
                    return
                self.pending_recipe_points[step_index] = (x_mm, y_mm)
                self.acknowledge_pc_event(sequence, AckStatus.OK)
                print(f"[PLC] recipe step {step_index}: x={x_mm:.3f} y={y_mm:.3f}")
            else:
                self.acknowledge_pc_event(sequence, AckStatus.INVALID_STATE)
            return

        if event_type == EventCode.RECIPE_DOWNLOAD_END:
            if self.mode == ModeCode.SEMI_AUTO and self.state == PlcState.SEMI_IDLE and self.pending_recipe_points:
                if any(point is None for point in self.pending_recipe_points):
                    self.acknowledge_pc_event(sequence, AckStatus.INVALID_PAYLOAD)
                    return
                self.scan_points = [point for point in self.pending_recipe_points if point is not None]
                self.pending_recipe_points = []
                self.recipe_loaded = True
                self.acknowledge_pc_event(sequence, AckStatus.OK)
                self.queue_plc_event(EventCode.RECIPE_LOADED, [len(self.scan_points), self.recipe_rows, self.recipe_cols])
                print(f"[PLC] recipe loaded: {len(self.scan_points)} points")
            else:
                self.acknowledge_pc_event(sequence, AckStatus.INVALID_STATE)
            return

        if event_type in {EventCode.MANUAL_MOVE_REQUEST, EventCode.MANUAL_HOME_REQUEST, EventCode.MANUAL_JOG_REQUEST}:
            if self.mode == ModeCode.MANUAL and self.state == PlcState.MANUAL_IDLE:
                self.stored_manual_event = (event_type, payload)
                self.acknowledge_pc_event(sequence, AckStatus.OK)
                self.transition(PlcState.MANUAL_VALIDATE_COMMAND)
            else:
                self.acknowledge_pc_event(sequence, AckStatus.INVALID_STATE)
            return

        if event_type == EventCode.MANUAL_CAPTURE_DONE:
            if self.mode == ModeCode.MANUAL:
                self.acknowledge_pc_event(sequence, AckStatus.OK)
            else:
                self.acknowledge_pc_event(sequence, AckStatus.INVALID_STATE)
            return

        if event_type == EventCode.START_RUN:
            if self.mode == ModeCode.SEMI_AUTO and self.state == PlcState.SEMI_IDLE:
                if not self.recipe_loaded or not self.scan_points:
                    self.active_error_code = ErrorCode.ERR_PLC_RECIPE_NOT_LOADED
                    self.acknowledge_pc_event(sequence, AckStatus.INVALID_STATE)
                    return
                self.current_step = 0
                self.acknowledge_pc_event(sequence, AckStatus.OK)
                self.queue_plc_event(EventCode.RUN_STARTED)
                self.transition(PlcState.SEMI_LOAD_NEXT_STEP)
            else:
                self.acknowledge_pc_event(sequence, AckStatus.INVALID_STATE)
            return

        if event_type == EventCode.CAPTURE_AUTHORIZED:
            if self.mode == ModeCode.SEMI_AUTO and self.state == PlcState.SEMI_WAIT_CAPTURE_AUTH:
                self.acknowledge_pc_event(sequence, AckStatus.OK)
                self.transition(PlcState.SEMI_OPEN_CAPTURE_WINDOW)
            else:
                self.acknowledge_pc_event(sequence, AckStatus.INVALID_STATE)
            return

        if event_type == EventCode.CAPTURE_REJECTED:
            if self.mode == ModeCode.SEMI_AUTO:
                self.acknowledge_pc_event(sequence, AckStatus.OK)
                self.active_error_code = ErrorCode(payload[0]) if payload and payload[0] in ErrorCode._value2member_map_ else ErrorCode.ERR_OPERATOR_CAPTURE_REJECTED
                self.queue_plc_event(EventCode.PLC_ERROR, [int(self.active_error_code), self.current_step])
                self.transition(PlcState.ERROR)
            else:
                self.acknowledge_pc_event(sequence, AckStatus.INVALID_STATE)
            return

        if event_type == EventCode.CAPTURE_DONE:
            if self.mode == ModeCode.SEMI_AUTO and self.state == PlcState.SEMI_WAIT_CAPTURE_DONE:
                self.acknowledge_pc_event(sequence, AckStatus.OK)
                self.transition(PlcState.SEMI_CLOSE_CAPTURE_WINDOW)
            else:
                self.acknowledge_pc_event(sequence, AckStatus.INVALID_STATE)
            return

        if event_type == EventCode.STOP_RUN:
            self.stop_motion_safely()
            self.acknowledge_pc_event(sequence, AckStatus.OK)
            self.queue_plc_event(EventCode.RUN_STOPPED)
            self.transition(PlcState.IDLE)
            return

        if event_type == EventCode.RESET_ERROR:
            if self.reset_allowed():
                self.active_error_code = ErrorCode.ERR_NONE
                self.acknowledge_pc_event(sequence, AckStatus.OK)
                self.queue_plc_event(EventCode.PLC_READY)
                self.transition(PlcState.IDLE)
            else:
                self.acknowledge_pc_event(sequence, AckStatus.REJECTED)
            return

        self.acknowledge_pc_event(sequence, AckStatus.UNKNOWN_EVENT)

    def run_state(self) -> None:
        now = time.time()

        if self.state == PlcState.BOOT:
            self.mode = ModeCode.NONE
            self.active_error_code = ErrorCode.ERR_NONE
            self.memory.write_d(PLC_ACK_BASE, [0, 0])
            self.memory.write_d(PLC_EVENT_BASE, [0] * EVENT_WORDS)
            self.memory.write_d(PC_ACK_BASE, [0, 0])
            self.transition(PlcState.WAIT_PC_READY)

        elif self.state == PlcState.WAIT_PC_READY:
            pass

        elif self.state == PlcState.IDLE:
            pass

        elif self.state == PlcState.MANUAL_IDLE:
            pass

        elif self.state == PlcState.MANUAL_VALIDATE_COMMAND:
            self.run_manual_validate_command()

        elif self.state == PlcState.MANUAL_START_COMMAND:
            self.queue_plc_event(EventCode.MANUAL_COMMAND_STARTED)
            self.motion_done_at = time.time() + self.motion_time_for_target()
            self.transition(PlcState.MANUAL_EXECUTING)

        elif self.state == PlcState.MANUAL_EXECUTING:
            if not self.safety_ok():
                self.stop_motion_safely()
                self.active_error_code = ErrorCode.ERR_SAFETY_OPERATION_NOT_ALLOWED
                self.queue_plc_event(EventCode.SAFETY_ERROR, [int(self.active_error_code)])
                self.transition(PlcState.ERROR)
            elif self.motion_done_at is not None and now >= self.motion_done_at:
                self.actual_position = self.target_position
                self.transition(PlcState.MANUAL_DONE)

        elif self.state == PlcState.MANUAL_DONE:
            self.queue_plc_event(EventCode.MANUAL_COMMAND_DONE, encode_xy_mm(*self.actual_position))
            self.transition(PlcState.MANUAL_IDLE)

        elif self.state == PlcState.SEMI_IDLE:
            pass

        elif self.state == PlcState.SEMI_LOAD_NEXT_STEP:
            if self.current_step >= len(self.scan_points):
                self.transition(PlcState.SEMI_RUN_COMPLETE)
            else:
                self.target_position = self.scan_points[self.current_step]
                self.queue_plc_event(EventCode.SEMI_AUTO_STEP_STARTED, [self.current_step])
                self.motion_done_at = time.time() + self.motion_time_for_target()
                self.transition(PlcState.SEMI_MOVE_TO_POSITION)

        elif self.state == PlcState.SEMI_MOVE_TO_POSITION:
            if not self.safety_ok():
                self.stop_motion_safely()
                self.active_error_code = ErrorCode.ERR_SAFETY_OPERATION_NOT_ALLOWED
                self.queue_plc_event(EventCode.SAFETY_ERROR, [int(self.active_error_code), self.current_step])
                self.transition(PlcState.ERROR)
            elif self.motion_done_at is not None and now >= self.motion_done_at:
                self.actual_position = self.target_position
                self.transition(PlcState.SEMI_POSITION_REACHED)

        elif self.state == PlcState.SEMI_POSITION_REACHED:
            self.queue_plc_event(EventCode.POSITION_REACHED, [self.current_step] + encode_xy_mm(*self.actual_position))
            self.queue_plc_event(EventCode.CAPTURE_AUTH_REQUEST, [self.current_step])
            self.capture_auth_deadline = time.time() + 8.0
            self.transition(PlcState.SEMI_WAIT_CAPTURE_AUTH)

        elif self.state == PlcState.SEMI_WAIT_CAPTURE_AUTH:
            if self.capture_auth_deadline and now > self.capture_auth_deadline:
                self.active_error_code = ErrorCode.ERR_COMM_PC_ACK_TIMEOUT
                self.queue_plc_event(EventCode.CAPTURE_TIMEOUT, [int(self.active_error_code), self.current_step])
                self.transition(PlcState.ERROR)

        elif self.state == PlcState.SEMI_OPEN_CAPTURE_WINDOW:
            self.queue_plc_event(EventCode.CAPTURE_WINDOW_OPEN, [self.current_step])
            self.capture_done_deadline = time.time() + 8.0
            self.transition(PlcState.SEMI_WAIT_CAPTURE_DONE)

        elif self.state == PlcState.SEMI_WAIT_CAPTURE_DONE:
            if self.capture_done_deadline and now > self.capture_done_deadline:
                self.active_error_code = ErrorCode.ERR_CAMERA_FRAME_TIMEOUT
                self.queue_plc_event(EventCode.CAPTURE_TIMEOUT, [int(self.active_error_code), self.current_step])
                self.transition(PlcState.ERROR)

        elif self.state == PlcState.SEMI_CLOSE_CAPTURE_WINDOW:
            self.queue_plc_event(EventCode.CAPTURE_WINDOW_CLOSED, [self.current_step])
            self.transition(PlcState.SEMI_STEP_COMPLETE)

        elif self.state == PlcState.SEMI_STEP_COMPLETE:
            self.queue_plc_event(EventCode.STEP_COMPLETE, [self.current_step])
            self.current_step += 1
            self.transition(PlcState.SEMI_LOAD_NEXT_STEP)

        elif self.state == PlcState.SEMI_RUN_COMPLETE:
            self.queue_plc_event(EventCode.RUN_COMPLETE)
            self.transition(PlcState.IDLE)

        elif self.state == PlcState.ERROR:
            self.stop_motion_safely()

    def run_manual_validate_command(self) -> None:
        if not self.safety_ok():
            self.active_error_code = ErrorCode.ERR_SAFETY_OPERATION_NOT_ALLOWED
            self.queue_plc_event(EventCode.MANUAL_COMMAND_ERROR, [int(self.active_error_code)])
            self.transition(PlcState.ERROR)
            return
        if self.stored_manual_event is None:
            self.active_error_code = ErrorCode.ERR_PLC_INVALID_STATE
            self.queue_plc_event(EventCode.MANUAL_COMMAND_ERROR, [int(self.active_error_code)])
            self.transition(PlcState.MANUAL_IDLE)
            return
        event_type, payload = self.stored_manual_event
        if event_type == EventCode.MANUAL_MOVE_REQUEST:
            try:
                x_mm, y_mm = decode_xy_mm(payload)
            except Exception:
                self.active_error_code = ErrorCode.ERR_PLC_INVALID_PAYLOAD
                self.queue_plc_event(EventCode.MANUAL_COMMAND_ERROR, [int(self.active_error_code)])
                self.transition(PlcState.MANUAL_IDLE)
                return
            if not self.target_in_range(x_mm, y_mm):
                self.active_error_code = ErrorCode.ERR_MOTION_TARGET_OUT_OF_RANGE
                self.queue_plc_event(EventCode.MANUAL_COMMAND_ERROR, [int(self.active_error_code)])
                self.transition(PlcState.MANUAL_IDLE)
                return
            self.target_position = (x_mm, y_mm)
            self.transition(PlcState.MANUAL_START_COMMAND)
            return
        if event_type == EventCode.MANUAL_HOME_REQUEST:
            self.target_position = (0.0, 0.0)
            self.transition(PlcState.MANUAL_START_COMMAND)
            return
        if event_type == EventCode.MANUAL_JOG_REQUEST:
            # Payload convention for demo: [axis, direction, distance_mm_x1000]
            self.target_position = (10.0, 10.0)
            self.transition(PlcState.MANUAL_START_COMMAND)
            return
        self.active_error_code = ErrorCode.ERR_PLC_UNKNOWN_EVENT
        self.queue_plc_event(EventCode.MANUAL_COMMAND_ERROR, [int(self.active_error_code)])
        self.transition(PlcState.MANUAL_IDLE)

    def safety_ok(self) -> bool:
        return True

    def target_in_range(self, x_mm: float, y_mm: float) -> bool:
        return 0.0 <= x_mm <= 500.0 and 0.0 <= y_mm <= 500.0

    def motion_time_for_target(self) -> float:
        x_mm, y_mm = self.target_position
        return 0.15 + min(0.5, (abs(x_mm) + abs(y_mm)) / 1000.0)

    def stop_motion_safely(self) -> None:
        self.motion_done_at = None

    def reset_allowed(self) -> bool:
        return self.state == PlcState.ERROR


def default_scan_points() -> list[tuple[float, float]]:
    return [(10, 10), (30, 10), (50, 10), (10, 30), (30, 30), (50, 30)]


def main() -> None:
    parser = argparse.ArgumentParser(description="PLC simulator for PC/PLC state-machine prototype")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=15000)
    args = parser.parse_args()

    memory = RegisterMemory()
    SlmpRequestHandler.memory = memory
    state_machine = PlcStateMachine(memory, default_scan_points())
    state_machine.start()

    server = ThreadedSlmpServer((args.host, args.port), SlmpRequestHandler)
    print(f"[SLMP] simulator listening on {args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[SLMP] stopping")
    finally:
        state_machine.stop()
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
