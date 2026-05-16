# AOI System — Operator Manual

This guide explains how to use the AOI System HMI to monitor board inspections, review results, and manage system settings.

---

## 1. Dashboard Overview

The main dashboard provides a real-time list of all PCB inspection runs.

### Key Components:
- **Run List**: Displays all recent scans with their Serial Number, Board ID, and Status.
- **Search & Filters**: Use the top bar to find specific boards by Serial Number or Order ID.
- **Status Indicators**:
    - `COMPLETED`: The inspection cycle for this board is finished.
    - `PENDING`: The inspection is still in progress or waiting for data.

---

## 2. Reviewing Inspection Results

To see the detailed images of a specific board:
1. Locate the board in the **Run List**.
2. Click on the row to open the **Run Gallery**.
3. In the Gallery, you will see images from both **Top** and **Bottom** cameras.
4. Images marked with a red border indicate a `FAIL` condition. Green indicates `PASS`.
5. Click on any image to zoom in and review the defect in detail.

---

## 3. Managing System Settings

The **Settings** page allows you to adjust how the system manages data.

### Configuration Options:
- **Data Retention Policy**: Set how many days images are kept on the local IPC. After this period, they are automatically moved to long-term storage to save disk space.
- **Cloud Sync Retry**: If the network connection is lost, this defines how often the system tries to re-upload files to the server.

> [!IMPORTANT]
> Always click the **Save** button after making changes to ensure the new parameters are applied to the backend.

---

## 4. Maintenance & Troubleshooting

- **Image Not Loading**: Ensure the `IMAGE_WATCH_DIR` in the settings matches the folder where the camera software saves its output.
- **Database Connection Error**: If the dashboard shows a connection error, restart the system using the **System Launcher**.
- **Disk Full**: If you see a disk warning, check the **Data Retention Policy** and consider reducing the number of days images are stored locally.

---

## 5. Daily Checklist
1. Ensure Docker is running (Green icon in system tray).
2. Launch the system via `launcher.py`.
3. Verify that the **Run List** updates as new PCBs pass through the machine.
4. Periodically check the **Settings** to ensure the sync worker is active.
