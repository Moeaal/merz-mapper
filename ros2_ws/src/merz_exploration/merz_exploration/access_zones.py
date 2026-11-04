"""Work out what is reachable from an entrance. No ROS imports.

An access zone is the free space connected to an entrance. Closed doors look like walls to the LIDAR, so exploring with
doors as found naturally stops at them (O5). A landmark belongs to the zone if it lies on or beside that free space,
since door and sign landmarks sit on the wall and never in free space itself.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np

from merz_exploration.map_io import FREE, GridMap


def nearest_free_cell(grid: GridMap, row: int, col: int, max_radius_cells: int) -> Optional[tuple[int, int]]:
    """Return the closest free cell to (row, col), or None if none is in range.

    The start pose can land on an occupied or unknown cell through small pose or map errors, which would otherwise make
    the entire zone come out empty.
    """
    rows, cols = np.nonzero(grid.cells == FREE)
    if rows.size == 0:
        return None
    distances = np.hypot(rows - row, cols - col)
    best = int(np.argmin(distances))
    return (int(rows[best]), int(cols[best])) if distances[best] <= max_radius_cells else None


def flood_fill(cells: np.ndarray, seed: tuple[int, int]) -> np.ndarray:
    """Return a boolean mask of the free cells connected to seed, moving in 4 directions.

    Four-connected, as 8-connected would leak through a diagonal gap between two wall cells, which a robot could not
    use. Unknown cells block the fill: only space actually observed as free counts as reachable.
    """
    height, width = cells.shape
    mask = np.zeros(cells.shape, dtype=bool)
    if not (0 <= seed[0] < height and 0 <= seed[1] < width) or cells[seed] != FREE:
        return mask
    mask[seed] = True
    queue = deque([seed])
    while queue:
        row, col = queue.popleft()
        for next_row, next_col in ((row + 1, col), (row - 1, col), (row, col + 1), (row, col - 1)):
            if (0 <= next_row < height and 0 <= next_col < width and not mask[next_row, next_col]
                    and cells[next_row, next_col] == FREE):
                mask[next_row, next_col] = True
                queue.append((next_row, next_col))
    return mask


def zone_for_entrance(grid: GridMap, x: float, y: float, seed_search_m: float = 1.0) -> np.ndarray:
    """Return the reachable mask from a start position in metres. Empty if there is no free cell near it."""
    row, col = grid.world_to_cell(x, y)
    seed = nearest_free_cell(grid, row, col, int(np.ceil(seed_search_m / grid.resolution)))
    if seed is None:
        return np.zeros(grid.cells.shape, dtype=bool)
    return flood_fill(grid.cells, seed)


def touches_zone(grid: GridMap, zone: np.ndarray, x: float, y: float, adjacency_m: float) -> bool:
    """True if a point is within adjacency_m of a cell in the zone. Points off the grid can still be near its edge."""
    row, col = grid.world_to_cell(x, y)
    radius = int(np.ceil(adjacency_m / grid.resolution))
    row_low, row_high = max(0, row - radius), min(zone.shape[0], row + radius + 1)
    col_low, col_high = max(0, col - radius), min(zone.shape[1], col + radius + 1)
    if row_low >= row_high or col_low >= col_high:
        return False
    rows, cols = np.nonzero(zone[row_low:row_high, col_low:col_high])
    if rows.size == 0:
        return False
    return bool(np.any(np.hypot(rows + row_low - row, cols + col_low - col) * grid.resolution <= adjacency_m))


@dataclass(frozen=True)
class ZoneResult:
    landmark_ids: list[int]
    junction_ids: list[int]
    area_m2: float


def compute_zone(grid: GridMap, start_x: float, start_y: float, landmarks: Iterable[dict], junctions: Iterable[dict],
                 landmark_adjacency_m: float = 0.5, junction_adjacency_m: float = 0.5,
                 seed_search_m: float = 1.0) -> ZoneResult:
    """List the landmarks and junctions reachable from a start position. Rows need id, x and y keys."""
    zone = zone_for_entrance(grid, start_x, start_y, seed_search_m)
    return ZoneResult(
        landmark_ids=[row['id'] for row in landmarks
                      if touches_zone(grid, zone, row['x'], row['y'], landmark_adjacency_m)],
        junction_ids=[row['id'] for row in junctions
                      if touches_zone(grid, zone, row['x'], row['y'], junction_adjacency_m)],
        area_m2=float(zone.sum()) * grid.resolution ** 2,
    )
