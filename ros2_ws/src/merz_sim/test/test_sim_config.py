"""The simulated rover against the real stack's files: same frames, same sensor poses, inside the Nav2 footprint,
within the 0.5 m/s limit, and the mode (b) estimator never reads simulator ground truth."""
import ast
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
import yaml

xacro = pytest.importorskip('xacro')

PACKAGE = Path(__file__).resolve().parents[1]
SRC = PACKAGE.parent
ROVER = yaml.safe_load((PACKAGE / 'config' / 'sim_rover.yaml').read_text())
POSES = yaml.safe_load((SRC / 'merz_description' / 'config' / 'sensor_poses.yaml').read_text())
NAV2 = yaml.safe_load((SRC / 'merz_bringup' / 'config' / 'nav2.yaml').read_text())
EKF = yaml.safe_load((SRC / 'merz_bringup' / 'config' / 'ekf.yaml').read_text())['ekf_filter_node']['ros__parameters']
LAUNCH = (PACKAGE / 'launch' / 'sim.launch.py').read_text()


def expand(gz='fortress', cameras=True) -> ET.Element:
    doc = xacro.process_file(str(PACKAGE / 'urdf' / 'merz_sim_rover.urdf.xacro'), mappings={
        'rover_file': str(PACKAGE / 'config' / 'sim_rover.yaml'), 'gz_version': gz, 'cameras': str(cameras).lower()})
    return ET.fromstring(doc.toxml())


def parents(root):
    return {j.find('child').get('link'): j.find('parent').get('link') for j in root.findall('joint')}


def joint_xyz(root, child):
    joint = next(j for j in root.findall('joint') if j.find('child').get('link') == child)
    return [float(v) for v in joint.find('origin').get('xyz').split()]


def sensors(root):
    return {s.get('name'): s for s in root.iter('sensor')}


@pytest.mark.parametrize('gz', ['fortress', 'harmonic'])
@pytest.mark.parametrize('cameras', [True, False])
def test_xacro_expands_with_the_real_frame_names(gz, cameras):
    tree = parents(expand(gz, cameras))
    assert 'base_link' not in tree   # the root, on the floor
    for frame in ('laser', 'camera_link', 'sign_camera'):
        assert tree[frame] == 'base_link'
    for frame in ('camera_color_optical_frame', 'camera_depth_optical_frame', 'camera_imu_optical_frame'):
        assert tree[frame] == 'camera_link'
    assert tree['sign_camera_optical_frame'] == 'sign_camera'


def test_an_unknown_gazebo_version_fails_the_expansion():
    with pytest.raises(Exception):
        expand('garden')


@pytest.mark.parametrize('gz, tag, other', [('fortress', 'ignition_frame_id', 'gz_frame_id'),
                                            ('harmonic', 'gz_frame_id', 'ignition_frame_id')])
def test_version_specific_tags(gz, tag, other):
    root = expand(gz)
    for sensor in sensors(root).values():
        assert sensor.find(tag) is not None and sensor.find(other) is None
    prefix = 'ignition-gazebo-' if gz == 'fortress' else 'gz-sim-'
    assert all(p.get('filename').startswith(prefix) for p in root.iter('plugin'))


def test_sensor_frames_and_topics():
    s = sensors(expand())
    assert s['rplidar_s2'].findtext('ignition_frame_id') == 'laser'
    assert s['rplidar_s2'].findtext('topic') == '/scan'
    assert s['d455_imu'].findtext('ignition_frame_id') == 'camera_imu_optical_frame'
    assert s['d455_imu'].findtext('topic') == '/camera/camera/imu'
    assert s['d455_rgbd'].findtext('ignition_frame_id') == 'camera_color_optical_frame'
    assert s['sign_cam'].findtext('ignition_frame_id') == 'sign_camera_optical_frame'
    assert s['sign_cam'].findtext('topic') == '/sign_cam/image_raw'


def test_cameras_false_leaves_only_lidar_and_imu():
    assert set(sensors(expand(cameras=False))) == {'rplidar_s2', 'd455_imu'}


def test_lidar_is_rplidar_s2_like():
    lidar = sensors(expand())['rplidar_s2']
    assert float(lidar.findtext('update_rate')) == 10.0
    assert float(lidar.findtext('lidar/range/max')) == 30.0
    assert lidar.get('type') == 'gpu_lidar'


def test_sign_camera_is_on_a_mast_at_about_1_5_m():
    root = expand()
    assert joint_xyz(root, 'sign_camera')[2] == pytest.approx(1.5, abs=0.1)
    assert 'mast' in parents(root)


@pytest.mark.parametrize('frame, key', [('laser', 'lidar'), ('camera_link', 'd455'), ('sign_camera', 'sign_camera')])
def test_sensor_poses_match_merz_description(frame, key):
    """The simulated sensors sit where the real URDF says they are (both are placeholders until measured)."""
    real = POSES[frame]
    assert joint_xyz(expand(), frame) == pytest.approx([real['x'], real['y'], real['z']])
    assert ROVER[key]['x'] == real['x'] and ROVER[key]['z'] == real['z']


def test_lidar_does_not_see_the_mast():
    """The mast is closer to the LIDAR than range_min, so it is not a permanent obstacle in every scan."""
    gap = abs(ROVER['lidar']['x'] - ROVER['mast']['x']) - ROVER['mast']['radius']
    assert 0.0 < gap < ROVER['lidar']['range_min']
    assert ROVER['lidar']['z'] > ROVER['chassis']['ground_clearance'] + ROVER['chassis']['height']


def test_rover_fits_inside_the_nav2_footprint():
    footprint = yaml.safe_load(NAV2['local_costmap']['local_costmap']['ros__parameters']['footprint'])
    xs, ys = [p[0] for p in footprint], [p[1] for p in footprint]
    half_width = ROVER['wheels']['separation'] / 2 + ROVER['wheels']['width'] / 2
    assert max(xs) >= ROVER['chassis']['length'] / 2 and min(xs) <= -ROVER['chassis']['length'] / 2
    assert max(ys) >= max(half_width, ROVER['chassis']['width'] / 2)
    assert ROVER['casters']['x_offset'] + ROVER['casters']['radius'] <= max(xs)


def test_speed_limit_is_0_5_m_s_everywhere():
    assert ROVER['limits']['max_linear_m_s'] <= 0.5
    dwb = NAV2['controller_server']['ros__parameters']['FollowPath']
    assert dwb['max_vel_x'] <= 0.5 and dwb['max_speed_xy'] <= 0.5
    assert NAV2['velocity_smoother']['ros__parameters']['max_velocity'][0] <= 0.5


def test_wheels_touch_the_floor_with_the_casters():
    root = expand()
    assert joint_xyz(root, 'left_wheel')[2] == pytest.approx(ROVER['wheels']['radius'])
    assert joint_xyz(root, 'front_caster')[2] == pytest.approx(ROVER['casters']['radius'])
    assert joint_xyz(root, 'left_wheel')[1] == pytest.approx(ROVER['wheels']['separation'] / 2)


def test_drive_plugin_matches_the_yaml_and_uses_sim_topics():
    plugin = next(p for p in expand().iter('plugin') if p.get('name').endswith('DiffDrive'))
    assert float(plugin.findtext('wheel_separation')) == ROVER['wheels']['separation']
    assert float(plugin.findtext('wheel_radius')) == ROVER['wheels']['radius']
    assert plugin.findtext('topic') == '/sim/cmd_vel'
    assert plugin.findtext('odom_topic') == '/sim/wheel_odom'
    assert plugin.findtext('tf_topic') == '/sim/wheel_tf'


# ---------- mode (b): the estimator's inputs

def test_scan_mode_ekf_reads_only_scan_odometry_and_the_imu():
    """Mode (b) loads merz_bringup's ekf.yaml unchanged: inputs /odom_scan and the IMU, nothing from the simulator."""
    inputs = {v for k, v in EKF.items() if k[:-1] in ('odom', 'imu', 'pose', 'twist') and isinstance(v, str)}
    assert inputs == {'/odom_scan', '/camera/camera/imu'}


def test_rf2o_takes_no_initial_pose_from_a_topic():
    scan = yaml.safe_load((SRC / 'merz_bringup' / 'config' / 'scan_odometry.yaml').read_text())
    assert scan['rf2o_laser_odometry']['ros__parameters']['init_pose_from_topic'] == ''


def test_wheel_mode_override_only_replaces_odom0():
    override = yaml.safe_load((PACKAGE / 'config' / 'ekf_wheel_mode.yaml').read_text())
    params = override['ekf_filter_node']['ros__parameters']
    assert set(params) == {'odom0', 'odom0_config'}
    assert params['odom0'] == '/wheel/odometry'
    # vx and vy only: yaw rate stays with the IMU, as in mode (b)
    assert [i for i, on in enumerate(params['odom0_config']) if on] == [6, 7]


def test_launch_loads_the_wheel_override_only_in_wheel_mode():
    """The ekf_wheel_mode.yaml append sits inside the `== 'wheel'` branch of _localisation."""
    tree = ast.parse(LAUNCH)
    func = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == '_localisation')
    branch = next(n for n in ast.walk(func) if isinstance(n, ast.If))
    assert "'wheel'" in ast.unparse(branch.test)
    inside = ast.unparse(ast.Module(body=branch.body, type_ignores=[]))
    outside = ast.unparse(ast.Module(body=branch.orelse, type_ignores=[]))
    assert 'ekf_wheel_mode.yaml' in inside and 'ekf_wheel_mode.yaml' not in outside
    assert 'rf2o_laser_odometry' in outside and 'rf2o_laser_odometry' not in inside
    assert 'WHEEL_ODOM_RAW' in inside and 'WHEEL_ODOM_RAW' not in outside


def test_every_ros_node_in_the_launch_uses_sim_time():
    tree = ast.parse(LAUNCH)
    for call in (n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, 'id', '') == 'Node'):
        package = next(k.value.value for k in call.keywords if k.arg == 'package')
        if package in ('ros_gz_sim', 'ros_gz_bridge'):
            continue   # the bridge publishes /clock itself; the spawner only runs once
        params = next((k.value for k in call.keywords if k.arg == 'parameters'), None)
        assert params is not None and 'SIM_TIME' in ast.unparse(params), package
