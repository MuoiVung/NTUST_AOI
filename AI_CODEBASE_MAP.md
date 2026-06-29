# AI Codebase Map

This file serves as a high-level map of the repository structure. It is designed to help AI Assistants quickly index the project without needing to grep through hundreds of files.

## Project Root: `/`
- `headless_runner.py`: The entry point for starting/stopping the entire system without a GUI. Use this for automated tests.
- `launcher.py`: The entry point for humans. It launches a PySide6 Desktop Dashboard.
- `README.md`: Human-facing setup instructions.

## The Core Logic: `/machine_control`
This folder contains the software that runs on the industrial PC physically connected to the machine.
- `pc_controller.py`: The central orchestrator. It manages the state machine, talks to the PLC, triggers the cameras, and pushes data to the backend.
- `recipe.py`: Contains the mathematical logic to calculate the XY grid path based on the circuit board's dimensions.
- `shared_protocol.py`: Defines the exact memory addresses (Registers) and Event Codes used to communicate with the Mitsubishi FX5U PLC over SLMP.
- `camera.py`: The SDK wrapper for triggering the physical Top and Bottom cameras.

## The Database & Backend: `/ntust_aoi_pcb_db`
This folder contains the system's memory and external API.
- `api/main.py`: A FastAPI application. It provides HTTP endpoints for the UI (React) and the Machine (PC Controller). It also manages WebSockets to push real-time updates to the UI when a new image is saved.
- `scripts/pg_adapter.py`: A wrapper around `psycopg2` that handles direct PostgreSQL database queries.
- `docker-compose.yml`: Provisions the `pcb_aoi_db` PostgreSQL container and PGAdmin.

## The Frontend: `/NTUST-AOI-UI`
The dashboard used by operators.
- `components/`: Contains React UI components.
  - `ImageViewer.tsx`: Receives WebSocket events and displays the high-res camera images in real-time.
  - `MachineStatus.tsx`: Displays the current state of the PLC (Connected/Error).
- `src/App.tsx`: The main React Router and layout wrapper.

## Testing & Mocks: `/simulation`
Tools used to test the system without physical hardware.
- `plc_sim.py`: A simulated FX5U PLC. It mimics the SLMP memory registers and fakes the physical movement of the XY table.
- `shopfloor_sim.py`: A mock MES (Manufacturing Execution System). It returns fake PCB dimensions when given a barcode (e.g., `SN24_TEST`).

## Documentation: `/docs`
Human-readable documentation.
- `EN/WORKFLOWS.md`: Plain-English sequences explaining how the components interact (Initialization, Scanning, Taking Photos).
- `requirements/REAL_HARDWARE_INTEGRATION.md`: Step-by-step guide for deploying this code onto the real factory floor.
