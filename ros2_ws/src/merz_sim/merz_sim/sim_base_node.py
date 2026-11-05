"""Simulated base: /cmd_vel_mux -> merz_base BaseController -> /sim/cmd_vel (bridged to Gazebo's DiffDrive).

It takes the place of merz_base's base_node in simulation, so twist_mux, the gamepad/keyboard override and Nav2 all
connect exactly as on the rover. Unlike base_node it uses the ROS clock (simulation time): the simulator can run
slower than real time, and the timeout must count simulated seconds.
"""
from geometry_msgs.msg import Twist
import rclpy
from rclpy.node import Node

from merz_base.base_controller import BaseController, BaseLimits, check_update_rate
from merz_sim.twist_backend import TwistBackend


class SimBaseNode(Node):

    def __init__(self) -> None:
        super().__init__('sim_base_node')
        track = self.declare_parameter('track_width_m', 0.44).value
        full_speed = self.declare_parameter('full_speed_m_s', 1.0).value
        limits = BaseLimits(
            max_linear_m_s=self.declare_parameter('max_linear_m_s', 0.5).value,
            max_angular_rad_s=self.declare_parameter('max_angular_rad_s', 1.0).value,
            max_linear_accel_m_s2=self.declare_parameter('max_linear_accel_m_s2', 0.5).value,
            max_angular_accel_rad_s2=self.declare_parameter('max_angular_accel_rad_s2', 1.0).value,
            track_width_m=track,
            full_speed_m_s=full_speed,
            command_timeout_s=self.declare_parameter('command_timeout_s', 0.5).value,
        )
        period_s = check_update_rate(self.declare_parameter('update_rate_hz', 20.0).value)
        self._publisher = self.create_publisher(Twist, 'sim_cmd_vel', 10)
        self._controller = BaseController(limits, TwistBackend(self._send, full_speed, track))
        self.create_subscription(Twist, 'cmd_vel', self._on_command, 10)
        self.create_timer(period_s, self._on_timer)

    def _now_s(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9

    def _send(self, linear: float, angular: float) -> None:
        msg = Twist()
        msg.linear.x = float(linear)
        msg.angular.z = float(angular)
        self._publisher.publish(msg)

    def _on_command(self, msg: Twist) -> None:
        self._controller.on_command(msg.linear.x, msg.angular.z, self._now_s())

    def _on_timer(self) -> None:
        self._controller.update(self._now_s())

    def close(self) -> None:
        self._controller.close()


def main() -> None:
    rclpy.init()
    node = SimBaseNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.close()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
