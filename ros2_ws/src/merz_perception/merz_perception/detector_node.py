"""Run the detector at a few Hz on one camera. The logic is in engines.py."""
import time

from cv_bridge import CvBridge
import rclpy
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image

from merz_interfaces.msg import Detection as DetectionMsg
from merz_interfaces.msg import DetectionArray
from merz_perception.engines import RateLimiter, keep_labels, make_engine


class DetectorNode(Node):

    def __init__(self) -> None:
        super().__init__('detector')
        self._engine = make_engine(
            self.declare_parameter('engine', 'ultralytics').value,
            self.declare_parameter('weights', '').value,
            self.declare_parameter('confidence', 0.25).value,
            self.declare_parameter('image_size', 640).value,
        )
        self._allowed = self.declare_parameter('allowed_labels', ['']).value
        self._allowed = [label for label in self._allowed if label]
        self._limiter = RateLimiter(self.declare_parameter('rate_hz', 3.0).value)
        self._bridge = CvBridge()
        self._publisher = self.create_publisher(DetectionArray, 'detections', 10)
        # Depth 1: if inference falls behind, process the newest image instead of a growing backlog.
        qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT, history=HistoryPolicy.KEEP_LAST, depth=1)
        self.create_subscription(Image, 'image', self._on_image, qos)

    def _on_image(self, msg: Image) -> None:
        if not self._limiter.ready(time.monotonic()):
            return
        image = self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        output = DetectionArray()
        output.header = msg.header   # the image's stamp, so depth and TF can be matched to it later
        for detection in keep_labels(self._engine.detect(image), self._allowed):
            output.detections.append(DetectionMsg(
                label=detection.label, confidence=float(detection.confidence),
                x_min=float(detection.x_min), y_min=float(detection.y_min),
                x_max=float(detection.x_max), y_max=float(detection.y_max)))
        self._publisher.publish(output)


def main() -> None:
    rclpy.init()
    node = DetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
