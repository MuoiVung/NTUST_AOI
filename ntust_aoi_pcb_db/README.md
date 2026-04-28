# AOI Image Storage System (PostgreSQL)

This project implements a high-performance **PostgreSQL + File System** storage architecture for an Automated Optical Inspection (AOI) system.

## 1. Quick Start (Hosting)
You can host the database and admin tools via Docker.

```bash
docker-compose up -d
```

### Services
*   **PostgreSQL Database**: Port `5432`
*   **Web UI (pgAdmin 4)**: [http://localhost:5050](http://localhost:5050)
    *   **Email**: `<Your Admin Email>`
    *   **Password**: *See `DB_ROOT_PASSWORD` in `.env`*
*   **Image Server (Nginx)**: [http://localhost:8080](http://localhost:8080) (Serves static images)

> **To Stop:**
> ```bash
> docker-compose down
> ```

---

## 2. Configuration (`.env`)
The system relies on a `.env` file for security. 
Copy the example file and update it with your own secure passwords:

```bash
cp .env.example .env
```
*   `DB_ROOT_USER` / `DB_ROOT_PASSWORD`: Superuser credentials for Postgres and pgAdmin.
*   `APP_DOMAIN`: The base URL for the image server (e.g., `http://<hostname>.local:8080`).

---

## 3. Installation & Setup Guide

### Step 1: Initialize Configuration (.env)
The system uses the `.env` file to securely store configuration details (database passwords, image folder paths, etc.).
Create the `.env` file from the provided example template:

**For macOS/Linux:**
```bash
cp .env.example .env
```
**For Windows:**
```cmd
copy .env.example .env
```
*Open the newly created `.env` file and adjust the parameters (such as `IMAGE_WATCH_DIR`) to fit your machine's setup.*

### Step 2: Start the Database (Docker)
Ensure Docker and Docker Compose are installed.
Run the database system (PostgreSQL) and the Image Server (Nginx) using the following command:
```bash
docker-compose up -d
```
*To stop the system, use the command: `docker-compose down`*

### Step 3: Install Python Environment (Virtual Environment)
A virtual environment helps isolate the Python libraries for this project, avoiding conflicts with other projects.
```bash
# Create the virtual environment (only needed once)
# On macOS/Linux:
python3 -m venv venv
# On Windows:
python -m venv venv

# Activate the virtual environment (You must run this command every time you open a new Terminal)
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

# Install the required libraries
pip install -r requirements.txt
```

### Step 4: Run Functional Scripts

#### A. Run the Folder Monitor (Automatically log new images)
This script continuously monitors the `IMAGE_WATCH_DIR` directory. When a new image is copied or downloaded into this folder, its name and size will be automatically saved to the Database.
```bash
python scripts/folder_monitor.py
```
*(Note: You must have the `venv` activated as in Step 3 to run this script)*

#### B. Initialize Database and Generate Mock Data (For Testing)
If you want to automatically generate a set of fake image data (Mock data) along with records saved to the DB for performance testing:
```bash
# Generate 1 run with 5 images
python scripts/generate_mock_data.py --runs 1 --images_per_run 5

# Generate a larger dataset
python scripts/generate_mock_data.py --runs 100 --images_per_run 20
```

#### C. Reset Database
Clear all data in the Database and start over from scratch:
```bash
python scripts/reset_db.py
```

---

## 4. Connection Guide

### A. Web UI (pgAdmin 4)
1.  Open [http://localhost:5050](http://localhost:5050).
2.  Login with:
    *   **Email**: `<Your Admin Email>`
    *   **Password**: *Your DB_ROOT_PASSWORD*
3.  Add Server:
    *   **Host**: `postgres` (internal Docker DNS)
    *   **Port**: `5432`
    *   **Username**: *Your DB_ROOT_USER*
    *   **Password**: *Your DB_ROOT_PASSWORD*
    *   **Database**: `pcb_aoi_db`

### B. Accessing Images & Hostname
The system uses the `APP_DOMAIN` defined in `.env` (e.g. `http://<HOST_IP>:8080`).
*   **Images**: Stored images can be accessed via `{APP_DOMAIN}/images/{relative_path}`.
*   **PgAdmin**: `{APP_DOMAIN_HOST}:5050` (e.g. `http://<HOST_IP>:5050`)

To find your host IP:
**On macOS:**
```bash
ipconfig getifaddr en0
```
**On Windows:**
```cmd
ipconfig
# Look for "IPv4 Address"
```
**On Linux:**
```bash
hostname -I
```

