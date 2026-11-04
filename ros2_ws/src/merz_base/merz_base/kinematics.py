"""Convert a body velocity into left and right wheel speeds, for a differential or skid-steer base. No ROS imports.

    v_left  = v - w * B / 2
    v_right = v + w * B / 2

On a skid-steer rover, wheels slip while turning, so B here is an effective track width, larger than the measured one.
It must be found by commanding fixed turns and measuring them with the IMU (TODO: measure on rover).
"""
from __future__ import annotations


def wheel_speeds(linear_m_s: float, angular_rad_s: float, track_width_m: float) -> tuple[float, float]:
    """Return (left, right) in m/s."""
    offset = angular_rad_s * track_width_m / 2.0
    return linear_m_s - offset, linear_m_s + offset


def normalised(speed_m_s: float, full_speed_m_s: float) -> float:
    """Return speed as a fraction of the motor's full speed, -1 to 1."""
    return max(-1.0, min(1.0, speed_m_s / full_speed_m_s))
