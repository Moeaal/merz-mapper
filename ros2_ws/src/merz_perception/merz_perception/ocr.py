"""OCR engines behind one interface: PaddleOCR, with RapidOCR (ONNX Runtime) as the fallback. No ROS imports.

PaddleOCR may be hard to install on the Jetson (aarch64 with GPU), so the fallback exists from the start. The result
formats differ between library versions, so parsing is kept in small functions that can be tested without the libraries.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np


@dataclass(frozen=True)
class OcrResult:
    text: str
    confidence: float


class OcrEngine(Protocol):
    def read(self, image_bgr: np.ndarray) -> OcrResult | None:
        """Return the most confident text in the image, or None if there is none."""
        ...


def _best(candidates: list[OcrResult]) -> OcrResult | None:
    candidates = [c for c in candidates if c.text.strip()]
    return max(candidates, key=lambda c: c.confidence) if candidates else None


def parse_paddle_result(result: Any) -> OcrResult | None:
    """Handle both result shapes: 3.x gives dicts of rec_texts and rec_scores; 2.x gives [[box, (text, score)], ...]."""
    if not result:
        return None
    candidates: list[OcrResult] = []
    for page in result:
        if page is None:
            continue
        if hasattr(page, 'get') and page.get('rec_texts') is not None:
            candidates += [OcrResult(t, float(s)) for t, s in zip(page['rec_texts'], page['rec_scores'])]
        else:
            candidates += [OcrResult(line[1][0], float(line[1][1])) for line in page]
    return _best(candidates)


def parse_rapidocr_result(result: Any) -> OcrResult | None:
    """RapidOCR gives (lines, timings), where each line is [box, text, score], or lines=None when empty."""
    if not result or not result[0]:
        return None
    return _best([OcrResult(line[1], float(line[2])) for line in result[0]])


class PaddleEngine:
    def __init__(self) -> None:
        from paddleocr import PaddleOCR

        self._ocr = PaddleOCR(lang='en')
        self._use_predict = hasattr(self._ocr, 'predict')   # 3.x API; 2.x only has ocr()

    def read(self, image_bgr: np.ndarray) -> OcrResult | None:
        raw = self._ocr.predict(image_bgr) if self._use_predict else self._ocr.ocr(image_bgr)
        return parse_paddle_result(raw)


class RapidEngine:
    def __init__(self) -> None:
        from rapidocr_onnxruntime import RapidOCR

        self._ocr = RapidOCR()

    def read(self, image_bgr: np.ndarray) -> OcrResult | None:
        return parse_rapidocr_result(self._ocr(image_bgr))


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
