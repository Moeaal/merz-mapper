# merz_sim

**Status: IMPLEMENTED - not yet built or tested on hardware, and NOT YET RUN IN ROS OR GAZEBO.** Everything here is
PROPOSED. The code was written in a cloud container where ROS 2 and Gazebo could not be installed (see "What was and was
not run" below). Only the pure-Python parts (world generator, bridge table, xacro expansion, config cross-checks,
simulated base logic) have been run, as unit tests. Expect corrections the first time it is launched.

A Gazebo simulation, so that SLAM Toolbox, Nav2 and frontier exploration can be developed before the rover arrives.
It runs the **real** configuration from `merz_bringup` and `merz_exploration` (EKF, rf2o, SLAM, Nav2, twist_mux,
explore_lite), unchanged apart from `use_sim_time`. The simulator publishes the same topics and frames as the real
drivers, so whatever is tuned here carries over to the rover.

## What it contains
| Part | File | Notes |
| --- | --- | --- |
| Rover model | `urdf/merz_sim_rover.urdf.xacro` | Parametric differential drive. Same frame names as `merz_description` + the RealSense driver |
| All rover numbers | `config/sim_rover.yaml` | **One file**: chassis, wheels, casters, mast, limits, sensor poses and settings. Placeholders (TODO: measure on rover). Sensor poses equal `merz_description/config/sensor_poses.yaml` (a test checks this) |
| 2D LIDAR | `gpu_lidar`, `/scan`, frame `laser` | RPLIDAR S2-like: 10 Hz, 30 m, 1600 samples per turn (S2: about 3000; halved for speed) |
| D455 | `rgbd_camera` + `imu` | Colour, depth (aligned by construction), camera_info, IMU at 200 Hz in `camera_imu_optical_frame`. Point cloud from `depth_image_proc` |
| Sign camera | `camera` on a mast at 1.5 m | `/sign_cam/image_raw`, `/sign_cam/camera_info`, frame `sign_camera_optical_frame` |
| World | `worlds/merz_floor.yaml` -> SDF | Made-up university floor (not Merz Court): 30 m main corridor, 4-way junction, atrium (open area) with pillars, 6 rooms (2 behind closed doors), north dead end, **3 entrances** (west, south, east), each with a closed porch so exploration can finish. `merz_sim/world_gen.py` writes the SDF at launch |
| Gazebo-version table | `merz_sim/gz_compat.py` (+ the `gz_version` switch at the top of the xacro) | The only places with Fortress/Harmonic differences |
| Simulated base | `sim_base_node` | `/cmd_vel_mux` -> **merz_base's own `BaseController`** (0.5 m/s clamp, ramp, timeout) -> `/sim/cmd_vel` -> Gazebo |
| Headless check | `sim_check_node` | Waits for `/map`, odometry, sensor topics and TF; exit code 0 = pass |
| One launch file | `launch/sim.launch.py` | Starts everything |

## Distro and simulator choice (PROPOSED)
- **ROS 2 Humble + Gazebo Fortress** by default. Humble is what JetPack 6 (Ubuntu 22.04) gives, and is the
  repository's target (decisions #6, OPEN_ISSUES #2, `docs/CLAUDE_CODE_ROADMAP.md`). Fortress is the Gazebo release
  Humble's own binaries (`ros-humble-ros-gz`, from packages.ros.org) are built against [S1].
- **Caveat:** Fortress is reported to reach end of life in September 2026 [S2] (a secondary source; the official
  gazebosim.org page could not be reached from this session). The binaries stay installable but get no fixes.
- **Harmonic** (newer, Jazzy's pairing) also works with Humble, but only with ros_gz binaries from the Gazebo
  (OSRF) package repository or a source build [S1, S3]. Pass `gz_version:=harmonic`. The apt package name commonly
  given for it, `ros-humble-ros-gzharmonic`, was **not** confirmed in this session.
- Gazebo Classic (gazebo11) was not used: it is end of life and is not the default for any current ROS 2 release.
- If the supervisor picks Jazzy: use `gz_version:=harmonic`, and change SLAM Toolbox to its lifecycle launch (see
  `merz_bringup/launch/slam.launch.py`). Nothing else in this package should need to change.
- The simulation is for an **x86-64 Ubuntu 22.04 PC** (a lab PC, or a laptop that can run Ubuntu). It is not meant to
  run on the Jetson; the Raspberry Pi 5 is likely too slow for the cameras (`cameras:=false` may be usable there).

Sources (accessed 2026-11-05; to be added to `docs/RESEARCH_INDEX.md` by the student):
[S1] ros_gz README (version/binary table), https://github.com/gazebosim/ros_gz ;
[S2] "Software dependencies and versions", CPS Gazebo docs, https://cps-gazebo-sim.readthedocs.io/en/latest/quick_info/software_dependencies_and_versions.html ;
[S3] Open Robotics Discourse, "Will Gazebo Harmonic ever be recommended for ROS2 Humble?", https://discourse.openrobotics.org/t/will-gazebo-harmonic-ever-be-recommended-for-ros2-humble/48820 .

## The two odometry modes (decisions #10 is still PROPOSED)
| | (a) `odom_mode:=wheel` | (b) `odom_mode:=scan` (default) |
| --- | --- | --- |
| Linear motion | Simulated wheel odometry (Gazebo DiffDrive, from wheel joint angles) -> covariance relay -> `/wheel/odometry` | rf2o scan matching `/scan` -> `/odom_rf2o` -> covariance relay -> `/odom_scan` |
| Yaw rate | D455 IMU gyro z | D455 IMU gyro z |
| EKF config | `merz_bringup/config/ekf.yaml` + `config/ekf_wheel_mode.yaml` (replaces `odom0` only) | `merz_bringup/config/ekf.yaml`, unchanged (the real rover's plan) |
| Fused from odometry | vx, vy (vy = 0, no sideways motion) | vx, vy |

The two modes differ **only** in where linear motion comes from, which suits the O8-style comparison.

**Mode (b) uses no simulator ground truth.** In mode (b) the DiffDrive odometry is not bridged at all; the DiffDrive
TF is never bridged in either mode; no pose or ground-truth topic is bridged; rf2o has `init_pose_from_topic: ''`. The
estimator only sees `/scan`, `/camera/camera/imu` and the static TF from the URDF. `test/test_gz_compat.py` and
`test/test_sim_config.py` check this, and `sim_check_node` fails if `/wheel/odometry` or `/sim/wheel_odometry_raw`
has any publisher in scan mode.

TF: `map -> odom` SLAM Toolbox, `odom -> base_link` EKF only, sensor frames from `robot_state_publisher`, as REP 105 and
`docs/SOFTWARE_ARCHITECTURE.md`.

## Install (Ubuntu 22.04, ROS 2 Humble, x86-64 PC). Not run in this session
```bash
sudo apt install ros-humble-desktop ros-humble-ros-gz ros-humble-navigation2 ros-humble-nav2-bringup \
  ros-humble-slam-toolbox ros-humble-robot-localization ros-humble-twist-mux ros-humble-xacro \
  ros-humble-depth-image-proc ros-humble-teleop-twist-keyboard python3-vcstool python3-rosdep
```
`ros-humble-ros-gz` pulls in Gazebo Fortress. For Harmonic instead, follow the Gazebo docs for "Harmonic with Humble"
(OSRF repository) and do not install `ros-humble-ros-gz`.

## Build
```bash
cd ~/merz-mapper/ros2_ws
vcs import src < merz.repos
```
```bash
rosdep install --from-paths src --ignore-src -r -y
```
```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```
`merz.repos` brings rf2o and explore_lite (m-explore-ros2, pinned for Humble; decisions #19). `rosdep` will also want the
real-sensor drivers that `merz_bringup` depends on (realsense2_camera, usb_cam); they install but are not used here.

## Run
Everything (headless Gazebo, SLAM, Nav2, exploration), mode (b), west entrance:
```bash
ros2 launch merz_sim sim.launch.py
```
Mode (a), from the south entrance, with the Gazebo window and RViz:
```bash
ros2 launch merz_sim sim.launch.py odom_mode:=wheel entrance:=south gui:=true rviz:=true
```
Lighter run, LIDAR + IMU only (no camera rendering):
```bash
ros2 launch merz_sim sim.launch.py cameras:=false
```
SLAM with keyboard driving and no Nav2 (keys go through twist_mux at teleop priority, as the gamepad does):
```bash
ros2 launch merz_sim sim.launch.py nav:=false rviz:=true
```
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=/cmd_vel_teleop -p speed:=0.3 -p turn:=0.8
```
Save the map at the end:
```bash
ros2 run nav2_map_server map_saver_cli -f ~/merz_data/maps/sim_map
```
Arguments: `odom_mode` (scan | wheel), `entrance` (west | south | east), `gz_version` (fortress | harmonic),
`cameras`, `gui`, `rviz`, `nav`, `explore`, `explore_delay_s` (default 25 s), `world` (another layout YAML).
To change the rover, edit only `config/sim_rover.yaml`; to change the building, edit only `worlds/merz_floor.yaml`.
To look at the generated world: `ros2 run merz_sim make_world -o /tmp/merz_floor.sdf`, then `ign gazebo /tmp/merz_floor.sdf`.

## Headless check (the smoke test to run first)
Terminal 1:
```bash
ros2 launch merz_sim sim.launch.py cameras:=false explore:=false
```
Terminal 2, after about 10 s:
```bash
ros2 run merz_sim sim_check_node --ros-args -p odom_mode:=scan -p cameras:=false -p timeout_s:=120.0
```
It prints OK/FAIL for `/clock`, `/scan`, `/camera/camera/imu`, `/odometry/filtered`, `/map`, the mode's odometry
topics, the TF chain `map->odom->base_link` and two sensor frames, then `RESULT: PASS` or `RESULT: FAIL`. Repeat with
`odom_mode:=wheel` and with `cameras:=true`. It shows data flows; it does not judge map quality or exploration.

## What was and was not run
Run (2026-11-05, cloud container, Ubuntu 24.04, Python 3.13, no ROS):
- `python -m pytest ros2_ws/src/merz_sim`: **61 passed**. Covers the world (valid SDF for both Gazebo versions,
  closed building, every entrance reachable from every other with a robot-sized clearance, junction, rooms behind
  closed doors unreachable), the bridge table per mode (no ground truth in mode b), the xacro (expands for both versions,
  frames, sensor poses = merz_description, LIDAR 10 Hz/30 m, mast at 1.5 m, fits the Nav2 footprint, 0.5 m/s limit),
  the launch file's mode branches (by reading its source), and the simulated base with merz_base's controller.

**Not run** (installing ROS 2 / Gazebo was not possible in this session):
- `colcon build`, `colcon test`, any `ros2 launch`, Gazebo itself, the bridge, SLAM, Nav2, explore_lite, rf2o.
- So these are unchecked guesses, from memory of the Fortress/ros_gz Humble APIs, to verify on first launch:
  Gazebo topic names derived by the sensors (`/camera/sim_rgbd/image`, `.../depth_image`, `.../camera_info`,
  `/sign_cam/camera_info`); that `ignition_frame_id` sets the frame of each message; that friction set on the
  fixed-joint caster links survives URDF-to-SDF lumping; `ros_gz_sim create -world`; `depth_image_proc`'s executable
  name `point_cloud_xyz_node`; `--headless-rendering` needing EGL on the PC. Check with `ign topic -l` and
  `ros2 topic list` / `ros2 run tf2_tools view_frames`.
- How well rf2o and SLAM Toolbox do in the plain simulated corridors (OPEN_ISSUES #17 is exactly this question:
  this simulation is a cheap first look, not evidence about the real corridor).

## Known gaps
- No glass (OPEN_ISSUES #4): Gazebo's GPU LIDAR sees every surface, so glass behaviour is not simulated.
- Colour `camera_info` is not published (only the aligned-depth one, which `landmark_node` and `depth_image_proc` use).
- Skid-steer slip is not modelled; DiffDrive is an ideal two-wheel drive.
- `tools/test_static_refs.py` needs two small changes to know about this package (it was out of scope here): add
  `'merz_sim'` to the package set in `test_the_workspace_was_found`, and add `('ros_gz_sim', 'create')`,
  `('ros_gz_bridge', 'parameter_bridge')` and `('depth_image_proc', 'point_cloud_xyz_node')` to
  `THIRD_PARTY_EXECUTABLES`. Until then those 2 tests fail.
