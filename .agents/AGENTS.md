# AI Agent Rules for NTUST AOI Project

Hello fellow AI Agent! When you are spawned into this repository, please read these rules before taking any action. This will save your context window tokens and prevent you from breaking the delicate hardware-software interactions.

## 0. Prerequisite Skills (Superpowers & Agency Agents)
**CRITICAL:** This repository relies on advanced AI skills (like `agency-technical-writer`, `agency-backend-architect`, `superpowers`, etc.) from the `agency-agents` repository.
- Check if you have these skills loaded in your `<skills>` block.
- If you do NOT have them, immediately inform the user and suggest they run the following command to download them to their global config:
  `git clone https://github.com/msitarzewski/agency-agents ~/.gemini/config/skills/agency-agents`
  `git clone https://github.com/obra/superpowers ~/.gemini/config/skills/superpowers`
- **Important:** When the user downloads the `agency-agents` repo, it contains over 200 agents. However, the AI will automatically read the `.agents/skills.json` file in this workspace to aggressively filter out the irrelevant ones. The AI on the new machine will NOT crash from token limits!
- Once installed, you will have the superpower framework to handle complex, multi-agent tasks.

## 1. Project Architecture (Token Saver)
Instead of searching the entire workspace, here is where everything lives:
- **`NTUST-AOI-UI/`**: The React/Vite frontend. It uses TailwindCSS and WebSocket hooks to receive real-time database updates.
- **`ntust_aoi_pcb_db/`**: The FastAPI Backend and PostgreSQL database configurations.
  - `api/main.py`: The FastAPI server. **Do NOT modify database records manually here**, use the `DatabaseManager`.
  - `docker-compose.yml`: Spawns Postgres (port 5433 mapped to 5432 internally).
- **`machine_control/`**: The core logic running on the industrial PC.
  - `pc_controller.py`: The brain. It connects to the PLC and the cameras. It POSTs images directly to the FastAPI backend.
  - `recipe.py`: Generates the dynamic inspection grid (Rows x Cols) based on physical PCB dimensions.
- **`simulation/`**: Mock environments for testing without hardware.
  - `plc_sim.py`: Simulates the FX5U PLC via SLMP.
  - `shopfloor_sim.py`: Simulates the factory MES API.

## 2. Core Architectural Rules (CRITICAL)

### Do Not Break the Async/Sync Boundaries
- The FastAPI backend is highly asynchronous.
- The `pc_controller.py` uses blocking threads for the PLC (SLMP protocol) because industrial hardware requires strict sequential execution. **Do not refactor `pc_controller.py` into `asyncio`** unless explicitly requested, as it will break the SLMP timing.

### Hardware Communication (SLMP)
- Communication with the Mitsubishi PLC is done via SLMP (MC Protocol).
- The PLC relies on a strict Event/Sequence/ACK pattern. If the PC receives an Event (e.g., `POSITION_REACHED`), it **MUST** respond with an `ACK` matching the sequence number, or the PLC will halt forever. See `machine_control/shared_protocol.py` before modifying any PLC logic.

### Database Operations
- We no longer use physical file watchers (`folder_monitor.py` is deprecated).
- Images are captured by `pc_controller.py` and sent directly via `requests.post()` to `FASTAPI_URL` (`http://127.0.0.1:8000/images/`).
- Do NOT hardcode API URLs. Always use `os.environ.get("FASTAPI_URL")`.

## 3. Automation and Testing
- To start the entire ecosystem locally without the PySide6 Desktop GUI, run:
  ```bash
  python headless_runner.py start
  ```
- To shut down the ecosystem and clean up Docker/Python processes, run:
  ```bash
  python headless_runner.py stop
  ```
- Use these commands to spin up the environment before running a `browser_subagent` to test the React UI.
