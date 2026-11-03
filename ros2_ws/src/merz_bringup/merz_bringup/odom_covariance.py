"""Add a covariance to scan-matching odometry. No ROS imports, so it can be unit-tested on Windows.

Why this exists: rf2o publishes nav_msgs/Odometry with its covariance left at zero. The EKF reads a zero
variance as "this measurement is perfect" and would effectively ignore the IMU. So the variances are set
here, from YAML, where they can be tuned from measurements.
"""
from __future__ import annotations

from dataclasses import dataclass

COVARIANCE_SIZE = 36
# Index of each diagonal entry in the 6x6 row-major covariance: x, y, z, roll, pitch, yaw.
X, Y, YAW = 0, 7, 35


@dataclass(frozen=True)
class ScanOdomNoise:
    """Standard deviations of the scan-matching velocities and the plausibility limits."""

    vx_std: float       # m/s
    vy_std: float       # m/s
    vyaw_std: float     # rad/s
    max_speed: float    # m/s; anything faster is treated as a scan-matching failure
    max_yaw_rate: float # rad/s


def twist_covariance(noise: ScanOdomNoise) -> list[float]:
    """Return the 6x6 twist covariance as a flat list, with variances on the planar diagonal.

    The unused axes (z, roll, pitch) get a large variance rather than zero, to state they are unknown.
    """
    unused = 1.0e3
    covariance = [0.0] * COVARIANCE_SIZE
    for index in (14, 21, 28):
        covariance[index] = unused
    covariance[X] = noise.vx_std ** 2
    covariance[Y] = noise.vy_std ** 2
    covariance[YAW] = noise.vyaw_std ** 2
    return covariance


def pose_covariance() -> list[float]:
    """Return a large pose covariance. The EKF is not configured to fuse rf2o's pose, which drifts unbounded."""
    covariance = [0.0] * COVARIANCE_SIZE
    for index in range(0, COVARIANCE_SIZE, 7):
        covariance[index] = 1.0e3
    return covariance


def is_plausible(vx: float, vy: float, vyaw: float, noise: ScanOdomNoise) -> bool:
    """Reject a velocity the rover cannot reach, as scan matching can jump in long featureless corridors."""
    speed = (vx * vx + vy * vy) ** 0.5
    return speed <= noise.max_speed and abs(vyaw) <= noise.max_yaw_rate
