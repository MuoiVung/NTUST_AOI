# NTUST AOI System — Architecture Reference

> **Purpose:** This document is the single authoritative reference for the entire repository's architecture. AI agents and new engineers should read this document first before modifying any code. It contains the tech stack, module responsibilities, data flows, database schema, inter-process protocols, and key constraints.

---

## 1. System Overview

The **NTUST AOI (Automated Optical Inspection)** system is a full-stack industrial application for PCB quality inspection on a factory floor. It integrates physical hardware (Mitsubishi FX5U PLC, dual-camera array) with a modern software stack (FastAPI, PostgreSQL, React).

**High-level topology (development mode):**

```
+----------------------------------------------------------------------------------+
|  Factory Network (LAN)                                                           |
|                                                                                  |
|  +------------------+    SLMP/TCP      +----------+                             |
|  |  PC Controller   |<---------------->| PLC FX5U |                             |
|  |  (pc_controller) |                  | Port 15000                             |
|  |                  |  JSON/TCP        +----------+                             |
|  |                  |<---------------->|  Camera  |                             |
|  |                  |                  | Port 16000                             |
|  |                  |                  +----------+                             |
|  |     POST /images/                                                            |
|  |          |                                                                   |
|  v          v                                                                   |
|  +--------------------+                                                         |
|  |  FastAPI Backend   |<------ WebSocket ------> React UI (Port 3001)          |
|  |  (Port 8000)       |                                                         |
|  |  PostgreSQL Pool   |                                                         |
|  +--------+-----------+                                                         |
|           | psycopg2                                                            |
|  +--------v-----------+     MinIO/NAS (external, Port 9000)                    |
|  |  PostgreSQL DB     |                                                         |
|  |  (Port 5433)       |                                                         |
|  +--------------------+                                                         |
+----------------------------------------------------------------------------------+
```

---

## 2. Repository Structure

```
NTUST_AOI/
├── Makefile                     # Unified command interface (start, stop, test, check-*)
├── PROGRESS.md                  # What's done, what's pending, changelog
├── ARCHITECTURE.md              # This document — full technical reference
├── headless_runner.py           # CLI process manager (dev/CI)
├── launcher.py                  # PySide6 desktop process manager (dev GUI)
├── test_sn5434.py               # End-to-end integration test
│
├── machine_control/             # [MODULE 1] Hardware Interface Layer
│   ├── README.md                # Module responsibilities, interfaces, constraints
│   ├── pc_controller.py         # Central state machine & orchestrator (1026 lines)
│   ├── shared_protocol.py       # SLMP event codes, D-register map, TCP client (568 lines)
│   ├── camera_tcp.py            # TCP client for camera service (JSON protocol)
│   ├── database_pg.py           # PostgreSQL adapter for machine-side writes
│   ├── recipe.py                # XY grid recipe generation from PCB dimensions
│   └── serialtest_api_client.py # HTTP client for factory MES/SerialTest API
│
├── ntust_aoi_pcb_db/            # [MODULE 2] Backend API & Database Layer
│   ├── README.md                # Module responsibilities, interfaces, constraints
│   ├── api/
│   │   └── main.py              # FastAPI application (732 lines)
│   ├── sql/
│   │   └── init.sql             # PostgreSQL schema + triggers (source of truth)
│   ├── scripts/
│   │   ├── sync_to_server.py    # Push images to MinIO/NAS
│   │   ├── reset_db.py          # Dev utility: truncate all tables
│   │   └── generate_mock_data.py
│   ├── docker-compose.yml       # PostgreSQL + pgAdmin + Nginx containers
│   ├── requirements.txt         # Python backend dependencies
│   └── .env                     # Runtime environment variables
│
├── NTUST-AOI-UI/                # [MODULE 3] Operator Dashboard (React)
│   ├── README.md                # Module responsibilities, interfaces, constraints
│   ├── App.tsx                  # Main router & layout
│   ├── types.ts                 # Shared TypeScript interfaces
│   ├── components/
│   │   ├── OperatorDashboard.tsx  # Main HMI panel (30KB — largest component)
│   │   ├── ImageViewer.tsx      # Real-time WebSocket image stream
│   │   ├── RunList.tsx          # Paginated inspection run history
│   │   ├── RunGallery.tsx       # Image grid for a single run
│   │   ├── Dashboard.tsx        # Metrics and charts overview
│   │   ├── NewInspection.tsx    # Start inspection form
│   │   ├── EditRun.tsx          # Edit/annotate a run
│   │   └── Settings.tsx         # System configuration UI
│   ├── services/                # API call helpers (fetch wrappers)
│   ├── utils/                   # Shared utility functions
│   └── package.json
│
├── simulation/                  # [MODULE 4] Hardware Simulators (dev/test only)
│   ├── README.md                # Module responsibilities, switch-to-hardware guide
│   ├── plc_sim.py               # Fake Mitsubishi FX5U PLC (SLMP TCP, Port 15000)
│   ├── camera_sim.py            # Fake camera service (JSON TCP, Port 16000)
│   ├── shopfloor_sim.py         # Fake factory MES REST API (Port 9090)
│   └── shared_protocol.py       # Mirror of machine_control/shared_protocol.py
│
├── docs/
│   ├── deployment/
│   │   ├── PRODUCTION_DEPLOYMENT_ARCHITECTURE.md  # Target production build plan
│   │   └── REAL_HARDWARE_INTEGRATION.md           # Real PLC/camera setup guide
│   └── reference/
│       ├── DATABASE_SCHEMA.md           # Full PostgreSQL schema reference
│       └── WORKFLOWS.md                 # Operational state sequence diagrams
│
└── .agents/
    └── AGENTS.md               # AI agent landing page (what/how-to-run/how-to-verify)
```

---

## 3. Tech Stack

### 3.1 Machine Control (Python — Synchronous/Blocking)

| Component | Library / Tool | Version |
|---|---|---|
| Runtime | CPython | 3.10+ |
| PLC comms | Raw TCP socket (`socket`) | stdlib |
| Camera comms | Raw TCP socket (`socket`) | stdlib |
| HTTP client (MES) | `urllib.request` | stdlib |
| DB writes | `psycopg2` | 2.9.10 |
| Config loading | `python-dotenv` | 1.2.1 |
| Logging | `logging.handlers.RotatingFileHandler` | stdlib |
| CLI args | `argparse` | stdlib |

> **CRITICAL:** `pc_controller.py` is intentionally synchronous and blocking. Do NOT refactor it to `asyncio`. The SLMP protocol requires strict sequential request/ACK timing. Introducing async delays will cause the PLC to halt indefinitely.

### 3.2 Backend API (Python — Asynchronous)

| Component | Library / Tool | Version |
|---|---|---|
| Web framework | FastAPI | >= 0.111.0 |
| ASGI server | Uvicorn | >= 0.30.0 |
| Data validation | Pydantic | >= 2.7.0 |
| DB driver | psycopg2-binary | 2.9.10 |
| DB pool | `psycopg2.pool.SimpleConnectionPool` | — |
| PG NOTIFY bridge | `select.select()` + `psycopg2` | — |
| WebSocket | FastAPI native (`WebSocket`) | — |
| Object storage | `minio` | 7.2.5 |
| Config | `python-dotenv` | 1.2.1 |

### 3.3 Database

| Component | Value |
|---|---|
| Engine | PostgreSQL 18 (via Docker in dev) |
| DB name | `pcb_aoi_db` |
| Host (dev) | `127.0.0.1:5433` |
| Schema init | `ntust_aoi_pcb_db/sql/init.sql` |
| DB admin UI | pgAdmin 4 at `localhost:5050` |
| Image HTTP server | Nginx at `localhost:8080` |

### 3.4 Frontend (React)

| Component | Library / Tool | Version |
|---|---|---|
| Framework | React | 19.x |
| Build tool | Vite | 6.x |
| Language | TypeScript | ~5.8 |
| Charts | Recharts | 3.x |
| HTTP calls | Native `fetch` (in `services/`) | — |
| Real-time | Native `WebSocket` | — |
| Dev server | `localhost:3001` | — |

### 3.5 Infrastructure (Dev Mode)

| Component | Tool |
|---|---|
| DB container | Docker Compose (postgres:18) |
| Image server | Docker Compose (nginx:alpine) |
| DB admin | Docker Compose (pgAdmin4) |
| Object storage | MinIO (external server at `192.168.40.21:9000`) |
| Python environment | Conda (`aoi_env`, Python 3.10+) |

---

## 4. Database Schema

All tables live in the `pcb_aoi_db` PostgreSQL database. Schema is initialized from `ntust_aoi_pcb_db/sql/init.sql`.

```
orders                           # Manufacturing work orders
  m_no (PK)                      # Work order number
  target_quantity                # Planned board count
  actual_quantity                # Auto-incremented by trigger on run COMPLETED
  status                         # ACTIVE / CLOSED

runs                             # One per PCB scan session
  run_number (PK)                # Unique run ID
  serial_number                  # Scanned barcode / PCB serial
  semi_model                     # PCB model (from MES)
  m_no (FK -> orders)
  machine_id                     # hostname of the IPC
  status                         # COMPLETED / IN_PROGRESS / ERROR
  is_latest                      # True only for the most recent run per S/N

run_steps                        # One row per XY grid position within a run
  step_id (PK)
  run_number (FK -> runs)
  step_index, row_idx, col_idx
  target_x_mm, target_y_mm       # Planned coordinates sent to PLC
  actual_x_mm, actual_y_mm       # Actual position reported by PLC
  status                         # PENDING / COMPLETED / ERROR
  timestamps: started_at, position_reached_at, capture_auth_at,
              capture_window_at, capture_done_at, completed_at

images                           # One row per captured image file
  image_id (UUID PK)
  run_number (FK -> runs)
  side                           # "Top" or "Bottom"
  local_path                     # Absolute path on the IPC disk
  longterm_path                  # Key in MinIO/NAS after sync
  is_uploaded_longterm           # Upload status flag
  row_idx, col_idx               # Grid position
  condition                      # PASS / FAIL (set by external AI server)
  file_size_bytes, capture_time

error_log                        # Machine and software errors
  error_id (PK)
  run_number (FK), step_id (FK)
  error_code, error_symbol, error_category
  source                         # e.g. "pc_controller", "plc"
  recovery_action, resolved, details_json (JSONB)

external_lookup_log              # Audit trail of MES/Shopfloor API calls
  lookup_id (PK)
  serial_number_query
  http_status_code, raw_response_json (JSONB)
  pcb_length_mm, pcb_width_mm    # Dimensions returned by MES

system_configs                   # Key-value store for runtime parameters
  config_name (UNIQUE), config_value, unit
```

**PostgreSQL Trigger:**
`increment_order_quantity` fires `AFTER INSERT OR UPDATE ON runs`. When `status = 'COMPLETED'` and `is_latest = TRUE`, it increments `orders.actual_quantity` by 1.

**PostgreSQL NOTIFY (Real-time push):**
`api/main.py` runs a background task that listens on channel `ui_update` via `LISTEN ui_update`. A trigger fires `NOTIFY ui_update '<json>'` when a new image row is inserted. The FastAPI task picks this up and broadcasts it to all connected WebSocket clients — this is the real-time image push mechanism.

---

## 5. PLC Communication Protocol (SLMP)

The PC communicates with the Mitsubishi FX5U PLC using **SLMP 3E Binary TCP** (Seamless Message Protocol / MC Protocol). All logic lives in `machine_control/shared_protocol.py`.

### D-Register Mailbox Map

| Register | Direction | Purpose |
|---|---|---|
| D100 | PC -> PLC | Event Code (PC-to-PLC command) |
| D101 | PC -> PLC | Sequence Number |
| D102–D109 | PC -> PLC | Data payload |
| D200 | PLC -> PC | Event Code (PLC-to-PC notification) |
| D201 | PLC -> PC | Sequence Number |
| D202–D209 | PLC -> PC | Data payload |

### Event/ACK Lifecycle

```
PC writes EventCode to D100          (e.g., START_RUN = 13)
    |
    v
PLC reads D100, processes command
    |
    v
PLC writes EventCode to D200         (e.g., RUN_STARTED = 102)
    |
    v
PC reads D200, sends ACK to D100     (ACK_OK = 1)
    |
    v
PLC reads D100 ACK, clears D200
```

> **CRITICAL:** If the PC reads a PLC event and does NOT write the matching ACK back with the correct sequence number, the PLC halts forever. Every `recv_event()` call MUST be followed by `send_ack()`. See `shared_protocol.py` for byte format details.

### Key Event Codes

| Code | Name | Direction |
|---|---|---|
| 10 | `PC_READY` | PC -> PLC |
| 13 | `START_RUN` | PC -> PLC |
| 18–20 | `RECIPE_DOWNLOAD_START/STEP_DATA/END` | PC -> PLC |
| 50 | `CAPTURE_AUTHORIZED` | PC -> PLC |
| 52 | `CAPTURE_DONE` | PC -> PLC |
| 100 | `PLC_READY` | PLC -> PC |
| 151 | `POSITION_REACHED` | PLC -> PC |
| 152 | `CAPTURE_AUTH_REQUEST` | PLC -> PC |
| 155 | `STEP_COMPLETE` | PLC -> PC |
| 105 | `RUN_COMPLETE` | PLC -> PC |

---

## 6. Camera Communication Protocol

The camera service uses a **custom JSON-over-TCP** protocol on port `16000`. The `machine_control/camera_tcp.py` module is the client.

```
Request:  {"cmd": "SAVE_LATEST", "mode": "...", "step_index": N, ...}\n
Response: {"ok": true, "path": "/abs/path/to/image.jpg"}\n
```

Supported commands: `START`, `STOP`, `READY`, `FRESH`, `SAVE_LATEST`, `STATUS`.

In real deployment, the physical camera SDK service (IDS, Basler, etc.) must implement this same JSON-over-TCP interface so `pc_controller.py` requires no changes when switching from simulation to hardware.

---

## 7. MES / Shopfloor API Integration

When a barcode is scanned, `machine_control/serialtest_api_client.py` calls the factory MES REST API:

```
GET https://<MES_HOST>/ashx/WebAPI/Board/SerialTest/HandlerGetSerialInfo.ashx?sn=<SERIAL>
```

**Response fields used:**

| Field | Used For |
|---|---|
| `HasData` | `"1"` = board exists in MES |
| `M_NO` | Work order number, links run to `orders` table |
| `SemiModel` | PCB model name stored in run record |
| `PCB_Length`, `PCB_Width` | Input to `recipe.py` for XY grid calculation |

The client supports two modes: `fixture` (built-in static test data, no network) and `real` (live HTTPS call). In simulation, `simulation/shopfloor_sim.py` provides a local FastAPI mock at `localhost:9090`.

---

## 8. Real-Time Update Pipeline

How a captured image appears on the operator's screen in milliseconds:

```
1. Camera captures image -> saves to disk (local_path)
2. pc_controller.py -> POST /images/ to FastAPI (metadata + image path)
3. FastAPI inserts row into images table
4. PostgreSQL TRIGGER fires: NOTIFY ui_update '<json_payload>'
5. FastAPI background task (listen_pg_notifications) receives the NOTIFY
6. FastAPI broadcasts JSON over all active WebSocket connections (/ws/ui-updates)
7. React UI (ImageViewer.tsx) receives WebSocket message -> renders the image
```

The image binary is served by Nginx (`localhost:8080`) or fetched from MinIO — NOT through the FastAPI process.

---

## 9. Key API Endpoints

All endpoints served by `FastAPI` at `http://localhost:8000`.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/runs/` | List inspection runs (filterable by S/N, M_NO, status) |
| `POST` | `/runs/start` | Trigger a new inspection for a given serial number |
| `GET` | `/runs/{run_number}` | Get run details including all images |
| `GET` | `/images/` | List images with filters |
| `POST` | `/images/` | Create image record (called by `pc_controller.py`) |
| `GET` | `/images/{image_id}/file` | Stream image binary from disk/MinIO |
| `GET` | `/orders/` | List manufacturing orders |
| `GET` | `/system-configs/` | Read system configuration KV store |
| `PUT` | `/system-configs/{key}` | Update a config value |
| `WebSocket` | `/ws/ui-updates` | Real-time push stream |

---

## 10. Image Storage Strategy

| Location | Purpose | Path Pattern |
|---|---|---|
| **Local disk** | Immediate access by API and Nginx | `watch_dir/<M_NO>/<SN>/<run_number>/TOP/*.jpg` |
| **MinIO/NAS** | Long-term archival on external server | `aoi-images/<M_NO>/<SN>/<run_number>/...` |

`scripts/sync_to_server.py` runs continuously in the background, polling for `is_uploaded_longterm = FALSE`, uploading to MinIO, and updating `longterm_path` and `is_uploaded_longterm` in the DB.

The planned external AI inference server will `GET` images via Nginx, run analysis, then `PATCH /images/{id}` to set `condition = 'PASS'` or `'FAIL'`.

---

## 11. Environment Variables

All configuration loaded from `.env` files via `python-dotenv`.

| Variable | Default | Used By |
|---|---|---|
| `DB_HOST` | `127.0.0.1` | API, machine_control |
| `DB_PORT` | `5433` | API, machine_control |
| `DB_ROOT_USER` | `admin` | API, machine_control |
| `DB_ROOT_PASSWORD` | `aoi123!` | API, machine_control |
| `FASTAPI_URL` | `http://127.0.0.1:8000` | pc_controller.py |
| `SHOPFLOOR_API_URL` | `http://127.0.0.1:9090/...` | headless_runner.py |
| `MINIO_ENDPOINT` | `192.168.40.21:9000` | API, sync script |
| `MINIO_ACCESS_KEY` | `aoi_admin` | API, sync script |
| `MINIO_SECRET_KEY` | `aoi@1234` | API, sync script |
| `MINIO_BUCKET` | `aoi-images` | API, sync script |
| `IMAGE_WATCH_DIR` | `./watch_dir` | API, Nginx |

> **Rule:** Never hardcode these values. Always use `os.environ.get("VAR_NAME", default)`.

---

## 12. Running the System

### Prerequisites
- Conda environment `aoi_env` with Python 3.10+ (see `.agents/AGENTS.md` section 0)
- Node.js 18+
- Docker Desktop (for dev PostgreSQL)

### Start (Development/Simulation Mode)
```bash
conda activate aoi_env
python headless_runner.py start
```
Starts: Docker (PostgreSQL), FastAPI (port 8000), React UI (port 3001), PLC Simulator (port 15000), Shopfloor Simulator (port 9090), PC Controller.

### Stop
```bash
python headless_runner.py stop
```

### End-to-End Integration Test
```bash
conda activate aoi_env
python test_sn5434.py
```
Sends `SN5434` through the full pipeline: API -> PLC simulation -> image capture -> DB verification.

### Access Points
| Service | URL |
|---|---|
| Operator Dashboard | http://localhost:3001 |
| FastAPI Swagger UI | http://localhost:8000/docs |
| pgAdmin (DB admin) | http://localhost:5050 |
| Nginx Image Server | http://localhost:8080 |

---

## 13. Simulation vs. Hardware Mapping

| Simulator | Port | Replaced By (Production) |
|---|---|---|
| `simulation/plc_sim.py` | 15000 | Mitsubishi FX5U PLC (real IP, same port) |
| `simulation/camera_sim.py` | 16000 | Physical camera SDK service (same JSON protocol) |
| `simulation/shopfloor_sim.py` | 9090 | Factory MES HTTPS endpoint |

To switch from simulation to hardware: change `--plc-host` to the real PLC IP (e.g., `192.168.3.250`) and `--api-mode real` in the `pc_controller.py` launch arguments. No other code changes required.

---

## 14. Critical Rules for Modifying Code

1. **Never make `pc_controller.py` async.** SLMP timing is wall-clock sensitive. `asyncio` introduces non-deterministic delays that cause PLC event sequence failures.

2. **Every PLC event received must be acknowledged.** Pattern: `event = recv_event()` -> process -> `send_ack(event.sequence)`. Missing an ACK stalls the PLC permanently.

3. **Never hardcode database credentials or API URLs.** Use `os.environ.get()` for all runtime config.

4. **Do not bypass the `PostgresDatabase` class** in `machine_control/database_pg.py`. All machine-side DB writes must go through this class.

5. **FastAPI uses connection pooling.** Always call `release_db_connection(conn)` in a `finally` block after `get_db_connection()` to prevent pool exhaustion.

6. **`simulation/shared_protocol.py` is a separate copy** of `machine_control/shared_protocol.py`. When updating event codes or register addresses, update both files.

---

## 15. Future Integration Points

| Feature | Status | Notes |
|---|---|---|
| AI Inference Server | Planned | `GET` images from Nginx, `PATCH /images/{id}` with PASS/FAIL result |
| NAS/MinIO Archival | Implemented | `sync_to_server.py` handles background upload |
| Production build (Electron + PyInstaller) | Planned | See `docs/PRODUCTION_DEPLOYMENT_ARCHITECTURE.md` |
| Native PostgreSQL (Docker-free) | Planned | For production IPC deployment, install PostgreSQL natively |
| Real camera SDK integration | Pending hardware | SDK must expose the `camera_tcp.py` JSON-over-TCP interface |
