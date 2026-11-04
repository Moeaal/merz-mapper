# Software architecture

Status rule: **IMPLEMENTED** means the code is in the repo. It becomes **TESTED** only when a logbook entry records a result on
hardware. As of 2026-11-03, all the code below is IMPLEMENTED: nothing has been built with colcon or run on hardware.
Unit tests of the pure-Python logic pass on Windows (`docs/BUILD_PROGRESS.md`). Names of third-party topics are from driver docs
and source, and must be confirmed when the drivers run.

Design rule: each package keeps its logic in plain Python modules with no `rclpy` import, wrapped by a thin `*_node.py`.

## Packages
| Package | Contents | Objectives | Status |
| --- | --- | --- | --- |
| `merz_interfaces` | Messages: `Detection(Array)`, `SignReading`, `Landmark(Array)` | O3, O4 | IMPLEMENTED |
| `merz_description` | xacro URDF; poses in `config/sensor_poses.yaml` (placeholders) | O1, O4 | IMPLEMENTED |
| `merz_bringup` | Sensor, teleop, EKF, SLAM and Nav2 config; top-level launch files; `scan_odom_relay_node` | O1, O2 | IMPLEMENTED |
| `merz_perception` | `detector_node` (Ultralytics or TensorRT engine), `sign_reader_node`, `offline_batch` | O3 | IMPLEMENTED |
| `merz_semantic_map` | `landmark_node`, SQLite database | O4, O6, O8 | IMPLEMENTED |
| `merz_exploration` | explore_lite launch; `access_zone_node`, `junction_photo_node`, `mission_node`; `compute_access_zones` | O2, O5, O7 | IMPLEMENTED |
| `merz_base` | `base_node`: serial, Jetson GPIO and mock backends, timeout, limits | O1 | IMPLEMENTED (rover unknown; mock by default) |
| `web/` (not ROS) | FastAPI route API, mobile page, QR posters, sample data | O6, O7 | IMPLEMENTED (sample data only) |
| `tools/eval/` (not ROS) | Scripts for O2-O8 | O2-O8 | IMPLEMENTED (synthetic data only) |

## Top-level launch files
| Command | Runs |
| --- | --- |
| `merz_bringup lidar`, `d455`, `c920`, `teleop` | One device at a time |
| `merz_bringup sensors` | All sensors + URDF |
| `merz_bringup mapping` | Manual mapping for G1: sensors, teleop, base, localisation, SLAM |
| `merz_bringup explore_from_entrance entrance:=X` | Full autonomy run |
| `merz_bringup record_bag` | Rosbag of a run |

## Data flow
```
RPLIDAR S2 --/scan--> rf2o --/odom_rf2o--> scan_odom_relay --/odom_scan--+
D455 IMU --/camera/camera/imu (gyro z only)------------------------------+--> EKF --/odometry/filtered, odom->base_link
/scan --> SLAM Toolbox --/map, map->odom--> Nav2 <-- explore_lite (goals)
                                             |
                                          /cmd_vel --> twist_mux <-- /cmd_vel_teleop <-- gamepad (deadman)
                                                           |
                                                     /cmd_vel_mux --> merz_base --> motors

D455 colour --> detector_d455 --/perception/d455/detections--+
D455 aligned depth, camera_info -----------------------------+--> landmark_node --/landmarks, SQLite
C920 --> detector_c920 --/perception/c920/detections--> sign_reader --/perception/sign_readings--^

/scan + TF + D455 colour --> junction_photo_node --> SQLite (junctions, edges, photos)
mission end --> saved map + posegraph --> access_zone_node --> SQLite (zones)
SQLite --> FastAPI --> website (phone, via an entrance QR code)
```

## TF tree (REP 105)
`map -> odom -> base_link -> {laser, camera_link -> (D455 optical + IMU frames), sign_camera -> sign_camera_optical_frame}`
- `map->odom`: SLAM Toolbox. `odom->base_link`: EKF only (rf2o has `publish_tf: false`). `base_link` is on the floor at the centre
  of rotation. Sensor frames: static, from the URDF, except for the D455's internal frames, from its driver's factory calibration.

## Topics
| Topic | Type | Publisher |
| --- | --- | --- |
| `/scan` | sensor_msgs/LaserScan | sllidar_ros2 |
| `/camera/camera/color/image_raw`, `.../aligned_depth_to_color/image_raw`, `.../depth/color/points`, `.../imu` | Image, PointCloud2, Imu | realsense2_camera (4.54+ naming; older drivers differ) |
| `/sign_cam/image_raw`, `/sign_cam/camera_info` | Image, CameraInfo | usb_cam |
| `/odom_rf2o` | nav_msgs/Odometry | rf2o_laser_odometry (no covariance) |
| `/odom_scan` | nav_msgs/Odometry | scan_odom_relay |
| `/odometry/filtered` | nav_msgs/Odometry | robot_localization |
| `/map` | nav_msgs/OccupancyGrid | slam_toolbox |
| `/cmd_vel` | geometry_msgs/Twist | Nav2 (velocity smoother) |
| `/cmd_vel_teleop` | geometry_msgs/Twist | teleop_twist_joy |
| `/cmd_vel_mux` | geometry_msgs/Twist | twist_mux; **only `merz_base` reads it** |
| `/perception/d455/detections`, `/perception/c920/detections` | merz_interfaces/DetectionArray | detector_node |
| `/perception/sign_readings` | merz_interfaces/SignReading | sign_reader_node |
| `/landmarks` | merz_interfaces/LandmarkArray | landmark_node |
| `/explore/resume`, `/explore/frontiers` | Bool, MarkerArray | mission_node, explore_lite |

## Services
`/mission_node/finish` (end the run), `/access_zone_node/compute` (both std_srvs/Trigger).

## Dependencies
ROS 2 Humble (decisions #21, DECIDED), slam_toolbox, nav2, robot_localization, twist_mux, joy, teleop_twist_joy, usb_cam, librealsense2 +
realsense2_camera. Source builds via `ros2_ws/merz.repos`: sllidar_ros2, rf2o_laser_odometry (decisions #14, PROPOSED), m-explore-ros2
(decisions #7, PROPOSED). Python: Ultralytics, TensorRT (JetPack), PaddleOCR or RapidOCR, FastAPI.

Database: `docs/DATABASE_SCHEMA.md`. Procedure: `docs/BUILD_GUIDE.md`. Experiments: `docs/EXPERIMENTS.md`.
