# Setup & Deployment Guide for AOI System on AAEON Modular HMI Panel PC

This document provides step-by-step instructions to deploy the `aoidb` source code (PostgreSQL database and image storage) on AAEON's Modular HMI Panel PC.

---

## 1. Requirements & Environment Preparation

AAEON Modular HMI Panel PCs (e.g., OMNI series) usually come with **Windows 10/11 IoT Enterprise** or **Ubuntu Linux**. Because the `aoidb` system is fully Dockerized, it can run efficiently on both platforms.

### Required Software on the HMI:
1. **Docker & Docker Compose**: 
   - *Windows*: Install [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/) (make sure to enable the WSL 2 backend).
   - *Ubuntu Linux*: Install Docker Engine and the Docker Compose plugin via Terminal (`apt install docker-ce docker-compose-plugin`).
2. **Python 3.9+** (optional, but necessary if you want to run data simulation or automation scripts like `generate_mock_data.py` directly from the HMI environment).
3. **Git** (if you want to clone the repo, or you can simply transfer the source code via USB/network).

---

## 2. Setting Up the System

### Step 1: Copy Source Code to the HMI
1. Create a dedicated directory on the HMI, for example: `D:\AOI\aoidb` (Windows) or `/opt/aoi/aoidb` (Linux).
2. Copy the entire contents of the current `aoidb` folder into it. Ensure the folder structure (especially `nginx`, `sql`) remains intact.

### Step 2: Configure the `.env` File
1. Open a Terminal (Command Prompt / PowerShell on Windows, bash on Linux) and navigate to the directory where you copied the source.
2. Initialize the environment variable file:
   * **Windows**: `copy .env.example .env`
   * **Linux**: `cp .env.example .env`
3. Edit the `.env` file (using Notepad, vim, nano) and modify the values for security:
   ```env
   DB_ROOT_USER=my_secure_admin       # Change Postgres username
   DB_ROOT_PASSWORD=my_secure_pass!   # Change Postgres password
   APP_DOMAIN=http://<HMI_STATIC_IP>:8080 # Set the static IP of your HMI in the LAN
   ```

### Step 3: Build and Start Services
Since all settings are defined in `docker-compose.yml`, starting the application is very simple. Run the following command in the directory containing `docker-compose.yml`:

```bash
docker-compose up -d --build
```

**This command will initialize 3 services:**
* `postgres`: The PostgreSQL database managing the metadata (Port `5432`).
* `pgadmin`: The Web UI to view and manage your database (Port `5050`).
* `image_server`: The Nginx server hosting the direct image download links (Port `8080`).

---

## 3. Verification

Once the containers start successfully, verify the deployment from the HMI's browser:

1. **Check Container Status**: Run `docker ps` to verify that `aoi_postgres`, `aoi_pgadmin` and `aoi_image_server` are up and running.
2. **Access the Database Management UI**:
   * Open a web browser and go to: [http://localhost:5050](http://localhost:5050)
   * Login with: 
     * **Email**: `admin@aoi.com` (configured in `docker-compose.yml`)
     * **Password**: *[The password you set in `.env`]*

---

## 4. Integrating External Cameras (Folder Monitoring)

If your AOI system relies on a third-party camera software that saves images locally to a fixed directory on the HMI, you can use the included `folder_monitor.py` script. This script runs in the background, watches a specific folder, and automatically pushes the image metadata into the PostgreSQL database.

1. **Install Python Requirements (if not already done)**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Configure the Watch Directory**:
   In your `.env` file, you can specify the target directory (default is `./images/raw_incoming`):
   ```env
   IMAGE_WATCH_DIR=D:\Path\To\Your\Camera\Folder
   ```
3. **Run the Monitor Script**:
   Open a new terminal, activate the Python environment, and run:
   ```bash
   python scripts/folder_monitor.py
   ```
   *Note: You can configure this Python script to start automatically on Windows boot using Task Scheduler or placing a `.bat` shortcut in the `shell:startup` folder.*

---

## 5. Enable Auto-Start

In an industrial environment, the AOI DB system must stay active whenever the machine is powered on.

* **On Windows IoT / 10 / 11**:
  * In Docker Desktop: Navigate to `Settings > General` and check `"Start Docker Desktop when you log in"` (Alternatively, configure it as a background service).
  * Because `docker-compose.yml` specifies `restart: always` for all services, the containers will automatically restart when Docker Desktop launches without further manual input.
  
* **On Ubuntu Linux**:
  * Enable the Docker daemon to start on boot: `sudo systemctl enable docker`
  * Services will automatically come online thanks to the `restart: always` compose rule.

---

## 6. IPC (Industrial PC) Best Practices

1. **Static IP**: You ***must*** assign a Static IP (or reserve a network MAC address) on the LAN interface the cameras and AI processing nodes will use to access the HMI. External nodes connect using this IP (e.g., `192.168.1.100:8000`), not `localhost`.
2. **Storage Endurance (Read/Write)**: The `./images/` and `./postgres_data/` volumes will grow rapidly. To prevent wear on the OS drive (C:\), we highly recommend moving the Docker working directory space and these data volumes to a separate partition (e.g., `D:\`) or onto a durable, industrial-grade SSD designed for continuous write cycles.
3. **Firewall Configurations**: Make sure to allow incoming traffic on ports `5432` (Direct DB connection) and `8080` (Image Download) if the local operating system firewall is active.
