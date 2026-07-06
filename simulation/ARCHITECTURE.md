# simulation — Architecture Reference

> Read this when you need to understand **how simulators map to real hardware** or
> how to switch from simulation to real devices.
> For how to run the simulators, see [`README.md`](README.md).

---

## 1. Simulation vs. Hardware Mapping

| Simulator | Port | Protocol | Replaced By (Production) |
|---|---|---|---|
| `plc_sim.py` | 15000 | SLMP 3E Binary TCP | Mitsubishi FX5U PLC (real IP, same port) |
| `camera_sim.py` | 16000 | JSON-over-TCP | Physical camera SDK service (same JSON interface) |
| `shopfloor_sim.py` | 9090 | HTTP REST (FastAPI) | Factory MES HTTPS endpoint |

**No code changes required to switch to hardware.** Only CLI arguments change:

```bash
# Simulation (default dev mode)
python pc_controller.py \
  --plc-host 127.0.0.1 --plc-port 15000 \
  --camera-host 127.0.0.1 --camera-port 16000 \
  --api-mode fixture

# Real hardware
python pc_controller.py \
  --plc-host 192.168.3.250 --plc-port 15000 \
  --camera-host 192.168.3.100 --camera-port 16000 \
  --api-mode real
```

See [`docs/deployment/REAL_HARDWARE_INTEGRATION.md`](../docs/deployment/REAL_HARDWARE_INTEGRATION.md)
for the full hardware switchover guide.

---

## 2. Protocol Fidelity

### `plc_sim.py` — PLC Simulator
- Implements the full SLMP 3E Binary TCP server
- Responds to all EventCodes the PC controller sends
- Simulates XY table movement with configurable delay
- Does **not** simulate PLC hardware faults or E-stop conditions

### `camera_sim.py` — Camera Simulator
- Implements the full JSON-over-TCP server on port 16000
- On `SAVE_LATEST`: selects a random image from `mock_images/` folder
  (or generates a placeholder if the folder is empty/missing)
- Does **not** simulate camera focus errors or exposure settings

### `shopfloor_sim.py` — MES Simulator
- Implements `GET /api/v1/shopfloor/info?sn=<SERIAL>`
- Returns static fixture data: board dimensions, M_NO, SemiModel
- Does **not** implement authentication or rate limiting

---

## 3. `shared_protocol.py` Sync Rule

`simulation/shared_protocol.py` is a **manual copy** of
`machine_control/shared_protocol.py`.

When updating D-register addresses or EventCodes in `machine_control/shared_protocol.py`,
**immediately update `simulation/shared_protocol.py` to match**.

Both files must stay in sync — divergence causes the simulator to misinterpret
commands from `pc_controller.py`.

> **Never import from `simulation/` in production modules.**
> Dependency must flow: `machine_control/` → hardware, never ← simulation.
