"""
Validation tests for the PC/PLC state-machine prototype.

Run from the same directory as:
    python test_controller_validation.py

What this validates:
    1. Startup handshake: PC_READY -> PLC_READY.
    2. Invalid state rejection: START_RUN before Semi-Auto mode.
    3. Manual-mode validation error: out-of-range target.
    4. Semi-auto error path: PC rejects capture, PLC reports PLC_ERROR.
    5. Full PC controller Manual Mode run.
    6. Full PC controller Semi-Auto Mode run.

The tests use only the Python standard library.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Iterator

from shared_protocol import (
    AckStatus,
    ErrorCode,
    EventCode,
    ModeCode,
    PcEventMailbox,
    PlcAckError,
    Slmp3eClient,
    SlmpConfig,
    encode_xy_mm,
)

ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        return int(sock.getsockname()[1])


def wait_for_port(host: str, port: int, timeout_sec: float = 5.0) -> None:
    deadline = time.time() + timeout_sec
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return
        except OSError as exc:
            last_error = exc
            time.sleep(0.05)
    raise TimeoutError(f"Timed out waiting for {host}:{port}: {last_error}")


@contextlib.contextmanager
def running_plc_sim() -> Iterator[tuple[int, subprocess.Popen[str]]]:
    """Start plc_sim.py on a free localhost port and stop it after the test."""
    port = get_free_port()
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "plc_sim.py", "--host", HOST, "--port", str(port)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    try:
        wait_for_port(HOST, port, timeout_sec=5.0)
        yield port, proc
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3.0)


def connect_mailbox(port: int) -> tuple[Slmp3eClient, PcEventMailbox]:
    client = Slmp3eClient(SlmpConfig(host=HOST, port=port, timeout_sec=2.0))
    client.connect()
    return client, PcEventMailbox(client)


def handshake(mailbox: PcEventMailbox) -> None:
    mailbox.publish_pc_event(EventCode.PC_READY, timeout_sec=2.0)
    event = mailbox.wait_for_plc_event(EventCode.PLC_READY, timeout_sec=3.0)
    assert event.event_type == int(EventCode.PLC_READY)
    mailbox.acknowledge_plc_event(event, AckStatus.OK)


def set_mode(mailbox: PcEventMailbox, mode: ModeCode) -> None:
    if mode == ModeCode.MANUAL:
        mailbox.publish_pc_event(EventCode.SET_MODE_MANUAL, timeout_sec=2.0)
    elif mode == ModeCode.SEMI_AUTO:
        mailbox.publish_pc_event(EventCode.SET_MODE_SEMI_AUTO, timeout_sec=2.0)
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    event = mailbox.wait_for_plc_event(EventCode.MODE_CHANGED, timeout_sec=3.0)
    assert event.event_type == int(EventCode.MODE_CHANGED)
    assert event.payload[0] == int(mode)
    mailbox.acknowledge_plc_event(event, AckStatus.OK)


def run_pc_controller(mode: str, port: int, capture_dir: Path, timeout_sec: float = 30.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "pc_controller.py",
            "--mode",
            mode,
            "--host",
            HOST,
            "--port",
            str(port),
            "--capture-dir",
            str(capture_dir),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout_sec,
    )


class ControllerValidationTests(unittest.TestCase):
    def test_01_startup_handshake(self) -> None:
        with running_plc_sim() as (port, _proc):
            client, mailbox = connect_mailbox(port)
            try:
                handshake(mailbox)
            finally:
                client.close()

    def test_02_start_run_before_semi_auto_is_rejected(self) -> None:
        with running_plc_sim() as (port, _proc):
            client, mailbox = connect_mailbox(port)
            try:
                handshake(mailbox)
                with self.assertRaises(PlcAckError) as ctx:
                    mailbox.publish_pc_event(EventCode.START_RUN, timeout_sec=2.0)
                self.assertEqual(ctx.exception.status, int(AckStatus.INVALID_STATE))
            finally:
                client.close()

    def test_03_manual_out_of_range_target_reports_manual_command_error(self) -> None:
        with running_plc_sim() as (port, _proc):
            client, mailbox = connect_mailbox(port)
            try:
                handshake(mailbox)
                set_mode(mailbox, ModeCode.MANUAL)

                # This target is intentionally outside the simulator's valid 0..500 mm range.
                mailbox.publish_pc_event(
                    EventCode.MANUAL_MOVE_REQUEST,
                    encode_xy_mm(999.0, 999.0),
                    timeout_sec=2.0,
                )

                event = mailbox.wait_for_plc_event(EventCode.MANUAL_COMMAND_ERROR, timeout_sec=3.0)
                self.assertEqual(event.event_type, int(EventCode.MANUAL_COMMAND_ERROR))
                self.assertEqual(event.payload[0], int(ErrorCode.ERR_MOTION_TARGET_OUT_OF_RANGE))
                mailbox.acknowledge_plc_event(event, AckStatus.OK)
            finally:
                client.close()

    def test_04_semi_auto_capture_rejected_reports_plc_error(self) -> None:
        with running_plc_sim() as (port, _proc):
            client, mailbox = connect_mailbox(port)
            try:
                handshake(mailbox)
                set_mode(mailbox, ModeCode.SEMI_AUTO)
                mailbox.publish_pc_event(EventCode.START_RUN, timeout_sec=2.0)

                # Consume PLC events until the capture authorization request appears.
                saw_auth_request = False
                deadline = time.time() + 8.0
                while time.time() < deadline:
                    event = mailbox.wait_for_plc_event(timeout_sec=2.0)
                    if event.event_type == int(EventCode.CAPTURE_AUTH_REQUEST):
                        saw_auth_request = True
                        mailbox.acknowledge_plc_event(event, AckStatus.OK)
                        break
                    mailbox.acknowledge_plc_event(event, AckStatus.OK)

                self.assertTrue(saw_auth_request, "PLC did not request capture authorization")

                mailbox.publish_pc_event(
                    EventCode.CAPTURE_REJECTED,
                    [int(ErrorCode.ERR_OPERATOR_CAPTURE_REJECTED), 0],
                    timeout_sec=2.0,
                )
                error_event = mailbox.wait_for_plc_event(EventCode.PLC_ERROR, timeout_sec=3.0)
                self.assertEqual(error_event.payload[0], int(ErrorCode.ERR_OPERATOR_CAPTURE_REJECTED))
                mailbox.acknowledge_plc_event(error_event, AckStatus.REJECTED)
            finally:
                client.close()

    def test_05_full_pc_controller_manual_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir, running_plc_sim() as (port, _proc):
            capture_dir = Path(tmpdir) / "manual_captures"
            result = run_pc_controller("manual", port, capture_dir, timeout_sec=30.0)

            self.assertEqual(result.returncode, 0, msg=result.stdout)
            self.assertIn("PC_IDLE -> PC_MANUAL_SELECT", result.stdout)
            self.assertIn("manual demo complete", result.stdout)

            captures = sorted(capture_dir.glob("capture_*.json"))
            self.assertEqual(len(captures), 3, msg=f"stdout:\n{result.stdout}")
            for path in captures:
                record = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(record["mode"], "manual")

    def test_06_full_pc_controller_semi_auto_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir, running_plc_sim() as (port, _proc):
            capture_dir = Path(tmpdir) / "semi_auto_captures"
            result = run_pc_controller("semi-auto", port, capture_dir, timeout_sec=40.0)

            self.assertEqual(result.returncode, 0, msg=result.stdout)
            self.assertIn("PC_IDLE -> PC_SEMI_SELECT", result.stdout)
            self.assertIn("semi-auto run complete", result.stdout)

            captures = sorted(capture_dir.glob("capture_*.json"))
            # plc_sim.default_scan_points() contains six scan points.
            self.assertEqual(len(captures), 6, msg=f"stdout:\n{result.stdout}")
            for path in captures:
                record = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(record["mode"], "semi-auto")
                self.assertIsNotNone(record["step_index"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
