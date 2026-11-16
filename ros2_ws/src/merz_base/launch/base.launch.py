"""The rover base driver, listening only to the output of twist_mux. Backend and limits are in config/base.yaml.

    ros2 launch merz_base base.launch.py                    # mock: nothing moves
    ros2 launch merz_base base.launch.py backend:=pca9685   # the rover's motor HATs (wheels off the ground first)
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    config = os.path.join(get_package_share_directory('merz_base'), 'config', 'base.yaml')
    return LaunchDescription([
        DeclareLaunchArgument('backend', default_value='mock', choices=['mock', 'pca9685', 'serial', 'gpio'],
                              description='Motor backend. mock moves nothing.'),
        Node(package='merz_base', executable='base_node', name='base_node',
             parameters=[config, {'backend': LaunchConfiguration('backend')}],
             remappings=[('cmd_vel', '/cmd_vel_mux')], output='screen'),
    ])
