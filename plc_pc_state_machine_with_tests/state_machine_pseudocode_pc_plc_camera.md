# Pseudocode: PC Controller, PLC Simulator, and Camera TCP Service

## 1. Purpose

This document defines the high-level pseudocode for the vision capture control system.

The system is divided into three programs:

1. **PC Controller**
2. **PLC / PLC-Simulator Controller**
3. **Camera TCP Service**

The architecture separates responsibilities:

```text
PC Controller:
    Operator workflow
    Mode selection
    PLC communication
    Camera authorization
    Image capture request
    Logging and error handling

PLC / PLC Simulator:
    Motion authority
    Safety authority
    Manual command validation
    Semi-auto sequence execution
    Event acknowledgement
    Error reporting

Camera TCP Service:
    Camera startup/shutdown
    Frame freshness monitoring
    Save latest image request
    Camera status reporting
```

The programs communicate using two protocols:

```text
PC Controller <-> PLC:
    MC/SLMP-style event mailbox

PC Controller <-> Camera Service:
    Local TCP newline-delimited JSON commands
```

---

## 2. Shared PC <-> PLC Event Mailbox

### 2.1 PC -> PLC Mailbox

```text
D100 = PC event type
D101 = PC event sequence number
D102-D109 = PC event payload
D110 = PLC acknowledgement sequence
D111 = PLC acknowledgement status
```

### 2.2 PLC -> PC Mailbox

```text
D200 = PLC event type
D201 = PLC event sequence number
D202-D209 = PLC event payload
D210 = PC acknowledgement sequence
D211 = PC acknowledgement status
```

---

## 3. Shared ACK Codes

```text
ACK_OK               = 0
ACK_REJECTED         = 1
ACK_BUSY             = 2
ACK_INVALID_STATE    = 3
ACK_INVALID_PAYLOAD  = 4
ACK_SAFETY_NOT_OK    = 5
ACK_TIMEOUT          = 6
ACK_UNKNOWN_EVENT    = 8
```

---

## 4. Shared PC -> PLC Events

```text
NONE                    = 0

PC_READY                = 10
SET_MODE_MANUAL         = 11
SET_MODE_SEMI_AUTO      = 12
START_RUN               = 13
PAUSE_RUN               = 14
RESUME_RUN              = 15
STOP_RUN                = 16
RESET_ERROR             = 17

MANUAL_HOME_REQUEST     = 30
MANUAL_MOVE_REQUEST     = 31
MANUAL_JOG_REQUEST      = 32
MANUAL_CAPTURE_DONE     = 33

CAPTURE_AUTHORIZED      = 50
CAPTURE_REJECTED        = 51
CAPTURE_DONE            = 52

PC_HEARTBEAT            = 90
```

---

## 5. Shared PLC -> PC Events

```text
NONE                    = 0

PLC_READY               = 100
MODE_CHANGED            = 101
RUN_STARTED             = 102
RUN_PAUSED              = 103
RUN_STOPPED             = 104
RUN_COMPLETE            = 105

MANUAL_COMMAND_STARTED  = 130
MANUAL_COMMAND_DONE     = 131
MANUAL_COMMAND_ERROR    = 132

SEMI_AUTO_STEP_STARTED  = 150
POSITION_REACHED        = 151
CAPTURE_AUTH_REQUEST    = 152
CAPTURE_WINDOW_OPEN     = 153
CAPTURE_WINDOW_CLOSED   = 154
STEP_COMPLETE           = 155

PLC_ERROR               = 900
MOTION_ERROR            = 901
SAFETY_ERROR            = 902
CAPTURE_TIMEOUT         = 903
COMMUNICATION_TIMEOUT   = 904
```

---

## 6. Shared PC <-> PLC Communication Functions

### 6.1 Send PC Event

```text
FUNCTION Send_PC_Event(event_type, payload):

    pc_sequence = pc_sequence + 1

    WRITE:
        D100 = event_type
        D101 = pc_sequence
        D102-D109 = payload

    WAIT until:
        D110 == pc_sequence

    IF D111 == ACK_OK:
        RETURN SUCCESS

    ELSE:
        RETURN FAILURE_WITH_ACK_STATUS(D111)
```

### 6.2 Read PLC Event

```text
FUNCTION Read_PLC_Event():

    READ:
        plc_event_type = D200
        plc_sequence   = D201
        plc_payload    = D202-D209

    IF plc_event_type == NONE:
        RETURN NO_EVENT

    IF plc_sequence == last_plc_sequence_seen:
        RETURN NO_NEW_EVENT

    RETURN PLC_EVENT(plc_event_type, plc_sequence, plc_payload)
```

### 6.3 Acknowledge PLC Event

```text
FUNCTION Acknowledge_PLC_Event(plc_event, status):

    WRITE:
        D210 = plc_event.sequence
        D211 = status

    last_plc_sequence_seen = plc_event.sequence
```

---

# Part A - PC Controller State Machine

## 7. PC Controller Responsibilities

```text
Starting the operator workflow
Connecting to the PLC
Connecting to the camera TCP service
Selecting Manual or Semi-Auto Mode
Sending events to the PLC
Receiving PLC events
Authorizing image capture
Requesting image capture from the camera service
Handling PC-side errors
Logging run data
```

---

## 8. PC Controller State List

```text
PC_STARTUP
PC_CONNECT_CAMERA
PC_CONNECT_PLC
PC_WAIT_PLC_READY
PC_IDLE

PC_MANUAL_SELECT
PC_MANUAL_IDLE
PC_MANUAL_SEND_COMMAND
PC_MANUAL_WAIT_STARTED
PC_MANUAL_WAIT_RESULT
PC_MANUAL_CAPTURE
PC_MANUAL_REPORT_CAPTURE_DONE

PC_SEMI_SELECT
PC_SEMI_START_RUN
PC_SEMI_MONITOR_RUN
PC_SEMI_CHECK_CAPTURE_READY
PC_SEMI_AUTHORIZE_CAPTURE
PC_SEMI_WAIT_CAPTURE_WINDOW
PC_SEMI_CAPTURE_IMAGE
PC_SEMI_REPORT_CAPTURE_DONE

PC_ERROR
PC_SHUTDOWN
```

---

## 9. PC Controller Variables

```text
pc_state
selected_mode
pc_sequence
last_plc_sequence_seen

board_name
board_side
current_step
expected_step
requested_step
current_position
image_index

plc_connected
camera_connected
camera_running
storage_ready
operator_pause_requested

active_error_code
```

---

## 10. PC Main State Machine

```text
PROGRAM PC_Controller

pc_state = PC_STARTUP

LOOP forever:

    CASE pc_state:

        PC_STARTUP:
            Load_PC_Configuration()
            Initialize_Logger()
            pc_state = PC_CONNECT_CAMERA

        PC_CONNECT_CAMERA:
            result = Camera_TCP_Connect()

            IF result == SUCCESS:
                Camera_TCP_Command(START)
                pc_state = PC_CONNECT_PLC

            ELSE:
                active_error_code = ERR_CAMERA_NOT_DETECTED
                pc_state = PC_ERROR

        PC_CONNECT_PLC:
            result = Connect_To_PLC_MC_SLMP()

            IF result == SUCCESS:
                Send_PC_Event(PC_READY, payload = [])
                pc_state = PC_WAIT_PLC_READY

            ELSE:
                active_error_code = ERR_COMM_CONNECT_FAILED
                pc_state = PC_ERROR

        PC_WAIT_PLC_READY:
            plc_event = Wait_For_PLC_Event(timeout)

            IF plc_event.type == PLC_READY:
                Acknowledge_PLC_Event(plc_event, ACK_OK)
                pc_state = PC_IDLE

            ELSE IF timeout:
                active_error_code = ERR_COMM_PLC_EVENT_TIMEOUT
                pc_state = PC_ERROR

            ELSE IF plc_event.type is ERROR_EVENT:
                Acknowledge_PLC_Event(plc_event, ACK_REJECTED)
                active_error_code = plc_event.payload.error_code
                pc_state = PC_ERROR

        PC_IDLE:
            Display("System Ready / Idle")

            operator_action = Get_Operator_Action()

            IF operator_action == SELECT_MANUAL_MODE:
                pc_state = PC_MANUAL_SELECT

            ELSE IF operator_action == SELECT_SEMI_AUTO_MODE:
                pc_state = PC_SEMI_SELECT

            ELSE IF operator_action == SHUTDOWN:
                pc_state = PC_SHUTDOWN

            ELSE:
                Remain in PC_IDLE
```

---

## 11. PC Manual Mode State Machine

```text
        PC_MANUAL_SELECT:
            result = Send_PC_Event(SET_MODE_MANUAL, payload = [])

            IF result == SUCCESS:
                plc_event = Wait_For_PLC_Event(MODE_CHANGED)

                IF plc_event.payload.mode == MANUAL:
                    Acknowledge_PLC_Event(plc_event, ACK_OK)
                    selected_mode = MANUAL
                    pc_state = PC_MANUAL_IDLE

                ELSE:
                    active_error_code = ERR_PC_INVALID_MODE
                    pc_state = PC_ERROR

            ELSE:
                active_error_code = Convert_ACK_To_Error(result.ack_status)
                pc_state = PC_ERROR

        PC_MANUAL_IDLE:
            Display("Manual Mode Ready")

            manual_command = Get_Manual_Command_From_Operator()

            IF manual_command == MOVE:
                payload = Encode_Target_Position(manual_command.x, manual_command.y)
                pc_state = PC_MANUAL_SEND_COMMAND

            ELSE IF manual_command == HOME:
                payload = Encode_Home_Request()
                pc_state = PC_MANUAL_SEND_COMMAND

            ELSE IF manual_command == JOG:
                payload = Encode_Jog_Request(axis, direction, distance)
                pc_state = PC_MANUAL_SEND_COMMAND

            ELSE IF manual_command == CAPTURE_ONLY:
                pc_state = PC_MANUAL_CAPTURE

            ELSE IF manual_command == EXIT_TO_IDLE:
                pc_state = PC_IDLE

            ELSE:
                Remain in PC_MANUAL_IDLE

        PC_MANUAL_SEND_COMMAND:
            result = Send_PC_Event(manual_command.event_type, payload)

            IF result == SUCCESS:
                pc_state = PC_MANUAL_WAIT_STARTED

            ELSE:
                active_error_code = Convert_ACK_To_Error(result.ack_status)
                pc_state = PC_ERROR

        PC_MANUAL_WAIT_STARTED:
            plc_event = Wait_For_PLC_Event(timeout)

            IF plc_event.type == MANUAL_COMMAND_STARTED:
                Acknowledge_PLC_Event(plc_event, ACK_OK)
                pc_state = PC_MANUAL_WAIT_RESULT

            ELSE IF plc_event.type == MANUAL_COMMAND_ERROR:
                Acknowledge_PLC_Event(plc_event, ACK_REJECTED)
                active_error_code = plc_event.payload.error_code
                pc_state = PC_ERROR

            ELSE IF timeout:
                active_error_code = ERR_COMM_PLC_EVENT_TIMEOUT
                pc_state = PC_ERROR

        PC_MANUAL_WAIT_RESULT:
            plc_event = Wait_For_PLC_Event(timeout)

            IF plc_event.type == MANUAL_COMMAND_DONE:
                Acknowledge_PLC_Event(plc_event, ACK_OK)

                IF Operator_Wants_Capture():
                    pc_state = PC_MANUAL_CAPTURE
                ELSE:
                    pc_state = PC_MANUAL_IDLE

            ELSE IF plc_event.type == MANUAL_COMMAND_ERROR:
                Acknowledge_PLC_Event(plc_event, ACK_REJECTED)
                active_error_code = plc_event.payload.error_code
                pc_state = PC_ERROR

            ELSE IF plc_event.type is ERROR_EVENT:
                Acknowledge_PLC_Event(plc_event, ACK_REJECTED)
                active_error_code = plc_event.payload.error_code
                pc_state = PC_ERROR

            ELSE IF timeout:
                active_error_code = ERR_COMM_PLC_EVENT_TIMEOUT
                pc_state = PC_ERROR

        PC_MANUAL_CAPTURE:
            IF Camera_Is_Ready() == FALSE:
                active_error_code = ERR_CAMERA_ACQUISITION_NOT_RUNNING
                pc_state = PC_ERROR

            ELSE IF Camera_Has_Fresh_Frame() == FALSE:
                active_error_code = ERR_CAMERA_STALE_FRAME
                pc_state = PC_ERROR

            ELSE IF Storage_Ready() == FALSE:
                active_error_code = ERR_STORAGE_PATH_INVALID
                pc_state = PC_ERROR

            ELSE:
                result = Camera_Save_Latest_Image()

                IF result == SUCCESS:
                    pc_state = PC_MANUAL_REPORT_CAPTURE_DONE
                ELSE:
                    active_error_code = ERR_IMAGE_SAVE_FAILED
                    pc_state = PC_ERROR

        PC_MANUAL_REPORT_CAPTURE_DONE:
            result = Send_PC_Event(
                MANUAL_CAPTURE_DONE,
                payload = [image_index, 0, 0, 0]
            )

            IF result == SUCCESS:
                pc_state = PC_MANUAL_IDLE

            ELSE:
                active_error_code = Convert_ACK_To_Error(result.ack_status)
                pc_state = PC_ERROR
```

---

## 12. PC Semi-Auto Mode State Machine

```text
        PC_SEMI_SELECT:
            result = Send_PC_Event(SET_MODE_SEMI_AUTO, payload = [])

            IF result == SUCCESS:
                plc_event = Wait_For_PLC_Event(MODE_CHANGED)

                IF plc_event.payload.mode == SEMI_AUTO:
                    Acknowledge_PLC_Event(plc_event, ACK_OK)
                    selected_mode = SEMI_AUTO
                    pc_state = PC_SEMI_START_RUN

                ELSE:
                    active_error_code = ERR_PC_INVALID_MODE
                    pc_state = PC_ERROR

            ELSE:
                active_error_code = Convert_ACK_To_Error(result.ack_status)
                pc_state = PC_ERROR

        PC_SEMI_START_RUN:
            IF Metadata_Ready() == FALSE:
                active_error_code = ERR_PC_METADATA_MISSING
                pc_state = PC_ERROR

            ELSE IF Camera_Is_Ready() == FALSE:
                active_error_code = ERR_CAMERA_ACQUISITION_NOT_RUNNING
                pc_state = PC_ERROR

            ELSE IF Storage_Ready() == FALSE:
                active_error_code = ERR_STORAGE_PATH_INVALID
                pc_state = PC_ERROR

            ELSE:
                result = Send_PC_Event(START_RUN, payload = [])

                IF result == SUCCESS:
                    pc_state = PC_SEMI_MONITOR_RUN

                ELSE:
                    active_error_code = Convert_ACK_To_Error(result.ack_status)
                    pc_state = PC_ERROR

        PC_SEMI_MONITOR_RUN:
            plc_event = Wait_For_PLC_Event(timeout)

            IF plc_event.type == RUN_STARTED:
                Acknowledge_PLC_Event(plc_event, ACK_OK)
                pc_state = PC_SEMI_MONITOR_RUN

            ELSE IF plc_event.type == SEMI_AUTO_STEP_STARTED:
                current_step = plc_event.payload.step_index
                expected_step = current_step
                Acknowledge_PLC_Event(plc_event, ACK_OK)
                pc_state = PC_SEMI_MONITOR_RUN

            ELSE IF plc_event.type == POSITION_REACHED:
                current_position = plc_event.payload.position
                Acknowledge_PLC_Event(plc_event, ACK_OK)
                pc_state = PC_SEMI_MONITOR_RUN

            ELSE IF plc_event.type == CAPTURE_AUTH_REQUEST:
                requested_step = plc_event.payload.step_index
                Acknowledge_PLC_Event(plc_event, ACK_OK)
                pc_state = PC_SEMI_CHECK_CAPTURE_READY

            ELSE IF plc_event.type == CAPTURE_WINDOW_OPEN:
                Acknowledge_PLC_Event(plc_event, ACK_OK)
                pc_state = PC_SEMI_CAPTURE_IMAGE

            ELSE IF plc_event.type == CAPTURE_WINDOW_CLOSED:
                Acknowledge_PLC_Event(plc_event, ACK_OK)
                pc_state = PC_SEMI_MONITOR_RUN

            ELSE IF plc_event.type == STEP_COMPLETE:
                Acknowledge_PLC_Event(plc_event, ACK_OK)
                pc_state = PC_SEMI_MONITOR_RUN

            ELSE IF plc_event.type == RUN_COMPLETE:
                Acknowledge_PLC_Event(plc_event, ACK_OK)
                pc_state = PC_IDLE

            ELSE IF plc_event.type is ERROR_EVENT:
                Acknowledge_PLC_Event(plc_event, ACK_REJECTED)
                active_error_code = plc_event.payload.error_code
                pc_state = PC_ERROR

            ELSE IF timeout:
                active_error_code = ERR_COMM_PLC_EVENT_TIMEOUT
                pc_state = PC_ERROR

        PC_SEMI_CHECK_CAPTURE_READY:
            IF requested_step != expected_step:
                Send_PC_Event(
                    CAPTURE_REJECTED,
                    payload = [ERR_PC_SEQUENCE_MISMATCH, requested_step]
                )
                active_error_code = ERR_PC_SEQUENCE_MISMATCH
                pc_state = PC_ERROR

            ELSE IF Camera_Is_Ready() == FALSE:
                Send_PC_Event(
                    CAPTURE_REJECTED,
                    payload = [ERR_CAMERA_ACQUISITION_NOT_RUNNING, requested_step]
                )
                active_error_code = ERR_CAMERA_ACQUISITION_NOT_RUNNING
                pc_state = PC_ERROR

            ELSE IF Camera_Has_Fresh_Frame() == FALSE:
                Send_PC_Event(
                    CAPTURE_REJECTED,
                    payload = [ERR_CAMERA_STALE_FRAME, requested_step]
                )
                active_error_code = ERR_CAMERA_STALE_FRAME
                pc_state = PC_ERROR

            ELSE IF Storage_Ready() == FALSE:
                Send_PC_Event(
                    CAPTURE_REJECTED,
                    payload = [ERR_STORAGE_PATH_INVALID, requested_step]
                )
                active_error_code = ERR_STORAGE_PATH_INVALID
                pc_state = PC_ERROR

            ELSE IF operator_pause_requested == TRUE:
                Send_PC_Event(
                    CAPTURE_REJECTED,
                    payload = [ERR_OPERATOR_PAUSE_ACTIVE, requested_step]
                )
                active_error_code = ERR_OPERATOR_PAUSE_ACTIVE
                pc_state = PC_ERROR

            ELSE:
                pc_state = PC_SEMI_AUTHORIZE_CAPTURE

        PC_SEMI_AUTHORIZE_CAPTURE:
            result = Send_PC_Event(
                CAPTURE_AUTHORIZED,
                payload = [requested_step, 0, 0, 0]
            )

            IF result == SUCCESS:
                pc_state = PC_SEMI_WAIT_CAPTURE_WINDOW

            ELSE:
                active_error_code = Convert_ACK_To_Error(result.ack_status)
                pc_state = PC_ERROR

        PC_SEMI_WAIT_CAPTURE_WINDOW:
            plc_event = Wait_For_PLC_Event(CAPTURE_WINDOW_OPEN)

            IF plc_event.type == CAPTURE_WINDOW_OPEN:
                Acknowledge_PLC_Event(plc_event, ACK_OK)
                pc_state = PC_SEMI_CAPTURE_IMAGE

            ELSE IF timeout:
                active_error_code = ERR_COMM_PLC_EVENT_TIMEOUT
                pc_state = PC_ERROR

            ELSE IF plc_event.type is ERROR_EVENT:
                Acknowledge_PLC_Event(plc_event, ACK_REJECTED)
                active_error_code = plc_event.payload.error_code
                pc_state = PC_ERROR

        PC_SEMI_CAPTURE_IMAGE:
            result = Camera_Save_Latest_Image()

            IF result == SUCCESS:
                pc_state = PC_SEMI_REPORT_CAPTURE_DONE

            ELSE:
                Send_PC_Event(
                    CAPTURE_REJECTED,
                    payload = [ERR_IMAGE_SAVE_FAILED, requested_step]
                )
                active_error_code = ERR_IMAGE_SAVE_FAILED
                pc_state = PC_ERROR

        PC_SEMI_REPORT_CAPTURE_DONE:
            result = Send_PC_Event(
                CAPTURE_DONE,
                payload = [requested_step, image_index, 0, 0]
            )

            IF result == SUCCESS:
                pc_state = PC_SEMI_MONITOR_RUN

            ELSE:
                active_error_code = Convert_ACK_To_Error(result.ack_status)
                pc_state = PC_ERROR
```

---

## 13. PC Error and Shutdown States

```text
        PC_ERROR:
            Display_Error(active_error_code)
            Log_Error(active_error_code)

            operator_action = Get_Error_Action()

            IF operator_action == RESET:
                result = Send_PC_Event(RESET_ERROR, payload = [active_error_code])

                IF result == SUCCESS:
                    active_error_code = ERR_NONE
                    pc_state = PC_IDLE
                ELSE:
                    Remain in PC_ERROR

            ELSE IF operator_action == STOP:
                Send_PC_Event(STOP_RUN, payload = [])
                pc_state = PC_IDLE

            ELSE IF operator_action == SHUTDOWN:
                pc_state = PC_SHUTDOWN

            ELSE:
                Remain in PC_ERROR

        PC_SHUTDOWN:
            Camera_TCP_Command(STOP)
            Camera_TCP_Close()
            Close_PLC_Connection()
            Save_Logs()
            Display("System shutdown complete")
            EXIT PROGRAM
```

---

# Part B - PLC / PLC-Simulator State Machine

## 14. PLC Responsibilities

```text
Receiving PC events
Acknowledging PC events
Validating commands
Maintaining PLC state
Executing manual commands
Running semi-auto sequence
Requesting capture authorization
Waiting for capture completion
Handling safety and motion errors
Publishing PLC events
```

---

## 15. PLC State List

```text
PLC_BOOT
PLC_WAIT_PC_READY
PLC_IDLE

PLC_MANUAL_IDLE
PLC_MANUAL_VALIDATE_COMMAND
PLC_MANUAL_START_COMMAND
PLC_MANUAL_EXECUTING
PLC_MANUAL_DONE

PLC_SEMI_IDLE
PLC_SEMI_LOAD_NEXT_STEP
PLC_SEMI_MOVE_TO_POSITION
PLC_SEMI_POSITION_REACHED
PLC_SEMI_WAIT_CAPTURE_AUTH
PLC_SEMI_OPEN_CAPTURE_WINDOW
PLC_SEMI_WAIT_CAPTURE_DONE
PLC_SEMI_CLOSE_CAPTURE_WINDOW
PLC_SEMI_STEP_COMPLETE
PLC_SEMI_RUN_COMPLETE

PLC_ERROR
```

---

## 16. PLC Variables

```text
plc_state
mode

last_pc_sequence_handled
plc_sequence
active_plc_event_sequence
waiting_for_pc_ack

current_step
total_steps
target_position
actual_position

motion_timer
capture_auth_timer
capture_done_timer

safety_ok
motion_ok
active_error_code
```

---

## 17. PLC Main Scan Loop

```text
PROGRAM PLC_Control_State_Machine

plc_state = PLC_BOOT

LOOP every PLC scan:

    Update_Safety_Status()
    Update_Motion_Status()
    Check_Heartbeat()

    pc_event = Read_PC_Event_Mailbox()

    IF pc_event.sequence is new:
        Handle_PC_Event(pc_event)

    Run_PLC_State()

    Check_PC_Acknowledgement_For_Last_PLC_Event()
```

---

## 18. PLC Event Handler

```text
FUNCTION Handle_PC_Event(pc_event):

    IF pc_event.type == PC_READY:
        IF plc_state == PLC_WAIT_PC_READY:
            Acknowledge_PC_Event(pc_event.sequence, ACK_OK)
            Publish_PLC_Event(PLC_READY, payload = [])
            plc_state = PLC_IDLE
        ELSE:
            Acknowledge_PC_Event(pc_event.sequence, ACK_OK)

    ELSE IF pc_event.type == SET_MODE_MANUAL:
        IF plc_state is PLC_IDLE or PLC_MANUAL_IDLE:
            mode = MANUAL
            plc_state = PLC_MANUAL_IDLE
            Acknowledge_PC_Event(pc_event.sequence, ACK_OK)
            Publish_PLC_Event(MODE_CHANGED, payload = [MANUAL])
        ELSE:
            Acknowledge_PC_Event(pc_event.sequence, ACK_BUSY)

    ELSE IF pc_event.type == SET_MODE_SEMI_AUTO:
        IF plc_state is PLC_IDLE or PLC_SEMI_IDLE:
            mode = SEMI_AUTO
            plc_state = PLC_SEMI_IDLE
            Acknowledge_PC_Event(pc_event.sequence, ACK_OK)
            Publish_PLC_Event(MODE_CHANGED, payload = [SEMI_AUTO])
        ELSE:
            Acknowledge_PC_Event(pc_event.sequence, ACK_BUSY)

    ELSE IF pc_event.type == MANUAL_MOVE_REQUEST:
        IF mode == MANUAL AND plc_state == PLC_MANUAL_IDLE:
            Store_Manual_Command(pc_event)
            plc_state = PLC_MANUAL_VALIDATE_COMMAND
            Acknowledge_PC_Event(pc_event.sequence, ACK_OK)
        ELSE:
            Acknowledge_PC_Event(pc_event.sequence, ACK_INVALID_STATE)

    ELSE IF pc_event.type == MANUAL_HOME_REQUEST:
        IF mode == MANUAL AND plc_state == PLC_MANUAL_IDLE:
            Store_Manual_Command(pc_event)
            plc_state = PLC_MANUAL_VALIDATE_COMMAND
            Acknowledge_PC_Event(pc_event.sequence, ACK_OK)
        ELSE:
            Acknowledge_PC_Event(pc_event.sequence, ACK_INVALID_STATE)

    ELSE IF pc_event.type == START_RUN:
        IF mode == SEMI_AUTO AND plc_state == PLC_SEMI_IDLE:
            current_step = 0
            Acknowledge_PC_Event(pc_event.sequence, ACK_OK)
            Publish_PLC_Event(RUN_STARTED, payload = [])
            plc_state = PLC_SEMI_LOAD_NEXT_STEP
        ELSE:
            Acknowledge_PC_Event(pc_event.sequence, ACK_INVALID_STATE)

    ELSE IF pc_event.type == CAPTURE_AUTHORIZED:
        IF mode == SEMI_AUTO AND plc_state == PLC_SEMI_WAIT_CAPTURE_AUTH:
            Acknowledge_PC_Event(pc_event.sequence, ACK_OK)
            plc_state = PLC_SEMI_OPEN_CAPTURE_WINDOW
        ELSE:
            Acknowledge_PC_Event(pc_event.sequence, ACK_INVALID_STATE)

    ELSE IF pc_event.type == CAPTURE_REJECTED:
        IF mode == SEMI_AUTO:
            Acknowledge_PC_Event(pc_event.sequence, ACK_OK)
            active_error_code = pc_event.payload.error_code
            Publish_PLC_Event(PLC_ERROR, payload = [active_error_code])
            plc_state = PLC_ERROR
        ELSE:
            Acknowledge_PC_Event(pc_event.sequence, ACK_INVALID_STATE)

    ELSE IF pc_event.type == CAPTURE_DONE:
        IF mode == SEMI_AUTO AND plc_state == PLC_SEMI_WAIT_CAPTURE_DONE:
            Acknowledge_PC_Event(pc_event.sequence, ACK_OK)
            plc_state = PLC_SEMI_CLOSE_CAPTURE_WINDOW
        ELSE:
            Acknowledge_PC_Event(pc_event.sequence, ACK_INVALID_STATE)

    ELSE IF pc_event.type == STOP_RUN:
        Stop_Motion_Safely()
        Acknowledge_PC_Event(pc_event.sequence, ACK_OK)
        Publish_PLC_Event(RUN_STOPPED, payload = [])
        plc_state = PLC_IDLE

    ELSE IF pc_event.type == RESET_ERROR:
        IF Reset_Allowed():
            Clear_Alarms()
            active_error_code = ERR_NONE
            Acknowledge_PC_Event(pc_event.sequence, ACK_OK)
            plc_state = PLC_IDLE
        ELSE:
            Acknowledge_PC_Event(pc_event.sequence, ACK_REJECTED)

    ELSE:
        Acknowledge_PC_Event(pc_event.sequence, ACK_UNKNOWN_EVENT)
```

---

## 19. PLC State Execution

### 19.1 Startup and Idle

```text
FUNCTION Run_PLC_State():

    CASE plc_state:

        PLC_BOOT:
            Initialize_PLC_Internal_State()
            Clear_Event_Mailboxes()
            mode = NONE
            plc_state = PLC_WAIT_PC_READY

        PLC_WAIT_PC_READY:
            Do_Nothing()
            Wait for PC_READY event

        PLC_IDLE:
            Do_Nothing()
            Wait for mode selection
```

### 19.2 PLC Manual Mode States

```text
        PLC_MANUAL_IDLE:
            Do_Nothing()
            Wait for manual PC command

        PLC_MANUAL_VALIDATE_COMMAND:
            IF safety_ok == FALSE:
                active_error_code = ERR_SAFETY_OPERATION_NOT_ALLOWED
                Publish_PLC_Event(
                    MANUAL_COMMAND_ERROR,
                    payload = [active_error_code]
                )
                plc_state = PLC_ERROR

            ELSE IF Manual_Command_Payload_Valid() == FALSE:
                active_error_code = ERR_PLC_INVALID_PAYLOAD
                Publish_PLC_Event(
                    MANUAL_COMMAND_ERROR,
                    payload = [active_error_code]
                )
                plc_state = PLC_MANUAL_IDLE

            ELSE IF Target_In_Range() == FALSE:
                active_error_code = ERR_MOTION_TARGET_OUT_OF_RANGE
                Publish_PLC_Event(
                    MANUAL_COMMAND_ERROR,
                    payload = [active_error_code]
                )
                plc_state = PLC_MANUAL_IDLE

            ELSE:
                plc_state = PLC_MANUAL_START_COMMAND

        PLC_MANUAL_START_COMMAND:
            Start_Manual_Command()
            Publish_PLC_Event(MANUAL_COMMAND_STARTED, payload = [])
            plc_state = PLC_MANUAL_EXECUTING

        PLC_MANUAL_EXECUTING:
            IF safety_ok == FALSE:
                Stop_Motion_Safely()
                active_error_code = ERR_SAFETY_OPERATION_NOT_ALLOWED
                Publish_PLC_Event(SAFETY_ERROR, payload = [active_error_code])
                plc_state = PLC_ERROR

            ELSE IF Motion_Error():
                Stop_Motion_Safely()
                active_error_code = ERR_MOTION_DRIVE_ALARM
                Publish_PLC_Event(MANUAL_COMMAND_ERROR, payload = [active_error_code])
                plc_state = PLC_ERROR

            ELSE IF Motion_Timeout():
                Stop_Motion_Safely()
                active_error_code = ERR_MOTION_TIMEOUT
                Publish_PLC_Event(MANUAL_COMMAND_ERROR, payload = [active_error_code])
                plc_state = PLC_ERROR

            ELSE IF Motion_Done():
                plc_state = PLC_MANUAL_DONE

        PLC_MANUAL_DONE:
            Publish_PLC_Event(MANUAL_COMMAND_DONE, payload = [])
            plc_state = PLC_MANUAL_IDLE
```

### 19.3 PLC Semi-Auto Mode States

```text
        PLC_SEMI_IDLE:
            Do_Nothing()
            Wait for START_RUN

        PLC_SEMI_LOAD_NEXT_STEP:
            IF current_step >= total_steps:
                plc_state = PLC_SEMI_RUN_COMPLETE

            ELSE:
                Load_Target_For_Current_Step(current_step)
                Publish_PLC_Event(
                    SEMI_AUTO_STEP_STARTED,
                    payload = [current_step]
                )
                plc_state = PLC_SEMI_MOVE_TO_POSITION

        PLC_SEMI_MOVE_TO_POSITION:
            IF entering_state:
                Start_Motion_To_Target(target_position)

            IF safety_ok == FALSE:
                Stop_Motion_Safely()
                active_error_code = ERR_SAFETY_OPERATION_NOT_ALLOWED
                Publish_PLC_Event(SAFETY_ERROR, payload = [active_error_code])
                plc_state = PLC_ERROR

            ELSE IF Motion_Error():
                Stop_Motion_Safely()
                active_error_code = ERR_MOTION_DRIVE_ALARM
                Publish_PLC_Event(MOTION_ERROR, payload = [active_error_code])
                plc_state = PLC_ERROR

            ELSE IF Motion_Timeout():
                Stop_Motion_Safely()
                active_error_code = ERR_MOTION_TIMEOUT
                Publish_PLC_Event(MOTION_ERROR, payload = [active_error_code])
                plc_state = PLC_ERROR

            ELSE IF Position_Reached():
                plc_state = PLC_SEMI_POSITION_REACHED

        PLC_SEMI_POSITION_REACHED:
            Publish_PLC_Event(
                POSITION_REACHED,
                payload = [current_step, actual_position]
            )

            Publish_PLC_Event(
                CAPTURE_AUTH_REQUEST,
                payload = [current_step]
            )

            Start_Capture_Authorization_Timer()
            plc_state = PLC_SEMI_WAIT_CAPTURE_AUTH

        PLC_SEMI_WAIT_CAPTURE_AUTH:
            IF Capture_Authorization_Timer_Expired():
                active_error_code = ERR_COMM_PC_ACK_TIMEOUT
                Publish_PLC_Event(CAPTURE_TIMEOUT, payload = [active_error_code])
                plc_state = PLC_ERROR

            ELSE:
                Wait for CAPTURE_AUTHORIZED or CAPTURE_REJECTED event

        PLC_SEMI_OPEN_CAPTURE_WINDOW:
            Publish_PLC_Event(
                CAPTURE_WINDOW_OPEN,
                payload = [current_step]
            )

            Start_Capture_Done_Timer()
            plc_state = PLC_SEMI_WAIT_CAPTURE_DONE

        PLC_SEMI_WAIT_CAPTURE_DONE:
            IF Capture_Done_Timer_Expired():
                active_error_code = ERR_CAMERA_FRAME_TIMEOUT
                Publish_PLC_Event(CAPTURE_TIMEOUT, payload = [active_error_code])
                plc_state = PLC_ERROR

            ELSE:
                Wait for CAPTURE_DONE event

        PLC_SEMI_CLOSE_CAPTURE_WINDOW:
            Publish_PLC_Event(
                CAPTURE_WINDOW_CLOSED,
                payload = [current_step]
            )

            plc_state = PLC_SEMI_STEP_COMPLETE

        PLC_SEMI_STEP_COMPLETE:
            Publish_PLC_Event(
                STEP_COMPLETE,
                payload = [current_step]
            )

            current_step = current_step + 1
            plc_state = PLC_SEMI_LOAD_NEXT_STEP

        PLC_SEMI_RUN_COMPLETE:
            Publish_PLC_Event(RUN_COMPLETE, payload = [])
            plc_state = PLC_IDLE
```

---

## 20. PLC Error State

```text
        PLC_ERROR:
            Stop_Motion_Safely()
            Set_Error_Code(active_error_code)
            Wait for RESET_ERROR or STOP_RUN event
```

The PLC should not automatically leave `PLC_ERROR`. It should only leave after a valid reset or stop command.

---

# Part C - Camera TCP Service

## 21. Camera Service Responsibilities

```text
Opening the camera
Starting acquisition
Maintaining the latest frame
Reporting readiness
Reporting frame freshness
Saving the latest image on request
Stopping acquisition
Returning errors to the PC controller
```

The PC controller should not directly access camera internals. It should only use TCP commands.

---

## 22. Camera TCP Commands

Commands are newline-delimited JSON messages.

### 22.1 START

```json
{"cmd": "START"}
```

Expected response:

```json
{"ok": true, "status": "running"}
```

### 22.2 STOP

```json
{"cmd": "STOP"}
```

Expected response:

```json
{"ok": true, "status": "stopped"}
```

### 22.3 READY

```json
{"cmd": "READY"}
```

Expected response:

```json
{"ok": true, "ready": true}
```

### 22.4 FRESH

```json
{"cmd": "FRESH", "max_age_sec": 1.0}
```

Expected response:

```json
{"ok": true, "fresh": true}
```

### 22.5 SAVE_LATEST

```json
{
  "cmd": "SAVE_LATEST",
  "path": "captures/board_A/T/row_001/img_0001.png",
  "wait_for_new": true,
  "max_wait_sec": 2.0,
  "metadata": {
    "mode": "semi-auto",
    "step": 1,
    "x_mm": 20.0,
    "y_mm": 10.0
  }
}
```

Expected response:

```json
{
  "ok": true,
  "path": "captures/board_A/T/row_001/img_0001.png",
  "image_index": 1
}
```

### 22.6 STATUS

```json
{"cmd": "STATUS"}
```

Expected response:

```json
{
  "ok": true,
  "running": true,
  "latest_frame_age_sec": 0.04,
  "last_error": 0
}
```

---

## 23. Camera Service State List

```text
CAMERA_OFF
CAMERA_STARTING
CAMERA_RUNNING
CAMERA_STOPPING
CAMERA_ERROR
```

---

## 24. Camera Service Variables

```text
camera_state
camera_running
latest_frame
latest_frame_timestamp
last_error_code
image_index
capture_directory
```

---

## 25. Camera TCP Service Pseudocode

```text
PROGRAM Camera_TCP_Service

camera_state = CAMERA_OFF

START TCP server on localhost

LOOP forever:

    client_message = Wait_For_JSON_Command()

    IF client_message.cmd == START:
        Handle_START()

    ELSE IF client_message.cmd == STOP:
        Handle_STOP()

    ELSE IF client_message.cmd == READY:
        Handle_READY()

    ELSE IF client_message.cmd == FRESH:
        Handle_FRESH(client_message.max_age_sec)

    ELSE IF client_message.cmd == SAVE_LATEST:
        Handle_SAVE_LATEST(client_message)

    ELSE IF client_message.cmd == STATUS:
        Handle_STATUS()

    ELSE:
        Reply({
            ok: false,
            error_code: ERR_PLC_UNKNOWN_EVENT,
            message: "Unknown camera command"
        })
```

---

## 26. Camera Command Handlers

```text
FUNCTION Handle_START():

    IF camera_state == CAMERA_RUNNING:
        Reply({ok: true, status: "running"})
        RETURN

    camera_state = CAMERA_STARTING

    result = Open_Camera()
    IF result == FAILED:
        last_error_code = ERR_CAMERA_OPEN_FAILED
        camera_state = CAMERA_ERROR
        Reply({ok: false, error_code: last_error_code})
        RETURN

    result = Load_Camera_Settings()
    IF result == FAILED:
        last_error_code = ERR_CAMERA_SETTINGS_LOAD_FAILED
        camera_state = CAMERA_ERROR
        Reply({ok: false, error_code: last_error_code})
        RETURN

    Start_Continuous_Acquisition()
    camera_state = CAMERA_RUNNING

    Reply({ok: true, status: "running"})
```

```text
FUNCTION Handle_STOP():

    IF camera_state == CAMERA_RUNNING:
        Stop_Continuous_Acquisition()
        Close_Camera()

    camera_state = CAMERA_OFF

    Reply({ok: true, status: "stopped"})
```

```text
FUNCTION Handle_READY():

    ready = (
        camera_state == CAMERA_RUNNING
        AND latest_frame exists
        AND last_error_code == ERR_NONE
    )

    Reply({
        ok: true,
        ready: ready
    })
```

```text
FUNCTION Handle_FRESH(max_age_sec):

    IF latest_frame does not exist:
        Reply({ok: true, fresh: false})
        RETURN

    age = Current_Time() - latest_frame_timestamp

    IF age <= max_age_sec:
        Reply({ok: true, fresh: true, age_sec: age})
    ELSE:
        Reply({ok: true, fresh: false, age_sec: age})
```

```text
FUNCTION Handle_SAVE_LATEST(message):

    IF camera_state != CAMERA_RUNNING:
        Reply({
            ok: false,
            error_code: ERR_CAMERA_ACQUISITION_NOT_RUNNING
        })
        RETURN

    IF message.wait_for_new == true:
        Wait until latest_frame_timestamp > request_time
        OR timeout after message.max_wait_sec

    IF latest_frame is stale or missing:
        Reply({
            ok: false,
            error_code: ERR_CAMERA_STALE_FRAME
        })
        RETURN

    result = Save_Frame_To_File(latest_frame, message.path)

    IF result == SUCCESS:
        image_index = image_index + 1
        Reply({
            ok: true,
            path: message.path,
            image_index: image_index
        })

    ELSE:
        Reply({
            ok: false,
            error_code: ERR_IMAGE_SAVE_FAILED
        })
```

```text
FUNCTION Handle_STATUS():

    IF latest_frame exists:
        age = Current_Time() - latest_frame_timestamp
    ELSE:
        age = null

    Reply({
        ok: true,
        running: camera_state == CAMERA_RUNNING,
        latest_frame_age_sec: age,
        last_error: last_error_code
    })
```

---

# Part D - State Machine Interaction Summary

## 27. Manual Mode Interaction

```text
PC_MANUAL_IDLE
    -> PC_MANUAL_SEND_COMMAND
    -> PC_MANUAL_WAIT_STARTED
    -> PC_MANUAL_WAIT_RESULT
    -> optional PC_MANUAL_CAPTURE
    -> PC_MANUAL_REPORT_CAPTURE_DONE
    -> PC_MANUAL_IDLE

PLC_MANUAL_IDLE
    -> PLC_MANUAL_VALIDATE_COMMAND
    -> PLC_MANUAL_START_COMMAND
    -> PLC_MANUAL_EXECUTING
    -> PLC_MANUAL_DONE
    -> PLC_MANUAL_IDLE

Camera Service:
    PC calls READY/FRESH/SAVE_LATEST only when capture is needed
```

---

## 28. Semi-Auto Mode Interaction

```text
PC_SEMI_MONITOR_RUN
    -> PC_SEMI_CHECK_CAPTURE_READY
    -> PC_SEMI_AUTHORIZE_CAPTURE
    -> PC_SEMI_WAIT_CAPTURE_WINDOW
    -> PC_SEMI_CAPTURE_IMAGE
    -> PC_SEMI_REPORT_CAPTURE_DONE
    -> PC_SEMI_MONITOR_RUN

PLC_SEMI_LOAD_NEXT_STEP
    -> PLC_SEMI_MOVE_TO_POSITION
    -> PLC_SEMI_POSITION_REACHED
    -> PLC_SEMI_WAIT_CAPTURE_AUTH
    -> PLC_SEMI_OPEN_CAPTURE_WINDOW
    -> PLC_SEMI_WAIT_CAPTURE_DONE
    -> PLC_SEMI_CLOSE_CAPTURE_WINDOW
    -> PLC_SEMI_STEP_COMPLETE
    -> PLC_SEMI_LOAD_NEXT_STEP

Camera Service:
    PC checks READY/FRESH before CAPTURE_AUTHORIZED
    PC calls SAVE_LATEST after CAPTURE_WINDOW_OPEN
```

---

## 29. Consistency Check

This design is logically consistent because:

```text
PC_IDLE has exits to Manual Mode, Semi-Auto Mode, and Shutdown.

PLC_IDLE has exits through received mode-selection events.

Manual Mode:
    PC controls the sequence.
    PLC validates and executes each command.

Semi-Auto Mode:
    PLC controls the sequence.
    PC authorizes and performs image capture.

Camera service is separated from the PC controller.
The PC controller communicates with the camera only through local TCP.

Every PC event requires PLC acknowledgement.
Every PLC event requires PC acknowledgement.
Every camera command returns a success or failure response.

All errors converge to explicit error states.

No state relies on blind command execution.

The PLC remains motion and safety authority.
The PC remains workflow and capture authority.
The camera service remains image acquisition authority.
```
