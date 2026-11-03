"""SLAM Toolbox, online async. Publishes /map and map->odom.

Give posegraph:=<path without extension> to continue from an earlier run, so all the entrances end up
in the same map frame. Then the start pose in that frame is also required (start_x, start_y, start_yaw).

Node note: on Humble this is a plain node. From Jazzy, slam_toolbox is a lifecycle node and needs configuring
and activating; if the project moves to Jazzy, include the package's online_async_launch.py instead.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _node(context):
    config = os.path.join(get_package_share_directory('merz_bringup'), 'config', 'slam.yaml')
    parameters = [config]
    posegraph = LaunchConfiguration('posegraph').perform(context)
    if posegraph:
        parameters.append({
            'map_file_name': posegraph,
            'map_start_pose': [float(LaunchConfiguration(arg).perform(context))
                               for arg in ('start_x', 'start_y', 'start_yaw')],
        })
    return [Node(package='slam_toolbox', executable='async_slam_toolbox_node', name='slam_toolbox',
                 parameters=parameters, output='screen')]


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription([
        DeclareLaunchArgument('posegraph', default_value='', description='Earlier posegraph, no extension.'),
        DeclareLaunchArgument('start_x', default_value='0.0', description='Metres, in the earlier map frame.'),
        DeclareLaunchArgument('start_y', default_value='0.0', description='Metres, in the earlier map frame.'),
        DeclareLaunchArgument('start_yaw', default_value='0.0', description='Radians, in the earlier map frame.'),
        OpaqueFunction(function=_node),
    ])
