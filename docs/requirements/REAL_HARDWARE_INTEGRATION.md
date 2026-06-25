# Real Hardware Integration Guide

This document outlines the exact steps and code modifications required to transition the NTUST_AOI system from the current simulated environment to a production environment using a real Mitsubishi PLC and an IDS Industrial Camera.

## 1. PLC Integration (Mitsubishi SLMP)

The SLMP protocol (MC Protocol 3E) is already fully implemented and verified. Moving to real hardware only requires network configuration changes.

**Action Items:**
1. Connect the PC and the Mitsubishi FX5U PLC to the same local network.
2. In the PLC parameters (GX Works3), configure an Ethernet port to accept SLMP TCP connections on a specific port (e.g., `5000`).
3. Modify the startup configuration in the PC (e.g., via `.env` or `launcher.py`) to point to the real PLC's IP address instead of `127.0.0.1:15000`.
   - *No changes to `shared_protocol.py` are required as the memory addressing rules remain identical.*

## 2. Camera Integration (IDS uEye / Peak)

The system currently uses a mock class (`RealCameraSDK`) that copies fake images. This must be replaced with the actual camera manufacturer's SDK bindings (e.g., `ids_peak` or `pyueye` for Python).

**Action Items:**
1. **Dependencies:** Install the IDS Peak Python bindings or equivalent OpenCV bindings (`pip install ids_peak ids_peak_ipl` or `opencv-python`).
2. **Modify `RealCameraSDK` in `machine_control/pc_controller.py`:**
   - **`__init__()` & `start()`:** Initialize the IDS DeviceManager, find the connected camera, and open a data stream. Configure settings like Exposure, Gain, and PixelFormat.
   - **`save_latest()`:** Remove the `shutil.copy2` mockup logic. Replace it with a command to acquire the latest image buffer from the camera stream, convert it to a NumPy array, and save it to the provided `filepath` (e.g., using `cv2.imwrite(filepath, image_array)`).
   - **`stop()`:** Ensure the device stream is cleanly closed and memory is freed to prevent locking issues on restart.
3. **Trigger Synchronization:** Decide whether the camera uses a **Software Trigger** (PC sends a command over USB/GigE) or a **Hardware Trigger** (PLC sends an electrical pulse directly to the camera's GPIO). If using Software Trigger, the `save_latest()` function must explicitly send the trigger command.

## 3. Factory MES API Integration

The system currently bypasses external network calls by using a mock data fixture to determine PCB dimensions.

**Action Items:**
1. In `machine_control/pc_controller.py` (or through a `.env` variable), change the initialization of the `SerialTestApiClient` from `api_mode="fixture"` to `api_mode="http"`.
2. Provide the actual factory MES API Endpoint URL to the client.
3. If the factory API requires authentication (e.g., Bearer Token, API Key), modify `serialtest_api_client.py` to include the necessary HTTP headers in the `requests.get()` call.

## 4. Vision/AI Core Integration (Defect Detection)

Currently, the `folder_monitor.py` script detects new images and immediately inserts them into the database with a default condition of `UNKNOWN` or `PASS`.

**Action Items:**
1. **AI Processing Pipeline:** Integrate your Deep Learning models (e.g., YOLO, ResNet) or OpenCV heuristic algorithms directly into `folder_monitor.py` (or as a separate microservice).
2. **Database Update:** Before `folder_monitor.py` executes `insert_image_record()`, pass the `file_path` to the AI Engine. 
3. Based on the AI Engine's output, dynamically set the `condition` variable to `'PASS'` or `'FAIL'`, and save bounding box metadata if defects are found.
