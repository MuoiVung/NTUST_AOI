---
title: '第六章:檔案儲存database, Peter, Vincent'
tags: [Documentation]

---

# Technical SOP & Manual: AOI Database Management System

## Document Control

| Field | Entry |
|---|---|
| Document title | Technical SOP & Manual: AOI Database Management System |
| System | PC Vision Database + IDS Camera Sync + MinIO Storage |
| Intended users | Factory Operators, Database Administrators, System Maintainers |
| Version | Draft v1.0 |
| Date | May 22, 2026 |
| Prepared by | IIOT Lab NTUST |
| Approved by | Project Lead |

---

## 1. Purpose

This document provides a single, comprehensive Standard Operating Procedure (SOP) and Technical Manual for the Automated Optical Inspection (AOI) Database System. It integrates both the daily **Operator Manual (User Guide)** for factory floor personnel and the technical **Maintenance & Administrator Manual** for database administrators and system engineers.

Consolidating these manuals into a single file allows for seamless printing to PDF, offline distribution, and unified version control.

---

## 2. System Overview & Architecture

The AOI database system acts as the central datastore for PCB inspection runs and dual-camera captures on the industrial PC (IPC).

*   **Database Engine:** PostgreSQL running inside a Docker container (`aoi_postgres`), exposing port `5433` mapping to `5432` internally.
*   **Database Schema:** A high-performance 2-table schema (`runs` and `images`) designed to keep grid load latency under 50ms.
*   **Image Storage Replication:** Captured images are saved to a local folder and mirrored immediately to long-term server storage (`D:\AOI_Images`) via a background MinIO client daemon.
*   **Image Web Server:** An Nginx container (`aoi_image_server`) serving static images on port `8080` for HMI web browser rendering.

---

## 3. Operator Manual (User Guide)

This section guides factory floor operators on starting, running, and shutting down the inspection system, as well as handling basic HMI errors.

### 3.1 System Startup and Shutdown Procedures

#### Station Boot-up (Startup Workflow)
1.  **Switch on IPC:** Power on the AAEON Industrial Panel PC (IPC).
2.  **Open Launcher:** Double-click the **`AOI_Launcher`** shortcut icon on the Windows Desktop.
    *   *Visual Reference:* The AOI Control Panel window will open in an idle state.
        
3.  **Start All Services:** Click the **`▶ Start All Services`** button. The launcher will automatically:
    *   Start Docker containers (`aoi_postgres` on `5433`, `aoi_image_server` on `8080`, and `aoi_pgadmin` on `5050`).
    *   Activate the backend server.
    *   Initialize the sync client (`mc.exe`).
                ![image](https://hackmd.io/_uploads/HyzKtFZlGx.png)

4.  **Verify Web HMI:** Once all service indicators turn **Green (✔ Running)**, the browser will open the Web Console at `http://localhost:3001`. Confirm the dashboard shows "Database Connected".
    ![848af4b9-73b8-4388-a88d-61340018ea28](https://hackmd.io/_uploads/H1_zcY-xGe.jpg)


    

#### Station Power-down (Safe Shutdown)
1.  **Wait for Scan Completion:** Ensure there are no active conveyor scans and wait for all camera image writes to finish.
2.  **Close Services:** Click the **`⏹ Close Services`** button on the Launcher. This gracefully stops all python daemons and runs a safe Docker shutdown (`docker compose down`) to flush database write buffers.
   
    ![9b39f897-16c8-41bb-9e3b-1a53288731cd](https://hackmd.io/_uploads/ryn19FZlMg.jpg)


3.  **Shut Down Windows:** After the launcher closes (about 1.5 seconds), safely shut down the Windows OS.
4.  **⚠️ CRITICAL WARNING:** Never switch off the IPC main power supply directly while services are active. Bypassing the PostgreSQL shutdown routine can corrupt database files!

---

### 3.2 PCB Barcode Scanning and Recipe Dispatch

#### Scanning the PCB Serial Number
*   When a PCB enters the conveyor, use the barcode scanner to scan the board's barcode/QR code.
*   The scanner sends the scanned ID to the database, creating a new inspection run (`run_code`) under the active `run_number`.

#### Recipe Retrieval & Dispatch
*   The system automatically queries the scanned board ID against the database recipes.
*   It retrieves the exact grid dimensions (e.g., a $5\times 5$ or $7\times 7$ grid layout).
*   This grid recipe is sent to the PLC registers, automating toolpath coordinates without manual input.

#### Fallback Procedure (Manual Input)
*   If the barcode is damaged, the operator clicks **"Manual Input"** on the Dashboard, selects the Order Code and Board Number from the dropdowns, and clicks **"Confirm"** to dispatch the run.

---

### 3.3 Dual-Camera Real-time Monitoring and Inspection Verification

#### Real-time Scanning Grid
*   The Dashboard displays a live grid matching the active PCB layout. As the axes move, grid tiles update in real-time.
*   Dual cameras (Top & Bottom) trigger simultaneously, capture images, and register them instantly in the `images` database table.

#### Visual Defect Indication
*   **Green Tile Outline (PASS):** Image block successfully passed the AI inference check.
*   **Red Tile Outline (FAIL):** Image block is marked as a potential defect (misalignment, missing component, solder bridge).

#### Manual Operator Verification (QC Override)
*   For `FAIL` (Red) tiles, the operator clicks the tile to view a high-resolution magnification.
*   If it is a false positive, the operator clicks the **"QC Override - PASS"** button. This updates the database record (`condition = 'PASS'`), allowing the PCB to bypass the rework station.

---

### 3.4 Operator Troubleshooting Guide

*   **Issue 1: Barcode Scanner unresponsive:**
    *   *Troubleshooting:* Check the USB connection, wipe the scanner window clean, and check the Dashboard status bar for scanner COM port errors.
*   **Issue 2: Grid tiles do not render or images are missing:**
    *   *Troubleshooting:* Check if the Nginx image proxy service is active by verifying `http://localhost:8080` is reachable. Restart Nginx via the Dashboard control panel if needed.
*   **Issue 3: Camera fails to trigger at coordinate stop:**
    *   *Troubleshooting:* Verify PLC serial communication state and ensure camera SDK is connected (Continuous Capture Worker active).

---

## 4. Maintenance & Administrator Manual (Active Setup)

This section provides systems administrators and database developers with advanced guides for deploying, backing up, and troubleshooting the active factory floor environment.

### 4.1 Database Deployment and Local Network Configuration

#### Dockerized Architecture
The database and static server environment are managed via Docker Compose. The `docker-compose.yml` file is located at `ntust_aoi_pcb_db/` and manages:
1.  **PostgreSQL 15+ (`aoi_postgres`):** Runs on host port `5433`, mapped internally to `5432`. Persistent data is stored in the host volume `./postgres_data`.
2.  **pgAdmin 4 (`aoi_pgadmin`):** Web administration interface running on port `5050`.
3.  **Nginx Alpine (`aoi_image_server`):** Hosts static camera captures in `./images` on port `8080`.

#### Environment Configuration (`.env`)
Ensure the `.env` file generated from `.env.example` contains:
```bash
DB_ROOT_USER=admin
DB_ROOT_PASSWORD=your_secure_password
DB_PGADMIN_PASSWORD=pgadmin_web_password
```

#### Static Local IP Peering
The IPC is bound to a static local IP (e.g., `192.168.40.21`). External camera ingestion triggers or remote AI processing machines can connect directly to the database via standard PostgreSQL adapters at:
`postgresql://admin:your_secure_password@192.168.40.21:5433/pcb_aoi_db`

---

### 4.2 Relational Schema Design and Indexing Optimization

The active production database consists of a simplified **2-Table model** to achieve maximum query speed and low serialization latency.

#### 1. Table: `runs`
Holds metadata representing an entire PCB inspection run.
*   `run_code` (VARCHAR(50), PRIMARY KEY): The unique identifier format (combines date, board code, side, and run index).
*   `machine_id` (VARCHAR(50), NOT NULL): The IPC identification key.
*   `board_code` (VARCHAR(20), NOT NULL): The model name of the PCB under inspection.
*   `date_str` (CHAR(8), NOT NULL): Capture date in `YYYYMMDD` format.
*   `side` (VARCHAR(10)): Scan face (`T` for Top, `B` for Bottom).
*   `illumination` (VARCHAR(20)): Light source profile name.
*   `status` (VARCHAR(20), DEFAULT 'COMPLETED'): Inspection status trace.
*   `note` (TEXT): Diagnostic comments or operator notes.
*   `start_time` (TIMESTAMP): Scan startup timestamp.
*   `created_at` (TIMESTAMP): Record creation log.

#### 2. Table: `images`
Holds metadata cataloging each individual segmented photo captured by the camera worker.
*   `image_id` (UUID, PRIMARY KEY, DEFAULT `uuid_generate_v4()`): Unique image identification key.
*   `run_code` (VARCHAR(50), NOT NULL, FOREIGN KEY): Links to the active `runs.run_code` with `ON DELETE CASCADE`.
*   `file_path` (TEXT, NOT NULL): The location of the saved image file on the disk/server.
*   `row_idx` (INTEGER): Row coordinate index of the image block.
*   `col_idx` (INTEGER): Column coordinate index of the image block.
*   `condition` (VARCHAR(10)): AI evaluation result (`PASS` or `FAIL`).
*   `note` (TEXT): Specific override comments if applicable.
*   `capture_time` (TIMESTAMP): Time image was captured.
*   `file_name` (VARCHAR(255)): Original image file name on disk.
*   `file_size_bytes` (BIGINT): File storage size.
*   `checksum` (VARCHAR(64)): MD5/SHA checksum for integrity validation.

#### Active Indexes
To keep query lookup times beneath $50\text{ms}$ when loading inspection grids of millions of records, the following indexes are actively configured:
*   `idx_runs_date` on `runs(date_str)` - Optimizes calendar-based search queries on the dashboard.
*   `idx_runs_board_date` on `runs(board_code, date_str DESC)` - Speeds up board history trends queries.
*   `idx_images_run_code` on `images(run_code)` - Essential for HMI/Dashboard grid rendering.
*   `idx_images_condition` on `images(condition)` - Speeds up quick filtering of defects.

---

### 4.3 MinIO Object Storage and Real-time Mirroring Client

Captured images are backed up and synchronized in real-time to a secure repository.

```mermaid
graph LR
    A["Camera SDK / IPC Local folder"] -->|Saves PNGs| B["aoi_client/aoi-images/"]
    B -->|"Real-time mc.exe mirror --watch"| C["aoi_server MinIO Object Storage"]
    C -->|Maps physically to| D["D:\AOI_Images on Server"]
```

#### MinIO Server Deployment (`aoi_server`)
*   Managed by `01_Run_Server.bat` which starts the local storage engine `minio.exe`.
*   Sets credentials: User: `aoi_admin` / Password: `aoi@1234`.
*   Host IP binding: `192.168.40.21` (API Port: `9000`, Console Web UI: `9001`).
*   Physical storage mapping: Maps data to the server directory `D:\AOI_Images`.

#### MinIO Client Configuration (`aoi_client`)
*   Managed by `02_Run_Client.bat` on the camera PC.
*   Registers connections alias on startup:
    ```bash
    mc.exe alias set lab_cloud http://192.168.40.21:9000 aoi_admin aoi@1234
    ```
*   Runs the continuous mirroring task in watchdog mode:
    ```bash
    mc.exe mirror --watch --exclude "*.exe" --exclude "*.bat" .\aoi-images\ lab_cloud/aoi-images
    ```

#### ⚠️ Operational Issues Checklist (Current Active Setup)
*   **Issue 5.1: Network Connection Lost / Timeout to Lab Cloud:**
    *   *Symptom:* The client terminal logs connection timed out or failed to reach `http://192.168.40.21:9000`. Captured images remain only on the local machine.
    *   *Recovery Action Checklist:*
        1. Open the CMD terminal on the client PC and ping the server: `ping 192.168.40.21`.
        2. Verify if the Server PC is powered on and `01_Run_Server.bat` is running.
        3. Check firewall configurations on port `9000` and `9001` on both machines.
*   **Issue 5.2: Mirroring Client Process Exits / Terminated Silently:**
    *   *Symptom:* Network is online, but new images saved in `.\aoi-images\` are not showing up in pgAdmin or MinIO console. The CMD prompt `AOI IMAGE SYNC SYSTEM` has closed.
    *   *Recovery Action Checklist:*
        1. Go to the Windows Desktop, locate the `aoi_client` folder, and double-click `02_Run_Client.bat`.
        2. Verify that the window launches, displays `[+] CONNECTION ESTABLISHED!`, and stays open.
        3. Check the Windows Event Viewer to see if the process was terminated by antivirus or system memory manager limits.
*   **Issue 5.3: MinIO Bucket Access / Credentials Change lockout:**
    *   *Symptom:* The client script launches but logs access denied errors when attempting to execute `mc.exe alias` or mirror writes.
    *   *Recovery Action Checklist:*
        1. Verify that the passwords in the `.bat` file on both client and server are identical (`aoi@1234`).
        2. Open a web browser on the IPC and navigate to `http://192.168.40.21:9001`. Try logging in with the administrative GUI credentials to verify credentials manually.
        3. Run `mc.exe alias list` in the client directory to check the configured targets.

---

### 4.4 DB Backup, Restoration and Performance Benchmarks

#### Docker PostgreSQL Backup
To perform a secure backup of the schema and all relational data rows inside the running Docker container:
```bash
docker exec -t aoi_postgres pg_dump -U admin -d pcb_aoi_db > aoi_db_backup.sql
```

#### Database Restoration
To restore a previously backed up `.sql` dump into a fresh database instance:
```bash
cat aoi_db_backup.sql | docker exec -i aoi_postgres psql -U admin -d pcb_aoi_db
```

#### Performance Benchmarking
The workspace includes a dedicated performance benchmarker at `ntust_aoi_pcb_db/scripts/benchmark_runner.py`. Admin can measure maximum throughput via separate tests:
- *Ingestion benchmark:* `python benchmark_runner.py --mode ingest` (evaluates maximum write limits per second).
- *Read latency benchmark:* `python benchmark_runner.py --mode read` (evaluates indexing capacity under bulk requests).
- *HTML report generator:* `python generate_html_report.py` (packages results into readable charts `benchmark_report.html`).

---

### 4.5 Advanced Database Operational Troubleshooting & Factory Recovery

#### ⚠️ Scenario 4.5.1: PCB Scan / Re-run Primary Key Conflict
*   **Issue Description:**
    A PCB scan is interrupted midway (e.g. camera offline, conveyor jam, physical vibration). The operator clears the conveyor and attempts to re-scan the exact same board. The HMI Dashboard displays a **`400 Bad Request` / "Run code already exists"** or database throws primary key constraint violations on `runs.run_code`.
*   **Recovery Action Checklist:**
    *   `[ ]` **Option A: Safe Barcode Versioning Suffix (Recommended):**
        *   Rather than deleting old database records, instruct the HMI to append a revision suffix to the scanned ID (e.g., `Board_101` -> `Board_101_v2` or `Board_101_retry_1`).
        *   Start the scan. The backend registers it as a new run, preserving the historical failed inspection for quality control audits.
    *   `[ ]` **Option B: Clean-Slate Purge (Override):**
        *   If a total overwrite is required: Send a `DELETE` request to the backend endpoint `/runs/{run_code}`.
        *   Confirm that the cascading database foreign key deletes all associated records in the `images` table automatically.
        *   Clean out the physical folder `captures/{board_name}/{side}/` to remove partial image files and avoid storage remnants.
        *   Re-insert the board and execute the scan. The database will accept the original code.

#### ⚠️ Scenario 4.5.2: Database Startup Lockout after Sudden Factory Power Failure
*   **Issue Description:**
    A sudden factory blackout or direct IPC hardware shutdown (bypassing OS shutdown routine) leaves PostgreSQL in an unreleased lock state. Upon rebooting, the Dashboard shows "Database Offline" and the `aoi_postgres` Docker container crashes repeatedly in a loop.
*   **Recovery Action Checklist:**
    *   `[ ]` **Check container status:** Run `docker ps -a` and check if the database container is stuck in restarting loop.
    *   `[ ]` **Inspect logs:** Run `docker logs aoi_postgres` and look for the fatal message:
        `FATAL: lock file "postmaster.pid" already exists`
    *   `[ ]` **Stop services:** Run `docker-compose down` to stop all daemon processes safely.
    *   `[ ]` **Locate data volume:** Navigate to the local host directory at:
        `c:\Users\Peter\OneDrive - 國立臺灣科技大學\Documents\NTUST\AOI\ntust_aoi_pcb_db\postgres_data\`
    *   `[ ]` **Delete lock file:** Search for the file named `postmaster.pid`. Delete this file completely. (This orphan lock file prevents PostgreSQL from acquiring a writing handle on database files).
    *   `[ ]` **Reboot services:** Start the containers:
        `docker-compose up -d`
    *   `[ ]` **Verify recovery:** Monitor container health: `docker logs -f aoi_postgres`. Confirm that the database engine initiates automatic crash recovery and displays:
        `database system is ready to accept connections`

#### ⚠️ Scenario 4.5.3: Database Connection Pool Exhaustion under High-Throughput Scans
*   **Issue Description:**
    During high-speed dual-camera scans, the backend API begins throwing `HTTP 500` errors, and the SQLAlchemy logs output:
    `TimeoutError: QueuePool limit of size 5 overflow 10 reached`
*   **Recovery Action Checklist:**
    *   `[ ]` **Increase SQLAlchemy Pool Size:** Update database connection parameters in backend engine creator scripts to support high concurrency peaks:
        ```python
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            pool_size=20,          # Increase connection threshold
            max_overflow=10,       # Allow burst overrides
            pool_timeout=30        # Seconds to wait before throwing timeout
        )
        ```
    *   `[ ]` **Audit Database Session Lifecycle:** Ensure all FastAPI route controllers utilize safe dependency generator yields, forcing connections back to the pool immediately upon request completion:
        ```python
        def get_db():
            db = SessionLocal()
            try:
                yield db
            finally:
                db.close() # Return connection handle back to Pool
        ```
    *   `[ ]` **Perform Connection Status Query:** Execute an admin query inside pgAdmin to monitor active connections:
        ```sql
        SELECT count(*), state FROM pg_stat_activity GROUP BY state;
        ```

---

## 5. Maintenance & Administrator Manual (In Progress / Roadmap Drafts)

This section outlines the high-level roadmap and engineering designs for planned future features currently under development.

### 5.1 [ROADMAP DRAFT] Data Lifecycle and Automated SSD Storage Cleanup
*   **Archiving Architecture:**
    *   The system is planned to monitor a `local_retention_period` configuration (e.g. set to `30` days).
    *   A background daemon script will select all images older than the retention period, compress them, and upload them to a centralized long-term object storage.
    *   Upon receiving an upload success verification token, the local daemon will update the database (`is_uploaded_longterm = true`, clear local paths, and trigger OS commands to delete local SSD files safely).
*   **⚠️ Operational Issues Checklist (Future Roadmap):**
    *   **Issue 3.1: SSD Partition Saturation due to Sync Daemon Lockups:**
        *   *Symptom:* The cleanup service crashes or gets locked behind a file access exception, causing the local SSD to hit 100% capacity and halting the camera capture software.
        *   *High-Level Action Checklist:*
            1. Access the IPC system monitor and verify the sync service is running.
            2. Verify database connection state to ensure it is not blocked by a connection timeout.
            3. Force a manual disk purge of the oldest cached directories if emergency space is needed.
    *   **Issue 3.2: Network Timeout during Remote Archiving Sync:**
        *   *Symptom:* Large raw image files fail to sync because the link bandwidth drops, filling up the transfer queue.
        *   *High-Level Action Checklist:*
            1. Verify network latency (ping test to remote archiving gateway).
            2. Tune upload timeout settings in the sync configuration file.
            3. Trigger a bulk resume command to push pending queues during idle shifts.
    *   **Issue 3.3: Image Corruptions / Checksum Validation Failures:**
        *   *Symptom:* The daemon detects that a transferred image has a different SHA/MD5 checksum on the server, causing it to block local file deletion.
        *   *High-Level Action Checklist:*
            1. Locate the specific corrupted image path logged in the service console.
            2. Perform a force re-upload of the original local source image.
            3. Do not run any delete commands until the server checksum matches the local database record.

---

### 5.2 [ROADMAP DRAFT] Real-time Folder Watchdog Ingestion
*   **Watchdog Architecture:**
    *   A lightweight Python background service utilizing the `watchdog` library is designed to monitor raw capture folders on the IPC.
    *   When the camera SDK writes an image block (`on_created` event), the script intercepts it, parses the filename parameters (e.g. `R2_C3_Top.png` -> row index 2, column index 3), and executes direct SQL insertions via a connection pool.
*   **⚠️ Operational Issues Checklist (Future Roadmap):**
    *   **Issue 4.1: Watchdog Service Fails to Startup automatically on IPC Boot:**
        *   *Symptom:* Cameras are scanning and saving files locally, but the Web Dashboard displays empty grids with no images registered.
        *   *High-Level Action Checklist:*
            1. Open Windows Service Manager (`services.msc`) or check Startup folders to verify if the watcher script was loaded.
            2. Manually launch the startup batch script (`run_watchdog.bat`) and check the terminal console for environment path errors.
    *   **Issue 4.2: File Access Denied / Partial File Ingestion:**
        *   *Symptom:* The watchdog triggers too fast, attempting to read and calculate the checksum of an image while the Camera SDK is still writing it to disk.
        *   *High-Level Action Checklist:*
            1. Ensure the script configuration has a settled delay parameter (typically `0.3` to `0.5` seconds) before opening the file handle.
            2. Enable file read/write locks in Python to wait for system release.
    *   **Issue 4.3: Database Write Queue Saturation:**
        *   *Symptom:* High-speed camera triggers cause high-frequency SQL insert queries, causing Postgres to throw transaction bottlenecks.
        *   *High-Level Action Checklist:*
            1. Implement multi-row batch inserts (`INSERT INTO images ... VALUES ...`) instead of single query insertions.
            2. Configure a local memory queue (e.g. using `queue.Queue` or a Redis broker) to buffer file metadata ingestion.

---

### 5.3 [ROADMAP DRAFT] Future 5-Table Schema Roadmap
To support large-scale enterprise tracing and multiple production lines, the database is planned to expand into a **5-Table normalized relational structure**:
1.  **`orders` table:** Tracks production quota batches, orders metadata, and factory run lines.
2.  **`board_numbers` table:** Acts as a central digital recipe database, storing board models, total row/column grid layouts, and preset PLC toolpath coordinates.
3.  **`runs` table:** Tracks metadata logs of inspection runs, linked to active orders and board numbers.
4.  **`images` table:** Catelogs camera captures with strict relational cascading.
5.  **`system_configs` table:** Holds global variables (such as local retention periods and cloud syncing variables).
