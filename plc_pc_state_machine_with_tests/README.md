# PC / PLC State-Machine Prototype

This package contains a local prototype of the two control programs:

- `plc_sim.py`: PLC simulator with a state machine and a minimal SLMP 3E binary D-register server.
- `pc_controller.py`: PC controller with Manual Mode and Semi-Auto Mode state machines.
- `shared_protocol.py`: shared event codes, error codes, ACK codes, state enums, payload helpers, and the PC-side SLMP client.

The simulated camera writes JSON capture records instead of real images. Later, replace `SimulatedCamera` in `pc_controller.py` with the IDS camera worker.

## Run

Terminal 1:

```bash
python plc_sim.py --host 127.0.0.1 --port 15000
```

Terminal 2, Manual Mode:

```bash
python pc_controller.py --mode manual --host 127.0.0.1 --port 15000
```

Terminal 2, Semi-Auto Mode:

```bash
python pc_controller.py --mode semi-auto --host 127.0.0.1 --port 15000
```

## What is simulated

The PLC simulator exposes D registers through a minimal SLMP 3E binary TCP server.

Mailbox layout:

```text
D100 = PC event type
D101 = PC event sequence
D102-D109 = PC payload
D110 = PLC ACK sequence
D111 = PLC ACK status

D200 = PLC event type
D201 = PLC event sequence
D202-D209 = PLC payload
D210 = PC ACK sequence
D211 = PC ACK status
```

Manual Mode flow:

```text
PC sends manual move request
PLC validates payload and safety
PLC reports MANUAL_COMMAND_STARTED
PLC executes simulated motion
PLC reports MANUAL_COMMAND_DONE
PC captures simulated image
PC sends MANUAL_CAPTURE_DONE
```

Semi-Auto Mode flow:

```text
PC sends START_RUN
PLC loads scan step
PLC moves to scan position
PLC reports POSITION_REACHED
PLC requests capture authorization
PC checks camera readiness
PC sends CAPTURE_AUTHORIZED
PLC opens capture window
PC captures simulated image
PC sends CAPTURE_DONE
PLC closes window and completes step
```

## Integration direction

When replacing the simulator with a real FX5U:

1. Configure the FX5U Ethernet port for SLMP/MC 3E binary TCP.
2. Keep `pc_controller.py` and `shared_protocol.py` as the PC-side starting point.
3. Replace `SimulatedCamera` with the real IDS camera worker.
4. Implement the PLC-side mailbox and state machine in ladder/ST using the same event codes and register map.
5. Test in this order: `PC_READY`, `PLC_READY`, Manual Mode single move, Manual Mode capture, Semi-Auto one step, then full scan.
