"""Pull images out of a ROS 2 bag, for labelling a custom YOLO dataset. Runs without ROS (uses the rosbags library).

    python tools/extract_frames.py ~/merz_data/bags/20261201_corridor --topic /sign_cam/image_raw/compressed \
        --out frames/ --every-seconds 2

Saving a frame every few seconds avoids labelling hundreds of near-identical images of a corridor.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


class IntervalSelector:
    """Choose frames at least a set time apart. Time comes from the bag, so results repeat exactly."""

    def __init__(self, every_seconds: float) -> None:
        self._every_ns = int(every_seconds * 1e9)
        self._next_ns: int | None = None

    def wants(self, timestamp_ns: int) -> bool:
        if self._next_ns is not None and timestamp_ns < self._next_ns:
            return False
        self._next_ns = timestamp_ns + self._every_ns
        return True


def decode_raw_image(data: np.ndarray, height: int, width: int, encoding: str, step: int) -> np.ndarray:
    """Convert sensor_msgs/Image data to BGR, ready for cv2.imwrite."""
    channels = {'rgb8': 3, 'bgr8': 3, 'mono8': 1}.get(encoding)
    if channels is None:
        raise ValueError(f'Unsupported encoding: {encoding}')
    rows = np.asarray(data, dtype=np.uint8).reshape(height, step)
    image = rows[:, :width * channels]
    if channels == 1:
        return np.stack([image] * 3, axis=2)
    image = image.reshape(height, width, 3)
    return image[..., ::-1].copy() if encoding == 'rgb8' else image.copy()


def extract(bag: Path, topic: str, out: Path, every_seconds: float) -> int:
    """Write selected frames as PNGs named by bag timestamp. Returns the number written."""
    import cv2
    from rosbags.highlevel import AnyReader

    out.mkdir(parents=True, exist_ok=True)
    selector = IntervalSelector(every_seconds)
    written = 0
    with AnyReader([bag]) as reader:
        connections = [c for c in reader.connections if c.topic == topic]
        if not connections:
            available = sorted({c.topic for c in reader.connections})
            raise ValueError(f"Topic '{topic}' is not in the bag. Available: {available}")
        for connection, timestamp, raw in reader.messages(connections=connections):
            if not selector.wants(timestamp):
                continue
            message = reader.deserialize(raw, connection.msgtype)
            if connection.msgtype.endswith('CompressedImage'):
                image = cv2.imdecode(np.asarray(message.data, dtype=np.uint8), cv2.IMREAD_COLOR)
            else:
                image = decode_raw_image(message.data, message.height, message.width, message.encoding, message.step)
            cv2.imwrite(str(out / f'{timestamp}.png'), image)
            written += 1
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('bag', type=Path, help='Bag directory.')
    parser.add_argument('--topic', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--every-seconds', type=float, default=2.0)
    args = parser.parse_args()
    print(f'Wrote {extract(args.bag, args.topic, args.out, args.every_seconds)} frames to {args.out}')


if __name__ == '__main__':
    main()
