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

## To find (for literature review)
- Semantic mapping with door-sign OCR on mobile robots (recent IEEE/RA-L papers).
- Evaluation methods for 2D occupancy map accuracy against floor plans.
- Robot-built maps for indoor wayfinding / QR-anchored navigation.
