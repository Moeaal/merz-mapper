"""Nav2 with our parameters, and keep-out zones when a mask is given. Output ends at /cmd_vel, which twist_mux reads.

    ros2 launch merz_bringup navigation.launch.py keepout_mask:=/path/to/mask.yaml
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from nav2_common.launch import RewrittenYaml


def _keepout_nodes(context):
    mask = LaunchConfiguration('keepout_mask').perform(context)
    if not mask:
        return []
    config = os.path.join(get_package_share_directory('merz_bringup'), 'config', 'keepout.yaml')
    return [GroupAction([
        Node(package='nav2_map_server', executable='map_server', name='filter_mask_server',
             parameters=[config, {'yaml_filename': os.path.expanduser(mask)}], output='screen'),
        Node(package='nav2_map_server', executable='costmap_filter_info_server', name='costmap_filter_info_server',
             parameters=[config], output='screen'),
        Node(package='nav2_lifecycle_manager', executable='lifecycle_manager', name='lifecycle_manager_keepout',
             parameters=[{'autostart': True, 'node_names': ['filter_mask_server', 'costmap_filter_info_server']}],
             output='screen'),
    ])]


def generate_launch_description() -> LaunchDescription:
    share = get_package_share_directory('merz_bringup')
    tree = os.path.join(share, 'behavior_trees', 'navigate_no_motion_recovery.xml')
    # The tree's installed path is only known here, so it is written into the parameters at launch.
    params = RewrittenYaml(
        source_file=os.path.join(share, 'config', 'nav2.yaml'),
        param_rewrites={'default_nav_to_pose_bt_xml': tree},
        convert_types=True,
    )
    nav2_launch = os.path.join(get_package_share_directory('nav2_bringup'), 'launch', 'navigation_launch.py')
    return LaunchDescription([
        DeclareLaunchArgument('keepout_mask', default_value='', description='Mask YAML. Empty disables keep-out.'),
        OpaqueFunction(function=_keepout_nodes),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(nav2_launch),
                                 launch_arguments={'params_file': params, 'autostart': 'true',
                                                   'use_sim_time': 'false'}.items()),
    ])
