"""RUN ON JETSON (or the Pi). Needs ROS 2; skipped on Windows. No hardware: messages are published by the test."""
import time

import pytest

rclpy = pytest.importorskip('rclpy')

from nav_msgs.msg import Odometry  # noqa: E402
from rclpy.executors import SingleThreadedExecutor  # noqa: E402

from merz_bringup.scan_odom_relay_node import ScanOdomRelay  # noqa: E402


@pytest.fixture
def ros():
    rclpy.init()
    yield
    rclpy.try_shutdown()


def _exchange(vx: float) -> list[Odometry]:
    relay = ScanOdomRelay()
    helper = rclpy.create_node('relay_test_helper')
    received: list[Odometry] = []
    helper.create_subscription(Odometry, 'odom_out', received.append, 10)
    publisher = helper.create_publisher(Odometry, 'odom_in', 10)
    message = Odometry()
    message.twist.twist.linear.x = vx
    executor = SingleThreadedExecutor()
    executor.add_node(relay)
    executor.add_node(helper)
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline and not received:
        publisher.publish(message)
        executor.spin_once(timeout_sec=0.05)
    relay.destroy_node()
    helper.destroy_node()
    return received


def test_relay_adds_covariance(ros):
    received = _exchange(0.2)
    assert received, 'nothing came out of the relay'
    assert received[0].twist.twist.linear.x == pytest.approx(0.2)
    assert received[0].twist.covariance[0] > 0


def test_relay_drops_implausible_speed(ros):
    assert not _exchange(50.0)
