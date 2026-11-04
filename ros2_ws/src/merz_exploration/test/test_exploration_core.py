"""Flood fill, access zones, map reading, junction rule and mission end, on synthetic data. No ROS needed."""
import math

import numpy as np
import pytest

from merz_exploration.access_zones import compute_zone, flood_fill, nearest_free_cell, touches_zone, zone_for_entrance
from merz_exploration.compute_access_zones import store_zone
from merz_exploration.junctions import JunctionTracker, is_junction, open_sector_count
from merz_exploration.map_io import FREE, OCCUPIED, UNKNOWN, GridMap, load_map, read_pgm
from merz_exploration.mission import EndReason, MissionMonitor
from merz_semantic_map.database import MerzDatabase


def grid_from(rows: list[str], resolution: float = 1.0) -> GridMap:
    """Draw a map as text, with the first row at the highest y: . free, # wall, ? unknown."""
    values = {'.': FREE, '#': OCCUPIED, '?': UNKNOWN}
    cells = np.array([[values[c] for c in row] for row in reversed(rows)], dtype=np.int8)
    return GridMap(cells=cells, resolution=resolution, origin_x=0.0, origin_y=0.0)


TWO_ROOMS = grid_from([
    '#######',
    '#..#..#',
    '#..#..#',
    '#######',
])


# ---- flood fill
def test_fill_stops_at_a_closed_door():
    mask = flood_fill(TWO_ROOMS.cells, (1, 1))
    assert mask.sum() == 4
    assert not mask[1, 4]


def test_fill_passes_through_an_open_door():
    grid = grid_from(['#######', '#.....#', '#..#..#', '#######'])
    assert flood_fill(grid.cells, (1, 1)).sum() == 9


def test_fill_does_not_leak_through_a_diagonal_gap():
    grid = grid_from(['####', '#.##', '##.#', '####'])
    mask = flood_fill(grid.cells, (2, 1))
    assert mask.sum() == 1


def test_unknown_space_blocks_the_fill():
    grid = grid_from(['#####', '#.?.#', '#####'])
    assert flood_fill(grid.cells, (1, 1)).sum() == 1


@pytest.mark.parametrize('seed', [(0, 0), (99, 99), (-1, 0)])
def test_fill_from_a_wall_or_outside_is_empty(seed):
    assert flood_fill(TWO_ROOMS.cells, seed).sum() == 0


def test_large_grid_does_not_hit_a_recursion_limit():
    assert flood_fill(np.zeros((1000, 1000), dtype=np.int8), (0, 0)).sum() == 1_000_000


# ---- start cell
def test_seed_snaps_to_the_nearest_free_cell():
    assert nearest_free_cell(TWO_ROOMS, 0, 1, max_radius_cells=2) == (1, 1)


def test_seed_is_none_beyond_the_search_radius():
    assert nearest_free_cell(TWO_ROOMS, 0, 1, max_radius_cells=0) is None


def test_zone_from_a_start_pose_on_a_wall_still_finds_the_room():
    assert zone_for_entrance(TWO_ROOMS, 1.5, 0.5, seed_search_m=2.0).sum() == 4


def test_zone_is_empty_when_no_free_space_is_nearby():
    assert zone_for_entrance(grid_from(['###', '###']), 1.0, 1.0).sum() == 0


# ---- zone membership
def test_landmark_on_the_wall_of_the_zone_touches_it():
    zone = flood_fill(TWO_ROOMS.cells, (1, 1))
    assert touches_zone(TWO_ROOMS, zone, x=3.5, y=1.5, adjacency_m=1.0)      # the dividing wall
    assert not touches_zone(TWO_ROOMS, zone, x=5.5, y=1.5, adjacency_m=1.0)  # in the other room


def test_point_outside_the_grid_is_safe():
    zone = flood_fill(TWO_ROOMS.cells, (1, 1))
    assert not touches_zone(TWO_ROOMS, zone, x=100.0, y=100.0, adjacency_m=1.0)


def test_compute_zone_separates_rooms_by_entrance():
    landmarks = [{'id': 1, 'x': 1.5, 'y': 1.5}, {'id': 2, 'x': 5.5, 'y': 1.5}]
    junctions = [{'id': 8, 'x': 2.5, 'y': 2.5}, {'id': 9, 'x': 4.5, 'y': 2.5}]
    left = compute_zone(TWO_ROOMS, 1.5, 1.5, landmarks, junctions)
    right = compute_zone(TWO_ROOMS, 5.5, 1.5, landmarks, junctions)
    assert left.landmark_ids == [1] and right.landmark_ids == [2]
    assert left.junction_ids == [8] and right.junction_ids == [9]
    assert left.area_m2 == 4.0


# ---- map files
def write_map(tmp_path, pixels: np.ndarray, negate: int = 0, comment: bool = True):
    header = b'P5\n' + (b'# CREATOR: map_saver\n' if comment else b'') + \
        f'{pixels.shape[1]} {pixels.shape[0]}\n255\n'.encode()
    (tmp_path / 'map.pgm').write_bytes(header + pixels.astype(np.uint8).tobytes())
    (tmp_path / 'map.yaml').write_text(
        f'image: map.pgm\nmode: trinary\nresolution: 0.05\norigin: [-1.0, -2.0, 0.0]\n'
        f'negate: {negate}\noccupied_thresh: 0.65\nfree_thresh: 0.25\n')
    return tmp_path / 'map.yaml'


def test_read_pgm_with_a_comment_in_the_header(tmp_path):
    write_map(tmp_path, np.array([[1, 2, 3], [4, 5, 6]]))
    assert read_pgm(tmp_path / 'map.pgm').tolist() == [[1, 2, 3], [4, 5, 6]]


def test_read_pgm_rejects_other_formats(tmp_path):
    (tmp_path / 'bad.pgm').write_bytes(b'P2\n1 1\n255\n0')
    with pytest.raises(ValueError, match='P5'):
        read_pgm(tmp_path / 'bad.pgm')


def test_load_map_applies_thresholds_and_flips_rows(tmp_path):
    # map_saver trinary output: 254 free, 0 occupied, 205 unknown. The image's top row is the highest y.
    path = write_map(tmp_path, np.array([[254, 0, 205], [254, 254, 254]]))
    grid = load_map(path)
    assert grid.cells.tolist() == [[FREE, FREE, FREE], [FREE, OCCUPIED, UNKNOWN]]
    assert grid.resolution == 0.05 and (grid.origin_x, grid.origin_y) == (-1.0, -2.0)


def test_world_and_cell_conversions_are_inverse():
    grid = GridMap(np.zeros((10, 10), dtype=np.int8), 0.05, -1.0, -2.0)
    assert grid.world_to_cell(-1.0 + 0.125, -2.0 + 0.275) == (5, 2)
    assert grid.cell_to_world(5, 2) == pytest.approx((-0.875, -1.725))


def test_saved_map_to_database_round_trip(tmp_path):
    # Two 1 m rooms at 0.05 m per cell, divided by a wall.
    pixels = np.full((40, 80), 0, dtype=np.uint8)
    pixels[5:35, 5:38] = 254
    pixels[5:35, 42:75] = 254
    path = write_map(tmp_path, pixels)
    database_path = tmp_path / 'merz.sqlite'
    with MerzDatabase(database_path) as database:
        database.upsert_landmark(1, 'door', 'M1', (-0.5, -1.0, 1.0))
        database.upsert_landmark(2, 'door', 'M2', (1.5, -1.0, 1.0))
        junction = database.add_junction(-0.5, -1.2)

    result = store_zone(path, database_path, 'east', 'East door', -0.5, -1.0)

    assert result.landmark_ids == [1] and result.junction_ids == [junction]
    with MerzDatabase(database_path) as database:
        assert database.connection.execute('SELECT name FROM entrances').fetchall() == [('East door',)]
        assert database.connection.execute('SELECT landmark_id FROM access_zones').fetchall() == [(1,)]

    # Recomputing offline must work, and update the existing entrance.
    assert store_zone(path, database_path, 'east', 'East entrance', -0.5, -1.0).landmark_ids == [1]
    with MerzDatabase(database_path) as database:
        assert database.connection.execute('SELECT name FROM entrances').fetchall() == [('East entrance',)]


# ---- junction rule
def scan_with_open_directions(*open_angles: float, open_range: float = 10.0, closed_range: float = 1.0):
    """A 360-degree scan with 1-degree steps, open over +/-40 degrees around each given angle."""
    angles = np.radians(np.arange(-180, 180))
    ranges = np.full(angles.size, closed_range)
    for centre in open_angles:
        offset = np.abs(np.arctan2(np.sin(angles - centre), np.cos(angles - centre)))
        ranges[offset <= math.radians(40)] = open_range
    return ranges, angles[0], math.radians(1)


def test_plain_corridor_has_two_open_sectors_and_is_not_a_junction():
    ranges, start, step = scan_with_open_directions(0.0, math.pi)
    sectors = open_sector_count(ranges, start, step, open_range_m=3.0)
    assert sectors == 2 and not is_junction(sectors)


def test_t_junction_and_crossroads():
    ranges, start, step = scan_with_open_directions(0.0, math.pi, math.pi / 2)
    assert open_sector_count(ranges, start, step, 3.0) == 3 and is_junction(3)
    ranges, start, step = scan_with_open_directions(0.0, math.pi, math.pi / 2, -math.pi / 2)
    assert open_sector_count(ranges, start, step, 3.0) == 4


def test_infinite_ranges_count_as_open_and_invalid_readings_do_not():
    ranges, start, step = scan_with_open_directions(0.0, math.pi, math.pi / 2, open_range=math.inf)
    assert open_sector_count(ranges, start, step, 3.0) == 3
    assert open_sector_count(np.full(360, np.nan), start, step, 3.0) == 0
    assert open_sector_count(np.zeros(360), start, step, 3.0) == 0


def test_laser_mounted_backwards_is_corrected_by_the_yaw_offset():
    # Open ahead only in the laser's own frame: rotated by pi it is behind the robot, still one open sector.
    ranges, start, step = scan_with_open_directions(0.0)
    assert open_sector_count(ranges, start, step, 3.0, yaw_offset=math.pi) == 1


def test_empty_scan_is_safe():
    assert open_sector_count([], 0.0, 0.1, 3.0) == 0


# ---- junction graph
def test_each_junction_is_recorded_once_and_edges_use_distance_driven():
    tracker = JunctionTracker(min_spacing_m=3.0)
    assert tracker.arrive(0.0, 0.0) == (0, True, None)
    assert tracker.arrive(0.5, 0.0) == (0, False, None)          # still at the same junction
    for x in (2.0, 4.0, 6.0, 8.0):
        tracker.update_pose(x, 0.0)
    tracker.update_pose(8.0, 2.0)                                # the corridor bends: path 8 + 2 m, line 8.2 m
    index, is_new, edge = tracker.arrive(8.0, 2.0)
    assert (index, is_new) == (1, True)
    assert edge[0] == 0 and edge[1] == pytest.approx(8.0)


def test_returning_to_a_known_junction_closes_a_loop():
    tracker = JunctionTracker(min_spacing_m=3.0)
    tracker.arrive(0.0, 0.0)
    tracker.update_pose(0.0, 0.0)
    tracker.update_pose(10.0, 0.0)
    tracker.arrive(10.0, 0.0)
    tracker.update_pose(0.0, 0.0)
    index, is_new, edge = tracker.arrive(0.0, 0.0)
    assert index == 0 and not is_new
    assert edge == (1, pytest.approx(10.0))


# ---- mission end
def monitor() -> MissionMonitor:
    instance = MissionMonitor(max_duration_s=100.0, no_frontier_timeout_s=10.0, startup_grace_s=5.0)
    instance.start(0.0)
    return instance


def test_no_end_while_frontiers_keep_appearing():
    instance = monitor()
    for time_s in range(0, 50, 5):
        instance.frontiers_seen(2, float(time_s))
        assert instance.check(float(time_s)) is None


def test_ends_once_frontiers_stop():
    instance = monitor()
    instance.frontiers_seen(1, 20.0)
    assert instance.check(29.0) is None
    assert instance.check(30.0) is EndReason.NO_FRONTIERS


def test_empty_frontier_reports_do_not_reset_the_timer():
    instance = monitor()
    instance.frontiers_seen(1, 20.0)
    instance.frontiers_seen(0, 29.0)
    assert instance.check(30.0) is EndReason.NO_FRONTIERS


def test_time_cap_wins_even_with_frontiers_remaining():
    instance = monitor()
    instance.frontiers_seen(5, 99.9)
    assert instance.check(100.0) is EndReason.TIME_CAP


def test_startup_grace_stops_an_early_end():
    instance = MissionMonitor(max_duration_s=100.0, no_frontier_timeout_s=1.0, startup_grace_s=20.0)
    instance.start(0.0)
    assert instance.check(19.0) is None
    assert instance.check(20.0) is EndReason.NO_FRONTIERS


def test_operator_can_finish_at_any_time():
    instance = monitor()
    instance.request_finish()
    assert instance.check(0.1) is EndReason.OPERATOR
