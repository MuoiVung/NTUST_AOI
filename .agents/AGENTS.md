# AI Agent Rules for NTUST AOI Project

Hello fellow AI Agent! When you are spawned into this repository, please read these rules before taking any action. This will save your context window tokens and prevent you from breaking the delicate hardware-software interactions.

## 0. Environment Setup & Dependency Management (CRITICAL)

When you first interact with this codebase or need to run Python scripts, you MUST use the `aoi_env` conda environment.

- **Activating the Environment**: Always ensure you are running scripts within the conda environment. Run `conda activate aoi_env` before executing any Python files.
- **Installing Dependencies**: If you need to install new libraries or update existing ones, do so ONLY inside the `aoi_env` environment (e.g., `conda install <package>` or `pip install <package>` while the environment is active). Do not install dependencies globally.
- **Creating the Environment (If missing)**: If the environment doesn't exist, create it using Python 3.10+: `conda create -n aoi_env python=3.10 -y` and then activate it to install requirements from `ntust_aoi_pcb_db/requirements.txt` or `requirements.txt`.

## 1. Project Architecture & Module Structure

The project is split into distinct modules to separate hardware logic from the web interface.

### `NTUST-AOI-UI/` (Frontend)
- **Tech Stack**: React 19, Vite, TypeScript, Recharts.
- **Purpose**: The Real-time React Dashboard for operators. It uses WebSockets/HTTP polling to receive database updates.
- **Key Files**:
  - `package.json`: Contains Vite and React dependencies.
  - `src/App.tsx` (or similar): Main dashboard layout.

### `ntust_aoi_pcb_db/` (Backend & Database)
- **Tech Stack**: Python 3.10+, FastAPI, Uvicorn, PostgreSQL, Docker.
- **Purpose**: Central data storage and API gateway. Receives images from the machine and serves them to the UI.
- **Key Files**:
  - `api/main.py`: The FastAPI server. **Do NOT modify database records manually here**, use the appropriate DatabaseManager.
  - `docker-compose.yml`: Spawns PostgreSQL (port 5433 mapped to 5432 internally).
  - `requirements.txt`: Backend dependencies (`fastapi`, `psycopg2-binary`, `pydantic`).

### `machine_control/` (Hardware Integration)
- **Tech Stack**: Python (Strictly Sync/Blocking).
- **Purpose**: The core logic running on the industrial PC. Connects to the Mitsubishi FX5U PLC and cameras.
- **Key Files**:
  - `pc_controller.py`: The brain. POSTs images directly to the FastAPI backend.
  - `recipe.py`: Generates the dynamic inspection grid (Rows x Cols) based on physical PCB dimensions.
  - `shared_protocol.py`: Defines the SLMP communication sequences.

### `simulation/` (Mock Environments)
- **Tech Stack**: Python, FastAPI.
- **Purpose**: Allows software testing without physical industrial hardware.
- **Key Files**:
  - `plc_sim.py`: Simulates the Mitsubishi FX5U PLC via SLMP. Listens on port 15000.
  - `shopfloor_sim.py`: Simulates the factory MES API. Runs on port 9090.

---

## 2. Core Architectural Rules (CRITICAL)

### Do Not Break the Async/Sync Boundaries
- The FastAPI backend (`ntust_aoi_pcb_db/`) is highly asynchronous. Use `async def` and `await`.
- The `pc_controller.py` uses blocking threads for the PLC (SLMP protocol) because industrial hardware requires strict sequential execution. **Do not refactor `pc_controller.py` into `asyncio`** unless explicitly requested, as it will break the SLMP timing.

### Hardware Communication (SLMP)
- Communication with the Mitsubishi PLC is done via SLMP (MC Protocol).
- The PLC relies on a strict Event/Sequence/ACK pattern. If the PC receives an Event (e.g., `POSITION_REACHED`), it **MUST** respond with an `ACK` matching the sequence number, or the PLC will halt forever. Read `machine_control/shared_protocol.py` before modifying any PLC logic.

### Database Operations
- Images are captured by `pc_controller.py` and sent directly via `requests.post()` to `FASTAPI_URL` (typically `http://127.0.0.1:8000/images/`).
- Do NOT hardcode API URLs. Always use `os.environ.get("FASTAPI_URL")`.

---

## 3. Automation, Testing, and Run Commands

The system relies on a unified runner script to manage all microservices.

### Running the Entire System (Headless)
To start the entire ecosystem locally without the PySide6 Desktop GUI (spins up Docker DB, FastAPI, React UI, and Simulators):
```bash
python headless_runner.py start
```

### Shutting Down the System
To shut down the ecosystem and cleanly kill all Docker/Python/Node processes:
```bash
python headless_runner.py stop
```

### Running the Integration Test
We have automated test scripts in the root directory. To run an end-to-end integration test (after starting the system):
```bash
python test_sn5434.py
```
*(This triggers a simulated scan of a PCB and runs it through the full inspection cycle).*

### Testing the UI via AI
Use the `headless_runner.py start` command to spin up the environment *before* running a `browser_subagent` to test the React UI on `http://localhost:3001`.
