# Engineering decisions log

One row per decision. Status: **CONFIRMED** (agreed with supervisor), **DECIDED**
(student decision, not yet agreed), **PROPOSED**, **SUPERSEDED**.
Never delete a row; mark it SUPERSEDED and add a new one.

| # | Date | Decision | Reason | Alternatives considered | Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-10 | Jetson Orin Nano, RPLIDAR S2, RealSense D455, C920 webcam | Fewest parts; all USB with ROS 2 drivers | Separate IMU; ultrasonic; stereo-only | Parts list; proposal Table 2 | DECIDED (supervisor sign-off not recorded) |
| 2 | 2026-10 | Use D455 built-in IMU; no separate IMU | D455 has a 6-axis Bosch BMI055 IMU | Separate 9-axis IMU | RESEARCH_INDEX [H2] | DECIDED |
| 3 | 2026-10 | No ultrasonic sensors, touchscreen, speaker | Not needed for objectives; less integration | - | - | DECIDED |
| 4 | 2026-10 | Python 3.12 / the Jetson's system Python, not 3.14 | 3.14 lacked pip/library support | Python 3.14 | Logbook 2026-10-30 | DECIDED |
| 5 | 2026-10 | Robot is the main contribution (~75%); website is a demonstrator; cut website first if late | Module brief requires autonomous rover + sensor fusion | - | Proposal s.6 | DECIDED |
| 6 | 2026-11 | JetPack / ROS 2 distro: **open** - recommended JetPack 6.2 + Humble | Depends on rover's existing set-up; see OPEN_ISSUES #2 | JetPack 7.2 + Jazzy | RESEARCH_INDEX [J1-J3] | PROPOSED |
| 7 | 2026-11 | Frontier exploration package: **open** - start with m-explore-ros2 (explore_lite) | Most used, works with SLAM Toolbox + Nav2 | frontier_exploration_ros2; roadmap_explorer; write own | RESEARCH_INDEX [N2-N4] | PROPOSED |
