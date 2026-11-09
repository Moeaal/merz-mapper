"""Read room numbers from sign detections, using the original camera image. Logic: sharpness, ocr, room_numbers."""
from cv_bridge import CvBridge
from message_filters import Subscriber, TimeSynchronizer
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image

from merz_interfaces.msg import DetectionArray, SignReading
from merz_perception.engines import Detection, clip_box
from merz_perception.ocr import make_ocr, prepare_crop, read_room_number
from merz_perception.room_numbers import ReadAgreement, RoomNumberValidator
from merz_perception.sharpness import is_sharp


class SignReaderNode(Node):

    def __init__(self) -> None:
        super().__init__('sign_reader')
        self._ocr = make_ocr(self.declare_parameter('ocr_engine', 'auto').value)
        self._validator = RoomNumberValidator(self.declare_parameter('room_regex', '').value)
        self._min_sharpness = self.declare_parameter('min_sharpness', 100.0).value
        self._sign_label = self.declare_parameter('sign_label', 'room_sign').value
        self._agreement = ReadAgreement(self.declare_parameter('min_agreement', 2).value,
                                        self.declare_parameter('agreement_window_s', 10.0).value)
        queue_size = self.declare_parameter('sync_queue_size', 20).value
        self._bridge = CvBridge()
        self._publisher = self.create_publisher(SignReading, 'sign_readings', 10)
        # Only runs when a detection arrives, so OCR costs nothing while no sign is in view. Detections carry their
        # image's exact stamp, so an exact-time filter is correct. The queue must span the detector's latency.
        self._sync = TimeSynchronizer([
            Subscriber(self, Image, 'image', qos_profile=qos_profile_sensor_data),
            Subscriber(self, DetectionArray, 'detections'),
        ], queue_size)
        self._sync.registerCallback(self._on_detections)

    def _on_detections(self, image_msg: Image, detections: DetectionArray) -> None:
        signs = [d for d in detections.detections if d.label == self._sign_label]
        if not signs:
            return
        image = self._bridge.imgmsg_to_cv2(image_msg, desired_encoding='bgr8')
        height, width = image.shape[:2]
        now_s = self.get_clock().now().nanoseconds * 1e-9
        for sign in signs:
            box = Detection(sign.label, sign.confidence, sign.x_min, sign.y_min, sign.x_max, sign.y_max)
            x0, y0, x1, y1 = clip_box(box, width, height, margin=0.1)
            crop = image[y0:y1, x0:x1]
            if crop.size == 0 or not is_sharp(crop, self._min_sharpness):
                continue
            result, text = read_room_number(self._ocr, prepare_crop(crop), self._validator)
            if result is None:
                continue
            if text is None:
                self.get_logger().info(f"Rejected OCR text '{result.text}'")
                continue
            if self._agreement.add(text, now_s):
                self._publisher.publish(SignReading(
                    header=image_msg.header, text=text, raw_text=result.text,
                    confidence=float(result.confidence), detection=sign))


def main() -> None:
    rclpy.init()
    node = SignReaderNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
