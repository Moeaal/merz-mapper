"""All sensors plus the URDF frames. Each sensor can be switched off, for one-at-a-time bring-up."""
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
        DeclareLaunchArgument('lidar', default_value='true'),
        DeclareLaunchArgument('d455', default_value='true'),
        DeclareLaunchArgument('c920', default_value='true'),
        _include('merz_description', 'description.launch.py'),
        _include('merz_bringup', 'lidar.launch.py', condition=IfCondition(LaunchConfiguration('lidar'))),
        _include('merz_bringup', 'd455.launch.py', condition=IfCondition(LaunchConfiguration('d455'))),
        _include('merz_bringup', 'c920.launch.py', condition=IfCondition(LaunchConfiguration('c920'))),
    ])
