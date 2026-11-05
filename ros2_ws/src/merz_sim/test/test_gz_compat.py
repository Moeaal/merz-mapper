"""Bridges per mode: in mode (b) nothing from the simulator that knows the true motion reaches ROS."""
import pytest

from merz_sim import gz_compat

ALL_MODES = [(mode, cameras) for mode in ('wheel', 'scan') for cameras in (True, False)]


def ros_names(items):
    return {item.ros_name or item.gz_topic for item in items}


@pytest.mark.parametrize('cameras', [True, False])
def test_scan_mode_bridges_no_ground_truth(cameras):
    items = gz_compat.bridges('scan', cameras)
    gz_topics = {item.gz_topic for item in items}
    assert not gz_topics & set(gz_compat.GROUND_TRUTH_GZ_TOPICS)
    assert gz_compat.WHEEL_ODOM_RAW not in ros_names(items)
    assert not any('odom' in t or 'pose' in t or t.endswith('/tf') for t in gz_topics)


@pytest.mark.parametrize('mode, cameras', ALL_MODES)
def test_the_drive_plugin_tf_is_never_bridged(mode, cameras):
    """The EKF alone owns odom->base_link; a second publisher would make the TF tree jump."""
    names = ros_names(gz_compat.bridges(mode, cameras))
    assert '/tf' not in names and '/sim/wheel_tf' not in names


def test_wheel_mode_bridges_the_wheel_odometry_under_a_raw_name():
    items = gz_compat.bridges('wheel', False)
    odom = [i for i in items if i.gz_topic == '/sim/wheel_odom']
    assert len(odom) == 1 and odom[0].ros_name == gz_compat.WHEEL_ODOM_RAW and odom[0].gz_to_ros


@pytest.mark.parametrize('mode, cameras', ALL_MODES)
def test_topics_are_named_as_the_real_drivers_name_them(mode, cameras):
    names = ros_names(gz_compat.bridges(mode, cameras))
    assert {'/clock', '/scan', '/camera/camera/imu', '/joint_states', '/sim/cmd_vel'} <= names
    if cameras:
        assert {'/camera/camera/color/image_raw', '/camera/camera/aligned_depth_to_color/image_raw',
                '/camera/camera/aligned_depth_to_color/camera_info', '/sign_cam/image_raw',
                '/sign_cam/camera_info'} <= names
    else:
        assert not any(n.startswith('/sign_cam') or 'image' in n for n in names)


def test_argument_syntax_and_direction():
    fortress, harmonic = gz_compat.version('fortress'), gz_compat.version('harmonic')
    scan = gz_compat.Bridge('/scan', 'sensor_msgs/msg/LaserScan', 'LaserScan')
    cmd = gz_compat.Bridge('/sim/cmd_vel', 'geometry_msgs/msg/Twist', 'Twist', gz_to_ros=False)
    assert scan.argument(fortress) == '/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan'
    assert scan.argument(harmonic) == '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan'
    assert cmd.argument(fortress) == '/sim/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist'


def test_remappings_only_where_names_differ():
    remaps = dict(gz_compat.bridge_remappings(gz_compat.bridges('scan', True)))
    assert remaps['/camera/sim_rgbd/image'] == '/camera/camera/color/image_raw'
    assert '/scan' not in remaps


def test_bad_arguments_are_refused():
    with pytest.raises(ValueError):
        gz_compat.version('classic')
    with pytest.raises(ValueError):
        gz_compat.bridges('ground_truth', False)


def test_commands():
    fortress = gz_compat.version('fortress')
    assert gz_compat.server_command(fortress, 'w.sdf') == ['ign', 'gazebo', '-r', '-s', '-v', '2',
                                                          '--headless-rendering', 'w.sdf']
    assert gz_compat.gui_command(gz_compat.version('harmonic')) == ['gz', 'sim', '-g']
    assert gz_compat.system_plugin(fortress, 'imu', 'Imu') == ('ignition-gazebo-imu-system',
                                                               'ignition::gazebo::systems::Imu')
