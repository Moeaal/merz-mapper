"""The full autonomy run from one entrance: sensors, base, localisation, SLAM, Nav2, exploration, perception, semantic map
and access zones. Saves the map, posegraph and database at the end. Read the safety checklist in the README first.

First entrance (creates the map):
    ros2 launch merz_bringup explore_from_entrance.launch.py entrance:=east entrance_name:="East door"
Later entrance (same map frame, so routes join up):
    ros2 launch merz_bringup explore_from_entrance.launch.py entrance:=west posegraph:=~/merz_data/maps/east_<time> \
        start_x:=12.0 start_y:=3.5 start_yaw:=1.57
"""
from datetime import datetime
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def _include(package: str, launch_file: str, arguments: dict | None = None) -> IncludeLaunchDescription:
    path = os.path.join(get_package_share_directory(package), 'launch', launch_file)
    return IncludeLaunchDescription(PythonLaunchDescriptionSource(path),
                                    launch_arguments=(arguments or {}).items())


def _run(context):
    def value(name: str) -> str:
        return LaunchConfiguration(name).perform(context)

    entrance = value('entrance')
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_prefix = os.path.join(os.path.expanduser(value('output_directory')), f'{entrance}_{stamp}')
    os.makedirs(os.path.dirname(output_prefix), exist_ok=True)
    database = os.path.expanduser(value('database'))
    posegraph = os.path.expanduser(value('posegraph'))
    start = {name: value(name) for name in ('start_x', 'start_y', 'start_yaw')}

    actions = [
        _include('merz_bringup', 'sensors.launch.py'),
        _include('merz_bringup', 'teleop.launch.py'),
        _include('merz_base', 'base.launch.py'),
        _include('merz_bringup', 'localisation.launch.py', {'use_wheel_odom': value('use_wheel_odom')}),
        _include('merz_bringup', 'slam.launch.py', {'posegraph': posegraph, **start}),
        _include('merz_bringup', 'navigation.launch.py', {'keepout_mask': value('keepout_mask')}),
        _include('merz_semantic_map', 'semantic_map.launch.py', {'database': database}),
    ]
    if value('perception').lower() == 'true':
        actions.append(_include('merz_perception', 'perception.launch.py'))
    if value('bag').lower() == 'true':
        actions.append(_include('merz_bringup', 'record_bag.launch.py', {'name': entrance, 'images': 'true'}))
    # Exploration starts last: its first goal would fail before TF, the map and Nav2 are up.
    actions.append(TimerAction(period=float(value('exploration_delay_s')), actions=[
        _include('merz_exploration', 'exploration.launch.py', {
            'entrance': entrance, 'entrance_name': value('entrance_name') or entrance, 'database': database,
            'output_prefix': output_prefix, **start,
        }),
    ]))
    return actions


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription([
        DeclareLaunchArgument('entrance', description='Short entrance id, as used in the QR URL.'),
        DeclareLaunchArgument('entrance_name', default_value=''),
        DeclareLaunchArgument('database', default_value='~/merz_data/merz.sqlite'),
        DeclareLaunchArgument('output_directory', default_value='~/merz_data/maps'),
        DeclareLaunchArgument('posegraph', default_value='', description='Earlier posegraph, no extension.'),
        DeclareLaunchArgument('start_x', default_value='0.0', description='Metres, in the shared map frame.'),
        DeclareLaunchArgument('start_y', default_value='0.0', description='Metres, in the shared map frame.'),
        DeclareLaunchArgument('start_yaw', default_value='0.0', description='Radians, in the shared map frame.'),
        DeclareLaunchArgument('keepout_mask', default_value='', description='Only valid in the same map frame.'),
        DeclareLaunchArgument('use_wheel_odom', default_value='false'),
        DeclareLaunchArgument('perception', default_value='true', description='False until a model is trained.'),
        DeclareLaunchArgument('bag', default_value='true', description='Record the run.'),
        DeclareLaunchArgument('exploration_delay_s', default_value='15.0'),
        OpaqueFunction(function=_run),
    ])
