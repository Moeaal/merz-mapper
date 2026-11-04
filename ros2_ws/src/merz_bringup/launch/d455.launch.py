"""RealSense D455 on its own: colour, aligned depth, point cloud and one united IMU topic."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    config = os.path.join(get_package_share_directory('merz_bringup'), 'config', 'd455.yaml')
    return LaunchDescription([
        Node(package='realsense2_camera', executable='realsense2_camera_node',
             namespace='camera', name='camera', parameters=[config], output='screen'),
    ])
