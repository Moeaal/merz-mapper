"""Load the robot's saved occupancy grid (map_saver .yaml + .pgm) and turn it into a PNG for the page.

The thresholds follow the map_server rules, as in ros2_ws/src/merz_exploration/merz_exploration/map_io.py. That module
is not imported, so the website keeps working without the ROS workspace's numpy code. Unknown cells become transparent,
so the page's own background shows where the robot has not been.
"""
from __future__ import annotations

from dataclasses import dataclass
import io
from pathlib import Path

import yaml

MAP_SAVER_UNKNOWN_PIXEL = 205
WALL_RGBA = (19, 35, 58, 255)        # the page's ink colour; the page recolours it for dark mode
FLOOR_RGBA = (255, 255, 255, 255)
UNKNOWN_RGBA = (0, 0, 0, 0)


@dataclass(frozen=True)
class GridMap:
    resolution: float      # metres per cell
    origin_x: float        # map-frame position of the bottom-left corner of the image, metres
    origin_y: float
    width: int             # cells
    height: int
    png: bytes             # one pixel per cell, row 0 at the top (highest y), as in the .pgm


def classify(pixel: int, info: dict) -> tuple[int, int, int, int]:
    """Colour for one 8-bit .pgm value, using the YAML's thresholds."""
    negate = bool(info.get('negate', 0))
    probability = pixel / 255.0 if negate else (255.0 - pixel) / 255.0
    if info.get('mode', 'trinary') == 'trinary' and not negate and pixel == MAP_SAVER_UNKNOWN_PIXEL:
        return UNKNOWN_RGBA
    if probability > float(info.get('occupied_thresh', 0.65)):
        return WALL_RGBA
    if probability < float(info.get('free_thresh', 0.25)):
        return FLOOR_RGBA
    return UNKNOWN_RGBA


def load_grid_map(yaml_path: str | Path) -> GridMap:
    from PIL import Image

    yaml_path = Path(yaml_path)
    info = yaml.safe_load(yaml_path.read_text())
    with Image.open(yaml_path.parent / info['image']) as source:
        grey = source.convert('L')
    lookup = [classify(value, info) for value in range(256)]
    # One lookup table per channel: fast, and needs nothing beyond Pillow.
    channels = [grey.point([colour[band] for colour in lookup]) for band in range(4)]
    image = Image.merge('RGBA', channels)
    buffer = io.BytesIO()
    image.save(buffer, format='PNG', optimize=True)
    origin = info.get('origin', [0.0, 0.0, 0.0])
    return GridMap(resolution=float(info['resolution']), origin_x=float(origin[0]), origin_y=float(origin[1]),
                   width=grey.width, height=grey.height, png=buffer.getvalue())
