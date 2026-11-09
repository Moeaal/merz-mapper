"""OCR engines behind one interface: PaddleOCR, with RapidOCR (ONNX Runtime) as the fallback. No ROS imports.

PaddleOCR may be hard to install on the Jetson (aarch64 with GPU), so the fallback exists from the start. The result
formats differ between library versions, so parsing is kept in small functions that can be tested without the libraries.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence

import numpy as np


Box = tuple[int, int, int, int]   # x1, y1, x2, y2 in pixels of the image given to OCR


@dataclass(frozen=True)
class OcrResult:
    text: str
    confidence: float
    box: Box | None = field(default=None, compare=False)


class OcrEngine(Protocol):
    def read(self, image_bgr: np.ndarray) -> OcrResult | None:
        """Return the most confident text in the image, or None if there is none."""
        ...


def _best(candidates: list[OcrResult]) -> OcrResult | None:
    candidates = [c for c in candidates if c.text.strip()]
    return max(candidates, key=lambda c: c.confidence) if candidates else None


def _box(points: Any) -> Box | None:
    """Axis-aligned box around a polygon ([[x, y], ...]); None if the points cannot be read."""
    try:
        pts = np.asarray(points, dtype=float).reshape(-1, 2)
    except (TypeError, ValueError):
        return None
    if pts.size == 0:
        return None
    x1, y1 = pts.min(axis=0)
    x2, y2 = pts.max(axis=0)
    return int(x1), int(y1), int(round(x2)), int(round(y2))


def parse_paddle_lines(result: Any) -> list[OcrResult]:
    """Every text line, with its box where given. 3.x: dicts of rec_texts/rec_scores/rec_polys; 2.x: [[box, (text, score)], ...]."""
    lines: list[OcrResult] = []
    if not result:
        return lines
    for page in result:
        if page is None:
            continue
        if hasattr(page, 'get') and page.get('rec_texts') is not None:
            polys = page.get('rec_polys')
            polys = [None] * len(page['rec_texts']) if polys is None else polys
            lines += [OcrResult(t, float(s), _box(p) if p is not None else None)
                      for t, s, p in zip(page['rec_texts'], page['rec_scores'], polys)]
        else:
            lines += [OcrResult(line[1][0], float(line[1][1]), _box(line[0])) for line in page]
    return [line for line in lines if line.text.strip()]


def parse_paddle_result(result: Any) -> OcrResult | None:
    """The most confident line of a PaddleOCR result (either version)."""
    return _best(parse_paddle_lines(result))


def parse_rapidocr_lines(result: Any) -> list[OcrResult]:
    """RapidOCR gives (lines, timings), where each line is [box, text, score], or lines=None when empty."""
    if not result or not result[0]:
        return []
    return [OcrResult(line[1], float(line[2]), _box(line[0])) for line in result[0] if str(line[1]).strip()]


def parse_rapidocr_result(result: Any) -> OcrResult | None:
    return _best(parse_rapidocr_lines(result))


def row_groups(lines: Sequence[OcrResult], gap_ratio: float = 0.6) -> list[Box]:
    """Union boxes of text pieces that sit side by side on one row (groups of two or more pieces only).

    PP-OCR's text detector sometimes splits one room number into overlapping pieces ("M1.1" + "14" for M1.14, seen
    on synthetic signs in perception/), and the pieces cannot be joined reliably as text; re-reading the union box
    can. Pieces join when they overlap vertically by half the smaller height and the horizontal gap is under
    gap_ratio x line height (overlaps count as gap <= 0). Ported from perception/merz_signs (decisions #24).
    """
    boxed = sorted((line.box for line in lines if line.box is not None), key=lambda b: b[0])
    groups: list[list[Box]] = []
    for box in boxed:
        for group in groups:
            last = group[-1]
            height = min(box[3] - box[1], last[3] - last[1])
            v_overlap = min(box[3], last[3]) - max(box[1], last[1])
            gap = box[0] - last[2]
            if height > 0 and v_overlap >= 0.5 * height and gap <= gap_ratio * height:
                group.append(box)
                break
        else:
            groups.append([box])
    return [(min(b[0] for b in g), min(b[1] for b in g), max(b[2] for b in g), max(b[3] for b in g))
            for g in groups if len(g) > 1]


def read_room_number(engine: OcrEngine, image_bgr: np.ndarray, validator: Any) -> tuple[OcrResult | None, str | None]:
    """OCR an (already prepared) sign crop and return (line used, room number or None).

    1. Read every line (engines without read_lines give just their best line).
    2. Re-read rows the text detector split into pieces, if the engine can recognise without detection.
    3. Validate each line and each space-separated token; drop any room number that is part of a longer one
       found in the same crop ("14" when "M1.14" is also read), then take the most confident.
    If nothing validates, the most confident raw line is returned with None, so the caller can log what was rejected.
    """
    read_lines = getattr(engine, 'read_lines', None)
    if read_lines is not None:
        lines = list(read_lines(image_bgr))
    else:
        best = engine.read(image_bgr)
        lines = [best] if best is not None else []
    recognise = getattr(engine, 'recognise', None)
    if recognise is not None:
        h, w = image_bgr.shape[:2]
        for x1, y1, x2, y2 in row_groups(lines):
            pad = max(2, (y2 - y1) // 10)
            merged = recognise(image_bgr[max(0, y1 - pad):min(h, y2 + pad), max(0, x1 - pad):min(w, x2 + pad)])
            if merged is not None and merged.text.strip():
                lines.append(OcrResult(merged.text, merged.confidence, (x1, y1, x2, y2)))
    found: dict[str, OcrResult] = {}
    for line in lines:
        for text in [line.text, *line.text.split()]:
            room = validator.validate(text)
            if room is not None and (room not in found or line.confidence > found[room].confidence):
                found[room] = line
    kept = {room: line for room, line in found.items() if not any(room != other and room in other for other in found)}
    if kept:
        room = max(kept, key=lambda r: kept[r].confidence)
        return kept[room], room
    return _best(lines), None


class PaddleEngine:
    def __init__(self) -> None:
        from paddleocr import PaddleOCR

        self._ocr = PaddleOCR(lang='en')
        self._use_predict = hasattr(self._ocr, 'predict')   # 3.x API; 2.x only has ocr()

    def read_lines(self, image_bgr: np.ndarray) -> list[OcrResult]:
        raw = self._ocr.predict(image_bgr) if self._use_predict else self._ocr.ocr(image_bgr)
        return parse_paddle_lines(raw)

    def read(self, image_bgr: np.ndarray) -> OcrResult | None:
        return _best(self.read_lines(image_bgr))

    def recognise(self, image_bgr: np.ndarray) -> OcrResult | None:
        """Recognition only (no detection), via the 3.x TextRecognition module. NOT RUN yet; returns None on 2.x."""
        if not hasattr(self, '_rec'):
            try:
                from paddleocr import TextRecognition

                self._rec = TextRecognition()
            except Exception:   # 2.x, or no model download: rows are simply not re-read
                self._rec = None
        if self._rec is None:
            return None
        for res in self._rec.predict(image_bgr):
            text, score = res.get('rec_text'), res.get('rec_score')
            if text:
                return OcrResult(str(text), float(score or 0.0))
        return None


class RapidEngine:
    def __init__(self) -> None:
        from rapidocr_onnxruntime import RapidOCR

        self._ocr = RapidOCR()

    def read_lines(self, image_bgr: np.ndarray) -> list[OcrResult]:
        return parse_rapidocr_lines(self._ocr(image_bgr))

    def read(self, image_bgr: np.ndarray) -> OcrResult | None:
        return _best(self.read_lines(image_bgr))

    def recognise(self, image_bgr: np.ndarray) -> OcrResult | None:
        """Recognition only (no detection step), for re-reading a merged row."""
        result, _ = self._ocr(image_bgr, use_det=False, use_cls=False, use_rec=True)
        if not result or not str(result[0][0]).strip():
            return None
        return OcrResult(str(result[0][0]), float(result[0][1]))


def make_ocr(name: str = 'auto') -> OcrEngine:
    """Create an OCR engine. "auto" tries PaddleOCR, then RapidOCR, and says so if both are missing."""
    if name == 'paddle':
        return PaddleEngine()
    if name == 'rapid':
        return RapidEngine()
    if name != 'auto':
        raise ValueError(f"Unknown OCR engine '{name}'. Choose paddle, rapid or auto")
    try:
        return PaddleEngine()
    except ImportError:
        pass
    try:
        return RapidEngine()
    except ImportError as error:
        raise ImportError('No OCR library found. Run: pip install rapidocr-onnxruntime') from error


def prepare_crop(crop_bgr: np.ndarray, min_height: int = 64) -> np.ndarray:
    """Upscale small sign crops, as OCR accuracy falls sharply for very small text."""
    height = crop_bgr.shape[0]
    if height == 0 or height >= min_height:
        return crop_bgr
    import cv2

    scale = min_height / height
    return cv2.resize(crop_bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
