"""Record a rosbag of a run, so SLAM can be re-run offline across the December-February leave.

    ros2 launch merz_bringup record_bag.launch.py name:=corridor_a images:=true

Images are large (tens of GB per hour), so they are opt-in. Use them when collecting labelling data.
"""
from datetime import datetime
import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction
from launch.substitutions import LaunchConfiguration

CORE_TOPICS = [
    '/scan', '/tf', '/tf_static', '/camera/camera/imu', '/odom_rf2o', '/odom_scan', '/odometry/filtered',
    '/map', '/map_updates', '/cmd_vel_mux', '/joy',
]
IMAGE_TOPICS = [
    '/camera/camera/color/image_raw', '/camera/camera/color/camera_info',
    '/camera/camera/aligned_depth_to_color/image_raw', '/camera/camera/aligned_depth_to_color/camera_info',
    '/sign_cam/image_raw/compressed', '/sign_cam/camera_info',
]


def _record(context):
    name = LaunchConfiguration('name').perform(context)
    root = os.path.expanduser(LaunchConfiguration('directory').perform(context))
    images = LaunchConfiguration('images').perform(context).lower() == 'true'
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    topics = CORE_TOPICS + (IMAGE_TOPICS if images else [])
    output = os.path.join(root, f'{stamp}_{name}')
    return [ExecuteProcess(cmd=['ros2', 'bag', 'record', '-s', 'mcap', '-o', output, *topics], output='screen')]


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription([
        DeclareLaunchArgument('name', default_value='run'),
        DeclareLaunchArgument('directory', default_value='~/merz_data/bags', description='Use the NVMe SSD.'),
        DeclareLaunchArgument('images', default_value='false'),
        OpaqueFunction(function=_record),
    ])
