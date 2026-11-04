"""Drive the motors from /cmd_vel_mux. The logic is in base_controller.py and backends.py."""
import time

from geometry_msgs.msg import Twist
import rclpy
from rclpy.node import Node

from merz_base.backends import make_backend
from merz_base.base_controller import BaseController, BaseLimits, check_update_rate

_BACKEND_DEFAULTS = {
    'serial_port': '/dev/merz_motors',
    'serial_baud': 115200,
    'serial_drive_format': 'M {left:.3f} {right:.3f}\n',
    'serial_stop_command': 'M 0 0\n',
    'serial_scale': 1.0,
    'gpio_left_pwm': -1,
    'gpio_left_forward': -1,
    'gpio_left_reverse': -1,
    'gpio_right_pwm': -1,
    'gpio_right_forward': -1,
    'gpio_right_reverse': -1,
    'gpio_pwm_frequency_hz': 1000.0,
}


class BaseNode(Node):

    def __init__(self) -> None:
        super().__init__('base_node')
        backend_name = self.declare_parameter('backend', 'mock').value
        config = {key: self.declare_parameter(key, value).value for key, value in _BACKEND_DEFAULTS.items()}
        limits = BaseLimits(
            max_linear_m_s=self.declare_parameter('max_linear_m_s', 0.5).value,
            max_angular_rad_s=self.declare_parameter('max_angular_rad_s', 1.0).value,
            max_linear_accel_m_s2=self.declare_parameter('max_linear_accel_m_s2', 0.5).value,
            max_angular_accel_rad_s2=self.declare_parameter('max_angular_accel_rad_s2', 1.0).value,
            track_width_m=self.declare_parameter('track_width_m', 0.4).value,
            full_speed_m_s=self.declare_parameter('full_speed_m_s', 1.0).value,
            command_timeout_s=self.declare_parameter('command_timeout_s', 0.5).value,
        )
        period_s = check_update_rate(self.declare_parameter('update_rate_hz', 20.0).value)
        self._controller = BaseController(limits, make_backend(backend_name, config))
        if backend_name == 'mock':
            self.get_logger().warn('Mock backend: no motor will move. Set "backend" in config/base.yaml.')
        self.create_subscription(Twist, 'cmd_vel', self._on_command, 10)
        self.create_timer(period_s, self._on_timer)

    # time.monotonic, not ROS time: a safety timeout must work even if the ROS clock stops or jumps.
    def _on_command(self, msg: Twist) -> None:
        self._controller.on_command(msg.linear.x, msg.angular.z, time.monotonic())

    def _on_timer(self) -> None:
        self._controller.update(time.monotonic())

    def close(self) -> None:
        self._controller.close()


def main() -> None:
    rclpy.init()
    node = BaseNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Stop the motors first, whatever else goes wrong during shutdown.
        node.close()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
