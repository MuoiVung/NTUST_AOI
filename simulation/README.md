# simulation — Module README

## Responsibility

This module contains **software simulators** for all physical hardware. It exists solely for development and testing — no production code depends on it.

## Files

| File | Simulates | Port | Protocol |
|---|---|---|---|
| `plc_sim.py` | Mitsubishi FX5U PLC | 15000 | SLMP 3E Binary TCP |
| `camera_sim.py` | Camera service (IDS/Basler) | 16000 | JSON-over-TCP |
| `shopfloor_sim.py` | Factory MES REST API | 9090 | HTTP (FastAPI) |
| `shared_protocol.py` | Copy of `machine_control/shared_protocol.py` | — | — |

## How to Switch Between Simulation and Real Hardware

Change only the CLI arguments when launching `pc_controller.py`:

```bash
# Simulation (default dev mode)
python pc_controller.py --plc-host 127.0.0.1 --plc-port 15000 --camera-host 127.0.0.1 --camera-port 16000

# Real hardware
python pc_controller.py --plc-host 192.168.3.250 --plc-port 15000 --camera-host 192.168.3.100 --camera-port 16000
```

No source code changes required to switch modes.

## Run Simulators

```bash
conda activate aoi_env
cd simulation

# Terminal 1: PLC simulator
python plc_sim.py --host 127.0.0.1 --port 15000

# Terminal 2: Camera simulator  
python camera_sim.py --host 127.0.0.1 --port 16000

# Terminal 3: MES/Shopfloor API
python shopfloor_sim.py  # port 9090
```

Or start everything at once from the repo root:

```bash
python headless_runner.py start
```

## Critical Constraints

1. **`shared_protocol.py` in this directory is a COPY** of `machine_control/shared_protocol.py`. If you update D-register addresses or EventCodes in one, update the other. Both files must stay in sync.
2. **Never import from `simulation/` in production modules.** The dependency must flow one way only: `machine_control/` → hardware; never `machine_control/` → `simulation/`.
