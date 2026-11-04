"""Static consistency checks across the workspace, by reading files only. They do not show that anything runs.

Catches the mistakes colcon or launch would only reveal on the Jetson: a launch file naming a missing config file, a node with no
entry point, a YAML section that does not match its node name, a remapped topic nobody provides.
"""
import ast
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / 'ros2_ws' / 'src'
LAUNCH_FILES = sorted(SRC.glob('*/launch/*.launch.py'))
PACKAGES = sorted(p.parent.name for p in SRC.glob('*/package.xml'))
PYTHON_PACKAGES = sorted(p.parent.name for p in SRC.glob('*/setup.py'))
THIRD_PARTY_EXECUTABLES = {
    ('sllidar_ros2', 'sllidar_node'), ('realsense2_camera', 'realsense2_camera_node'), ('usb_cam', 'usb_cam_node_exe'),
    ('joy', 'joy_node'), ('teleop_twist_joy', 'teleop_node'), ('twist_mux', 'twist_mux'),
    ('rf2o_laser_odometry', 'rf2o_laser_odometry_node'), ('robot_localization', 'ekf_node'),
    ('slam_toolbox', 'async_slam_toolbox_node'), ('robot_state_publisher', 'robot_state_publisher'), ('rviz2', 'rviz2'),
    ('explore_lite', 'explore'), ('nav2_map_server', 'map_server'), ('nav2_map_server', 'costmap_filter_info_server'),
    ('nav2_lifecycle_manager', 'lifecycle_manager'),
}


def launch_id(path: Path) -> str:
    return f'{path.parents[1].name}/{path.name}'


def literal_string(node: ast.AST):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def calls_named(tree: ast.AST, name: str) -> list[ast.Call]:
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call)
            and getattr(n.func, 'id', getattr(n.func, 'attr', None)) == name]


def keyword(call: ast.Call, name: str):
    for item in call.keywords:
        if item.arg == name:
            return item.value
    return None


def entry_points(package: str) -> dict[str, str]:
    text = (SRC / package / 'setup.py').read_text()
    return dict(re.findall(r'"(\w+) = ([\w.:]+)"', text))


def yaml_sections(package: str, file_name: str) -> set[str]:
    return set(yaml.safe_load((SRC / package / 'config' / file_name).read_text()))


def test_the_workspace_was_found():
    assert len(LAUNCH_FILES) >= 12
    assert set(PACKAGES) == {'merz_interfaces', 'merz_description', 'merz_bringup', 'merz_perception',
                             'merz_semantic_map', 'merz_exploration', 'merz_base'}


@pytest.mark.parametrize('path', sorted(SRC.rglob('*.yaml')), ids=lambda p: p.name)
def test_every_yaml_parses(path):
    assert yaml.safe_load(path.read_text()) is not None


@pytest.mark.parametrize('package', PACKAGES)
def test_package_xml_is_valid_and_named_after_its_folder(package):
    root = ET.parse(SRC / package / 'package.xml').getroot()
    assert root.findtext('name') == package
    assert root.findtext('export/build_type') in {'ament_python', 'ament_cmake'}


@pytest.mark.parametrize('package', PACKAGES)
def test_every_package_has_an_honest_readme(package):
    text = (SRC / package / 'README.md').read_text()
    assert 'IMPLEMENTED - not yet built or tested on hardware' in text.split('\n\n')[1]
    assert not re.search(r'\bTESTED\b', text)


@pytest.mark.parametrize('package', PYTHON_PACKAGES)
def test_entry_points_refer_to_a_real_main(package):
    for _name, target in entry_points(package).items():
        module, function = target.split(':')
        source = SRC / package / (module.replace('.', '/') + '.py')
        assert source.is_file(), source
        assert f'def {function}(' in source.read_text()


@pytest.mark.parametrize('path', LAUNCH_FILES, ids=launch_id)
def test_launch_file_has_a_description(path):
    assert 'def generate_launch_description' in path.read_text()


@pytest.mark.parametrize('path', LAUNCH_FILES, ids=launch_id)
def test_files_named_in_a_launch_file_exist(path):
    """Finds os.path.join(share..., 'folder', 'file') and _include('package', 'file')."""
    tree = ast.parse(path.read_text())
    own_package = path.parents[1].name
    share_of = {}
    for assign in (n for n in ast.walk(tree) if isinstance(n, ast.Assign)):
        if isinstance(assign.value, ast.Call) and getattr(assign.value.func, 'id', '') == 'get_package_share_directory':
            share_of[assign.targets[0].id] = literal_string(assign.value.args[0])
    for call in calls_named(tree, 'join'):
        first = call.args[0] if call.args else None
        package = None
        if isinstance(first, ast.Name):
            package = share_of.get(first.id)
        elif isinstance(first, ast.Call) and getattr(first.func, 'id', '') == 'get_package_share_directory':
            package = literal_string(first.args[0])
        if package is None or not package.startswith('merz_'):
            continue
        parts = [literal_string(a) for a in call.args[1:]]
        assert all(parts), f'{path.name}: path built from non-literal parts'
        assert (SRC / package / Path(*parts)).is_file(), f'{path.name} names missing {package}/{Path(*parts)}'
    for call in calls_named(tree, '_include'):
        package, file_name = (literal_string(a) for a in call.args[:2])
        if package and file_name:
            assert (SRC / package / 'launch' / file_name).is_file(), f'{path.name} includes missing {file_name}'
    assert own_package in PACKAGES


@pytest.mark.parametrize('path', LAUNCH_FILES, ids=launch_id)
def test_nodes_in_a_launch_file_exist(path):
    for call in calls_named(ast.parse(path.read_text()), 'Node'):
        package = literal_string(keyword(call, 'package'))
        executable = literal_string(keyword(call, 'executable'))
        if package in PYTHON_PACKAGES:
            assert executable in entry_points(package), f'{path.name}: no entry point {package} {executable}'
        else:
            assert (package, executable) in THIRD_PARTY_EXECUTABLES, f'{path.name}: unlisted {package} {executable}'


@pytest.mark.parametrize('config, package, names', [
    ('scan_odometry.yaml', 'merz_bringup', {'rf2o_laser_odometry', 'scan_odom_relay'}),
    ('ekf.yaml', 'merz_bringup', {'ekf_filter_node'}),
    ('slam.yaml', 'merz_bringup', {'slam_toolbox'}),
    ('teleop.yaml', 'merz_bringup', {'joy_node', 'teleop_node'}),
    ('twist_mux.yaml', 'merz_bringup', {'twist_mux'}),
    ('keepout.yaml', 'merz_bringup', {'filter_mask_server', 'costmap_filter_info_server'}),
    ('perception.yaml', 'merz_perception', {'detector_d455', 'detector_c920', 'sign_reader'}),
    ('semantic_map.yaml', 'merz_semantic_map', {'landmark_node'}),
    ('exploration.yaml', 'merz_exploration', {'explore_node', 'mission_node', 'access_zone_node',
                                              'junction_photo_node'}),
    ('base.yaml', 'merz_base', {'base_node'}),
])
def test_yaml_sections_match_node_names_used_in_launch(config, package, names):
    assert yaml_sections(package, config) == names
    launch_names = set()
    for path in LAUNCH_FILES:
        for call in calls_named(ast.parse(path.read_text()), 'Node'):
            launch_names.add(literal_string(keyword(call, 'name')))
    assert names <= launch_names


def test_parameters_read_by_python_nodes_are_declared_in_their_yaml():
    """A misspelt key in YAML is otherwise silently ignored, and the node just uses its default."""
    checks = [
        ('merz_bringup', 'scan_odom_relay_node.py', 'scan_odometry.yaml', 'scan_odom_relay'),
        ('merz_perception', 'detector_node.py', 'perception.yaml', 'detector_d455'),
        ('merz_perception', 'sign_reader_node.py', 'perception.yaml', 'sign_reader'),
        ('merz_semantic_map', 'landmark_node.py', 'semantic_map.yaml', 'landmark_node'),
        ('merz_exploration', 'junction_photo_node.py', 'exploration.yaml', 'junction_photo_node'),
        ('merz_exploration', 'mission_node.py', 'exploration.yaml', 'mission_node'),
        ('merz_exploration', 'access_zone_node.py', 'exploration.yaml', 'access_zone_node'),
    ]
    for package, node_file, config, section in checks:
        code = (SRC / package / package / node_file).read_text()
        declared = set(re.findall(r"declare_parameter\('(\w+)'", code))
        params = yaml.safe_load((SRC / package / 'config' / config).read_text())[section]['ros__parameters']
        unknown = set(params) - declared
        assert not unknown, f'{config} [{section}] has keys {node_file} never reads: {unknown}'


def test_base_node_yaml_keys_are_all_read():
    code = (SRC / 'merz_base' / 'merz_base' / 'base_node.py').read_text()
    declared = set(re.findall(r"declare_parameter\('(\w+)'", code)) | set(re.findall(r"'(\w+)':", code))
    params = yaml.safe_load((SRC / 'merz_base' / 'config' / 'base.yaml').read_text())['base_node']['ros__parameters']
    assert not set(params) - declared


def test_message_fields_used_in_python_exist():
    """rclpy would only raise this at runtime."""
    msg_dir = SRC / 'merz_interfaces' / 'msg'
    fields = {}
    for path in msg_dir.glob('*.msg'):
        lines = (line.split('#')[0].split() for line in path.read_text().splitlines())
        fields[path.stem] = {parts[1] for parts in lines if len(parts) >= 2}
    aliases = {'DetectionMsg': 'Detection'}
    for path in SRC.glob('merz_*/merz_*/*_node.py'):
        for call in (n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.Call)):
            name = aliases.get(getattr(call.func, 'id', None), getattr(call.func, 'id', None))
            if name in fields and path.name != 'junction_photo_node.py':
                for item in call.keywords:
                    assert item.arg in fields[name], f'{path.name}: {name} has no field {item.arg}'


def test_cmake_lists_every_message():
    cmake = (SRC / 'merz_interfaces' / 'CMakeLists.txt').read_text()
    for path in (SRC / 'merz_interfaces' / 'msg').glob('*.msg'):
        assert f'msg/{path.name}' in cmake


def test_imported_ros_packages_are_declared_as_dependencies():
    mapping = {'cv_bridge': 'cv_bridge', 'message_filters': 'message_filters', 'tf2_ros': 'tf2_ros',
               'merz_interfaces': 'merz_interfaces', 'nav_msgs': 'nav_msgs', 'sensor_msgs': 'sensor_msgs',
               'geometry_msgs': 'geometry_msgs', 'std_msgs': 'std_msgs', 'std_srvs': 'std_srvs',
               'visualization_msgs': 'visualization_msgs', 'slam_toolbox': 'slam_toolbox',
               'merz_semantic_map': 'merz_semantic_map', 'builtin_interfaces': 'builtin_interfaces',
               'rclpy': 'rclpy', 'cv2': 'python3-opencv', 'yaml': 'python3-yaml', 'numpy': 'python3-numpy'}
    for package in PYTHON_PACKAGES:
        depends = {e.text for e in ET.parse(SRC / package / 'package.xml').getroot().iter('exec_depend')}
        for path in (SRC / package / package).glob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                modules = []
                if isinstance(node, ast.Import):
                    modules = [alias.name.split('.')[0] for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    modules = [node.module.split('.')[0]]
                for module in modules:
                    if module in mapping and module != package:
                        assert mapping[module] in depends, f'{package}: {path.name} imports {module}, undeclared'


def test_no_core_module_imports_ros():
    """The design rule: logic lives in plain Python that can be tested on Windows."""
    for path in SRC.glob('merz_*/merz_*/*.py'):
        if not path.name.endswith('_node.py'):
            assert 'import rclpy' not in path.read_text(), path


def test_status_never_claims_tested():
    for path in SRC.glob('*/README.md'):
        assert 'IMPLEMENTED - not yet built or tested on hardware' in path.read_text(), path
