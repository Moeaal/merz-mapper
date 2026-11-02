# Software architecture

**Everything below is PLANNED. Nothing is implemented yet.** Change a row's
status to IMPLEMENTED only when the code is in `ros2_ws/src/`, and to TESTED only
when a logbook entry records the result.

## Packages
| Package | Contents | Objectives | Status |
| --- | --- | --- | --- |
| `merz_description` | URDF/xacro with measured sensor poses | O1, O4 | PLANNED |
| `merz_bringup` | Launch files; EKF, SLAM Toolbox, Nav2 YAML | O1, O2 | PLANNED |
| `merz_exploration` | Frontier exploration wrapper + access-zone recorder | O2, O5 | PLANNED |
| `merz_perception` | YOLO (TensorRT) detector, PaddleOCR sign reader | O3 | PLANNED |
| `merz_semantic_map` | Landmark fusion (detection + depth + pose) and SQLite writer | O4, O6 | PLANNED |
| `web/` (not ROS) | FastAPI route API + mobile website | O6, O7 | PLANNED |

## Planned data flow
```
RPLIDAR S2 --/scan--> SLAM Toolbox --/map, map->odom--> Nav2 <-- frontier explorer
Scan odom  --/odom_scan--\   (LIDAR scan matching; wheel odom only if encoders exist - decisions #10)
D455 IMU  --/imu---------> robot_localization EKF --/odometry/filtered, odom->base_link
D455 depth/colour --\
C920 image ---------> merz_perception --detections + text--> merz_semantic_map --> SQLite
                                                   (uses TF map->camera)          |
                                                                                   v
                                                                     FastAPI --> website
```

## TF tree (REP 105)
`map -> odom -> base_link -> {laser, camera_link (D455), sign_camera, imu}`
- `map->odom`: SLAM Toolbox. `odom->base_link`: EKF only (wheel driver must NOT
  also publish it). Sensor frames: static, from URDF.

## Topics / services (planned names - confirm when drivers run)
| Topic | Type | Publisher |
| --- | --- | --- |
| `/scan` | sensor_msgs/LaserScan | sllidar_ros2 |
| `/camera/...` (depth, color, imu) | Image / Imu | realsense2_camera (names depend on version/params) |
| `/sign_cam/image_raw` | sensor_msgs/Image | usb_cam |
| `/odometry/filtered` | nav_msgs/Odometry | robot_localization |
| `/map` | nav_msgs/OccupancyGrid | slam_toolbox |
| `/landmarks` | custom msg (TBD) | merz_semantic_map |

## Dependencies
ROS 2 distro TBD (decisions #6), slam_toolbox, nav2, robot_localization,
explore_lite (TBD, decisions #7), laser scan-matching odometry (TBD, decisions #10), librealsense2, TensorRT (JetPack), PaddleOCR, SQLite, FastAPI.
