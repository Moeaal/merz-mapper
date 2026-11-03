"""Gamepad teleop with a deadman, and twist_mux so that teleop overrides autonomy."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    share = get_package_share_directory('merz_bringup')
    teleop_config = os.path.join(share, 'config', 'teleop.yaml')
    mux_config = os.path.join(share, 'config', 'twist_mux.yaml')
    return LaunchDescription([
        Node(package='joy', executable='joy_node', name='joy_node', parameters=[teleop_config]),
        Node(package='teleop_twist_joy', executable='teleop_node', name='teleop_node',
             parameters=[teleop_config], remappings=[('cmd_vel', 'cmd_vel_teleop')]),
        Node(package='twist_mux', executable='twist_mux', name='twist_mux',
             parameters=[mux_config], remappings=[('cmd_vel_out', 'cmd_vel_mux')]),
    ])
