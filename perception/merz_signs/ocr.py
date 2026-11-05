"""PaddleOCR behind a small interface, with RapidOCR as a fallback. PROPOSED.

RapidOCR runs PaddleOCR's PP-OCR models converted to ONNX and ships them inside its pip wheel, so it works where
PaddleOCR cannot download its models (offline machines, some networks) or cannot be installed (some Jetson images).

PaddleOCR 3.x returns result objects with `rec_texts`/`rec_scores`; 2.x returns [[box, (text, score)], ...]. Both are
parsed here, in a function that can be tested without PaddleOCR installed.
"""
from __future__ import annotations

from typing import Any, Protocol

import numpy as np

from .room_parser import OcrLine


class OcrEngine(Protocol):
    def read(self, image_bgr: np.ndarray) -> list[OcrLine]:
        """Detect and recognise all text lines, with boxes where the engine gives them."""
        ...

    def recognise(self, image_bgr: np.ndarray) -> OcrLine | None:
        """Recognise one line of text that fills the image (no detection step). None if not supported."""
        ...


def _box(points: Any) -> tuple[int, int, int, int] | None:
    try:
        pts = np.asarray(points, dtype=float).reshape(-1, 2)
    except (TypeError, ValueError):
        return None
    if pts.size == 0:
        return None
    x1, y1 = pts.min(axis=0)
    x2, y2 = pts.max(axis=0)
    return int(x1), int(y1), int(round(x2)), int(round(y2))


def _field(page: Any, key: str) -> Any:
    """3.x result objects behave like dicts; some versions wrap the dict in a `.json` / `res` field."""
    try:
        value = page[key]
        if value is not None:
            return value
    except (KeyError, TypeError, IndexError):
        pass
    data = getattr(page, 'json', None)
    if isinstance(data, dict):
        data = data.get('res', data)
        return data.get(key)
    return None


def parse_paddle_result(result: Any) -> list[OcrLine]:
    lines: list[OcrLine] = []
    if not result:
        return lines
    for page in result:
        if page is None:
            continue
        texts = _field(page, 'rec_texts')
        if texts is not None:
            scores = _field(page, 'rec_scores')
            scores = [1.0] * len(texts) if scores is None else scores
            polys = _field(page, 'rec_polys')
            polys = [None] * len(texts) if polys is None else polys
            lines += [OcrLine(str(t), float(s), _box(p) if p is not None else None)
                      for t, s, p in zip(texts, scores, polys)]
            continue
        for item in page:          # 2.x
            text, score = item[1]
            lines.append(OcrLine(str(text), float(score), _box(item[0])))
    return [line for line in lines if line.text.strip()]


class PaddleEngine:
    """English PaddleOCR. Orientation and unwarping models are switched off: door signs are upright and small."""

    def __init__(self, lang: str = 'en', **kwargs: Any) -> None:
        from paddleocr import PaddleOCR

        try:   # 3.x argument names
            self._ocr = PaddleOCR(lang=lang, use_doc_orientation_classify=False, use_doc_unwarping=False,
                                  use_textline_orientation=False, **kwargs)
        except (TypeError, ValueError):   # 2.x
            self._ocr = PaddleOCR(lang=lang, use_angle_cls=False, **kwargs)
        self._predict = hasattr(self._ocr, 'predict')

    def read(self, image_bgr: np.ndarray) -> list[OcrLine]:
        raw = self._ocr.predict(image_bgr) if self._predict else self._ocr.ocr(image_bgr)
        return parse_paddle_result(raw)

    def recognise(self, image_bgr: np.ndarray) -> OcrLine | None:
        """NOT RUN in this session (PaddleOCR models could not be downloaded): uses the 3.x TextRecognition module."""
        if not hasattr(self, '_rec'):
            try:
                from paddleocr import TextRecognition

                self._rec = TextRecognition()
            except Exception as error:   # 2.x, or no model download
                print(f'PaddleOCR recognition-only mode unavailable ({type(error).__name__}); rows not re-read')
                self._rec = None
        if self._rec is None:
            return None
        for res in self._rec.predict(image_bgr):
            text, score = _field(res, 'rec_text'), _field(res, 'rec_score')
            if text:
                return OcrLine(str(text), float(score or 0.0))
        return None


def parse_rapidocr_result(result: Any) -> list[OcrLine]:
    """rapidocr_onnxruntime returns (lines, timings); each line is [box, text, score]; lines is None when empty."""
    if not result or not result[0]:
        return []
    return [OcrLine(str(line[1]), float(line[2]), _box(line[0])) for line in result[0] if str(line[1]).strip()]


class RapidEngine:
    def __init__(self) -> None:
        from rapidocr_onnxruntime import RapidOCR

        self._ocr = RapidOCR()

    def read(self, image_bgr: np.ndarray) -> list[OcrLine]:
        return parse_rapidocr_result(self._ocr(image_bgr))

    def recognise(self, image_bgr: np.ndarray) -> OcrLine | None:
        result, _ = self._ocr(image_bgr, use_det=False, use_cls=False, use_rec=True)
        if not result or not str(result[0][0]).strip():
            return None
        return OcrLine(str(result[0][0]), float(result[0][1]))


def make_ocr(name: str = 'paddle') -> OcrEngine:
    """paddle | rapid | auto (PaddleOCR, falling back to RapidOCR if it is missing or cannot load its models)."""
    if name == 'paddle':
        return PaddleEngine()
    if name == 'rapid':
        return RapidEngine()
    if name != 'auto':
        raise ValueError(f"Unknown OCR engine '{name}': use paddle, rapid or auto")
    try:
        return PaddleEngine()
    except Exception as error:   # ImportError, or a model download failure inside PaddleOCR
        print(f'PaddleOCR unavailable ({type(error).__name__}); using RapidOCR')
        return RapidEngine()


def prepare_crop(crop_bgr: np.ndarray, min_height: int = 96) -> np.ndarray:
    """Upscale small crops: recognition accuracy drops sharply when text is only a few pixels tall."""
    height = crop_bgr.shape[0]
    if height == 0 or height >= min_height:
        return crop_bgr
    import cv2

    scale = min_height / height
    return cv2.resize(crop_bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)


def sharpness(image_bgr: np.ndarray) -> float:
    """Variance of the Laplacian: low values mean blur. Logged so blur can be ruled in or out as a failure cause."""
    import cv2

    grey = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY) if image_bgr.ndim == 3 else image_bgr
    return float(cv2.Laplacian(grey, cv2.CV_64F).var())
