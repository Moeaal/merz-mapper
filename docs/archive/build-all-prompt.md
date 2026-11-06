# Build-all instructions for Claude Code

**Student command:** `Read docs/archive/build-all-prompt.md and carry it out.`
**To resume after a break or a full context:** `Continue docs/archive/build-all-prompt.md from docs/archive/build-progress.md.`

You are writing ALL Merz Mapper software that can be written before the hardware arrives,
working on the student's **Windows laptop** (no ROS 2 installed here). The student will
read and learn the code later; your job now is complete, clean, well-commented, consistent code.

## 0. Setup (do first)
1. Read `docs/MERZ_MAPPER_STATE.md`, `docs/SOFTWARE_ARCHITECTURE.md`, `docs/HARDWARE_REGISTER.md`,
   `docs/decisions.md`, `docs/CLAUDE_CODE_ROADMAP.md`. Use the `merz-mapper-engineering-brain` skill and
   the specialist skills it routes to (`ros2-engineering-skills` for ROS 2 mechanics).
2. `git pull` on main, then create branch `build/all-code`.
3. Create `docs/archive/build-progress.md` with a checklist of the phases below. Tick each phase when its commit
   is pushed, so any later session can resume from it.
4. Check Python 3.12 is available (`py -3.12 --version`). If missing, tell the student how to install it,
   then continue writing code anyway.

## 1. Ground rules
- **Target:** ROS 2 Humble, Ubuntu 22.04, JetPack 6.x on Jetson Orin Nano (decisions #6). Keep code
  distro-agnostic where easy (should also build on Jazzy).
- **Do not install ROS on Windows.** Write code you cannot build here, carefully.
- **Architecture for testability:** every package has a pure-Python core module (no `rclpy` import) holding
  all the logic, plus a thin ROS 2 node wrapping it. Unit tests (pytest) test the core and MUST run and pass on
  Windows. ROS-dependent tests (launch_testing etc.) are written but marked "run on Jetson".
- **Odometry:** no wheel encoders (decisions #10): LIDAR scan-matching odometry + D455 IMU gyro in the EKF.
  Make wheel odometry an optional, disabled input in case the rover has encoders.
- **Unknown numbers** (sensor poses, footprint, wheel base, motor limits, noise covariances, pins) go in YAML
  files with the comment `# TODO: measure on rover`. Never hard-code them.
- **Honesty:** every package README starts with a status line: `IMPLEMENTED - not yet built or tested on
  hardware`. Never write TESTED. List which unit tests pass on Windows.
- **Style:** Python 3.10+ with type hints, docstrings, comments explaining *why*. Follow REP 103/105
  (units, frames). No features beyond the stages in `docs/CLAUDE_CODE_ROADMAP.md`. Website stays small.
- **Commits:** one commit per phase on `build/all-code`, message `Phase N: <what>`, then `git push`.
  The student approves pushes. Do NOT merge into main.

## 2. Phases
Implement each phase exactly as specified in the matching stage of `docs/CLAUDE_CODE_ROADMAP.md`,
plus the extras listed here.

| Phase | Roadmap stage | Extras |
| --- | --- | --- |
| 1 | 1 Workspace + interfaces | Root `ros2_ws/README.md`; `rosdep` dependencies in every `package.xml`; `requirements.txt` for pure-Python deps |
| 2 | 2 Robot description | |
| 3 | 3 Sensor bringup + teleop | udev rules in `merz_bringup/udev/`, one `.rules` file per device |
| 4 | 4 Odometry, EKF, SLAM | Pick the scan-matching package after checking it supports Humble; record the choice in `docs/decisions.md` as PROPOSED |
| 5 | 5 Perception | Engine abstraction: `ultralytics` (now) and TensorRT `.engine` (on Jetson), chosen by param; `tools/export_tensorrt.md` with the export steps |
| 6 | 6 Semantic map + SQLite | `docs/software/database-schema.md` |
| 7 | 7 Exploration + access zones | |
| 8 | 8 Nav2 + full autonomy launch | |
| 9 | 9 Evaluation tools | `docs/planning/experiments.md` with the procedure per objective |
| 10 | 10 Website + QR posters | Must run on Windows with a sample database (`web/sample_data/`) so the student can open it in a browser now |
| 11 | 11 Rover base driver | Rover not yet known: write `merz_base` with a backend interface and two backends: (a) **serial** motor controller with a configurable command format, (b) **Jetson GPIO PWM** for an H-bridge using `Jetson.GPIO`, pins in `config/base.yaml` (placeholders; note that PWM pins must be enabled with `jetson-io` and checked against NVIDIA's Orin Nano pinout before use). Include a cmd_vel timeout that stops the motors, speed/acceleration limits, and a mock backend for unit tests |
| 12 | Build guide | See section 3 |
| 13 | Final check | See section 4 |

## 3. `docs/runbooks/build-guide.md` (phase 12)
A step-by-step guide the student follows when the hardware arrives. Mark it "not yet verified on hardware".
1. **Parts and connections:** table of every device, port and cable. Jetson USB 3 port -> D455 (direct, not
   through the hub); powered hub -> RPLIDAR adapter, C920, gamepad dongle; NVMe in the M.2 slot. Power: Jetson
   and hub supplied from the rover battery (DC-DC as needed); LIDAR start-up current up to 1.5 A at 5 V.
   An ASCII wiring diagram. Pins: only for `merz_base` GPIO backend, if used.
2. **Mechanical:** mast at ~1.5 m for the C920, LIDAR level and unobstructed, D455 forward-facing; how to measure
   each sensor pose and fill in `sensor_poses.yaml`.
3. **Jetson setup:** flash JetPack 6.x to the NVMe, power mode, ROS 2 Humble install, librealsense via the RSUSB
   source build (OPEN_ISSUES #3), the other drivers, `rosdep`, `colcon build`, udev rules.
4. **Bring-up checks, one device at a time:** the command to run and what "working" looks like (topic rates,
   RViz view).
5. **Calibration:** C920 intrinsics with the checkerboard; IMU noise (60 s stationary); EKF check (square path).
6. **Running:** manual mapping (G1), exploration from an entrance, perception, database, evaluation scripts,
   website.
7. **Troubleshooting:** the known risks from `docs/OPEN_ISSUES.md`.

## 4. Final check (phase 13)
- Run all Windows-runnable tests; paste the summary into `docs/archive/build-progress.md`.
- Check every launch file references packages, files and params that exist (static check by reading).
- Update `docs/SOFTWARE_ARCHITECTURE.md` (real package/node/topic names, status IMPLEMENTED),
  `docs/MERZ_MAPPER_STATE.md` (a few lines), and tick `docs/CLAUDE_CODE_ROADMAP.md` stages 1-11 as
  "implemented, untested".
- Draft `docs/logbook/<today>.md` (Hours and Reflection left blank).
- Push, then open a pull request `build/all-code -> main` (use `gh` if available; otherwise give the student
  the GitHub link to open it). Do not merge.
- Finish with a short summary: what exists, which tests pass, what must be measured or verified on the Jetson
  and rover, and the top 5 risks.
