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
| L1 | C. Case et al., "Autonomous sign reading for semantic mapping," Proc. IEEE ICRA, 2011 | Closest prior work: SLAM map annotated with room numbers read from wall signs; named locations recognised in 84% of cases. Verified 2026-11-05: pp. 3297-3303, DOI 10.1109/ICRA.2011.5980523 = [LB-3.6] |
| L2 | D. Balaban et al., "Automatic sign reading and localization for semantic mapping with an office robot," arXiv, 2022 | YOLOv5 sign detection + text recognition; placards localised from RGB-D point cloud; reports placement accuracy and text correctness. **Correction 2026-11-05:** only two authors (D. Balaban and J. Hart), so not "et al."; arXiv:2209.11432; mapping uses a modified ORB-SLAM on Azure Kinect RGB-D video = [LB-3.7] |
| L3 | X. Song et al., "Semantic mapping techniques for indoor mobile robots: Review and prospect," Measurement and Control, 2024 | Recent review for the literature-review section. **Correction 2026-11-05:** online 2024 but in vol. 58 (2025); DOI 10.1177/00202940241259903; pages and third author's name order unverified = [LB-3.2] |
| L4 | R. Alqobali et al., "A real-time semantic map production system for indoor robot navigation," Sensors, 2024 | LiDAR + YOLO in ROS; reports object localisation error - useful comparison for O4. Verified: vol. 24, no. 20, Art. 6691, DOI 10.3390/s24206691; results are from **simulation** = [LB-3.8] |

## Literature base for the report (branch `lit-review`, 2026-11-05)
Full IEEE references, DOIs, summaries, relevance and objectives are in `docs/research/literature-base.md`; the
proposed review structure and research gap are in `docs/research/lit-review-outline.md`. Checked through search
results quoting publisher pages, dblp and repositories (direct DOI/arXiv fetches were blocked); fields marked
UNVERIFIED there still need checking on the DOI page. Key: tag, first author + year, DOI, objectives.
| Topic | Tags (first author year, DOI) | Objectives |
| --- | --- | --- |
| 1 2D LIDAR SLAM | LB-1.1 Grisetti 2007 10.1109/TRO.2006.889486; 1.2 Grisetti 2010 10.1109/MITS.2010.939925; 1.3 Konolige 2010 10.1109/IROS.2010.5649043; 1.4 Hess 2016 10.1109/ICRA.2016.7487258; 1.5 Macenski 2021 10.21105/joss.02783; 1.6 Santos 2013 10.1109/SSRR.2013.6719348; 1.7 Yagfarov 2018 10.1109/ICARCV.2018.8581131; 1.8 Cadena 2016 10.1109/TRO.2016.2624754; 1.9 Kohlbrecher 2011 (DOI unverified) | O1, O2 |
| 2 Exploration | 2.1 Yamauchi 1997 10.1109/CIRA.1997.613851; 2.2 Holz 2010 (no DOI); 2.3 Juliá 2012 10.1007/s10514-012-9298-8; 2.4 Bircher 2016 10.1109/ICRA.2016.7487281; 2.5 Umari 2017 10.1109/IROS.2017.8202319; 2.6 Oršulić 2019 10.1109/LRA.2019.2928203; 2.7 Lluvia 2021 10.3390/s21072445; 2.8 Liu 2025 10.1038/s41598-025-97231-9; 2.9 Macenski 2020 (Nav2) 10.1109/IROS45743.2020.9341207 | O2, O5 |
| 3 Semantic mapping | 3.1 Kostavelis 2015 10.1016/j.robot.2014.12.006; 3.2 Song 2025 (=L3); 3.3 Martínez Mozos 2005 10.1109/ROBOT.2005.1570363; 3.4 Bormann 2016 10.1109/ICRA.2016.7487234; 3.5 Sünderhauf 2017 10.1109/IROS.2017.8206392; 3.6 Case 2011 (=L1); 3.7 Balaban 2022 (=L2); 3.8 Alqobali 2024 (=L4) | O3, O4, O5 |
| 4 Scene text / OCR | 4.1 Long 2021 10.1007/s11263-020-01369-0; 4.2 Shi 2017 10.1109/TPAMI.2016.2646371; 4.3 Liao 2020 10.1609/aaai.v34i07.6812; 4.4 Du 2020 arXiv:2009.09941; 4.5 Cui 2025 arXiv:2507.05595; 4.6 Baek 2019 10.1109/ICCV.2019.00481; 4.7 Smith 2007 10.1109/ICDAR.2007.56; 4.8 Fajrianti 2024 10.3390/network4030014 | O3 |
| 5 Embedded detection | 5.1 Redmon 2016 10.1109/CVPR.2016.91; 5.2 Terven 2023 10.3390/make5040083; 5.3 Wang 2024 (YOLOv10, NeurIPS) arXiv:2405.14458; 5.4 Ultralytics YOLO11 software; 5.5 Lema 2024 10.1016/j.vlsi.2023.102127; 5.6 Shakya 2026 10.1109/ACCESS.2025.3648968; 5.7 Alqahtani 2024 arXiv:2409.16808 | O3, O4 |
| 6 Fusion / scan odometry | 6.1 Thrun 2005 (book); 6.2 Moore 2016 10.1007/978-3-319-08338-4_25; 6.3 Jaimez 2016 (RF2O) 10.1109/ICRA.2016.7487647; 6.4 Censi 2008 10.1109/ROBOT.2008.4543181; 6.5 Olson 2009 10.1109/ROBOT.2009.5152375; 6.6 Zhang 2016 10.1109/ICRA.2016.7487211; 6.7 Li 2021 10.1109/JSEN.2019.2910826; 6.8 Kudriashov 2026 (DOI unverified); 6.9 Macenski 2023 10.1016/j.robot.2023.104493 | O1, O8 |
| 7 Landmark localisation | 7.1 Martins 2020 10.1007/s10846-019-01136-5; 7.2 Rollo 2023 10.1109/ECMR59166.2023.10256373; 7.3 Nicholson 2019 10.1109/LRA.2018.2866205; 7.4 Keselman 2017 10.1109/CVPRW.2017.167; 7.5 Zhang 2000 10.1109/34.888718 | O4, O8 |
| 8 Visitor wayfinding | 8.1 Fallah 2013 10.1093/iwc/iws010; 8.2 Kunhoth 2020 10.1186/s13673-020-00222-0; 8.3 Zafari 2019 10.1109/COMST.2019.2911558; 8.4 Mulloni 2009 10.1109/MPRV.2009.30; 8.5 Beeharee 2006 10.1145/1152215.1152233; 8.6 May 2003 10.1007/s00779-003-0248-5; 8.7 Garrido-Jurado 2014 10.1016/j.patcog.2014.01.005; 8.8 Tünger 2022 10.4305/METU.JFA.2022.2.4; 8.9 Fajrianti 2023 10.3390/info14070359 | O6, O7 |
| 9 Evaluation | 9.1 Kümmerle 2009 10.1007/s10514-009-9155-6; 9.2 Sturm 2012 10.1109/IROS.2012.6385773; 9.3 Zhang 2018 10.1109/IROS.2018.8593941; 9.4 Filatov 2017 10.23919/FRUCT.2017.8250173; 9.5 Schwertfeger 2016 10.1007/s10514-015-9493-5; 9.6 Amigoni 2009 10.1007/s10514-009-9137-8; 9.7 JCGM 100:2008 10.59161/JCGM100-2008E | O2, O4, O8 |

## Tool notes
- Context7 does not index `robot_localization` (checked 2026-11-02); use docs.ros.org for ROS packages.
- 2026-11-05 cloud session: doi.org, arXiv, Crossref, OpenAlex and JOSS were blocked for direct fetch. WebSearch and
  Consensus still worked; dblp and repository records in search results gave DOIs and pages.

## To find (for literature review)
- ~~Evaluation methods for 2D occupancy map accuracy against floor plans.~~ Covered: LB-1.7, LB-9.1, LB-9.4, LB-9.5.
- Robot-built maps for indoor wayfinding / QR-anchored navigation: QR wayfinding covered (LB-8.4, LB-8.8, LB-8.9);
  **no source found where a robot-built map feeds visitor directions** - one more targeted search before claiming
  the gap in the report.
- A peer-reviewed real-robot SLAM Toolbox vs Cartographer comparison (only preprints found so far).
- Fill the UNVERIFIED fields in `docs/research/literature-base.md` from the DOI pages.
- Proposal refs [1]-[10] are not in the repo; add them here so they can be checked.
