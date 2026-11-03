"""Logitech C920 on its own. Publishes /sign_cam/image_raw and /sign_cam/camera_info."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    config = os.path.join(get_package_share_directory('merz_bringup'), 'config', 'c920.yaml')
    return LaunchDescription([
        Node(package='usb_cam', executable='usb_cam_node_exe', namespace='sign_cam', name='usb_cam',
             parameters=[config], output='screen'),
    ])
