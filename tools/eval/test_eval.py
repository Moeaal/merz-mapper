"""Evaluation scripts on synthetic data with known answers. No ROS needed."""
from pathlib import Path
import sqlite3
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'ros2_ws' / 'src' / 'merz_semantic_map'))

import access_zone_compare  # noqa: E402
import common  # noqa: E402
from common import FREE, OCCUPIED, GridMap  # noqa: E402
import fusion_compare  # noqa: E402
import landmark_error  # noqa: E402
import map_coverage  # noqa: E402
from merz_semantic_map.database import MerzDatabase  # noqa: E402
import ocr_rate  # noqa: E402
import route_timing  # noqa: E402
import wall_error  # noqa: E402

SQUARE_10M = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]])


# ---- statistics
def test_describe_matches_hand_calculation():
    stats = common.describe([1.0, 2.0, 3.0])
    assert stats.mean == 2.0 and stats.sd == 1.0 and stats.maximum == 3.0
    assert stats.rmse == pytest.approx(np.sqrt(14 / 3))
    assert stats.ci95 == pytest.approx(4.303 / np.sqrt(3))     # t with 2 degrees of freedom


def test_describe_single_value_has_no_interval_and_empty_is_an_error():
    assert np.isnan(common.describe([1.0]).ci95)
    with pytest.raises(ValueError):
        common.describe([])


def test_large_sample_uses_the_normal_value():
    assert common.describe(range(100)).ci95 == pytest.approx(1.96 * np.std(range(100), ddof=1) / 10)


def test_format_table_aligns_columns():
    lines = common.format_table(['a', 'long'], [['xyz', 1.5]]).splitlines()
    assert lines[0].index('long') == lines[2].index('1.500')


def test_database_is_opened_read_only(tmp_path):
    path = tmp_path / 'merz.sqlite'
    MerzDatabase(path).close()
    with pytest.raises(sqlite3.OperationalError):
        common.query_database(path, "INSERT INTO meta VALUES ('a', 'b')")


# ---- O2 coverage
def test_polygon_test_with_a_concave_shape():
    u_shape = np.array([[0, 0], [3, 0], [3, 3], [2, 3], [2, 1], [1, 1], [1, 3], [0, 3]], dtype=float)
    x = np.array([0.5, 1.5, 2.5, 1.5, 4.0])
    y = np.array([2.0, 2.0, 2.0, 0.5, 0.5])
    assert map_coverage.points_in_polygon(x, y, u_shape).tolist() == [True, False, True, True, False]


def test_half_free_map_gives_50_percent():
    cells = np.full((100, 100), OCCUPIED, dtype=np.int8)
    cells[:, :50] = FREE
    result = map_coverage.coverage(GridMap(cells, 0.1, 0.0, 0.0), SQUARE_10M)
    assert result.polygon_area_m2 == pytest.approx(100.0)
    assert result.percent == pytest.approx(50.0)


def test_polygon_beyond_the_map_lowers_coverage():
    grid = GridMap(np.full((50, 100), FREE, dtype=np.int8), 0.1, 0.0, 0.0)     # the map stops at y = 5 m
    assert map_coverage.coverage(grid, SQUARE_10M).percent == pytest.approx(50.0)


# ---- O2 walls
def test_point_to_segment_distances():
    segments = np.array([[0.0, 0.0, 10.0, 0.0]])
    points = np.array([[5.0, 2.0], [-3.0, 4.0], [13.0, 4.0], [5.0, 0.0]])
    assert wall_error.distances_to_segments(points, segments).tolist() == pytest.approx([2.0, 5.0, 5.0, 0.0])


def test_nearest_of_several_segments_is_used():
    segments = np.array([[0.0, 0.0, 10.0, 0.0], [0.0, 3.0, 10.0, 3.0]])
    assert wall_error.distances_to_segments(np.array([[5.0, 2.0]]), segments)[0] == pytest.approx(1.0)


def test_known_wall_offset_and_exclusion_of_furniture():
    cells = np.full((100, 100), FREE, dtype=np.int8)
    cells[12, :] = OCCUPIED     # a mapped wall with its centre at y = 1.25 m
    cells[70, 50] = OCCUPIED    # furniture, far from the plan
    grid = GridMap(cells, 0.1, 0.0, 0.0)
    errors, excluded = wall_error.wall_errors(grid, np.array([[0.0, 1.0, 10.0, 1.0]]), match_radius_m=0.5)
    assert errors.size == 100 and errors.mean() == pytest.approx(0.25)
    assert excluded == pytest.approx(100 * 1 / 101)


def test_map_without_walls_is_an_error():
    with pytest.raises(ValueError, match='no occupied'):
        wall_error.wall_errors(GridMap(np.zeros((5, 5), np.int8), 0.1, 0, 0), np.array([[0.0, 0, 1, 0]]), 0.5)


# ---- O3
def test_read_rate_counts_each_sign_once_and_reports_false_reads():
    result = ocr_rate.score(['M2.14', 'M2.15', 'M2.16', 'M2.17'], ['m2.14', 'M2.14', 'M 2.15', 'M9.99', ''])
    assert result.percent == 50.0
    assert result.correct == {'M2.14', 'M2.15'}
    assert result.missed == {'M2.16', 'M2.17'}
    assert result.false_reads == {'M9.99'}


# ---- O4
def lm(id_, cls, text, x, y):
    return {'id': id_, 'class': cls, 'text': text, 'x': x, 'y': y, 'z': 1.0, 'observation_count': 3}


def truth(cls, text, x, y):
    return {'class': cls, 'text': text, 'x': str(x), 'y': str(y)}


def test_text_match_finds_the_named_sign_not_the_nearest():
    landmarks = [lm(1, 'room_sign', 'A', 0.1, 0), lm(2, 'room_sign', 'B', 1.0, 0)]
    matches, unmatched = landmark_error.match_landmarks([truth('room_sign', 'B', 0.0, 0.0)], landmarks, 2.0)
    assert matches[0].landmark['id'] == 2 and matches[0].error_m == pytest.approx(1.0)
    assert not unmatched


def test_no_landmark_is_matched_twice():
    matches, unmatched = landmark_error.match_landmarks(
        [truth('door', '', 0, 0), truth('door', '', 0.2, 0)], [lm(1, 'door', '', 0.1, 0)], 2.0)
    assert len(matches) == 1 and len(unmatched) == 1


def test_landmark_beyond_the_gate_is_reported_as_unmatched():
    matches, unmatched = landmark_error.match_landmarks([truth('lift', '', 0, 0)], [lm(1, 'lift', '', 5, 0)], 2.0)
    assert not matches and len(unmatched) == 1


def test_error_is_horizontal_only():
    matches, _ = landmark_error.match_landmarks([truth('lift', '', 0, 0)], [lm(1, 'lift', '', 3, 4)], 10.0)
    assert matches[0].error_m == pytest.approx(5.0)


# ---- O8
def test_paired_errors_use_the_first_observation_and_the_mean():
    observations = [
        {'id': 2, 'landmark_id': 1, 'x': 0.0, 'y': -1.0, 'stamp': 2.0},
        {'id': 1, 'landmark_id': 1, 'x': 0.0, 'y': 1.0, 'stamp': 1.0},   # the earliest, though stored later
    ]
    pairs = fusion_compare.paired_errors([truth('door', '', 0, 0)], [lm(1, 'door', '', 0, 0)], observations, 2.0)
    assert pairs[0].single_m == pytest.approx(1.0) and pairs[0].fused_m == pytest.approx(0.0)


def test_landmarks_with_too_few_observations_are_left_out():
    observations = [{'id': 1, 'landmark_id': 1, 'x': 0.0, 'y': 1.0, 'stamp': 1.0}]
    assert fusion_compare.paired_errors([truth('door', '', 0, 0)], [lm(1, 'door', '', 0, 0)], observations, 2.0) == []


# ---- O5
def test_zone_comparison_splits_every_case():
    survey = [{'entrance': 'e', 'room': room, 'reachable': answer}
              for room, answer in [('a', 'yes'), ('b', 'no'), ('c', 'no'), ('d', 'Yes')]]
    result = access_zone_compare.compare(survey, {('e', 'a'), ('e', 'c')})
    assert (result.both_yes, result.both_no) == (1, 1)
    assert result.extra == [('e', 'c')] and result.missing == [('e', 'd')]
    assert result.agreement_percent == 50.0


# ---- O6 and O7
def test_measure_reports_routes_and_times():
    def fake_query(entrance, room):
        return {'steps': [{'junction_id': 1}, {'junction_id': 2}]}

    routes = [{'entrance': 'e', 'room': 'a', 'expected': '1 2'}, {'entrance': 'e', 'room': 'b', 'expected': '1 3'},
              {'entrance': 'e', 'room': 'c', 'expected': ''}]
    results = route_timing.measure(routes, fake_query, repeats=3)
    assert [r.correct for r in results] == [True, False, None]
    assert all(len(r.times_s) == 3 for r in results)


# ---- plots
def test_all_plots_are_written(tmp_path):
    pytest.importorskip('matplotlib')
    rng = np.random.default_rng(0)
    cells = np.full((100, 100), FREE, dtype=np.int8)
    cells[10, :] = OCCUPIED
    cells[85:, :] = -1
    outputs = {
        'coverage.png': lambda p: map_coverage.plot(GridMap(cells, 0.1, 0, 0), SQUARE_10M * 0.8, p),
        'wall.png': lambda p: wall_error.plot(np.abs(rng.normal(0.08, 0.04, 500)), p),
        'landmarks.png': lambda p: landmark_error.plot(list(np.abs(rng.normal(0.3, 0.15, 25))), p),
        'fusion.png': lambda p: fusion_compare.plot(
            [fusion_compare.PairedError(i, abs(rng.normal(0.5, .2)), abs(rng.normal(.3, .1))) for i in range(12)], p),
        'times.png': lambda p: route_timing.plot(list(rng.normal(5, 1, 200)), p),
    }
    for name, draw in outputs.items():
        draw(tmp_path / name)
        assert (tmp_path / name).stat().st_size > 1000
