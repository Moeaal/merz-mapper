"""Camera geometry for landmark localisation. NumPy only, no ROS, so it can be checked against known answers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class Intrinsics:
    """Pinhole camera model, in pixels. For a sensor_msgs/CameraInfo: fx=k[0], fy=k[4], cx=k[2], cy=k[5]."""

    fx: float
    fy: float
    cx: float
    cy: float


@dataclass(frozen=True)
class BoundingBox:
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @property
    def centre(self) -> tuple[float, float]:
        return (self.x_min + self.x_max) / 2.0, (self.y_min + self.y_max) / 2.0

    def contains(self, u: float, v: float) -> bool:
        return self.x_min <= u <= self.x_max and self.y_min <= v <= self.y_max


def median_depth_in_box(depth_m: np.ndarray, box: BoundingBox, shrink: float = 0.5) -> Optional[float]:
    """Return the median valid depth (metres) in the central part of the box, or None if there are no valid pixels.

    The median ignores outliers. Only the central part is used (shrink=0.5 keeps the middle half of each side), as
    the edge of a box often falls on the wall behind the object. Zero and NaN mean "no reading" on the D455.
    """
    height, width = depth_m.shape
    centre_u, centre_v = box.centre
    half_w = (box.x_max - box.x_min) * shrink / 2.0
    half_h = (box.y_max - box.y_min) * shrink / 2.0
    x0, x1 = max(0, int(centre_u - half_w)), min(width, int(np.ceil(centre_u + half_w)))
    y0, y1 = max(0, int(centre_v - half_h)), min(height, int(np.ceil(centre_v + half_h)))
    if x0 >= x1 or y0 >= y1:
        return None
    values = depth_m[y0:y1, x0:x1]
    valid = values[np.isfinite(values) & (values > 0)]
    return float(np.median(valid)) if valid.size else None


def deproject(u: float, v: float, depth_m: float, k: Intrinsics) -> np.ndarray:
    """Pixel plus depth to a 3D point in the camera's optical frame (x right, y down, z forward)."""
    return np.array([(u - k.cx) * depth_m / k.fx, (v - k.cy) * depth_m / k.fy, depth_m])


def project(point_optical: np.ndarray, k: Intrinsics) -> Optional[tuple[float, float]]:
    """3D point in the optical frame to a pixel. None if it is behind the camera."""
    x, y, z = point_optical
    if z <= 0:
        return None
    return k.fx * x / z + k.cx, k.fy * y / z + k.cy


def transform_matrix(translation: tuple[float, float, float],
                     quaternion_xyzw: tuple[float, float, float, float]) -> np.ndarray:
    """Build a 4x4 transform from a geometry_msgs/Transform's values, normalising the quaternion."""
    x, y, z, w = np.asarray(quaternion_xyzw, dtype=float) / np.linalg.norm(quaternion_xyzw)
    matrix = np.eye(4)
    matrix[:3, :3] = [
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ]
    matrix[:3, 3] = translation
    return matrix


def apply_transform(matrix: np.ndarray, point: np.ndarray) -> np.ndarray:
    return matrix[:3, :3] @ point + matrix[:3, 3]


def inverse_transform(matrix: np.ndarray) -> np.ndarray:
    """Invert a rigid transform, using the fact that a rotation's inverse is its transpose."""
    inverse = np.eye(4)
    rotation = matrix[:3, :3].T
    inverse[:3, :3] = rotation
    inverse[:3, 3] = -rotation @ matrix[:3, 3]
    return inverse
