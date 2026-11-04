"""RUN ON JETSON (or the Pi). Needs ROS 2 and a built workspace; skipped on Windows. No hardware.

Feeds one synthetic detection, depth image, camera info and TF through the real node, and checks the landmark position.
"""
import math
import time

import numpy as np
import pytest

rclpy = pytest.importorskip('rclpy')
pytest.importorskip('cv_bridge')

from cv_bridge import CvBridge  # noqa: E402
from geometry_msgs.msg import TransformStamped  # noqa: E402
from rclpy.executors import SingleThreadedExecutor  # noqa: E402
from rclpy.qos import qos_profile_sensor_data  # noqa: E402
from sensor_msgs.msg import CameraInfo, Image  # noqa: E402
from tf2_ros import StaticTransformBroadcaster  # noqa: E402

from merz_interfaces.msg import Detection, DetectionArray, LandmarkArray  # noqa: E402
from merz_semantic_map.landmark_node import LandmarkNode  # noqa: E402


def test_landmark_position_through_the_real_node(tmp_path):
    rclpy.init(args=['--ros-args', '-p', f'database:={tmp_path / "merz.sqlite"}', '-p', f'photo_dir:={tmp_path}'])
    node = LandmarkNode()
    helper = rclpy.create_node('landmark_test_helper')
    received: list[LandmarkArray] = []
    helper.create_subscription(LandmarkArray, 'landmarks', received.append, 10)
    detections = helper.create_publisher(DetectionArray, 'detections', 10)
    depth = helper.create_publisher(Image, 'depth', qos_profile_sensor_data)
    info = helper.create_publisher(CameraInfo, 'depth_camera_info', qos_profile_sensor_data)

    # The optical frame sits at map (1, 2, 0), with the camera looking along map +x.
    transform = TransformStamped()
    transform.header.frame_id = 'map'
    transform.child_frame_id = 'test_optical'
    transform.transform.translation.x, transform.transform.translation.y = 1.0, 2.0
    q = transform.transform.rotation
    q.x, q.y, q.z, q.w = -0.5, 0.5, -0.5, 0.5
    broadcaster = StaticTransformBroadcaster(helper)
    broadcaster.sendTransform(transform)

    bridge = CvBridge()
    depth_msg = bridge.cv2_to_imgmsg(np.full((480, 640), 2000, dtype=np.uint16), encoding='16UC1')
    info_msg = CameraInfo(width=640, height=480)
    info_msg.k = [400.0, 0.0, 320.0, 0.0, 400.0, 240.0, 0.0, 0.0, 1.0]
    detection = Detection(label='door', confidence=0.9, x_min=310.0, y_min=230.0, x_max=330.0, y_max=250.0)

    executor = SingleThreadedExecutor()
    executor.add_node(node)
    executor.add_node(helper)
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline and not received:
        stamp = helper.get_clock().now().to_msg()
        for message in (depth_msg, info_msg):
            message.header.stamp, message.header.frame_id = stamp, 'test_optical'
        array = DetectionArray(detections=[detection])
        array.header = depth_msg.header
        depth.publish(depth_msg)
        info.publish(info_msg)
        detections.publish(array)
        executor.spin_once(timeout_sec=0.05)

    node.close()
    node.destroy_node()
    helper.destroy_node()
    rclpy.try_shutdown()

    assert received, 'no landmark was published'
    position = received[-1].landmarks[0].position
    assert math.dist((position.x, position.y, position.z), (3.0, 2.0, 0.0)) < 0.01
