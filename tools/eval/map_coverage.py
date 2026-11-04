"""O2 coverage: the share of an agreed corridor polygon that the map shows as free.

    python tools/eval/map_coverage.py --map map.yaml --polygon corridor.csv --plot coverage.png

The polygon CSV has columns x,y (metres, map frame), one row per vertex, in order. Target: >=90%.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import COLOUR_PRIMARY, FREE, GridMap, format_table, load_map, new_figure, pass_fail, read_csv, save_figure  # noqa: E402
from common import stats_dict, write_json  # noqa: E402,F401

TARGET_PERCENT = 90.0


@dataclass(frozen=True)
class Coverage:
    polygon_area_m2: float
    free_area_m2: float

    @property
    def percent(self) -> float:
        return 100.0 * self.free_area_m2 / self.polygon_area_m2 if self.polygon_area_m2 else 0.0


def points_in_polygon(x: np.ndarray, y: np.ndarray, polygon: np.ndarray) -> np.ndarray:
    """Ray casting, on arrays of points: a point is inside if a ray from it crosses the outline an odd number of times."""
    inside = np.zeros(x.shape, dtype=bool)
    x_previous, y_previous = polygon[-1]
    for x_vertex, y_vertex in polygon:
        spans = (y_vertex > y) != (y_previous > y)
        with np.errstate(divide='ignore', invalid='ignore'):
            crossing_x = (x_previous - x_vertex) * (y - y_vertex) / (y_previous - y_vertex) + x_vertex
        inside ^= spans & (x < crossing_x)
        x_previous, y_previous = x_vertex, y_vertex
    return inside


def polygon_mask(grid: GridMap, polygon: np.ndarray) -> np.ndarray:
    rows, cols = np.indices(grid.cells.shape)
    x = grid.origin_x + (cols + 0.5) * grid.resolution
    y = grid.origin_y + (rows + 0.5) * grid.resolution
    return points_in_polygon(x, y, polygon)


def coverage(grid: GridMap, polygon: np.ndarray) -> Coverage:
    """Polygon area comes from the outline, so a polygon reaching beyond the mapped area correctly lowers coverage."""
    x, y = polygon[:, 0], polygon[:, 1]
    area = 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
    mask = polygon_mask(grid, polygon)
    return Coverage(float(area), float(np.count_nonzero(mask & (grid.cells == FREE))) * grid.resolution ** 2)


def plot(grid: GridMap, polygon: np.ndarray, path: Path) -> None:
    figure, axes = new_figure()
    extent = (grid.origin_x, grid.origin_x + grid.cells.shape[1] * grid.resolution,
              grid.origin_y, grid.origin_y + grid.cells.shape[0] * grid.resolution)
    shades = np.select([grid.cells == FREE, grid.cells > 0], [1.0, 0.0], default=0.75)
    axes.imshow(shades, origin='lower', extent=extent, cmap='gray', vmin=0, vmax=1)
    closed = np.vstack([polygon, polygon[0]])
    axes.plot(closed[:, 0], closed[:, 1], color=COLOUR_PRIMARY, linewidth=1.5, label='Corridor polygon')
    axes.set_xlabel('x (m)')
    axes.set_ylabel('y (m)')
    axes.grid(False)
    axes.legend(loc='best', frameon=True)
    save_figure(figure, path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--map', required=True)
    parser.add_argument('--polygon', required=True)
    parser.add_argument('--plot', type=Path)
    parser.add_argument('--json', type=Path, help='Also save the numbers as JSON, for tools/web_import.py.')
    args = parser.parse_args()
    grid = load_map(args.map)
    polygon = np.array([[float(r['x']), float(r['y'])] for r in read_csv(args.polygon)])
    result = coverage(grid, polygon)
    print(format_table(['polygon m2', 'free m2', 'coverage %', f'>={TARGET_PERCENT:.0f}%'],
                       [[result.polygon_area_m2, result.free_area_m2, result.percent,
                         pass_fail(result.percent >= TARGET_PERCENT)]]))
    if args.plot:
        plot(grid, polygon, args.plot)
    if args.json:
        write_json(args.json, 'O2', 'map_coverage', result.percent >= TARGET_PERCENT,
                   {'polygon_m2': result.polygon_area_m2, 'free_m2': result.free_area_m2, 'percent': result.percent,
                    'target_percent': TARGET_PERCENT}, {'map': args.map, 'polygon': args.polygon})


if __name__ == '__main__':
    main()
