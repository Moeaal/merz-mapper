# Merz Mapper - current state

> Read this first in every new chat. Update it at the end of significant work.
> Status words: **CONFIRMED** (verified/agreed), **IMPLEMENTED** (code in repo),
> **TESTED** (measured result logged), **PLANNED** (in proposal), **PROPOSED**
> (suggested, not agreed), **UNKNOWN**.

**Last updated:** 2026-11-02 | **Phase:** Proposal + hardware procurement (pre-O1)

## Where things stand
- Repo: folder skeleton, templates, memory docs, Claude Code config (PR #1 merged 2026-11-02). **No ROS 2 code yet.**
- Claude setup: 4 skills enabled on claude.ai (brain, navigation-estimation, perception-jetson, ros2-engineering-skills); Context7 + Consensus connected.
- Nothing is IMPLEMENTED or TESTED. Every robot capability is PLANNED.
- Hardware: parts list ordered by supervisor (2026-11-02); delivery date TBC. Gamepad, mast, mounts, checkerboard, QR posters not yet ordered.
- Rover: university-built simple rover; spec unknown until received.
- Encoders: supervisor suggests none (decisions #10, PROPOSED) -> odometry from LIDAR scan matching + D455 IMU.
- Practice: supervisor's YOLO webcam script in `tools/yolo_practice/` (not robot code); Raspberry Pi 5 with Ubuntu + ROS 2 installed for learning (distro to confirm). Laptop dual-boot abandoned (BitLocker).

## Key dates
| What | Date | Notes |
| --- | --- | --- |
| D1 proposal | Fri 13 Nov 2026, 14:00 | 3 pages, third person, IEEE |
| G1 / O1 sensors + first manual map | Fri 18 Dec 2026 | last working day before leave |
| Leave (unavailable) | 19 Dec 2026 - ~4 Feb 2027 | |
| D2 poster | 23 Feb 2027 | a Tuesday; slides say "Friday" - confirm |
| O2-O8, G2-G4 | 5 Mar - 7 May 2027 | see proposal Table 1 |
| D3 demo, D4 report | May 2027 | TBC |

## Immediate next tasks (to G1)
1. Meeting 2026-11-02: questions in `docs/meetings/2026-11-02.md` (delivery dates, rover handover, encoders, distro).
2. Fix proposal before D1 (OPEN_ISSUES #6-9, #15: remove "wheel odometry" if no encoders).
3. Order remaining parts (gamepad, mast, mounts, checkerboard, QR posters).
4. ROS 2 tutorials on the Pi 5 (nodes, topics, launch).
5. Inspect rover on arrival; fill HARDWARE_REGISTER.
6. Flash Jetson, install ROS 2, bring up each sensor one at a time, record bags.

## Active blockers
- Rover spec unknown until received (OPEN_ISSUES #1).
- ROS 2 distro / JetPack undecided (OPEN_ISSUES #2).
- Parts delivery date unknown.

## Memory files
`docs/decisions.md` (engineering decisions) | `docs/HARDWARE_REGISTER.md` |
`docs/SOFTWARE_ARCHITECTURE.md` | `docs/OPEN_ISSUES.md` | `docs/RESEARCH_INDEX.md` |
`docs/logbook/` | `docs/meetings/`
