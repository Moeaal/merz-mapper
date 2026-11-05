"""What the headless check expects for each odometry mode, and how its results are judged. No ROS imports."""
from __future__ import annotations

from dataclasses import dataclass, field

# Topics that must carry at least one message, for every run.
COMMON_TOPICS = ('/clock', '/scan', '/camera/camera/imu', '/odometry/filtered', '/map')
CAMERA_TOPICS = ('/camera/camera/color/image_raw', '/camera/camera/aligned_depth_to_color/image_raw',
                 '/camera/camera/depth/color/points', '/sign_cam/image_raw')
MODE_TOPICS = {'wheel': ('/wheel/odometry',), 'scan': ('/odom_rf2o', '/odom_scan')}
# In mode (b) these must have NO publisher at all: they carry the simulator's knowledge of the true wheel motion.
FORBIDDEN_IN_SCAN_MODE = ('/sim/wheel_odometry_raw', '/wheel/odometry')
TRANSFORMS = (('map', 'odom'), ('odom', 'base_link'), ('base_link', 'laser'), ('base_link', 'camera_imu_optical_frame'))


def expected_topics(odom_mode: str, cameras: bool) -> tuple[str, ...]:
    if odom_mode not in MODE_TOPICS:
        raise ValueError(f"odom_mode must be 'wheel' or 'scan', not {odom_mode!r}")
    return COMMON_TOPICS + MODE_TOPICS[odom_mode] + (CAMERA_TOPICS if cameras else ())


@dataclass
class CheckReport:
    received: dict[str, int] = field(default_factory=dict)        # topic -> messages counted
    transforms: dict[str, bool] = field(default_factory=dict)     # "parent->child" -> found
    forbidden_publishers: dict[str, int] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return (all(n > 0 for n in self.received.values()) and all(self.transforms.values())
                and not any(self.forbidden_publishers.values()))

    def lines(self) -> list[str]:
        out = [f'{"OK  " if n else "FAIL"} topic {t} ({n} messages)' for t, n in sorted(self.received.items())]
        out += [f'{"OK  " if ok else "FAIL"} tf    {name}' for name, ok in sorted(self.transforms.items())]
        out += [f'{"FAIL" if n else "OK  "} none  {t} ({n} publishers; must be 0 in scan mode)'
                for t, n in sorted(self.forbidden_publishers.items())]
        out.append('RESULT: PASS' if self.passed else 'RESULT: FAIL')
        return out
