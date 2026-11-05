"""Detection -> crop -> OCR -> room number -> JSON-ready dict. PROPOSED; no ROS.

The detector and OCR engine are injected, so the logic is tested with fakes (tests/test_pipeline.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .detector import Detector, UltralyticsDetector, WholeImage, pad_box
from .ocr import OcrEngine, prepare_crop, sharpness
from .room_parser import OcrLine, RoomParser, row_groups

CONFIG_PATH = Path(__file__).resolve().parents[1] / 'config' / 'sign_formats.yaml'


@dataclass
class Settings:
    room_patterns: list[str]
    prefix_letters: int = 1
    sign_label: str = 'door_sign'
    crop_margin: float = 0.10
    min_crop_height: int = 96
    min_sharpness: float = 0.0
    detector: dict[str, Any] = field(default_factory=lambda: {'mode': 'none'})
    keep_raw_text: bool = True


def load_settings(path: str | Path = CONFIG_PATH) -> Settings:
    import yaml

    data = yaml.safe_load(Path(path).read_text(encoding='utf-8'))
    return Settings(**data)


def make_detector(settings: Settings) -> Detector:
    cfg = settings.detector
    mode = cfg.get('mode', 'none')
    if mode == 'none':
        return WholeImage(settings.sign_label)
    if mode == 'yoloe':
        prompts = cfg.get('prompts') or {'door sign': settings.sign_label}
        return UltralyticsDetector(cfg['weights'], cfg.get('confidence', 0.25), cfg.get('image_size', 640),
                                   prompts=list(prompts), prompt_labels=list(prompts.values()))
    if mode == 'yolo':
        return UltralyticsDetector(cfg['weights'], cfg.get('confidence', 0.25), cfg.get('image_size', 640))
    raise ValueError(f"Unknown detector mode '{mode}': use none, yoloe or yolo")


class SignPipeline:
    def __init__(self, settings: Settings, detector: Detector, ocr: OcrEngine) -> None:
        self.settings = settings
        self.detector = detector
        self.ocr = ocr
        self.parser = RoomParser(settings.room_patterns, settings.prefix_letters)

    def read_sign(self, crop: np.ndarray) -> list[OcrLine]:
        """OCR a sign crop, then re-read any row the text detector split into pieces (see row_groups)."""
        image = prepare_crop(crop, self.settings.min_crop_height)
        lines = self.ocr.read(image)
        recognise = getattr(self.ocr, 'recognise', None)
        if recognise is None:
            return lines
        h, w = image.shape[:2]
        for x1, y1, x2, y2 in row_groups(lines):
            pad = max(2, (y2 - y1) // 10)
            merged = recognise(image[max(0, y1 - pad):min(h, y2 + pad), max(0, x1 - pad):min(w, x2 + pad)])
            if merged is not None:
                lines.append(OcrLine(merged.text, merged.confidence, (x1, y1, x2, y2)))
        return lines

    def process(self, image_bgr: np.ndarray, image_name: str = '') -> dict[str, Any]:
        s = self.settings
        h, w = image_bgr.shape[:2]
        detections_out = []
        for det in self.detector.detect(image_bgr):
            record: dict[str, Any] = {'label': det.label, 'confidence': round(det.confidence, 4),
                                      'box': list(det.box)}
            if det.label == s.sign_label:
                x1, y1, x2, y2 = pad_box(det.box, w, h, s.crop_margin)
                crop = image_bgr[y1:y2, x1:x2]
                sharp = sharpness(crop) if crop.size else 0.0
                record.update({'crop_box': [x1, y1, x2, y2], 'sharpness': round(sharp, 1),
                               'sharp_enough': sharp >= s.min_sharpness})
                lines = self.read_sign(crop) if crop.size and record['sharp_enough'] else []
                found = self.parser.candidates(lines)
                if s.keep_raw_text:
                    record['ocr_lines'] = [{'text': l.text, 'confidence': round(l.confidence, 4)} for l in lines]
                record['room_candidates'] = [{'room': c.room, 'confidence': round(c.confidence, 4),
                                              'repaired': c.repaired} for c in found]
                record['room_number'] = found[0].room if found else None
            detections_out.append(record)
        signs = [d for d in detections_out if d.get('room_number')]
        best = max(signs, key=lambda d: d['room_candidates'][0]['confidence'], default=None)
        return {'image': image_name, 'width': w, 'height': h, 'detections': detections_out,
                'room_number': best['room_number'] if best else None}
