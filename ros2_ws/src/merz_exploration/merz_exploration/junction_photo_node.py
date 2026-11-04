"""Save a photo and pose at each corridor junction, for the website's directions. The rule is in junctions.py."""
from pathlib import Path

import cv2
from cv_bridge import CvBridge
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import Image, LaserScan
from tf2_ros import Buffer, TransformException, TransformListener

from merz_exploration.junctions import JunctionTracker, is_junction, open_sector_count
from merz_semantic_map.database import MerzDatabase


class JunctionPhotoNode(Node):

    def __init__(self) -> None:
        super().__init__('junction_photo_node')
        self._map_frame = self.declare_parameter('map_frame', 'map').value
        self._base_frame = self.declare_parameter('base_frame', 'base_link').value
        self._open_range_m = self.declare_parameter('open_range_m', 3.0).value
        self._min_open_sectors = self.declare_parameter('min_open_sectors', 3).value
        self._laser_yaw = self.declare_parameter('laser_yaw_rad', 0.0).value
        self._photo_dir = Path(self.declare_parameter('photo_dir', '~/merz_data/photos').value).expanduser()
        self._photo_dir.mkdir(parents=True, exist_ok=True)
        self._database = MerzDatabase(self.declare_parameter('database', '~/merz_data/merz.sqlite').value)
        self._tracker = JunctionTracker(min_spacing_m=self.declare_parameter('min_spacing_m', 3.0).value)
        # Database ids of the junctions, in the tracker's order.
        self._junction_ids: list[int] = []
        for row in self._database.junctions():   # a later run links to the junctions found earlier
            self._tracker.positions.append((row['x'], row['y']))
            self._junction_ids.append(row['id'])
        self._bridge = CvBridge()
        self._latest_image: Image | None = None
        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)
        self.create_subscription(Image, 'image', self._on_image, qos_profile_sensor_data)
        self.create_subscription(LaserScan, 'scan', self._on_scan, qos_profile_sensor_data)

    def _on_image(self, msg: Image) -> None:
        self._latest_image = msg

    def _on_scan(self, scan: LaserScan) -> None:
        try:
            transform = self._tf_buffer.lookup_transform(self._map_frame, self._base_frame, Time()).transform
        except TransformException:
            return     # no map yet
        x, y = transform.translation.x, transform.translation.y
        self._tracker.update_pose(x, y)
        sectors = open_sector_count(scan.ranges, scan.angle_min, scan.angle_increment, self._open_range_m,
                                    self._laser_yaw)
        if not is_junction(sectors, self._min_open_sectors):
            return
        index, is_new, edge = self._tracker.arrive(x, y)
        if is_new:
            self._junction_ids.append(self._database.add_junction(x, y, self._save_photo(x, y, scan)))
            self.get_logger().info(f'Junction {self._junction_ids[-1]} at ({x:.1f}, {y:.1f})')
        if edge is not None:
            self._database.add_junction_edge(self._junction_ids[edge[0]], self._junction_ids[index], edge[1])

    def _save_photo(self, x: float, y: float, scan: LaserScan) -> int | None:
        """Save the latest camera image. A junction without a photo is still useful for routing, so None is allowed."""
        if self._latest_image is None:
            return None
        stamp = scan.header.stamp.sec + scan.header.stamp.nanosec * 1e-9
        path = self._photo_dir / f'junction_{scan.header.stamp.sec}_{scan.header.stamp.nanosec}.jpg'
        image = self._bridge.imgmsg_to_cv2(self._latest_image, desired_encoding='bgr8')
        if not cv2.imwrite(str(path), image):
            self.get_logger().error(f'Could not save {path}')
            return None
        return self._database.add_photo(str(path), x, y, None, stamp)

    def close(self) -> None:
        self._database.close()


def main() -> None:
    rclpy.init()
    node = JunctionPhotoNode()
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
