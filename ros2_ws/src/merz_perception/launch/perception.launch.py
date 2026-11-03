"""Detector on the D455 and on the C920, and the sign reader. Needs the camera drivers running."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    config = os.path.join(get_package_share_directory('merz_perception'), 'config', 'perception.yaml')
    return LaunchDescription([
        Node(package='merz_perception', executable='detector_node', name='detector_d455', parameters=[config],
             remappings=[('image', '/camera/camera/color/image_raw'), ('detections', '/perception/d455/detections')],
             output='screen'),
        Node(package='merz_perception', executable='detector_node', name='detector_c920', parameters=[config],
             remappings=[('image', '/sign_cam/image_raw'), ('detections', '/perception/c920/detections')],
             output='screen'),
        Node(package='merz_perception', executable='sign_reader_node', name='sign_reader', parameters=[config],
             remappings=[('image', '/sign_cam/image_raw'), ('detections', '/perception/c920/detections'),
                         ('sign_readings', '/perception/sign_readings')],
             output='screen'),
    ])
