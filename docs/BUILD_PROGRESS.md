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
- [ ] 8. Nav2 + full autonomy launch
- [ ] 9. Evaluation tools
- [ ] 10. Website + QR posters
- [ ] 11. Rover base driver
- [ ] 12. Build guide
- [ ] 13. Final check

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
Filled in at phase 13.
