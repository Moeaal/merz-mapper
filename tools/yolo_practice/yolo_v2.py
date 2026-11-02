"""Live object detection from the laptop camera using YOLO (Ultralytics).

Setup (once, in the PyCharm terminal):
    pip install ultralytics opencv-python numpy

The first run downloads the model weights (yolo11n.pt, ~6 MB), so run it once
with internet access before the session.

Keys in the video window:
    q or ESC  quit
    s         save the current annotated frame to the 'snapshots' folder

Detections are printed to the Run window and collected into a matrix.
On exit they are saved to detections.csv with columns:
    frame, class_id, confidence, x1, y1, x2, y2, cx, cy
(pixel coordinates, origin at the top-left of the image)
"""
import csv
import os
import time
from datetime import datetime

import cv2
import numpy as np
from ultralytics import YOLO

# ---- Settings -------------------------------------------------------------
CAMERA_INDEX = 0          # 0 = built-in laptop camera; try 1 or 2 for an external one
MODEL_NAME = "yolo11n.pt" # n = nano (fastest). Larger: yolo11s.pt, yolo11m.pt (more accurate, slower)
CONFIDENCE = 0.8          # ignore detections below this confidence (0-1)
IMAGE_SIZE = 640          # inference size in pixels; smaller = faster
FRAME_WIDTH = 1280        # requested camera resolution
FRAME_HEIGHT = 720
SNAPSHOT_DIR = "snapshots"
WINDOW = "YOLO detection (q to quit, s to save)"
PRINT_EVERY = 10          # print every Nth frame so the console isn't flooded (1 = every frame)
CSV_FILE = "detections.csv"

# ---- Camera and model -----------------------------------------------------
model = YOLO(MODEL_NAME)
print(f"Loaded {MODEL_NAME}: {len(model.names)} classes, e.g. {list(model.names.values())[:8]}")

# CAP_DSHOW opens the camera much faster on Windows and avoids a common warning
backend = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY
cap = cv2.VideoCapture(CAMERA_INDEX, backend)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
if not cap.isOpened():
    raise RuntimeError(f"Could not open camera {CAMERA_INDEX}. Is another app using it? "
                       "Try a different CAMERA_INDEX.")

last_time = time.time()
fps = 0.0
frame_num = 0
history = []   # one block of rows per frame, stacked into a single matrix at the end
try:
    while True:
        ok, frame = cap.read()
        if not ok:
            print("Lost the camera feed")
            break

        # Run YOLO on the frame. results[0] holds the detections for this image.
        results = model(frame, conf=CONFIDENCE, imgsz=IMAGE_SIZE, verbose=False)
        result = results[0]

        # Draw the boxes and labels on a copy of the frame
        annotated = result.plot()

        # ---- Detections as a matrix ----------------------------------------
        frame_num += 1
        boxes = result.boxes
        xyxy = boxes.xyxy.cpu().numpy()                    # (N, 4): x1, y1, x2, y2 in pixels
        conf = boxes.conf.cpu().numpy()                    # (N,)
        cls = boxes.cls.cpu().numpy().astype(int)          # (N,)
        labels = [model.names[c] for c in cls]             # class names, same order as the rows
        cx = (xyxy[:, 0] + xyxy[:, 2]) / 2                 # box centre x
        cy = (xyxy[:, 1] + xyxy[:, 3]) / 2                 # box centre y

        # Matrix for this frame, columns: class_id, confidence, x1, y1, x2, y2, cx, cy
        detections = np.column_stack([cls, conf, xyxy, cx, cy])

        # Add the frame number as column 0 and keep it for the whole run
        if len(detections):
            history.append(np.column_stack([np.full(len(detections), frame_num), detections]))

        # Print to the PyCharm Run window
        if frame_num % PRINT_EVERY == 0 and len(detections):
            print(f"--- frame {frame_num} ---")
            for name, row in zip(labels, detections):
                print(f"{name:12s} conf={row[1]:.2f}  centre=({row[6]:.0f}, {row[7]:.0f})  "
                      f"box=({row[2]:.0f}, {row[3]:.0f})-({row[4]:.0f}, {row[5]:.0f})")

        # Build a text summary, e.g. {'person': 2, 'cup': 1}
        counts = {}
        for name in labels:
            counts[name] = counts.get(name, 0) + 1

        # Smoothed frames-per-second display
        now = time.time()
        fps = 0.9 * fps + 0.1 * (1.0 / max(now - last_time, 1e-6))
        last_time = now
        summary = ", ".join(f"{n} x{c}" for n, c in counts.items()) or "nothing detected"
        cv2.putText(annotated, f"{fps:.1f} FPS | {summary}", (10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow(WINDOW, annotated)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):                               # q or ESC
            break
        if key == ord("s"):                                     # save a snapshot
            os.makedirs(SNAPSHOT_DIR, exist_ok=True)
            path = os.path.join(SNAPSHOT_DIR, datetime.now().strftime("yolo_%Y%m%d_%H%M%S.jpg"))
            cv2.imwrite(path, annotated)
            print(f"Saved {path}")
        if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:   # window closed with the X
            break
finally:
    cap.release()
    cv2.destroyAllWindows()

    all_detections = np.vstack(history) if history else np.empty((0, 9))
    # columns: frame, class_id, confidence, x1, y1, x2, y2, cx, cy
    print(f"Collected {len(all_detections)} detections over {frame_num} frames")
    # Write the CSV with the class name added after class_id
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["frame", "class_id", "class_name", "confidence",
                         "x1", "y1", "x2", "y2", "cx", "cy"])
        for row in all_detections:
            class_id = int(row[1])
            writer.writerow([int(row[0]), class_id, model.names[class_id],
                             f"{row[2]:.3f}", *[f"{v:.1f}" for v in row[3:]]])
    print(f"Saved {CSV_FILE}")
