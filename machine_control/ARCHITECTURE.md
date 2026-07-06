# machine_control — Architecture Reference

> Read this when you need to understand **how the protocols work internally**.
> For what this module does, its interfaces, and how to run it, see [`README.md`](README.md).

---

## 1. Tech Stack

| Component | Library / Tool | Notes |
|---|---|---|
| Runtime | CPython 3.10+ | Synchronous / blocking — intentional |
| PLC comms | Raw `socket` (stdlib) | SLMP 3E Binary TCP |
| Camera comms | Raw `socket` (stdlib) | JSON-over-TCP |
| HTTP client (MES) | `urllib.request` (stdlib) | No third-party HTTP lib |
| DB writes | `psycopg2` 2.9.10 | Direct, no ORM |
| Config | `python-dotenv` 1.2.1 | Reads `.env` at startup |
| Logging | `logging.RotatingFileHandler` | Rotates at 10MB |

> **CRITICAL:** `pc_controller.py` is intentionally **synchronous and blocking**.
> SLMP requires strict sequential request/ACK timing. Do NOT refactor to `asyncio`.

---

## 2. PLC Communication Protocol (SLMP)

The PC communicates with the Mitsubishi FX5U PLC using **SLMP 3E Binary TCP**
(Seamless Message Protocol / MC Protocol). All logic lives in `shared_protocol.py`.

### D-Register Mailbox Map

| Register | Direction | Purpose |
|---|---|---|
| D100 | PC → PLC | Event Code (command) |
| D101 | PC → PLC | Sequence Number |
| D102–D109 | PC → PLC | Data payload |
| D200 | PLC → PC | Event Code (notification) |
| D201 | PLC → PC | Sequence Number |
| D202–D209 | PLC → PC | Data payload |

### Event / ACK Lifecycle

```
PC writes EventCode to D100   (e.g., START_RUN = 13)
    │
    ▼
PLC reads D100, processes command
    │
    ▼
PLC writes EventCode to D200  (e.g., RUN_STARTED = 102)
    │
    ▼
PC reads D200, sends ACK to D100  (ACK_OK = 1)
    │
    ▼
PLC reads D100 ACK, clears D200
```

> **CRITICAL:** If the PC does NOT send the matching ACK with the correct sequence
> number, the PLC halts **permanently**. Every `recv_event()` call MUST be followed
> by `send_ack()`. See `shared_protocol.py` for the exact byte format.

### Key Event Codes

| Code | Name | Direction |
|---|---|---|
| 10 | `PC_READY` | PC → PLC |
| 13 | `START_RUN` | PC → PLC |
| 18–20 | `RECIPE_DOWNLOAD_START / STEP_DATA / END` | PC → PLC |
| 50 | `CAPTURE_AUTHORIZED` | PC → PLC |
| 52 | `CAPTURE_DONE` | PC → PLC |
| 100 | `PLC_READY` | PLC → PC |
| 151 | `POSITION_REACHED` | PLC → PC |
| 152 | `CAPTURE_AUTH_REQUEST` | PLC → PC |
| 155 | `STEP_COMPLETE` | PLC → PC |
| 105 | `RUN_COMPLETE` | PLC → PC |

---

## 3. Camera Communication Protocol

The camera service uses **JSON-over-TCP** on port `16000`. Client: `camera_tcp.py`.

```
Request:  {"cmd": "SAVE_LATEST", "mode": "...", "step_index": N, ...}\n
Response: {"ok": true, "path": "/abs/path/to/image.jpg"}\n
```

**Supported commands:** `START`, `STOP`, `READY`, `FRESH`, `SAVE_LATEST`, `STATUS`

In production, the physical camera SDK service (IDS, Basler, etc.) must implement
this same JSON-over-TCP interface. `pc_controller.py` requires **no code changes**
when switching from simulation to real hardware — only CLI arguments change.

---

## 4. MES / Shopfloor API Integration

When a barcode is scanned, `serialtest_api_client.py` calls the factory MES:

```
GET https://<MES_HOST>/api/v1/shopfloor/info?sn=<SERIAL>
```

**Response fields used:**

| Field | Used For |
|---|---|
| `HasData` | `"1"` = board exists in MES |
| `M_NO` | Work order number → links run to `orders` table |
| `SemiModel` | PCB model name stored in run record |
| `PCB_Length`, `PCB_Width` | Input to `recipe.py` for XY grid calculation |

**Modes:**
- `fixture` — built-in static test data, no network (default for simulation)
- `real` — live HTTPS call to factory MES

In simulation, `simulation/shopfloor_sim.py` provides a local mock at `localhost:9090`.

---

## 5. Sync with simulation/

`simulation/shared_protocol.py` is a **separate copy** of `machine_control/shared_protocol.py`.
When updating D-register addresses or EventCodes, **update both files**.
