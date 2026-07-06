# ⛔ HUMAN-ONLY ZONE — AI AGENTS MUST NOT MODIFY ANY FILE IN THIS DIRECTORY

---

## Hard Constraint

**AI agents must treat every file in this directory as strictly read-only.**

Do NOT:
- Create new files here
- Modify existing files here
- Delete files here
- Rename files here

This constraint has **no exception** and **no override**. If a task seems to require
editing files in this directory, stop and ask the human engineer to do it directly.

---

## What Is in This Directory?

This directory contains the **original hardware design specifications** and
**compiled system architecture documents** provided by the hardware vendor
and system architect. These are the source-of-truth for physical hardware behavior:

| File | Contents |
|---|---|
| `PART1_SUMMARY.md` | System summary and overview |
| `PART2_CONVEYOR.md` | Conveyor belt hardware design |
| `PART3_HMI.md` | HMI panel hardware design |
| `PART4_XY_TABLE.md` | XY table mechanical and electrical specs |
| `PART5_CAMERA.md` | Camera system hardware and optics specs |
| `PART6_DB.md` | Original database design from hardware team |
| `overall_system_architect.png` | High-level system architecture diagram |
| `duo_aoi_compiled_graphs.pdf` | Compiled hardware graphs and measurements |
| `SerialTest_API_整合指南v2.pdf` | Factory MES API integration guide (vendor doc) |

---

## How to Update These Files

Only a **human engineer** with direct knowledge of the hardware change may update
files in this directory. Steps:

1. Obtain updated specification from hardware vendor or system architect
2. Replace the file directly in this directory
3. Commit with message: `docs: update system architect overall - <reason>`
4. Note the change in `PROGRESS.md`

---

## Why This Restriction Exists

These documents describe **physical hardware behavior** that cannot be inferred
from code alone. An AI agent modifying them without hardware knowledge could
introduce subtle errors that cause:
- Incorrect XY table movement sequences
- Camera calibration errors
- PLC communication failures

The risk of an incorrect hardware spec document is higher than the cost of
requiring human involvement for updates.
