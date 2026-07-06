## Completed Work

### Core System
- [x] **`machine_control/pc_controller.py`** — Complete state machine: PLC handshake, recipe download, step loop (SLMP), camera trigger (JSON/TCP), DB write, error log
- [x] **`machine_control/shared_protocol.py`** — SLMP 3E Binary TCP client, D-register map, all EventCode/AckStatus/ErrorCode enums
- [x] **`machine_control/camera_tcp.py`** — JSON-over-TCP camera client protocol
- [x] **`machine_control/database_pg.py`** — psycopg2 adapter for machine-side DB writes
- [x] **`machine_control/recipe.py`** — Calculates XY grid from PCB dimensions (rows × cols)
- [x] **`machine_control/serialtest_api_client.py`** — HTTP client for MES API (fixture + real mode)

### Backend & Database
- [x] **`ntust_aoi_pcb_db/api/main.py`** — Full FastAPI application: REST endpoints, WebSocket, PG NOTIFY listener
- [x] **`ntust_aoi_pcb_db/sql/init.sql`** — PostgreSQL schema: 7 tables + indexes + `increment_order_quantity` trigger

- [x] **`ntust_aoi_pcb_db/scripts/sync_to_server.py`** — Background sync images to MinIO/NAS
- [x] **Real-time WebSocket pipeline** — Camera → FastAPI → PG NOTIFY → WebSocket → React UI

### Frontend (Operator Dashboard)
- [x] **`NTUST-AOI-UI/components/OperatorDashboard.tsx`** — Fully functional main HMI panel
- [x] **`NTUST-AOI-UI/components/ImageViewer.tsx`** — Real-time WebSocket image stream
- [x] **`NTUST-AOI-UI/components/RunList.tsx`** — Paginated inspection run history
- [x] **`NTUST-AOI-UI/components/RunGallery.tsx`** — Image grid for a single run
- [x] **`NTUST-AOI-UI/components/Dashboard.tsx`** — Metrics + Recharts charts
- [x] **`NTUST-AOI-UI/components/NewInspection.tsx`** — Form to start a new inspection
- [x] **`NTUST-AOI-UI/components/Settings.tsx`** — System config UI

### Simulators (Dev/Test)
- [x] **`simulation/plc_sim.py`** — Fake Mitsubishi FX5U PLC (SLMP TCP, port 15000)
- [x] **`simulation/camera_sim.py`** — Fake camera service (JSON TCP, port 16000)
- [x] **`simulation/shopfloor_sim.py`** — Fake MES REST API (port 9090)

### Launcher & Tooling
- [x] **`launcher.py`** — PySide6 desktop GUI: Start/Stop services, log viewer, settings editor
- [x] **`headless_runner.py`** — CLI process manager for dev/CI
- [x] **`test_sn5434.py`** — End-to-end integration test
- [x] **`Makefile`** — Unified command interface (start, stop, test, check-api, install)

### Documentation
- [x] **`ARCHITECTURE.md`** — Full architecture, tech stack, schema, protocol
- [x] **`docs/reference/DATABASE_SCHEMA.md`** — Detailed PostgreSQL schema: 7 tables + triggers + NOTIFY channels
- [x] **`docs/reference/WORKFLOWS.md`** — Sequence diagram of inspection lifecycle
- [x] **`docs/deployment/PRODUCTION_DEPLOYMENT_ARCHITECTURE.md`** — Production build plan
- [x] **`docs/deployment/REAL_HARDWARE_INTEGRATION.md`** — Real hardware integration guide
- [x] **Module READMEs** — `machine_control/`, `ntust_aoi_pcb_db/`, `NTUST-AOI-UI/`, `simulation/`

---

## In Progress / To Do

### Real Hardware Integration
- [ ] **Real Camera SDK** — Replace `simulation/camera_sim.py` with real SDK service (IDS/Basler) implementing JSON-over-TCP interface of `camera_tcp.py`
- [ ] **Connect Real FX5U PLC** — Test `pc_controller.py` with physical PLC at real IP (currently only tested with simulator)
- [ ] **Calibration** — Measure and calibrate `fov_step_mm` and `margin_mm` with real camera and XY table

### AI Inference Integration
- [ ] **AI Server interface** — AI machine needs to implement `PUT /images/{id}` with `{"condition": "PASS"/"FAIL"}` after running inference
- [ ] **Connect Real NAS/MinIO** — Configure `MINIO_ENDPOINT` pointing to real NAS server, test `sync_to_server.py`

### Production Build (Deployment)
> See details: [`docs/deployment/PRODUCTION_DEPLOYMENT_ARCHITECTURE.md`](docs/deployment/PRODUCTION_DEPLOYMENT_ARCHITECTURE.md)

- [x] **Phase 1: Remove Docker** — Install native PostgreSQL on Windows IPC, remove docker-compose dependency
- [ ] **Phase 2: Build Core Engine** — PyInstaller build `api/main.py` + `pc_controller.py` into `.exe`
- [ ] **Phase 3: Windows Services** — Use NSSM to register `.exe` as Windows Services (auto-start)
- [ ] **Phase 4: Engineer Tool** — Refactor `launcher.py` → `AOI_ConfigTool.exe` (Stop/Restart services + Log viewer + Settings)
- [ ] **Phase 5: Operator Dashboard** — Electron build React UI into `AOI_Dashboard.exe`

### Tech Debt
- [ ] **Extract `simulation/shared_protocol.py`** — Currently a manual copy. Consider using symlink or shared package to avoid drift
- [ ] **Identify disabled steps in `launcher.py`** — `monitor` card is commented out, needs re-evaluation
- [ ] **`/services/status` endpoint** — Uses `wmic` (Windows-only), needs refactoring for cross-platform or clear Windows-only documentation

---

## Changelog

| Date | Changes |
|---|---|
| 2026-07-06 | Removed Docker dependencies (docker-compose) to support native macOS and Windows execution |
| 2026-07-05 | Translated `PROGRESS.md` into English |
| 2026-07-05 | Created `ARCHITECTURE.md`, `DATABASE_SCHEMA.md`, `PROGRESS.md`, `Makefile`, 4 module READMEs |
| 2026-07-05 | Restructured `docs/` into `deployment/` and `reference/`, removed 3 outdated files |
| 2026-07-05 | Shortened `AGENTS.md` to a 60-line landing page based on Principle 2 |
| 2026-07-03 | Created `docs/deployment/PRODUCTION_DEPLOYMENT_ARCHITECTURE.md` (Docker-free production architecture) |
| 2026-07-03 | Updated `AGENTS.md` with conda env rules, removed superpowers |
