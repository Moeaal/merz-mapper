# Merz Mapper ROS 2 workspace

**Status: IMPLEMENTED - not yet built or tested on hardware.** This code was written on a Windows laptop with no ROS 2.
A cloud check on ROS 2 Humble (RoboStack, 2026-11-04) passed `colcon build` and `colcon test`; it has not yet been built on the
Jetson or Pi (`docs/archive/build-progress.md`).

**Target:** ROS 2 Humble, Ubuntu 22.04, JetPack 6.x (decisions #6, still PROPOSED). The full step-by-step
procedure is in `docs/runbooks/build-guide.md`.

## Packages
| Package | Purpose | Type |
| --- | --- | --- |
| `merz_interfaces` | `Detection`, `SignReading`, `Landmark` messages and their arrays | ament_cmake |
| `merz_description` | URDF/xacro; sensor poses in `config/sensor_poses.yaml` | ament_cmake |
| `merz_bringup` | Sensor drivers, teleop, EKF, SLAM, Nav2 config, top-level launch files | ament_python |
| `merz_perception` | YOLO detector and door-sign reader | ament_python |
| `merz_semantic_map` | Landmark localisation and the SQLite database | ament_python |
| `merz_exploration` | Frontier exploration, access zones, junction photos, mission end | ament_python |
| `merz_base` | `/cmd_vel` to motors, with a command timeout | ament_python |
| `merz_sim` | Gazebo simulation of the rover and a made-up floor, for SLAM, Nav2 and exploration (never launched yet) | ament_python |

## Design rule
Every package keeps its logic in plain Python modules with no `rclpy` import, and wraps them in a thin
`*_node.py`. The logic can therefore be unit-tested on Windows, and the nodes contain only ROS plumbing.

## Build (on the Jetson or the Pi)
```bash
cd ~/merz-mapper/ros2_ws
vcs import src < merz.repos                                  # sllidar_ros2, rf2o, m-explore-ros2
rosdep install --from-paths src --ignore-src -r -y
pip install -r requirements.txt
colcon build --symlink-install
source install/setup.bash
colcon test && colcon test-result --verbose                  # includes the ROS-only tests
```
Source `/opt/ros/humble/setup.bash` first. Put it in `~/.bashrc` once it works.

## Run the unit tests on Windows
From the repository root:
```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
```
ROS-only tests skip themselves on Windows. A skip is not a pass: they still need running on the Jetson.
