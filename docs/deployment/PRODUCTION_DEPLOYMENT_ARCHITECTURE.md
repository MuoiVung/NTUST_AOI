# NTUST AOI - Target Production Deployment Architecture

> **Target Audience:** AI Agents & Deployment Engineers performing the final production packaging for the Industrial PC (IPC).

## 1. Architectural Overview & Philosophy

The AOI machine operates in an industrial environment requiring high stability, zero-dependency execution for operators, and ease of maintenance for engineers. 

To achieve this, the system transitions from a "Development Mode" (using raw Python scripts, Venv, and Docker) to a **"Production Mode" (Docker-free, Standalone Executables, and Windows Services)**.

### Core Architectural Decisions:
1. **Docker-Free IPC:** Docker Desktop on Windows IPCs consumes excess RAM, requires virtualization (Hyper-V), and can interfere with real-time PLC networking. PostgreSQL must be installed as a **Native Windows Service** via its standard `.exe` installer.
2. **Distributed Cloud/NAS:** The AOI machine does NOT run MinIO locally. It pushes images to an external NAS/MinIO server and interacts with a separate AI inference server over the LAN.
3. **Background Core (Windows Services):** The API Backend (`main.py`) and the PLC Hardware Controller (`pc_controller.py`) are compiled into `.exe` files and run purely in the background automatically upon Windows boot.
4. **Dual-Interface System:** The system provides two distinct user interfaces tailored to specific roles (Operator vs. Engineer).

---

## 2. Component Specifications

### 2.1 The Core Engine (Background Services)
- **Compilation:** Use `PyInstaller` (or `Nuitka`) to compile `ntust_aoi_pcb_db/api/main.py` and `machine_control/pc_controller.py` into standalone executables.
- **Service Registration:** Use a tool like **NSSM (Non-Sucking Service Manager)** to register these `.exe` files as Windows Services:
  - `AOI_API_Service` (Port 8000)
  - `AOI_PLC_Service`
- **Logging:** All `stdout` and `stderr` must be redirected to physical text files (e.g., `C:\AOI_System\logs\system.log`) using Python's `logging` module with timed rotating file handlers.

### 2.2 The Operator Dashboard (`AOI_Dashboard.exe`)
- **Purpose:** Human-Machine Interface (HMI) for the factory floor operator.
- **Technology:** React 19 built statically (`npm run build`) and wrapped in **Electron**.
- **Behavior:**
  - Launches in Full-Screen / Kiosk Mode.
  - Automatically connects to `ws://localhost:8000` to stream images.
  - Hides all complex logs and terminal windows.

### 2.3 The Engineer Config Tool (`AOI_ConfigTool.exe`)
- **Purpose:** Diagnostic and maintenance tool for system engineers.
- **Technology:** PySide6 (Refactored from the current `launcher.py`).
- **Behavior:**
  - **Service Management:** Replaces the internal `QProcess` Python calls with `subprocess.run(["net", "start", "AOI_API_Service"])` to start/stop the background Windows Services.
  - **Log Viewer:** Tails the text files in `C:\AOI_System\logs\` to display real-time system logs.
  - **Environment Settings:** Provides a GUI to edit the `.env` file (e.g., NAS IP, PLC Port).

---

## 3. Step-by-Step Execution Plan for AI Agents

When an AI Agent is tasked with migrating this repository to Production Mode, it should follow these exact phases:

### Phase 1: Database Migration
1. Remove all dependencies on `docker-compose.yml`.
2. Document instructions for the human engineer to install Native PostgreSQL 16+.
3. Update database connection strings in the `.env` file to point to `localhost:5432` natively.

### Phase 2: Core Engine Packaging
1. Write a build script (`build_core.bat`) that runs PyInstaller on `main.py` and `pc_controller.py`.
2. Write an installation script (`install_services.bat`) using `nssm.exe` to install the generated executables as Windows Services. Ensure `nssm` is configured to set the working directory correctly so the `.env` file is loaded.

### Phase 3: Config Tool Refactoring
1. Modify `launcher.py`:
   - Remove `QProcess` executions of Python scripts.
   - Change the "Start All" and "Stop All" buttons to execute `net start / net stop` on the registered Windows Services.
   - Change the Log Tabs to read from the physical log text files instead of `stdout`.
2. Compile `launcher.py` into `AOI_ConfigTool.exe` using PyInstaller.

### Phase 4: Operator Dashboard Packaging
1. Create a `main.js` script for Electron in the `NTUST-AOI-UI` directory.
2. Configure `package.json` to build the React app and then package it using `electron-builder`.
3. Output the final `AOI_Dashboard.exe` setup file.

### Phase 5: Final Directory Structure
The resulting deployment folder (copied to the IPC) should look like this:
```text
C:\AOI_System\
├── core\
│   ├── AOI_API.exe
│   ├── AOI_Controller.exe
│   └── .env
├── UI\
│   └── AOI_Dashboard.exe (Electron App)
├── Tools\
│   └── AOI_ConfigTool.exe (PySide6 App)
├── logs\
│   └── (Auto-generated log files)
└── install_services.bat
```

> **Note to AI:** Do not refactor `pc_controller.py` into `asyncio` during this process. Maintain the strict synchronous logic required for the SLMP protocol.
