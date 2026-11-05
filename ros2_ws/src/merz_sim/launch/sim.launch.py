"""The whole simulated stack in one launch file (PROPOSED; see the README for what has and has not been run).

    ros2 launch merz_sim sim.launch.py                         # mode (b): scan matching + IMU, no wheel odometry
    ros2 launch merz_sim sim.launch.py odom_mode:=wheel        # mode (a): simulated wheel odometry + IMU
    ros2 launch merz_sim sim.launch.py entrance:=south gui:=true rviz:=true
    ros2 launch merz_sim sim.launch.py cameras:=false          # LIDAR + IMU only: much lighter

Starts: Gazebo (headless by default) with the generated floor world, the parametric rover, the ros_gz bridge,
robot_state_publisher, the simulated base (merz_base's BaseController), twist_mux, odometry for the chosen mode,
the robot_localization EKF, SLAM Toolbox (online async), Nav2 and explore_lite.

The EKF, SLAM, Nav2, twist_mux and explore_lite parameters are merz_bringup's and merz_exploration's own files,
unchanged, with use_sim_time added. Only the Gazebo parts and mode (a) are simulation-specific.
"""
import os
import tempfile

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, OpaqueFunction, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from nav2_common.launch import RewrittenYaml
import yaml

from merz_sim import gz_compat, world_gen

SIM_TIME = {'use_sim_time': True}


def _flag(context, name: str) -> bool:
    value = context.launch_configurations[name].lower()
    if value not in ('true', 'false'):
        raise ValueError(f'{name} must be true or false, not {value!r}')
    return value == 'true'


def _simulator(context, sim: str, gz: gz_compat.GzVersion, entrance: world_gen.Entrance, cameras: bool) -> list:
    """Gazebo, the robot model, the spawn and the bridge."""
    layout_file = context.launch_configurations['world'] or os.path.join(sim, 'worlds', 'merz_floor.yaml')
    world_file = world_gen.write_world(
        layout_file, os.path.join(tempfile.gettempdir(), 'merz_sim', f'merz_floor_{gz.name}.sdf'), gz.name)
    xacro_file = os.path.join(sim, 'urdf', 'merz_sim_rover.urdf.xacro')
    rover_file = os.path.join(sim, 'config', 'sim_rover.yaml')
    # The xacro is expanded here, in Python, so its output can be checked before anything starts.
    import xacro
    description = xacro.process_file(xacro_file, mappings={
        'rover_file': rover_file, 'gz_version': gz.name, 'cameras': str(cameras).lower()}).toxml()

    bridges = gz_compat.bridges(context.launch_configurations['odom_mode'], cameras)
    actions = [
        ExecuteProcess(cmd=gz_compat.server_command(gz, str(world_file), headless=not _flag(context, 'gui')),
                       output='screen', name='gz_server'),
        Node(package='robot_state_publisher', executable='robot_state_publisher', name='robot_state_publisher',
             parameters=[{'robot_description': ParameterValue(description, value_type=str), **SIM_TIME}],
             output='screen'),
        Node(package='ros_gz_sim', executable='create', name='spawn_rover', output='screen',
             arguments=['-world', gz_compat.WORLD_NAME, '-name', gz_compat.MODEL_NAME, '-topic', 'robot_description',
                        '-x', str(entrance.x), '-y', str(entrance.y), '-z', '0.02', '-Y', str(entrance.yaw)]),
        Node(package='ros_gz_bridge', executable='parameter_bridge', name='gz_bridge', output='screen',
             arguments=gz_compat.bridge_arguments(gz, bridges), remappings=gz_compat.bridge_remappings(bridges)),
    ]
    if _flag(context, 'gui'):
        actions.append(ExecuteProcess(cmd=gz_compat.gui_command(gz), output='screen', name='gz_gui'))
    if cameras:
        points_config = os.path.join(sim, 'config', 'depth_to_points.yaml')
        actions.append(Node(
            package='depth_image_proc', executable='point_cloud_xyz_node', name='point_cloud_xyz_node',
            parameters=[points_config, SIM_TIME], output='screen',
            remappings=[('image_rect', '/camera/camera/aligned_depth_to_color/image_raw'),
                        ('camera_info', '/camera/camera/aligned_depth_to_color/camera_info'),
                        ('points', '/camera/camera/depth/color/points')]))
    return actions


def _base(sim: str, bringup: str) -> list:
    """Velocity chain, as on the rover: Nav2 /cmd_vel + teleop /cmd_vel_teleop -> twist_mux -> /cmd_vel_mux -> base."""
    with open(os.path.join(sim, 'config', 'sim_rover.yaml')) as stream:
        rover = yaml.safe_load(stream)
    limits = dict(rover['limits'])
    limits['track_width_m'] = float(rover['wheels']['separation'])
    mux_config = os.path.join(bringup, 'config', 'twist_mux.yaml')
    return [
        Node(package='twist_mux', executable='twist_mux', name='twist_mux',
             parameters=[mux_config, SIM_TIME], remappings=[('cmd_vel_out', 'cmd_vel_mux')], output='screen'),
        Node(package='merz_sim', executable='sim_base_node', name='sim_base_node',
             parameters=[limits, SIM_TIME], output='screen',
             remappings=[('cmd_vel', '/cmd_vel_mux'), ('sim_cmd_vel', '/sim/cmd_vel')]),
    ]


def _localisation(context, sim: str, bringup: str) -> list:
    """Odometry for the chosen mode, then the EKF (odom->base_link) and SLAM Toolbox (map->odom)."""
    ekf_configs = [os.path.join(bringup, 'config', 'ekf.yaml')]
    if context.launch_configurations['odom_mode'] == 'wheel':
        # Mode (a): DiffDrive odometry (bridged as /sim/wheel_odometry_raw) + a covariance -> /wheel/odometry.
        wheel_config = os.path.join(sim, 'config', 'wheel_odometry.yaml')
        ekf_configs.append(os.path.join(sim, 'config', 'ekf_wheel_mode.yaml'))
        odometry = [Node(package='merz_bringup', executable='scan_odom_relay_node', name='wheel_odom_relay',
                         parameters=[wheel_config, SIM_TIME], output='screen',
                         remappings=[('odom_in', gz_compat.WHEEL_ODOM_RAW), ('odom_out', '/wheel/odometry')])]
    else:
        # Mode (b): exactly merz_bringup/launch/localisation.launch.py, the real rover's plan (decisions #10, #14).
        scan_config = os.path.join(bringup, 'config', 'scan_odometry.yaml')
        odometry = [
            Node(package='rf2o_laser_odometry', executable='rf2o_laser_odometry_node', name='rf2o_laser_odometry',
                 parameters=[scan_config, SIM_TIME], output='screen'),
            Node(package='merz_bringup', executable='scan_odom_relay_node', name='scan_odom_relay',
                 parameters=[scan_config, SIM_TIME], output='screen',
                 remappings=[('odom_in', '/odom_rf2o'), ('odom_out', '/odom_scan')]),
        ]
    slam_config = os.path.join(bringup, 'config', 'slam.yaml')
    return odometry + [
        Node(package='robot_localization', executable='ekf_node', name='ekf_filter_node',
             parameters=[*ekf_configs, SIM_TIME], output='screen'),
        # Humble: a plain node. On Jazzy slam_toolbox is a lifecycle node (see merz_bringup/launch/slam.launch.py).
        Node(package='slam_toolbox', executable='async_slam_toolbox_node', name='slam_toolbox',
             parameters=[slam_config, SIM_TIME], output='screen'),
    ]


def _navigation(bringup: str) -> list:
    """Nav2 with merz_bringup's parameters and no-motion recovery tree, as in merz_bringup/launch/navigation.launch.py."""
    tree = os.path.join(bringup, 'behavior_trees', 'navigate_no_motion_recovery.xml')
    params = RewrittenYaml(source_file=os.path.join(bringup, 'config', 'nav2.yaml'),
                           param_rewrites={'default_nav_to_pose_bt_xml': tree}, convert_types=True)
    nav2_launch = os.path.join(get_package_share_directory('nav2_bringup'), 'launch', 'navigation_launch.py')
    return [IncludeLaunchDescription(PythonLaunchDescriptionSource(nav2_launch), launch_arguments={
        'params_file': params, 'autostart': 'true', 'use_sim_time': 'true'}.items())]


def _exploration(context, exploration: str) -> list:
    """explore_lite with merz_exploration's parameters, started late: its first goal fails before the map and Nav2 exist."""
    config = os.path.join(exploration, 'config', 'exploration.yaml')
    return [TimerAction(period=float(context.launch_configurations['explore_delay_s']), actions=[
        Node(package='explore_lite', executable='explore', name='explore_node',
             parameters=[config, SIM_TIME], output='screen')])]


def _everything(context):
    sim = get_package_share_directory('merz_sim')
    bringup = get_package_share_directory('merz_bringup')
    exploration = get_package_share_directory('merz_exploration')
    gz = gz_compat.version(context.launch_configurations['gz_version'])
    default_layout = os.path.join(sim, 'worlds', 'merz_floor.yaml')
    layout = world_gen.load_layout(context.launch_configurations['world'] or default_layout)
    places = world_gen.entrances(layout)
    key = context.launch_configurations['entrance']
    if key not in places:
        raise ValueError(f'entrance must be one of {sorted(places)}, not {key!r}')
    cameras = _flag(context, 'cameras')
    if context.launch_configurations['odom_mode'] not in ('wheel', 'scan'):
        raise ValueError("odom_mode must be 'wheel' or 'scan'")

    actions = (_simulator(context, sim, gz, places[key], cameras) + _base(sim, bringup)
               + _localisation(context, sim, bringup))
    if _flag(context, 'nav'):
        actions += _navigation(bringup)
        if _flag(context, 'explore'):
            actions += _exploration(context, exploration)
    if _flag(context, 'rviz'):
        rviz_config = os.path.join(sim, 'rviz', 'sim.rviz')
        actions.append(Node(package='rviz2', executable='rviz2', name='rviz2', arguments=['-d', rviz_config],
                            parameters=[SIM_TIME]))
    return actions


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription([
        DeclareLaunchArgument('odom_mode', default_value='scan',
                              description="scan: rf2o + IMU, no wheel odometry (decisions #10). wheel: simulated "
                                          "wheel odometry + IMU."),
        DeclareLaunchArgument('entrance', default_value='west', description='Start pose: west, south or east.'),
        DeclareLaunchArgument('gz_version', default_value='fortress',
                              description='fortress (Humble binaries) or harmonic (ros-humble-ros-gzharmonic / Jazzy).'),
        DeclareLaunchArgument('cameras', default_value='true',
                              description='false: no D455 RGB-D or sign camera rendering (LIDAR + IMU only).'),
        DeclareLaunchArgument('gui', default_value='false', description='Gazebo GUI. Default headless.'),
        DeclareLaunchArgument('rviz', default_value='false', description='RViz with the map, scan and costmaps.'),
        DeclareLaunchArgument('nav', default_value='true', description='Nav2. false: SLAM + teleop only.'),
        DeclareLaunchArgument('explore', default_value='true', description='explore_lite (needs nav:=true).'),
        DeclareLaunchArgument('explore_delay_s', default_value='25.0',
                              description='Wall-clock seconds before exploration starts.'),
        DeclareLaunchArgument('world', default_value='', description='Layout YAML. Empty: worlds/merz_floor.yaml.'),
        OpaqueFunction(function=_everything),
    ])
