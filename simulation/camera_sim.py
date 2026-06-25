"""
Standalone simulated camera service.

Run:
    python camera_sim.py --host 127.0.0.1 --port 16000 --capture-dir captures_simulated

The PC controller connects to this service over local TCP. The simulator writes
JSON capture records, but a real camera process can implement the same command
set while saving actual PNG/TIFF images from the IDS camera worker.
"""

from __future__ import annotations

import argparse
import json
import socketserver
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional


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


class CameraState:
    def __init__(self, output_dir: Path):
        self.lock = threading.RLock()
        self.output_dir = output_dir
        self.running = False
        self.image_index = 0
        self.last_frame_time = 0.0

    def start(self) -> dict[str, Any]:
        with self.lock:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.running = True
            self.last_frame_time = time.time()
            return self.status()

    def stop(self) -> dict[str, Any]:
        with self.lock:
            self.running = False
            return self.status()

    def tick_live_frame(self) -> None:
        # Simulates continuous acquisition. A real camera service would update this
        # from the image acquisition thread when new frames arrive.
        if self.running:
            self.last_frame_time = time.time()

    def ready(self) -> bool:
        with self.lock:
            self.tick_live_frame()
            return self.running

    def fresh(self, max_age_sec: float) -> bool:
        with self.lock:
            self.tick_live_frame()
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
    ) -> dict[str, Any]:
        with self.lock:
            self.tick_live_frame()
            if not self.running:
                raise RuntimeError("camera acquisition is not running")
            if (time.time() - self.last_frame_time) > 1.0:
                raise RuntimeError("latest frame is stale")

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
            self.output_dir.mkdir(parents=True, exist_ok=True)
            path = self.output_dir / f"capture_{self.image_index:04d}.json"
            path.write_text(json.dumps(asdict(record), indent=2), encoding="utf-8")
            return {"path": str(path), "image_index": self.image_index}

    def status(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "ready": self.running,
            "image_index": self.image_index,
            "last_frame_time": self.last_frame_time,
            "output_dir": str(self.output_dir),
        }


class CameraRequestHandler(socketserver.StreamRequestHandler):
    camera_state: CameraState

    def handle(self) -> None:
        peer = self.client_address
        print(f"[CAM-SIM] client connected: {peer}")
        while True:
            line = self.rfile.readline()
            if not line:
                print(f"[CAM-SIM] client disconnected: {peer}")
                return

            try:
                request = json.loads(line.decode("utf-8"))
                response = self.dispatch(request)
            except Exception as exc:
                response = {"ok": False, "error": str(exc)}

            self.wfile.write((json.dumps(response) + "\n").encode("utf-8"))
            self.wfile.flush()

    def dispatch(self, request: dict[str, Any]) -> dict[str, Any]:
        cmd = str(request.get("cmd", "")).upper()

        if cmd == "START":
            return {"ok": True, **self.camera_state.start()}

        if cmd == "STOP":
            return {"ok": True, **self.camera_state.stop()}

        if cmd == "READY":
            return {"ok": True, "ready": self.camera_state.ready()}

        if cmd == "FRESH":
            max_age_sec = float(request.get("max_age_sec", 1.0))
            return {"ok": True, "fresh": self.camera_state.fresh(max_age_sec)}

        if cmd == "STATUS":
            return {"ok": True, **self.camera_state.status()}

        if cmd == "SAVE_LATEST":
            result = self.camera_state.save_latest(
                mode=str(request.get("mode", "unknown")),
                step_index=request.get("step_index"),
                x_mm=request.get("x_mm"),
                y_mm=request.get("y_mm"),
                plc_event_sequence=request.get("plc_event_sequence"),
                note=str(request.get("note", "")),
            )
            return {"ok": True, **result}

        raise ValueError(f"unknown camera command: {cmd!r}")


class ThreadedCameraServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


def main() -> None:
    parser = argparse.ArgumentParser(description="Local TCP simulated camera service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=16000)
    parser.add_argument("--capture-dir", default="captures_simulated")
    args = parser.parse_args()

    CameraRequestHandler.camera_state = CameraState(Path(args.capture_dir))
    server = ThreadedCameraServer((args.host, args.port), CameraRequestHandler)

    print(f"[CAM-SIM] listening on {args.host}:{args.port}")
    print(f"[CAM-SIM] capture dir: {args.capture_dir}")
    print("[CAM-SIM] press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[CAM-SIM] stopping")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
