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


def normalised_pair(left_m_s: float, right_m_s: float, full_speed_m_s: float) -> tuple[float, float]:
    """Return both wheel speeds as fractions of full speed, scaled together so neither goes past 1.

    Clamping each wheel on its own would change the ratio between them, and with it the radius of the turn: the rover
    would follow a different arc from the one Nav2 or the operator asked for. Scaling both by the same factor keeps
    the arc and only slows the rover down along it.
    """
    left, right = left_m_s / full_speed_m_s, right_m_s / full_speed_m_s
    largest = max(abs(left), abs(right))
    if largest > 1.0:
        left, right = left / largest, right / largest
    return left, right
