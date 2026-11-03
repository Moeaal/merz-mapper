"""Manual mapping for gate G1: sensors, gamepad, base, localisation and SLAM.

    ros2 launch merz_bringup mapping.launch.py

Save the map afterwards with:
    ros2 run nav2_map_server map_saver_cli -f ~/merz_data/maps/first_map
Record alongside with record_bag.launch.py in a second terminal.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def _include(package: str, launch_file: str, **kwargs) -> IncludeLaunchDescription:
    path = os.path.join(get_package_share_directory(package), 'launch', launch_file)
    return IncludeLaunchDescription(PythonLaunchDescriptionSource(path), **kwargs)


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription([
        DeclareLaunchArgument('c920', default_value='false', description='Not needed for the map itself.'),
        DeclareLaunchArgument('base', default_value='true', description='False when pushing the rover by hand.'),
        DeclareLaunchArgument('use_wheel_odom', default_value='false'),
        _include('merz_bringup', 'sensors.launch.py', launch_arguments={'c920': LaunchConfiguration('c920')}.items()),
        _include('merz_bringup', 'teleop.launch.py'),
        _include('merz_base', 'base.launch.py', condition=IfCondition(LaunchConfiguration('base'))),
        _include('merz_bringup', 'localisation.launch.py',
                 launch_arguments={'use_wheel_odom': LaunchConfiguration('use_wheel_odom')}.items()),
        _include('merz_bringup', 'slam.launch.py'),
    ])
