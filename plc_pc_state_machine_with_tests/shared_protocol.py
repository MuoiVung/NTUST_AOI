"""
Shared protocol definitions for the PC <-> PLC event-control prototype.

This module defines:
- Event codes
- ACK status codes
- Error codes
- State/mode enums
- D-register mailbox addresses
- Minimal SLMP 3E binary TCP client for D-register word reads/writes
- Event mailbox helpers used by the PC controller

The simulator implements the matching subset of SLMP 3E binary TCP.
For a real FX5U, configure the PLC Ethernet port for SLMP/MC 3E binary TCP
and point the PC controller at the PLC IP/port.
"""

from __future__ import annotations

import socket
import struct
import time
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Iterable, Optional


class EventCode(IntEnum):
    NONE = 0

    # PC -> PLC common events
    PC_READY = 10
    SET_MODE_MANUAL = 11
    SET_MODE_SEMI_AUTO = 12
    START_RUN = 13
    PAUSE_RUN = 14
    RESUME_RUN = 15
    STOP_RUN = 16
    RESET_ERROR = 17

    # PC -> PLC manual events
    MANUAL_HOME_REQUEST = 30
    MANUAL_MOVE_REQUEST = 31
    MANUAL_JOG_REQUEST = 32
    MANUAL_CAPTURE_DONE = 33

    # PC -> PLC semi-auto capture events
    CAPTURE_AUTHORIZED = 50
    CAPTURE_REJECTED = 51
    CAPTURE_DONE = 52

    # PC -> PLC heartbeat
    PC_HEARTBEAT = 90

    # PLC -> PC common events
    PLC_READY = 100
    MODE_CHANGED = 101
    RUN_STARTED = 102
    RUN_PAUSED = 103
    RUN_STOPPED = 104
    RUN_COMPLETE = 105

    # PLC -> PC manual responses
    MANUAL_COMMAND_STARTED = 130
    MANUAL_COMMAND_DONE = 131
    MANUAL_COMMAND_ERROR = 132

    # PLC -> PC semi-auto responses
    SEMI_AUTO_STEP_STARTED = 150
    POSITION_REACHED = 151
    CAPTURE_AUTH_REQUEST = 152
    CAPTURE_WINDOW_OPEN = 153
    CAPTURE_WINDOW_CLOSED = 154
    STEP_COMPLETE = 155

    # PLC -> PC errors
    PLC_ERROR = 900
    MOTION_ERROR = 901
    SAFETY_ERROR = 902
    CAPTURE_TIMEOUT = 903
    COMMUNICATION_TIMEOUT = 904


class AckStatus(IntEnum):
    OK = 0
    REJECTED = 1
    BUSY = 2
    INVALID_STATE = 3
    INVALID_PAYLOAD = 4
    SAFETY_NOT_OK = 5
    TIMEOUT = 6
    DUPLICATE_SEQUENCE = 7
    UNKNOWN_EVENT = 8


class ErrorCode(IntEnum):
    ERR_NONE = 0

    # PC / software
    ERR_PC_NOT_READY = 1001
    ERR_PC_INVALID_MODE = 1002
    ERR_PC_INTERNAL_EXCEPTION = 1003
    ERR_PC_CONFIG_MISSING = 1004
    ERR_PC_CONFIG_INVALID = 1005
    ERR_PC_OPERATOR_ABORT = 1006
    ERR_PC_PAUSED = 1007
    ERR_PC_SEQUENCE_MISMATCH = 1008
    ERR_PC_METADATA_MISSING = 1009
    ERR_PC_MODE_SWITCH_NOT_ALLOWED = 1010

    # PLC / state machine
    ERR_PLC_NOT_READY = 2001
    ERR_PLC_INVALID_STATE = 2002
    ERR_PLC_BUSY = 2003
    ERR_PLC_UNKNOWN_EVENT = 2004
    ERR_PLC_INVALID_PAYLOAD = 2005
    ERR_PLC_SEQUENCE_DUPLICATE = 2006
    ERR_PLC_SEQUENCE_SKIPPED = 2007
    ERR_PLC_MODE_NOT_SELECTED = 2008
    ERR_PLC_MANUAL_ONLY_EVENT = 2009
    ERR_PLC_SEMIAUTO_ONLY_EVENT = 2010
    ERR_PLC_RESET_NOT_ALLOWED = 2011
    ERR_PLC_RECIPE_NOT_LOADED = 2012
    ERR_PLC_STEP_INDEX_INVALID = 2013

    # Communication
    ERR_COMM_CONNECT_FAILED = 3001
    ERR_COMM_SOCKET_CLOSED = 3002
    ERR_COMM_TIMEOUT = 3003
    ERR_COMM_BAD_RESPONSE = 3004
    ERR_COMM_SLMP_END_CODE = 3005
    ERR_COMM_WRITE_FAILED = 3006
    ERR_COMM_READ_FAILED = 3007
    ERR_COMM_ACK_TIMEOUT = 3008
    ERR_COMM_PLC_EVENT_TIMEOUT = 3009
    ERR_COMM_PC_ACK_TIMEOUT = 3010
    ERR_COMM_HEARTBEAT_LOST = 3011
    ERR_COMM_WRONG_PORT = 3012
    ERR_COMM_WRONG_IP = 3013
    ERR_COMM_FIREWALL_BLOCKED = 3014
    ERR_COMM_FRAME_MODE_MISMATCH = 3015

    # Camera
    ERR_CAMERA_NOT_DETECTED = 4001
    ERR_CAMERA_OPEN_FAILED = 4002
    ERR_CAMERA_ALREADY_IN_USE = 4003
    ERR_CAMERA_SETTINGS_MISSING = 4004
    ERR_CAMERA_SETTINGS_LOAD_FAILED = 4005
    ERR_CAMERA_PIPELINE_MISSING = 4006
    ERR_CAMERA_PIPELINE_LOAD_FAILED = 4007
    ERR_CAMERA_ACQUISITION_NOT_RUNNING = 4008
    ERR_CAMERA_FRAME_TIMEOUT = 4009
    ERR_CAMERA_FRAME_INCOMPLETE = 4010
    ERR_CAMERA_STALE_FRAME = 4011
    ERR_CAMERA_PROCESSING_FAILED = 4012
    ERR_CAMERA_BRIGHTNESS_UNSTABLE = 4013
    ERR_CAMERA_FOCUS_BAD = 4014
    ERR_CAMERA_LIGHTING_BAD = 4015

    # Storage
    ERR_STORAGE_PATH_MISSING = 5001
    ERR_STORAGE_PATH_INVALID = 5002
    ERR_STORAGE_PERMISSION_DENIED = 5003
    ERR_STORAGE_DISK_FULL = 5004
    ERR_STORAGE_FILENAME_INVALID = 5005
    ERR_IMAGE_SAVE_FAILED = 5006
    ERR_IMAGE_VERIFY_FAILED = 5007
    ERR_IMAGE_INDEX_DUPLICATE = 5008
    ERR_LOG_CREATE_FAILED = 5009
    ERR_LOG_WRITE_FAILED = 5010

    # Motion
    ERR_MOTION_NOT_HOMED = 6001
    ERR_MOTION_HOME_FAILED = 6002
    ERR_MOTION_TARGET_OUT_OF_RANGE = 6003
    ERR_MOTION_AXIS_BUSY = 6004
    ERR_MOTION_START_FAILED = 6005
    ERR_MOTION_TIMEOUT = 6006
    ERR_MOTION_POSITION_NOT_REACHED = 6007
    ERR_MOTION_POSITION_MISMATCH = 6008
    ERR_MOTION_DRIVE_ALARM = 6009
    ERR_MOTION_LIMIT_SWITCH = 6010
    ERR_MOTION_ENCODER_ERROR = 6011
    ERR_MOTION_COLLISION_RISK = 6012
    ERR_MOTION_STEP_MISMATCH = 6013

    # Safety
    ERR_SAFETY_ESTOP_ACTIVE = 7001
    ERR_SAFETY_GUARD_OPEN = 7002
    ERR_SAFETY_INTERLOCK_OPEN = 7003
    ERR_SAFETY_LIGHT_CURTAIN = 7004
    ERR_SAFETY_AIR_PRESSURE_LOW = 7005
    ERR_SAFETY_SERVO_NOT_READY = 7006
    ERR_SAFETY_MACHINE_AREA_NOT_CLEAR = 7007
    ERR_SAFETY_RESET_REQUIRED = 7008
    ERR_SAFETY_OPERATION_NOT_ALLOWED = 7009
    ERR_SAFETY_UNKNOWN = 7010

    # Operator / workflow
    ERR_OPERATOR_BOARD_NAME_MISSING = 8001
    ERR_OPERATOR_SIDE_MISSING = 8002
    ERR_OPERATOR_INVALID_MODE_SELECTION = 8003
    ERR_OPERATOR_START_NOT_ALLOWED = 8004
    ERR_OPERATOR_PAUSE_ACTIVE = 8005
    ERR_OPERATOR_CAPTURE_REJECTED = 8006
    ERR_OPERATOR_CONFIRMATION_REQUIRED = 8007
    ERR_OPERATOR_WRONG_SAMPLE = 8008
    ERR_OPERATOR_RUN_ABORTED = 8009
    ERR_OPERATOR_RESET_DENIED = 8010

    # Unknown / fatal
    ERR_UNKNOWN = 9000
    ERR_FATAL_SYSTEM = 9001
    ERR_FATAL_PLC = 9002
    ERR_FATAL_PC = 9003
    ERR_FATAL_CAMERA = 9004
    ERR_FATAL_MOTION = 9005
    ERR_RESERVED_UNHANDLED = 9999


class ModeCode(IntEnum):
    NONE = 0
    MANUAL = 1
    SEMI_AUTO = 2


class PcState(str, Enum):
    STARTUP = "PC_STARTUP"
    INIT_CAMERA = "PC_INIT_CAMERA"
    CONNECT_PLC = "PC_CONNECT_PLC"
    WAIT_PLC_READY = "PC_WAIT_PLC_READY"
    IDLE = "PC_IDLE"

    MANUAL_SELECT = "PC_MANUAL_SELECT"
    MANUAL_IDLE = "PC_MANUAL_IDLE"
    MANUAL_SEND_COMMAND = "PC_MANUAL_SEND_COMMAND"
    MANUAL_WAIT_STARTED = "PC_MANUAL_WAIT_STARTED"
    MANUAL_WAIT_RESULT = "PC_MANUAL_WAIT_RESULT"
    MANUAL_CAPTURE = "PC_MANUAL_CAPTURE"
    MANUAL_REPORT_CAPTURE_DONE = "PC_MANUAL_REPORT_CAPTURE_DONE"

    SEMI_SELECT = "PC_SEMI_SELECT"
    SEMI_START_RUN = "PC_SEMI_START_RUN"
    SEMI_MONITOR_RUN = "PC_SEMI_MONITOR_RUN"
    SEMI_CHECK_CAPTURE_READY = "PC_SEMI_CHECK_CAPTURE_READY"
    SEMI_AUTHORIZE_CAPTURE = "PC_SEMI_AUTHORIZE_CAPTURE"
    SEMI_WAIT_CAPTURE_WINDOW = "PC_SEMI_WAIT_CAPTURE_WINDOW"
    SEMI_CAPTURE_IMAGE = "PC_SEMI_CAPTURE_IMAGE"
    SEMI_REPORT_CAPTURE_DONE = "PC_SEMI_REPORT_CAPTURE_DONE"

    ERROR = "PC_ERROR"
    SHUTDOWN = "PC_SHUTDOWN"


class PlcState(str, Enum):
    BOOT = "PLC_BOOT"
    WAIT_PC_READY = "PLC_WAIT_PC_READY"
    IDLE = "PLC_IDLE"

    MANUAL_IDLE = "PLC_MANUAL_IDLE"
    MANUAL_VALIDATE_COMMAND = "PLC_MANUAL_VALIDATE_COMMAND"
    MANUAL_START_COMMAND = "PLC_MANUAL_START_COMMAND"
    MANUAL_EXECUTING = "PLC_MANUAL_EXECUTING"
    MANUAL_DONE = "PLC_MANUAL_DONE"

    SEMI_IDLE = "PLC_SEMI_IDLE"
    SEMI_LOAD_NEXT_STEP = "PLC_SEMI_LOAD_NEXT_STEP"
    SEMI_MOVE_TO_POSITION = "PLC_SEMI_MOVE_TO_POSITION"
    SEMI_POSITION_REACHED = "PLC_SEMI_POSITION_REACHED"
    SEMI_WAIT_CAPTURE_AUTH = "PLC_SEMI_WAIT_CAPTURE_AUTH"
    SEMI_OPEN_CAPTURE_WINDOW = "PLC_SEMI_OPEN_CAPTURE_WINDOW"
    SEMI_WAIT_CAPTURE_DONE = "PLC_SEMI_WAIT_CAPTURE_DONE"
    SEMI_CLOSE_CAPTURE_WINDOW = "PLC_SEMI_CLOSE_CAPTURE_WINDOW"
    SEMI_STEP_COMPLETE = "PLC_SEMI_STEP_COMPLETE"
    SEMI_RUN_COMPLETE = "PLC_SEMI_RUN_COMPLETE"

    ERROR = "PLC_ERROR"


@dataclass(frozen=True)
class PlcEvent:
    event_type: int
    sequence: int
    payload: list[int]

    @property
    def name(self) -> str:
        return event_name(self.event_type)


class PlcProtocolError(RuntimeError):
    pass


class PlcAckError(RuntimeError):
    def __init__(self, sequence: int, status: int):
        self.sequence = sequence
        self.status = status
        super().__init__(f"PLC rejected sequence {sequence}: {ack_name(status)}")


# Mailbox layout. D-registers only for the prototype.
PC_EVENT_BASE = 100       # D100-D109
PLC_ACK_BASE = 110        # D110-D111
PLC_EVENT_BASE = 200      # D200-D209
PC_ACK_BASE = 210         # D210-D211
PAYLOAD_WORDS = 8
EVENT_WORDS = 2 + PAYLOAD_WORDS


def event_name(code: int) -> str:
    try:
        return EventCode(code).name
    except ValueError:
        return f"UNKNOWN_EVENT_{code}"


def ack_name(code: int) -> str:
    try:
        return AckStatus(code).name
    except ValueError:
        return f"UNKNOWN_ACK_{code}"


def error_name(code: int) -> str:
    try:
        return ErrorCode(code).name
    except ValueError:
        return f"UNKNOWN_ERROR_{code}"


def signed32_to_words(value: int) -> list[int]:
    value &= 0xFFFFFFFF
    return [value & 0xFFFF, (value >> 16) & 0xFFFF]


def words_to_signed32(low: int, high: int) -> int:
    value = ((high & 0xFFFF) << 16) | (low & 0xFFFF)
    if value & 0x80000000:
        value -= 0x100000000
    return value


def encode_xy_mm(x_mm: float, y_mm: float, scale: int = 1000) -> list[int]:
    return signed32_to_words(round(x_mm * scale)) + signed32_to_words(round(y_mm * scale))


def decode_xy_mm(payload: list[int], scale: int = 1000) -> tuple[float, float]:
    if len(payload) < 4:
        raise ValueError("XY payload requires four words")
    x_counts = words_to_signed32(payload[0], payload[1])
    y_counts = words_to_signed32(payload[2], payload[3])
    return x_counts / scale, y_counts / scale


def pad_payload(payload: Optional[Iterable[int]], size: int = PAYLOAD_WORDS) -> list[int]:
    values = [int(v) & 0xFFFF for v in (payload or [])]
    return (values + [0] * size)[:size]


# ---------------------------------------------------------------------------
# Minimal SLMP 3E binary D-register client
# ---------------------------------------------------------------------------

DEVICE_CODES = {"D": 0xA8}


@dataclass
class SlmpConfig:
    host: str = "127.0.0.1"
    port: int = 15000
    timeout_sec: float = 3.0


class Slmp3eClient:
    """Minimal SLMP 3E binary TCP client for D-register word read/write."""

    def __init__(self, config: SlmpConfig):
        self.config = config
        self.sock: Optional[socket.socket] = None

    def connect(self) -> None:
        self.sock = socket.create_connection(
            (self.config.host, self.config.port),
            timeout=self.config.timeout_sec,
        )
        self.sock.settimeout(self.config.timeout_sec)

    def close(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            finally:
                self.sock = None

    def _recv_exact(self, count: int) -> bytes:
        if self.sock is None:
            raise PlcProtocolError("SLMP client is not connected")
        chunks: list[bytes] = []
        remaining = count
        while remaining > 0:
            chunk = self.sock.recv(remaining)
            if not chunk:
                raise PlcProtocolError("Socket closed while reading SLMP response")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def _send_request(self, command: int, subcommand: int, payload: bytes) -> bytes:
        if self.sock is None:
            raise PlcProtocolError("SLMP client is not connected")

        monitoring_timer = 0x0010
        request_data = (
            struct.pack("<H", monitoring_timer)
            + struct.pack("<H", command)
            + struct.pack("<H", subcommand)
            + payload
        )
        header = (
            b"\x50\x00"      # 3E binary request subheader
            + b"\x00"         # network number
            + b"\xFF"         # PLC number
            + b"\xFF\x03"     # module I/O number
            + b"\x00"         # station number
            + struct.pack("<H", len(request_data))
        )
        self.sock.sendall(header + request_data)

        response_header = self._recv_exact(9)
        if response_header[:2] != b"\xD0\x00":
            raise PlcProtocolError(f"Unexpected response header: {response_header.hex(' ')}")
        data_length = struct.unpack("<H", response_header[7:9])[0]
        response_data = self._recv_exact(data_length)
        if len(response_data) < 2:
            raise PlcProtocolError("SLMP response missing end code")
        end_code = struct.unpack("<H", response_data[:2])[0]
        if end_code != 0:
            raise PlcProtocolError(f"SLMP nonzero end code 0x{end_code:04X}")
        return response_data[2:]

    @staticmethod
    def _parse_device(device: str) -> tuple[str, int]:
        device = device.strip().upper()
        if not device:
            raise ValueError("Empty device address")
        prefix = device[0]
        if prefix not in DEVICE_CODES:
            raise ValueError("This prototype supports only D registers")
        return prefix, int(device[1:])

    def read_words(self, head_device: str, count: int) -> list[int]:
        prefix, number = self._parse_device(head_device)
        device_code = DEVICE_CODES[prefix]
        payload = (
            number.to_bytes(3, "little", signed=False)
            + bytes([device_code])
            + struct.pack("<H", count)
        )
        data = self._send_request(command=0x0401, subcommand=0x0000, payload=payload)
        expected = count * 2
        if len(data) < expected:
            raise PlcProtocolError("SLMP read response too short")
        return list(struct.unpack("<" + "H" * count, data[:expected]))

    def write_words(self, head_device: str, values: Iterable[int]) -> None:
        values_list = [int(v) & 0xFFFF for v in values]
        if not values_list:
            raise ValueError("write_words requires at least one value")
        prefix, number = self._parse_device(head_device)
        device_code = DEVICE_CODES[prefix]
        data = struct.pack("<" + "H" * len(values_list), *values_list)
        payload = (
            number.to_bytes(3, "little", signed=False)
            + bytes([device_code])
            + struct.pack("<H", len(values_list))
            + data
        )
        self._send_request(command=0x1401, subcommand=0x0000, payload=payload)


class PcEventMailbox:
    """PC-side helper for publishing PC events and receiving PLC events."""

    def __init__(self, client: Slmp3eClient):
        self.client = client
        self.pc_sequence = 0
        self.last_plc_sequence_seen = 0

    def next_sequence(self) -> int:
        self.pc_sequence += 1
        if self.pc_sequence > 32767:
            self.pc_sequence = 1
        return self.pc_sequence

    def publish_pc_event(
        self,
        event_type: EventCode | int,
        payload: Optional[Iterable[int]] = None,
        timeout_sec: float = 3.0,
    ) -> int:
        sequence = self.next_sequence()
        words = [int(event_type), sequence] + pad_payload(payload)
        self.client.write_words(f"D{PC_EVENT_BASE}", words)
        self.wait_for_plc_ack(sequence, timeout_sec=timeout_sec)
        return sequence

    def wait_for_plc_ack(self, sequence: int, timeout_sec: float) -> None:
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            ack_seq, ack_status = self.client.read_words(f"D{PLC_ACK_BASE}", 2)
            if ack_seq == sequence:
                if ack_status == int(AckStatus.OK):
                    return
                raise PlcAckError(sequence, ack_status)
            time.sleep(0.02)
        raise TimeoutError(f"Timeout waiting for PLC ACK for sequence {sequence}")

    def poll_plc_event(self) -> Optional[PlcEvent]:
        words = self.client.read_words(f"D{PLC_EVENT_BASE}", EVENT_WORDS)
        event_type = words[0]
        sequence = words[1]
        payload = words[2:]
        if event_type == int(EventCode.NONE) or sequence == 0:
            return None
        if sequence == self.last_plc_sequence_seen:
            return None
        return PlcEvent(event_type=event_type, sequence=sequence, payload=payload)

    def wait_for_plc_event(
        self,
        expected: EventCode | int | None = None,
        timeout_sec: float = 10.0,
    ) -> PlcEvent:
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            event = self.poll_plc_event()
            if event is not None:
                if expected is None or event.event_type == int(expected):
                    return event
                # Return unexpected events to the state machine so it can decide.
                return event
            time.sleep(0.02)
        expected_text = "ANY" if expected is None else event_name(int(expected))
        raise TimeoutError(f"Timeout waiting for PLC event {expected_text}")

    def acknowledge_plc_event(self, event: PlcEvent, status: AckStatus | int = AckStatus.OK) -> None:
        self.client.write_words(f"D{PC_ACK_BASE}", [event.sequence, int(status)])
        self.last_plc_sequence_seen = event.sequence
