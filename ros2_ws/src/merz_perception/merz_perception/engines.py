"""Object detection engines behind one interface, chosen by a parameter. No ROS imports.

"ultralytics" runs .pt weights (laptop now, Jetson while developing). "tensorrt" runs a TensorRT .engine on the
Jetson, built with the steps in tools/export_tensorrt.md. The nodes never know which one is in use.
Heavy libraries are imported only when an engine is created, so importing this module costs nothing.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol

import numpy as np


@dataclass(frozen=True)
class Detection:
    """One detected object. Pixel coordinates, top-left origin."""

    label: str
    confidence: float
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class DetectorEngine(Protocol):
    def detect(self, image_bgr: np.ndarray) -> list[Detection]:
        """Return the detections in one BGR image."""
        ...


class UltralyticsEngine:
    """Run any model format that Ultralytics can load."""

    def __init__(self, weights: str, confidence: float, image_size: int) -> None:
        from ultralytics import YOLO

        # task is given explicitly as it cannot be inferred from an exported .engine file.
        self._model = YOLO(weights, task='detect')
        self._confidence = confidence
        self._image_size = image_size

    def detect(self, image_bgr: np.ndarray) -> list[Detection]:
        results = self._model.predict(image_bgr, conf=self._confidence, imgsz=self._image_size, verbose=False)
        detections = []
        for result in results:
            names = result.names
            for box in result.boxes:
                x_min, y_min, x_max, y_max = (float(v) for v in box.xyxy[0].tolist())
                detections.append(Detection(names[int(box.cls[0])], float(box.conf[0]), x_min, y_min, x_max, y_max))
        return detections


# The engine names offered as a parameter, and the weight file types each accepts.
_ACCEPTED_SUFFIXES = {
    'ultralytics': {'.pt', '.onnx'},
    'tensorrt': {'.engine'},
}


def make_engine(name: str, weights: str, confidence: float = 0.25, image_size: int = 640) -> DetectorEngine:
    """Create an engine, failing early with a clear message if the settings cannot work."""
    if name not in _ACCEPTED_SUFFIXES:
        raise ValueError(f"Unknown engine '{name}'. Choose one of: {sorted(_ACCEPTED_SUFFIXES)}")
    path = Path(weights).expanduser()
    if path.suffix not in _ACCEPTED_SUFFIXES[name]:
        raise ValueError(f"Engine '{name}' needs a {sorted(_ACCEPTED_SUFFIXES[name])} file, got '{path.name}'")
    if not path.is_file():
        raise FileNotFoundError(f'Model file not found: {path}')
    # Ultralytics loads a TensorRT engine through the same class, which keeps NMS and box decoding in one tested
    # place rather than re-writing them here. The separate name is what lets the choice be checked above.
    return UltralyticsEngine(str(path), confidence, image_size)


def keep_labels(detections: Iterable[Detection], allowed: Iterable[str]) -> list[Detection]:
    """Keep only the allowed labels. An empty allowed list keeps everything."""
    allowed_set = set(allowed)
    if not allowed_set:
        return list(detections)
    return [d for d in detections if d.label in allowed_set]


def clip_box(detection: Detection, width: int, height: int, margin: float = 0.0) -> tuple[int, int, int, int]:
    """Return integer (x0, y0, x1, y1) inside the image, grown by margin (a fraction of the box size)."""
    grow_x = (detection.x_max - detection.x_min) * margin
    grow_y = (detection.y_max - detection.y_min) * margin
    x0 = max(0, int(detection.x_min - grow_x))
    y0 = max(0, int(detection.y_min - grow_y))
    x1 = min(width, int(round(detection.x_max + grow_x)))
    y1 = min(height, int(round(detection.y_max + grow_y)))
    return x0, y0, x1, y1


class RateLimiter:
    """Allow an action at most once per period, as detection runs at a few Hz rather than camera rate."""

    def __init__(self, rate_hz: float) -> None:
        self._period = 1.0 / rate_hz if rate_hz > 0 else 0.0
        self._next_time: float | None = None

    def ready(self, now_s: float) -> bool:
        if self._next_time is not None and now_s < self._next_time:
            return False
        self._next_time = now_s + self._period
        return True
