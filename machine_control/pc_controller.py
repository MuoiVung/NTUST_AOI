"""
PC controller for the DUO_AOI PC <-> PLC <-> camera simulator.

This version extends the earlier simulator with:
- optional SQLite database logging
- optional SerialTest API fixture lookup
- generated scan recipe metadata from PCB dimensions

Run the PLC simulator and camera simulator first:
    python plc_sim.py --host 127.0.0.1 --port 15000
    python camera_sim.py --host 127.0.0.1 --port 16000 --capture-dir captures_simulated

Then run one of:
    python pc_controller.py --mode manual
    python pc_controller.py --mode semi-auto --database-path sim.db --serial-number C26602074
"""

from __future__ import annotations

import argparse
import hashlib
import time
import logging
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger("pc_controller")
logger.setLevel(logging.INFO)
if not logger.handlers:
    rfh = RotatingFileHandler("pc_controller.log", maxBytes=10*1024*1024, backupCount=5)
    sh = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    rfh.setFormatter(formatter)
    sh.setFormatter(formatter)
    logger.addHandler(rfh)
    logger.addHandler(sh)

def print(*args, **kwargs):
    logger.info(" ".join(map(str, args)))


from database_pg import PostgresDatabase, RunInfo, StepInfo, open_database
from recipe import Recipe, RecipeStep, RecipeValidationError, generate_grid_recipe, validate_board_dimensions
from serialtest_api_client import SerialLookupResult, SerialTestApiClient, SerialTestApiError
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


def ack_name(code: int) -> str:
    try:
        return AckStatus(code).name
    except ValueError:
        return f"UNKNOWN_ACK_{code}"


class PcController:
    def __init__(
        self,
        host: str,
        port: int,
        mode: str,
        camera_host: str,
        camera_port: int,
        database_path: str | None = None,
        serial_number: str = "C26602074",
        board_side: str = "T",
        api_mode: str = "fixture",
        api_endpoint: Optional[str] = None,
        api_fixture: str | None = None,
        operator_id: str = "operator",
        machine_id: str = "DUO_AOI_SIM",
    ):
        self.host = host
        self.port = port
        self.camera_host = camera_host
        self.camera_port = camera_port
        self.requested_mode = mode
        self.state = PcState.STARTUP
        self.reconnect_attempts = 0
        self.client = Slmp3eClient(SlmpConfig(host=host, port=port))
        self.mailbox = PcEventMailbox(self.client)
        self.plc_host = host
        self.plc_port = port
        self.camera_top = RealCameraSDK("CAM1", "TOP")
        self.camera_bottom = RealCameraSDK("CAM2", "BOTTOM")

        self.api_endpoint = api_endpoint
        self.db: PostgresDatabase = open_database()
        with self.db.conn.cursor() as cur:
            cur.execute("LISTEN new_run_sn;")
            
        kwargs = {"mode": api_mode}
        if api_endpoint:
            kwargs["endpoint"] = api_endpoint
        if api_fixture:
            kwargs["fixture_path"] = api_fixture
        self.api_client = SerialTestApiClient(**kwargs)

        self.serial_number = serial_number
        self.board_side = board_side
        self.operator_id = operator_id
        self.machine_id = machine_id
        self.active_error_code = ErrorCode.ERR_NONE
        self.selected_mode = ModeCode.NONE
        self.current_step: Optional[int] = None
        self.expected_step: Optional[int] = None
        self.current_position: Optional[tuple[float, float]] = None
        self.requested_step: Optional[int] = None
        self.manual_command: Optional[tuple[EventCode, list[int], tuple[float, float] | None]] = None
        self.manual_points = [(20.0, 15.0), (40.0, 15.0), (40.0, 35.0)]
        self.operator_id = ""
        self.run_code: Optional[str] = None
        self.m_no: str = "UNKNOWN_M_NO"
        self.manual_index = 0
        self.recipe: Optional[Recipe] = None
        self.step_ids: dict[int, int] = {}
        self.last_lookup: Optional[SerialLookupResult] = None
        self.semi_auto_prepared = False
        self.recipe_downloaded = False

    def transition(self, new_state: PcState) -> None:
        if new_state != self.state:
            print(f"[PC] {self.state.value} -> {new_state.value}")
            self.db.log_event(
                {
                    "run_code": self.run_code,
                    "source": "PC",
                    "direction": "PC_INTERNAL",
                    "event_name": "STATE_TRANSITION",
                    "pc_state": new_state.value,
                    "mode": self.mode_text(),
                    "step_index": self.current_step,
                    "payload_json": {"from": self.state.value, "to": new_state.value},
                }
            )
            self.state = new_state

    def mode_text(self) -> str:
        if self.selected_mode == ModeCode.MANUAL:
            return "manual"
        if self.selected_mode == ModeCode.SEMI_AUTO:
            return "semi-auto"
        return self.requested_mode

    def run(self) -> None:
        try:
            while self.state != PcState.SHUTDOWN:
                try:
                    self.run_state()
                except OSError as exc:
                    print(f"[PC] PLC connection lost during run loop: {exc}")
                    if self.run_code:
                        self.mark_run_status(self.run_code, "FAILED")
                        self.run_code = None
                    self.enter_error(ErrorCode.ERR_COMM_CONNECT_FAILED, f"PLC disconnected: {exc}")
                time.sleep(0.02)
        finally:
            self.shutdown_resources()

    def run_state(self) -> None:
        if self.state == PcState.STARTUP:
            self.transition(PcState.INIT_CAMERA)

        elif self.state == PcState.INIT_CAMERA:
            try:
                self.camera_top.start()
                self.camera_bottom.start()
                self.transition(PcState.CONNECT_PLC)
            except Exception as exc:
                print(f"[PC] camera connection error: {exc}")
                self.enter_error(ErrorCode.ERR_CAMERA_NOT_DETECTED, str(exc))

        elif self.state == PcState.CONNECT_PLC:
            try:
                self.client.connect()
                print(f"[PC] connected to PLC at {self.host}:{self.port}")
                self.reconnect_attempts = 0
                self.db.set_config("plc_status", "OK")
                self.mailbox.sync_sequence()
                self.mailbox.publish_pc_event(EventCode.PC_READY)
                self.log_pc_event(EventCode.PC_READY, None, None, [], "PC_TO_PLC")
                self.transition(PcState.WAIT_PLC_READY)
            except Exception as exc:
                print(f"[PC] connection error: {exc}")
                self.db.set_config("plc_status", "ERROR")
                self.enter_error(ErrorCode.ERR_COMM_CONNECT_FAILED, str(exc))

        elif self.state == PcState.WAIT_PLC_READY:
            event = self.wait_event(EventCode.PLC_READY, timeout_sec=5.0)
            if event is None:
                return
            self.ack(event)
            self.transition(PcState.IDLE)

        elif self.state == PcState.IDLE:
            if self.requested_mode == "manual":
                self.prepare_manual_run()
                self.transition(PcState.MANUAL_SELECT)
            elif self.requested_mode == "semi-auto":
                import select
                # Check DB for pending run signal via NOTIFY
                pending_sn = None
                try:
                    if select.select([self.db.conn], [], [], 0) == ([self.db.conn], [], []):
                        self.db.conn.poll()
                        while self.db.conn.notifies:
                            notify = self.db.conn.notifies.pop(0)
                            pending_sn = notify.payload
                except Exception as e:
                    print(f"[PC] Error polling notifications: {e}")
                
                if pending_sn:
                    print(f"[PC] Detected pending run for S/N: {pending_sn}")
                    self.serial_number = pending_sn
                    self.run_code = None
                    self.semi_auto_prepared = False
                    self.recipe_downloaded = False
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
                self.enter_error(ErrorCode.ERR_PC_INVALID_MODE, "PLC did not enter manual mode")

        elif self.state == PcState.MANUAL_IDLE:
            if self.manual_index >= len(self.manual_points):
                print("[PC] manual demo complete")
                if self.run_code:
                    self.db.finish_run(self.run_code, "COMPLETED")
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
                self.enter_error(self.payload_error(event), "manual command error")
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
                self.enter_error(self.payload_error(event), "manual command error")
            else:
                self.handle_unexpected_event(event)

        elif self.state == PcState.MANUAL_CAPTURE:
            if not self.camera_ready():
                self.enter_error(ErrorCode.ERR_CAMERA_ACQUISITION_NOT_RUNNING, "camera not ready")
                return
            _, _, target = self.manual_command or (None, None, None)
            x_mm, y_mm = target if target else (None, None)
            try:
                path_top = self.camera_top.save_latest(
                    mode="MANUAL",
                    step_index=self.manual_index,
                    x_mm=x_mm,
                    y_mm=y_mm,
                    plc_event_sequence=None,
                    note="manual mode image",
                    run_code=self.run_code or "MANUAL_RUN",
                    m_no=self.m_no,
                    sn=self.serial_number or "UNKNOWN_SN",
                    row_idx=0,
                    col_idx=self.manual_index
                )
                self.log_camera_image(path_top, self.manual_index, self.camera_top)

                path_bottom = self.camera_bottom.save_latest(
                    mode="MANUAL",
                    step_index=self.manual_index,
                    x_mm=x_mm,
                    y_mm=y_mm,
                    plc_event_sequence=None,
                    note="manual mode image",
                    run_code=self.run_code or "MANUAL_RUN",
                    m_no=self.m_no,
                    sn=self.serial_number or "UNKNOWN_SN",
                    row_idx=0,
                    col_idx=self.manual_index
                )
                self.log_camera_image(path_bottom, self.manual_index, self.camera_bottom)
                self.transition(PcState.MANUAL_REPORT_CAPTURE_DONE)
            except Exception as exc:
                print(f"[PC] camera save error: {exc}")
                self.enter_error(ErrorCode.ERR_IMAGE_SAVE_FAILED, str(exc))

        elif self.state == PcState.MANUAL_REPORT_CAPTURE_DONE:
            self.send_or_error(EventCode.MANUAL_CAPTURE_DONE, [self.manual_index, self.camera_top.image_index])
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
                self.enter_error(ErrorCode.ERR_PC_INVALID_MODE, "PLC did not enter semi-auto mode")

        elif self.state == PcState.SEMI_START_RUN:
            if not self.semi_auto_prepared:
                if not self.prepare_semi_auto_run():
                    return
            if not self.camera_ready():
                self.enter_error(ErrorCode.ERR_CAMERA_ACQUISITION_NOT_RUNNING, "camera not ready")
                return
            if not self.recipe_downloaded:
                if not self.download_recipe_to_plc():
                    return
            self.send_or_error(EventCode.START_RUN)
            if self.state != PcState.ERROR:
                if self.run_code:
                    self.db.mark_run_status(self.run_code, "RUNNING")
                self.transition(PcState.SEMI_MONITOR_RUN)

        elif self.state == PcState.SEMI_MONITOR_RUN:
            event = self.wait_event(timeout_sec=15.0)
            if event is None:
                return
            self.handle_semi_event(event)

        elif self.state == PcState.SEMI_CHECK_CAPTURE_READY:
            if self.requested_step != self.expected_step:
                self.reject_capture(ErrorCode.ERR_PC_SEQUENCE_MISMATCH)
            elif not self.camera_ready():
                self.reject_capture(ErrorCode.ERR_CAMERA_ACQUISITION_NOT_RUNNING)
            elif not self.camera_fresh():
                self.reject_capture(ErrorCode.ERR_CAMERA_STALE_FRAME)
            else:
                self.mark_step(self.requested_step, "CAPTURE_AUTHORIZED", capture_auth_at="CURRENT_TIMESTAMP")
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
                self.mark_step(self.requested_step, "CAPTURE_WINDOW_OPEN", capture_window_at="CURRENT_TIMESTAMP")
                self.transition(PcState.SEMI_CAPTURE_IMAGE)
            else:
                self.handle_unexpected_event(event)

        elif self.state == PcState.SEMI_CAPTURE_IMAGE:
            x_mm, y_mm = self.current_position if self.current_position else (None, None)
            row_idx = 0
            col_idx = self.requested_step or 0
            if self.recipe and self.recipe.steps:
                for s in self.recipe.steps:
                    if s.step_index == self.requested_step:
                        row_idx = s.row_idx
                        col_idx = s.col_idx
                        break
            try:
                path_top = self.camera_top.save_latest(
                    mode="SEMI_AUTO",
                    step_index=self.requested_step,
                    x_mm=x_mm,
                    y_mm=y_mm,
                    plc_event_sequence=None,
                    note="semi-auto mode image",
                    run_code=self.run_code or "SEMI_RUN",
                    m_no=self.m_no,
                    sn=self.serial_number or "UNKNOWN_SN",
                    row_idx=row_idx,
                    col_idx=col_idx
                )
                self.log_camera_image(path_top, self.requested_step, self.camera_top)

                path_bottom = self.camera_bottom.save_latest(
                    mode="SEMI_AUTO",
                    step_index=self.requested_step,
                    x_mm=x_mm,
                    y_mm=y_mm,
                    plc_event_sequence=None,
                    note="semi-auto mode image",
                    run_code=self.run_code or "SEMI_RUN",
                    m_no=self.m_no,
                    sn=self.serial_number or "UNKNOWN_SN",
                    row_idx=row_idx,
                    col_idx=col_idx
                )
                self.log_camera_image(path_bottom, self.requested_step, self.camera_bottom)
                self.mark_step(self.requested_step, "CAPTURED", capture_done_at="CURRENT_TIMESTAMP")
                self.transition(PcState.SEMI_REPORT_CAPTURE_DONE)
            except Exception as exc:
                print(f"[PC] camera save error: {exc}")
                try:
                    self.mailbox.publish_pc_event(
                        EventCode.CAPTURE_REJECTED,
                        [int(ErrorCode.ERR_IMAGE_SAVE_FAILED), self.requested_step or 0],
                        timeout_sec=1.0,
                    )
                except Exception:
                    pass
                self.enter_error(ErrorCode.ERR_IMAGE_SAVE_FAILED, str(exc))

        elif self.state == PcState.SEMI_REPORT_CAPTURE_DONE:
            self.send_or_error(EventCode.CAPTURE_DONE, [self.requested_step or 0, self.camera_top.image_index])
            if self.state != PcState.ERROR:
                self.transition(PcState.SEMI_MONITOR_RUN)

        elif self.state == PcState.ERROR:
            print(f"[PC] ERROR {int(self.active_error_code)} {error_name(int(self.active_error_code))}")
            try:
                self.mailbox.publish_pc_event(EventCode.STOP_RUN, [int(self.active_error_code)], timeout_sec=1.0)
            except Exception:
                pass
            if self.run_code:
                self.db.finish_run(self.run_code, "ERROR")
            
            # Clean up old sockets/cameras and auto-reconnect
            try:
                self.camera_top.stop()
                self.camera_bottom.stop()
                self.client.close()
            except:
                pass
            
            # Exponential Backoff for Reconnection
            self.reconnect_attempts += 1
            sleep_time = min(2.0 * (2 ** (self.reconnect_attempts - 1)), 30.0)
            print(f"[PC] Auto-reconnecting in {sleep_time} seconds... (Attempt {self.reconnect_attempts})")
            time.sleep(sleep_time)
            self.transition(PcState.STARTUP)

    def prepare_manual_run(self) -> None:
        if self.run_code is not None:
            return
        self.run_code = f"MANUAL_{int(time.time())}"
        self.db.create_run(
            RunInfo(
                run_code=self.run_code,
                mode="manual",
                board_side=self.board_side,
                serial_number=self.serial_number,
                machine_id=self.machine_id,
                operator_id=self.operator_id,
                recipe_name="manual-demo",
                note="manual simulator run",
            )
        )

    def prepare_semi_auto_run(self) -> bool:
        try:
            lookup = self.api_client.lookup(self.serial_number)
            self.last_lookup = lookup
            self.db.log_external_lookup(
                {
                    "serial_number_query": lookup.serial_number_query,
                    "api_endpoint": lookup.api_endpoint,
                    "http_status_code": lookup.http_status_code,
                    "has_data": lookup.has_data,
                    "msg": lookup.msg,
                    "sn_returned": lookup.sn,
                    "m_no": lookup.m_no,
                    "p_no": lookup.p_no,
                    "semi_model": lookup.semi_model,
                    "pcb_length_mm": lookup.pcb_length_mm,
                    "pcb_width_mm": lookup.pcb_width_mm,
                    "accepted": lookup.ok,
                    "raw_response_json": lookup.raw_response,
                }
            )
            if not lookup.ok:
                self.enter_error(ErrorCode.ERR_OPERATOR_BOARD_NAME_MISSING, lookup.msg or "serial lookup failed")
                return False
            length, width = validate_board_dimensions(lookup.pcb_length_mm, lookup.pcb_width_mm)
            self.recipe = generate_grid_recipe(length, width, name=f"grid_{int(length)}x{int(width)}")
            self.m_no = lookup.m_no or "UNKNOWN_M_NO"
            
            # 1. Invalidates previous incomplete runs and gets deleted run codes
            import datetime
            import os
            import shutil
            sn_for_run = lookup.sn or self.serial_number
            deleted_runs = self.db.check_and_invalidate_previous_runs(sn_for_run)
            
            # Delete physical folders of incomplete runs
            watch_dir = os.getenv("IMAGE_WATCH_DIR", os.path.join(os.path.dirname(__file__), "..", "watch_dir"))
            for d_run in deleted_runs:
                # Top side
                run_path_top = os.path.join(watch_dir, self.m_no, sn_for_run, d_run, "TOP")
                if os.path.exists(run_path_top):
                    shutil.rmtree(run_path_top, ignore_errors=True)
                # Bottom side
                run_path_bottom = os.path.join(watch_dir, self.m_no, sn_for_run, d_run, "BOTTOM")
                if os.path.exists(run_path_bottom):
                    shutil.rmtree(run_path_bottom, ignore_errors=True)
            
            # 2. ISO 8601-like run_code
            self.run_code = f"{sn_for_run}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.db.create_run(
                RunInfo(
                    run_code=self.run_code,
                    mode="semi-auto",
                    board_code=lookup.semi_model,
                    board_side=self.board_side,
                    serial_number=lookup.sn or self.serial_number,
                    production_work_order=lookup.m_no,
                    packaging_work_order=lookup.p_no,
                    semi_model=lookup.semi_model,
                    pcb_length_mm=length,
                    pcb_width_mm=width,
                    recipe_name=self.recipe.name,
                    machine_id=self.machine_id,
                    operator_id=self.operator_id,
                    note="created from SerialTest API lookup",
                    api_has_data=lookup.has_data,
                    api_msg=lookup.msg,
                    api_raw_response_json=lookup.raw_response,
                )
            )
            for step in self.recipe.steps:
                step_id = self.db.create_step(
                    self.run_code,
                    StepInfo(
                        step_index=step.step_index,
                        row_idx=step.row_idx,
                        col_idx=step.col_idx,
                        target_x_mm=step.target_x_mm,
                        target_y_mm=step.target_y_mm,
                        status="PENDING",
                    ),
                )
                self.step_ids[step.step_index] = step_id
            self.semi_auto_prepared = True
            print(
                f"[PC] prepared semi-auto run {self.run_code}: "
                f"{self.recipe.rows}x{self.recipe.cols} grid from {length}x{width} mm"
            )
            return True
        except (SerialTestApiError, RecipeValidationError) as exc:
            self.enter_error(ErrorCode.ERR_PC_METADATA_MISSING, str(exc))
            return False

    def download_recipe_to_plc(self) -> bool:
        """Send the generated recipe/grid to the PLC simulator before START_RUN.

        Payload format:
            RECIPE_DOWNLOAD_START: [step_count, rows, cols]
            RECIPE_STEP_DATA: [step_index, row_idx, col_idx, x_lo, x_hi, y_lo, y_hi]
            RECIPE_DOWNLOAD_END: []

        The PLC simulator acknowledges every PC event. After END, the PLC publishes
        RECIPE_LOADED, which the PC acknowledges before starting the run.
        """
        if self.recipe is None:
            self.enter_error(ErrorCode.ERR_PLC_RECIPE_NOT_LOADED, "recipe not prepared")
            return False
        try:
            self.send_or_error(
                EventCode.RECIPE_DOWNLOAD_START,
                [len(self.recipe.steps), self.recipe.rows, self.recipe.cols],
            )
            if self.state == PcState.ERROR:
                return False
            for step in self.recipe.steps:
                payload = [step.step_index, step.row_idx, step.col_idx] + encode_xy_mm(
                    step.target_x_mm,
                    step.target_y_mm,
                )
                self.send_or_error(EventCode.RECIPE_STEP_DATA, payload)
                if self.state == PcState.ERROR:
                    return False
            self.send_or_error(EventCode.RECIPE_DOWNLOAD_END)
            if self.state == PcState.ERROR:
                return False
            event = self.wait_event(EventCode.RECIPE_LOADED, timeout_sec=5.0)
            if event is None:
                return False
            self.ack(event)
            self.recipe_downloaded = True
            print(
                f"[PC] downloaded recipe to PLC: "
                f"{len(self.recipe.steps)} steps, {self.recipe.rows}x{self.recipe.cols}"
            )
            return True
        except Exception as exc:
            self.enter_error(ErrorCode.ERR_COMM_WRITE_FAILED, str(exc))
            return False

    def handle_semi_event(self, event: PlcEvent) -> None:
        print(f"[PC] PLC event {event.name} seq={event.sequence} payload={event.payload}")
        et = event.event_type
        if et == int(EventCode.RUN_STARTED):
            self.ack(event)
        elif et == int(EventCode.SEMI_AUTO_STEP_STARTED):
            self.current_step = event.payload[0]
            self.expected_step = self.current_step
            self.mark_step(self.current_step, "MOVING")
            self.ack(event)
        elif et == int(EventCode.POSITION_REACHED):
            self.current_step = event.payload[0]
            self.current_position = decode_xy_mm(event.payload[1:5])
            self.mark_step(
                self.current_step,
                "POSITION_REACHED",
                actual_x_mm=self.current_position[0],
                actual_y_mm=self.current_position[1],
                position_reached_at="CURRENT_TIMESTAMP",
            )
            self.ack(event)
        elif et == int(EventCode.CAPTURE_AUTH_REQUEST):
            self.requested_step = event.payload[0]
            self.ack(event)
            self.transition(PcState.SEMI_CHECK_CAPTURE_READY)
        elif et == int(EventCode.CAPTURE_WINDOW_OPEN):
            self.ack(event)
            self.mark_step(self.current_step, "CAPTURE_WINDOW_OPEN", capture_window_at="CURRENT_TIMESTAMP")
            self.transition(PcState.SEMI_CAPTURE_IMAGE)
        elif et == int(EventCode.CAPTURE_WINDOW_CLOSED):
            self.ack(event)
        elif et == int(EventCode.STEP_COMPLETE):
            self.mark_step(event.payload[0], "COMPLETED", completed_at="CURRENT_TIMESTAMP")
            self.ack(event)
        elif et == int(EventCode.RUN_COMPLETE):
            self.ack(event)
            print("[PC] semi-auto run complete")
            if self.run_code:
                self.db.finish_run(self.run_code, "COMPLETED")
            # Loop back to IDLE to wait for next board!
            self.transition(PcState.IDLE)
        elif et >= 900:
            self.ack(event, AckStatus.REJECTED)
            self.enter_error(self.payload_error(event), "PLC error event")
        else:
            self.handle_unexpected_event(event)

    def camera_ready(self) -> bool:
        try:
            return self.camera_top.ready() and self.camera_bottom.ready()
        except Exception as exc:
            print(f"[PC] camera ready error: {exc}")
            return False

    def camera_fresh(self) -> bool:
        try:
            return self.camera_top.latest_frame_fresh() and self.camera_bottom.latest_frame_fresh()
        except Exception as exc:
            print(f"[PC] camera fresh error: {exc}")
            return False

    def send_or_error(self, event_type: EventCode, payload: Optional[list[int]] = None) -> None:
        try:
            print(f"[PC] send {event_type.name} payload={payload or []}")
            sequence = self.mailbox.publish_pc_event(event_type, payload or [], timeout_sec=3.0)
            self.log_pc_event(event_type, sequence, AckStatus.OK, payload or [], "PC_TO_PLC")
        except PlcAckError as exc:
            print(f"[PC] ACK error: {exc}")
            self.log_pc_event(event_type, exc.sequence, AckStatus(exc.status), payload or [], "PC_TO_PLC")
            self.enter_error(ErrorCode.ERR_PLC_INVALID_STATE, str(exc))
        except Exception as exc:
            print(f"[PC] communication error while sending {event_type.name}: {exc}")
            self.enter_error(ErrorCode.ERR_COMM_ACK_TIMEOUT, str(exc))

    def wait_event(self, expected: Optional[EventCode] = None, timeout_sec: float = 10.0) -> Optional[PlcEvent]:
        try:
            return self.mailbox.wait_for_plc_event(expected=expected, timeout_sec=timeout_sec)
        except TimeoutError as exc:
            print(f"[PC] timeout: {exc}")
            self.enter_error(ErrorCode.ERR_COMM_PLC_EVENT_TIMEOUT, str(exc))
            return None
        except Exception as exc:
            print(f"[PC] communication error while waiting for event: {exc}")
            self.enter_error(ErrorCode.ERR_COMM_READ_FAILED, str(exc))
            return None

    def ack(self, event: PlcEvent, status: AckStatus = AckStatus.OK) -> None:
        print(f"[PC] ACK PLC event {event.name} seq={event.sequence} status={status.name}")
        self.mailbox.acknowledge_plc_event(event, status)
        self.db.log_event(
            {
                "run_code": self.run_code,
                "step_id": self.step_ids.get(event.payload[0]) if event.payload else None,
                "source": "PLC",
                "direction": "PLC_TO_PC",
                "event_name": event.name,
                "event_code": event.event_type,
                "sequence_number": event.sequence,
                "ack_name": status.name,
                "ack_code": int(status),
                "pc_state": self.state.value,
                "mode": self.mode_text(),
                "step_index": event.payload[0] if event.payload else self.current_step,
                "payload_json": event.payload,
            }
        )

    def payload_error(self, event: PlcEvent) -> ErrorCode:
        code = event.payload[0] if event.payload else int(ErrorCode.ERR_UNKNOWN)
        return ErrorCode(code) if code in ErrorCode._value2member_map_ else ErrorCode.ERR_UNKNOWN

    def handle_unexpected_event(self, event: PlcEvent) -> None:
        print(f"[PC] unexpected PLC event {event.name}")
        self.ack(event, AckStatus.REJECTED)
        if event.event_type >= 900:
            self.enter_error(self.payload_error(event), "unexpected PLC error event")
        else:
            self.enter_error(ErrorCode.ERR_PLC_INVALID_STATE, f"unexpected PLC event {event.name}")

    def reject_capture(self, code: ErrorCode) -> None:
        self.mailbox.publish_pc_event(EventCode.CAPTURE_REJECTED, [int(code), self.requested_step or 0])
        self.log_pc_event(
            EventCode.CAPTURE_REJECTED,
            None,
            AckStatus.REJECTED,
            [int(code), self.requested_step or 0],
            "PC_TO_PLC",
        )
        self.mark_step(self.requested_step, "CAPTURE_REJECTED", error_code=int(code))
        self.enter_error(code, "capture rejected")

    def enter_error(self, code: ErrorCode, message: str = "") -> None:
        self.db.set_config("plc_status", "ERROR")
        self.active_error_code = code
        self.db.log_error(
            {
                "run_code": self.run_code,
                "step_id": self.step_ids.get(self.current_step) if self.current_step is not None else None,
                "error_code": int(code),
                "error_symbol": error_name(int(code)),
                "error_category": self.error_category(code),
                "error_message": message,
                "source": "PC",
                "pc_state": self.state.value,
                "mode": self.mode_text(),
                "step_index": self.current_step,
                "recovery_action": "Stop simulator run and inspect logs",
                "details_json": {"requested_step": self.requested_step},
            }
        )
        self.transition(PcState.ERROR)

    @staticmethod
    def error_category(code: ErrorCode) -> str:
        value = int(code)
        if value < 1000:
            return "OK"
        categories = {
            1: "PC_SOFTWARE",
            2: "PLC_STATE_MACHINE",
            3: "COMMUNICATION",
            4: "CAMERA",
            5: "STORAGE",
            6: "MOTION",
            7: "SAFETY",
            8: "OPERATOR_WORKFLOW",
            9: "FATAL_UNKNOWN",
        }
        return categories.get(value // 1000, "UNKNOWN")

    def log_pc_event(
        self,
        event_type: EventCode,
        sequence: Optional[int],
        ack_status: Optional[AckStatus],
        payload: list[int],
        direction: str,
    ) -> None:
        self.db.log_event(
            {
                "run_code": self.run_code,
                "step_id": self.step_ids.get(self.current_step) if self.current_step is not None else None,
                "source": "PC",
                "direction": direction,
                "event_name": event_type.name,
                "event_code": int(event_type),
                "sequence_number": sequence,
                "ack_name": ack_status.name if ack_status is not None else None,
                "ack_code": int(ack_status) if ack_status is not None else None,
                "pc_state": self.state.value,
                "mode": self.mode_text(),
                "step_index": self.current_step,
                "payload_json": payload,
            }
        )

    def mark_step(self, step_index: Optional[int], status: str, **fields: object) -> None:
        if step_index is None:
            return
        step_id = self.step_ids.get(step_index)
        if step_id is None:
            return
        normalized = {k: (None if v == "CURRENT_TIMESTAMP" else v) for k, v in fields.items()}
        # sqlite table stores timestamp strings; use CURRENT_TIMESTAMP via a separate simple update if requested.
        timestamp_fields = [k for k, v in fields.items() if v == "CURRENT_TIMESTAMP"]
        self.db.update_step_status(step_id, status, step_index=step_index, **normalized)
        if timestamp_fields:
            # Direct SQL is kept here only to support the simulator timestamp convenience.
            conn = getattr(self.db, "conn", None)
            if conn is not None:
                try:
                    with conn.cursor() as cur:
                        assignments = ", ".join(f"{name} = CURRENT_TIMESTAMP" for name in timestamp_fields)
                        cur.execute(f"UPDATE run_steps SET {assignments} WHERE step_id = %s", (step_id,))
                except Exception as e:
                    print(f"[DB] Error updating timestamp: {e}")

    def log_camera_image(
        self,
        path: Path,
        step_index: Optional[int],
        camera: RealCameraSDK
    ) -> None:
        checksum = None
        file_size = None
        try:
            data = path.read_bytes()
            checksum = hashlib.sha256(data).hexdigest()
            file_size = len(data)
        except OSError:
            pass
        recipe_step = self.recipe_step(step_index)
        row_idx = recipe_step.row_idx if recipe_step else 0
        col_idx = recipe_step.col_idx if recipe_step else 0

        # Send to FastAPI immediately
        try:
            import requests
            import os
            base_url = os.environ.get("FASTAPI_URL", "http://127.0.0.1:8000").rstrip('/')
            api_url = f"{base_url}/images/"
            payload = {
                "run_number": self.run_code or "UNKNOWN",
                "side": camera.side,
                "row_idx": row_idx,
                "col_idx": col_idx,
                "file_size_bytes": file_size or 0,
                "local_path": str(path)
            }
            response = requests.post(api_url, json=payload, timeout=2)
            if response.status_code not in (200, 201):
                logger.error(f"Failed to post image metadata to API: {response.text}")
        except Exception as e:
                logger.error(f"Error posting image metadata to API: {e}")

        # Still log to local DB if needed
        self.db.log_image(
            {
                "run_code": self.run_code,
                "step_id": self.step_ids.get(step_index) if step_index is not None else None,
                "file_path": str(path),
                "image_index": camera.image_index,
                "row_idx": row_idx,
                "col_idx": col_idx,
                "camera_id": camera.camera_id,
                "camera_side": camera.side,
                "condition": "UNKNOWN",
                "capture_status": "CAPTURED",
                "file_size_bytes": file_size,
                "checksum": checksum,
                "metadata_json": {"step_index": step_index},
            }
        )

    def recipe_step(self, step_index: Optional[int]) -> Optional[RecipeStep]:
        if self.recipe is None or step_index is None:
            return None
        for step in self.recipe.steps:
            if step.step_index == step_index:
                return step
        return None

    def shutdown_resources(self) -> None:
        try:
            self.camera_top.stop()
            self.camera_bottom.stop()
        except Exception:
            pass
        try:
            self.client.close()
        except Exception:
            pass
        finally:
            self.db.set_config("plc_status", "ERROR")
            self.db.close()
        print("[PC] shutdown complete")


class RealCameraSDK:
    def __init__(self, camera_id: str, side: str):
        self.camera_id = camera_id
        self.side = side
        self.image_index = 0
        print(f"[{self.camera_id}] Initializing real camera connection ({self.side})...")

    def start(self):
        print(f"[{self.camera_id}] Camera started")

    def stop(self):
        print(f"[{self.camera_id}] Camera stopped")

    def ready(self) -> bool:
        return True

    def latest_frame_fresh(self) -> bool:
        return True

    def save_latest(self, mode: str, step_index: Optional[int], x_mm: Optional[float], y_mm: Optional[float], plc_event_sequence: Optional[int], note: str, run_code: str, m_no: str = "UNKNOWN_M_NO", sn: str = "UNKNOWN_SN", row_idx: int = 0, col_idx: int = 0) -> Path:
        self.image_index += 1
        import os
        import random
        import shutil
        
        watch_dir = os.getenv("IMAGE_WATCH_DIR", os.path.join(os.path.dirname(__file__), "..", "watch_dir"))
        mock_dir = os.path.join(os.path.dirname(__file__), "..", "mock_images")
        
        # New structure: watch_dir/{M_NO}/{SN}/{run_code}/{board_side}/
        run_folder = os.path.join(watch_dir, m_no, sn, run_code, self.side)
        os.makedirs(run_folder, exist_ok=True)
        os.makedirs(mock_dir, exist_ok=True)
        
        # New filename: {run_code}_{side}_r{row_idx}_c{col_idx}.jpg
        filename = f"{run_code}_{self.side}_r{row_idx}_c{col_idx}.jpg"
        filepath = os.path.join(run_folder, filename)
        
        mock_images = [f for f in os.listdir(mock_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
        if mock_images:
            chosen = random.choice(mock_images)
            shutil.copy2(os.path.join(mock_dir, chosen), filepath)
            print(f"[{self.camera_id}] Copied {chosen} to {filepath}")
        else:
            with open(filepath, "wb") as f:
                f.write(b"fake image data from SDK - please put real images in mock_images folder!")
            print(f"[CAMERA SDK] Created fake image {filepath}")
            
        return Path(filepath)

def main() -> None:
    parser = argparse.ArgumentParser(description="PC controller for the DUO_AOI PLC simulator")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=15000)
    parser.add_argument("--mode", choices=["manual", "semi-auto"], required=True)
    parser.add_argument("--camera-host", default="127.0.0.1")
    parser.add_argument("--camera-port", type=int, default=16000)
    parser.add_argument("--database-path", default="")
    parser.add_argument("--serial-number", default="C26602074")
    parser.add_argument("--board-side", default="T")
    parser.add_argument("--api-mode", choices=["fixture", "real"], default="fixture")
    parser.add_argument("--api-endpoint", default="")
    parser.add_argument("--api-fixture", default="")
    parser.add_argument("--operator-id", default="operator")
    parser.add_argument("--machine-id", default="DUO_AOI_SIM")
    args = parser.parse_args()

    controller = PcController(
        args.host,
        args.port,
        args.mode,
        args.camera_host,
        args.camera_port,
        database_path=args.database_path or None,
        serial_number=args.serial_number,
        board_side=args.board_side,
        api_mode=args.api_mode,
        api_endpoint=args.api_endpoint or None,
        api_fixture=args.api_fixture or None,
        operator_id=args.operator_id,
        machine_id=args.machine_id,
    )
    controller.run()


if __name__ == "__main__":
    main()
