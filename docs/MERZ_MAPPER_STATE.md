# Merz Mapper - current state

> Read this first in every new chat. Update it at the end of significant work.
> Status words: **CONFIRMED** (verified/agreed), **IMPLEMENTED** (code in repo),
> **TESTED** (measured result logged), **PLANNED** (in proposal), **PROPOSED**
> (suggested, not agreed), **UNKNOWN**.

**Last updated:** 2026-11-10 (eve) | **Phase:** Hardware bring-up (pre-O1); about one week ahead of `hardware-arrival-plan.md`

## Where things stand
- **2026-11-10 Jetson bring-up (student; logbook 2026-11-10, values to fill):** JetPack 6.2.x flashed from microSD (firmware already compatible) -> **L4T R36.4.7, Ubuntu 22.04.5**; SSH, GitHub (SSH key) and Claude Code on the Jetson; **ROS 2 Humble** (`ros-humble-desktop` + `ros-dev-tools`, decisions #32); `sllidar_ros2` built; **RPLIDAR C1 publishing `/scan`** with `sllidar_c1_launch.py` (decisions #31). Rate, 1 m check and USB IDs still to log. Repo now has separate C1/S2 LIDAR configs (decisions #33). `.gitignore` now ignores `ros2_ws/src/third_party/` (e4700f8). Whole workspace NOT yet built on the Jetson.
- **2026-11-09 hardware received:** Jetson Orin Nano 8 GB Dev Kit, 4-wheel rover (12 V motors, no encoders), C920, RPLIDAR C1 (stand-in), 2x Waveshare Motor Driver HAT (PCA9685 + TB6612FNG, I2C). **D455 and S2 on the way.** Bench power from mains; battery not chosen (4S LiPo considered).
- **Motor/power plan (PROPOSED):** HATs jumper-wired to the Jetson I2C (decisions #28); kill switch on the 12 V motor supply before any wheel test (#29); 4S LiPo -> buck to 12 V (#30). PCA9685 backend for `merz_base` still to write.
- Repo: memory docs, Claude Code config (PR #1 merged 2026-11-02). All pre-hardware code written on `build/all-code` (2026-11-03), merged to `main` via PR #2.
- Safety review of `ros2_ws` (2026-11-04, branch `build/safety-review`): 3 bugs fixed with tests (limit validation in `merz_base`, wheel saturation changing the arc, blocking TF lookup in `landmark_node`); 12 open findings in `docs/software/safety-review.md`, two **High**: no stop path independent of the Jetson (decisions #19, PROPOSED) and untested wireless-gamepad link loss. Unit tests only (L0-L1); nothing run on ROS or hardware.
- Website (demonstrator) redesigned on branch `build/website-design` (PR #5, merged 2026-11-04): pan/zoom occupancy-grid map with route, swipeable photo steps synced to the map, searchable room picker, About page, accessible light/dark design, QR poster PDF, sample data. **IMPLEMENTED**; checked only in a headless browser and `pytest`, not on real phones or with rover data.
- Website v2 (PR #7, merged 2026-11-04; supersedes the PR #5 redesign): data-driven site built from a rover run by `tools/web_import.py`. Until the rover runs, it shows a clearly labelled SYNTHETIC run from `tools/synthetic_run/`. **IMPLEMENTED**, checked only with pytest and a headless browser. Design brief `docs/website/design-brief.md`; deploy via `tools/web_export.py` + GitHub Pages workflow. **Website frozen until O1 is done** (robot first).
- Hardware arrival plan (2026-11-04): `docs/planning/hardware-arrival-plan.md` - week-by-week plan from parts arrival to May 2027 (all PROPOSED). PLAN only; nothing run.
- Claude setup: 4 skills enabled on claude.ai (brain, navigation-estimation, perception-jetson, ros2-engineering-skills); Context7 + Consensus connected.
- Code status: all packages, website and evaluation tools are **IMPLEMENTED; nothing is TESTED on hardware**. On 2026-11-04 a cloud ROS 2 Humble check (RoboStack, not the Jetson's apt build) passed `colcon build` (11 packages) and `colcon test` (193 tests), after pinning `m-explore-ros2` (decisions #19b, PROPOSED); record in `docs/archive/build-progress.md`. Poses, footprint, limits, covariances and motor interface are placeholders; no trained model exists. Next: `docs/planning/hardware-arrival-plan.md` (when) + `docs/runbooks/build-guide.md` (commands).
- Config check (branch `build/config-check`, 2026-11-04): every Nav2, DWB, SLAM Toolbox, robot_localization and rf2o key in `merz_bringup/config` checked against Humble source (RESEARCH_INDEX [C1-C7]). One real bug fixed (custom no-motion BT never applied). Static checks only. Follow-up PROPOSED in decisions #18.
- 2026-11-05 merges (all **PROPOSED**; none run on ROS or hardware):
  - PR #12 `docs/research/distro-decision.md`, `docs/runbooks/jetson-bringup.md`, `docs/runbooks/o1-checklist.md`: proposes JetPack 6.2.x + Ubuntu 22.04 + Humble. **Risk: the D455 IMU may not stream on JetPack 6 (hiddraw removed)** -> day-1 go/no-go test; fallback JetPack 7.2.1 + Jazzy (OPEN_ISSUES #22, decisions #21-22). Humble/22.04 end of support May 2027 (= project end).
  - PR #10 `docs/research/literature-base.md` (71 sources, ~12 fields UNVERIFIED) + `lit-review-outline.md`; RESEARCH_INDEX updated. Proposal refs [3] [4] [6] match the verified forms.
  - PR #11 `ros2_ws/src/merz_sim`: Gazebo Fortress sim, parametric diff-drive rover, generated 3-entrance world, `odom_mode:=wheel|scan`. Unit tests only; never built or launched. Needs an x86 Ubuntu 22.04 PC (decisions #23).
  - PR #13 `perception/` + `docs/research/perception-plan.md`: non-ROS YOLO/YOLOE -> OCR -> regex prototype, `score_ocr.py` for O3, `PHOTO_CHECKLIST.md`. Synthetic images only. None of the 5 landmark classes is in COCO -> Merz Court photos needed. Found the OCR split-row bug ("M1.14" read as "14").
  - PR #9 (proposal figures) closed unmerged; branch `proposal-figures` kept for poster/report reuse.
- Repo tidy-up (PR #14, merged 2026-11-06): docs sorted into `planning/`, `runbooks/`, `software/`, `website/`, `research/`, `archive/` (index: `docs/INDEX.md`); new root README; `tools/test_md_links.py` checks Markdown links. No robot code changed.
- 2026-11-07: student ran the perception prototype on a Windows laptop (synthetic crops + laptop webcam, `--ocr rapid`). Result to be logged. OpenCV headless/GUI conflict found and documented in `perception/README.md`.
- Memory sync (branch `memory-sync-2026-11-09`): applied PR #10-#14 suggestions to decisions, OPEN_ISSUES, HARDWARE_REGISTER, RESEARCH_INDEX, SOFTWARE_ARCHITECTURE; ported the OCR split-row fix into `merz_perception` (decisions #24, unit tests only); logbook drafts for 5-7 Nov (student to add hours + reflection).
- Hardware: see HARDWARE_REGISTER (updated 2026-11-10). Rover CAD still to be shared by supervisor. Gamepad, mast, checkerboard, QR posters: already owned.
- Confirmed 2026-11-02: QR + phone image-to-image navigation for demonstrator (decisions #12); Claude use allowed (#13).
- Encoders: **none** (decisions #10, DECIDED by student 2026-11-09) -> odometry from LIDAR scan matching + D455 IMU.
- Practice: supervisor's YOLO webcam script in `tools/yolo_practice/` (not robot code); Raspberry Pi 5 with Ubuntu + ROS 2 installed for learning (distro to confirm). Laptop dual-boot abandoned (BitLocker).

## Settled by the student - do NOT raise again
(2026-11-09. The student owns engineering choices; only bring to the supervisor what truly needs him.)
- **No wheel encoders** (decisions #10). Only if the D455 IMU or scan matching fails in practice will wheel encoders be requested (decisions #22, OPEN_ISSUES #17, #22).
- **OS / JetPack / ROS 2 distro is the student's choice**, made and solved at bring-up. Not a supervisor question.
- **Testing in Merz Court is allowed** (university-supervised project).
- **No floor plan needed.** O2 wall check uses laser-meter measurements (OPEN_ISSUES #14).
- **No extra PC.** Development happens on the Jetson when it arrives; the simulation is optional.
- **Gamepad, mast, checkerboard, QR posters: already owned.**
- **Bench power from mains for now; battery decided later** (by ~end Nov, before the first corridor map).
- Focus advice on **what can be done now**, not on future hardware questions.

## Key dates
| What | Date | Notes |
| --- | --- | --- |
| D1 proposal | Fri 13 Nov 2026, 14:00 | **Submitted** (student, 2026-11-05) |
| G1 / O1 sensors + first manual map | Fri 18 Dec 2026 | last working day before leave |
| Leave (unavailable) | 19 Dec 2026 - ~4 Feb 2027 | |
| D2 poster | 23 Feb 2027 | a Tuesday; slides say "Friday" - confirm |
| O2-O8, G2-G4 | 5 Mar - 7 May 2027 | see proposal Table 1 |
| D3 demo, D4 report | May 2027 | TBC |

## Immediate next tasks (to G1)
1. Fill the blanks in logbook 2026-11-09/10 (C1 rate, 1 m check, USB IDs, versions, hours, reflection) and merge the logbook PR.
2. **Build the whole workspace on the Jetson** (plan §5.2 Thu): `rosdep install ... --skip-keys librealsense2`, `rf2o_laser_odometry` alone first (decisions #14), then `explore_lite` (test `main` vs pin, #19b), then everything; `colcon test`; log `vcs export src --exact`.
3. **LIDAR via the repo launch** (plan §5.3 Mon): `lidar_c1.yaml` / `lidar_s2.yaml` + `lidar_model:=c1|s2` IMPLEMENTED (decisions #33, static tests only) -> run `ros2 launch merz_bringup lidar.launch.py` on the Jetson; 1-minute bench bag.
4. **C920** bring-up (plan §5.3 Wed); photograph 10 Merz Court door signs -> room format (OPEN_ISSUES #23).
5. **Kill switch + motor bench test** (plan §5.4, can start early): set HAT addresses, jumper-wire, `i2cdetect`, spin each wheel from a script; then Claude Code writes the PCA9685 backend in `merz_base`.
6. Supervisor/technician: motor stall current (#28), LiPo rules + battery/buck loan (#29), rover CAD for mounts.
7. Battery decision by ~end Nov (decisions #30).
8. When the D455 arrives: librealsense RSUSB build (plan §5.2 Wed) and the **IMU go/no-go** (#22) the same day.

## Active blockers
- D455 and S2 not yet arrived (D455 needed for the IMU in the EKF; not needed for a scan-only first map).
- Battery not chosen (blocks untethered corridor driving) - OPEN_ISSUES #29.
- Motor stall current unknown - not a blocker for bench tests (HAT current limit + student's own supply); needed for battery wiring (OPEN_ISSUES #28).
- Watch: D455 IMU on JetPack 6 (#22); L4T 36.4.7 vs planned 36.5.2 (#27).

## Memory files
`docs/INDEX.md` (all docs by category) | `docs/decisions.md` (engineering decisions) | `docs/HARDWARE_REGISTER.md` | `docs/SOFTWARE_ARCHITECTURE.md` | `docs/OPEN_ISSUES.md` | `docs/RESEARCH_INDEX.md` | `docs/logbook/` | `docs/meetings/` | `docs/CLAUDE_CODE_ROADMAP.md` (code build plan, stage prompts) | `docs/runbooks/build-guide.md` (hardware procedure) | `docs/planning/hardware-arrival-plan.md` (day-by-day timeline) | `docs/planning/experiments.md` | `docs/software/database-schema.md` | `docs/archive/` (finished build-all prompt and progress)
