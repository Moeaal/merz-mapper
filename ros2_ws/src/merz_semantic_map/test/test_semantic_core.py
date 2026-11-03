"""Landmark geometry and database tests using synthetic data with known answers. No ROS needed."""
import math
import sqlite3

import numpy as np
import pytest

from merz_semantic_map.database import MerzDatabase
from merz_semantic_map.geometry import (BoundingBox, Intrinsics, apply_transform, deproject, inverse_transform,
                                        median_depth_in_box, project, transform_matrix)
from merz_semantic_map.localiser import FUSED, SINGLE_OBSERVATION, LandmarkMap, LocaliserConfig, locate_in_map

K = Intrinsics(fx=400.0, fy=400.0, cx=320.0, cy=240.0)
CONFIG = LocaliserConfig()
ONE_CM = 0.01
IDENTITY = np.eye(4)
# The optical frame relative to a level, forward-facing camera body: z forward, x right, y down (REP 103).
BODY_FROM_OPTICAL = transform_matrix((0, 0, 0), (-0.5, 0.5, -0.5, 0.5))


def depth_image(value: float = 2.0) -> np.ndarray:
    return np.full((480, 640), value, dtype=np.float32)


def box_around(u: float, v: float, half: float = 10.0) -> BoundingBox:
    return BoundingBox(u - half, v - half, u + half, v + half)


def yaw_matrix(yaw: float, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> np.ndarray:
    return transform_matrix((x, y, z), (0.0, 0.0, math.sin(yaw / 2), math.cos(yaw / 2)))


# ---- geometry
def test_deproject_centre_pixel_is_straight_ahead():
    assert deproject(320, 240, 2.0, K) == pytest.approx([0, 0, 2.0])


def test_deproject_off_centre_pixel():
    assert deproject(420, 140, 2.0, K) == pytest.approx([0.5, -0.5, 2.0])


def test_project_is_the_inverse_of_deproject():
    point = deproject(100, 300, 3.3, K)
    assert project(point, K) == pytest.approx((100, 300))


def test_project_behind_camera_is_none():
    assert project(np.array([0.0, 0.0, -1.0]), K) is None


def test_quaternion_matches_a_known_rotation():
    # Rotating +x by 90 degrees about z must give +y.
    assert apply_transform(yaw_matrix(math.pi / 2), np.array([1.0, 0, 0])) == pytest.approx([0, 1, 0], abs=1e-12)


def test_optical_frame_convention():
    # Straight ahead of the camera in its optical frame (+z) is +x in the body frame.
    assert apply_transform(BODY_FROM_OPTICAL, np.array([0, 0, 1.0])) == pytest.approx([1, 0, 0], abs=1e-12)
    # The right of the image (+x optical) is -y in the body frame, since +y is left.
    assert apply_transform(BODY_FROM_OPTICAL, np.array([1.0, 0, 0])) == pytest.approx([0, -1, 0], abs=1e-12)


def test_inverse_transform_undoes_transform():
    matrix = yaw_matrix(0.7, 1.0, -2.0, 0.5)
    point = np.array([0.3, 0.4, 0.5])
    assert apply_transform(inverse_transform(matrix), apply_transform(matrix, point)) == pytest.approx(point)


# ---- median depth
def test_median_ignores_invalid_pixels_and_outliers():
    depth = depth_image(2.0)
    depth[235:240, 315:320] = 0.0          # no reading
    depth[240:243, 320:323] = np.nan       # no reading
    depth[243:245, 323:325] = 50.0         # outlier
    assert median_depth_in_box(depth, box_around(320, 240)) == pytest.approx(2.0)


def test_median_uses_the_central_part_so_the_wall_behind_is_ignored():
    depth = depth_image(5.0)               # the wall behind
    depth[230:251, 310:331] = 2.0          # the object fills only the middle of a larger box
    assert median_depth_in_box(depth, box_around(320, 240, half=20)) == pytest.approx(2.0)


def test_median_none_when_nothing_is_valid_or_the_box_is_outside():
    assert median_depth_in_box(depth_image(0.0), box_around(320, 240)) is None
    assert median_depth_in_box(depth_image(), BoundingBox(900, 900, 950, 950)) is None


# ---- locating in the map: positions to within 1 cm
def test_locate_with_identity_pose():
    position = locate_in_map(box_around(420, 140), depth_image(2.0), K, IDENTITY, CONFIG)
    assert np.linalg.norm(position - [0.5, -0.5, 2.0]) < ONE_CM


def test_locate_with_translated_and_rotated_robot():
    # The robot is at (3, 4, 0), facing +y (yaw 90 degrees). The camera is 0.2 m ahead of it and 1 m up.
    # A sign straight ahead at 2 m depth must therefore be at (3, 4 + 0.2 + 2, 1).
    map_from_base = yaw_matrix(math.pi / 2, 3.0, 4.0)
    base_from_camera = transform_matrix((0.2, 0.0, 1.0), (0, 0, 0, 1))
    map_from_optical = map_from_base @ base_from_camera @ BODY_FROM_OPTICAL

    position = locate_in_map(box_around(320, 240), depth_image(2.0), K, map_from_optical, CONFIG)

    assert np.linalg.norm(position - [3.0, 6.2, 1.0]) < ONE_CM


def test_full_round_trip_recovers_a_known_landmark_from_many_views():
    truth = np.array([5.0, 2.0, 1.2])
    landmarks = LandmarkMap(CONFIG)
    for robot_x, robot_y, yaw in [(2.0, 2.0, 0.0), (3.0, 1.0, 0.7), (4.0, 3.5, -1.0), (3.5, 2.0, 0.1)]:
        map_from_optical = yaw_matrix(yaw, robot_x, robot_y, 1.0) @ BODY_FROM_OPTICAL
        pixel = project(apply_transform(inverse_transform(map_from_optical), truth), K)
        depth = apply_transform(inverse_transform(map_from_optical), truth)[2]
        position = locate_in_map(box_around(*pixel), depth_image(depth), K, map_from_optical, CONFIG)
        landmarks.add_observation('room_sign', position, 0.9, 0.0)

    assert len(landmarks.landmarks) == 1
    assert np.linalg.norm(landmarks.landmarks[0].position - truth) < ONE_CM


@pytest.mark.parametrize('depth', [0.3, 0.59, 6.01, 20.0])
def test_depth_outside_the_trusted_range_is_rejected(depth):
    assert locate_in_map(box_around(320, 240), depth_image(depth), K, IDENTITY, CONFIG) is None


@pytest.mark.parametrize('depth', [0.6, 6.0])
def test_depth_at_the_limits_is_accepted(depth):
    assert locate_in_map(box_around(320, 240), depth_image(depth), K, IDENTITY, CONFIG) is not None


# ---- association and fusion
def test_same_class_within_the_gate_merges_and_averages():
    landmarks = LandmarkMap(CONFIG)
    landmarks.add_observation('door', np.array([1.0, 0, 0]), 0.5, 1.0)
    landmark, is_new = landmarks.add_observation('door', np.array([1.2, 0, 0]), 0.9, 2.0)
    assert not is_new and len(landmarks.landmarks) == 1
    assert landmark.position == pytest.approx([1.1, 0, 0])
    assert landmark.count == 2 and landmark.confidence == 0.9
    assert (landmark.first_seen_s, landmark.last_seen_s) == (1.0, 2.0)


def test_beyond_the_gate_makes_a_new_landmark():
    landmarks = LandmarkMap(CONFIG)
    landmarks.add_observation('door', np.array([0.0, 0, 0]), 0.5, 0.0)
    assert landmarks.add_observation('door', np.array([1.5, 0, 0]), 0.5, 0.0)[1] is True


def test_different_classes_never_merge():
    landmarks = LandmarkMap(CONFIG)
    landmarks.add_observation('door', np.zeros(3), 0.5, 0.0)
    landmarks.add_observation('lift', np.zeros(3), 0.5, 0.0)
    assert len(landmarks.landmarks) == 2


def test_nearest_landmark_wins_when_two_are_in_the_gate():
    landmarks = LandmarkMap(CONFIG)
    first, _ = landmarks.add_observation('door', np.array([0.0, 0, 0]), 0.5, 0.0)
    landmarks.config = LocaliserConfig(gate_m=0.5)
    second, _ = landmarks.add_observation('door', np.array([0.9, 0, 0]), 0.5, 0.0)
    landmarks.config = LocaliserConfig(gate_m=2.0)
    chosen, _ = landmarks.add_observation('door', np.array([0.8, 0, 0]), 0.5, 0.0)
    assert chosen is second and first.count == 1


def test_running_mean_and_covariance_match_numpy():
    rng = np.random.default_rng(3)
    points = rng.normal([1.0, 2.0, 0.5], 0.05, (50, 3))
    landmarks = LandmarkMap(CONFIG)
    for point in points:
        landmarks.add_observation('door', point, 0.5, 0.0)
    landmark = landmarks.landmarks[0]
    assert landmark.position == pytest.approx(points.mean(axis=0))
    assert landmark.covariance == pytest.approx(np.cov(points.T))


def test_averaging_reduces_error_in_fused_mode_compared_to_single():
    rng = np.random.default_rng(7)
    truth = np.array([2.0, 1.0, 0.5])
    points = truth + rng.normal(0, 0.1, (100, 3))
    fused, single = LandmarkMap(LocaliserConfig(fusion_mode=FUSED)), LandmarkMap(
        LocaliserConfig(fusion_mode=SINGLE_OBSERVATION))
    for point in points:
        fused.add_observation('door', point, 0.5, 0.0)
        single.add_observation('door', point, 0.5, 0.0)
    assert single.landmarks[0].position == pytest.approx(points[0])
    assert single.landmarks[0].count == 100
    assert np.linalg.norm(fused.landmarks[0].position - truth) < np.linalg.norm(points[0] - truth)


def test_unknown_fusion_mode_is_rejected():
    with pytest.raises(ValueError, match='fusion_mode'):
        LocaliserConfig(fusion_mode='magic')


# ---- attaching text
def _sign_map() -> LandmarkMap:
    landmarks = LandmarkMap(LocaliserConfig(gate_m=0.5))   # below the 1 m spacing, so the two signs stay separate
    landmarks.add_observation('room_sign', np.array([0.0, 0.0, 3.0]), 0.9, 0.0)     # straight ahead: pixel (320, 240)
    landmarks.add_observation('room_sign', np.array([1.0, 0.0, 3.0]), 0.9, 0.0)     # to the right: pixel about (453, 240)
    landmarks.add_observation('door', np.array([0.0, 0.1, 3.0]), 0.9, 0.0)
    return landmarks


def test_text_goes_to_the_sign_that_projects_into_the_box():
    landmarks = _sign_map()
    chosen = landmarks.attach_text('M2.14', box_around(453, 240), K, IDENTITY)
    assert chosen is landmarks.landmarks[1] and chosen.text == 'M2.14'
    assert landmarks.landmarks[0].text == ''


def test_text_is_not_attached_when_no_sign_is_in_the_box():
    landmarks = _sign_map()
    assert landmarks.attach_text('M2.14', box_around(50, 50), K, IDENTITY) is None
    assert all(lm.text == '' for lm in landmarks.landmarks)


def test_nearest_sign_to_the_box_centre_wins_when_two_are_inside():
    landmarks = _sign_map()
    chosen = landmarks.attach_text('M2.14', BoundingBox(300, 200, 480, 280), K, IDENTITY)
    assert chosen is landmarks.landmarks[1]      # centre u=390: closer to 453 (63 px) than 320 (70 px)


def test_text_is_never_attached_to_a_non_sign():
    landmarks = LandmarkMap(CONFIG)
    landmarks.add_observation('door', np.array([0.0, 0.0, 3.0]), 0.9, 0.0)
    assert landmarks.attach_text('M2.14', box_around(320, 240), K, IDENTITY) is None


# ---- database
def test_landmark_round_trip_and_update(tmp_path):
    with MerzDatabase(tmp_path / 'sub' / 'merz.sqlite') as database:
        database.upsert_landmark(1, 'door', '', (1.0, 2.0, 0.5), confidence=0.5)
        database.upsert_landmark(1, 'door', 'M2.14', (1.1, 2.1, 0.5), confidence=0.9, observation_count=4)
        rows = database.landmarks()
    assert len(rows) == 1
    assert rows[0]['text'] == 'M2.14' and rows[0]['x'] == 1.1 and rows[0]['observation_count'] == 4


def test_database_persists_and_next_id_continues(tmp_path):
    path = tmp_path / 'merz.sqlite'
    with MerzDatabase(path) as database:
        assert database.next_landmark_id() == 1
        database.upsert_landmark(7, 'lift', '', (0, 0, 0))
    with MerzDatabase(path) as database:
        assert database.next_landmark_id() == 8
        assert database.landmarks()[0]['class'] == 'lift'


def test_access_zone_is_replaced_not_appended(tmp_path):
    with MerzDatabase(tmp_path / 'merz.sqlite') as database:
        database.upsert_entrance('east', 'East door', 0, 0)
        database.upsert_landmark(1, 'door', '', (0, 0, 0))
        database.upsert_landmark(2, 'door', '', (1, 0, 0))
        database.set_access_zone('east', [1, 2])
        database.set_access_zone('east', [2])
        rows = database.connection.execute('SELECT landmark_id FROM access_zones').fetchall()
    assert rows == [(2,)]


def test_foreign_keys_are_enforced(tmp_path):
    with MerzDatabase(tmp_path / 'merz.sqlite') as database:
        with pytest.raises(sqlite3.IntegrityError):
            database.add_observation(999, (0, 0, 0))


def test_a_later_run_updates_stored_landmarks_instead_of_duplicating_them(tmp_path):
    with MerzDatabase(tmp_path / 'merz.sqlite') as database:
        database.upsert_landmark(5, 'door', 'M2.14', (1.0, 0.0, 0.0), (0.04, 0.0, 0.0), 0.8, observation_count=3)
        rows = database.landmarks()

    landmarks = LandmarkMap(CONFIG)
    landmarks.restore(rows)
    same, is_new = landmarks.add_observation('door', np.array([1.4, 0.0, 0.0]), 0.5, 9.0)
    other, other_new = landmarks.add_observation('door', np.array([9.0, 0.0, 0.0]), 0.5, 9.0)

    assert same.landmark_id == 5 and not is_new and same.text == 'M2.14'
    assert same.position == pytest.approx([1.1, 0.0, 0.0])    # (3 * 1.0 + 1.4) / 4
    assert other_new and other.landmark_id == 6


def test_junction_edge_stored_once_in_either_order(tmp_path):
    with MerzDatabase(tmp_path / 'merz.sqlite') as database:
        a, b = database.add_junction(0, 0), database.add_junction(3, 4)
        database.add_junction_edge(b, a, 5.0)
        database.add_junction_edge(a, b, 5.5)
        database.add_junction_edge(a, a, 1.0)
        rows = database.connection.execute('SELECT a, b, length_m FROM junction_edges').fetchall()
    assert rows == [(a, b, 5.5)]
