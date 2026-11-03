"""Landmark localiser. Needs perception, the D455 and TF. Override the database per run with database:=<path>."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    config = os.path.join(get_package_share_directory('merz_semantic_map'), 'config', 'semantic_map.yaml')
    return LaunchDescription([
        DeclareLaunchArgument('database', default_value='~/merz_data/merz.sqlite'),
        DeclareLaunchArgument('fusion_mode', default_value='fused', description='fused or single_observation (O8).'),
        Node(package='merz_semantic_map', executable='landmark_node', name='landmark_node',
             parameters=[config, {'database': LaunchConfiguration('database'),
                                  'fusion_mode': LaunchConfiguration('fusion_mode')}],
             remappings=[
                 ('detections', '/perception/d455/detections'),
                 ('depth', '/camera/camera/aligned_depth_to_color/image_raw'),
                 ('depth_camera_info', '/camera/camera/aligned_depth_to_color/camera_info'),
                 ('sign_camera_info', '/sign_cam/camera_info'),
                 ('sign_readings', '/perception/sign_readings'),
             ],
             output='screen'),
    ])
