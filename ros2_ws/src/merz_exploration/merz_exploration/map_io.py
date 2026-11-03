"""Read saved occupancy grids (map_saver's .yaml + .pgm). No ROS imports. Also used by tools/eval.

Cell values are normalised to the nav_msgs/OccupancyGrid convention: 0 free, 100 occupied, -1 unknown. Row 0 of the
returned array is the bottom of the map (y increasing), matching OccupancyGrid rather than the image's top-down rows.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

FREE, OCCUPIED, UNKNOWN = 0, 100, -1
MAP_SAVER_UNKNOWN_PIXEL = 205


@dataclass(frozen=True)
class GridMap:
    cells: np.ndarray            # 2D int8, row 0 at the lowest y
    resolution: float            # metres per cell
    origin_x: float              # world position of the corner of cell (0, 0), metres
    origin_y: float

    def world_to_cell(self, x: float, y: float) -> tuple[int, int]:
        """Return (row, col). May be outside the grid."""
        return int(np.floor((y - self.origin_y) / self.resolution)), int(np.floor((x - self.origin_x) / self.resolution))

    def cell_to_world(self, row: int, col: int) -> tuple[float, float]:
        """Return the world position of the centre of a cell."""
        return self.origin_x + (col + 0.5) * self.resolution, self.origin_y + (row + 0.5) * self.resolution

    def in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < self.cells.shape[0] and 0 <= col < self.cells.shape[1]


def read_pgm(path: Path) -> np.ndarray:
    """Read an 8-bit binary PGM (P5), the format map_saver writes. Comments in the header are allowed."""
    data = Path(path).read_bytes()
    tokens: list[bytes] = []
    position = 0
    while len(tokens) < 4:
        while data[position:position + 1].isspace():
            position += 1
        if data[position:position + 1] == b'#':
            position = data.index(b'\n', position) + 1
            continue
        start = position
        while not data[position:position + 1].isspace():
            position += 1
        tokens.append(data[start:position])
    position += 1   # exactly one whitespace byte separates the header from the pixels
    if tokens[0] != b'P5':
        raise ValueError(f'{path}: expected a binary P5 PGM, got {tokens[0]!r}')
    width, height, max_value = int(tokens[1]), int(tokens[2]), int(tokens[3])
    if max_value > 255:
        raise ValueError(f'{path}: only 8-bit PGM is supported')
    pixels = np.frombuffer(data, dtype=np.uint8, count=width * height, offset=position)
    return pixels.reshape(height, width)


def load_map(yaml_path: str | Path) -> GridMap:
    """Load a map from its YAML file, following the map_server rules for thresholds and negation."""
    yaml_path = Path(yaml_path).expanduser()
    info = yaml.safe_load(yaml_path.read_text())
    raw = read_pgm(yaml_path.parent / info['image'])
    image = raw.astype(np.float64)
    # map_server: occupancy probability = (255 - pixel) / 255, or pixel / 255 when negate is set.
    probability = image / 255.0 if info.get('negate', 0) else (255.0 - image) / 255.0
    cells = np.full(probability.shape, UNKNOWN, dtype=np.int8)
    cells[probability > float(info['occupied_thresh'])] = OCCUPIED
    cells[probability < float(info['free_thresh'])] = FREE
    # map_saver writes unknown cells as exactly 205, which is probability 0.196. With its usual free_thresh of 0.25,
    # the rule above would call them free, and flood fill would then leak through unexplored space. So the marker
    # value takes priority. (Trinary is the mode map_saver and slam_toolbox write.)
    if info.get('mode', 'trinary') == 'trinary' and not info.get('negate', 0):
        cells[raw == MAP_SAVER_UNKNOWN_PIXEL] = UNKNOWN
    origin = info.get('origin', [0.0, 0.0, 0.0])
    return GridMap(cells=np.flipud(cells), resolution=float(info['resolution']),
                   origin_x=float(origin[0]), origin_y=float(origin[1]))
