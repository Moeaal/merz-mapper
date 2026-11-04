"""Publish the static sensor frames from the URDF. Add rviz:=true to look at the model."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:
    share = get_package_share_directory('merz_description')
    xacro_file = os.path.join(share, 'urdf', 'merz_rover.urdf.xacro')
    rviz_file = os.path.join(share, 'rviz', 'description.rviz')

    # value_type=str stops launch parsing the XML as YAML.
    robot_description = ParameterValue(
        Command([
            'xacro ', xacro_file,
            ' include_d455_internal_frames:=', LaunchConfiguration('include_d455_internal_frames'),
        ]),
        value_type=str,
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('rviz', default_value='false'),
        DeclareLaunchArgument(
            'include_d455_internal_frames', default_value='false',
            description='True only if the RealSense driver is NOT running (it publishes these frames itself).',
        ),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{
                'robot_description': robot_description,
                'use_sim_time': LaunchConfiguration('use_sim_time'),
            }],
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            arguments=['-d', rviz_file],
            condition=IfCondition(LaunchConfiguration('rviz')),
        ),
    ])
