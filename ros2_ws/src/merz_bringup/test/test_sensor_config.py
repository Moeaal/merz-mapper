"""Check the safety and consistency rules in the sensor and teleop YAML. No ROS needed."""
from pathlib import Path

import yaml

PACKAGE = Path(__file__).resolve().parents[1]


def load(name: str) -> dict:
    return yaml.safe_load((PACKAGE / 'config' / name).read_text())


def test_teleop_outranks_navigation():
    topics = load('twist_mux.yaml')['twist_mux']['ros__parameters']['topics']
    assert topics['teleop']['priority'] > topics['navigation']['priority']
    assert topics['navigation']['topic'] == 'cmd_vel'


def test_mux_inputs_time_out_quickly_so_a_dead_publisher_cannot_keep_the_robot_moving():
    topics = load('twist_mux.yaml')['twist_mux']['ros__parameters']['topics']
    assert all(0 < t['timeout'] <= 1.0 for t in topics.values())


def test_deadman_is_required_and_there_is_no_turbo():
    params = load('teleop.yaml')['teleop_node']['ros__parameters']
    assert params['require_enable_button'] is True
    assert params['enable_turbo_button'] == -1


def test_teleop_speed_is_below_the_spec_limit():
    params = load('teleop.yaml')['teleop_node']['ros__parameters']
    assert params['scale_linear']['x'] <= 0.5


def test_d455_publishes_one_united_imu_topic():
    params = load('d455.yaml')['/**']['ros__parameters']
    assert params['enable_gyro'] and params['enable_accel']
    assert params['unite_imu_method'] == 2


def test_camera_info_name_matches_the_driver_name():
    assert load('c920_camera_info.yaml')['camera_name'] == load('c920.yaml')['/**']['ros__parameters']['camera_name']


def test_each_device_has_its_own_udev_rules_file():
    names = {p.name for p in (PACKAGE / 'udev').glob('*.rules')}
    assert names == {'99-merz-rplidar.rules', '99-merz-c920.rules', '99-merz-d455.rules', '99-merz-gamepad.rules'}


def test_driver_device_paths_match_the_udev_symlinks():
    for lidar in ('lidar_c1.yaml', 'lidar_s2.yaml'):
        assert load(lidar)['/**']['ros__parameters']['serial_port'] == '/dev/rplidar'
    assert 'SYMLINK+="rplidar"' in (PACKAGE / 'udev' / '99-merz-rplidar.rules').read_text()
    assert load('c920.yaml')['/**']['ros__parameters']['video_device'] == '/dev/c920'
    assert 'SYMLINK+="c920"' in (PACKAGE / 'udev' / '99-merz-c920.rules').read_text()


def test_each_lidar_uses_its_own_driver_settings():
    """Values from sllidar_ros2's own sllidar_c1_launch.py and sllidar_s2_launch.py (decisions #33)."""
    c1 = load('lidar_c1.yaml')['/**']['ros__parameters']
    s2 = load('lidar_s2.yaml')['/**']['ros__parameters']
    assert (c1['serial_baudrate'], c1['scan_mode']) == (460800, 'Standard')
    assert (s2['serial_baudrate'], s2['scan_mode']) == (1000000, 'DenseBoost')
    assert c1['frame_id'] == s2['frame_id'] == 'laser'


def test_lidar_launch_offers_one_config_per_model():
    text = (PACKAGE / 'launch' / 'lidar.launch.py').read_text()
    assert "choices=['c1', 's2']" in text
    assert 'lidar_c1.yaml' in text and 'lidar_s2.yaml' in text
