# YOLO practice script (from supervisor)

`yolo_v2.py` - live object detection from a webcam with Ultralytics YOLO (`yolo11n.pt`,
pretrained on COCO). Given by Dr Wright, week of 26 Oct 2026, for practice. **Not part of
the robot software** - status: practice only (towards O3).

## Run (laptop)
```
pip install ultralytics opencv-python numpy   # use Python 3.12, not 3.14 (decisions #4)
python yolo_v2.py
```
First run downloads `yolo11n.pt` (~6 MB; weights are gitignored). Keys: `q`/ESC quit,
`s` save snapshot. Output `detections.csv` (frame, class, confidence, box, centre) and
`snapshots/` are gitignored.

## Notes for O3
- COCO classes do not include door, lift, stairs, exit sign or room sign - a custom
  dataset/fine-tune is needed (see `merz-perception-jetson` skill).
- `CONFIDENCE = 0.8` is high; for recall tests try 0.25-0.5.
- `CAMERA_INDEX = 1` usually selects an external USB webcam (e.g. the C920).
