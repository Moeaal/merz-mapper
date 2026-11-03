"""Reject blurred sign crops before they cost GPU time in OCR. NumPy only.

The variance of the Laplacian is high when an image has hard edges and low when motion blur has removed them.
The threshold has no universal value; it must be set from real C920 crops (TODO: measure on rover).
"""
from __future__ import annotations

import numpy as np


def to_gray(image: np.ndarray) -> np.ndarray:
    """Convert BGR to gray as float. A one-channel input is accepted unchanged."""
    if image.ndim == 2:
        return image.astype(np.float64)
    if image.ndim == 3 and image.shape[2] == 3:
        return image.astype(np.float64) @ np.array([0.114, 0.587, 0.299])
    raise ValueError(f'Expected a gray or BGR image, got shape {image.shape}')


def variance_of_laplacian(image: np.ndarray) -> float:
    """Return the sharpness score. Images too small for the 3x3 kernel score 0."""
    gray = to_gray(image)
    if gray.shape[0] < 3 or gray.shape[1] < 3:
        return 0.0
    laplacian = (gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:] - 4.0 * gray[1:-1, 1:-1])
    return float(laplacian.var())


def is_sharp(image: np.ndarray, threshold: float) -> bool:
    return variance_of_laplacian(image) >= threshold
