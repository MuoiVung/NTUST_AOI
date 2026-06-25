"""
Shared local TCP camera protocol for the PC <-> camera separation.

Protocol:
    - One JSON object per line.
    - Request:  {"cmd": "READY", ...}\n
    - Reply:    {"ok": true, ...}\n

Supported commands:
    START        Start simulated/real acquisition.
    STOP         Stop acquisition.
    READY        Return whether camera service is running.
    FRESH        Return whether latest frame is fresh.
    SAVE_LATEST  Save the latest frame/image/record and return path/index.
    STATUS       Return camera service status.

The simulator writes JSON files instead of real images. A real IDS camera service
can keep the same command names and response fields.
"""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


class CameraTcpError(RuntimeError):
    pass


@dataclass
class CameraConfig:
    host: str = "127.0.0.1"
    port: int = 16000
    timeout_sec: float = 3.0


class CameraTcpClient:
    """Small client wrapper used by the PC controller."""

    def __init__(self, config: CameraConfig):
        self.config = config
        self.sock: Optional[socket.socket] = None
        self._reader = None

    def connect(self) -> None:
        self.sock = socket.create_connection(
            (self.config.host, self.config.port),
            timeout=self.config.timeout_sec,
        )
        self.sock.settimeout(self.config.timeout_sec)
        self._reader = self.sock.makefile("r", encoding="utf-8", newline="\n")

    def close(self) -> None:
        try:
            if self._reader is not None:
                self._reader.close()
        finally:
            self._reader = None
            if self.sock is not None:
                try:
                    self.sock.close()
                finally:
                    self.sock = None

    def request(self, cmd: str, **kwargs: Any) -> dict[str, Any]:
        if self.sock is None or self._reader is None:
            raise CameraTcpError("camera TCP client is not connected")

        payload = {"cmd": cmd, **kwargs}
        self.sock.sendall((json.dumps(payload) + "\n").encode("utf-8"))

        line = self._reader.readline()
        if not line:
            raise CameraTcpError("camera service closed connection")

        try:
            response = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CameraTcpError(f"invalid camera response: {line!r}") from exc

        if not response.get("ok", False):
            raise CameraTcpError(response.get("error", "camera request failed"))

        return response

    # Interface expected by pc_controller.py
    def start(self) -> None:
        self.connect()
        self.request("START")
        print(f"[CAM-CLIENT] connected to camera service at {self.config.host}:{self.config.port}")

    def stop(self) -> None:
        if self.sock is not None:
            try:
                self.request("STOP")
            except Exception:
                pass
        self.close()
        print("[CAM-CLIENT] camera connection closed")

    def ready(self) -> bool:
        return bool(self.request("READY").get("ready", False))

    def latest_frame_fresh(self, max_age_sec: float = 1.0) -> bool:
        return bool(self.request("FRESH", max_age_sec=max_age_sec).get("fresh", False))

    @property
    def image_index(self) -> int:
        return int(self.request("STATUS").get("image_index", 0))

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
        response = self.request(
            "SAVE_LATEST",
            mode=mode,
            step_index=step_index,
            x_mm=x_mm,
            y_mm=y_mm,
            plc_event_sequence=plc_event_sequence,
            note=note,
        )
        path = Path(str(response["path"]))
        print(f"[CAM-CLIENT] saved {path}")
        return path
