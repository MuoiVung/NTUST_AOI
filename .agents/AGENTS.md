# AGENTS.md

This repository is designed for long-running coding-agent work. The goal is not
to maximize raw code output. The goal is to leave the repo in a state where the
next session can continue without guessing.

## Project Overview

An industrial **Automated Optical Inspection (AOI)** system for PCB quality control
on a factory floor. It connects a Mitsubishi FX5U PLC and dual-camera array to a
FastAPI + PostgreSQL backend and a React operator dashboard.

## Quick Start

```bash
conda activate aoi_env          # Always activate first
python init.py                  # Install dependencies and start the system
python tasks.py test            # Run end-to-end integration test (SN5434)
python tasks.py stop            # Stop all services cleanly
```

Access points after start:
- Operator UI: http://localhost:3001
- API Swagger: http://localhost:8000/docs
- pgAdmin: http://localhost:5050

## Startup Workflow

Before writing code:

1. Confirm the working directory with `pwd`.
2. Read `.agents/PROGRESS.md` for the latest verified state and next step.
3. Read `.agents/feature_list.json` and choose the highest-priority unfinished feature.
4. Review recent commits with `git log --oneline -5`.
5. Run `python init.py`.
6. Run the required smoke or end-to-end verification before starting new work.

If baseline verification is already failing, fix that first. Do not stack new
feature work on top of a broken starting state.

## Working Rules

- Work on one feature at a time.
- Do not mark a feature complete just because code was added.
- Keep changes within the selected feature scope unless a blocker forces a
  narrow supporting fix.
- Do not silently change verification rules during implementation.
- Prefer durable repo artifacts over chat summaries.

### Hard Constraints (NTUST AOI Specific)
> These are non-negotiable. Do not bypass any of them.

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

6. **Pull before every session.** Run `git pull origin main` then `python tasks.py git-check`
   before making any changes. Never work on a stale checkout.

7. **Never commit directly to `main`.** All changes go on a dedicated branch:
   `git checkout -b <type>/<description>` (types: `feat`, `fix`, `docs`, `refactor`).

8. **Human must resolve all merge conflicts.** When merging into `main`, if any
   conflict exists: stop, display full conflict diff, do NOT auto-resolve.
   A human must review and resolve each conflict manually.

9. **After modifying any source file, run `python tasks.py update-docs`** and update all
   listed `.md` files before committing. Doc updates go in the same commit as
   the code change.

10. **`docs/system architect overall/` is HUMAN-ONLY.** AI agents must never
    create, modify, or delete any file in that directory.

## Required Artifacts

- `.agents/feature_list.json`: source of truth for feature state
- `.agents/PROGRESS.md`: session log and current verified status
- `init.py`: standard startup and verification path
- `.agents/session-handoff.md`: optional compact handoff for larger sessions

## Definition Of Done

A feature is done only when all of the following are true:

- the target behavior is implemented
- the required verification actually ran
- evidence is recorded in `.agents/feature_list.json` or `.agents/PROGRESS.md`
- the repository remains restartable from the standard startup path

## End Of Session

Before ending a session:

1. Update `.agents/PROGRESS.md`.
2. Update `.agents/feature_list.json`.
3. Record any unresolved risk or blocker.
4. Commit with a descriptive message once the work is in a safe state.
5. Leave the repo clean enough for the next session to run `python init.py`
   immediately.

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
