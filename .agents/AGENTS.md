# AGENTS.md — NTUST AOI

## Project Overview

An industrial **Automated Optical Inspection (AOI)** system for PCB quality control
on a factory floor. It connects a Mitsubishi FX5U PLC and dual-camera array to a
FastAPI + PostgreSQL backend and a React operator dashboard.

---

## Quick Start

```bash
conda activate aoi_env          # Always activate first
make setup                      # Install all Python + Node dependencies (first time only)
make start                      # Start full system (DB + API + UI + simulators)
make test                       # Run end-to-end integration test (SN5434)
make stop                       # Stop all services cleanly
```

Fallback if `make` unavailable: `python headless_runner.py start|stop`

Access points after `make start`:
- Operator UI: http://localhost:3001
- API Swagger: http://localhost:8000/docs
- pgAdmin: http://localhost:5050

---

## Hard Constraints

> These are non-negotiable. Do not bypass any of them.

### Code

1. **`pc_controller.py` must stay synchronous.** SLMP protocol requires blocking ACK
   timing. No `asyncio` refactoring — ever.
   *(Applicability: any change to `machine_control/`. Expiry: if SLMP is replaced by async protocol.)*

2. **Every PLC event received must be ACK'd.** Pattern: `recv_event()` → process →
   `send_ack(seq)`. Missing ACK → PLC halts permanently.
   *(Applicability: any change to `pc_controller.py` or `shared_protocol.py`.)*

3. **No hardcoded URLs or credentials.** Always use `os.environ.get("VAR_NAME")`.
   *(Applicability: all Python files. Check `.env.example` for variable names.)*

4. **Conda env only.** Run all Python commands inside `conda activate aoi_env`.
   Never install packages globally.

5. **Never commit `.env` files or secrets.** Use `.env.example` as the template
   with placeholder values only.

### Git Workflow

6. **Pull before every session.** Run `git pull origin main` then `make git-check`
   before making any changes. Never work on a stale checkout.

7. **Never commit directly to `main`.** All changes go on a dedicated branch:
   `git checkout -b <type>/<description>` (types: `feat`, `fix`, `docs`, `refactor`).

8. **Human must resolve all merge conflicts.** When merging into `main`, if any
   conflict exists: stop, display full conflict diff, do NOT auto-resolve.
   A human must review and resolve each conflict manually.
   *(See `docs/GIT_WORKFLOW.md` for the full conflict protocol.)*

### Documentation

9. **After modifying any source file, run `make update-docs`** and update all
   listed `.md` files before committing. Doc updates go in the same commit as
   the code change.

10. **`docs/system architect overall/` is HUMAN-ONLY.** AI agents must never
    create, modify, or delete any file in that directory.

---

## Topic Docs

Read these on-demand — only when the task requires it.

| Document | Read when... |
|---|---|
| [`ARCHITECTURE.md`](../ARCHITECTURE.md) | Need system topology or module routing |
| [`machine_control/README.md`](../machine_control/README.md) | Working on hardware/PLC/camera code |
| [`machine_control/ARCHITECTURE.md`](../machine_control/ARCHITECTURE.md) | Need PLC D-register map, event codes, camera protocol |
| [`ntust_aoi_pcb_db/README.md`](../ntust_aoi_pcb_db/README.md) | Working on backend API |
| [`ntust_aoi_pcb_db/ARCHITECTURE.md`](../ntust_aoi_pcb_db/ARCHITECTURE.md) | Need DB schema, real-time pipeline, API endpoints |
| [`NTUST-AOI-UI/README.md`](../NTUST-AOI-UI/README.md) | Working on frontend components |
| [`NTUST-AOI-UI/ARCHITECTURE.md`](../NTUST-AOI-UI/ARCHITECTURE.md) | Need component tree, WebSocket flow |
| [`simulation/README.md`](../simulation/README.md) | Working on simulators |
| [`simulation/ARCHITECTURE.md`](../simulation/ARCHITECTURE.md) | Need sim vs hardware mapping |
| [`docs/reference/DATABASE_SCHEMA.md`](../docs/reference/DATABASE_SCHEMA.md) | Need full PostgreSQL column-level schema |
| [`docs/GIT_WORKFLOW.md`](../docs/GIT_WORKFLOW.md) | Need branch naming, merge conflict steps |
| [`docs/deployment/REAL_HARDWARE_INTEGRATION.md`](../docs/deployment/REAL_HARDWARE_INTEGRATION.md) | Deploying to physical PLC/camera |
