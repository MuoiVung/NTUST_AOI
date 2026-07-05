# NTUST AOI — Database Schema Reference

> **Source of truth:** `ntust_aoi_pcb_db/sql/init.sql` and `ntust_aoi_pcb_db/api/main.py`.  
> This document is generated from the actual source code. Do not edit manually without also updating the SQL.

---

## Overview

- **Engine:** PostgreSQL 18
- **Database name:** `pcb_aoi_db`
- **Connection (dev):** `postgresql://admin:aoi123!@127.0.0.1:5433/pcb_aoi_db`
- **Schema init:** `ntust_aoi_pcb_db/sql/init.sql`
- **Extension:** `uuid-ossp` (for `uuid_generate_v4()`)

---

## Entity-Relationship Diagram

```
orders (1) ────────────── (N) runs
                                │
                    ┌───────────┼───────────┐
                    │           │           │
               (N) images  (N) run_steps  (N) error_log
                                │
                           step_id (FK) ──> (N) error_log

external_lookup_log  (independent audit log, no FK to runs)
system_configs       (independent KV store)
```

---

## Table 1: `orders`

Manufacturing work orders. Each order tracks a production batch.

```sql
CREATE TABLE orders (
    m_no            VARCHAR(50) PRIMARY KEY,
    target_quantity INT NOT NULL DEFAULT 0,
    actual_quantity INT NOT NULL DEFAULT 0,
    status          VARCHAR(20) DEFAULT 'ACTIVE',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

| Column | Type | Nullable | Description |
|---|---|---|---|
| `m_no` | `VARCHAR(50)` | NOT NULL | **Primary Key.** Manufacturing order number (e.g., `MO-DEMO-001`) |
| `target_quantity` | `INT` | NOT NULL | Planned number of PCBs to inspect |
| `actual_quantity` | `INT` | NOT NULL | Boards completed — auto-incremented by trigger |
| `status` | `VARCHAR(20)` | — | `ACTIVE` / `COMPLETED` / `CANCELLED` |
| `created_at` | `TIMESTAMP` | — | Record creation time |

**Notes:**
- `actual_quantity` is automatically incremented by the `increment_order_quantity` trigger (see Triggers section). Do NOT update it manually.
- When `DELETE FROM runs` is called via the API, `actual_quantity` is recalculated by a count query.

---

## Table 2: `runs`

One record per PCB inspection session. The central table linking all other data.

```sql
CREATE TABLE runs (
    run_number    VARCHAR(50) PRIMARY KEY,
    serial_number VARCHAR(50) NOT NULL,
    semi_model    VARCHAR(100),
    m_no          VARCHAR(50) NOT NULL REFERENCES orders(m_no),
    machine_id    VARCHAR(50),
    status        VARCHAR(20) DEFAULT 'COMPLETED',
    is_latest     BOOLEAN DEFAULT TRUE,
    start_time    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_runs_serial ON runs(serial_number);
CREATE INDEX idx_runs_order  ON runs(m_no);
CREATE INDEX idx_runs_m_no_created_at ON runs(m_no, created_at DESC);
```

| Column | Type | Nullable | Description |
|---|---|---|---|
| `run_number` | `VARCHAR(50)` | NOT NULL | **Primary Key.** Unique run ID |
| `serial_number` | `VARCHAR(50)` | NOT NULL | Scanned PCB barcode / serial |
| `semi_model` | `VARCHAR(100)` | — | PCB model name returned by MES |
| `m_no` | `VARCHAR(50)` | NOT NULL | **FK → orders.m_no** |
| `machine_id` | `VARCHAR(50)` | — | Hostname of the IPC running `pc_controller.py` |
| `status` | `VARCHAR(20)` | — | `PENDING` / `RUNNING` / `COMPLETED` / `ERROR` |
| `is_latest` | `BOOLEAN` | — | `TRUE` = most recent run for this serial number. Old runs are set to `FALSE` when re-scanned |
| `start_time` | `TIMESTAMP` | — | When the inspection began |
| `created_at` | `TIMESTAMP` | — | Record insertion time |

**Status lifecycle used by API:**
```
PENDING  →  (pc_controller picks it up)  →  RUNNING  →  COMPLETED / ERROR
```

**Important:** The API at `POST /runs/start` writes `pending_run_sn` into `system_configs`. The `pc_controller.py` listens for `NOTIFY new_run_sn` on the PostgreSQL channel to pick up the pending serial number.

---

## Table 3: `images`

One record per captured image file. Each inspection step generates two images (Top + Bottom).

```sql
CREATE TABLE images (
    image_id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_number            VARCHAR(50) NOT NULL REFERENCES runs(run_number) ON DELETE CASCADE,
    side                  VARCHAR(10),
    local_path            TEXT,
    longterm_path         TEXT,
    is_uploaded_longterm  BOOLEAN DEFAULT FALSE,
    row_idx               INTEGER,
    col_idx               INTEGER,
    condition             VARCHAR(10),
    file_size_bytes       BIGINT,
    capture_time          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_images_run ON images(run_number);
```

| Column | Type | Nullable | Description |
|---|---|---|---|
| `image_id` | `UUID` | NOT NULL | **Primary Key.** Auto-generated via `uuid_generate_v4()` |
| `run_number` | `VARCHAR(50)` | NOT NULL | **FK → runs.run_number** (CASCADE DELETE) |
| `side` | `VARCHAR(10)` | — | `Top` or `Bottom` |
| `local_path` | `TEXT` | — | Absolute file path on the IPC disk |
| `longterm_path` | `TEXT` | — | Storage key in MinIO/NAS after archival (`bucket/path`) |
| `is_uploaded_longterm` | `BOOLEAN` | — | `FALSE` until `sync_to_server.py` uploads successfully |
| `row_idx` | `INTEGER` | — | Row position in the XY inspection grid |
| `col_idx` | `INTEGER` | — | Column position in the XY inspection grid |
| `condition` | `VARCHAR(10)` | — | `UNKNOWN` (default) → `PASS` / `FAIL` (set by AI server) |
| `file_size_bytes` | `BIGINT` | — | Image file size |
| `capture_time` | `TIMESTAMP` | — | When the camera captured the image |

**Notes:**
- `condition` is inserted as `'UNKNOWN'` by `POST /images/`. The external AI inference server calls `PUT /images/{image_id}` to set it to `'PASS'` or `'FAIL'`.
- Deleting a run (`DELETE /runs/{run_number}`) also deletes all child images from the DB AND removes the physical files from disk and MinIO (CASCADE + application logic).

---

## Table 4: `run_steps`

Step-by-step execution log. One record per XY grid position per run, tracking timestamps for each phase of the SLMP event cycle.

```sql
CREATE TABLE run_steps (
    step_id             SERIAL PRIMARY KEY,
    run_number          VARCHAR(50) NOT NULL REFERENCES runs(run_number) ON DELETE CASCADE,
    step_index          INTEGER NOT NULL,
    row_idx             INTEGER,
    col_idx             INTEGER,
    target_x_mm         REAL,
    target_y_mm         REAL,
    actual_x_mm         REAL,
    actual_y_mm         REAL,
    status              VARCHAR(50) NOT NULL,
    started_at          TIMESTAMP,
    position_reached_at TIMESTAMP,
    capture_auth_at     TIMESTAMP,
    capture_window_at   TIMESTAMP,
    capture_done_at     TIMESTAMP,
    completed_at        TIMESTAMP,
    error_code          INTEGER,
    note                TEXT
);
CREATE INDEX idx_run_steps_run ON run_steps(run_number);
```

| Column | Type | Nullable | Description |
|---|---|---|---|
| `step_id` | `SERIAL` | NOT NULL | **Primary Key.** Auto-incrementing |
| `run_number` | `VARCHAR(50)` | NOT NULL | **FK → runs.run_number** (CASCADE DELETE) |
| `step_index` | `INTEGER` | NOT NULL | Sequential index within the run (0-based) |
| `row_idx`, `col_idx` | `INTEGER` | — | Grid position |
| `target_x_mm`, `target_y_mm` | `REAL` | — | Coordinates sent to PLC via SLMP |
| `actual_x_mm`, `actual_y_mm` | `REAL` | — | Actual position reported by PLC |
| `status` | `VARCHAR(50)` | NOT NULL | `PENDING` / `MOVING` / `CAPTURE_AUTH` / `CAPTURING` / `COMPLETED` / `ERROR` |
| `started_at` | `TIMESTAMP` | — | When `SEMI_AUTO_STEP_STARTED` was received from PLC |
| `position_reached_at` | `TIMESTAMP` | — | When `POSITION_REACHED` was received from PLC |
| `capture_auth_at` | `TIMESTAMP` | — | When `CAPTURE_AUTH_REQUEST` was received |
| `capture_window_at` | `TIMESTAMP` | — | When `CAPTURE_WINDOW_OPEN` was received |
| `capture_done_at` | `TIMESTAMP` | — | When capture completed and `CAPTURE_DONE` was sent to PLC |
| `completed_at` | `TIMESTAMP` | — | When `STEP_COMPLETE` was received from PLC |
| `error_code` | `INTEGER` | — | SLMP error code if step failed |
| `note` | `TEXT` | — | Free-text note |

---

## Table 5: `error_log`

Persistent log of all machine and software errors with full context.

```sql
CREATE TABLE error_log (
    error_id        SERIAL PRIMARY KEY,
    run_number      VARCHAR(50) REFERENCES runs(run_number) ON DELETE SET NULL,
    step_id         INTEGER REFERENCES run_steps(step_id) ON DELETE SET NULL,
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_code      INTEGER NOT NULL,
    error_symbol    VARCHAR(100),
    error_category  VARCHAR(100),
    error_message   TEXT,
    source          VARCHAR(50) NOT NULL,
    recovery_action TEXT,
    resolved        BOOLEAN DEFAULT FALSE,
    details_json    JSONB
);
CREATE INDEX idx_error_log_run ON error_log(run_number);
```

| Column | Type | Nullable | Description |
|---|---|---|---|
| `error_id` | `SERIAL` | NOT NULL | **Primary Key.** Auto-incrementing |
| `run_number` | `VARCHAR(50)` | — | **FK → runs.run_number** (SET NULL on delete) |
| `step_id` | `INTEGER` | — | **FK → run_steps.step_id** (SET NULL on delete) |
| `timestamp` | `TIMESTAMP` | — | When the error occurred |
| `error_code` | `INTEGER` | NOT NULL | Numeric error code (from `shared_protocol.py` `ErrorCode` enum) |
| `error_symbol` | `VARCHAR(100)` | — | Human-readable name (e.g., `TIMEOUT`, `PLC_ACK_FAILED`) |
| `error_category` | `VARCHAR(100)` | — | Category (e.g., `SLMP`, `CAMERA`, `API`) |
| `error_message` | `TEXT` | — | Full error message string |
| `source` | `VARCHAR(50)` | NOT NULL | Origin module (e.g., `pc_controller`, `plc`, `api`) |
| `recovery_action` | `TEXT` | — | What action was taken or recommended |
| `resolved` | `BOOLEAN` | — | `FALSE` = open error; `TRUE` = acknowledged |
| `details_json` | `JSONB` | — | Arbitrary JSON for extra context |

---

## Table 6: `external_lookup_log`

Audit trail of every call made to the factory MES/Shopfloor API. Used for debugging connectivity and verifying board data received.

```sql
CREATE TABLE external_lookup_log (
    lookup_id           SERIAL PRIMARY KEY,
    run_number          VARCHAR(50),
    serial_number_query VARCHAR(50) NOT NULL,
    query_time          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    api_endpoint        TEXT,
    http_status_code    INTEGER,
    has_data            VARCHAR(10),
    msg                 TEXT,
    sn_returned         VARCHAR(50),
    semi_model          VARCHAR(100),
    pcb_length_mm       REAL,
    pcb_width_mm        REAL,
    accepted            BOOLEAN DEFAULT FALSE,
    raw_response_json   JSONB,
    error_message       TEXT
);
```

| Column | Type | Nullable | Description |
|---|---|---|---|
| `lookup_id` | `SERIAL` | NOT NULL | **Primary Key.** Auto-incrementing |
| `run_number` | `VARCHAR(50)` | — | Associated run (no FK, log is independent) |
| `serial_number_query` | `VARCHAR(50)` | NOT NULL | The S/N sent to the MES API |
| `query_time` | `TIMESTAMP` | — | When the API call was made |
| `api_endpoint` | `TEXT` | — | Full URL called |
| `http_status_code` | `INTEGER` | — | HTTP response code (200, 404, etc.) |
| `has_data` | `VARCHAR(10)` | — | MES response field: `"1"` = found, `"0"` = not found |
| `msg` | `TEXT` | — | MES response message |
| `sn_returned` | `VARCHAR(50)` | — | SN returned by MES (may differ from query) |
| `semi_model` | `VARCHAR(100)` | — | PCB model returned by MES |
| `pcb_length_mm`, `pcb_width_mm` | `REAL` | — | Board dimensions returned by MES |
| `accepted` | `BOOLEAN` | — | Whether the result was accepted and used for the run |
| `raw_response_json` | `JSONB` | — | Full raw JSON response from MES |
| `error_message` | `TEXT` | — | Exception message if the API call failed |

---

## Table 7: `system_configs`

Key-value configuration store. Used for both runtime parameters and internal inter-process signaling.

```sql
CREATE TABLE system_configs (
    config_key   SERIAL PRIMARY KEY,
    config_name  VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT,
    unit         VARCHAR(20)
);
```

| Column | Type | Nullable | Description |
|---|---|---|---|
| `config_key` | `SERIAL` | NOT NULL | **Primary Key.** Auto-incrementing |
| `config_name` | `VARCHAR(100)` | NOT NULL | **UNIQUE.** Configuration parameter name |
| `config_value` | `TEXT` | — | Value (always stored as text, cast as needed) |
| `unit` | `VARCHAR(20)` | — | Optional unit (e.g., `mm`, `Seconds`) |

**Known keys initialized by `POST /configs/init`:**

| `config_name` | Default Value | Unit | Purpose |
|---|---|---|---|
| `longterm_sync_interval` | `0` | `Seconds` | Interval for MinIO sync loop |
| `sync_retry_interval` | `0` | `Seconds` | Retry delay on upload failure |
| `camera_fov_step_mm` | `40.0` | `mm` | Camera field-of-view step for grid generation |
| `camera_margin_mm` | `10.0` | `mm` | Edge margin for grid generation |

**Internal signaling keys (not exposed via `/configs/` endpoint):**

| `config_name` | Purpose |
|---|---|
| `pending_run_sn` | Written by `POST /runs/start`; read by `pc_controller.py` after receiving `NOTIFY new_run_sn` |
| `plc_status` | Written by `pc_controller.py` to report PLC connection state (`OK` / `ERROR`) |

---

## Triggers

### `increment_order_quantity`

Fires `AFTER INSERT OR UPDATE ON runs`.

```sql
CREATE OR REPLACE FUNCTION increment_order_quantity()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'COMPLETED' AND NEW.is_latest = TRUE THEN
        IF OLD.status IS NULL OR OLD.status != 'COMPLETED' THEN
            UPDATE orders SET actual_quantity = actual_quantity + 1
            WHERE m_no = NEW.m_no;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_increment_order_quantity
AFTER INSERT OR UPDATE ON runs
FOR EACH ROW EXECUTE FUNCTION increment_order_quantity();
```

**Logic:** Increments `orders.actual_quantity` by 1 only when:
1. The run's `status` transitions **to** `COMPLETED` (not already COMPLETED)
2. AND `is_latest = TRUE` (prevents double-counting historical re-scans)

---

## PostgreSQL NOTIFY Channels

The system uses PostgreSQL's native pub/sub for inter-process communication:

| Channel | NOTIFY sender | LISTEN receiver | Payload | Purpose |
|---|---|---|---|---|
| `ui_update` | DB trigger on `images` INSERT | `api/main.py` background task | JSON with image metadata | Real-time WebSocket push to React UI |
| `new_run_sn` | `api/main.py` (`POST /runs/start`) | `machine_control/pc_controller.py` | Serial number string | Signal to start a new inspection run |

---

## Indexes Summary

| Table | Index | Columns |
|---|---|---|
| `runs` | `idx_runs_serial` | `serial_number` |
| `runs` | `idx_runs_order` | `m_no` |
| `runs` | `idx_runs_m_no_created_at` | `m_no, created_at DESC` |
| `images` | `idx_images_run` | `run_number` |
| `run_steps` | `idx_run_steps_run` | `run_number` |
| `error_log` | `idx_error_log_run` | `run_number` |

---

## API Endpoints that Interact with the Schema

| Method | Path | Table(s) Affected |
|---|---|---|
| `GET` | `/runs/` | `runs` (READ) |
| `GET` | `/runs/{run_number}` | `runs` (READ) |
| `POST` | `/runs/start` | `system_configs` (WRITE), NOTIFY `new_run_sn` |
| `DELETE` | `/runs/{run_number}` | `runs`, `images` (DELETE + file cleanup) |
| `GET` | `/images/` | `images` (READ) |
| `POST` | `/images/` | `images` (INSERT, triggers `ui_update` NOTIFY) |
| `PUT` | `/images/{image_id}` | `images.condition` (UPDATE) |
| `DELETE` | `/images/{image_id}` | `images` (DELETE + file cleanup) |
| `GET` | `/images/proxy/{image_id}` | `images` (READ — serves binary) |
| `GET` | `/system/status` | `system_configs`, `runs` (READ) |
| `GET` | `/configs/` | `system_configs` (READ, excludes internal keys) |
| `PUT` | `/configs/{config_name}` | `system_configs` (UPDATE) |
| `POST` | `/configs/init` | `system_configs` (INSERT ON CONFLICT DO NOTHING) |
