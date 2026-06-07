---
title: '第五章:相機模組camera, Marnel'
tags: [Documentation]

---

# End-User SOP: Vision-Based Component Capture System

## Document Control

| Field | Entry |
|---|---|
| Document title | End-User SOP: Vision-Based Component Capture System |
| System | PC Vision System + Mitsubishi FX5U PLC |
| Intended users | Operators, technicians, process engineers |
| Version | Draft v1.1 |
| Date | 2026-05-25 |
| Prepared by | Marnel Altius |
| Approved by | To be assigned |


---

## 0. Revision History

| Version | Date | Description | Author |
|---|---|---|---|
| Draft v1.1 | 2026-05-25 | Initial end-user SOP draft | Marnel Altius |


---




## 1. Purpose

This SOP explains how an end user should operate the vision-based component capture system.

The system uses:

- A PC-based vision program
- An IDS camera
- A Mitsubishi FX5U PLC
- Motion hardware controlled by the PLC
- Image capture and file saving controlled by the PC

The system has two operating modes:

| Mode | Use Case | Summary |
|---|---|---|
| Manual Mode | Setup, testing, teaching, troubleshooting | The operator issues each instruction from the PC. |
| Semi-Auto Mode | Normal structured scanning | The PLC controls the motion sequence, while the PC authorizes and performs image capture. |

---

## 2. Important Safety Rules

1. Do not place hands, tools, samples, cables, or loose objects inside the machine movement area during operation.
2. Do not bypass guards, interlocks, emergency stops, PLC safety logic, or software warnings.
3. Do not operate the system if the camera, PLC, motion stage, lighting, or PC software is behaving abnormally.
4. Use Manual Mode only for setup, testing, inspection, and recovery operations.
5. Use Semi-Auto Mode for normal scanning after setup is complete.
6. Stop the run immediately if unexpected motion, incorrect positioning, camera failure, or abnormal lighting is observed.
7. Only reset faults after the cause has been checked and corrected.
8. The PLC controls machine motion and safety. The PC requests actions and captures images, but it does not directly control raw machine outputs.

---

## 3. User Responsibilities

### Operator

The operator is responsible for:

- Preparing the machine area
- Starting the PC vision software
- Entering board or sample information
- Selecting Manual Mode or Semi-Auto Mode
- Monitoring system status
- Confirming image capture results
- Stopping the system if unsafe or abnormal behavior occurs

### Technician / Engineer

The technician or engineer is responsible for:

- PLC setup
- Camera setup
- Calibration
- Network configuration
- Motion parameter adjustment
- Troubleshooting persistent faults
- Updating approved recipes or scan paths

---

## 4. System Overview

The PC and PLC work together during operation.

```text
PC Vision System
    - Operator interface
    - Camera control
    - Image capture
    - Image saving
    - Capture authorization

PLC
    - Machine safety
    - Motion control
    - Homing
    - Positioning
    - Sequence execution
    - Alarm handling
```

In normal operation:

```text
PLC moves the machine.
PC confirms camera readiness.
PC captures and saves images.
PLC waits for capture completion before continuing.
```

---

## 5. Operating Modes


![ChatGPT Image May 18, 2026, 04_42_07 PM](https://hackmd.io/_uploads/Byp3f8OJze.jpg)

![image](https://hackmd.io/_uploads/r1pwR8-xzl.png)


## 5.1 Manual Mode

Manual Mode is used when the operator wants to control the process step by step from the PC.

Use Manual Mode for:

- Initial setup
- Camera test shots
- Teaching or checking positions
- Single-position capture
- Troubleshooting
- Recovery after an error

In Manual Mode:

```text
The PC tells the PLC what action to perform.
The PLC checks safety and executes the action.
The PC captures an image only when instructed.
```

The PLC does not automatically advance through a scan sequence in Manual Mode.

---

## 5.2 Semi-Auto Mode

Semi-Auto Mode is used for normal scanning.

Use Semi-Auto Mode when:

- The machine is already set up
- The scan path or sequence is ready
- Camera and lighting are stable
- Board/sample metadata has been entered
- The operator is ready to run a structured scan

In Semi-Auto Mode:

```text
The PLC controls the scan sequence.
The PC monitors the PLC.
The PLC requests permission before image capture.
The PC authorizes capture, captures the image, and confirms completion.
The PLC continues to the next step only after capture is complete.
```

---

## 6. Pre-Operation Checklist

Complete this checklist before starting any run.

| Check | Required Condition | Complete |
|---|---|---|
| Machine area | Clear of tools, hands, cables, and loose parts | ☐ |
| Emergency stop | Released and functional | ☐ |
| PLC | Powered and ready | ☐ |
| PC | Powered and logged in | ☐ |
| Camera | Connected and detected | ☐ |
| Lighting | Powered and stable | ☐ |
| Motion system | No visible obstruction | ☐ |
| Sample / board | Correctly placed and secured | ☐ |
| Software | Vision program opened successfully | ☐ |
| Storage | Save location available with enough disk space | ☐ |
| Metadata | Board name, side, or sample ID available | ☐ |

Do not continue if any required condition is not satisfied.

---

## 7. Startup Procedure

1. Verify that the machine area is clear.
2. Power on the PLC and motion hardware.
3. Power on the PC.
4. Connect the camera if it is not already connected.
5. Turn on the lighting system.
6. Open the PC vision software.
7. Confirm that the camera is detected.
8. Load the approved camera settings.
9. Load the approved image pipeline settings.
10. Confirm that live image acquisition is running.
11. Confirm that the displayed image is stable and properly illuminated.
12. Connect the PC software to the PLC.
13. Wait until the system reports that the PLC is ready.
14. Select the operating mode:
    - Manual Mode for setup or testing
    - Semi-Auto Mode for normal scanning

---

## 8. Manual Mode Procedure

Use this procedure when operating the system step by step.

### 8.1 Enter Manual Mode

1. From the PC software, select **Manual Mode**.
2. Confirm that the PLC accepts the mode change.
3. Confirm that the machine is idle and safe.
4. Confirm that the live camera view is visible.

### 8.2 Manual Move

1. Enter or select the target position.
2. Press the command to request movement.
3. Wait for the PLC to confirm that the command has started.
4. Watch the machine during movement.
5. Wait for the PLC to report that the command is complete.
6. If an error occurs, stop and follow the abnormal condition procedure.

### 8.3 Manual Image Capture

1. Confirm that the machine has stopped moving.
2. Confirm that the live image is clear and stable.
3. Confirm that the correct board/sample information is entered.
4. Press the capture command.
5. Verify that the image is saved successfully.
6. Repeat the move and capture process as needed.

### 8.4 Exit Manual Mode

1. Confirm that no motion is active.
2. Return the machine to a safe position if required.
3. Select another mode or close the software according to the shutdown procedure.

---

## 9. Semi-Auto Mode Procedure

Use this procedure for normal scanning.

### 9.1 Enter Semi-Auto Mode

1. From the PC software, select **Semi-Auto Mode**.
2. Confirm that the PLC accepts the mode change.
3. Enter the required board/sample information.
4. Confirm the correct board side or sample orientation.
5. Confirm that the camera view is stable.
6. Confirm that the save folder is correct.
7. Confirm that the machine area is clear.

### 9.2 Start Semi-Auto Run

1. Press **Start Run**.
2. Monitor the PC software status.
3. Confirm that the PLC starts the run.
4. The PLC will move the machine to the next scan position.
5. When the PLC reaches a capture position, the PC will check whether image capture is allowed.

The PC should only authorize image capture if:

- The camera is running
- A fresh image frame is available
- The save folder is valid
- Board/sample metadata is entered
- The expected scan step matches the PLC step
- No operator pause is active
- No camera error is active
- No storage error is active

### 9.3 During Semi-Auto Capture

For each scan point:

1. PLC moves to the scan position.
2. PLC reports that the position has been reached.
3. PLC requests image capture authorization.
4. PC checks camera, storage, metadata, and system status.
5. If checks pass, PC authorizes capture.
6. PC captures and saves the image.
7. PC reports capture completion.
8. PLC advances to the next scan step.

### 9.4 Complete Semi-Auto Run

1. Wait until the PLC reports that the run is complete.
2. Confirm that the PC saved all required images.
3. Review the run log for errors or skipped captures.
4. Remove the board/sample only after confirming that the machine is idle.
5. Prepare the next board/sample or proceed to shutdown.

---

## 10. Pause, Stop, and Reset

## 10.1 Pause

Use **Pause** when the process should temporarily stop but no fault has occurred.

Examples:

- Operator needs to inspect the setup
- Lighting needs to stabilize
- Camera view needs to be checked
- Board/sample information needs confirmation

Procedure:

1. Press **Pause** on the PC software.
2. Wait for the system to enter a paused or idle state.
3. Do not enter the machine area unless motion has stopped and it is safe.
4. Press **Resume** only after confirming that operation can continue safely.

## 10.2 Stop

Use **Stop** when the run should be ended or interrupted.

Examples:

- Wrong board/sample loaded
- Incorrect setup detected
- Operator decides to cancel the run
- Non-emergency abnormal condition occurs

Procedure:

1. Press **Stop** on the PC software.
2. Wait for PLC confirmation that the run has stopped.
3. Check the machine state.
4. Review the log to determine where the run stopped.

## 10.3 Emergency Stop

Use the physical emergency stop if immediate machine stopping is required.

Examples:

- Unexpected motion
- Collision risk
- Person or object inside machine movement area
- Severe mechanical or electrical abnormality

Procedure:

1. Press the emergency stop.
2. Do not reset immediately.
3. Notify the responsible technician or engineer.
4. Identify and correct the cause.
5. Reset only after the area is safe and the cause is understood.

## 10.4 Reset Error

Only reset errors after the cause has been corrected.

Procedure:

1. Read the error message on the PC software.
2. Check the PLC or machine indicators if needed.
3. Correct the cause of the error.
4. Confirm that the machine area is clear.
5. Press **Reset Error**.
6. Confirm that the PLC and PC return to a ready or idle state.

---

## 11. Normal Shutdown Procedure

1. Confirm that no scan is running.
2. Confirm that the machine is idle.
3. Save or export logs if required.
4. Verify that captured images are stored in the expected folder.
5. Close the PC vision software.
6. Turn off lighting if required.
7. Power down the motion system if required.
8. Power down the PLC and PC according to local procedure.
9. Clean the work area.

---

## 12. Image Storage and File Verification

Images should be saved in a structured folder.

Example:

```text
captures/
    board_name/
        side/
            row_001/
                img_0001.png
                img_0002.png
```

After each run, verify:

- The correct board/sample folder was created
- The correct side or orientation folder was used
- Images are present for the expected scan points
- File names are sequential or match the run log
- No image files are missing or corrupted
- The run log matches the image count

---

## 13. Abnormal Conditions and Operator Response

| Condition | What It Means | Operator Action |
|---|---|---|
| Camera not detected | PC cannot access camera | Check camera cable and restart software if needed |
| No live image | Camera stream is not active | Check camera, lighting, and software status |
| Poor image quality | Lighting, focus, or settings may be incorrect | Pause and inspect image setup |
| PLC not ready | PLC is not available or not in ready state | Check PLC power/network and notify technician |
| Motion error | PLC could not complete movement | Stop operation and inspect machine |
| Safety error | Interlock or safety condition is active | Resolve safety condition before reset |
| Capture rejected | PC did not allow capture | Check camera, storage, metadata, and step status |
| Storage error | Image cannot be saved | Check disk space, folder path, and permissions |
| Communication timeout | PC and PLC lost communication | Stop operation and check network/software |
| Unexpected motion | Machine behavior is abnormal | Use emergency stop if needed |

---

## 14. Operator Decision Guide

Use **Manual Mode** when:

- You are setting up the system
- You need one test image
- You are checking a position
- You are recovering from an error
- You need controlled step-by-step operation

Use **Semi-Auto Mode** when:

- Setup is complete
- The board/sample is ready
- The scan sequence is known
- The system is stable
- You want normal structured scanning

Do not use Semi-Auto Mode if:

- The camera image is unstable
- The board/sample is not secured
- The machine area is not clear
- Metadata has not been entered
- The previous error has not been resolved

---

## 15. Run Completion Checklist

After completing a run, verify:

| Check | Complete |
|---|---|
| PLC reports run complete or stopped safely | ☐ |
| Machine is idle | ☐ |
| Images were saved in the expected folder | ☐ |
| Image count matches expected scan count | ☐ |
| Run log contains no unresolved errors | ☐ |
| Board/sample can be safely removed | ☐ |
| Work area is ready for the next run | ☐ |

---

## 16. Key Rules to Remember

```text
The PLC controls motion and safety.
The PC controls camera capture and image saving.
Manual Mode means the PC issues each high-level instruction.
Semi-Auto Mode means the PLC controls the scan sequence.
The PC must authorize and complete image capture before the PLC continues.
Do not bypass safety checks.
Do not reset faults without understanding the cause.
```

# Error Code Reference  
## Vision Capture System: PC ↔ PLC Event Communication

## 1. Purpose

This document defines the recommended error-code system for the vision capture system using PC ↔ PLC event communication.

The system includes:

- PC vision software
- Mitsubishi FX5U PLC
- MC/SLMP communication
- IDS camera acquisition
- Motion control
- Image saving and logging
- Manual Mode and Semi-Auto Mode operation

The error-code system separates:

```text
ACK status codes:
    Short accept/reject responses for event communication.

Error codes:
    Detailed fault identifiers used for diagnostics, logs, PLC events, and operator messages.
```

---

## 2. Error Code Structure

Use a 4-digit numeric code:

```text
XYYY
```

Where the first digit identifies the error category.

| Range | Category |
|---:|---|
| `0000` | No error / OK |
| `1000-1999` | PC / software errors |
| `2000-2999` | PLC / state-machine errors |
| `3000-3999` | Communication / MC-SLMP errors |
| `4000-4999` | Camera / image acquisition errors |
| `5000-5999` | Image saving / storage errors |
| `6000-6999` | Motion / positioning errors |
| `7000-7999` | Safety / interlock errors |
| `8000-8999` | Operator / workflow errors |
| `9000-9999` | Reserved / unknown / fatal errors |

---

## 3. ACK Status Codes

ACK status codes are used in:

```text
D111 = PLC acknowledgement status for PC → PLC event
D211 = PC acknowledgement status for PLC → PC event
```

| Code | Symbol | Meaning |
|---:|---|---|
| `0` | `ACK_OK` | Accepted / OK |
| `1` | `ACK_REJECTED` | Rejected |
| `2` | `ACK_BUSY` | Receiver is busy |
| `3` | `ACK_INVALID_STATE` | Event not allowed in current state |
| `4` | `ACK_INVALID_PAYLOAD` | Payload data is invalid |
| `5` | `ACK_SAFETY_NOT_OK` | Safety condition prevents action |
| `6` | `ACK_TIMEOUT` | Timeout occurred |
| `7` | `ACK_DUPLICATE_SEQUENCE` | Duplicate event sequence number |
| `8` | `ACK_UNKNOWN_EVENT` | Event type is not recognized |

---

## 4. Error Codes

## 4.1 0000: No Error

| Code | Symbol | Meaning |
|---:|---|---|
| `0000` | `ERR_NONE` | No error |
| `0001` | `WARN_NONE` | No active warning |

---

## 4.2 1000-1999: PC / Software Errors

| Code | Symbol | Meaning | Typical Action |
|---:|---|---|---|
| `1001` | `ERR_PC_NOT_READY` | PC software is not ready | Restart or complete startup |
| `1002` | `ERR_PC_INVALID_MODE` | PC selected invalid mode | Select Manual or Semi-Auto |
| `1003` | `ERR_PC_INTERNAL_EXCEPTION` | Unhandled PC software exception | Check logs, restart software |
| `1004` | `ERR_PC_CONFIG_MISSING` | Required configuration file missing | Load correct config |
| `1005` | `ERR_PC_CONFIG_INVALID` | Configuration file invalid | Check settings file |
| `1006` | `ERR_PC_OPERATOR_ABORT` | Operator aborted operation | Confirm safe stop |
| `1007` | `ERR_PC_PAUSED` | PC is paused | Resume or stop |
| `1008` | `ERR_PC_SEQUENCE_MISMATCH` | PC expected step differs from PLC step | Stop and inspect event log |
| `1009` | `ERR_PC_METADATA_MISSING` | Board/sample metadata missing | Enter board name/side/sample ID |
| `1010` | `ERR_PC_MODE_SWITCH_NOT_ALLOWED` | Mode switch requested while busy | Wait for idle state |

---

## 4.3 2000-2999: PLC / State-Machine Errors

| Code | Symbol | Meaning | Typical Action |
|---:|---|---|---|
| `2001` | `ERR_PLC_NOT_READY` | PLC is not ready | Check PLC RUN state |
| `2002` | `ERR_PLC_INVALID_STATE` | Event not allowed in current PLC state | Check mode/state |
| `2003` | `ERR_PLC_BUSY` | PLC is busy executing another action | Wait or stop current operation |
| `2004` | `ERR_PLC_UNKNOWN_EVENT` | PLC received unknown event type | Check PC event code |
| `2005` | `ERR_PLC_INVALID_PAYLOAD` | PLC received malformed event payload | Check payload mapping |
| `2006` | `ERR_PLC_SEQUENCE_DUPLICATE` | Duplicate PC sequence number | Check PC event sender |
| `2007` | `ERR_PLC_SEQUENCE_SKIPPED` | Unexpected sequence jump | Check communication reliability |
| `2008` | `ERR_PLC_MODE_NOT_SELECTED` | No valid mode selected | Select Manual or Semi-Auto |
| `2009` | `ERR_PLC_MANUAL_ONLY_EVENT` | Manual event sent outside Manual Mode | Select Manual Mode |
| `2010` | `ERR_PLC_SEMIAUTO_ONLY_EVENT` | Semi-auto event sent outside Semi-Auto Mode | Select Semi-Auto Mode |
| `2011` | `ERR_PLC_RESET_NOT_ALLOWED` | Reset rejected by PLC | Resolve fault condition first |
| `2012` | `ERR_PLC_RECIPE_NOT_LOADED` | Semi-auto recipe/step list missing | Load recipe or scan path |
| `2013` | `ERR_PLC_STEP_INDEX_INVALID` | Step index outside valid range | Check recipe/sequence |

---

## 4.4 3000-3999: Communication / MC-SLMP Errors

| Code | Symbol | Meaning | Typical Action |
|---:|---|---|---|
| `3001` | `ERR_COMM_CONNECT_FAILED` | PC failed to connect to PLC | Check IP, port, Ethernet |
| `3002` | `ERR_COMM_SOCKET_CLOSED` | TCP socket closed unexpectedly | Reconnect after safe stop |
| `3003` | `ERR_COMM_TIMEOUT` | Communication timeout | Check network and PLC state |
| `3004` | `ERR_COMM_BAD_RESPONSE` | Invalid SLMP/MC response | Check protocol/frame settings |
| `3005` | `ERR_COMM_SLMP_END_CODE` | PLC returned nonzero SLMP end code | Decode SLMP end code |
| `3006` | `ERR_COMM_WRITE_FAILED` | PC failed to write PLC registers | Check connection |
| `3007` | `ERR_COMM_READ_FAILED` | PC failed to read PLC registers | Check connection |
| `3008` | `ERR_COMM_ACK_TIMEOUT` | Sender did not receive ACK in time | Check receiver state |
| `3009` | `ERR_COMM_PLC_EVENT_TIMEOUT` | PC waited too long for PLC event | Check PLC state machine |
| `3010` | `ERR_COMM_PC_ACK_TIMEOUT` | PLC waited too long for PC ACK | Check PC software |
| `3011` | `ERR_COMM_HEARTBEAT_LOST` | Heartbeat lost | Enter safe stop/hold |
| `3012` | `ERR_COMM_WRONG_PORT` | Wrong PLC port selected | Check SLMP/MC port |
| `3013` | `ERR_COMM_WRONG_IP` | Wrong PLC IP selected | Check IP address |
| `3014` | `ERR_COMM_FIREWALL_BLOCKED` | Firewall may block connection | Allow TCP port |
| `3015` | `ERR_COMM_FRAME_MODE_MISMATCH` | Binary/ASCII frame mismatch | Match PLC and PC settings |

---

## 4.5 4000-4999: Camera / Acquisition Errors

| Code | Symbol | Meaning | Typical Action |
|---:|---|---|---|
| `4001` | `ERR_CAMERA_NOT_DETECTED` | Camera not found | Check cable/power/device manager |
| `4002` | `ERR_CAMERA_OPEN_FAILED` | PC could not open camera | Close other camera software |
| `4003` | `ERR_CAMERA_ALREADY_IN_USE` | Camera used by another program | Close IDS peak cockpit/other app |
| `4004` | `ERR_CAMERA_SETTINGS_MISSING` | Camera `.cset` missing | Load correct settings file |
| `4005` | `ERR_CAMERA_SETTINGS_LOAD_FAILED` | Failed to load camera settings | Check file/path |
| `4006` | `ERR_CAMERA_PIPELINE_MISSING` | Pipeline JSON missing | Load approved pipeline config |
| `4007` | `ERR_CAMERA_PIPELINE_LOAD_FAILED` | Failed to load pipeline settings | Check JSON validity |
| `4008` | `ERR_CAMERA_ACQUISITION_NOT_RUNNING` | Acquisition is stopped | Restart acquisition |
| `4009` | `ERR_CAMERA_FRAME_TIMEOUT` | No frame received in time | Check camera/USB/GigE/load |
| `4010` | `ERR_CAMERA_FRAME_INCOMPLETE` | Frame received incomplete | Check bandwidth/cable |
| `4011` | `ERR_CAMERA_STALE_FRAME` | Latest frame too old | Restart acquisition |
| `4012` | `ERR_CAMERA_PROCESSING_FAILED` | Pipeline processing failed | Check pixel format/settings |
| `4013` | `ERR_CAMERA_BRIGHTNESS_UNSTABLE` | Auto brightness not stable | Wait/discard frames |
| `4014` | `ERR_CAMERA_FOCUS_BAD` | Image focus unacceptable | Adjust focus |
| `4015` | `ERR_CAMERA_LIGHTING_BAD` | Lighting unstable or insufficient | Check lighting |

---

## 4.6 5000-5999: Image Saving / Storage Errors

| Code | Symbol | Meaning | Typical Action |
|---:|---|---|---|
| `5001` | `ERR_STORAGE_PATH_MISSING` | Save path not set | Select save folder |
| `5002` | `ERR_STORAGE_PATH_INVALID` | Save path invalid | Correct folder path |
| `5003` | `ERR_STORAGE_PERMISSION_DENIED` | PC cannot write to folder | Check permissions |
| `5004` | `ERR_STORAGE_DISK_FULL` | Not enough disk space | Free space or change drive |
| `5005` | `ERR_STORAGE_FILENAME_INVALID` | Invalid board/sample/file name | Remove invalid characters |
| `5006` | `ERR_IMAGE_SAVE_FAILED` | Image write failed | Check path/camera/image object |
| `5007` | `ERR_IMAGE_VERIFY_FAILED` | Saved image could not be verified | Re-capture image |
| `5008` | `ERR_IMAGE_INDEX_DUPLICATE` | Image index already exists | Check indexing/logging |
| `5009` | `ERR_LOG_CREATE_FAILED` | Could not create log file | Check permissions |
| `5010` | `ERR_LOG_WRITE_FAILED` | Could not write event log | Check disk/path |

---

## 4.7 6000-6999: Motion / Positioning Errors

| Code | Symbol | Meaning | Typical Action |
|---:|---|---|---|
| `6001` | `ERR_MOTION_NOT_HOMED` | Axis not homed | Perform homing |
| `6002` | `ERR_MOTION_HOME_FAILED` | Homing failed | Check sensors/limits |
| `6003` | `ERR_MOTION_TARGET_OUT_OF_RANGE` | Target outside allowed travel | Check target position |
| `6004` | `ERR_MOTION_AXIS_BUSY` | Axis already moving | Wait or stop |
| `6005` | `ERR_MOTION_START_FAILED` | Motion command failed to start | Check drive/PLC logic |
| `6006` | `ERR_MOTION_TIMEOUT` | Axis did not reach target in time | Check obstruction/drive |
| `6007` | `ERR_MOTION_POSITION_NOT_REACHED` | Position reached signal missing | Check tolerance/sensor |
| `6008` | `ERR_MOTION_POSITION_MISMATCH` | Actual position differs from target | Check calibration |
| `6009` | `ERR_MOTION_DRIVE_ALARM` | Servo/drive alarm active | Check drive alarm code |
| `6010` | `ERR_MOTION_LIMIT_SWITCH` | Limit switch active | Move away/check target |
| `6011` | `ERR_MOTION_ENCODER_ERROR` | Encoder feedback error | Inspect drive/cable |
| `6012` | `ERR_MOTION_COLLISION_RISK` | PLC detected collision risk | Stop and inspect |
| `6013` | `ERR_MOTION_STEP_MISMATCH` | PLC step and PC step mismatch | Stop and inspect log |

---

## 4.8 7000-7999: Safety / Interlock Errors

| Code | Symbol | Meaning | Typical Action |
|---:|---|---|---|
| `7001` | `ERR_SAFETY_ESTOP_ACTIVE` | Emergency stop active | Inspect and reset safely |
| `7002` | `ERR_SAFETY_GUARD_OPEN` | Guard/door open | Close guard |
| `7003` | `ERR_SAFETY_INTERLOCK_OPEN` | Safety interlock not satisfied | Inspect interlock |
| `7004` | `ERR_SAFETY_LIGHT_CURTAIN` | Light curtain interrupted | Clear area |
| `7005` | `ERR_SAFETY_AIR_PRESSURE_LOW` | Pneumatic pressure low | Check air supply |
| `7006` | `ERR_SAFETY_SERVO_NOT_READY` | Servo safety/ready signal false | Check drive |
| `7007` | `ERR_SAFETY_MACHINE_AREA_NOT_CLEAR` | Area not clear | Remove obstruction |
| `7008` | `ERR_SAFETY_RESET_REQUIRED` | Safety reset required | Reset after inspection |
| `7009` | `ERR_SAFETY_OPERATION_NOT_ALLOWED` | Operation blocked by safety logic | Check safety status |
| `7010` | `ERR_SAFETY_UNKNOWN` | Unknown safety fault | Inspect PLC diagnostics |

---

## 4.9 8000-8999: Operator / Workflow Errors

| Code | Symbol | Meaning | Typical Action |
|---:|---|---|---|
| `8001` | `ERR_OPERATOR_BOARD_NAME_MISSING` | Board/sample name missing | Enter board/sample name |
| `8002` | `ERR_OPERATOR_SIDE_MISSING` | Board side missing | Enter T/B or required side |
| `8003` | `ERR_OPERATOR_INVALID_MODE_SELECTION` | Invalid mode selected | Select valid mode |
| `8004` | `ERR_OPERATOR_START_NOT_ALLOWED` | Start pressed before ready | Complete checklist |
| `8005` | `ERR_OPERATOR_PAUSE_ACTIVE` | Run is paused by operator | Resume or stop |
| `8006` | `ERR_OPERATOR_CAPTURE_REJECTED` | Operator or PC rejected capture | Check reason |
| `8007` | `ERR_OPERATOR_CONFIRMATION_REQUIRED` | Confirmation required before continuing | Confirm in UI |
| `8008` | `ERR_OPERATOR_WRONG_SAMPLE` | Wrong sample/board detected | Stop and correct |
| `8009` | `ERR_OPERATOR_RUN_ABORTED` | Operator aborted run | Confirm safe stop |
| `8010` | `ERR_OPERATOR_RESET_DENIED` | Reset denied due to unresolved cause | Diagnose first |

---

## 4.10 9000-9999: Unknown / Fatal / Reserved

| Code | Symbol | Meaning | Typical Action |
|---:|---|---|---|
| `9000` | `ERR_UNKNOWN` | Unknown error | Check full logs |
| `9001` | `ERR_FATAL_SYSTEM` | Fatal system error | Stop and notify engineer |
| `9002` | `ERR_FATAL_PLC` | Fatal PLC-side error | Inspect PLC program/diagnostics |
| `9003` | `ERR_FATAL_PC` | Fatal PC-side error | Restart software/PC |
| `9004` | `ERR_FATAL_CAMERA` | Fatal camera subsystem error | Restart camera/software |
| `9005` | `ERR_FATAL_MOTION` | Fatal motion subsystem error | Lock out and inspect |
| `9999` | `ERR_RESERVED_UNHANDLED` | Reserved unhandled error | Engineering review required |

---

## 5. Recommended PLC Register Mapping

Use one register for the active error and additional registers for detail.

| Register | Meaning |
|---|---|
| `D120` | Active PLC error code |
| `D121` | PLC error detail 1 |
| `D122` | PLC error detail 2 |
| `D123` | Last rejected PC event type |
| `D124` | Last rejected PC sequence |
| `D125` | Last PLC state |
| `D126` | Last mode |
| `D127` | Last step index |

---

## 6. PLC → PC Error Event Payload

When sending an error event from PLC to PC:

```text
D200 = PLC_ERROR / MOTION_ERROR / SAFETY_ERROR / CAPTURE_TIMEOUT
D201 = PLC event sequence number
D202 = main error code
D203 = detail code
D204 = current step index
D205 = current mode
D206 = current PLC state
D207-D209 = reserved
```

Example:

```text
D200 = 901     MOTION_ERROR
D201 = 57      PLC event sequence
D202 = 6006    ERR_MOTION_TIMEOUT
D203 = 2       axis number or detail
D204 = 14      step index
D205 = 2       semi-auto mode
D206 = 35      PLC state code
```

---

## 7. Operator-Facing Message Format

The UI and logs should not show only a raw code. Always display:

```text
Error code
Plain-language message
Operating mode
Step index
Recommended action
Timestamp
```

Example:

```text
Error 6006: Motion timeout
Mode: Semi-Auto
Step: 14
Action: Stop operation. Check obstruction, drive alarm, and target position.
```

---

## 8. Python Enum Appendix

```python
from enum import IntEnum


class AckStatus(IntEnum):
    OK = 0
    REJECTED = 1
    BUSY = 2
    INVALID_STATE = 3
    INVALID_PAYLOAD = 4
    SAFETY_NOT_OK = 5
    TIMEOUT = 6
    DUPLICATE_SEQUENCE = 7
    UNKNOWN_EVENT = 8


class ErrorCode(IntEnum):
    ERR_NONE = 0

    # PC / software
    ERR_PC_NOT_READY = 1001
    ERR_PC_INVALID_MODE = 1002
    ERR_PC_INTERNAL_EXCEPTION = 1003
    ERR_PC_CONFIG_MISSING = 1004
    ERR_PC_CONFIG_INVALID = 1005
    ERR_PC_OPERATOR_ABORT = 1006
    ERR_PC_PAUSED = 1007
    ERR_PC_SEQUENCE_MISMATCH = 1008
    ERR_PC_METADATA_MISSING = 1009
    ERR_PC_MODE_SWITCH_NOT_ALLOWED = 1010

    # PLC / state machine
    ERR_PLC_NOT_READY = 2001
    ERR_PLC_INVALID_STATE = 2002
    ERR_PLC_BUSY = 2003
    ERR_PLC_UNKNOWN_EVENT = 2004
    ERR_PLC_INVALID_PAYLOAD = 2005
    ERR_PLC_SEQUENCE_DUPLICATE = 2006
    ERR_PLC_SEQUENCE_SKIPPED = 2007
    ERR_PLC_MODE_NOT_SELECTED = 2008
    ERR_PLC_MANUAL_ONLY_EVENT = 2009
    ERR_PLC_SEMIAUTO_ONLY_EVENT = 2010
    ERR_PLC_RESET_NOT_ALLOWED = 2011
    ERR_PLC_RECIPE_NOT_LOADED = 2012
    ERR_PLC_STEP_INDEX_INVALID = 2013

    # Communication
    ERR_COMM_CONNECT_FAILED = 3001
    ERR_COMM_SOCKET_CLOSED = 3002
    ERR_COMM_TIMEOUT = 3003
    ERR_COMM_BAD_RESPONSE = 3004
    ERR_COMM_SLMP_END_CODE = 3005
    ERR_COMM_WRITE_FAILED = 3006
    ERR_COMM_READ_FAILED = 3007
    ERR_COMM_ACK_TIMEOUT = 3008
    ERR_COMM_PLC_EVENT_TIMEOUT = 3009
    ERR_COMM_PC_ACK_TIMEOUT = 3010
    ERR_COMM_HEARTBEAT_LOST = 3011
    ERR_COMM_WRONG_PORT = 3012
    ERR_COMM_WRONG_IP = 3013
    ERR_COMM_FIREWALL_BLOCKED = 3014
    ERR_COMM_FRAME_MODE_MISMATCH = 3015

    # Camera
    ERR_CAMERA_NOT_DETECTED = 4001
    ERR_CAMERA_OPEN_FAILED = 4002
    ERR_CAMERA_ALREADY_IN_USE = 4003
    ERR_CAMERA_SETTINGS_MISSING = 4004
    ERR_CAMERA_SETTINGS_LOAD_FAILED = 4005
    ERR_CAMERA_PIPELINE_MISSING = 4006
    ERR_CAMERA_PIPELINE_LOAD_FAILED = 4007
    ERR_CAMERA_ACQUISITION_NOT_RUNNING = 4008
    ERR_CAMERA_FRAME_TIMEOUT = 4009
    ERR_CAMERA_FRAME_INCOMPLETE = 4010
    ERR_CAMERA_STALE_FRAME = 4011
    ERR_CAMERA_PROCESSING_FAILED = 4012
    ERR_CAMERA_BRIGHTNESS_UNSTABLE = 4013
    ERR_CAMERA_FOCUS_BAD = 4014
    ERR_CAMERA_LIGHTING_BAD = 4015

    # Storage
    ERR_STORAGE_PATH_MISSING = 5001
    ERR_STORAGE_PATH_INVALID = 5002
    ERR_STORAGE_PERMISSION_DENIED = 5003
    ERR_STORAGE_DISK_FULL = 5004
    ERR_STORAGE_FILENAME_INVALID = 5005
    ERR_IMAGE_SAVE_FAILED = 5006
    ERR_IMAGE_VERIFY_FAILED = 5007
    ERR_IMAGE_INDEX_DUPLICATE = 5008
    ERR_LOG_CREATE_FAILED = 5009
    ERR_LOG_WRITE_FAILED = 5010

    # Motion
    ERR_MOTION_NOT_HOMED = 6001
    ERR_MOTION_HOME_FAILED = 6002
    ERR_MOTION_TARGET_OUT_OF_RANGE = 6003
    ERR_MOTION_AXIS_BUSY = 6004
    ERR_MOTION_START_FAILED = 6005
    ERR_MOTION_TIMEOUT = 6006
    ERR_MOTION_POSITION_NOT_REACHED = 6007
    ERR_MOTION_POSITION_MISMATCH = 6008
    ERR_MOTION_DRIVE_ALARM = 6009
    ERR_MOTION_LIMIT_SWITCH = 6010
    ERR_MOTION_ENCODER_ERROR = 6011
    ERR_MOTION_COLLISION_RISK = 6012
    ERR_MOTION_STEP_MISMATCH = 6013

    # Safety
    ERR_SAFETY_ESTOP_ACTIVE = 7001
    ERR_SAFETY_GUARD_OPEN = 7002
    ERR_SAFETY_INTERLOCK_OPEN = 7003
    ERR_SAFETY_LIGHT_CURTAIN = 7004
    ERR_SAFETY_AIR_PRESSURE_LOW = 7005
    ERR_SAFETY_SERVO_NOT_READY = 7006
    ERR_SAFETY_MACHINE_AREA_NOT_CLEAR = 7007
    ERR_SAFETY_RESET_REQUIRED = 7008
    ERR_SAFETY_OPERATION_NOT_ALLOWED = 7009
    ERR_SAFETY_UNKNOWN = 7010

    # Operator / workflow
    ERR_OPERATOR_BOARD_NAME_MISSING = 8001
    ERR_OPERATOR_SIDE_MISSING = 8002
    ERR_OPERATOR_INVALID_MODE_SELECTION = 8003
    ERR_OPERATOR_START_NOT_ALLOWED = 8004
    ERR_OPERATOR_PAUSE_ACTIVE = 8005
    ERR_OPERATOR_CAPTURE_REJECTED = 8006
    ERR_OPERATOR_CONFIRMATION_REQUIRED = 8007
    ERR_OPERATOR_WRONG_SAMPLE = 8008
    ERR_OPERATOR_RUN_ABORTED = 8009
    ERR_OPERATOR_RESET_DENIED = 8010

    # Unknown / fatal
    ERR_UNKNOWN = 9000
    ERR_FATAL_SYSTEM = 9001
    ERR_FATAL_PLC = 9002
    ERR_FATAL_PC = 9003
    ERR_FATAL_CAMERA = 9004
    ERR_FATAL_MOTION = 9005
    ERR_RESERVED_UNHANDLED = 9999
```

