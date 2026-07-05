# machine_control — Module README

## Responsibility

This module is the **hardware interface layer**. It runs directly on the Industrial PC (IPC) connected to the machine. It is the **only** module that communicates with physical or simulated hardware.

## Files

| File | Responsibility |
|---|---|
| `pc_controller.py` | Central state machine. Orchestrates the entire inspection cycle: PLC handshake → recipe download → step loop → camera trigger → DB write. **1026 lines.** |
| `shared_protocol.py` | SLMP 3E Binary TCP client + all D-register addresses + all EventCode/AckStatus enums. Source of truth for PLC protocol. |
| `camera_tcp.py` | JSON-over-TCP client for camera service. One connection per run. |
| `database_pg.py` | psycopg2 adapter for all machine-side DB writes (runs, run_steps, error_log, external_lookup_log). |
| `recipe.py` | Calculates the XY grid (rows × cols) from PCB dimensions returned by MES. |
| `serialtest_api_client.py` | HTTP client for factory MES API. Supports `fixture` mode (no network) and `real` mode (live HTTPS). |

## Interfaces

**Inbound (what this module receives):**
- PLC events over SLMP/TCP (port 15000)
- Camera responses over JSON/TCP (port 16000)
- MES API responses over HTTPS (configurable endpoint)
- `NOTIFY new_run_sn` from PostgreSQL (via `pc_controller.py` listening on the DB channel)

**Outbound (what this module sends):**
- SLMP commands to PLC D-registers (D100–D109)
- Camera commands: `START`, `SAVE_LATEST`, etc.
- `POST /images/` to FastAPI backend (sends image metadata)
- DB writes via `database_pg.py`: inserts into `runs`, `run_steps`, `error_log`

## Critical Constraints

1. **NEVER refactor `pc_controller.py` to use `asyncio`.** SLMP timing is wall-clock sensitive. Async introduces non-deterministic delays that cause the PLC to halt permanently.
2. **Every PLC event MUST be acknowledged.** Pattern: `recv_event()` → process → `send_ack(seq)`. Missing an ACK stalls the PLC forever. See `shared_protocol.py`.
3. **Never hardcode URLs or credentials.** Use `os.environ.get("FASTAPI_URL")` etc.
4. **`simulation/shared_protocol.py` is a mirror of this file.** If you update event codes or register addresses here, update the simulation copy too.

## Run (with simulators)

```bash
conda activate aoi_env
# Start PLC + camera simulators first (see simulation/README.md)
cd machine_control
python pc_controller.py --mode semi-auto --api-mode fixture
```
