# Build progress

Tracks `docs/BUILD_ALL_PROMPT.md`. To resume: `Continue docs/BUILD_ALL_PROMPT.md from docs/BUILD_PROGRESS.md.`

**Branch:** `build/all-code` (never merged by Claude; the student reviews the pull request).
**Status words:** code here is IMPLEMENTED at most. Nothing has run on hardware. A cloud `colcon build` + `colcon test` on
ROS 2 Humble passed on 2026-11-04 (see "ROS 2 Humble check" below); that is software-only evidence, not a Jetson or Pi result.

## Phases (ticked when the commit is pushed)
- [x] 1. Workspace + interfaces
- [x] 2. Robot description
- [x] 3. Sensor bringup + teleop
- [x] 4. Odometry, EKF, SLAM
- [x] 5. Perception
- [x] 6. Semantic map + SQLite
- [x] 7. Exploration + access zones
- [x] 8. Nav2 + full autonomy launch
- [x] 9. Evaluation tools
- [x] 10. Website + QR posters
- [x] 11. Rover base driver
- [x] 12. Build guide
- [x] 13. Final check

## Environment notes
- Python 3.12 (decisions #4) is **not installed** on the laptop; only 3.14.7 is.
  Install it with `winget install Python.Python.3.12`. Windows unit tests have been run on 3.14.7,
  so re-run them on 3.12 once it is installed. The Jetson target is Python 3.10 (Ubuntu 22.04).
- `gh` is not installed, so the pull request has to be opened from the GitHub link.

## How to run the Windows tests
```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
```

## Test summary
Run on 2026-11-03, on Windows, in a clean venv installed from `requirements-dev.txt`, Python 3.14.7 (`python -m pytest`):
```
337 passed, 4 skipped
```
| Tests | Count |
| --- | --- |
| `merz_description/test/test_urdf.py` | 6 |
| `merz_bringup/test/` (config, localisation, navigation) | 32 |
| `merz_perception/test/test_perception_core.py` | 40 |
| `merz_semantic_map/test/test_semantic_core.py` | 36 |
| `merz_exploration/test/test_exploration_core.py` | 33 |
| `merz_base/test/test_base_core.py` | 31 |
| `tools/test_extract_frames.py` | 7 |
| `tools/eval/test_eval.py` | 22 |
| `web/test_web.py` | 28 |
| `tools/test_static_refs.py` (cross-file consistency) | 102 |

**The 4 skipped files need ROS 2. On Windows they skip, and a skip is not a pass. They were first run, and passed, in the ROS 2 Humble
cloud check on 2026-11-04 (below). They still need running on the Jetson or Pi:**
`merz_base/test/test_ros_base_node.py`, `merz_bringup/test/test_ros_launch_files.py`,
`merz_bringup/test/test_ros_scan_odom_relay.py`, `merz_semantic_map/test/test_ros_landmark_node.py`.

## Final checks
- **Launch references:** `tools/test_static_refs.py` reads each of the 16 launch files and checks its config files, included launch files and
  executables exist, and YAML sections match node names. Also checks YAML keys, message fields and declared dependencies.
- **Those checks were tested:** 11 deliberate faults were added one at a time to a scratch copy, and all 11 were caught.
- **`launch_validator.py`** (ros2-engineering-skills), all launch files: 0 errors, 19 warnings. All warnings are arguments without a
  description, left as they are.
- **Website:** run locally with the sample data, API checked live, page checked at 360 px wide in headless Chrome. No real phone yet.
- **Not checked, as it needs ROS:** ~~`colcon build`~~ (done in the cloud on 2026-11-04, see below); every node and launch file actually running; third-party parameter and topic names
  (the Nav2 plugin list and DWB parameters were written from memory of Humble's defaults, with only a summary of the file available to
  check against); anything on hardware.

## ROS 2 Humble check (cloud, 2026-11-04)
Branch `build/ros-check`, from `main` at `f81bf11`. Run by Claude Code in a cloud container. **Software-only (no hardware, no live
sensors, no Nav2 or SLAM run).**

### How ROS 2 was installed
- The container is Ubuntu 24.04, and its network policy blocks `packages.ros.org` (HTTP 403), so the official apt packages could not be
  installed (also tried: the `ros:humble-ros-base` Docker image, whose apt sources are the same blocked host).
- ROS 2 Humble was installed from **RoboStack** (`robostack-humble` conda channel, conda-forge builds of the Humble release) with
  micromamba. This is ROS 2 Humble, but **not the same binaries as the Jetson** (apt, Ubuntu 22.04, Python 3.10).
- Versions: `ros-humble-ros-base` 0.10.0, `rclpy` 3.3.16, `slam_toolbox` 2.6.10, `nav2_bringup` 1.1.18, `robot_localization` 3.5.3,
  Python 3.11.15, NumPy 1.26.4, colcon-core 0.19.0.
- Tools pinned to Ubuntu 22.04's generation, because conda's newest versions break Humble's build tooling (environment only, no repo
  change): CMake 3.26.4 (CMake 4.2 failed), GCC 12.4 (GCC 15 failed in Humble message headers), empy 3.3.4 (empy 4 breaks
  `rosidl_adapter`), setuptools 59.6.0 (79+ breaks `--symlink-install`, and drops `tests_require`, so colcon silently ran 0 tests),
  pytest 7.4.4 (pytest 8 rejects Humble's `launch_testing` plugin). CMake was given `-DPython_EXECUTABLE=<env>/bin/python`, as
  FindPython did not find the conda interpreter on its own.
- `rosdep` could not be used (it needs apt); the dependencies in each `package.xml` were installed by hand from RoboStack, plus
  `image_geometry` for `multirobot_map_merge` (in the m-explore-ros2 repo, not used by Merz).

### Commands
```bash
vcs import src < merz.repos
colcon build --symlink-install --cmake-args -DPython_EXECUTABLE=$CONDA_PREFIX/bin/python -DPython3_EXECUTABLE=$CONDA_PREFIX/bin/python
source install/setup.bash && export ROS_LOCALHOST_ONLY=1
colcon test --packages-select merz_interfaces merz_description merz_base merz_bringup merz_perception merz_semantic_map merz_exploration
colcon test-result --all
python -m pytest ros2_ws/src tools web        # from the repo root, with the overlay sourced
```

### Third-party commits built
| Repo | Commit |
| --- | --- |
| `sllidar_ros2` (`main`) | `34300099fadfc772965962dec837bf436706188f` |
| `rf2o_laser_odometry` (`ros2`) | `b38c68e46387b98845ecbfeb6660292f967a00d3` |
| `m-explore-ros2` (now pinned) | `926033fdef55af37ec0455660c0e4d00aa47e82f` |

### Results
- **`colcon build`: 11 packages finished, 0 failed** (7 Merz packages, `rf2o_laser_odometry`, `sllidar_ros2`, `explore_lite`,
  `multirobot_map_merge`; `explore_lite_msgs` is built as well). Merz packages give only warnings: `tests_require` is unknown to newer
  setuptools (the standard Humble `setup.py` template; harmless on 22.04), and an unused CMake variable in `merz_description`.
  Third-party packages give compiler warnings only. rf2o builds on Humble, which decisions #14 asked to be proved (on the Pi it is still
  to be repeated).
- **`colcon test`: 192 tests, 0 errors, 0 failures, 0 skipped.**

| Package | Tests |
| --- | --- |
| `merz_base` | 32 |
| `merz_bringup` | 50 |
| `merz_exploration` | 33 |
| `merz_perception` | 40 |
| `merz_semantic_map` | 37 |

- **The 4 ROS-only test files all ran (not skipped) and passed, 20 test cases:**
  - `merz_base/test/test_ros_base_node.py`: 1 (commands reach the backend; the timeout stops it).
  - `merz_bringup/test/test_ros_launch_files.py`: 16, one per launch file; every launch description loads. This shows each file imports
    and its packages and files are found. It does not start the nodes.
  - `merz_bringup/test/test_ros_scan_odom_relay.py`: 2 (covariance added; implausible speed dropped).
  - `merz_semantic_map/test/test_ros_landmark_node.py`: 1 (landmark position through the real node).
- **Full repo suite with the overlay sourced** (`ros2_ws/src tools web`): **357 passed, 0 skipped** (the 337 Windows tests plus the 20
  ROS cases).
- `merz_description/test/test_urdf.py` (6 tests) is not registered in `merz_description/CMakeLists.txt`, so `colcon test` does not
  run it; it passed in the repo-root pytest run. Registering it with `ament_cmake_pytest` is a possible later change (not made).
- With pytest 7 the repo-root `pytest.ini` `testpaths` collected nothing, so paths were given explicitly. `requirements-dev.txt` asks
  for pytest 8 for the Windows workflow, where this does not arise.

### Fix made
- **`ros2_ws/merz.repos`: `m-explore-ros2` pinned to `926033f` instead of `main`.** From `96d1888` (2026-01-13) `main` includes
  `tf2_ros/buffer.hpp`, a header Humble does not have, so `explore_lite` failed to compile
  (`fatal error: tf2_ros/buffer.hpp: No such file or directory`). `926033f` (2025-07-24) is the last commit before that change. It has every
  parameter in `exploration.yaml` and the `explore/resume` and `explore/frontiers` topics that `mission_node` uses. Built and tested again
  from a fresh `vcs import` of the edited file: same results as above.
- What the pin gives up (upstream commits after `926033f`): the `explore/status` topic (not used by Merz), a fix that puts the frontier
  sphere markers at the centroid (visual only; `mission_node` only counts ADD markers), and upstream #51 "Do not blacklist for preempted
  goal", **which changes exploration behaviour**. Recorded as decisions #19 (PROPOSED) for the student to accept, or to replace with a
  Humble fork that back-ports #51.
- No Merz source, configuration, parameter, launch file or test was changed.
- Re-run after merging `main` (`ec7f5b0`, the config check that added `default_nav_to_pose_bt_xml` to `nav2.yaml` and one test):
  `colcon build` 11 packages finished; `colcon test` **193 tests, 0 errors, 0 failures, 0 skipped** (`merz_bringup` now 51);
  repo-root pytest **358 passed, 0 skipped**.

### Still not checked
- Anything on the Jetson or Pi (apt binaries, Python 3.10, ARM64), or with `rosdep`.
- Nodes running together, launch files actually launched, Nav2/SLAM/EKF behaviour, third-party parameter names at run time.
- Anything on hardware.
