"""RPLIDAR on its own. Publishes /scan.

Two LIDARs, two config files (decisions #33):
    ros2 launch merz_bringup lidar.launch.py                    # C1 stand-in (default until the S2 arrives)
    ros2 launch merz_bringup lidar.launch.py lidar_model:=s2    # RPLIDAR S2
The argument also works on any launch file that includes this one (sensors, mapping, exploration).
When the S2 is fitted for good, change the default below to 's2'.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import LaunchConfigurationEquals
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    c1_config = os.path.join(get_package_share_directory('merz_bringup'), 'config', 'lidar_c1.yaml')
    s2_config = os.path.join(get_package_share_directory('merz_bringup'), 'config', 'lidar_s2.yaml')
    return LaunchDescription([
        DeclareLaunchArgument('lidar_model', default_value='c1', choices=['c1', 's2'],
                              description='Which RPLIDAR is fitted: c1 (temporary stand-in) or s2'),
        Node(package='sllidar_ros2', executable='sllidar_node', name='sllidar_node',
             parameters=[c1_config], output='screen', condition=LaunchConfigurationEquals('lidar_model', 'c1')),
        Node(package='sllidar_ros2', executable='sllidar_node', name='sllidar_node',
             parameters=[s2_config], output='screen', condition=LaunchConfigurationEquals('lidar_model', 's2')),
    ])
