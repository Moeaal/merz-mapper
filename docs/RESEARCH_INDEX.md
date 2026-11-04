# Research index

Cache of verified findings so they are not searched again. Tag = short id used
in other docs. Add the access date for web sources. Proposal references [1]-[10]
are in the proposal and not repeated here.

## Hardware
| Tag | Source | Key finding | Accessed |
| --- | --- | --- | --- |
| H1 | SLAMTEC RPLIDAR S2 datasheet v2.0, https://bucket-download.slamtec.com/4a5f962943b5140f97ae3b7fab7ed9bdf2adee11/SLAMTEC_rplidar_datasheet_S2_v2.0_en.pdf ; Waveshare wiki https://www.waveshare.com/wiki/RPLIDAR_S2 | 10 Hz typical scan, 32 kHz sampling, 0.12° resolution; 30 m (white) / 10 m (black); UART 3.3 V level; 5 V supply, startup current up to 1.5 A | 2026-11-02 |
| H2 | Intel store D455 page, https://store.intelrealsense.com/buy-intel-realsense-depth-camera-d455.html | Ideal range 0.6-6 m; min-Z ~52 cm; <2% at 4 m; depth FOV 87°x58°; global shutter | 2026-11-02 |
| H3 | librealsense Jetson install doc, https://docs.ros.org/en/ros2_packages/humble/api/librealsense2/_sources/doc/installation_jetson.md.txt ; issue #12831 https://github.com/IntelRealSense/librealsense/issues/12831 | JetPack 6 needs RSUSB/libuvc source build or MIPI driver route; detection problems common | 2026-11-02 |

## Jetson / ROS 2 versions
| Tag | Source | Key finding | Accessed |
| --- | --- | --- | --- |
| J1 | NVIDIA forum, https://forums.developer.nvidia.com/t/title-beginner-seeking-setup-help-for-ros2-on-jetson-orin-nano-and-onboard-simulation-options/313529 | JetPack 6 = Ubuntu 22.04 -> install ROS 2 Humble from apt | 2026-11-02 |
| J2 | Open Robotics discourse, https://discourse.openrobotics.org/t/supporting-newer-versions-of-ubuntu/51924 | JetPack 7.x = Ubuntu 24.04; Orin support expected with 7.2 | 2026-11-02 |
| J3 | Community wiki (unofficial), https://github.com/ashBabu/Utilities/wiki/Flashing-Jetson | Reports JetPack 7.2 now supports Orin Nano; some Isaac ROS parts still Humble-only | 2026-11-02 |

## Navigation / exploration
| Tag | Source | Key finding | Accessed |
| --- | --- | --- | --- |
| N1 | Proposal refs [3] SLAM Toolbox, [4] Nav2, [6] Yamauchi 1997 | Core methods | - |
| N2 | m-explore-ros2, https://github.com/robo-friends/m-explore-ros2 | explore_lite port; Humble+; source build only; `return_to_init` param | 2026-11-02 |
| N3 | frontier_exploration_ros2, https://discourse.openrobotics.org/t/frontier-exploration-ros2-modern-autonomous-exploration-system-for-ros-2/57222 | Tested on Humble + Jazzy with Nav2 + SLAM Toolbox; author reports shorter paths than m-explore (author's own benchmark) | 2026-11-02 |
| N4 | roadmap_explorer, https://index.ros.org/r/roadmap_explorer/ | Frontier-based + roadmap; Humble tested | 2026-11-02 |
| N5 | Husarion exploration tutorial, https://husarion.com/tutorials/ros2-tutorials/10-exploration/ | Worked example: slam_toolbox + nav2 + explore_lite + sllidar_ros2 | 2026-11-02 |
| N6 | rf2o_laser_odometry `ros2` branch, https://github.com/MAPIRlab/rf2o_laser_odometry | GPL-3.0. Params: laser_scan_topic, odom_topic, publish_tf, base_frame_id, odom_frame_id, init_pose_from_topic, freq. Source: `publish()` sets **no covariance**. README does not name a ROS 2 distro, so Humble support is unconfirmed upstream | 2026-11-03 |
| N7 | Build log (anecdotal), https://hackmd.io/@ming0071/SJ61ZNg2R | Reports building rf2o on Humble from the Adlink-ROS `humble-devel` branch: the fallback | 2026-11-03 |
| N8 | sllidar_ros2 `launch/sllidar_s2_launch.py`, https://github.com/Slamtec/sllidar_ros2 | S2: serial_baudrate 1000000, scan_mode DenseBoost, executable sllidar_node | 2026-11-03 |
| N9 | m-explore-ros2 README and `explore/config/params.yaml`, https://github.com/robo-friends/m-explore-ros2 | Package explore_lite, executable explore; topics explore/resume (Bool), explore/frontiers (markers); stock params incl. min_frontier_size 0.75, progress_timeout 30 | 2026-11-03 |
| N10 | Ultralytics TensorRT page, https://docs.ultralytics.com/integrations/tensorrt/ | `format="engine"`; `YOLO("x.engine")` loads for inference; NVIDIA GPU needed; engines are hardware- and runtime-specific; current versions use `quantize=16/8` in place of deprecated `half`/`int8` | 2026-11-03 |

## ROS 2 Humble config validation (`build/config-check`, 2026-11-04)
Every parameter and plugin name in `merz_bringup/config` was checked against the source that declares it, at the
commits below. docs.nav2.org and docs.ros.org were blocked by this session's network, so the docs were read from
their GitHub sources instead.
| Tag | Source | Key finding | Accessed |
| --- | --- | --- | --- |
| C1 | Nav2 `humble` branch, commit 3c3db59, https://github.com/ros-navigation/navigation2/tree/humble (`nav2_bringup/params/nav2_params.yaml`, `nav2_behavior_tree/CMakeLists.txt`, `*/plugins.xml`, each server's `declare_parameter` calls) | All Nav2, DWB, costmap, planner, smoother, behaviour, waypoint-follower, velocity-smoother and map_server keys and plugin classes in `nav2.yaml`/`keepout.yaml` exist in Humble. All 47 BT `plugin_lib_names` are Humble libraries. DWB in Humble never reads `FollowPath.stateful` (only the goal checker does); harmless, kept for parity with the stock file | 2026-11-04 |
| C2 | Nav2 Humble `nav2_common/launch/rewritten_yaml.py` (same commit) | `param_rewrites` **only replaces keys already in the YAML**; it never adds one. `nav2_bt_navigator/src/navigators/navigate_to_pose.cpp` then falls back to the stock `navigate_to_pose_w_replanning_and_recovery.xml` (has Spin + BackUp) | 2026-11-04 |
| C3 | Nav2 Humble `nav2_behavior_tree/include/nav2_behavior_tree/bt_action_server_impl.hpp` | An unreadable `default_nav_to_pose_bt_xml` makes bt_navigator fail `on_activate()`; Humble has no fallback for an empty value | 2026-11-04 |
| C4 | Nav2 docs source, commit 74f751f, https://github.com/ros-navigation/docs.nav2.org (`configuring_bt_navigator.md`) | Current (post-Humble) docs: an **empty** `default_nav_to_pose_bt_xml` loads the stock tree, so a placeholder must be non-empty to fail safely on later distros | 2026-11-04 |
| C5 | SLAM Toolbox `humble` branch, v2.6.10, commit dccc5d1, https://github.com/SteveMacenski/slam_toolbox/tree/humble (`config/mapper_params_online_async.yaml`, `solvers/ceres_solver.cpp`, `src/slam_toolbox_common.cpp`) | All 50 keys in `slam.yaml` are declared; `ceres_*` and `mode` live in the Ceres solver plugin. Stock keys we leave at defaults: `min_laser_range`, `min_pass_through`, `occupancy_threshold`, `restamp_tf` | 2026-11-04 |
| C6 | robot_localization `humble-devel`, commit 7ebaee2, https://github.com/cra-ros-pkg/robot_localization/tree/humble-devel (`src/ros_filter.cpp`, `doc/state_estimation_nodes.rst`) | All keys in `ekf.yaml` and `ekf_wheel_odom.yaml` exist, including the per-sensor suffixes `_config`, `_queue_size`, `_differential`, `_relative`, `_remove_gravitational_acceleration` | 2026-11-04 |
| C7 | rf2o_laser_odometry `ros2` branch, commit b38c68e, `src/CLaserOdometry2DNode.cpp` | Declares exactly the 7 keys in `scan_odometry.yaml`; `init_pose_from_topic: ''` skips the ground-truth subscription (source line 53). Launch node name `rf2o_laser_odometry` matches the YAML key. Confirms [N6] | 2026-11-04 |

## Related work (found via Consensus, 2026-11-02 - read before citing)
| Tag | Source | Key finding |
| --- | --- | --- |
| L1 | C. Case et al., "Autonomous sign reading for semantic mapping," Proc. IEEE ICRA, 2011 | Closest prior work: SLAM map annotated with room numbers read from wall signs; named locations recognised in 84% of cases |
| L2 | D. Balaban et al., "Automatic sign reading and localization for semantic mapping with an office robot," arXiv, 2022 | YOLOv5 sign detection + text recognition; placards localised from RGB-D point cloud; reports placement accuracy and text correctness |
| L3 | X. Song et al., "Semantic mapping techniques for indoor mobile robots: Review and prospect," Measurement and Control, 2024 | Recent review for the literature-review section |
| L4 | R. Alqobali et al., "A real-time semantic map production system for indoor robot navigation," Sensors, 2024 | LiDAR + YOLO in ROS; reports object localisation error - useful comparison for O4 |

## Tool notes
- Context7 does not index `robot_localization` (checked 2026-11-02); use docs.ros.org for ROS packages.

## To find (for literature review)
- Evaluation methods for 2D occupancy map accuracy against floor plans.
- Robot-built maps for indoor wayfinding / QR-anchored navigation.
