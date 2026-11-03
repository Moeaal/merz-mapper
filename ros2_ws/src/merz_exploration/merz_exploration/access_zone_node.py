"""Service wrapper: compute the access zone from a saved map on request. The logic is in compute_access_zones.py."""
import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger

from merz_exploration.compute_access_zones import store_zone


class AccessZoneNode(Node):

    def __init__(self) -> None:
        super().__init__('access_zone_node')
        self._map_yaml = self.declare_parameter('map_yaml', '').value
        self._database = self.declare_parameter('database', '~/merz_data/merz.sqlite').value
        self._entrance = self.declare_parameter('entrance', '').value
        self._entrance_name = self.declare_parameter('entrance_name', '').value
        self._start_x = self.declare_parameter('start_x', 0.0).value
        self._start_y = self.declare_parameter('start_y', 0.0).value
        self._start_yaw = self.declare_parameter('start_yaw', 0.0).value
        self._landmark_adjacency = self.declare_parameter('landmark_adjacency_m', 0.5).value
        self._junction_adjacency = self.declare_parameter('junction_adjacency_m', 0.5).value
        self.create_service(Trigger, '~/compute', self._on_compute)

    def _on_compute(self, _request: Trigger.Request, response: Trigger.Response) -> Trigger.Response:
        try:
            result = store_zone(self._map_yaml, self._database, self._entrance,
                                self._entrance_name or self._entrance, self._start_x, self._start_y, self._start_yaw,
                                self._landmark_adjacency, self._junction_adjacency)
        except (OSError, ValueError, KeyError) as error:
            response.success = False
            response.message = f'Could not compute the access zone: {error}'
            self.get_logger().error(response.message)
            return response
        response.success = True
        response.message = (f'{self._entrance}: {result.area_m2:.1f} m2, {len(result.landmark_ids)} landmarks, '
                            f'{len(result.junction_ids)} junctions')
        self.get_logger().info(response.message)
        return response


def main() -> None:
    rclpy.init()
    node = AccessZoneNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
