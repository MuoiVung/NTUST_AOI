# AOI System Operational Workflow

This document outlines the operational sequences of the NTUST Automated Optical Inspection (AOI) system. It focuses on the logical steps and actions taken by each component, written in plain language for clarity.

## 1. System Components

The system consists of the following interacting nodes:
*   **The Machine (PLC)**: The physical robot that controls the XY Table, the conveyor belt, and the lighting.
*   **Main Computer (PC)**: The central processing unit. It coordinates the machine's movements, triggers the cameras, and processes data.
*   **Camera System**: Dual-camera setup (Top and Bottom) that takes high-resolution photos of the circuit boards.
*   **Factory System (MES)**: The external factory database that provides board dimensions based on the barcode.
*   **Database & Dashboard**: The local repository and user interface that stores inspection histories and displays live images.

---

## 2. Main Inspection Workflow

The following sequence diagram illustrates a complete inspection cycle, from startup to the completion of a board.

```mermaid
sequenceDiagram
    participant Operator as Operator
    participant DB as Dashboard & Database
    participant PC as Main Computer (PC)
    participant Camera as Cameras
    participant MES as Factory System
    participant Machine as The Machine (PLC)

    %% Phase 1: Initialization
    Note over Operator,Machine: Phase 1: Initialization & Handshake
    PC->>Machine: Establish network connection
    PC->>DB: Update machine status to Connected
    PC->>Machine: Send system ready signal
    Machine-->>PC: Acknowledge signal
    Machine->>PC: Confirm machine is ready
    PC-->>Machine: Acknowledge confirmation
    Note over PC,Machine: Both systems enter Standby mode

    %% Phase 2: Barcode Scan & Verification
    Note over Operator,Machine: Phase 2: Barcode Scanning & Verification
    Operator->>DB: Scan circuit board barcode
    DB->>PC: Notify PC of new barcode
    PC->>MES: Request board dimensions for barcode
    MES-->>PC: Return board length and width
    PC->>PC: Calculate required inspection points based on size

    %% Phase 3: Preparing the Machine
    Note over Operator,Machine: Phase 3: Preparing the Inspection Route
    PC->>DB: Create a new inspection record
    PC->>Machine: Notify start of recipe download (Total points)
    Machine-->>PC: Acknowledge
    PC->>Machine: Send X and Y coordinates for all inspection points
    PC->>Machine: Notify end of recipe download
    Machine->>PC: Confirm recipe is loaded
    PC-->>Machine: Acknowledge
    PC->>Machine: Command machine to start inspection

    %% Phase 4: Taking Photos
    Note over Operator,Machine: Phase 4: The Inspection Loop
    loop For every inspection point
        Machine->>PC: Notify machine is moving to next point
        PC-->>Machine: Acknowledge
        Note over Machine: The Machine moves the XY table
        
        Machine->>PC: Notify machine has arrived at destination
        PC-->>Machine: Acknowledge
        
        Machine->>PC: Request permission to capture image
        PC-->>Machine: Grant permission
        
        Note right of PC: The PC coordinates the hardware
        PC->>Camera: Trigger image capture (Top & Bottom)
        Camera-->>PC: Return captured images
        
        Note left of PC: Saving and displaying results
        PC->>DB: Save images and inspection metadata
        DB-->>Operator: Display new images on the dashboard
        
        PC->>Machine: Confirm image capture is complete
        Machine-->>PC: Acknowledge
        Machine->>PC: Notify camera window is closed
        PC-->>Machine: Acknowledge
        Machine->>PC: Mark current inspection point as completed
        PC-->>Machine: Acknowledge
    end

    %% Phase 5: Finishing Up
    Note over Operator,Machine: Phase 5: Run Completion
    Machine->>PC: Notify all inspection points are completed
    PC-->>Machine: Acknowledge
    PC->>DB: Mark the inspection record as Completed
    PC->>Machine: Send system ready signal for the next board
    Note over PC,Machine: Both systems return to Standby mode
```

---

## 3. Synchronization Mechanism

To ensure the machine and the computer never lose synchronization, they rely on a strict handshake protocol:
*   **Event Polling**: The Main Computer continuously monitors the Machine's memory registers to detect new events or status changes.
*   **Acknowledgment (ACK)**: Every time the Machine sends an event (like "arrived at destination"), the Computer must send back an acknowledgment. The Machine will pause and wait indefinitely until it receives this acknowledgment, ensuring no step or photo is ever skipped.
*   **Safety Heartbeat**: Both the Machine and the Computer continuously exchange a heartbeat signal. If the connection is lost or unplugged, the heartbeat stops, and the Machine automatically locks its motors within 5 seconds to prevent accidents.
