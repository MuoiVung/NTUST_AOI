# 🔬 NTUST AOI System

Welcome to the **NTUST Automated Optical Inspection (AOI)** platform. This repository contains a complete industrial solution for PCB inspection, including a PostgreSQL metadata engine, a dual-camera capture handler, and a modern React-based HMI.

---

## 📂 Project Documentation

We provide comprehensive documentation in both English and Traditional Chinese to support global deployment and local operation in Taiwan.

### 🇬🇧 English (EN)
- [**Operator Manual**](docs/EN/OPERATOR_MANUAL.md): How to use the dashboard and review results.
- [**Setup & Deployment Guide**](docs/EN/SETUP_GUIDE.md): How to install and configure the system on an IPC.
- [**System Architecture**](docs/EN/ARCHITECTURE.md): Deep dive into the IPC-Master control flow.
- [**Database Schema**](docs/EN/DATABASE_SCHEMA.md): Details on the 5-table relational structure.
- [**Data Lifecycle Flow**](docs/EN/DATA_FLOW.md): Visualizing image capture and long-term archiving.

### 🇹🇼 Traditional Chinese (ZH-TW)
- [**操作員手冊 (Operator Manual)**](docs/ZH-TW/OPERATOR_MANUAL.md)
- [**安裝與部署指南 (Setup Guide)**](docs/ZH-TW/SETUP_GUIDE.md)
- [**系統架構 (Architecture)**](docs/ZH-TW/ARCHITECTURE.md)
- [**數據庫架構 (Database Schema)**](docs/ZH-TW/DATABASE_SCHEMA.md)
- [**數據生命週期流程 (Data Flow)**](docs/ZH-TW/DATA_FLOW.md)

---

## 🚀 Quick Start

To launch the entire system (Database, Backend, and Frontend) with a single command:

1. Ensure **Docker Desktop** is running.
2. Run the system launcher:
   ```bash
   python launcher.py
   ```
3. Access the HMI at: `http://localhost:3001`

---

## 🏗 Repository Structure

```text
.
├── docs/               # Multi-language Documentation
│   ├── EN/             # English Docs
│   └── ZH-TW/          # Traditional Chinese (Taiwan) Docs
├── ntust_aoi_pcb_db/   # Backend, Database & Docker Configs
├── NTUST-AOI-UI/       # React-based HMI Frontend
├── skills/             # AI Agent helper skills
└── launcher.py         # Main system orchestrator
```

---

## 🛠 Tech Stack
- **Frontend**: React, Vite, Tailwind CSS.
- **Backend**: Python FastAPI, Uvicorn.
- **Database**: PostgreSQL (Dockerized).
- **Storage**: Local FS + Long-term Archiving logic.
