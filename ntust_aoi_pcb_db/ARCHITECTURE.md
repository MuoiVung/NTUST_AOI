# ntust_aoi_pcb_db — Architecture Reference

> Read this when you need to understand **the data model, real-time pipeline, and API internals**.
> For what this module does, its interfaces, and how to run it, see [`README.md`](README.md).

---

## 1. Tech Stack

| Component | Library / Tool | Version |
|---|---|---|
| Web framework | FastAPI | ≥ 0.111.0 |
| ASGI server | Uvicorn | ≥ 0.30.0 |
| Data validation | Pydantic | ≥ 2.7.0 |
| DB driver | psycopg2-binary | 2.9.10 |
| DB pool | `psycopg2.pool.SimpleConnectionPool` | max 10 conns |
| PG NOTIFY bridge | `select.select()` + `psycopg2` | — |
| WebSocket | FastAPI native (`WebSocket`) | — |
| Object storage | `minio` | 7.2.5 |
| Config | `python-dotenv` | 1.2.1 |

---

## 2. Database Schema

All tables live in the `pcb_aoi_db` PostgreSQL database.
Schema source of truth: `sql/init.sql`.
Full column-level reference: [`docs/reference/DATABASE_SCHEMA.md`](../docs/reference/DATABASE_SCHEMA.md).

```
orders                          # Manufacturing work orders
  m_no (PK)                     # Work order number
  target_quantity               # Planned board count
  actual_quantity               # Auto-incremented by trigger on run COMPLETED
  status                        # ACTIVE / CLOSED

runs                            # One per PCB scan session
  run_number (PK)
  serial_number                 # Scanned barcode / PCB serial
  semi_model                    # PCB model (from MES)
  m_no (FK → orders)
  machine_id                    # hostname of the IPC
  status                        # COMPLETED / IN_PROGRESS / ERROR
  is_latest                     # True only for the most recent run per S/N

run_steps                       # One row per XY grid position within a run
  step_id (PK)
  run_number (FK → runs)
  step_index, row_idx, col_idx
  target_x_mm, target_y_mm     # Planned coordinates sent to PLC
  actual_x_mm, actual_y_mm     # Actual position reported by PLC
  status                        # PENDING / COMPLETED / ERROR
  timestamps: started_at, position_reached_at, capture_auth_at,
              capture_window_at, capture_done_at, completed_at

images                          # One row per captured image file
  image_id (UUID PK)
  run_number (FK → runs)
  side                          # "Top" or "Bottom"
  local_path                    # Absolute path on IPC disk
  longterm_path                 # Key in MinIO/NAS after sync
  is_uploaded_longterm          # Upload status flag
  row_idx, col_idx              # Grid position
  condition                     # PASS / FAIL (set by external AI server)
  file_size_bytes, capture_time

error_log                       # Machine and software errors
  error_id (PK)
  run_number (FK), step_id (FK)
  error_code, error_symbol, error_category
  source                        # e.g. "pc_controller", "plc"
  recovery_action, resolved, details_json (JSONB)

external_lookup_log             # Audit trail of MES/Shopfloor API calls
  lookup_id (PK)
  serial_number_query
  http_status_code, raw_response_json (JSONB)
  pcb_length_mm, pcb_width_mm  # Dimensions returned by MES

system_configs                  # Key-value store for runtime parameters
  config_name (UNIQUE), config_value, unit
  # Internal keys (NOT exposed via /configs/ endpoint):
  #   pending_run_sn  — queued serial number for next inspection
  #   plc_status      — current PLC connection state
```

### PostgreSQL Trigger

`increment_order_quantity` fires `AFTER INSERT OR UPDATE ON runs`.
When `status = 'COMPLETED'` AND `is_latest = TRUE`, it increments
`orders.actual_quantity` by 1.

### PostgreSQL NOTIFY (Real-time push)

`api/main.py` runs a background task listening on channel `ui_update` via
`LISTEN ui_update`. A trigger fires `NOTIFY ui_update '<json>'` when a new
image row is inserted. The FastAPI task broadcasts it to all WebSocket clients.

---

## 3. Real-Time Update Pipeline

How a captured image appears on the operator's screen:

```
1. Camera captures image → saves to disk (local_path)
2. pc_controller.py → POST /images/ to FastAPI (metadata + image path)
3. FastAPI inserts row into images table
4. PostgreSQL TRIGGER fires: NOTIFY ui_update '<json_payload>'
5. FastAPI background task (listen_pg_notifications) receives the NOTIFY
6. FastAPI broadcasts JSON over all active WebSocket connections (/ws/ui-updates)
7. React UI (ImageViewer.tsx) receives WebSocket message → renders the image
```

> The image **binary** is served by Nginx (`localhost:8080`) or fetched from MinIO.
> It does NOT pass through the FastAPI process.

---

## 4. Key API Endpoints

All endpoints at `http://localhost:8000`. Full Swagger: `/docs`.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/runs/` | List inspection runs (filter by S/N, M_NO, status) |
| `POST` | `/runs/start` | Queue new inspection for a serial number |
| `GET` | `/runs/{run_number}` | Get run details including all images |
| `GET` | `/images/` | List images with filters |
| `POST` | `/images/` | Create image record (called by `pc_controller.py`) |
| `GET` | `/images/{image_id}/file` | Stream image binary from disk/MinIO |
| `PATCH` | `/images/{image_id}` | Update condition (called by AI inference server) |
| `GET` | `/orders/` | List manufacturing orders |
| `GET` | `/system-configs/` | Read system configuration KV store |
| `PUT` | `/system-configs/{key}` | Update a config value |
| `WebSocket` | `/ws/ui-updates` | Real-time push stream |
| `GET` | `/system/status` | Health check |

---

## 5. Image Storage Strategy

| Location | Purpose | Path Pattern |
|---|---|---|
| **Local disk** | Immediate access by API and Nginx | `watch_dir/<M_NO>/<SN>/<run_number>/TOP/*.jpg` |
| **MinIO/NAS** | Long-term archival | `aoi-images/<M_NO>/<SN>/<run_number>/...` |

`scripts/sync_to_server.py` runs continuously, polling for
`is_uploaded_longterm = FALSE`, uploading to MinIO, then updating
`longterm_path` and `is_uploaded_longterm` in the DB.

The planned external AI inference server will `GET` images via Nginx,
run analysis, then `PATCH /images/{id}` to set `condition = 'PASS'` or `'FAIL'`.

---

## 6. Connection Pool Rule

Always release connections in a `finally` block:
```python
conn = get_db_connection()
try:
    # ... use conn
finally:
    release_db_connection(conn)
```
Pool max = 10 connections. Failure to release causes pool exhaustion.
