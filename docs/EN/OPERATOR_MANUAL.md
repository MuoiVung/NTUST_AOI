# 👥 1. Operator Manual (User Guide)
> **Target Audience:** Factory Inspection Operators  
> **Topic Phase:** Complete outline and draft structure of themes for next week's manual submission.

---

## Theme 1: System Startup and Shutdown Procedures

### 📌 Objective & Scope:
This section provides clear, visual, step-by-step instructions on how to safely start the AOI inspection station and shut it down to prevent any data loss or filesystem corruption.

### 📋 Content Outline & Key Drafts:
*   **Station Boot-up (Startup Workflow):**
    *   *Step 1:* Switch on the power supply of the AAEON Industrial Panel PC (IPC).
        
        ![Step 1: Powering on the IPC](path/to/step1_power.png)
        
    *   *Step 2:* Once the OS loads, double-click the **`AOI_Launcher`** shortcut icon on the Windows Desktop. This opens the AOI Control Panel (Launcher GUI) in an idle state.
        
        ![Step 2: Double-click Launcher Shortcut](path/to/step2_desktop.png)
        
    *   *Step 3:* On the Launcher Control Panel window, click the big **`▶ Start All Services`** button. The launcher will automatically start Docker containers (PostgreSQL & Nginx), activate the backend server, boot up the folder monitoring worker, and configure the sync client.
        
        ![Step 3: Clicking Start All Services](path/to/step3_launcher_start.png)
        
    *   *Step 4:* Once all service status indicators turn **Green (✔ Running)**, the system will automatically launch the web browser and open the AOI Web Console at `http://localhost:3001`. Verify that the dashboard displays "Database Connected".
        
        ![Step 4: AOI Web Dashboard](path/to/step4_web_dashboard.png)

*   **Station Power-down (Safe Shutdown):**
    *   *Step 1:* Ensure there are no active PCB scans running on the conveyor belt and wait for any ongoing image writes to finish.
        
        ![Step 1: Idle Dashboard Screen](path/to/shutdown_step1.png)
        
    *   *Step 2:* Open or focus the Desktop Launcher window, and click the **`⏹ Close Services`** button. This gracefully terminates all active python processes, stops the UI server, and runs a safe Docker shutdown (`docker compose down`) to safely flush data buffers and stop the database.
        
        ![Step 2: Clicking Close Services](path/to/shutdown_step2.png)
        
    *   *Step 3:* Wait for the launcher window to close automatically (about 1.5 seconds), then safely shut down the Windows operating system. 
        
        **⚠️ CRITICAL WARNING:** Never switch off the IPC main power supply directly while services are active. Doing so will bypass the graceful shutdown of the PostgreSQL daemon and can cause database file corruption!

---

## Theme 2: PCB Barcode Scanning and Recipe Dispatch

### 📌 Objective & Scope:
Guides the operator on how to scan incoming PCB serial numbers, select work orders, and understand how the system automatically queries and applies scanning parameters (Recipe).

### 📋 Content Outline & Key Drafts:
*   **Scanning the PCB Serial Number:**
    *   As a PCB enters the conveyor belt at the AOI station, use the fixed or hand-held barcode scanner to read the barcode/QR code on the board.
    *   The system registers this S/N (`serial_number`) in the active database under a new inspection run (`run_number`).
*   **Recipe Retrieval & Dispatch (Data-driven Mechanism):**
    *   The system automatically checks the scanned board ID against the `board_numbers` table.
    *   It retrieves the exact grid dimensions: `grid_rows` and `grid_cols` (e.g., a $5\times 5$ or $7\times 7$ grid layout).
    *   This grid recipe is sent to the PLC registers. The operator does not need to manually configure the PLC toolpath coordinates for new board types.
*   **Fallback Procedure (Manual Input):**
    *   In case the barcode sticker is damaged or the scanner fails, the operator can click "Manual Input" on the Web Dashboard, select the target Order Code and Board Number from a secure dropdown menu, and hit "Confirm" to proceed.

---

## Theme 3: Dual-Camera Real-time Monitoring and Inspection Verification

### 📌 Objective & Scope:
Explains how the operator monitors the visual inspection grid during scanning and registers quality verification.

### 📋 Content Outline & Key Drafts:
*   **Real-time Scanning Grid:**
    *   The Dashboard displays a live grid matching the active PCB layout. As the axis moves, the grid tiles update in real-time.
    *   The dual cameras (Top & Bottom) trigger simultaneously, capture images, and register them instantly in the `images` database table.
*   **Visual Defect Indication:**
    *   **Green Tile Outline (PASS):** Image patch successfully passed the AI inference check.
    *   **Red Tile Outline (FAIL):** Image patch marked as a potential defect (misalignment, missing component, solder bridge).
*   **Manual Operator Verification (QC Override):**
    *   If a tile is flagged as `FAIL` (Red), the operator can click on that specific grid tile to view a high-resolution magnification.
    *   If it is a false alarm (False Positive), the operator clicks the "QC Override - PASS" button. This updates the database record `condition = 'PASS'` for that image tile, allowing the board to bypass the rework station.

---

## Theme 4: Operator Troubleshooting Guide

### 📌 Objective & Scope:
Provides immediate, simple troubleshooting procedures for factory operators when facing standard hardware or software blocks.

### 📋 Content Outline & Key Drafts:
*   **Issue 1: Barcode Scanner unresponsive:**
    *   *Troubleshooting:* Check the USB connection, wipe the scanner window clean, and check the Dashboard status bar for scanner COM port errors.
*   **Issue 2: Grid tiles do not render or images are missing:**
    *   *Troubleshooting:* Check if the Nginx image proxy service is active by verifying `http://localhost:8080` is reachable. Restart the Nginx service via the Dashboard control panel if needed.
*   **Issue 3: Camera fails to trigger at coordinate stop:**
    *   *Troubleshooting:* Verify PLC serial communication state and ensure camera SDK is connected (Continuous Capture Worker active).
