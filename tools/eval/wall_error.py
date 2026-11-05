"""O2 wall accuracy: the distance from each occupied map cell to the nearest wall on the floor plan.

    python tools/eval/wall_error.py --map map.yaml --walls floorplan_walls.csv --plot wall_error.png

The walls CSV has columns x1,y1,x2,y2 (metres, map frame). Align the floor plan to the map first, and report how.
Cells beyond --match-radius are probably not walls (furniture, people) so they are excluded, and the share excluded is
always reported, as a large share would mean the mean is flattering the map. Target: 0.15 m (rule: docs/planning/experiments.md).
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (COLOUR_PRIMARY, OCCUPIED, STATS_HEADERS, GridMap, describe, format_table, load_map, new_figure,  # noqa: E402
                    pass_fail, read_csv, save_figure, stats_row)
from common import stats_dict, write_json  # noqa: E402,F401

TARGET_M = 0.15


def distances_to_segments(points: np.ndarray, segments: np.ndarray) -> np.ndarray:
    """Return, for each (x, y) point, the distance to the nearest segment (x1, y1, x2, y2)."""
    start, end = segments[:, :2], segments[:, 2:]
    direction = end - start
    length_squared = np.maximum((direction ** 2).sum(axis=1), 1e-12)   # zero-length segments act as points
    offsets = points[:, None, :] - start[None, :, :]
    fraction = np.clip((offsets * direction[None, :, :]).sum(axis=2) / length_squared, 0.0, 1.0)
    closest = start[None, :, :] + fraction[:, :, None] * direction[None, :, :]
    return np.linalg.norm(points[:, None, :] - closest, axis=2).min(axis=1)


def occupied_points(grid: GridMap) -> np.ndarray:
    rows, cols = np.nonzero(grid.cells == OCCUPIED)
    return np.column_stack([grid.origin_x + (cols + 0.5) * grid.resolution,
                            grid.origin_y + (rows + 0.5) * grid.resolution])


def wall_errors(grid: GridMap, segments: np.ndarray, match_radius_m: float) -> tuple[np.ndarray, float]:
    """Return (the errors of matched cells, the percentage of occupied cells excluded)."""
    points = occupied_points(grid)
    if points.size == 0:
        raise ValueError('The map has no occupied cells')
    distances = distances_to_segments(points, segments)
    matched = distances[distances <= match_radius_m]
    return matched, 100.0 * (1.0 - matched.size / distances.size)


def plot(errors: np.ndarray, path: Path) -> None:
    figure, axes = new_figure()
    axes.hist(errors, bins=30, color=COLOUR_PRIMARY, edgecolor='white', linewidth=0.5)
    axes.axvline(TARGET_M, color='black', linestyle='--', linewidth=1, label=f'Target {TARGET_M} m')
    axes.set_xlabel('Distance to floor plan wall (m)')
    axes.set_ylabel('Occupied cells')
    axes.legend(frameon=False)
    save_figure(figure, path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--map', required=True)
    parser.add_argument('--walls', required=True)
    parser.add_argument('--match-radius', type=float, default=0.5, help='Metres. Decide this before the run.')
    parser.add_argument('--plot', type=Path)
    parser.add_argument('--json', type=Path, help='Also save the numbers as JSON, for tools/web_import.py.')
    args = parser.parse_args()
    segments = np.array([[float(r[k]) for k in ('x1', 'y1', 'x2', 'y2')] for r in read_csv(args.walls)])
    errors, excluded = wall_errors(load_map(args.map), segments, args.match_radius)
    stats = describe(errors)
    print(format_table(STATS_HEADERS, [stats_row('wall error (m)', stats)]))
    print(f'Excluded beyond {args.match_radius} m: {excluded:.1f}% of occupied cells')
    print(f'Within {TARGET_M} m: {100.0 * np.mean(errors <= TARGET_M):.1f}% of matched cells')
    print(f'Mean <= {TARGET_M} m: {pass_fail(stats.mean <= TARGET_M)}')
    if args.plot:
        plot(errors, args.plot)
    if args.json:
        write_json(args.json, 'O2', 'wall_error', stats.mean <= TARGET_M,
                   {'stats': stats_dict(stats), 'excluded_percent': float(excluded),
                    'within_target_percent': float(100.0 * np.mean(errors <= TARGET_M)), 'target_m': TARGET_M,
                    'match_radius_m': args.match_radius,
                    'histogram': np.histogram(errors, bins=20, range=(0.0, args.match_radius))[0].tolist()},
                   {'map': args.map, 'walls': args.walls})


if __name__ == '__main__':
    main()
