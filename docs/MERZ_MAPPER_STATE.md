# Merz Mapper - current state

> Read this first in every new chat. Update it at the end of significant work.
> Status words: **CONFIRMED** (verified/agreed), **IMPLEMENTED** (code in repo),
> **TESTED** (measured result logged), **PLANNED** (in proposal), **PROPOSED**
> (suggested, not agreed), **UNKNOWN**.

**Last updated:** 2026-11-19 | **Phase:** Hardware bring-up (pre-O1); **on track for G1 (18 Dec)**, about 1-1.5 weeks ahead on the work in the student's control (progress check below)

## Where things stand
- **2026-11-10 Jetson bring-up (student; logbook 2026-11-10, values to fill):** JetPack 6.2.x flashed from microSD (firmware already compatible) -> **L4T R36.4.7, Ubuntu 22.04.5**; SSH, GitHub (SSH key) and Claude Code on the Jetson; **ROS 2 Humble** (`ros-humble-desktop` + `ros-dev-tools`, decisions #32); `sllidar_ros2` built; **RPLIDAR C1 publishing `/scan`** with `sllidar_c1_launch.py` (decisions #31). Rate, 1 m check and USB IDs still to log. Repo now has separate C1/S2 LIDAR configs (decisions #33). `.gitignore` now ignores `ros2_ws/src/third_party/` (e4700f8). **Whole workspace built on the Jetson** (all 12 packages; realsense not yet). `colcon test`: 389 tests, 41 third-party lint failures (ignored), 1 ours (merz_sim launch test path; fixed on `logbook/2026-11-10-build`). LIDAR bench bag: 10.0 Hz. Test fix merged (PR #20). **C920 running** via `merz_bringup c920.launch.py` (student report; rate and USB ID to log).
- **2026-11-09 hardware received:** Jetson Orin Nano 8 GB Dev Kit, 4-wheel rover (12 V motors, no encoders), C920, RPLIDAR C1 (stand-in), 2x Waveshare Motor Driver HAT (PCA9685 + TB6612FNG, I2C). **D455 and S2 on the way.** Bench power from mains; battery not chosen (4S LiPo considered).
- **Motor/power plan (PROPOSED):** HATs jumper-wired to the Jetson I2C (decisions #28); kill switch on the 12 V motor supply before any wheel test (#29); 4S LiPo -> buck to 12 V (#30). Wheels spin from the Jetson (bench test 2026-11-16); PCA9685 backend written (decisions #35).
- Repo: memory docs, Claude Code config (PR #1 merged 2026-11-02). All pre-hardware code written on `build/all-code` (2026-11-03), merged to `main` via PR #2.
- Safety review of `ros2_ws` (2026-11-04, branch `build/safety-review`): 3 bugs fixed with tests (limit validation in `merz_base`, wheel saturation changing the arc, blocking TF lookup in `landmark_node`); 12 open findings in `docs/software/safety-review.md`, two **High**: no stop path independent of the Jetson (decisions #19, PROPOSED) and wireless-gamepad link loss (TESTED 2026-11-19, lifted: wheels stop). Other findings: unit tests only.
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

## Progress check (2026-11-19, against the proposal Gantt and `hardware-arrival-plan.md`)
- **Plan:** week 2 (16-20 Nov) = Jetson, ROS 2, workspace. **Done:** all of week 2, most of week 3 (C1 LIDAR, C920, bench bags) and
  the motor/gamepad half of week 4 (motors, teleop, link-loss stop), plus a practice map. About 1-1.5 weeks ahead.
- **O1 checklist** (`docs/runbooks/o1-checklist.md`, ticked 2026-11-19): Tier 1 A-C mostly done; D/E done except the D455 items.
  Open Tier 1 items: NVMe (root or data drive), versions/power mode/USB autosuspend log, TF `view_frames`, C920 rate +
  udev replug, D455 bring-up + IMU go/no-go, all sensors together 20 min, mounts + power for the moving rig, sensor poses.
- **Risks to G1:** (1) D455 and S2 delivery - the "all sensors together" part of O1 needs the D455; if it is not here by about
  4 Dec, map with C1/scan-only and log the deviation (checklist "cut" rule 4). (2) Power for the moving rig (battery or a
  trolley with a long lead, checklist F) - decide by end Nov. (3) NVMe not used yet - bags on the microSD.
- **Proposal deviations so far (all logged):** C1 instead of S2 until it arrives (decisions #31/#33); no wheel encoders
  (decisions #10, scan odometry); website frozen until O1 (robot first). None changes an objective.

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
2. ~~Build the whole workspace on the Jetson~~ DONE 2026-11-10 (rf2o `b38c68e`, explore_lite pin `926033f`, sllidar `3430009`). Optional: test m-explore `main` vs the pin (#19b).
3. ~~LIDAR via the repo launch + bench bag~~ DONE 2026-11-10 (C1, 10.0 Hz, decisions #33).
4. ~~C920 bring-up~~ DONE 2026-11-10. Still: photograph ~10 Merz Court door signs -> room format (OPEN_ISSUES #23).
5. **Mounts (student, from 2026-11-19):** design the LIDAR/D455/mast/Jetson/HAT/battery mounts; measure the sensor poses into `merz_description/config/sensor_poses.yaml` and the footprint into `nav2.yaml`.
5b. ~~Motor bench test~~ DONE 2026-11-16/19: HATs on bus 7; **wheel map corrected 2026-11-19: 0x40 = left (A RL, B FL), 0x41 = right (A FR, B RR)**; all "+" forward; lifted: start ~15% duty, 0.33 m/s at 30% (decisions #36, min-duty model). **ROS drives the motors** (`base_node backend:=pca9685`, forward/turn/timeout correct, lifted, 2026-11-19). **Gamepad teleop working** (DualSense, Bluetooth; deadman, forward, turn correct; link-loss stop passed = safety review R2 TESTED, lifted). PCA9685 backend: decisions #35/#36. **First map made 2026-11-19 (bench, moved by hand, C1, no IMU): pipeline LIDAR -> rf2o -> EKF -> SLAM Toolbox -> map_saver works**; map small and occluded by bench clutter. **Blocker now: rover not self-contained** (mains + breadboard + bench supply) -> battery/buck, wiring, mounting, then floor drive + calibration + first real map.
6. Supervisor/technician: motor stall current (#28), LiPo rules + battery/buck loan (#29), rover CAD for mounts.
7. Battery decision by ~end Nov (decisions #30).
8. When the D455 arrives: librealsense RSUSB build (plan §5.2 Wed) and the **IMU go/no-go** (#22) the same day.

## Active blockers
- D455 and S2 not yet arrived (D455 needed for the IMU in the EKF; not needed for a scan-only first map).
- **Rover not self-contained** (mains extension, breadboard, bench supply): blocks every floor test. Needs battery + buck (OPEN_ISSUES #29, decisions #30), wiring off the breadboard, mounting (rover CAD).
- Motor stall current unknown - not a blocker for bench tests (HAT current limit + student's own supply); needed for battery wiring (OPEN_ISSUES #28).
- Watch: D455 IMU on JetPack 6 (#22); L4T 36.4.7 vs planned 36.5.2 (#27).

## Memory files
`docs/INDEX.md` (all docs by category) | `docs/decisions.md` (engineering decisions) | `docs/HARDWARE_REGISTER.md` | `docs/SOFTWARE_ARCHITECTURE.md` | `docs/OPEN_ISSUES.md` | `docs/RESEARCH_INDEX.md` | `docs/logbook/` | `docs/meetings/` | `docs/CLAUDE_CODE_ROADMAP.md` (code build plan, stage prompts) | `docs/runbooks/build-guide.md` (hardware procedure) | `docs/planning/hardware-arrival-plan.md` (day-by-day timeline) | `docs/planning/experiments.md` | `docs/software/database-schema.md` | `docs/archive/` (finished build-all prompt and progress)
