# O1 / G1 checklist: from parts arrival to the first manual map

**Deadline: G1 / O1, Fri 18 Dec 2026** (last working day before leave on 19 Dec; OPEN_ISSUES #5). **Aim: first map by Fri 11 Dec.**
O1 pass rule (`docs/planning/experiments.md`): *all sensors publishing at the same time; a map saved; the bag replays.*

**Status: PLANNED.** Tick a box only when the result is written in `docs/logbook/` (date, versions, command, output).
How-to for each step: `docs/runbooks/jetson-bringup.md` (written as "runbook §n"). Day-by-day timing: `docs/planning/hardware-arrival-plan.md`.
Markers: **[ROVER]** = depends on the unknown rover; **[MISSING]** = part not ordered; **[ASK]** = needs Dr Wright.

**Order rule.** Tier 1 is the minimum for O1, and every Tier 1 item comes before any Tier 2 item. If a Tier 1 item is blocked,
go on to the next Tier 1 item; do not start Tier 2. Tier 3 waits until Tier 1 is complete. The first map can be made by
**pushing the sensor rig by hand** (`mapping.launch.py base:=false`), so O1 does not have to wait for the motors.

---

## Tier 1: essentials for O1 (in this order)

### A. Decisions and orders (this week; no hardware needed)
- [ ] **[ASK]** Distro agreed: JetPack 6.2.x + Ubuntu 22.04 + Humble (PROPOSED, `docs/research/distro-decision.md`), or the fallback
- [ ] **[ASK]** The IMU fallback in distro-decision.md §5 agreed (scan-only map for G1; separate IMU or not)
- [ ] **[ASK]** Access to an x86_64 Ubuntu 20.04/22.04 PC for SDK Manager, or agreement to use the host-free route (runbook §2.2)
- [ ] **[ASK]** Permission to test in Merz Court corridors, and which corridor to map first
- [ ] **[MISSING]** Order a wireless gamepad (only needed for driving; a pushed map does not need it)
- [ ] A USB-C 3.x cable for the D455 (short, good quality) and, for route 2.2, a USB-to-M.2 NVMe enclosure, a 64 GB+ microSD card
      and a 16 GB+ USB stick. Check which ones the kit already has.

### B. Arrival and inspection (day 1)
- [ ] Unpack; photograph every label (runbook §1)
- [ ] Record the Jetson SKU, carrier and RAM **[SKU]**; check the camera is a D455 (not a D455f)
- [ ] Each part checked against the parts list; anything missing reported to Dr Wright the same day
- [ ] HARDWARE_REGISTER rows set to RECEIVED (via a PR; the register is not edited in this branch)
- [ ] **[ROVER]** Rover inspected: motors, controller, encoders?, battery voltage/capacity, mounting points, any existing computer
      (OPEN_ISSUES #1). Photos and notes in the logbook

### C. Jetson platform (week 2)
- [ ] NVMe fitted; JetPack 6.2.x flashed; **root is on the NVMe** (`findmnt -n -o SOURCE /`) (runbook §2, gate 2.5)
- [ ] Versions table filled in: L4T, JetPack, CUDA, TensorRT, power mode (runbook §1)
- [ ] Power mode set and recorded; USB autosuspend off; SSH works (runbook §3)
- [ ] ROS 2 Humble installed; the `/chatter` pub/echo gate passes (runbook §4.1)
- [ ] librealsense **v2.59.1** built with RSUSB; `rs-enumerate-devices` shows the D455 on **USB 3.x** (runbook §4.2)
- [ ] Workspace imported; `rf2o_laser_odometry`, `sllidar_ros2`, `realsense2_camera`, `explore_lite` each build alone (runbook §4.4)
- [ ] Full `colcon build` and `colcon test` pass on the Jetson (OPEN_ISSUES #16); third-party commits recorded
- [ ] udev rules installed with the real IDs; `/dev/rplidar` and `/dev/c920` survive a replug (runbook §5)

### D. Sensors one at a time, on the bench (week 3)
- [ ] **RPLIDAR S2:** `/scan` at about 10 Hz for 5 min; outline correct in RViz (runbook §6.1)
- [ ] **D455 depth + colour:** colour and aligned depth at about 15 Hz for 10 min, direct port; 2 m wall reads about 2 m (runbook §6.2)
- [ ] **D455 IMU: GO / NO-GO by the end of its time-boxed day** (runbook §6.3)
  - [ ] GO: `/camera/camera/imu` steady for 10 min; rotation shows on the right axis; firmware version logged
  - [ ] or NO-GO logged, with the fallback chosen (distro-decision.md §5) and Dr Wright told
- [ ] **C920:** `/sign_cam/image_raw` at about 10 Hz, 1920x1080 MJPEG (runbook §6.4)
- [ ] **TF:** `description.launch.py` gives one connected tree (`view_frames`), placeholder poses accepted for the bench (runbook §6.6)
- [ ] **All sensors together for 20 min** via `sensors.launch.py`: rates within about 10%, no USB resets in `dmesg`, peak temperature logged
      (runbook §6.7). **This is the first half of O1.**

### E. Bags (week 3, as soon as D passes)
- [ ] 2-min bench bag recorded with `record_bag.launch.py`; `ros2 bag info` counts match the live rates (runbook §7)
- [ ] The bag replays, and `/scan` replays at about 10 Hz
- [ ] Bags are on the NVMe; free space checked

### F. Sensors on a moving platform (week 4)
- [ ] **[MISSING][ROVER]** Mast and mounts designed from the rover CAD and printed, or a temporary rigid mount (tape and cable ties are fine for G1)
- [ ] LIDAR level, with a clear view; nothing of the rover in the scan plane (check `/scan` in RViz)
- [ ] **[ROVER]** Power for the moving rig: battery + DC-DC for the Jetson and hub, ratings checked first (runbook §8); or the bench supply on a
      trolley with a long lead, if the battery is not ready
- [ ] Sensor poses measured into `sensor_poses.yaml`, with their uncertainty logged (build-guide.md §2)

### G. First manual map (target Thu 10 Dec, latest Fri 18 Dec)
- [ ] Permission confirmed; people nearby told; a second person present
- [ ] Choose the route: driven (needs Tier 2 motors + gamepad) **or pushed by hand** with `ros2 launch merz_bringup mapping.launch.py base:=false`
- [ ] `record_bag.launch.py name:=first_map` running in a second terminal
- [ ] Move slowly, turn gently, close a loop if possible; watch `/map` in RViz
- [ ] Map saved: `ros2 run nav2_map_server map_saver_cli -f ~/merz_data/maps/first_map` (build-guide.md §6)
- [ ] The `first_map` bag replays, and SLAM rebuilds a map from it offline (`use_sim_time`) (hardware-arrival-plan.md Fri 11 Dec)
- [ ] **O1 met:** all sensors publishing together + map saved + bag replays, with evidence in the logbook (rates, screenshots, bag names)

### H. Before leave (by Thu 17 Dec)
- [ ] Bags, maps and logbook copied to the laptop **and** OneDrive; the copies open
- [ ] All config and logbook changes committed and pushed; commit tagged `g1-first-map`
- [ ] STATE updated with exactly where work stopped (via a PR)
- [ ] Rover stored safely: battery disconnected and at its storage charge **[ROVER]**

---

## Tier 2: makes the map better, or lets the rover drive (only after Tier 1 is complete)
- [ ] **[ROVER]** Motor interface identified; `merz_base` backend chosen; wheels off the ground for the first tests
- [ ] **[ROVER]** Stop path that does not depend on the Jetson (decisions #19 R1, OPEN_ISSUES #19); physical power cut in reach
- [ ] **[MISSING]** Gamepad: deadman works; switching the pad off stops the output (runbook §6.5; safety-review.md High finding)
- [ ] Motors: right direction and sign; kill teleop with wheels turning, and they stop within `command_timeout_s` (build-guide.md §4)
- [ ] IMU noise: 60 s still bag; gyro bias and SD logged (build-guide.md §5) (skip if the IMU was NO-GO)
- [ ] Scan odometry: measured 5 m straight line, 5 runs, against the laser meter (hardware-arrival-plan.md Tue 8 Dec)
- [ ] **Long plain corridor bag**: does `/odom_scan` keep counting? If not, tell Dr Wright at once (OPEN_ISSUES #17)
- [ ] EKF 2 m square, 3 times each way (build-guide.md §5)
- [ ] D455 flat-wall test at 1, 2, 3 and 4 m (build-guide.md §5)
- [ ] Test whether `m-explore-ros2` `main` builds on apt Humble (runbook §4.4); if so, propose replacing the pin in decisions #19
- [ ] Power budget: measured current of each device and of the whole rig; battery runtime estimate (O1 threat in experiments.md)

## Tier 3: useful before leave, but not O1 (only if Tier 1 and 2 are done)
- [ ] **[MISSING]** C920 intrinsics with the checkerboard, autofocus off (build-guide.md §5)
- [ ] Bags with `images:=true` through the corridors, with one corridor kept apart as the O3 test set (hardware-arrival-plan.md Tue 15 Dec)
- [ ] Door-sign list (`signs.csv`) and glass-wall notes while in the building (Wed 16 Dec)
- [ ] Floor plan requested from estates or Dr Wright (OPEN_ISSUES #14)
- [ ] A second and a third map
- [ ] YOLO/TensorRT and OCR installs (week 7 in the plan, after leave)

---

## If time runs short (cut in this order)
1. Tier 3 entirely.
2. Tier 2 calibration items (they are needed for O2/O8, not O1). Keep the corridor bag: it tells you about OPEN_ISSUES #17 early.
3. Driving: make the G1 map **pushed by hand** (`base:=false`).
4. The D455 IMU: map with scan odometry only, and log the deviation.
Never cut: all sensors together for 20 min, a saved map, a bag that replays, and the backups.
