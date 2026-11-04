"""Republish rf2o odometry with a covariance set, for the EKF. The logic is in odom_covariance.py."""
import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node

from merz_bringup.odom_covariance import ScanOdomNoise, is_plausible, pose_covariance, twist_covariance


class ScanOdomRelay(Node):

    def __init__(self) -> None:
        super().__init__('scan_odom_relay')
        self._noise = ScanOdomNoise(
            vx_std=self.declare_parameter('vx_std', 0.05).value,
            vy_std=self.declare_parameter('vy_std', 0.05).value,
            vyaw_std=self.declare_parameter('vyaw_std', 0.1).value,
            max_speed=self.declare_parameter('max_speed', 1.5).value,
            max_yaw_rate=self.declare_parameter('max_yaw_rate', 3.0).value,
        )
        self._twist_covariance = twist_covariance(self._noise)
        self._pose_covariance = pose_covariance()
        self._publisher = self.create_publisher(Odometry, 'odom_out', 10)
        self.create_subscription(Odometry, 'odom_in', self._on_odom, 10)

    def _on_odom(self, msg: Odometry) -> None:
        twist = msg.twist.twist
        if not is_plausible(twist.linear.x, twist.linear.y, twist.angular.z, self._noise):
            self.get_logger().warn(
                f'Dropped implausible scan odometry: vx={twist.linear.x:.2f} m/s, '
                f'vyaw={twist.angular.z:.2f} rad/s', throttle_duration_sec=2.0)
            return
        msg.twist.covariance = self._twist_covariance
        msg.pose.covariance = self._pose_covariance
        self._publisher.publish(msg)


def main() -> None:
    rclpy.init()
    node = ScanOdomRelay()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
