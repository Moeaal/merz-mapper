"""Frontier exploration plus the access zone, junction photo and mission-end nodes. Needs SLAM and Nav2 running."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, TextSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:
    config = os.path.join(get_package_share_directory('merz_exploration'), 'config', 'exploration.yaml')
    database = LaunchConfiguration('database')
    entrance = LaunchConfiguration('entrance')
    output_prefix = LaunchConfiguration('output_prefix')
    # slam_toolbox's save_map writes <prefix>.yaml, which is what the access zone reads.
    map_yaml = [output_prefix, TextSubstitution(text='.yaml')]

    return LaunchDescription([
        DeclareLaunchArgument('entrance', description='Short entrance id, as used in the QR URL.'),
        DeclareLaunchArgument('entrance_name', default_value=''),
        DeclareLaunchArgument('database', default_value='~/merz_data/merz.sqlite'),
        DeclareLaunchArgument('output_prefix', description='Absolute path and name, without an extension.'),
        DeclareLaunchArgument('start_x', default_value='0.0'),
        DeclareLaunchArgument('start_y', default_value='0.0'),
        DeclareLaunchArgument('start_yaw', default_value='0.0'),
        Node(package='explore_lite', executable='explore', name='explore_node', parameters=[config], output='screen'),
        Node(package='merz_exploration', executable='mission_node', name='mission_node',
             parameters=[config, {'output_prefix': output_prefix}], output='screen'),
        Node(package='merz_exploration', executable='access_zone_node', name='access_zone_node',
             # value_type stops launch guessing a type: "1" would become an int, and an empty name would fail.
             parameters=[config, {
                 'map_yaml': map_yaml,
                 'database': database,
                 'entrance': ParameterValue(entrance, value_type=str),
                 'entrance_name': ParameterValue(LaunchConfiguration('entrance_name'), value_type=str),
                 'start_x': ParameterValue(LaunchConfiguration('start_x'), value_type=float),
                 'start_y': ParameterValue(LaunchConfiguration('start_y'), value_type=float),
                 'start_yaw': ParameterValue(LaunchConfiguration('start_yaw'), value_type=float),
             }], output='screen'),
        Node(package='merz_exploration', executable='junction_photo_node', name='junction_photo_node',
             parameters=[config, {'database': database}],
             remappings=[('image', '/camera/camera/color/image_raw'), ('scan', '/scan')], output='screen'),
    ])
