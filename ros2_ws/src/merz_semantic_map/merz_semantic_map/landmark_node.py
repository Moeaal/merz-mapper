"""Turn detections into map-frame landmarks and store them. All the logic is in localiser.py and database.py."""
import math
from pathlib import Path

from builtin_interfaces.msg import Time
import cv2
from cv_bridge import CvBridge
from geometry_msgs.msg import Point
from message_filters import ApproximateTimeSynchronizer, Subscriber
import numpy as np
import rclpy
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time as RclpyTime
from sensor_msgs.msg import CameraInfo, Image
from tf2_ros import Buffer, TransformException, TransformListener

from merz_interfaces.msg import DetectionArray, Landmark, LandmarkArray, SignReading
from merz_semantic_map.database import MerzDatabase
from merz_semantic_map.geometry import BoundingBox, Intrinsics, transform_matrix
from merz_semantic_map.localiser import LandmarkMap, LocaliserConfig, locate_in_map


def stamp_to_seconds(stamp: Time) -> float:
    return stamp.sec + stamp.nanosec * 1e-9


def seconds_to_stamp(seconds: float) -> Time:
    sec = int(math.floor(seconds))
    return Time(sec=sec, nanosec=int((seconds - sec) * 1e9))


def intrinsics_from(info: CameraInfo) -> Intrinsics:
    return Intrinsics(fx=info.k[0], fy=info.k[4], cx=info.k[2], cy=info.k[5])


class LandmarkNode(Node):

    def __init__(self) -> None:
        super().__init__('landmark_node')
        self._map_frame = self.declare_parameter('map_frame', 'map').value
        self._tf_timeout = Duration(seconds=self.declare_parameter('tf_timeout_s', 0.2).value)
        self._depth_scale = self.declare_parameter('depth_scale_m', 0.001).value   # D455 16UC1 is in millimetres
        self._photo_dir = Path(self.declare_parameter('photo_dir', '~/merz_data/photos').value).expanduser()
        self._photo_dir.mkdir(parents=True, exist_ok=True)
        self._config = LocaliserConfig(
            min_depth_m=self.declare_parameter('min_depth_m', 0.6).value,
            max_depth_m=self.declare_parameter('max_depth_m', 6.0).value,
            gate_m=self.declare_parameter('gate_m', 1.0).value,
            fusion_mode=self.declare_parameter('fusion_mode', 'fused').value,
        )
        self._landmarks = LandmarkMap(self._config)
        self._database = MerzDatabase(self.declare_parameter('database', '~/merz_data/merz.sqlite').value)
        self._landmarks.restore(self._database.landmarks())   # a later run adds to the same database
        self._bridge = CvBridge()
        self._sign_intrinsics: Intrinsics | None = None
        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)
        self._publisher = self.create_publisher(LandmarkArray, 'landmarks', 10)

        self.create_subscription(CameraInfo, 'sign_camera_info', self._on_sign_camera_info, qos_profile_sensor_data)
        self.create_subscription(SignReading, 'sign_readings', self._on_sign_reading, 10)
        # Detections are produced from the colour image; aligned depth is stamped close to it.
        self._sync = ApproximateTimeSynchronizer([
            Subscriber(self, DetectionArray, 'detections'),
            Subscriber(self, Image, 'depth', qos_profile=qos_profile_sensor_data),
            Subscriber(self, CameraInfo, 'depth_camera_info', qos_profile=qos_profile_sensor_data),
        ], queue_size=self.declare_parameter('sync_queue_size', 30).value,
            slop=self.declare_parameter('sync_slop_s', 0.05).value)
        self._sync.registerCallback(self._on_detections)

    def _lookup(self, frame: str, stamp: Time) -> np.ndarray | None:
        """Pose of a camera in the map at the image's time. None means the observation must be rejected (O4 risk)."""
        try:
            transform = self._tf_buffer.lookup_transform(
                self._map_frame, frame, RclpyTime.from_msg(stamp), timeout=self._tf_timeout).transform
        except TransformException as error:
            self.get_logger().warn(f'Observation rejected, no pose at image time: {error}',
                                   throttle_duration_sec=5.0)
            return None
        t, q = transform.translation, transform.rotation
        return transform_matrix((t.x, t.y, t.z), (q.x, q.y, q.z, q.w))

    def _on_detections(self, detections: DetectionArray, depth: Image, info: CameraInfo) -> None:
        if not detections.detections:
            return
        pose = self._lookup(depth.header.frame_id, depth.header.stamp)
        if pose is None:
            return
        depth_m = self._bridge.imgmsg_to_cv2(depth, desired_encoding='passthrough').astype(np.float32)
        if depth.encoding == '16UC1':
            depth_m = depth_m * self._depth_scale
        intrinsics = intrinsics_from(info)
        stamp_s = stamp_to_seconds(depth.header.stamp)
        for detection in detections.detections:
            box = BoundingBox(detection.x_min, detection.y_min, detection.x_max, detection.y_max)
            position = locate_in_map(box, depth_m, intrinsics, pose, self._config)
            if position is None:
                continue
            landmark, _is_new = self._landmarks.add_observation(detection.label, position, detection.confidence,
                                                                stamp_s)
            self._store(landmark)
            self._database.add_observation(landmark.landmark_id, position, confidence=float(detection.confidence),
                                           stamp=stamp_s)
        self._publish(detections.header.stamp)

    def _on_sign_camera_info(self, info: CameraInfo) -> None:
        self._sign_intrinsics = intrinsics_from(info)

    def _on_sign_reading(self, reading: SignReading) -> None:
        if self._sign_intrinsics is None:
            return
        pose = self._lookup(reading.header.frame_id, reading.header.stamp)
        if pose is None:
            return
        d = reading.detection
        landmark = self._landmarks.attach_text(reading.text, BoundingBox(d.x_min, d.y_min, d.x_max, d.y_max),
                                               self._sign_intrinsics, pose)
        if landmark is None:
            self.get_logger().info(f"Read '{reading.text}' but no sign landmark projects into its box yet")
            return
        self._store(landmark)

    def _store(self, landmark) -> None:
        covariance = landmark.covariance
        self._database.upsert_landmark(
            landmark.landmark_id, landmark.landmark_class, landmark.text, landmark.position,
            (covariance[0, 0], covariance[1, 1], covariance[2, 2]), landmark.confidence, landmark.count,
            landmark.first_seen_s, landmark.last_seen_s)

    def _publish(self, stamp: Time) -> None:
        output = LandmarkArray()
        output.header.stamp = stamp
        output.header.frame_id = self._map_frame
        for landmark in self._landmarks.landmarks:
            x, y, z = (float(v) for v in landmark.position)
            output.landmarks.append(Landmark(
                id=landmark.landmark_id, landmark_class=landmark.landmark_class, text=landmark.text,
                position=Point(x=x, y=y, z=z), covariance=[float(v) for v in landmark.covariance.flatten()],
                confidence=float(landmark.confidence), observation_count=landmark.count,
                photo_path=landmark.photo_path, first_seen=seconds_to_stamp(landmark.first_seen_s),
                last_seen=seconds_to_stamp(landmark.last_seen_s)))
        self._publisher.publish(output)

    def close(self) -> None:
        self._database.close()


def main() -> None:
    rclpy.init()
    node = LandmarkNode()
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
