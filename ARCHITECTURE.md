# NTUST AOI System — Architecture Overview

> **Purpose:** High-level system overview and routing guide.
> For deep-dive protocol and schema details, follow the links in §4.

---

## 1. System Overview

The **NTUST AOI (Automated Optical Inspection)** system is a full-stack industrial
application for PCB quality inspection on a factory floor. It integrates physical
hardware (Mitsubishi FX5U PLC, dual-camera array) with a modern software stack
(FastAPI, PostgreSQL, React).

**High-level topology (development mode):**

```
+----------------------------------------------------------------------------------+
|  Factory Network (LAN)                                                           |
|                                                                                  |
|  +------------------+    SLMP/TCP      +----------+                             |
|  |  PC Controller   |<--------------->| PLC FX5U |                             |
|  |  (pc_controller) |                  | Port 15000                             |
|  |                  |  JSON/TCP        +----------+                             |
|  |                  |<--------------->|  Camera  |                             |
|  |                  |                  | Port 16000                             |
|  |                  |                  +----------+                             |
|  |     POST /images/                                                            |
|  |          |                                                                   |
|  v          v                                                                   |
|  +--------------------+                                                         |
|  |  FastAPI Backend   |<------ WebSocket ------>  React UI (Port 3001)         |
|  |  (Port 8000)       |                                                         |
|  |  PostgreSQL Pool   |                                                         |
|  +--------+-----------+                                                         |
|           | psycopg2                                                            |
|  +--------v-----------+     MinIO/NAS (external, Port 9000)                    |
|  |  PostgreSQL DB     |                                                         |
|  |  (Port 5433)       |                                                         |
|  +--------------------+                                                         |
+----------------------------------------------------------------------------------+
```

---

## 2. Repository Structure

```
NTUST_AOI/
├── Makefile                     # Unified command interface — use this first
├── README.md                    # Project overview and Quick Start
├── PROGRESS.md                  # What's done, what's pending, changelog
├── ARCHITECTURE.md              # This document — system overview and routing
├── headless_runner.py           # Underlying process manager (used by Makefile)
├── launcher.py                  # PySide6 desktop process manager (dev GUI)
├── test_sn5434.py               # End-to-end integration test
│
├── machine_control/             # [MODULE 1] Hardware Interface Layer
│   ├── README.md                # Responsibility, interfaces, how to run
│   └── ARCHITECTURE.md          # PLC protocol, camera protocol, MES integration
│
├── ntust_aoi_pcb_db/            # [MODULE 2] Backend API & Database Layer
│   ├── README.md                # Responsibility, interfaces, how to run
│   ├── ARCHITECTURE.md          # DB schema, real-time pipeline, API endpoints
│   ├── api/main.py              # FastAPI application
│   ├── sql/init.sql             # PostgreSQL schema (source of truth)
│   ├── scripts/                 # DB utilities (sync, reset, mock data)
│   └── docker-compose.yml       # PostgreSQL + pgAdmin + Nginx containers
│
├── NTUST-AOI-UI/                # [MODULE 3] Operator Dashboard (React)
│   ├── README.md                # Responsibility, interfaces, how to run
│   └── ARCHITECTURE.md          # Component tree, WebSocket flow, data patterns
│
├── simulation/                  # [MODULE 4] Hardware Simulators (dev/test only)
│   ├── README.md                # How to run simulators, switch to hardware
│   └── ARCHITECTURE.md          # Sim vs hardware mapping, protocol fidelity
│
└── docs/
    ├── GIT_WORKFLOW.md          # Branch naming, merge protocol, conflict steps
    ├── reference/
    │   ├── DATABASE_SCHEMA.md   # Full PostgreSQL schema column reference
    │   └── WORKFLOWS.md         # Operational state sequence diagrams
    ├── deployment/
    │   ├── PRODUCTION_DEPLOYMENT_ARCHITECTURE.md
    │   └── REAL_HARDWARE_INTEGRATION.md
    └── system architect overall/ # ⛔ HUMAN-ONLY — AI must not modify
```

---

## 3. Tech Stack Summary

| Module | Language | Key Technologies |
|---|---|---|
| `machine_control/` | Python 3.10 (sync) | Raw TCP sockets, psycopg2, python-dotenv |
| `ntust_aoi_pcb_db/` | Python 3.10 (async) | FastAPI, psycopg2 pool, PG NOTIFY, MinIO |
| `NTUST-AOI-UI/` | TypeScript | React 19, Vite 6, Recharts, native WebSocket |
| `simulation/` | Python 3.10 | FastAPI (shopfloor), raw TCP (PLC/camera) |
| Infrastructure | — | PostgreSQL 18, Docker Compose, Nginx, Conda |

---

## 4. Deep Dive — Per-Module Architecture

| Document | Contents |
|---|---|
| [`machine_control/ARCHITECTURE.md`](machine_control/ARCHITECTURE.md) | PLC protocol (SLMP), D-register map, camera JSON-TCP, MES API |
| [`ntust_aoi_pcb_db/ARCHITECTURE.md`](ntust_aoi_pcb_db/ARCHITECTURE.md) | DB schema, PG NOTIFY pipeline, API endpoints, image storage |
| [`NTUST-AOI-UI/ARCHITECTURE.md`](NTUST-AOI-UI/ARCHITECTURE.md) | Component tree, WebSocket flow, data fetching patterns |
| [`simulation/ARCHITECTURE.md`](simulation/ARCHITECTURE.md) | Sim vs hardware mapping, protocol fidelity, switchover steps |
| [`docs/reference/DATABASE_SCHEMA.md`](docs/reference/DATABASE_SCHEMA.md) | Full column-level PostgreSQL schema reference |
| [`docs/GIT_WORKFLOW.md`](docs/GIT_WORKFLOW.md) | Branch naming, merge conflict protocol |

---

## 5. Environment Variables

All configuration loaded from `.env` via `python-dotenv`. Never hardcode values.
Template: [`.env.example`](.env.example)

Key variables: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`,
`FASTAPI_URL`, `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`,
`MINIO_BUCKET`, `IMAGE_WATCH_DIR`
