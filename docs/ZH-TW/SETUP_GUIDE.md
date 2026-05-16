# AOI 系統在 AAEON 模組化 HMI 面板電腦上的安裝與部署指南

本文件提供了在 AAEON 模組化 HMI 面板電腦上部署 `aoidb` 源代碼（PostgreSQL 數據庫與影像存儲）的分步說明。

---

## 1. 需求與環境準備

AAEON 模組化 HMI 面板電腦（例如 OMNI 系列）通常搭載 **Windows 10/11 IoT Enterprise** 或 **Ubuntu Linux**。由於 `aoidb` 系統已完全 Docker 化，它可以高效地在兩個平台上運行。

### HMI 必備軟體：
1. **Docker & Docker Compose**：
   - *Windows*: 安裝 [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/) (確保啟用 WSL 2 後端)。
   - *Ubuntu Linux*: 通過終端安裝 Docker Engine 和 Docker Compose 插件 (`apt install docker-ce docker-compose-plugin`)。
2. **Python 3.9+** (可選，但若要直接在 HMI 環境運行數據模擬或自動化腳本如 `generate_mock_data.py` 則為必需)。
3. **Git** (若要克隆倉庫，或直接通過 USB/網絡傳輸源代碼)。

---

## 2. 系統設置

### 步驟 1：將源代碼複製到 HMI
1. 在 HMI 上創建專用目錄，例如：`D:\AOI\aoidb` (Windows) 或 `/opt/aoi/aoidb` (Linux)。
2. 將當前 `aoidb` 文件夾的全部內容複製到該目錄中。確保文件夾結構（特別是 `nginx`, `sql`）保持完整。

### 步驟 2：配置 `.env` 文件
1. 打開終端 (Windows 上的命令提示字元 / PowerShell，Linux 上的 bash) 並進入複製源代碼的目錄。
2. 初始化環境變量文件：
   - **Windows**: `copy .env.example .env`
   - **Linux**: `cp .env.example .env`
3. 編輯 `.env` 文件（使用記事本, vim, nano）並修改參數以確保安全：
   ```env
   DB_ROOT_USER=my_secure_admin       # 修改 Postgres 用戶名
   DB_ROOT_PASSWORD=my_secure_pass!   # 修改 Postgres 密碼
   APP_DOMAIN=http://<HMI_STATIC_IP>:8080 # 設置 HMI 在區網內的固定 IP
   ```

### 步驟 3：構建與啟動服務
由於所有設置都已在 `docker-compose.yml` 中定義，啟動應用程序非常簡單。在包含 `docker-compose.yml` 的目錄中運行以下命令：

```bash
docker-compose up -d --build
```

**此命令將初始化 3 個服務：**
- `postgres`：管理元數據的 PostgreSQL 數據庫 (端口 `5432`)。
- `pgadmin`：用於查看和管理數據庫的 Web UI (端口 `5050`)。
- `image_server`：託管影像下載鏈接的 Nginx 服務器 (端口 `8080`)。

---

## 3. 驗證

容器成功啟動後，請從 HMI 的瀏覽器進行驗證：

1. **檢查容器狀態**：運行 `docker ps` 確認 `aoi_postgres`, `aoi_pgadmin` 和 `aoi_image_server` 正在運行。
2. **訪問數據庫管理 UI**：
   - 打開網頁瀏覽器並訪問：[http://localhost:5050](http://localhost:5050)
   - 登錄信息：
     - **Email**: `admin@aoi.com` (在 `docker-compose.yml` 中配置)
     - **Password**: *[您在 `.env` 中設置的密碼]*

---

## 4. 集成外部相機 (文件夾監控)

如果您的 AOI 系統依賴第三方相機軟體將影像保存到 HMI 上的固定目錄，您可以使用內置的 `folder_monitor.py` 腳本。該腳本在背景運行，監控特定文件夾，並自動將影像元數據推送到 PostgreSQL 數據庫。

1. **安裝 Python 需求 (若尚未安裝)**：
   ```bash
   pip install -r requirements.txt
   ```
2. **配置監控目錄**：
   在您的 `.env` 文件中，指定目標目錄（預設為 `./images/raw_incoming`）：
   ```env
   IMAGE_WATCH_DIR=D:\Path\To\Your\Camera\Folder
   ```
3. **運行監控腳本**：
   打開新終端，激活 Python 環境，然後運行：
   ```bash
   python scripts/folder_monitor.py
   ```
   *註：您可以通過任務排程器 (Task Scheduler) 或將 `.bat` 快捷方式放入 `shell:startup` 文件夾，設置此 Python 腳本在 Windows 啟動時自動運行。*

---

## 5. 啟用自動啟動

在工業環境中，AOI DB 系統必須在機台通電時保持開啟。

- **在 Windows IoT / 10 / 11**：
  - 在 Docker Desktop 中：進入 `Settings > General` 並勾選 `"Start Docker Desktop when you log in"` (或者將其配置為背景服務)。
  - 由於 `docker-compose.yml` 為所有服務指定了 `restart: always`，當 Docker Desktop 啟動時，容器將自動重啟，無需手動干預。
  
- **在 Ubuntu Linux**：
  - 啟用 Docker 守護進程開機自啟：`sudo systemctl enable docker`
  - 服務將通過 `restart: always` 的 Compose 規則自動上線。

---

## 6. IPC (工業電腦) 最佳實踐

1. **固定 IP (Static IP)**：您 ***必須*** 在相機和 AI 處理節點用於訪問 HMI 的區域網接口上分配固定 IP（或保留網絡 MAC 地址）。外部節點使用此 IP 連接（例如：`192.168.1.100:8000`），而非 `localhost`。
2. **存儲耐用性 (讀/寫)**：`./images/` 和 `./postgres_data/` 卷將快速增長。為防止操作系統硬碟 (C:\) 磨損，我們強烈建議將 Docker 工作空間和這些數據卷移至獨立分區（例如 `D:\`）或設計用於持續寫入循環的耐用、工業級 SSD。
3. **防火牆配置**：如果本地操作系統防火牆已啟用，請確保允許端口 `5432` (數據庫直接連接) 和 `8080` (影像下載) 的入站流量。
