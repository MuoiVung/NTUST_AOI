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
    *   *Step 2:* Once the OS loads, double-click the `AOI_Launcher` shortcut on the Desktop. This triggers a batch script that automatically initializes the PostgreSQL database and Nginx static image server containers in background daemon mode.
    *   *Step 3:* Verify that the HMI control interface loads in the browser at `http://localhost:3001` with a green indicator status showing "Database Connected".
*   **Station Power-down (Safe Shutdown):**
    *   *Step 1:* Close any open board inspections and wait for active write processes to complete.
    *   *Step 2:* Click the `⏹ Shutdown Services` button on the Desktop Launcher GUI (or run the safe shutdown batch script). This calls `docker-compose down` to gracefully flush transaction buffers to the disk and stop the PostgreSQL daemon.
    *   *Step 3:* Safely shut down the operating system. **CRITICAL WARNING:** Turning off the IPC power switch directly without running this shutdown workflow may cause data block corruption in PostgreSQL.

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
    *   In case the barcode sticker is damaged or the scanner fails, the operator can click "Manual Input" on the HMI, select the target Order Code and Board Number from a secure dropdown menu, and hit "Confirm" to proceed.

---

## Theme 3: Dual-Camera Real-time Monitoring and Inspection Verification

### 📌 Objective & Scope:
Explains how the operator monitors the visual inspection grid during scanning and registers quality verification.

### 📋 Content Outline & Key Drafts:
*   **Real-time Scanning Grid:**
    *   The HMI displays a live grid matching the active PCB layout. As the axis moves, the grid tiles update in real-time.
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
    *   *Troubleshooting:* Check the USB connection, wipe the scanner window clean, and check the HMI status bar for scanner COM port errors.
*   **Issue 2: Grid tiles do not render or images are missing:**
    *   *Troubleshooting:* Check if the Nginx image proxy service is active by verifying `http://localhost:8080` is reachable. Restart the Nginx service via the HMI control panel if needed.
*   **Issue 3: Camera fails to trigger at coordinate stop:**
    *   *Troubleshooting:* Verify PLC serial communication state and ensure camera SDK is connected (Continuous Capture Worker active).
