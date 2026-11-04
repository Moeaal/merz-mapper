"""End an exploration run: stop the explorer, save the map and posegraph, compute the access zone.

The end rule is in mission.py. To finish by hand: ros2 service call /mission_node/finish std_srvs/srv/Trigger
"""
from pathlib import Path

import rclpy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from slam_toolbox.srv import SaveMap, SerializePoseGraph
from std_msgs.msg import Bool
from std_msgs.msg import String
from std_srvs.srv import Trigger
from visualization_msgs.msg import MarkerArray

from merz_exploration.mission import EndReason, MissionMonitor


class MissionNode(Node):

    def __init__(self) -> None:
        super().__init__('mission_node')
        group = ReentrantCallbackGroup()
        self._output_prefix = str(Path(self.declare_parameter('output_prefix', '~/merz_data/maps/run').value)
                                  .expanduser())
        Path(self._output_prefix).parent.mkdir(parents=True, exist_ok=True)
        self._monitor = MissionMonitor(
            max_duration_s=self.declare_parameter('max_duration_s', 1800.0).value,
            no_frontier_timeout_s=self.declare_parameter('no_frontier_timeout_s', 60.0).value,
            startup_grace_s=self.declare_parameter('startup_grace_s', 30.0).value,
        )
        self._ended = False
        self._resume = self.create_publisher(Bool, 'explore/resume', 10)
        self._save_map = self.create_client(SaveMap, '/slam_toolbox/save_map', callback_group=group)
        self._save_graph = self.create_client(SerializePoseGraph, '/slam_toolbox/serialize_map', callback_group=group)
        self._access_zone = self.create_client(Trigger, '/access_zone_node/compute', callback_group=group)
        self.create_subscription(MarkerArray, 'explore/frontiers', self._on_frontiers, 10, callback_group=group)
        self.create_service(Trigger, '~/finish', self._on_finish, callback_group=group)
        self._monitor.start(self._now_s())
        self.create_timer(1.0, self._on_timer, callback_group=group)

    def _now_s(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9

    def _on_frontiers(self, msg: MarkerArray) -> None:
        # explore_lite deletes old markers with DELETE actions, so count only those being added.
        count = sum(1 for marker in msg.markers if marker.action == marker.ADD)
        self._monitor.frontiers_seen(count, self._now_s())

    def _on_finish(self, _request: Trigger.Request, response: Trigger.Response) -> Trigger.Response:
        self._monitor.request_finish()
        response.success = True
        response.message = 'Finishing the mission.'
        return response

    async def _on_timer(self) -> None:
        reason = self._monitor.check(self._now_s())
        if reason is None or self._ended:
            return
        self._ended = True
        await self._finish(reason)

    async def _finish(self, reason: EndReason) -> None:
        self.get_logger().info(f'Mission ending: {reason.value}')
        self._resume.publish(Bool(data=False))   # the stop request goes out first, before any slow saving

        # slam_toolbox writes the .yaml and .pgm for the access zone, and the posegraph lets later entrances continue.
        await self._call(self._save_map, SaveMap.Request(name=String(data=self._output_prefix)), 'save map')
        await self._call(self._save_graph, SerializePoseGraph.Request(filename=self._output_prefix), 'save posegraph')
        result = await self._call(self._access_zone, Trigger.Request(), 'access zone')
        if result is not None:
            self.get_logger().info(result.message)
        self.get_logger().info(f'Mission complete. Outputs at {self._output_prefix}.*')

    async def _call(self, client, request, description: str):
        """Call a service. Failures are logged and do not stop the remaining saves."""
        if not client.wait_for_service(timeout_sec=5.0):
            self.get_logger().error(f'{description}: service not available')
            return None
        try:
            return await client.call_async(request)
        except Exception as error:   # any failure here must still let the other outputs be saved
            self.get_logger().error(f'{description} failed: {error}')
            return None


def main() -> None:
    rclpy.init()
    node = MissionNode()
    # Multi-threaded, so a timer that awaits a service does not block the service's response from being handled.
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
