# Real Hardware Integration Guide (Deployment Guide)

This document provides step-by-step instructions for migrating the NTUST AOI system from a simulated environment to real hardware. This includes integrating the **Mitsubishi FX5U PLC**, the **Dual Camera System**, and the **Factory Network (MES/Shopfloor)**.

## Step 1: Network Infrastructure Preparation

The AOI system requires the PC Controller and all hardware devices to be on the same Local Area Network (LAN).

1. **Set a Static IP for the Workstation (PC Controller):**
   - Open network settings on the PC and assign a static IPv4 address. Example: `192.168.3.10`.
   - Subnet Mask: `255.255.255.0`.
2. **Verify PLC FX5U Connection:**
   - Connect an Ethernet cable from the FX5U's RJ45 port to the PC (or via a Network Switch).
   - Ensure the PLC's IP is statically set via GX Works3 (Example: `192.168.3.250`).
   - Open a Terminal on the PC and run: `ping 192.168.3.250`. Ensure there is a successful reply.
3. **Open the SLMP Port on the FX5U:**
   - In GX Works3 -> Ethernet Configuration.
   - Add a new **SLMP Connection (TCP)**.
   - Set the Port to `15000` (or your configured port; the source code defaults to 15000).

## Step 2: PC Controller Software Configuration

You must disable "Simulation Mode" and enable "Real Mode" by configuring environment variables and startup parameters.

1. **Configure the `.env` file:**
   Open the `.env` file (or `ntust_aoi_pcb_db/.env`) and set the following:
   ```env
   # Point the Database API to the running backend (usually localhost)
   FASTAPI_URL=http://127.0.0.1:8000
   
   # Point the Shopfloor API to the real factory MES server
   SHOPFLOOR_API_URL=http://<MES_SERVER_IP>/ashx/WebAPI/Board/SerialTest/HandlerGetSerialInfo.ashx
   ```

2. **Configure Camera Mode (`machine_control/pc_controller.py`):**
   Ensure the `--camera-mode real` flag is passed to the `pc_controller.py` script. The system expects a dual-camera setup. Verify that the necessary Camera SDK Drivers are properly installed on the host OS.

## Step 3: System Startup

Instead of clicking through individual scripts, use the `headless_runner.py` utility for a clean startup.

1. **Disable the PLC Simulator:**
   **DO NOT** run `plc_sim.py`.
   *(If you are using `headless_runner.py start`, edit the script and comment out the line that starts `plc_sim.py`).*

2. **Start the Machine Logic:**
   Open a Terminal and run the command to connect to the real PLC:
   ```bash
   cd machine_control
   python pc_controller.py --mode semi-auto --api-mode real --camera-mode real --plc-host 192.168.3.250 --plc-port 15000 --api-endpoint http://<MES_SERVER_IP>/...
   ```
   *(If you are using `launcher.py`, click the **Settings** button on the top right and enter the real PLC IP `192.168.3.250` in the configuration box).*

3. **Start the UI and Database:**
   If using `launcher.py`, click **Start All** (except the PLC Sim).
   The Backend System (Port 8000) and Frontend (Port 3001) will be ready to ingest images.

## Step 4: Dry-Run and Verification Procedure

Once the system is booted, follow these steps to isolate any potential issues:

### 4.1. Handshake Verification
- **PC Terminal Log:** The `pc_controller.py` terminal must log: `[PC] connected to PLC at 192.168.3.250:15000`.
- **Operator Dashboard (React UI):** The PLC status indicator must turn green and display **"CONNECTED"**. If it shows an error, verify that the SLMP port in GX Works3 is open and the ethernet cable is secured.

### 4.2. Shopfloor (MES) Verification
- Scan a real barcode (S/N) into the React UI.
- Check the `pc_controller.py` terminal to ensure the API successfully retrieved the board dimensions (e.g., `200x150 mm`). If it returns a 404/500 error, verify the network routing to the factory's MES server.

### 4.3. Camera Verification (1-Step Dry-Run)
- Place a sample PCB on the XY Table.
- The PLC will execute the `SEMI_AUTO_RUN` command. When the XY table stops at the first coordinate, you should hear the camera trigger mechanism.
- Observe the React UI. The captured image should instantly populate on the screen. If it does, the full pipeline (Hardware -> PC -> DB -> WebSocket) is functioning perfectly!

### Troubleshooting Guide
- **PLC Timeout:** Check the Sequence Event Queue. If the PLC does not receive a `PC_ACK` response, it will stall the execution loop. Ensure `pc_controller.py` is running and has not crashed.
- **Images Not Appearing on UI:** Check the FastAPI backend logs (`uvicorn`) to verify if the POST request from `pc_controller.py` was received. If not, double-check the `FASTAPI_URL` environment variable configuration.
