# AI Agent Rules — NTUST AOI

## What is this project?

An industrial **Automated Optical Inspection (AOI)** system for PCB quality control on a factory floor.
Full architecture: [`ARCHITECTURE.md`](../ARCHITECTURE.md) | Full schema: [`docs/reference/DATABASE_SCHEMA.md`](../docs/reference/DATABASE_SCHEMA.md)

**4 modules:**
| Directory | Role |
|---|---|
| `machine_control/` | Hardware layer — PLC (SLMP), Camera (JSON/TCP), sync/blocking Python |
| `ntust_aoi_pcb_db/` | Backend — FastAPI + PostgreSQL + MinIO |
| `NTUST-AOI-UI/` | Operator Dashboard — React 19, Vite, WebSocket |
| `simulation/` | Dev-only simulators (PLC, Camera, MES) |

Each module has its own `README.md` with responsibilities, interfaces, and constraints.

---

## How do I run it?

```bash
# Prerequisites: conda aoi_env (Python 3.10+), Node.js 18+, Docker Desktop

conda activate aoi_env           # ALWAYS use this env — never install globally

make start                       # Start full system (Docker DB + API + UI + Simulators)
make stop                        # Stop everything cleanly
make test                        # Run end-to-end integration test
```

If `make` is not available: `python headless_runner.py start|stop`

---

## How do I verify it?

```bash
make test                        # E2E test: scans SN5434, checks DB records + image files
make check-api                   # Hits /runs/ and /system/status, prints JSON
```

Access points after `make start`:
- Operator UI: http://localhost:3001
- API Swagger: http://localhost:8000/docs
- pgAdmin: http://localhost:5050

---

## Critical rules (non-negotiable)

1. **`pc_controller.py` must stay synchronous.** SLMP protocol requires blocking ACK timing. No `asyncio` refactoring.
2. **Every PLC event received must be ACK'd.** Missing ACK → PLC halts permanently.
3. **No hardcoded URLs/credentials.** Always `os.environ.get("VAR_NAME")`.
4. **Conda env only.** `conda activate aoi_env` before any Python command.
5. **Update module `README.md` when modifying a module's interface or constraints.**

---

## Environment setup (first time)

```bash
conda create -n aoi_env python=3.10 -y
conda activate aoi_env
pip install -r ntust_aoi_pcb_db/requirements.txt
cd NTUST-AOI-UI && npm install
```
