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
LAUNCH_FILES = sorted(SRC.glob('*/launch/*.launch.py'))


@pytest.mark.parametrize('path', LAUNCH_FILES, ids=lambda p: p.name)
def test_launch_file_loads(path):
    description = PythonLaunchDescriptionSource(str(path)).get_launch_description(LaunchContext())
    assert isinstance(description, LaunchDescription)
