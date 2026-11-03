"""Compute one entrance's access zone from a saved map and store it. Needs no ROS, so it can be re-run offline.

    python -m merz_exploration.compute_access_zones --map map.yaml --database merz.sqlite --entrance east \
        --start 0.0 0.0 --name "East door"
"""
from __future__ import annotations

import argparse
from pathlib import Path

from merz_exploration.access_zones import ZoneResult, compute_zone
from merz_exploration.map_io import load_map
from merz_semantic_map.database import MerzDatabase


def store_zone(map_yaml: str | Path, database_path: str | Path, entrance: str, name: str, start_x: float,
               start_y: float, start_yaw: float = 0.0, landmark_adjacency_m: float = 0.5,
               junction_adjacency_m: float = 0.5) -> ZoneResult:
    grid = load_map(map_yaml)
    with MerzDatabase(database_path) as database:
        database.upsert_entrance(entrance, name, start_x, start_y, start_yaw)
        result = compute_zone(grid, start_x, start_y, database.landmarks(), database.junctions(),
                              landmark_adjacency_m, junction_adjacency_m)
        database.set_access_zone(entrance, result.landmark_ids, result.junction_ids)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--map', required=True, help='Map YAML saved by map_saver or slam_toolbox.')
    parser.add_argument('--database', required=True)
    parser.add_argument('--entrance', required=True, help='Short id, as used in the QR URL.')
    parser.add_argument('--name', help='Display name. Defaults to the id.')
    parser.add_argument('--start', nargs=2, type=float, required=True, metavar=('X', 'Y'),
                        help='Start position in the map frame, metres.')
    parser.add_argument('--yaw', type=float, default=0.0)
    parser.add_argument('--landmark-adjacency', type=float, default=0.5, help='Metres.')
    parser.add_argument('--junction-adjacency', type=float, default=0.5, help='Metres.')
    args = parser.parse_args()
    result = store_zone(args.map, args.database, args.entrance, args.name or args.entrance, args.start[0],
                        args.start[1], args.yaw, args.landmark_adjacency, args.junction_adjacency)
    print(f'{args.entrance}: {result.area_m2:.1f} m2 reachable, {len(result.landmark_ids)} landmarks, '
          f'{len(result.junction_ids)} junctions')


if __name__ == '__main__':
    main()
