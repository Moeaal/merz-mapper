"""RUN ON JETSON (or the Pi). Needs ROS 2; skipped on Windows. Uses the mock backend, so nothing moves.

Shows that the node's plumbing and timeout work with real ROS messages and timers. It does NOT show that real motors stop: test that
with the wheels off the ground, using the checklist in merz_bringup/README.md.
"""
import time

import pytest

rclpy = pytest.importorskip('rclpy')

from geometry_msgs.msg import Twist  # noqa: E402
from rclpy.executors import SingleThreadedExecutor  # noqa: E402

from merz_base.base_node import BaseNode  # noqa: E402


def test_commands_reach_the_backend_and_the_timeout_stops_it():
    rclpy.init()
    node = BaseNode()      # the default backend is mock
    backend = node._controller._backend
    helper = rclpy.create_node('base_test_helper')
    publisher = helper.create_publisher(Twist, 'cmd_vel', 10)
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    executor.add_node(helper)
    command = Twist()
    command.linear.x = 0.2

    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline and not backend.commands:
        publisher.publish(command)
        executor.spin_once(timeout_sec=0.02)
    assert backend.commands, 'no command reached the backend'
    assert node._controller.timed_out is False

    # Stop publishing, and let the default 0.5 s timeout pass.
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and not node._controller.timed_out:
        executor.spin_once(timeout_sec=0.02)
    assert node._controller.timed_out
    assert backend.stop_count > 0

    node.close()
    assert backend.closed
    node.destroy_node()
    helper.destroy_node()
    rclpy.try_shutdown()
