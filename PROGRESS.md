## Phần đã hoàn thành

### Hệ thống cốt lõi

- [x] **`machine_control/pc_controller.py`** — State machine hoàn chỉnh: PLC handshake, recipe download, step loop (SLMP), camera trigger (JSON/TCP), DB write, error log
- [x] **`machine_control/shared_protocol.py`** — SLMP 3E Binary TCP client, D-register map, tất cả EventCode/AckStatus/ErrorCode enum
- [x] **`machine_control/camera_tcp.py`** — JSON-over-TCP camera client protocol
- [x] **`machine_control/database_pg.py`** — psycopg2 adapter cho machine-side DB writes
- [x] **`machine_control/recipe.py`** — Tính toán XY grid từ kích thước PCB (rows × cols)
- [x] **`machine_control/serialtest_api_client.py`** — HTTP client MES API (fixture + real mode)

### Backend & Database

- [x] **`ntust_aoi_pcb_db/api/main.py`** — FastAPI đầy đủ: REST endpoints, WebSocket, PG NOTIFY listener
- [x] **`ntust_aoi_pcb_db/sql/init.sql`** — PostgreSQL schema: 7 bảng + indexes + trigger `increment_order_quantity`
- [x] **`ntust_aoi_pcb_db/docker-compose.yml`** — PostgreSQL 18, pgAdmin 4, Nginx image server
- [x] **`ntust_aoi_pcb_db/scripts/sync_to_server.py`** — Background sync images lên MinIO/NAS
- [x] **Real-time WebSocket pipeline** — Camera → FastAPI → PG NOTIFY → WebSocket → React UI

### Frontend (Operator Dashboard)

- [x] **`NTUST-AOI-UI/components/OperatorDashboard.tsx`** — Main HMI panel đầy đủ chức năng
- [x] **`NTUST-AOI-UI/components/ImageViewer.tsx`** — Real-time WebSocket image stream
- [x] **`NTUST-AOI-UI/components/RunList.tsx`** — Lịch sử inspection runs có phân trang
- [x] **`NTUST-AOI-UI/components/RunGallery.tsx`** — Image grid cho từng run
- [x] **`NTUST-AOI-UI/components/Dashboard.tsx`** — Metrics + Recharts charts
- [x] **`NTUST-AOI-UI/components/NewInspection.tsx`** — Form bắt đầu inspection mới
- [x] **`NTUST-AOI-UI/components/Settings.tsx`** — System config UI

### Simulators (Dev/Test)

- [x] **`simulation/plc_sim.py`** — Fake Mitsubishi FX5U PLC (SLMP TCP, port 15000)
- [x] **`simulation/camera_sim.py`** — Fake camera service (JSON TCP, port 16000)
- [x] **`simulation/shopfloor_sim.py`** — Fake MES REST API (port 9090)

### Launcher & Tooling

- [x] **`launcher.py`** — PySide6 desktop GUI: Start/Stop services, log viewer, settings editor
- [x] **`headless_runner.py`** — CLI process manager cho dev/CI
- [x] **`test_sn5434.py`** — End-to-end integration test
- [x] **`Makefile`** — Unified command interface (start, stop, test, check-api, install)

### Documentation

- [x] **`ARCHITECTURE.md`** — Toàn bộ kiến trúc, tech stack, schema, protocol
- [x] **`docs/reference/DATABASE_SCHEMA.md`** — PostgreSQL schema chi tiết 7 bảng + triggers + NOTIFY channels
- [x] **`docs/reference/WORKFLOWS.md`** — Sequence diagram vòng đời inspection
- [x] **`docs/deployment/PRODUCTION_DEPLOYMENT_ARCHITECTURE.md`** — Kế hoạch build production
- [x] **`docs/deployment/REAL_HARDWARE_INTEGRATION.md`** — Hướng dẫn tích hợp phần cứng thật
- [x] **Module READMEs** — `machine_control/`, `ntust_aoi_pcb_db/`, `NTUST-AOI-UI/`, `simulation/`

---

## Đang làm / Cần làm

### Tích hợp phần cứng thật (Hardware Integration)

- [ ] **Camera SDK thật** — Thay `simulation/camera_sim.py` bằng service SDK thật (IDS/Basler) implement JSON-over-TCP interface của `camera_tcp.py`
- [ ] **Kết nối PLC FX5U thật** — Test `pc_controller.py` với PLC vật lý ở IP thật (hiện tại chỉ test với simulator)
- [ ] **Calibration** — Đo và chuẩn hóa `fov_step_mm` và `margin_mm` với camera và bàn XY thật

### AI Inference Integration

- [ ] **AI Server interface** — Máy AI cần implement `PUT /images/{id}` với `{"condition": "PASS"/"FAIL"}` sau khi chạy inference
- [ ] **Kết nối NAS/MinIO thật** — Cấu hình `MINIO_ENDPOINT` trỏ đến server NAS thật, test `sync_to_server.py`

### Production Build (Deployment)

> Xem chi tiết: [`docs/deployment/PRODUCTION_DEPLOYMENT_ARCHITECTURE.md`](docs/deployment/PRODUCTION_DEPLOYMENT_ARCHITECTURE.md)

- [ ] **Phase 1: Remove Docker** — Cài PostgreSQL native trên IPC Windows, xóa docker-compose dependency
- [ ] **Phase 2: Build Core Engine** — PyInstaller build `api/main.py` + `pc_controller.py` thành `.exe`
- [ ] **Phase 3: Windows Services** — Dùng NSSM đăng ký `.exe` làm Windows Services (auto-start)
- [ ] **Phase 4: Engineer Tool** — Refactor `launcher.py` → `AOI_ConfigTool.exe` (Stop/Restart services + Log viewer + Settings)
- [ ] **Phase 5: Operator Dashboard** — Electron build React UI thành `AOI_Dashboard.exe`

### Cải thiện kỹ thuật (Tech Debt)

- [ ] **Tách `simulation/shared_protocol.py`** — Hiện tại là file copy thủ công. Xem xét dùng symlink hoặc shared package để tránh drift
- [ ] **`launcher.py` bước nào đang disable** — `monitor` card đang bị comment, cần đánh giá lại
- [ ] **`/services/status` endpoint** — Dùng `wmic` (Windows-only), cần refactor cho cross-platform hoặc ghi chú rõ Windows-only

---

## Lịch sử thay đổi

| Ngày | Thay đổi |
|---|---|
| 2026-07-05 | Tạo `ARCHITECTURE.md`, `DATABASE_SCHEMA.md`, `PROGRESS.md`, `Makefile`, 4 module READMEs |
| 2026-07-05 | Tái cấu trúc `docs/` thành `deployment/` và `reference/`, xóa 3 file outdated |
| 2026-07-05 | Rút gọn `AGENTS.md` thành landing page 60 dòng theo Principle 2 |
| 2026-07-03 | Tạo `docs/deployment/PRODUCTION_DEPLOYMENT_ARCHITECTURE.md` (kiến trúc production Docker-free) |
| 2026-07-03 | Cập nhật `AGENTS.md` với conda env rules, xóa superpowers |
