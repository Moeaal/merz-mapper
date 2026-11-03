"""Check the project's Nav2 rules in the YAML and behaviour tree. No ROS needed; Nav2 itself must check the rest."""
import ast
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
import yaml

PACKAGE = Path(__file__).resolve().parents[1]
NAV2 = yaml.safe_load((PACKAGE / 'config' / 'nav2.yaml').read_text())
SPEC_MAX_SPEED = 0.5  # m/s


def follow_path() -> dict:
    return NAV2['controller_server']['ros__parameters']['FollowPath']


def costmap(name: str) -> dict:
    return NAV2[name][name]['ros__parameters']


def test_controller_respects_the_speed_limit():
    assert follow_path()['max_vel_x'] <= SPEC_MAX_SPEED
    assert follow_path()['max_speed_xy'] <= SPEC_MAX_SPEED


def test_smoother_respects_the_speed_limit():
    assert NAV2['velocity_smoother']['ros__parameters']['max_velocity'][0] <= SPEC_MAX_SPEED


def test_the_rover_never_reverses_or_strafes():
    assert follow_path()['min_vel_x'] == 0.0
    assert follow_path()['max_vel_y'] == 0.0
    assert NAV2['velocity_smoother']['ros__parameters']['min_velocity'][0] == 0.0


def test_nav2_uses_the_ekf_odometry():
    assert NAV2['bt_navigator']['ros__parameters']['odom_topic'] == '/odometry/filtered'
    assert NAV2['controller_server']['ros__parameters']['odom_topic'] == '/odometry/filtered'


def test_frontier_goals_can_be_planned_into_unknown_space():
    assert NAV2['planner_server']['ros__parameters']['GridBased']['allow_unknown'] is True
    assert costmap('global_costmap')['track_unknown_space'] is True


def test_footprints_are_identical_and_a_closed_polygon_around_base_link():
    local, global_ = costmap('local_costmap')['footprint'], costmap('global_costmap')['footprint']
    assert local == global_
    points = ast.literal_eval(local)
    assert len(points) >= 3
    assert max(p[0] for p in points) > 0 > min(p[0] for p in points)
    assert max(p[1] for p in points) > 0 > min(p[1] for p in points)


@pytest.mark.parametrize('name', ['local_costmap', 'global_costmap'])
def test_keepout_filter_is_on_both_costmaps_and_matches_the_info_server(name):
    params = costmap(name)
    assert params['filters'] == ['keepout_filter']
    keepout = yaml.safe_load((PACKAGE / 'config' / 'keepout.yaml').read_text())
    info = keepout['costmap_filter_info_server']['ros__parameters']
    assert params['keepout_filter']['filter_info_topic'] == info['filter_info_topic']
    assert info['mask_topic'] == keepout['filter_mask_server']['ros__parameters']['topic_name']
    assert info['type'] == 0


def test_depth_is_an_extra_obstacle_source_within_its_trusted_range():
    layer = costmap('local_costmap')['voxel_layer']
    assert layer['observation_sources'].split() == ['scan', 'depth']
    assert layer['depth']['data_type'] == 'PointCloud2'
    assert layer['depth']['obstacle_min_range'] >= 0.6


def test_moving_recoveries_are_absent():
    tree = ET.parse(PACKAGE / 'behavior_trees' / 'navigate_no_motion_recovery.xml')
    tags = {element.tag for element in tree.iter()}
    assert not tags & {'Spin', 'BackUp', 'DriveOnHeading'}
    assert {'ComputePathToPose', 'FollowPath', 'Wait', 'ClearEntireCostmap'} <= tags
    assert NAV2['behavior_server']['ros__parameters']['behavior_plugins'] == ['wait']


def test_recovery_tree_only_uses_loaded_plugins():
    plugins = NAV2['bt_navigator']['ros__parameters']['plugin_lib_names']
    assert 'nav2_wait_action_bt_node' in plugins
    assert 'nav2_compute_path_to_pose_action_bt_node' in plugins
    assert len(plugins) == len(set(plugins))
