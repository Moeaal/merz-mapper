"""Decide when the robot is at a corridor junction. No ROS imports.

The rule, kept deliberately simple so it can be explained and checked:
  The scan is divided into four 90-degree sectors around the robot: ahead, left, behind and right. A sector is "open"
  if the median range in it exceeds open_range_m. A plain corridor has two open sectors (ahead and behind). Three or more
  means a junction. A photo is taken once per junction: the robot must have moved min_spacing_m from every saved one.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Optional, Sequence

import numpy as np

SECTOR_CENTRES = (0.0, math.pi / 2, math.pi, -math.pi / 2)


def open_sector_count(ranges: Sequence[float], angle_min: float, angle_increment: float, open_range_m: float,
                      yaw_offset: float = 0.0) -> int:
    """Count open sectors in a scan. yaw_offset is the laser's yaw relative to the robot."""
    values = np.asarray(ranges, dtype=float)
    if values.size == 0:
        return 0
    angles = angle_min + np.arange(values.size) * angle_increment + yaw_offset
    # inf means no return within range, which counts as open. NaN and 0 are invalid readings and are removed.
    usable = ~np.isnan(values) & (values > 0)
    count = 0
    for centre in SECTOR_CENTRES:
        offset = np.abs(np.arctan2(np.sin(angles - centre), np.cos(angles - centre)))
        in_sector = usable & (offset <= math.pi / 4)
        if in_sector.any() and np.median(values[in_sector]) > open_range_m:
            count += 1
    return count


def is_junction(open_sectors: int, min_open_sectors: int = 3) -> bool:
    return open_sectors >= min_open_sectors


@dataclass
class JunctionTracker:
    """Keeps saved junctions and the path between them, so that the route graph can be built."""

    min_spacing_m: float = 3.0
    positions: list[tuple[float, float]] = field(default_factory=list)
    _last_index: Optional[int] = None
    _travelled_m: float = 0.0
    _previous: Optional[tuple[float, float]] = None

    def update_pose(self, x: float, y: float) -> None:
        """Add up the distance driven. Edge lengths are path length, not the straight line."""
        if self._previous is not None:
            self._travelled_m += math.hypot(x - self._previous[0], y - self._previous[1])
        self._previous = (x, y)

    def nearest_within_spacing(self, x: float, y: float) -> Optional[int]:
        best, best_distance = None, self.min_spacing_m
        for index, (jx, jy) in enumerate(self.positions):
            distance = math.hypot(x - jx, y - jy)
            if distance < best_distance:
                best, best_distance = index, distance
        return best

    def arrive(self, x: float, y: float) -> tuple[int, bool, Optional[tuple[int, float]]]:
        """Record being at a junction.

        Returns (index of the junction, True if it is new, edge). The edge is (previous index, length in metres) when
        the robot has driven here from another junction, otherwise None. Returning to a known junction also links
        it to the previous one, which is how loops in the corridors enter the graph.
        """
        index = self.nearest_within_spacing(x, y)
        is_new = index is None
        if is_new:
            self.positions.append((x, y))
            index = len(self.positions) - 1
        edge = None
        if self._last_index is not None and self._last_index != index:
            edge = (self._last_index, self._travelled_m)
        if self._last_index != index:
            self._travelled_m = 0.0
        self._last_index = index
        return index, is_new, edge
