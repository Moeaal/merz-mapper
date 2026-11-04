# Merz Mapper: what to do once the parts arrive

**Written 2026-11-04. Status: PLAN.** None of these steps has been run, so nothing here is TESTED. All the code in the
repository is IMPLEMENTED: it is written, and the unit tests and a cloud ROS 2 Humble build pass. None of it has run on the
Jetson or the rover. Expect to fix commands, topic names and parameters as you go. Each time you do, change this file and
`docs/BUILD_GUIDE.md`.

How this file relates to the others:
- `docs/BUILD_GUIDE.md`: the **commands** for each hardware step. This file says **when** to run them, **why**, and what
  must be finished before the next step starts.
- `docs/EXPERIMENTS.md`: how each objective (O1-O8) is measured, with its pass rule.
- `docs/REVIEW.md`: safety findings that must be closed before the rover moves on its own.
- `ros2_ws/src/merz_bringup/README.md`: the **safety checklist**. Read it before any motion.

Contents
1. [Timeline at a glance](#1-timeline-at-a-glance)
2. [How to use the GitHub repository](#2-how-to-use-the-github-repository)
3. [How to use the repository on the Jetson](#3-how-to-use-the-repository-on-the-jetson)
4. [What each piece of code does](#4-what-each-piece-of-code-does)
5. [Day-by-day plan](#5-day-by-day-plan)
6. [Code still to write](#6-code-still-to-write)
7. [Other important things](#7-other-important-things)
8. [Daily routine and checklists](#8-daily-routine-and-checklists)

---

## 1. Timeline at a glance

The dates assume the parts arrive by **Mon 9 Nov 2026**. If they arrive late, move every pre-leave week back by the
same amount, **but keep G1 at Fri 18 Dec**. To make room, cut the "nice to have" items marked *(optional)*.

| Week | Dates | Main goal | Gate or deliverable |
| --- | --- | --- | --- |
| 1 | 9-13 Nov | Unpack, inspect, photograph, register the parts. **Submit the proposal** | **D1, Fri 13 Nov 14:00** |
| 2 | 16-20 Nov | Flash the Jetson, install ROS 2 Humble, build librealsense and the workspace | `colcon build` passes on the Jetson |
| 3 | 23-27 Nov | Bring up the sensors one at a time, add udev rules, design and print the mounts | All sensors publish on the bench |
| 4 | 30 Nov-4 Dec | Motors and base driver, gamepad, safety tests, sensors fitted, poses measured | Rover drives by gamepad safely |
| 5 | 7-11 Dec | Calibration (IMU, scan odometry, EKF square test), **first manual map** | **Target: first map by Fri 11 Dec** |
| 6 | 14-18 Dec | Buffer, a second and third map, bags with images, backups, G1 write-up | **G1 / O1, Fri 18 Dec** |
| Leave | 19 Dec-~4 Feb | Unavailable. Optional laptop-only work if you want it (section 5.7) | - |
| 7 | 8-12 Feb | Hardware health check; label images; train the first YOLO model | Model v1 |
| 8 | 15-19 Feb | Poster; perception running on the rover; TensorRT | Poster ready |
| 9 | 22-26 Feb | **Poster (Tue 23 Feb)**; Nav2 on blocks, then supervised point-to-point goals | **D2** |
| 10 | 1-5 Mar | First exploration from one entrance; keep-out mask | Autonomy starts (5 Mar) |
| 11-19 | 8 Mar-7 May | Experiments O2-O8, the website with real data, report writing | G2-G4, O2-O8 |
| - | May 2027 | Demo and report | D3, D4 |

The rule for the whole project: **the robot comes first** (decisions #5). If time runs short, cut the website, then any
stretch goals, but never the robot objectives.

---

## 2. How to use the GitHub repository

The repository `github.com/Moeaal/merz-mapper` is the **source of truth**: code, configuration, documents, logbook and
results all live here. Large data (bags, maps, photos, models) does **not** go in git (see `.gitignore`). It lives on the
Jetson's NVMe and is backed up to OneDrive.

### 2.1 The idea
```
           GitHub (main branch = the version that is known to build)
           /                 |                         \
   Laptop (Windows)     Claude Code sessions       Jetson on the rover
   docs, logbook,       (write code on claude/*    git pull -> colcon build -> run
   eval, website        branches, open PRs)        commit measured values on a branch
```
- **`main`** is the version you trust. Never work on `main` directly: make a branch, then merge it with a pull request (PR).
- **A branch for each piece of work**, for example `hw/sensor-poses`, `hw/base-serial`, `fix/velocity-timeout`,
  `logbook/2026-11-23`. Claude Code sessions use `claude/...` branches.
- **A PR to merge it:** on GitHub, *Pull requests -> New*, choose your branch, read the diff and merge it. Merge only after
  it has built on the Jetson, if it touches `ros2_ws/`.

### 2.2 Commands you will use (on any machine)
```bash
git clone https://github.com/Moeaal/merz-mapper.git
```
```bash
git switch main && git pull                 # get the latest version
```
```bash
git switch -c hw/sensor-poses               # start a new branch
```
```bash
git status                                  # see what has changed
```
```bash
git add ros2_ws/src/merz_description/config/sensor_poses.yaml docs/logbook/2026-12-01.md
```
```bash
git commit -m "Measured sensor poses on the rover (tape measure, +/-5 mm)"
```
```bash
git push -u origin hw/sensor-poses          # then open a PR on GitHub
```

### 2.3 Good habits
- **Commit small and often**, with a message that says *what* changed and *why*. The report will need the history.
- **Record the commit in every experiment.** `git rev-parse --short HEAD` gives the commit, and EXPERIMENTS requires it.
- **Tag milestones** so you can always go back to them, for example:
  ```bash
  git tag -a g1-first-map -m "Code used for the first manual map (G1)" && git push origin g1-first-map
  ```
- **Never commit:** bags, `.pgm` maps, `.pt` or `.engine` models, passwords or tokens. `.gitignore` already blocks most of
  these. Check with `git status` before every commit.
- **Logbook:** copy `docs/logbook/TEMPLATE.md` to `docs/logbook/YYYY-MM-DD.md` each day you work, and commit it.
  Meetings go in `docs/meetings/`.
- **Decisions:** any change to hardware, architecture or a pass rule becomes a row in `docs/decisions.md` (PROPOSED until
  Dr Wright agrees).
- **Update `docs/MERZ_MAPPER_STATE.md`** at the end of each week. It is what Claude reads first.

### 2.4 Using Claude Code with the repository
- Start a session on the repository. Claude reads `CLAUDE.md`, then `docs/MERZ_MAPPER_STATE.md`.
- Ask for one thing at a time, for example *"Fill in merz_base for a RoboClaw controller; here is the manual: ..."*.
  Claude works on a `claude/...` branch and pushes it. You review the PR, build it on the Jetson, then merge it.
- Paste the **real error output** from the Jetson (`colcon build`, `ros2 launch`) into the session. That is the fastest
  way to fix things.
- Claude must not merge PRs or change hardware decisions. That is your job, after checking.

---

## 3. How to use the repository on the Jetson

### 3.1 One-off set-up (Week 2)
1. **Make the Jetson user `merz`** when you set up Ubuntu. The paths in `merz_perception/config/perception.yaml` assume
   `/home/merz/...`. If you choose another name, change those paths.
2. **Give the Jetson access to GitHub.** The simplest way is an SSH key:
   ```bash
   ssh-keygen -t ed25519 -C "merz-jetson"
   ```
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```
   Add the printed key on GitHub: *Settings -> SSH and GPG keys -> New SSH key*. Then:
   ```bash
   git clone git@github.com:Moeaal/merz-mapper.git ~/merz-mapper
   ```
   ```bash
   git config --global user.name "Mohammed Abdulaal" && git config --global user.email "<your email>"
   ```
   (Alternative: HTTPS with a fine-grained personal access token limited to this one repository.)
3. **Make the data folders** that the launch files write to:
   ```bash
   mkdir -p ~/merz_data/{bags,maps,photos,models,eval}
   ```
4. **Build** using `docs/BUILD_GUIDE.md` section 3 ("Workspace").
5. **Source the workspace in every terminal:** add both lines to `~/.bashrc`:
   ```bash
   source /opt/ros/humble/setup.bash
   source ~/merz-mapper/ros2_ws/install/setup.bash
   ```

### 3.2 Each time the code changes
```bash
cd ~/merz-mapper && git switch main && git pull
```
```bash
cd ros2_ws && colcon build --symlink-install && source install/setup.bash
```
```bash
colcon test && colcon test-result --verbose
```
- With `--symlink-install`, edits to existing Python, launch and YAML files take effect without rebuilding. You must
  rebuild after adding a **new** file, changing `setup.py`, `package.xml` or a `.msg` file, or pulling new code.
- To try a PR before merging it: `git fetch && git switch <branch>`, build, test, then `git switch main` afterwards.
- If the build gets into a strange state: `rm -rf build install log` and build again.

### 3.3 Changes made on the Jetson
Values you measure on the rover (sensor poses, motor settings, teleop axes, calibration files, covariances) are edited on
the Jetson. Commit them from there, on a branch:
```bash
git switch -c hw/teleop-axes
```
```bash
git add ros2_ws/src/merz_bringup/config/teleop.yaml && git commit -m "Gamepad axes and deadman button measured" && git push -u origin hw/teleop-axes
```

### 3.4 Working on the rover without a screen
- **SSH from the laptop** (Windows has `ssh` built in): `ssh merz@<jetson-ip>`. Use **VS Code with Remote-SSH** to edit
  files on the Jetson from the laptop.
- **Use `tmux`** on the Jetson (`sudo apt install tmux`), so that a run keeps going if Wi-Fi drops:
  `tmux new -s run`, then `Ctrl-b d` to detach and `tmux attach -t run` to come back.
- **Seeing the map from Windows:** RViz needs Linux. The easiest option on Windows is **Foxglove** with
  `foxglove_bridge` running on the Jetson (`sudo apt install ros-humble-foxglove-bridge`, then
  `ros2 launch foxglove_bridge foxglove_bridge_launch.xml`, and connect from the laptop to `ws://<jetson-ip>:8765`).
  Otherwise plug a monitor into the Jetson for RViz on the bench. The Pi 5 can run RViz only if it also runs Humble
  (decisions #21).
- **Set the same `ROS_DOMAIN_ID`** on every ROS machine (for example `export ROS_DOMAIN_ID=42` in `~/.bashrc`), so that
  you do not see other students' robots on university Wi-Fi. University Wi-Fi often blocks DDS discovery between devices.
  If it does, use Foxglove, or a small travel router on the rover.

### 3.5 Where the data goes (on the Jetson)
| Folder | Written by | Back up? |
| --- | --- | --- |
| `~/merz_data/bags/` | `record_bag.launch.py` | **Yes, always.** Bags let you redo SLAM, perception and O8 offline |
| `~/merz_data/maps/` | `map_saver_cli`, `mission_node` | Yes |
| `~/merz_data/merz.sqlite` | `landmark_node`, `junction_photo_node`, access-zone code | Yes, once per run (copy and rename it with the run name) |
| `~/merz_data/photos/` | `junction_photo_node` | Yes |
| `~/merz_data/models/` | You (trained YOLO weights and engines) | Yes, the `.pt` file. Rebuild the `.engine` on the Jetson |

To copy to the laptop from Windows PowerShell: `scp -r merz@<jetson-ip>:~/merz_data/bags/first_map C:\merz_backup\`
and then put it on OneDrive. A 256 GB NVMe fills quickly with image bags (tens of GB per hour), so check `df -h` daily.

---

## 4. What each piece of code does

The rule throughout: the logic lives in plain Python modules with no ROS import (so it can be tested on Windows), and a
thin `*_node.py` connects it to ROS.

### 4.1 ROS 2 packages (`ros2_ws/src/`)

#### `merz_interfaces`: the messages
| File | What it is |
| --- | --- |
| `msg/Detection.msg`, `DetectionArray.msg` | One YOLO box (class, confidence, box) and a list of them, with the image's timestamp |
| `msg/SignReading.msg` | A room number read from a door sign |
| `msg/Landmark.msg`, `LandmarkArray.msg` | A landmark's position in the map, class, text and observation count |

#### `merz_description`: the robot's shape and sensor positions
| File | What it does | When you touch it |
| --- | --- | --- |
| `urdf/merz_rover.urdf.xacro` | Builds the TF frames `base_link -> laser, camera_link, sign_camera` | Rarely |
| `config/sensor_poses.yaml` | **All sensor positions and angles** (placeholders now) | **Week 4: fill in with measured values.** Errors here go straight into landmark error (O4) |
| `launch/description.launch.py` | Publishes the frames; `rviz:=true` shows the model | Every time you check the poses |

#### `merz_bringup`: sensors, teleop, localisation, SLAM and navigation
| File | What it does |
| --- | --- |
| `launch/lidar.launch.py`, `d455.launch.py`, `c920.launch.py` | Start one sensor each. Use them for bring-up |
| `launch/sensors.launch.py` | All sensors plus the URDF frames. Each can be switched off (`c920:=false`) |
| `launch/teleop.launch.py` | Gamepad -> `/cmd_vel_teleop`, with a deadman button, through `twist_mux` (teleop overrides autonomy) |
| `launch/localisation.launch.py` | rf2o scan-matching odometry + relay + EKF -> `odom -> base_link` |
| `launch/slam.launch.py` | SLAM Toolbox -> `/map` and `map -> odom`. `posegraph:=` continues an earlier map |
| `launch/mapping.launch.py` | **G1 manual mapping**: sensors + teleop + base + localisation + SLAM |
| `launch/navigation.launch.py` | Nav2, with an optional keep-out mask |
| `launch/explore_from_entrance.launch.py` | **The full autonomous run**: everything above plus exploration, perception and the semantic map |
| `launch/record_bag.launch.py` | Records a bag in `~/merz_data/bags`. `images:=true` adds camera images (large) |
| `merz_bringup/scan_odom_relay_node.py` + `odom_covariance.py` | Adds the covariance that rf2o leaves at zero, and drops implausible jumps |
| `config/lidar.yaml`, `d455.yaml`, `c920.yaml`, `c920_camera_info.yaml` | Driver settings; the C920 calibration result goes in `c920_camera_info.yaml` |
| `config/teleop.yaml` | Gamepad axes, deadman button, speeds. **Axis numbers are guesses: fix in Week 4** |
| `config/twist_mux.yaml` | Priorities: teleop 100 over navigation 10, 0.5 s timeouts |
| `config/scan_odometry.yaml` | rf2o settings, and the noise values (`vx_std` etc.) to measure in Week 5 |
| `config/ekf.yaml`, `ekf_wheel_odom.yaml` | The EKF: scan odometry vx, vy plus IMU yaw rate. `ekf_wheel_odom.yaml` is unused: no encoders (decisions #22) |
| `config/slam.yaml` | SLAM Toolbox settings (`max_laser_range` etc.) |
| `config/nav2.yaml`, `keepout.yaml` | Nav2: 0.5 m/s cap, no reversing, footprint (placeholder), keep-out filter |
| `behavior_trees/navigate_no_motion_recovery.xml` | Nav2 tree with no spinning or reversing when stuck (decisions #16) |
| `udev/99-merz-*.rules` | Fixed device names: `/dev/rplidar`, `/dev/c920`, etc. |
| `maps/README.md` | How to make a keep-out mask for glass |

#### `merz_base`: drives the motors
| File | What it does |
| --- | --- |
| `merz_base/base_node.py` | Reads `/cmd_vel_mux` and sends wheel commands at 20 Hz |
| `merz_base/kinematics.py` | Speed and turn rate -> left and right wheel speeds (skid-steer or differential) |
| `merz_base/base_controller.py` | Speed limits, acceleration limits, **0.5 s command timeout -> stop** |
| `merz_base/backends.py` | `mock` (default, moves nothing), `serial` (motor controller board), `gpio` (H-bridge via Jetson PWM) |
| `config/base.yaml` | **Every value is a placeholder.** Fill in for the real rover in Week 4 |

#### `merz_perception`: YOLO and door-sign reading (O3)
| File | What it does |
| --- | --- |
| `detector_node.py` + `engines.py` | Runs YOLO (`.pt` with Ultralytics, or a TensorRT `.engine`) on one camera at a few Hz |
| `sign_reader_node.py` | When a `room_sign` is detected on the C920: crop, check sharpness, OCR, validate, publish |
| `sharpness.py` | Rejects blurred crops (variance of the Laplacian) |
| `ocr.py` | PaddleOCR, or RapidOCR as a fallback if Paddle will not install on the Jetson |
| `room_numbers.py` | Cleans OCR text and checks it against the room-number pattern (`room_regex`) |
| `offline_batch.py` | Runs detection and OCR over a folder of images, with no ROS: use it to test the model on the laptop |
| `config/perception.yaml` | Model path, confidence, rates, `room_regex`, `min_sharpness`: **set from real data** |

#### `merz_semantic_map`: landmark positions and the database (O4, O6, O8)
| File | What it does |
| --- | --- |
| `landmark_node.py` | Joins D455 detections, depth and TF, and writes landmarks to SQLite |
| `localiser.py` | Box -> median depth -> 3D point -> map frame -> match to an existing landmark -> running mean |
| `geometry.py` | Camera maths (deprojection, projection) |
| `database.py` | The SQLite database (`docs/DATABASE_SCHEMA.md`): rooms, landmarks, observations, junctions, zones |
| `config/semantic_map.yaml` | `gate_m` (merge distance), `fusion_mode` (`fused` or `single_observation`, for O8) |

#### `merz_exploration`: exploring, access zones and junction photos (O2, O5, O7)
| File | What it does |
| --- | --- |
| `launch/exploration.launch.py` | explore_lite (frontier exploration) plus the three nodes below |
| `mission_node.py` + `mission.py` | Ends the run (no frontiers for 60 s, time cap, or by hand); saves the map and posegraph; asks for the access zone |
| `access_zone_node.py` + `access_zones.py` | Flood fill from the entrance over the free space: which rooms are reachable (O5) |
| `compute_access_zones.py` | The same, offline, from a saved map, with no ROS |
| `junction_photo_node.py` + `junctions.py` | Detects corridor junctions from the scan; saves a photo and pose; builds the route graph for the website |
| `map_io.py` | Reads saved `.yaml` + `.pgm` maps (also used by `tools/eval`) |

### 4.2 Tools (`tools/`, no ROS needed, run on the laptop or Jetson)
| File | What it does | When |
| --- | --- | --- |
| `extract_frames.py` | Pulls images out of a bag for labelling | Week 6 onwards |
| `export_tensorrt.md` | How to turn the trained YOLO model into a TensorRT engine on the Jetson | Week 8 |
| `eval/map_coverage.py`, `wall_error.py` | O2 | March onwards |
| `eval/ocr_rate.py` | O3 | March onwards |
| `eval/landmark_error.py` | O4 | March onwards |
| `eval/access_zone_compare.py` | O5 | March onwards |
| `eval/route_timing.py` | O6, O7 (needs the website running) | April |
| `eval/fusion_compare.py` | O8 | April |
| `web_import.py` | Turns a copy of `~/merz_data` into the website's data bundle | After the first real run |
| `web_export.py` | Exports the website as static files (GitHub Pages) | Demo |
| `synthetic_run/` | Makes an invented run so the website has something to show. **Not real data; never report it as results** | Already done |
| `yolo_practice/yolo_v2.py` | Dr Wright's webcam YOLO practice script. Not robot code | Learning |
| `test_*.py`, `eval/test_eval.py` | Tests | `python -m pytest` from the repo root |

### 4.3 Website (`web/`): the demonstrator
`app/main.py` (FastAPI, read-only API over the database), `app/routing.py` (shortest route over the junction graph),
`app/grid_map.py` (map to PNG), `qr_posters.py` (one QR poster per entrance), `frontend/` (the page, built into `dist/`).
How to run it: `web/README.md`. Cut this first if time runs short.

### 4.4 How it all connects during a run
```
Gamepad --> teleop --+
                     +--> twist_mux --> /cmd_vel_mux --> merz_base --> motors
Nav2 <-- explore_lite +
  ^
  |  /map, map->odom             odom->base_link
SLAM Toolbox <-- /scan --> rf2o --> relay --> EKF <-- D455 IMU (yaw rate)
D455 colour + depth --> detector --> landmark_node --> merz.sqlite --> website
C920 --> detector --> sign_reader --------^
/scan + TF + photo --> junction_photo_node --> merz.sqlite
run end --> mission_node --> map + posegraph --> access zones --> merz.sqlite
```

---

## 5. Day-by-day plan

How to use this section: each day lists **tasks**, then **done when** (the evidence that the step worked). Write the
evidence in that day's logbook entry. **If a step fails, stop and fix it before going on.** Debugging three new things at
once costs far more time than doing them one at a time.

### 5.1 Week 1 (9-13 Nov): inspection and the proposal
The proposal (D1, Fri 13 Nov 14:00) comes first this week. Give the hardware about half the time.

**Mon 9 Nov: unpack and record**
- Unpack everything. Photograph each part, its labels and serial numbers, and the rover from every side.
- Check each item against `Rover_Parts_List.xlsx`. Note anything missing or damaged, and email Dr Wright the same day.
- Update `docs/HARDWARE_REGISTER.md`: change the status to RECEIVED, and add the model and serial numbers.
- *Done when:* every part is accounted for, and the register is committed.

**Tue 10 Nov: inspect the rover (OPEN_ISSUES #1, the biggest unknown)**
Find out and write down, with photos:
- Motors: how many, which make and voltage. Skid-steer (4 wheels) or differential (2 wheels plus a caster)?
- **Motor controller:** make and model, how it is controlled (USB serial, UART, RC/PWM, CAN?), and whether it has its own
  **command timeout or watchdog** (that answers decisions #19 / REVIEW R1). Find its manual.
- Encoders are **not used** (decisions #22), even if the motors have them. Odometry comes from the LIDAR and the D455 IMU.
- **Battery:** chemistry (LiPo, Li-ion, lead acid), voltage, capacity, charger, fuse, and **is there a power switch or
  emergency stop?**
- Is there an existing computer or ROS driver on it? If so, ask whether to use it (`merz_base/README.md`).
- Space and mounting points for the Jetson, hub, LIDAR and mast. Ask Dr Wright for the CAD.
- *Done when:* the register's rover row has real values, and the questions for Dr Wright are listed.

**Wed 11 Nov: proposal**
- Finish the proposal. Use the rover facts from yesterday (the proposal must say scan matching + D455 IMU, not "wheel odometry": decisions #22).
- Bench check that needs no set-up: power each USB device from a laptop and confirm that it is detected. On Windows,
  Intel's RealSense Viewer can show the D455 and update its firmware. SLAMTEC's Windows tool can show the LIDAR spinning.

**Thu 12 Nov: proposal and ordering**
- Final checks on the proposal: third person, IEEE references, UK English.
- Order the missing parts (OPEN_ISSUES #10): **wired** or disconnect-safe gamepad (REVIEW R2), a checkerboard (or print
  one on A3 and glue it to a rigid board), mast material, a **physical emergency stop switch** if the rover has none,
  DC-DC converters once the battery voltage is known, cable ties, Velcro and short USB 3 cables.
- Get the **Jetson's power supply** ready for the bench (the dev kit's own adapter).

**Fri 13 Nov: submit D1 by 14:00**
- Submit. Then the meeting agenda for Dr Wright: tell him your decisions (Humble, no encoders: #21, #22), floor plan (#14), permission to test
  in Merz Court, the O2 and O8 pass rules (#21), the emergency stop and watchdog (decisions #19), and the unlisted parts.
- Write the week's logbook and update `MERZ_MAPPER_STATE.md`.

### 5.2 Week 2 (16-20 Nov): Jetson, ROS 2 and the workspace
**Mon 16 Nov: flash the Jetson**
- Flash **JetPack 6.x** (the latest 6.x release) for **ROS 2 Humble** (decisions #21). Do not use JetPack 7: Humble needs Ubuntu 22.04.
- Flash route (your laptop has no Linux, decisions #11):
  - **Developer kit:** the SD-card image route in NVIDIA's *Jetson Orin Nano Developer Kit Getting Started* guide. A kit
    from older stock may first need its firmware updated before JetPack 6 boots: follow NVIDIA's current instructions.
    Then move the system to the NVMe (or flash the NVMe directly from a department Ubuntu PC with SDK Manager).
  - SDK Manager needs an **x86-64 Ubuntu** PC, so the Pi 5 cannot do it. Ask the department for a lab PC.
- First boot: make the user `merz`, connect to Wi-Fi, run `sudo apt update && sudo apt upgrade`.
- Record the JetPack, L4T, CUDA and TensorRT versions (`cat /etc/nv_tegra_release`, `dpkg -l | grep -E "nvidia-jetpack|tensorrt"`)
  in the register.
- *Done when:* the Jetson boots from NVMe, and you can SSH in from the laptop.

**Tue 17 Nov: ROS 2 Humble and tools**
- Install ROS 2 (BUILD_GUIDE section 3), then the apt drivers from `merz_bringup/README.md`.
- Set the power mode (`sudo nvpmodel -q`), install `tmux`, `htop`, `git`, `jtop` (`sudo pip3 install jetson-stats`).
- Quick test: `ros2 run demo_nodes_cpp talker` in one terminal and `ros2 run demo_nodes_py listener` in another.
- *Done when:* the talker and listener talk.

**Wed 18 Nov: librealsense (allow the whole day, OPEN_ISSUES #3)**
- RSUSB source build, as in BUILD_GUIDE section 3. Plug the D455 **directly** into a Jetson USB 3 port.
- *Done when:* `rs-enumerate-devices` lists the D455 on **USB 3.x**, and `realsense-viewer` shows depth (if a monitor is attached).
  Log the librealsense version and the camera firmware.

**Thu 19 Nov: clone and build the workspace**
- Set up GitHub access and clone (section 3.1). `vcs import`, `rosdep install`, then build `rf2o_laser_odometry` **on its
  own first** (decisions #14): `colcon build --packages-select rf2o_laser_odometry`. Then build everything.
- Run `colcon test && colcon test-result --verbose`. The four ROS-only test files must **pass** here, not skip.
- *Done when:* the build and tests pass on the Jetson. Log the exact commit of each third-party repo
  (`vcs export src --exact`) in the logbook, as `merz.repos` uses branch names.

**Fri 20 Nov: udev, safety parts and catch-up**
- Install the udev rules (BUILD_GUIDE section 3). Check `/dev/rplidar` and `/dev/c920` appear. You may need to change the
  vendor or product IDs in the rules: get the real ones from `udevadm info -a -n /dev/ttyUSB0` and `lsusb`.
- Catch up on anything from Mon-Thu that failed.
- Update the register and STATE. Commit.

### 5.3 Week 3 (23-27 Nov): sensors one at a time, and mounts
Bench work: the sensors sit on the desk, connected to the Jetson. Follow BUILD_GUIDE section 4, one device per day.

**Mon 23 Nov: LIDAR**
- `ros2 launch merz_bringup lidar.launch.py`; `ros2 topic hz /scan` (about 10 Hz).
- View the scan in Foxglove or RViz (fixed frame `laser`). Hold a box at a measured distance and compare with the laser meter.
- Record a 1-minute bag: `ros2 launch merz_bringup record_bag.launch.py name:=lidar_bench`.
- *Done when:* the rate is steady and the room outline looks right.

**Tue 24 Nov: D455 and its IMU**
- `ros2 launch merz_bringup d455.launch.py`. Check colour, aligned depth (about 15 Hz) and `/camera/camera/imu`.
- Rotate the camera by hand around its vertical axis, and check which IMU axis changes. Note it: the EKF uses yaw rate.
- Point it at a flat wall at 1, 2 and 3 m, measured by the laser meter, and compare with the depth.
- If the topic names differ (older drivers use `/camera/...`), see BUILD_GUIDE section 7.
- *Done when:* all streams run for 10 minutes without dropping out.

**Wed 25 Nov: C920 and the URDF**
- `ros2 launch merz_bringup c920.launch.py`. Hold a printed room sign at 1-2 m. Is the text readable in the image?
- Find the real door-sign format in Merz Court (photograph 10 signs with your phone). Write the pattern down: it becomes
  `room_regex` in `perception.yaml`.
- `ros2 launch merz_description description.launch.py rviz:=true`, then `ros2 run tf2_tools view_frames`: one tree.
- *Done when:* the sign is readable and the TF tree is complete (with placeholder poses).

**Thu 26 Nov: all sensors together**
- `ros2 launch merz_bringup sensors.launch.py`, for 20 minutes. Watch `tegrastats` or `jtop` for temperature and power,
  and `dmesg -w` for USB errors.
- Record a short bag with images and check it plays back (`ros2 bag info`, `ros2 bag play`).
- *Done when:* every rate holds for 20 minutes together.

**Fri 27 Nov: mechanical design**
- Using the rover CAD: design the LIDAR mount (level, above everything else, with a clear 360° view), the D455 mount
  (forward and level) and the mast (C920 at about 1.5 m, stiff). Send them for 3D printing.
- Plan the wiring and power: battery -> emergency stop -> fuse -> DC-DC converters -> Jetson and hub. Check the
  converter ratings against the loads (BUILD_GUIDE section 1). Ask a technician to check it before you connect it.

### 5.4 Week 4 (30 Nov-4 Dec): motors, gamepad, safety and assembly
**Every motor test this week is done with the wheels off the ground, with the emergency stop in reach.**

**Mon 30 Nov: motor controller**
- From the controller's manual, fill in `merz_base/config/base.yaml`: `backend`, port, baud, command format, stop
  command and scale (serial), or the pins (GPIO). If the controller's protocol does not fit the text format (binary
  packets, for example), see section 6, item 1.
- Add a udev rule so the controller is always `/dev/merz_motors`.
- Test the controller **alone** first, with the manufacturer's tool or a short Python script: one wheel, slowly.
- *Done when:* you can turn each side forwards and backwards, slowly, from a script.

**Tue 1 Dec: base driver and gamepad**
- `ros2 launch merz_base base.launch.py`, then publish by hand:
  `ros2 topic pub -r 10 /cmd_vel_mux geometry_msgs/msg/Twist "{linear: {x: 0.1}}"`. Both sides must turn **forwards**.
  Then `angular: {z: 0.5}`: the rover must turn **left** (REP 103).
- Stop the publisher: the wheels must stop within 0.5 s (`command_timeout_s`).
- Gamepad: `ros2 topic echo /joy`, press each button and stick, and fix `teleop.yaml` (axes, deadman, signs).
- *Done when:* `ros2 launch merz_bringup teleop.launch.py` + base drives the wheels only while the deadman is held.

**Wed 2 Dec: safety tests (REVIEW.md, merz_bringup safety checklist)**
- Physical emergency stop while the wheels turn: they must stop.
- `kill -9` the base node while the wheels turn (REVIEW R1). If they **keep turning**, the rover must not run autonomously
  until a watchdog exists (decisions #19; section 6, item 2).
- Turn the gamepad off while holding the deadman with a stick pushed (REVIEW R2). `/cmd_vel_teleop` must stop.
- Unplug the controller's USB while driving (REVIEW R3): what happens?
- Write every result in the logbook, including failures. These are good material for the report.

**Thu 3 Dec: assembly**
- Fit the mounts, sensors, Jetson, hub and wiring. Tidy the cables so nothing enters the LIDAR's plane.
- Check the LIDAR is level with a spirit level.
- Measure the real speed limits: drive at full output and time it over 2 m, which gives `full_speed_m_s`.

**Fri 4 Dec: measure the sensor poses and footprint**
- Measure every pose (BUILD_GUIDE section 2) and fill in `merz_description/config/sensor_poses.yaml`, with the
  uncertainty of each measurement in the logbook.
- Measure the outer size of the rover, and set `footprint` in `nav2.yaml` (both costmaps) and the box in `sensor_poses.yaml`.
- Check in RViz/Foxglove: the scan lines up with the walls, and the rover faces the right way.
- Commit the measured values on a branch (`hw/measured-poses`) and merge it.
- *Done when:* the rover drives safely by gamepad with every sensor running.

### 5.5 Week 5 (7-11 Dec): calibration and the first map
**Mon 7 Dec: IMU and C920 calibration**
- IMU noise: 60 s still, motors off (BUILD_GUIDE section 5). Work out the gyro bias and SD (section 6, item 7: a small
  script). Compare with the covariance in the IMU messages.
- C920 intrinsics with the checkerboard, autofocus off. Save `c920_camera_info.yaml`.

**Tue 8 Dec: scan odometry and a corridor test**
- Drive a measured straight 5 m line by gamepad, 5 times. Compare `/odom_scan` with the laser meter, and set `vx_std`.
- **Drive down a long, plain corridor** and record a bag. Does `/odom_scan` keep counting distance? If it stalls, that is
  OPEN_ISSUES #17. There are no encoders (decisions #22), so try in order: drive slower, fuse rf2o `vyaw` in `ekf.yaml`,
  open doors for features; last resort, add D455 visual odometry as a second velocity source (section 6, item 13).

**Wed 9 Dec: EKF square test**
- 2 m square, 3 times each way, `mapping.launch.py`. Compare `/odometry/filtered` at the start and end. Measure
  `track_width_m` from fixed turns compared with the IMU.
- Tune only with a clear reason, one change at a time, and log each change.

**Thu 10 Dec: first manual map (O1)**
- Permission to test, people nearby told, emergency stop in reach.
- `mapping.launch.py` in one terminal, `record_bag.launch.py name:=first_map` in another. Drive slowly, turn gently,
  close a loop if possible. Save the map with `map_saver_cli` (BUILD_GUIDE section 6).
- *Done when:* a map is saved, and the bag plays back. **This meets the O1 target date.**

**Fri 11 Dec: back up and review**
- Copy the bag and map to the laptop and OneDrive. Replay the bag through SLAM on the Jetson
  (`ros2 bag play` with `use_sim_time`) to prove you can make maps offline over the leave.
- Tag the commit: `g1-first-map`. Update STATE, the register (DRIVER RUNNING / CALIBRATED / ON ROVER) and the logbook.

### 5.6 Week 6 (14-18 Dec): buffer and G1
**Mon 14 Dec:** buffer for anything that slipped. If nothing slipped, map a second corridor.

**Tue 15 Dec: data for the model.** Drive the corridors you will use, with `images:=true`, at the speed the robot will
explore at. Include doors, lifts, stairs, exit signs and room signs, in different lighting. **Keep one corridor apart as a
test set** (EXPERIMENTS, O3). Several short bags are easier to handle than one long one.

**Wed 16 Dec: ground truth while you are in the building.** Photograph or list every door sign in the test area (O3
`signs.csv`). Ask estates or Dr Wright for the floor plan (OPEN_ISSUES #14). Note glass walls and doors for the keep-out mask.

**Thu 17 Dec: back up everything.** Bags, maps, the database and photos, to the laptop **and** OneDrive. Check the copies
open. Commit all config and logbook changes. Write a clear note in STATE of exactly where you stopped.

**Fri 18 Dec: G1.** Show Dr Wright the sensors running and the map. Write the G1 logbook entry with evidence (rates,
screenshots, map, bag names). Store the rover safely: battery disconnected and charged to its storage level.

### 5.7 Leave (19 Dec-~4 Feb)
You are unavailable, so **nothing is planned**. If you do want some laptop-only work, these need no rover:
extract frames from the December bags (`tools/extract_frames.py`) and start labelling; re-run SLAM from bags; sketch the poster.

### 5.8 Week 7 (8-12 Feb): back to work, and the first model
- **Mon:** health check: charge the battery, run `sensors.launch.py` and teleop, drive a short loop. `git pull` and rebuild.
- **Tue-Wed:** extract frames (one every 2 s) and label a few hundred images with the classes in `perception.yaml`
  (`door`, `lift`, `stairs`, `exit_sign`, `room_sign`). Label Studio, CVAT or Roboflow all export YOLO format.
- **Thu:** train a small YOLO model on the laptop or a GPU machine (section 6, item 5). Keep the held-back corridor out.
- **Fri:** test it on the laptop with `python -m merz_perception.offline_batch`. Log mAP and an example image.

### 5.9 Week 8 (15-19 Feb): perception on the rover and the poster
- **Mon:** copy the `.pt` to `~/merz_data/models/merz_yolo.pt`, and set the path in `perception.yaml`. Run
  `perception.launch.py` with the cameras, and watch `/perception/*/detections`.
- **Tue:** install OCR (PaddleOCR, or `ocr_engine: rapid`). Set `room_regex` and `min_sharpness` from real crops.
- **Wed:** export to TensorRT on the Jetson (`tools/export_tensorrt.md`). Compare speed and accuracy, and log them.
- **Thu-Fri:** poster (D2). Only show TESTED results. The architecture, the map from G1 and calibration numbers are fine.

### 5.10 Week 9 (22-26 Feb): poster and Nav2
- **Tue 23 Feb: poster.** (Confirm the date: the slides say Friday, OPEN_ISSUES #11.)
- **Before Nav2**, make the code changes in section 6, items 3-4 (velocity timeout, collision monitor, e-stop lock),
  build, and test them on blocks.
- **Wed:** `navigation.launch.py` with the saved map and SLAM running, on blocks: give a goal in Foxglove/RViz and check
  that the wheels turn the right way. Stop the `controller_server` mid-goal and time how long the wheels keep turning (R4).
- **Thu-Fri:** on the floor, at reduced `max_vel_x` (for example 0.2 m/s), with someone holding the gamepad: short goals
  in an empty corridor. Check that obstacles stop it.

### 5.11 Week 10 (1-5 Mar): first exploration
- **Mon:** make the keep-out mask from the December map (`merz_bringup/maps/README.md`). Check it lines up in Foxglove/RViz.
- **Tue:** `explore_from_entrance.launch.py entrance:=<first> perception:=false`, supervised, slow. Watch
  `/explore/frontiers`. Does `mission_node` end the run when it should (its rule is an assumption to check)?
- **Wed:** check the saved map, posegraph and database. Run `compute_access_zones` offline and compare.
- **Thu:** the same with `perception:=true`. Check that landmarks appear in the database.
- **Fri:** record door states and conditions. Fix the problems found. Tag the commit `first-exploration`.

### 5.12 Weeks 11-19 (8 Mar-7 May): experiments, website, report
Follow `docs/EXPERIMENTS.md` for each objective. **Agree the pass rules with Dr Wright and write the ground truth before
each run.** Three runs per experiment. Each week below is Mon-Fri: one day of preparation and ground truth, two to three
days of runs, and one day of analysis and writing it up the same week.

| Week | Dates | Experiment | Ground truth to prepare first |
| --- | --- | --- | --- |
| 11 | 8-12 Mar | O2 coverage and walls, first entrance | Corridor polygon and walls CSV from the floor plan or a laser survey |
| 12 | 15-19 Mar | O4 landmark error | 20+ landmarks measured from two known corners |
| 13 | 22-26 Mar | O3 sign reading | `signs.csv` written on foot |
| 14 | 29 Mar-2 Apr | Second entrance (same map frame, `posegraph:=`) and O5 access zones | Walk-through `survey.csv`, door states |
| 15 | 5-9 Apr | O8 fused vs single (both comparisons, from bags) | Same truth as O4 |
| 16 | 12-16 Apr | Website with real data (`tools/web_import.py`), QR posters, O6 and O7 | `routes.csv`, walked by hand |
| 17 | 19-23 Apr | Repeat anything that failed; demo rehearsal | - |
| 18-19 | 26 Apr-7 May | Report writing; final runs only if needed | - |

Easter falls on 28 Mar 2027: check the university's Easter closure and building access, and move weeks 13-14 if needed.
Write the report **as you go**: each experiment's method, results table and figure on the week it is done.

---

## 6. Code still to write

Everything below is **PROPOSED**: none of it exists yet. Ask Claude Code for each one when you reach it, giving it the
facts you measured. Items 1-4 are safety-related and must be done before autonomous motion.

| # | What | Why | When | Size |
| --- | --- | --- | --- | --- |
| 1 | **Real motor interface** in `merz_base`: fill in `base.yaml`; if the controller uses binary packets (Sabertooth packetised serial, RoboClaw, etc.) or RC PWM, a new backend class in `backends.py` with tests; a udev rule for `/dev/merz_motors` | The serial backend only sends text commands; the rover's controller is unknown | Week 4 | Small-medium |
| 2 | **Independent stop** (decisions #19): either use the controller's own serial watchdog, or a small microcontroller (an Arduino, say) that cuts the motor enable unless it gets a heartbeat from the Jetson, plus a heartbeat publisher in `merz_base` | If the Jetson or `base_node` dies, nothing stops the motors (REVIEW R1) | Week 4, before autonomy | Medium |
| 3 | **Nav2 safety fixes:** `velocity_smoother.velocity_timeout` to 0.5 s (R4); `navigate_through_poses` no-motion tree (decisions #18); error handling in `base_node` (R3); lock fix in `mission_node` (R10) | Open findings in `docs/REVIEW.md` | Week 9 | Small |
| 4 | **`nav2_collision_monitor` and a latched e-stop lock** in twist_mux on a gamepad button (decisions #20) | Short-range stop at sensor rate; autonomy stays stopped after the deadman is released (R5, R6) | Week 9 | Medium |
| 5 | **YOLO training set-up:** `tools/train/merz.yaml` (dataset file with the 5 classes), a training script with a fixed seed, and a split that keeps one corridor out | Nothing trains the model yet; `tools/export_tensorrt.md` assumes `merz_yolo.pt` exists | Week 7 | Small |
| 6 | **RViz/Foxglove layouts** for mapping and navigation (map, scan, TF, costmaps, frontiers, keep-out mask) | Only `description.rviz` exists | Week 3-5 | Small |
| 7 | **Calibration analysis scripts:** IMU bias and noise from a bag; straight-line and square-test errors from `/odom_scan` and `/odometry/filtered`; D455 wall-distance check | BUILD_GUIDE asks for these numbers, but no tool computes them | Week 5 | Small |
| 8 | **Plan-to-map alignment tool:** rigid transform from named corners measured in the plan and picked in the map, then transforms `walls.csv`, the corridor polygon and `truth.csv` into the map frame | The O2, O4 and O8 scripts need truth in the map frame | Week 10 | Small |
| 9 | **Run scripts:** one `tmux` script (or systemd service) that starts a run, records a bag, and writes a `run_info.txt` (commit, parameters, time, power mode, battery) | EXPERIMENTS asks for these details for every run; easier than remembering | Week 5 | Small |
| 10 | **Backup script:** copy `~/merz_data` to the laptop and OneDrive, and check sizes | Losing bags would cost weeks | Week 5 | Small |
| 11 | **Battery monitoring** (if the controller or battery reports voltage): a node that warns, and stops autonomy below a threshold | Nothing in the software watches the battery (safety checklist) | Week 9 | Small |
| 12 | **Store sign crops** (`landmarks.photo_id`) | The website shows real signs without photos until this is done (`web/README.md`) | Week 16 | Small (optional) |
| 13 | **D455 visual odometry** as a second velocity source in the EKF (no encoders, decisions #22), only if the corridor test fails | OPEN_ISSUES #17 | Only if needed | Medium |
| 14 | **Privacy step for photos** (skip or blur frames with people in them) | Junction photos are published on the website (section 7) | Before Week 16 | Small |

---

## 7. Other important things

1. **Risk assessment and permission.** A mobile robot in a public building usually needs a university risk assessment,
   and permission from the building manager. Ask Dr Wright in Week 1, as it can take time and blocks every floor test.
2. **Battery safety.** If the rover uses LiPo batteries: charge only with the right charger, in a LiPo bag, never
   unattended, and store them at storage voltage over the leave.
3. **Photos of people (GDPR).** Junction photos and bag images may include students and staff, and the website publishes
   photos. Run when the corridors are quiet, and blur or delete frames with people in them before anything is published.
   Check the university's rules with Dr Wright.
4. **Stairs and drops** (OPEN_ISSUES #20). The sensors cannot see a floor edge. Test only where there are no drops, or put
   a keep-out zone around them, and **never leave the rover running unattended**.
5. **Glass** (OPEN_ISSUES #4). Mark every glass wall and door on a keep-out mask before autonomous runs.
6. **Record everything.** Every run gets a logbook entry: date and time, lighting, people, door states, commit, parameter
   files, bag name, power mode, battery. Without these, a result cannot be used in the report.
7. **Decide pass rules before the runs.** A pass rule chosen after seeing the results is not a valid test (EXPERIMENTS).
8. **Back up weekly**, and always before the leave.
9. **Keep `main` working.** Only merge what has built and been tested on the Jetson. Tag milestones.
10. **One thing at a time.** One new device, one new parameter or one new node per test.
11. **Keep the website small.** It is a demonstrator. The marks are in the robot (decisions #5).
12. **Questions to settle with Dr Wright early:** floor plan (#14), long-corridor odometry result (#17), O2 and O8 pass
    rules (#21), independent stop (decisions #19), test permission, poster date (#11).

---

## 8. Daily routine and checklists

### Start of each working day (Jetson)
```bash
cd ~/merz-mapper && git switch main && git pull
```
```bash
cd ros2_ws && colcon build --symlink-install && source install/setup.bash
```
```bash
df -h ~                                                        # disk space left for bags
```
```bash
cd ~/merz-mapper && cp -n docs/logbook/TEMPLATE.md docs/logbook/$(date +%F).md   # today's logbook entry
```
Check the battery, the emergency stop and the cables. Plan the day in the logbook.

### Before any motion
Go through the safety checklist in `ros2_ws/src/merz_bringup/README.md`.

### End of each working day
- Write the logbook (done, results, problems, next).
- Back up new bags and maps.
- Commit and push config and logbook changes on a branch, and open a PR.
- On Fridays: update `docs/MERZ_MAPPER_STATE.md` (and the claude.ai mirror) and `docs/HARDWARE_REGISTER.md`.

### Useful commands for debugging
| Command | Shows |
| --- | --- |
| `ros2 topic list`, `ros2 topic hz <topic>`, `ros2 topic echo <topic> --once` | Is it publishing, and how fast |
| `ros2 topic info -v <topic>` | Publishers, subscribers and QoS (for "no messages" problems) |
| `ros2 node list`, `ros2 param get <node> <param>` | What is running, and its settings |
| `ros2 run tf2_tools view_frames`, `ros2 run tf2_ros tf2_echo map base_link` | The TF tree, and one transform |
| `ros2 doctor --report` | General ROS problems |
| `tegrastats`, `jtop` | Jetson temperature, power and load |
| `dmesg -w`, `lsusb -t` | USB errors and USB speeds |
| `ros2 bag info <bag>` | What is in a bag |

When something breaks, look in `docs/BUILD_GUIDE.md` section 7 (troubleshooting) first, then paste the full error into a
Claude Code session.
