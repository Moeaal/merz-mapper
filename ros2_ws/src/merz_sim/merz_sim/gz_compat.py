"""Everything that depends on the Gazebo version, in one place. No ROS imports, so it is unit-tested without ROS.

PROPOSED (OPEN_ISSUES #2 leaves the ROS 2 distro open). The default is Gazebo Fortress, the Gazebo release that
ROS 2 Humble's own binary packages (`ros-humble-ros-gz`) are built against. Harmonic works with Humble only through
the separate `ros-humble-ros-gzharmonic` packages, and is the default pairing for Jazzy. If the project moves to
Jazzy, pass gz_version:=harmonic and check this table first.

What differs between versions:
  * system plugin library and class names (ignition-gazebo-* / ignition::gazebo vs gz-sim-* / gz::sim)
  * the SDF tag that sets a sensor's frame id (ignition_frame_id vs gz_frame_id); see the xacro
  * the message type prefix the bridge expects (ignition.msgs vs gz.msgs)
  * the command line (ign gazebo vs gz sim)
"""
from __future__ import annotations

from dataclasses import dataclass

WORLD_NAME = 'merz_floor'
MODEL_NAME = 'merz_rover'


@dataclass(frozen=True)
class GzVersion:
    name: str
    plugin_prefix: str    # library file name prefix
    plugin_namespace: str # C++ namespace of the systems
    msg_prefix: str       # bridge type prefix
    command: tuple[str, ...]


VERSIONS = {
    'fortress': GzVersion('fortress', 'ignition-gazebo', 'ignition::gazebo', 'ignition.msgs', ('ign', 'gazebo')),
    'harmonic': GzVersion('harmonic', 'gz-sim', 'gz::sim', 'gz.msgs', ('gz', 'sim')),
}


def version(name: str) -> GzVersion:
    try:
        return VERSIONS[name]
    except KeyError:
        raise ValueError(f'gz_version must be one of {sorted(VERSIONS)}, not {name!r}') from None


def system_plugin(gz: GzVersion, library: str, cls: str) -> tuple[str, str]:
    """Return (filename, name) of a Gazebo system, e.g. ('ignition-gazebo-physics-system', 'ignition::gazebo::systems::Physics')."""
    return f'{gz.plugin_prefix}-{library}-system', f'{gz.plugin_namespace}::systems::{cls}'


# World-level systems: physics, the GUI/user commands, scene publishing, rendering sensors (LIDAR and cameras) and IMUs.
WORLD_SYSTEMS = (('physics', 'Physics'), ('user-commands', 'UserCommands'), ('scene-broadcaster', 'SceneBroadcaster'),
                 ('sensors', 'Sensors'), ('imu', 'Imu'))


def server_command(gz: GzVersion, world_file: str, headless: bool = True) -> list[str]:
    """Gazebo server, running (-r) and without a GUI (-s). Headless rendering uses EGL, so no X display is needed."""
    command = [*gz.command, '-r', '-s', '-v', '2']
    if headless:
        command.append('--headless-rendering')
    return [*command, world_file]


def gui_command(gz: GzVersion) -> list[str]:
    return [*gz.command, '-g']


@dataclass(frozen=True)
class Bridge:
    """One topic through ros_gz_bridge. gz_to_ros False means ROS to Gazebo. ros_name is the name after remapping."""
    gz_topic: str
    ros_type: str
    gz_type: str
    gz_to_ros: bool = True
    ros_name: str = ''

    def argument(self, gz: GzVersion) -> str:
        direction = '[' if self.gz_to_ros else ']'
        return f'{self.gz_topic}@{self.ros_type}{direction}{gz.msg_prefix}.{self.gz_type}'

    def remapping(self) -> tuple[str, str] | None:
        return (self.gz_topic, self.ros_name) if self.ros_name and self.ros_name != self.gz_topic else None


# Ground truth that must never reach the estimator in mode (b). Listed so that a test can check it.
GROUND_TRUTH_GZ_TOPICS = ('/sim/wheel_odom', '/sim/wheel_tf')
WHEEL_ODOM_RAW = '/sim/wheel_odometry_raw'   # ROS name of the bridged wheel odometry, before covariance is added


def bridges(odom_mode: str, cameras: bool) -> list[Bridge]:
    """The topics bridged for one run. The ROS names match the real drivers, so merz_bringup's config works unchanged.

    odom_mode 'wheel': the DiffDrive plugin's odometry is bridged (mode a, simulated encoders).
    odom_mode 'scan':  it is NOT bridged. Nothing from the simulator that knows the true motion reaches ROS; the
                       estimator only gets /scan and the IMU, as on a rover without encoders (mode b).
    The DiffDrive TF (/sim/wheel_tf) is never bridged: the EKF alone owns odom->base_link.
    """
    if odom_mode not in ('wheel', 'scan'):
        raise ValueError(f"odom_mode must be 'wheel' or 'scan', not {odom_mode!r}")
    joint_states = f'/world/{WORLD_NAME}/model/{MODEL_NAME}/joint_state'
    items = [
        Bridge('/clock', 'rosgraph_msgs/msg/Clock', 'Clock'),
        Bridge('/scan', 'sensor_msgs/msg/LaserScan', 'LaserScan'),
        Bridge('/camera/camera/imu', 'sensor_msgs/msg/Imu', 'IMU'),
        Bridge(joint_states, 'sensor_msgs/msg/JointState', 'Model', ros_name='/joint_states'),
        Bridge('/sim/cmd_vel', 'geometry_msgs/msg/Twist', 'Twist', gz_to_ros=False),
    ]
    if odom_mode == 'wheel':
        items.append(Bridge('/sim/wheel_odom', 'nav_msgs/msg/Odometry', 'Odometry', ros_name=WHEEL_ODOM_RAW))
    if cameras:
        items += [
            Bridge('/camera/sim_rgbd/image', 'sensor_msgs/msg/Image', 'Image',
                   ros_name='/camera/camera/color/image_raw'),
            Bridge('/camera/sim_rgbd/depth_image', 'sensor_msgs/msg/Image', 'Image',
                   ros_name='/camera/camera/aligned_depth_to_color/image_raw'),
            Bridge('/camera/sim_rgbd/camera_info', 'sensor_msgs/msg/CameraInfo', 'CameraInfo',
                   ros_name='/camera/camera/aligned_depth_to_color/camera_info'),
            Bridge('/sign_cam/image_raw', 'sensor_msgs/msg/Image', 'Image'),
            Bridge('/sign_cam/camera_info', 'sensor_msgs/msg/CameraInfo', 'CameraInfo'),
        ]
    return items


def bridge_arguments(gz: GzVersion, items: list[Bridge]) -> list[str]:
    return [item.argument(gz) for item in items]


def bridge_remappings(items: list[Bridge]) -> list[tuple[str, str]]:
    return [r for r in (item.remapping() for item in items) if r]
