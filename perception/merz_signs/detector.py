"""Sign/landmark detectors. PROPOSED.

Three modes, so the pipeline can run before a Merz Court model exists:
- `none`:  the whole image is treated as one sign (for photos already cropped to a sign).
- `yoloe`: Ultralytics YOLOE with text prompts (zero-shot, e.g. "door sign"). A stopgap only; accuracy on Merz signs
           is UNKNOWN and must be measured.
- `yolo`:  a fine-tuned Ultralytics model (`.pt`, or `.engine` on the Jetson) with the classes in config.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

import numpy as np


@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    box: tuple[int, int, int, int]   # x1, y1, x2, y2 in pixels


class Detector(Protocol):
    def detect(self, image_bgr: np.ndarray) -> list[Detection]:
        ...


def pad_box(box: Sequence[float], width: int, height: int, margin: float = 0.1) -> tuple[int, int, int, int]:
    """Grow a box by `margin` of its size on each side (signs are often cropped too tight) and clip it to the image."""
    x1, y1, x2, y2 = box
    dx, dy = (x2 - x1) * margin, (y2 - y1) * margin
    return (max(0, int(x1 - dx)), max(0, int(y1 - dy)),
            min(width, int(round(x2 + dx))), min(height, int(round(y2 + dy))))


class WholeImage:
    def __init__(self, label: str = 'door_sign') -> None:
        self.label = label

    def detect(self, image_bgr: np.ndarray) -> list[Detection]:
        h, w = image_bgr.shape[:2]
        return [Detection(self.label, 1.0, (0, 0, w, h))]


class UltralyticsDetector:
    """Wraps YOLO / YOLOE. `labels` maps prompt or class names to the pipeline's class names."""

    def __init__(self, weights: str, confidence: float = 0.25, image_size: int = 640,
                 prompts: Sequence[str] | None = None, prompt_labels: Sequence[str] | None = None) -> None:
        if prompts:
            from ultralytics import YOLOE

            self.model = YOLOE(weights)
            self.model.set_classes(list(prompts))
            self.rename = dict(zip(prompts, prompt_labels or prompts))
        else:
            from ultralytics import YOLO

            self.model = YOLO(weights)
            self.rename = {}
        self.confidence = confidence
        self.image_size = image_size

    def detect(self, image_bgr: np.ndarray) -> list[Detection]:
        result = self.model.predict(image_bgr, conf=self.confidence, imgsz=self.image_size, verbose=False)[0]
        names = result.names
        out = []
        for xyxy, conf, cls in zip(result.boxes.xyxy.cpu().numpy(), result.boxes.conf.cpu().numpy(),
                                   result.boxes.cls.cpu().numpy().astype(int)):
            name = names[int(cls)]
            out.append(Detection(self.rename.get(name, name), float(conf), tuple(int(v) for v in xyxy)))
        return out
