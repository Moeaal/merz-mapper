# Build progress

Tracks `docs/BUILD_ALL_PROMPT.md`. To resume: `Continue docs/BUILD_ALL_PROMPT.md from docs/BUILD_PROGRESS.md.`

**Branch:** `build/all-code` (never merged by Claude; the student reviews the pull request).
**Status words:** code here is IMPLEMENTED at most. Nothing has been built with colcon or run on hardware.

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
| `web/test_web.py` | 38 (was 28; website redesign, branch `build/website-design`) |
| `tools/test_static_refs.py` (cross-file consistency) | 102 |

**The 4 skipped files need ROS 2. They are written but have never been run: a skip is not a pass. Run them on the Jetson or Pi:**
`merz_base/test/test_ros_base_node.py`, `merz_bringup/test/test_ros_launch_files.py`,
`merz_bringup/test/test_ros_scan_odom_relay.py`, `merz_semantic_map/test/test_ros_landmark_node.py`.

## Final checks
- **Launch references:** `tools/test_static_refs.py` reads each of the 16 launch files and checks its config files, included launch files and
  executables exist, and YAML sections match node names. Also checks YAML keys, message fields and declared dependencies.
- **Those checks were tested:** 11 deliberate faults were added one at a time to a scratch copy, and all 11 were caught.
- **`launch_validator.py`** (ros2-engineering-skills), all launch files: 0 errors, 19 warnings. All warnings are arguments without a
  description, left as they are.
- **Website:** run locally with the sample data, API checked live, page checked at 360 px wide in headless Chrome. No real phone yet.
- **Not checked, as it needs ROS:** `colcon build`; every node and launch file actually running; third-party parameter and topic names
  (the Nav2 plugin list and DWB parameters were written from memory of Humble's defaults, with only a summary of the file available to
  check against); anything on hardware.
