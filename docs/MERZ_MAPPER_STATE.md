# Merz Mapper - current state

> Read this first in every new chat. Update it at the end of significant work.
> Status words: **CONFIRMED** (verified/agreed), **IMPLEMENTED** (code in repo),
> **TESTED** (measured result logged), **PLANNED** (in proposal), **PROPOSED**
> (suggested, not agreed), **UNKNOWN**.

**Last updated:** 2026-11-04 | **Phase:** Proposal + hardware procurement (pre-O1)

## Where things stand
- Repo: memory docs, Claude Code config (PR #1 merged 2026-11-02). All pre-hardware code written on `build/all-code` (2026-11-03), merged to `main` via PR #2.
- Safety review of `ros2_ws` (2026-11-04, branch `build/safety-review`): 3 bugs fixed with tests (limit validation in `merz_base`, wheel saturation changing the arc, blocking TF lookup in `landmark_node`); 12 open findings in `docs/REVIEW.md`, two **High**: no stop path independent of the Jetson (decisions #19, PROPOSED) and untested wireless-gamepad link loss. Unit tests only (L0-L1); nothing run on ROS or hardware.
- Claude setup: 4 skills enabled on claude.ai (brain, navigation-estimation, perception-jetson, ros2-engineering-skills); Context7 + Consensus connected.
- Code status: all packages, website and evaluation tools are **IMPLEMENTED; nothing is TESTED**. No `colcon build` has been run and nothing has run on hardware; only pure-Python unit tests, on Windows (`docs/BUILD_PROGRESS.md`). Poses, footprint, limits, covariances and motor interface are placeholders; no trained model exists. Next: `docs/BUILD_GUIDE.md`.
- Config check (branch `build/config-check`, 2026-11-04): every Nav2, DWB, SLAM Toolbox, robot_localization and rf2o key and plugin name in `merz_bringup/config` checked against Humble source (RESEARCH_INDEX [C1-C7]). One real bug fixed: the custom no-motion BT was never applied (missing `default_nav_to_pose_bt_xml` key, so Nav2 used its stock tree with Spin/BackUp). Static checks only; still not run under ROS. Follow-up PROPOSED in decisions #18.
- Hardware: parts list ordered by supervisor; delivery expected within days of 3 Nov, rover arriving with them; rover CAD to be shared. Gamepad, mast, mounts, checkerboard, QR posters not yet ordered.
- Rover: university-built simple rover; spec unknown until received.
- Confirmed 2026-11-02: QR + phone image-to-image navigation for demonstrator (decisions #12); Claude use allowed (#13).
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
1. Send proposal draft to Dr Wright before next meeting; fix OPEN_ISSUES #6-9 first. D1 due 13 Nov 14:00.
2. ROS 2 tutorials on the Pi 5 (nodes, topics, launch). Review the `build/all-code` pull request; first real check is `colcon build` on the Pi, including rf2o (decisions #14).
3. 3D design of mast/sensor mounts once rover CAD arrives.
4. Inspect parts and rover on arrival; fill HARDWARE_REGISTER.
5. Next meeting: encoders (#10), distro, floor plan, test permission, unlisted parts (see minutes 2026-11-02 "Not covered").
6. Flash Jetson, install ROS 2, bring up each sensor one at a time, record bags.

## Active blockers
- Rover spec unknown until received (OPEN_ISSUES #1).
- ROS 2 distro / JetPack undecided (OPEN_ISSUES #2).
- Encoder plan and proposal wording ("wheel odometry") unresolved until next meeting (OPEN_ISSUES #15).

## Memory files
`docs/decisions.md` (engineering decisions) | `docs/HARDWARE_REGISTER.md` |
`docs/SOFTWARE_ARCHITECTURE.md` | `docs/OPEN_ISSUES.md` | `docs/RESEARCH_INDEX.md` |
`docs/logbook/` | `docs/meetings/` | `docs/CLAUDE_CODE_ROADMAP.md` (code build plan, stage prompts) | `docs/BUILD_GUIDE.md` (hardware procedure) | `docs/BUILD_PROGRESS.md` | `docs/EXPERIMENTS.md` | `docs/DATABASE_SCHEMA.md`
