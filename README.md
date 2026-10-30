# Merz Court Mapping Robot (EEE3094)

Autonomous rover that maps a floor of Merz Court, labels rooms and landmarks,
and records which rooms are reachable from each entrance. A demonstrator
website uses the resulting building database.

Student: Mohammed Abdulaal | Supervisor: Dr Nick Wright

## Folders
| Folder | What goes in it | Objectives |
| --- | --- | --- |
| `docs/logbook/` | One entry per day worked (copy `TEMPLATE.md`) | all |
| `docs/meetings/` | Supervisor meeting minutes (copy `TEMPLATE.md`) | all |
| `docs/decisions.md` | One line per decision + reason | all |
| `ros2_ws/src/` | ROS 2 packages, created with `ros2 pkg create` when needed | O1-O6 |
| `tools/` | Calibration and evaluation scripts | O8 |
| `data/` | Rosbags, maps, photos - NOT committed (see .gitignore) | - |
| `report/` | Poster (D2) and report (D4) drafts | D2, D4 |
| `web/` | FastAPI + demonstrator website (from April) | O7 |

## Planned ROS 2 packages
- `merz_bringup` - launch files + config (EKF, SLAM Toolbox, Nav2) - O1
- `merz_description` - URDF with sensor positions - O1
- `merz_exploration` - frontier exploration + access zones - O2, O5
- `merz_perception` - YOLO + PaddleOCR nodes - O3
- `merz_semantic_map` - landmark fusion + SQLite writer - O4, O6

## Bring-up (fill in once it works)
```bash
# e.g. ros2 launch merz_bringup rover.launch.py
```
