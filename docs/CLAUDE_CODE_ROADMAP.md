# Claude Code roadmap - building the Merz Mapper software

One stage per Claude Code session. Paste the **standard rules** below, then the stage prompt.
Review the branch on GitHub, merge, then tick the stage here.

**Where to run:** stages marked **[Pi]** need ROS 2 (`colcon build`) - run Claude Code on the
Raspberry Pi 5 (`curl -fsSL https://claude.ai/install.sh | bash`, then `cd ~/merz-mapper && claude`).
Stages marked **[Laptop]** are plain Python and can run on Windows.
**Target:** ROS 2 Humble (decisions #6; change here if the supervisor picks another distro).

## Standard rules (paste at the start of every stage)
```
Use the merz-mapper-engineering-brain skill. Read docs/MERZ_MAPPER_STATE.md and only the docs this stage needs.
Rules for this stage:
- Create a branch named stage-<N>-<short-name> from up-to-date main.
- Write clear, commented Python (rclpy) unless C++ is clearly needed. Keep it simple; no features beyond this stage.
- Put robot-specific numbers (sensor poses, footprint, noise values) in YAML params marked "TODO: measure on rover".
- Write unit tests for all logic that doesn't need hardware; run everything that can run on this machine and report exact results.
- Never call anything TESTED unless it was run on real hardware with results logged. Code that exists = IMPLEMENTED.
- Update docs/SOFTWARE_ARCHITECTURE.md (package status), docs/MERZ_MAPPER_STATE.md (a few lines), and draft today's logbook entry (leave Hours and Reflection blank).
- Commit, push the branch, and ask before anything else (no merging).
- Finish with: what you built, what is untested, what I must measure on the rover, and a plain-English explanation of how the code works so I can explain it in my report and demo.
```

## Stages
Stages 1-11 were written together on branch `build/all-code` (`docs/BUILD_ALL_PROMPT.md`). "Implemented, untested" means the code exists and its pure-Python unit tests pass on Windows, but it has not been built with colcon or run on hardware. Stage 11 was written before the rover's spec was known.

- [x] **1. Workspace and interfaces [Pi]** - implemented, untested
```
Stage 1: set up ros2_ws as a colcon workspace. Create package skeletons from SOFTWARE_ARCHITECTURE.md
(merz_description, merz_bringup, merz_perception, merz_semantic_map, merz_exploration) plus merz_interfaces
with messages Landmark (class, text, position in map frame, covariance, confidence, photo path, first/last seen)
and LandmarkArray. Add a README in ros2_ws explaining how to build and source. Make sure colcon build and colcon test pass.
```
- [x] **2. Robot description [Pi]** - implemented, untested
```
Stage 2: merz_description. Write a xacro URDF with base_link, laser, camera_link (D455 incl. imu frame),
sign_camera on a mast (~1.5 m). All poses come from config/sensor_poses.yaml (placeholders, TODO: measure).
Add a launch file for robot_state_publisher and an RViz config. Check the TF tree with check_urdf / tf2 tools.
```
- [x] **3. Sensor bringup and teleop [Pi]** - implemented, untested
```
Stage 3: merz_bringup sensors. Launch files for RPLIDAR S2 (sllidar_ros2), RealSense D455 (depth, colour,
gyro+accel united IMU), C920 (usb_cam), joystick teleop with deadman button and twist_mux (teleop overrides autonomy),
and a record_bag launch for /scan /tf /tf_static /imu /camera topics. Add udev rule files and instructions.
Each sensor must be launchable on its own. Document the exact install commands for the drivers.
```
- [x] **4. Odometry, EKF and SLAM [Pi]** - implemented, untested
```
Stage 4: localisation (decisions #10: no wheel encoders). Add laser scan-matching odometry (verify a maintained
ROS 2 package for our distro first, e.g. rf2o_laser_odometry; record the choice in decisions.md), robot_localization
EKF fusing scan odometry + IMU gyro z (two_d_mode), and slam_toolbox online async config. One launch file
"mapping.launch.py" for manual mapping (G1). Explain each EKF setting and which values must be tuned on the rover.
```
- [x] **5. Perception: detection and OCR [Laptop first, then Pi]** - implemented, untested
```
Stage 5: merz_perception. (a) Plain-Python core: detector wrapper (Ultralytics YOLO now, TensorRT engine later
via the same interface), sign-crop sharpness check, OCR wrapper (PaddleOCR, with a fallback), room-number
normaliser + validator using a configurable regex, and an offline script that runs on a folder of images and
writes a CSV. Unit-test the normaliser, sharpness check and CSV output. (b) ROS 2 nodes wrapping the core:
detector node (runs at a few Hz) and sign-reader node (triggered by sign detections). Add tools/extract_frames.py
to pull images from rosbags for labelling a custom dataset. Reuse ideas from tools/yolo_practice/ where useful.
```
- [x] **6. Semantic map and database [Pi]** - implemented, untested
```
Stage 6: merz_semantic_map. Landmark localiser: bbox -> median depth in box (reject outside 0.6-6 m) -> deproject
with camera intrinsics -> TF to map at the image timestamp -> associate with existing landmarks (distance gate +
class/text) -> running mean + count. SQLite writer with a documented schema (landmarks, entrances, access_zones,
junctions, photos). Unit tests with synthetic detections and known geometry (check positions to within 1 cm).
Also an option to compute landmark positions WITHOUT fusion (single sensor) for the O8 comparison.
```
- [x] **7. Exploration and access zones [Pi]** - implemented, untested
```
Stage 7: merz_exploration. Launch frontier exploration (explore_lite / m-explore-ros2, decisions #7) with Nav2.
Access-zone node: from a saved occupancy grid and an entrance start pose, flood-fill reachable free space and
list which door landmarks touch it; store per entrance in SQLite. Junction-photo node: save a photo + pose when
the robot is at a corridor junction (simple rule, documented). Unit-test the flood fill on small synthetic grids.
```
- [x] **8. Navigation and full autonomy launch [Pi]** - implemented, untested
```
Stage 8: Nav2 config for our rover (footprint from params, max speed 0.5 m/s, keep-out zones for glass via a
filter mask, D455 depth as extra costmap source). One launch "explore_from_entrance.launch.py entrance:=<name>"
that runs sensors, localisation, SLAM, Nav2, exploration, perception, semantic map and access zones together,
saves map + database at the end. Add a safety checklist to the README.
```
- [x] **9. Evaluation tools [Laptop]** - implemented, untested
```
Stage 9: tools/eval/ for O2-O8. Scripts: map coverage vs a corridor polygon; wall error vs floor plan
(mean, max, RMSE of distances); OCR read rate vs a manual sign list; landmark error vs laser-measured ground
truth; fused vs single-sensor comparison; access zones vs manual survey table; route-query timing. Each script
takes files as input, prints a table and saves report-ready plots (labelled axes, units). Unit tests with
synthetic data. Write docs/EXPERIMENTS.md with the procedure for each objective (ground truth, repeats, pass/fail).
```
- [x] **10. Demonstrator website [Laptop]** (keep small - demonstrator only) - implemented, untested
```
Stage 10: web/. FastAPI app reading the SQLite database: GET /entrances, GET /rooms?entrance=X (only reachable
rooms), GET /route?entrance=X&room=Y (shortest path over junction graph inside that access zone, with junction
photos as steps). Mobile-first static page: opened from a QR URL containing the entrance id, pick a room, see
step-by-step photo directions. Script to generate QR posters per entrance. Tests: route correctness on a sample
database and query time < 1 s.
```
- [x] **11. Rover base driver [Pi, after rover arrives]** - implemented, untested
```
Stage 11: the rover has arrived; its spec is in docs/HARDWARE_REGISTER.md. Write merz_base: a node that takes
/cmd_vel and drives the rover's motor controller, with a command timeout that stops the motors, and speed limits
from params. Ask me before guessing anything about the motor interface.
```

## After the hardware arrives (not code-writing - measuring)
Measure sensor poses -> update YAML; calibrate C920; tune EKF covariances (stationary + square-path tests);
record rosbags; first manual map (G1, by 18 Dec). Ask Claude Code: "help me run and log test X from EXPERIMENTS.md".
