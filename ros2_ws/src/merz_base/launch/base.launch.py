"""The rover base driver, listening only to the output of twist_mux. Backend and limits are in config/base.yaml."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    config = os.path.join(get_package_share_directory('merz_base'), 'config', 'base.yaml')
    return LaunchDescription([
        Node(package='merz_base', executable='base_node', name='base_node', parameters=[config],
             remappings=[('cmd_vel', '/cmd_vel_mux')], output='screen'),
    ])
