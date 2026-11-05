"""Headless smoke check: do the map, odometry, sensor and TF topics publish? Exit code 0 = pass, 1 = fail.

    ros2 run merz_sim sim_check_node --ros-args -p odom_mode:=scan -p cameras:=false -p timeout_s:=120.0

It only checks that data flows. It says nothing about map quality, odometry accuracy or whether exploration finishes.
"""
import sys
import time

from nav_msgs.msg import OccupancyGrid
import rclpy
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data, ReliabilityPolicy
from rclpy.time import Time
from rosidl_runtime_py.utilities import get_message
from tf2_ros import Buffer, TransformListener

from merz_sim.topic_checks import CheckReport, expected_topics, FORBIDDEN_IN_SCAN_MODE, TRANSFORMS


class SimCheck(Node):

    def __init__(self) -> None:
        super().__init__('sim_check')
        self.odom_mode = self.declare_parameter('odom_mode', 'scan').value
        self.cameras = self.declare_parameter('cameras', True).value
        self.timeout_s = self.declare_parameter('timeout_s', 120.0).value
        self.report = CheckReport()
        self._subs = []
        self._buffer = Buffer()
        self._listener = TransformListener(self._buffer, self)
        for topic in expected_topics(self.odom_mode, self.cameras):
            self.report.received[topic] = 0
        for parent, child in TRANSFORMS:
            self.report.transforms[f'{parent}->{child}'] = False

    def subscribe_when_known(self) -> None:
        """Subscribe to each topic once its type is visible in the graph."""
        types = dict(self.get_topic_names_and_types())
        for topic in list(self.report.received):
            if topic in types and topic not in [s.topic_name for s in self._subs]:
                if topic == '/map':
                    qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                                     reliability=ReliabilityPolicy.RELIABLE)
                    msg_type = OccupancyGrid
                else:
                    qos, msg_type = qos_profile_sensor_data, get_message(types[topic][0])
                self._subs.append(self.create_subscription(msg_type, topic, self._counter(topic), qos))

    def _counter(self, topic: str):
        def count(_msg) -> None:
            self.report.received[topic] += 1
        return count

    def check_transforms(self) -> None:
        for parent, child in TRANSFORMS:
            key = f'{parent}->{child}'
            if not self.report.transforms[key]:
                self.report.transforms[key] = self._buffer.can_transform(parent, child, Time(),
                                                                         timeout=Duration(seconds=0.0))

    def check_forbidden(self) -> None:
        if self.odom_mode == 'scan':
            for topic in FORBIDDEN_IN_SCAN_MODE:
                self.report.forbidden_publishers[topic] = self.count_publishers(topic)


def main() -> None:
    rclpy.init()
    node = SimCheck()
    # Wall-clock deadline: if simulation time never starts, the check must still end.
    deadline = time.monotonic() + node.timeout_s
    while time.monotonic() < deadline and not node.report.passed:
        node.subscribe_when_known()
        rclpy.spin_once(node, timeout_sec=0.2)
        node.check_transforms()
        node.check_forbidden()
    node.check_forbidden()
    for line in node.report.lines():
        print(line, flush=True)
    passed = node.report.passed
    node.destroy_node()
    rclpy.try_shutdown()
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
