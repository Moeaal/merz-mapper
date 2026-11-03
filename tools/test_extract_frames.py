"""Unit tests for tools/extract_frames.py. The end-to-end test writes a real ROS 2 bag with the rosbags library."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

_spec = importlib.util.spec_from_file_location('extract_frames', Path(__file__).with_name('extract_frames.py'))
extract_frames = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(extract_frames)


def test_interval_selector_spaces_out_frames():
    selector = extract_frames.IntervalSelector(1.0)
    times = [0, 500_000_000, 1_000_000_000, 1_500_000_000, 2_100_000_000]
    assert [selector.wants(t) for t in times] == [True, False, True, False, True]


def test_decode_rgb_swaps_to_bgr():
    data = np.array([10, 20, 30], np.uint8)
    assert extract_frames.decode_raw_image(data, 1, 1, 'rgb8', 3)[0, 0].tolist() == [30, 20, 10]


def test_decode_handles_row_padding():
    # 1 pixel wide, 2 tall, with a step of 4: one padding byte per row must be ignored.
    data = np.array([1, 2, 3, 99, 4, 5, 6, 99], np.uint8)
    assert extract_frames.decode_raw_image(data, 2, 1, 'bgr8', 4)[1, 0].tolist() == [4, 5, 6]


def test_decode_mono_gives_three_channels():
    assert extract_frames.decode_raw_image(np.array([7], np.uint8), 1, 1, 'mono8', 1).shape == (1, 1, 3)


def test_decode_rejects_depth_images():
    with pytest.raises(ValueError, match='Unsupported'):
        extract_frames.decode_raw_image(np.zeros(2, np.uint8), 1, 1, '16UC1', 2)


def _write_bag(path: Path) -> None:
    from rosbags.rosbag2 import Writer
    from rosbags.typesys import Stores, get_typestore

    store = get_typestore(Stores.ROS2_HUMBLE)
    Image = store.types['sensor_msgs/msg/Image']
    Header = store.types['std_msgs/msg/Header']
    Time = store.types['builtin_interfaces/msg/Time']
    with Writer(path, version=8) as writer:
        connection = writer.add_connection('/cam', Image.__msgtype__, typestore=store)
        for index in range(5):
            stamp_ns = index * 500_000_000 + 1
            message = Image(
                header=Header(stamp=Time(sec=0, nanosec=stamp_ns), frame_id='cam'),
                height=2, width=2, encoding='rgb8', is_bigendian=0, step=6,
                data=np.full(12, index * 10, dtype=np.uint8),
            )
            writer.write(connection, stamp_ns, store.serialize_cdr(message, Image.__msgtype__))


def test_extract_from_a_real_bag(tmp_path):
    pytest.importorskip('rosbags')
    pytest.importorskip('cv2')
    bag = tmp_path / 'bag'
    _write_bag(bag)
    out = tmp_path / 'frames'

    assert extract_frames.extract(bag, '/cam', out, every_seconds=1.0) == 3   # at 0, 1 and 2 s
    assert len(list(out.glob('*.png'))) == 3


def test_extract_names_available_topics_when_the_topic_is_wrong(tmp_path):
    pytest.importorskip('rosbags')
    bag = tmp_path / 'bag'
    _write_bag(bag)
    with pytest.raises(ValueError, match="/cam"):
        extract_frames.extract(bag, '/wrong', tmp_path / 'frames', 1.0)
