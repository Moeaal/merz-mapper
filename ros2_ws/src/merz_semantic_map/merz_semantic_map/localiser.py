"""Landmark pipeline: bbox -> median depth -> deproject -> map frame -> associate -> running mean. No ROS.

O8 needs fused and non-fused positions on the same data. fusion_mode selects what the live estimate does; every raw
observation is also stored, so tools/eval/fusion_compare.py can compute both from a single run.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from merz_semantic_map.geometry import (BoundingBox, Intrinsics, apply_transform, deproject, inverse_transform,
                                        median_depth_in_box, project)

FUSED = 'fused'                            # the running mean of all observations
SINGLE_OBSERVATION = 'single_observation'  # the first observation only, with no averaging
FUSION_MODES = {FUSED, SINGLE_OBSERVATION}


@dataclass(frozen=True)
class LocaliserConfig:
    min_depth_m: float = 0.6      # the D455's ideal range [H2]
    max_depth_m: float = 6.0
    gate_m: float = 1.0           # same-class observations closer than this are the same landmark. TODO: tune
    fusion_mode: str = FUSED

    def __post_init__(self) -> None:
        if self.fusion_mode not in FUSION_MODES:
            raise ValueError(f"fusion_mode must be one of {sorted(FUSION_MODES)}, got '{self.fusion_mode}'")


@dataclass
class TrackedLandmark:
    landmark_id: int
    landmark_class: str
    position: np.ndarray                 # metres, map frame
    count: int = 1
    text: str = ''
    confidence: float = 0.0
    first_seen_s: float = 0.0
    last_seen_s: float = 0.0
    photo_path: str = ''
    # Sum of squared differences from the mean (Welford's algorithm): gives the variance without storing all points.
    _scatter: np.ndarray = field(default_factory=lambda: np.zeros((3, 3)))

    @property
    def covariance(self) -> np.ndarray:
        """Sample covariance of the observations (m^2). Zero until there are two observations."""
        return self._scatter / (self.count - 1) if self.count > 1 else np.zeros((3, 3))


def locate_in_map(box: BoundingBox, depth_m: np.ndarray, intrinsics: Intrinsics, map_from_camera: np.ndarray,
                  config: LocaliserConfig) -> Optional[np.ndarray]:
    """Return the box's position in the map frame, or None if the depth is missing or out of the trusted range."""
    depth = median_depth_in_box(depth_m, box)
    if depth is None or not config.min_depth_m <= depth <= config.max_depth_m:
        return None
    u, v = box.centre
    return apply_transform(map_from_camera, deproject(u, v, depth, intrinsics))


class LandmarkMap:
    """Associates observations with landmarks and keeps their estimates."""

    def __init__(self, config: LocaliserConfig) -> None:
        self.config = config
        self.landmarks: list[TrackedLandmark] = []
        self._next_id = 1

    def restore(self, rows: list[dict]) -> None:
        """Load landmarks from the database, so a run from another entrance updates them instead of duplicating them.

        Only the variances are stored, so the restored scatter is diagonal. That only affects the covariance estimate.
        """
        for row in rows:
            count = int(row['observation_count'])
            scatter = np.diag([row['var_x'], row['var_y'], row['var_z']]) * max(count - 1, 0)
            self.landmarks.append(TrackedLandmark(
                landmark_id=int(row['id']), landmark_class=row['class'],
                position=np.array([row['x'], row['y'], row['z']], dtype=float), count=count, text=row['text'],
                confidence=row['confidence'], first_seen_s=row['first_seen'] or 0.0,
                last_seen_s=row['last_seen'] or 0.0, _scatter=scatter))
            self._next_id = max(self._next_id, int(row['id']) + 1)

    def add_observation(self, landmark_class: str, position: np.ndarray, confidence: float,
                        stamp_s: float) -> tuple[TrackedLandmark, bool]:
        """Fold in one observation. Returns the landmark and True if it was newly created."""
        landmark = self._nearest(landmark_class, position)
        if landmark is None:
            landmark = TrackedLandmark(self._next_id, landmark_class, np.array(position, dtype=float),
                                       confidence=confidence, first_seen_s=stamp_s, last_seen_s=stamp_s)
            self._next_id += 1
            self.landmarks.append(landmark)
            return landmark, True
        self._update(landmark, position, confidence, stamp_s)
        return landmark, False

    def _nearest(self, landmark_class: str, position: np.ndarray) -> Optional[TrackedLandmark]:
        candidates = [lm for lm in self.landmarks if lm.landmark_class == landmark_class]
        if not candidates:
            return None
        nearest = min(candidates, key=lambda lm: float(np.linalg.norm(lm.position - position)))
        return nearest if np.linalg.norm(nearest.position - position) <= self.config.gate_m else None

    def _update(self, landmark: TrackedLandmark, position: np.ndarray, confidence: float, stamp_s: float) -> None:
        landmark.count += 1
        landmark.confidence = max(landmark.confidence, confidence)
        landmark.last_seen_s = stamp_s
        if self.config.fusion_mode == SINGLE_OBSERVATION:
            return
        delta = position - landmark.position
        landmark.position = landmark.position + delta / landmark.count
        landmark._scatter = landmark._scatter + np.outer(delta, position - landmark.position)

    def attach_text(self, text: str, box_in_sign_camera: BoundingBox, sign_intrinsics: Intrinsics,
                    map_from_sign_camera: np.ndarray, sign_label: str = 'room_sign') -> Optional[TrackedLandmark]:
        """Give a room number to the sign landmark that lands inside the box where OCR read it.

        The C920 read the text and the D455 found the position, so they are joined by projecting each known sign into
        the C920 image. If several signs land in the box, the nearest to its centre wins. If none do, None is returned
        rather than guessing, and a later observation can try again.
        """
        camera_from_map = inverse_transform(map_from_sign_camera)
        centre_u, centre_v = box_in_sign_camera.centre
        best: Optional[TrackedLandmark] = None
        best_distance = float('inf')
        for landmark in self.landmarks:
            if landmark.landmark_class != sign_label:
                continue
            pixel = project(apply_transform(camera_from_map, landmark.position), sign_intrinsics)
            if pixel is None or not box_in_sign_camera.contains(*pixel):
                continue
            distance = float(np.hypot(pixel[0] - centre_u, pixel[1] - centre_v))
            if distance < best_distance:
                best, best_distance = landmark, distance
        if best is not None:
            best.text = text
        return best
