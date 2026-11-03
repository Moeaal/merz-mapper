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

## Unit tests that pass on Windows
`test/test_sensor_config.py` checks config rules: teleop priority above navigation, short mux timeouts,
deadman required, teleop speed within limits, and driver paths matching the udev symlinks.
