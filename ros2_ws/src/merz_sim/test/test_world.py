"""The generated world: valid SDF for both Gazebo versions, closed, connected, and with the features asked for."""
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from merz_sim import world_gen

LAYOUT_FILE = Path(__file__).resolve().parents[1] / 'worlds' / 'merz_floor.yaml'
ROBOT_CLEARANCE = 0.30   # m, about half the 0.5 m x 0.4 m chassis diagonal (0.32), less a little


@pytest.fixture(scope='module')
def layout():
    return world_gen.load_layout(LAYOUT_FILE)


@pytest.fixture(scope='module')
def grid(layout):
    return world_gen.occupancy(layout, resolution=0.1)


@pytest.mark.parametrize('gz, prefix', [('fortress', 'ignition-gazebo-'), ('harmonic', 'gz-sim-')])
def test_sdf_parses_and_uses_the_right_plugin_names(layout, gz, prefix):
    root = ET.fromstring(world_gen.world_sdf(layout, gz))
    world = root.find('world')
    assert world.get('name') == 'merz_floor'
    plugins = [p.get('filename') for p in world.findall('plugin')]
    assert plugins and all(p.startswith(prefix) for p in plugins)
    assert any('sensors' in p for p in plugins) and any('imu' in p for p in plugins)
    assert world.find("plugin[@filename='%ssensors-system']/render_engine" % prefix).text == 'ogre2'
    building = world.find("model[@name='building']")
    assert building.findtext('static') == 'true'
    assert len(building.findall('link/collision')) == len(world_gen.boxes(layout))


def test_unknown_gazebo_version_is_refused(layout):
    with pytest.raises(ValueError):
        world_gen.world_sdf(layout, 'garden')


def test_element_names_are_unique(layout):
    names = [b.name for b in world_gen.boxes(layout)]
    assert len(names) == len(set(names))


def test_at_least_two_entrances_each_with_a_free_start_pose(layout, grid):
    places = world_gen.entrances(layout)
    assert len(places) >= 2
    for place in places.values():
        cells, _ = world_gen.reachable(*grid, place.x, place.y, clearance=ROBOT_CLEARANCE)
        assert cells, f'{place.key}: the robot would start inside or against a wall'


def test_the_building_is_closed_so_exploration_can_finish(layout, grid):
    for place in world_gen.entrances(layout).values():
        _, open_to_outside = world_gen.reachable(*grid, place.x, place.y)
        assert not open_to_outside, f'{place.key}: free space leaks out of the layout'


def test_every_entrance_reaches_every_other_and_the_main_areas(layout, grid):
    """With a robot-sized clearance, i.e. the robot can actually drive between them."""
    res = grid[3]
    def cell(x, y):
        return int((x - grid[1]) / res), int((y - grid[2]) / res)
    places = list(world_gen.entrances(layout).values())
    region, _ = world_gen.reachable(*grid, places[0].x, places[0].y, clearance=ROBOT_CLEARANCE)
    for place in places[1:]:
        assert cell(place.x, place.y) in region, place.key
    for name, (x, y) in {'atrium': (-5, 0), 'junction': (15, 0), 'east corridor': (25, 0), 'north dead end': (15, 9),
                         'R1 via open door': (5, 4), 'R3 lab via open door': (5, -2.5), 'R4': (18, 4),
                         'R5': (27, 4)}.items():
        assert cell(x, y) in region, name


def test_rooms_behind_closed_doors_are_not_reachable(layout, grid):
    """R2 and R6 have closed doors: useful later for the access-zone logic (O5)."""
    res = grid[3]
    region, _ = world_gen.reachable(*grid, -9.0, 0.0)
    for x, y in ((11, 4), (22, -4)):
        assert (int((x - grid[1]) / res), int((y - grid[2]) / res)) not in region


def test_there_is_a_four_way_junction_and_long_corridors(layout, grid):
    """Free space in all four directions around (15, 0), and a corridor longer than 25 m."""
    region, _ = world_gen.reachable(*grid, 15.0, 0.0)
    res = grid[3]
    for x, y in ((12, 0), (18, 0), (15, 3), (15, -3)):
        assert (int((x - grid[1]) / res), int((y - grid[2]) / res)) in region
    assert all((int((x - grid[1]) / res), int((0 - grid[2]) / res)) in region for x in range(0, 30))


def test_open_doors_are_wide_enough_for_the_rover(layout):
    for wall in layout['walls']:
        for door in wall.get('doors', []):
            if not door.get('closed'):
                assert door['width'] >= 1.0   # 0.4 m chassis + clearance for Nav2's inflation


def test_a_door_that_does_not_fit_is_refused():
    layout = {'wall': {'thickness': 0.1, 'height': 2.0}, 'walls': [{'from': [0, 0], 'to': [2, 0],
                                                                    'doors': [{'at': 1.8, 'width': 1.0}]}],
              'entrances': {}}
    with pytest.raises(ValueError):
        world_gen.boxes(layout)


def test_door_splits_wall_and_corners_are_closed():
    layout = {'wall': {'thickness': 0.2, 'height': 2.0}, 'walls': [{'from': [0, 0], 'to': [10, 0],
                                                                    'doors': [{'at': 5.0, 'width': 1.0}]}],
              'entrances': {}}
    left, right = world_gen.boxes(layout)
    assert left.length == pytest.approx(4.5 + 0.1) and right.length == pytest.approx(4.5 + 0.1)
    assert left.x - left.length / 2 == pytest.approx(-0.1)
    assert right.x + right.length / 2 == pytest.approx(10.1)
    assert math.isclose(left.yaw, 0.0)


def test_write_world(tmp_path):
    out = world_gen.write_world(LAYOUT_FILE, tmp_path / 'w.sdf', 'fortress')
    assert ET.parse(out).getroot().tag == 'sdf'
