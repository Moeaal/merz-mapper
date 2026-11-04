# merz_bringup

**Status: IMPLEMENTED - not yet built or tested on hardware.** Parameter names and topics are from driver docs
and source, and have not been checked against the real devices.

Launch files and configuration for sensors, teleop, localisation, SLAM and navigation.

## Install the drivers (Ubuntu 22.04, Humble)
```bash
sudo apt install ros-humble-usb-cam ros-humble-joy ros-humble-teleop-twist-joy ros-humble-twist-mux \
  ros-humble-rosbag2-storage-mcap ros-humble-robot-localization ros-humble-slam-toolbox \
  ros-humble-navigation2 ros-humble-nav2-bringup ros-humble-xacro ros-humble-camera-calibration
# sllidar_ros2, rf2o and m-explore-ros2 are source builds: see ros2_ws/merz.repos
# librealsense + realsense2_camera: RSUSB source build, see docs/BUILD_GUIDE.md section 3 (OPEN_ISSUES #3)
```

## One sensor at a time
| Command | Expect |
| --- | --- |
| `ros2 launch merz_bringup lidar.launch.py` | `/scan` at about 10 Hz |
| `ros2 launch merz_bringup d455.launch.py` | `/camera/camera/color/image_raw`, `/camera/camera/aligned_depth_to_color/image_raw`, `/camera/camera/imu` |
| `ros2 launch merz_bringup c920.launch.py` | `/sign_cam/image_raw` at about 10 Hz |
| `ros2 launch merz_bringup teleop.launch.py` | `/joy`; `/cmd_vel_mux` moves only while the deadman is held |
| `ros2 launch merz_bringup sensors.launch.py c920:=false` | all sensors bar the ones switched off |
| `ros2 launch merz_bringup record_bag.launch.py name:=test` | a bag in `~/merz_data/bags` |

## Velocity command chain
```
Nav2 --/cmd_vel--> twist_mux (priority 10) ---+
Gamepad --/cmd_vel_teleop--> twist_mux (100) -+--/cmd_vel_mux--> merz_base
```
Stock Nav2 ends at `/cmd_vel`, so the mux output needs its own name. `merz_base` listens only to `/cmd_vel_mux`.

## Odometry, EKF and SLAM (decisions #10, #14)
`ros2 launch merz_bringup mapping.launch.py` runs the whole manual-mapping stack for G1 (`base:=false` if pushing by hand).
```
/scan -> rf2o -> /odom_rf2o -> scan_odom_relay (adds covariance) -> /odom_scan -+
/camera/camera/imu (gyro z only) -----------------------------------------------+-> EKF -> odom->base_link
/scan -> SLAM Toolbox -> /map, map->odom
```
Each EKF setting and why it is that value is in the comments of `config/ekf.yaml`.

| Setting | Why | Tune on the rover? |
| --- | --- | --- |
| `odom0_config`: vx, vy | Scan matching tells how far the rover moved; its pose is not fused, as it drifts | Add vyaw if gyro bias causes visible heading drift |
| `imu0_config`: vyaw only | No magnetometer means no absolute heading; integrated accelerometer drifts in seconds | No |
| `vx_std`, `vy_std`, `vyaw_std` in `scan_odometry.yaml` | rf2o gives none, and zero would mean "perfect" | **Yes**: straight-line test against the laser meter |
| IMU covariance | From the driver | **Yes**: stationary for 60 s; check against the measured noise |
| `process_noise_covariance` | Trust in the motion model | **Yes**: square-path test |
| `max_laser_range` in `slam.yaml` | Below 30 m, to limit noise from glass | **Yes**: check in the real corridors |

## Navigation and the full run
- `navigation.launch.py`: Nav2. Stock planner and controller values, limited to 0.5 m/s, no reversing. Spin and BackUp
  recoveries are removed until tested on the rover (`behavior_trees/`). Keep-out: `maps/README.md`.
- `explore_from_entrance.launch.py entrance:=<name>`: everything together. Add `perception:=false` until a model is
  trained. At the end `mission_node` saves `~/merz_data/maps/<entrance>_<time>.*`; the database is
  `~/merz_data/merz.sqlite`.

## Safety checklist: before any autonomous motion
Software stops are not proof the wheels stop. These checks have not yet been done on the real rover.
- [ ] A person is beside the rover at all times, with the gamepad, within reach of a **physical power cut**.
- [ ] The power cut has been tried while the wheels are turning.
- [ ] First run with the **wheels off the ground**: test that the deadman stops teleop, that holding it halts autonomy,
      and that killing the base node or `/cmd_vel_mux` stops the motors within `command_timeout_s`.
- [ ] Footprint and speed limits in `nav2.yaml` measured, not placeholders. First runs at reduced `max_vel_x`.
- [ ] TF checked in RViz: scan lines up with the walls and the rover faces the right way.
- [ ] Test area clear, permission to test obtained (minutes 2026-11-02), and people nearby informed.
- [ ] Glass walls and doors have keep-out zones, with the mask checked in RViz against the live map.
- [ ] Battery charged, and low-battery behaviour known. Nothing in the software monitors the battery.
- [ ] No stairs or drops in the test area. **The sensors are not set up to detect a floor edge.**

## Unit tests that pass on Windows
- `test/test_sensor_config.py`: teleop priority above navigation, short mux timeouts, deadman required, teleop speed
  within limits, driver paths matching the udev symlinks.
- `test/test_localisation.py`: covariance layout, plausibility gate, EKF owns `odom->base_link` and rf2o does not,
  fused axes, wheel odometry off by default.
- `test/test_navigation_config.py`: speed limit, no reversing, frames and odometry topic, moving recoveries removed,
  footprints equal, keep-out wired up, unknown space allowed for frontier goals.

**Not covered on Windows:** any launch file running, and whether Nav2 accepts these parameters.
