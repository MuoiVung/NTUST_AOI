# ntust_aoi_pcb_db — Module README

## Responsibility

This module is the **backend API and database layer**. It is the central hub that:
- Stores all inspection data in PostgreSQL
- Serves HTTP and WebSocket endpoints to both the React UI and `pc_controller.py`
- Pushes real-time image notifications to the UI via PostgreSQL NOTIFY → WebSocket

## Files

| File | Responsibility |
|---|---|
| `api/main.py` | FastAPI application (732 lines). All REST endpoints + WebSocket + PG NOTIFY listener task. |
| `sql/init.sql` | PostgreSQL schema: 7 tables, indexes, triggers. **Single source of truth for the schema.** |
| `scripts/sync_to_server.py` | Background script: polls for `is_uploaded_longterm = FALSE`, uploads to MinIO/NAS, updates DB. |
| `scripts/reset_db.py` | Dev utility: truncates all tables. **Never run in production.** |
| `scripts/generate_mock_data.py` | Dev utility: seeds fake runs and images for UI development. |

| `.env` | Runtime configuration. See Environment Variables section below. |
| `requirements.txt` | Python dependencies for this module. |

## Interfaces

**Inbound (what this module receives):**
- `POST /images/` from `pc_controller.py` — creates image records
- `POST /runs/start` from React UI — queues a new inspection
- `PUT /images/{id}` from AI inference server — sets `condition = PASS/FAIL`
- WebSocket `/ws/ui-updates` from React UI — client subscribes for real-time events

**Outbound (what this module sends):**
- WebSocket broadcast to React UI on every new image (triggered by PostgreSQL NOTIFY)
- `NOTIFY new_run_sn` to `pc_controller.py` when a new serial number is queued
- MinIO object URLs stored in `images.longterm_path`

## Database Quick Reference

Full schema: [`docs/reference/DATABASE_SCHEMA.md`](../docs/reference/DATABASE_SCHEMA.md)

| Table | Key purpose |
|---|---|
| `orders` | Work order tracking |
| `runs` | One per PCB scan session |
| `run_steps` | One per XY grid position within a run |
| `images` | One per captured image file |
| `error_log` | Machine and software error log |
| `external_lookup_log` | MES API call audit trail |
| `system_configs` | Runtime KV store + internal signals |

## Critical Constraints

1. **Always use `async def` and `await` in `api/main.py`.** This is an async FastAPI app.
2. **Always release DB connections.** Pattern: `conn = get_db_connection()` → `finally: release_db_connection(conn)`. Pool has max 10 connections.
3. **Do NOT write to DB using raw SQL strings with f-strings.** Use parameterized queries `(%s)` to prevent SQL injection.
4. **`system_configs` has two internal keys** (`pending_run_sn`, `plc_status`) that must NOT be exposed via `/configs/` — filter is already in the endpoint.

## Run

```bash
conda activate aoi_env
# 1. Start PostgreSQL Native Service manually (e.g. via Windows Services)
# 2. Start FastAPI
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Access: http://localhost:8000/docs
