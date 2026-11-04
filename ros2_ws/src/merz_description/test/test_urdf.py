"""Expand the xacro without ROS and check the frames and the YAML link."""
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
import yaml

xacro = pytest.importorskip('xacro')

PACKAGE = Path(__file__).resolve().parents[1]
XACRO_FILE = PACKAGE / 'urdf' / 'merz_rover.urdf.xacro'
POSES_FILE = PACKAGE / 'config' / 'sensor_poses.yaml'


def expand(poses_file: Path = POSES_FILE, internal_frames: bool = False) -> ET.Element:
    """Return the URDF root element. The YAML path is passed in as $(find ...) needs ROS."""
    mappings = {
        'sensor_poses_file': poses_file.as_posix(),
        'include_d455_internal_frames': 'true' if internal_frames else 'false',
    }
    doc = xacro.process_file(str(XACRO_FILE), mappings=mappings)
    return ET.fromstring(doc.toxml())


def parents(root: ET.Element) -> dict[str, str]:
    return {j.find('child').get('link'): j.find('parent').get('link') for j in root.findall('joint')}


def test_required_frames_hang_off_base_link():
    tree = parents(expand())
    assert tree['laser'] == 'base_link'
    assert tree['camera_link'] == 'base_link'
    assert tree['sign_camera'] == 'base_link'
    assert tree['sign_camera_optical_frame'] == 'sign_camera'


def test_d455_internal_frames_absent_by_default_so_the_driver_owns_them():
    links = {link.get('name') for link in expand().findall('link')}
    assert 'camera_color_optical_frame' not in links
    assert 'camera_imu_optical_frame' not in links


def test_d455_internal_frames_available_for_checks_without_the_driver():
    tree = parents(expand(internal_frames=True))
    assert tree['camera_imu_optical_frame'] == 'camera_link'


def test_all_links_are_connected_to_one_root():
    root = expand(internal_frames=True)
    tree = parents(root)
    links = {link.get('name') for link in root.findall('link')}
    assert links - set(tree) == {'base_link'}


def test_poses_come_from_the_yaml(tmp_path):
    poses = yaml.safe_load(POSES_FILE.read_text())
    poses['laser'].update(x=1.25, y=-0.5, z=0.75)
    poses['sign_camera']['pitch'] = 0.2
    custom = tmp_path / 'poses.yaml'
    custom.write_text(yaml.safe_dump(poses))

    joints = {j.get('name'): j.find('origin') for j in expand(custom).findall('joint')}
    assert [float(v) for v in joints['laser_joint'].get('xyz').split()] == [1.25, -0.5, 0.75]
    assert float(joints['sign_camera_joint'].get('rpy').split()[1]) == pytest.approx(0.2)


def test_every_pose_is_marked_for_measuring():
    text = POSES_FILE.read_text()
    assert text.count('TODO: measure on rover') >= 4
