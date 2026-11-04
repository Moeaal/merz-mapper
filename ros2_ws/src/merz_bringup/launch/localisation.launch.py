"""Scan-matching odometry plus the EKF, which publishes odom->base_link. Needs /scan, the IMU and TF."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _nodes(context):
    share = get_package_share_directory('merz_bringup')
    scan_config = os.path.join(share, 'config', 'scan_odometry.yaml')
    ekf_configs = [os.path.join(share, 'config', 'ekf.yaml')]
    if LaunchConfiguration('use_wheel_odom').perform(context).lower() == 'true':
        ekf_configs.append(os.path.join(share, 'config', 'ekf_wheel_odom.yaml'))
    return [
        Node(package='rf2o_laser_odometry', executable='rf2o_laser_odometry_node', name='rf2o_laser_odometry',
             parameters=[scan_config], output='screen'),
        Node(package='merz_bringup', executable='scan_odom_relay_node', name='scan_odom_relay',
             parameters=[scan_config], remappings=[('odom_in', '/odom_rf2o'), ('odom_out', '/odom_scan')]),
        Node(package='robot_localization', executable='ekf_node', name='ekf_filter_node',
             parameters=ekf_configs, output='screen'),
    ]


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription([
        DeclareLaunchArgument('use_wheel_odom', default_value='false',
                              description='Only if the rover turns out to have encoders (decisions #10).'),
        OpaqueFunction(function=_nodes),
    ])
