"""
SerialTest API client and fixture simulator.

The real API described in the guide is an HTTPS GET endpoint that accepts a
single `sn` parameter and returns JSON with HasData, Msg, board identity, and
PCB dimensions. The simulator uses fixture data by default so tests do not need
external network access.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


DEFAULT_ENDPOINT = (
    "https://tracking.aaeon.com.tw/ashx/WebAPI/Board/SerialTest/"
    "HandlerGetSerialInfo.ashx"
)


class SerialTestApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class SerialLookupResult:
    serial_number_query: str
    has_data: str
    msg: str
    sn: str = ""
    m_no: str = ""
    p_no: str = ""
    semi_model: str = ""
    pcb_length_mm: Optional[float] = None
    pcb_width_mm: Optional[float] = None
    raw_response: dict[str, Any] | None = None
    http_status_code: Optional[int] = None
    api_endpoint: str = DEFAULT_ENDPOINT

    @property
    def ok(self) -> bool:
        return self.has_data == "1"


DEFAULT_FIXTURE: dict[str, dict[str, Any]] = {
    "C26602074": {
        "SN": "C26602074",
        "M_NO": "MO-DEMO-001",
        "P_NO": "PO-DEMO-001",
        "SemiModel": "DUO-AOI-DEMO-BOARD",
        "PCB_Length": "84",
        "PCB_Width": "55",
        "HasData": "1",
        "Msg": "",
    },
    "BOARD_A_V2": {
        "SN": "BOARD_A_V2",
        "M_NO": "MO-DEMO-002",
        "P_NO": "PO-DEMO-002",
        "SemiModel": "DEMO-BOARD-A",
        "PCB_Length": "120",
        "PCB_Width": "80",
        "HasData": "1",
        "Msg": "",
    },
}


def _parse_float(value: Any) -> Optional[float]:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise SerialTestApiError(f"Invalid numeric API field: {value!r}") from exc


class SerialTestApiClient:
    def __init__(
        self,
        endpoint: str = DEFAULT_ENDPOINT,
        mode: str = "fixture",
        fixture_path: str | Path | None = None,
        timeout_sec: float = 5.0,
    ):
        self.endpoint = endpoint
        self.mode = mode
        self.timeout_sec = timeout_sec
        self.fixture = dict(DEFAULT_FIXTURE)
        if fixture_path:
            data = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
            self.fixture.update(data)

    def lookup(self, serial_number: str) -> SerialLookupResult:
        serial_number = serial_number.strip()
        if not serial_number:
            raise SerialTestApiError("Serial number is required")
        if self.mode == "fixture":
            raw = self.fixture.get(
                serial_number,
                {
                    "SN": "",
                    "PCB_Length": "",
                    "PCB_Width": "",
                    "HasData": "0",
                    "Msg": "查無此序號資料",
                },
            )
            return self._result_from_raw(serial_number, raw, http_status_code=200)
        if self.mode == "real":
            query = urllib.parse.urlencode({"sn": serial_number})
            url = f"{self.endpoint}?{query}"
            try:
                with urllib.request.urlopen(url, timeout=self.timeout_sec) as response:
                    status = int(response.status)
                    payload = response.read().decode("utf-8")
                raw = json.loads(payload)
            except Exception as exc:
                raise SerialTestApiError(f"SerialTest API request failed: {exc}") from exc
            return self._result_from_raw(serial_number, raw, http_status_code=status)
        raise ValueError(f"Unsupported SerialTest API mode: {self.mode}")

    def _result_from_raw(
        self,
        serial_number_query: str,
        raw: dict[str, Any],
        http_status_code: Optional[int],
    ) -> SerialLookupResult:
        has_data = str(raw.get("HasData", "0"))
        return SerialLookupResult(
            serial_number_query=serial_number_query,
            has_data=has_data,
            msg=str(raw.get("Msg", "")),
            sn=str(raw.get("SN", "")),
            m_no=str(raw.get("M_NO", "")),
            p_no=str(raw.get("P_NO", "")),
            semi_model=str(raw.get("SemiModel", "")),
            pcb_length_mm=_parse_float(raw.get("PCB_Length")) if has_data == "1" else None,
            pcb_width_mm=_parse_float(raw.get("PCB_Width")) if has_data == "1" else None,
            raw_response=raw,
            http_status_code=http_status_code,
            api_endpoint=self.endpoint,
        )
