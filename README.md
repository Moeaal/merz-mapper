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
| `docs/MERZ_MAPPER_STATE.md` | Current phase, next tasks, blockers (read first) | all |
| `docs/decisions.md` | Engineering decisions: reason, alternatives, evidence, status | all |
| `docs/HARDWARE_REGISTER.md` | Confirmed specs, drivers, power, integration status | O1 |
| `docs/SOFTWARE_ARCHITECTURE.md` | Packages, nodes, topics, TF, data flow | O1-O6 |
| `docs/OPEN_ISSUES.md` | Problems, severity, proposed fixes | all |
| `docs/RESEARCH_INDEX.md` | Verified sources and key findings | O8, D4 |
| `docs/BUILD_GUIDE.md` | Step-by-step procedure for when the hardware arrives | all |
| `docs/EXPERIMENTS.md` | Procedure and pass rule for each objective | O1-O8 |
| `ros2_ws/` | ROS 2 workspace; start with `ros2_ws/README.md` | O1-O6 |
| `tools/` | `eval/` = objective evaluation scripts; `extract_frames.py`; `yolo_practice/` = supervisor practice script | O3, O8 |
| `data/` | Rosbags, maps, photos - NOT committed (see .gitignore) | - |
| `report/` | Poster (D2) and report (D4) drafts | D2, D4 |
| `web/` | FastAPI + demonstrator website, sample data | O7 |

## ROS 2 packages
**Status: IMPLEMENTED - not yet built or tested on hardware.**
- `merz_interfaces` - shared messages - O3, O4
- `merz_bringup` - launch files + config (sensors, teleop, EKF, SLAM Toolbox, Nav2) - O1, O2
- `merz_description` - URDF with sensor positions - O1
- `merz_exploration` - frontier exploration + access zones - O2, O5
- `merz_perception` - YOLO + PaddleOCR nodes - O3
- `merz_semantic_map` - landmark fusion + SQLite writer - O4, O6
- `merz_base` - rover base driver - O1

## Bring-up
Not yet run. Follow `docs/BUILD_GUIDE.md`. Unit tests on Windows: `python -m pytest` (see `docs/BUILD_PROGRESS.md`).
