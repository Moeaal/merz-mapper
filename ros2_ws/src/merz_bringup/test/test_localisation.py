"""Check the scan odometry covariance logic and the EKF/SLAM configuration rules. No ROS needed."""
from pathlib import Path

import pytest
import yaml

from merz_bringup.odom_covariance import (COVARIANCE_SIZE, ScanOdomNoise, is_plausible, pose_covariance,
                                          twist_covariance)

PACKAGE = Path(__file__).resolve().parents[1]
NOISE = ScanOdomNoise(vx_std=0.05, vy_std=0.02, vyaw_std=0.1, max_speed=1.5, max_yaw_rate=3.0)

VX, VY, VYAW = 6, 7, 11


def params(name: str, node: str) -> dict:
    return yaml.safe_load((PACKAGE / 'config' / name).read_text())[node]['ros__parameters']


def test_twist_covariance_has_variances_on_the_right_diagonal():
    covariance = twist_covariance(NOISE)
    assert len(covariance) == COVARIANCE_SIZE
    assert covariance[0] == pytest.approx(0.05 ** 2)
    assert covariance[7] == pytest.approx(0.02 ** 2)
    assert covariance[35] == pytest.approx(0.1 ** 2)


def test_no_diagonal_is_zero_because_the_ekf_would_read_that_as_a_perfect_measurement():
    for covariance in (twist_covariance(NOISE), pose_covariance()):
        assert all(covariance[i] > 0 for i in range(0, COVARIANCE_SIZE, 7))


def test_off_diagonals_are_zero():
    covariance = twist_covariance(NOISE)
    assert all(covariance[i] == 0 for i in range(COVARIANCE_SIZE) if i % 7 != 0)


@pytest.mark.parametrize('vx, vy, vyaw, expected', [
    (0.5, 0.0, 0.5, True),
    (1.5, 0.0, 0.0, True),
    (1.6, 0.0, 0.0, False),
    (0.0, 0.0, -3.5, False),
    (1.2, 1.2, 0.0, False),   # the magnitude matters, not each axis
])
def test_plausibility_gate(vx, vy, vyaw, expected):
    assert is_plausible(vx, vy, vyaw, NOISE) is expected


def test_ekf_owns_odom_to_base_link_and_rf2o_does_not():
    ekf = params('ekf.yaml', 'ekf_filter_node')
    assert ekf['publish_tf'] is True and ekf['world_frame'] == 'odom' and ekf['two_d_mode'] is True
    assert params('scan_odometry.yaml', 'rf2o_laser_odometry')['publish_tf'] is False


def test_ekf_fuses_scan_velocity_and_only_gyro_yaw_rate():
    ekf = params('ekf.yaml', 'ekf_filter_node')
    assert ekf['odom0'] == '/odom_scan'
    assert [i for i, on in enumerate(ekf['odom0_config']) if on] == [VX, VY]
    assert [i for i, on in enumerate(ekf['imu0_config']) if on] == [VYAW]


def test_ekf_process_noise_is_15_by_15():
    assert len(params('ekf.yaml', 'ekf_filter_node')['process_noise_covariance']) == 15 * 15


def test_wheel_odometry_is_not_in_the_default_ekf_config():
    ekf = params('ekf.yaml', 'ekf_filter_node')
    assert 'odom1' not in ekf
    wheel = params('ekf_wheel_odom.yaml', 'ekf_filter_node')
    assert [i for i, on in enumerate(wheel['odom1_config']) if on] == [VX]


def test_slam_uses_the_project_frames():
    slam = params('slam.yaml', 'slam_toolbox')
    assert (slam['odom_frame'], slam['map_frame'], slam['base_frame']) == ('odom', 'map', 'base_link')
    assert slam['do_loop_closing'] is True
    assert slam['max_laser_range'] < 30.0
