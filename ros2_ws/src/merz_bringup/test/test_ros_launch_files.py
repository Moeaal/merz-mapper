"""RUN ON JETSON (or the Pi). Needs ROS 2 and a built workspace; skipped on Windows. Starts no hardware.

Loads every launch file's description, which shows that it imports and that its packages and files are installed.
"""
from pathlib import Path

import pytest

pytest.importorskip('launch')
pytest.importorskip('ament_index_python')

from launch import LaunchContext, LaunchDescription  # noqa: E402
from launch.launch_description_sources import PythonLaunchDescriptionSource  # noqa: E402

SRC = Path(__file__).resolve().parents[2]
# merz_sim is optional (decisions #23) and is not a dependency of merz_bringup, so colcon does not put its Python
# module on this test's path: sim.launch.py failed here with "No module named 'merz_sim'" on the Jetson (2026-11-10).
# Its launch file is checked by merz_sim's own tests and by tools/test_static_refs.py.
OPTIONAL_PACKAGES = {'merz_sim'}
LAUNCH_FILES = sorted(p for p in SRC.glob('*/launch/*.launch.py') if p.parents[1].name not in OPTIONAL_PACKAGES)


@pytest.mark.parametrize('path', LAUNCH_FILES, ids=lambda p: p.name)
def test_launch_file_loads(path):
    description = PythonLaunchDescriptionSource(str(path)).get_launch_description(LaunchContext())
    assert isinstance(description, LaunchDescription)
