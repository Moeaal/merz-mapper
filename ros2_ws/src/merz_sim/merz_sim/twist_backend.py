"""A merz_base motor backend that turns wheel outputs back into a body velocity for the simulator. No ROS imports.

Why: in simulation, /cmd_vel_mux goes through merz_base's own BaseController (clamp to 0.5 m/s, acceleration ramp,
arc-preserving wheel saturation, command timeout) before it reaches Gazebo. The simulated rover is then limited exactly
as the real one will be, and the base logic gets exercised by every simulated run.

BaseController hands this backend wheel speeds as fractions of full speed; Gazebo's DiffDrive wants a body twist,
so the inverse of merz_base.kinematics.wheel_speeds is applied:
    v = (v_left + v_right) / 2,   w = (v_right - v_left) / B
"""
from __future__ import annotations

from typing import Callable

Publish = Callable[[float, float], None]   # (linear m/s, angular rad/s)


def body_velocity(left: float, right: float, full_speed_m_s: float, track_width_m: float) -> tuple[float, float]:
    """Return (linear m/s, angular rad/s) for wheel outputs given as fractions of full speed."""
    v_left, v_right = left * full_speed_m_s, right * full_speed_m_s
    return (v_left + v_right) / 2.0, (v_right - v_left) / track_width_m


class TwistBackend:
    """MotorBackend (see merz_base.backends) whose output is a Twist to Gazebo instead of motor commands."""

    def __init__(self, publish: Publish, full_speed_m_s: float, track_width_m: float) -> None:
        self._publish = publish
        self._full_speed = full_speed_m_s
        self._track = track_width_m

    def drive(self, left: float, right: float) -> None:
        self._publish(*body_velocity(left, right, self._full_speed, self._track))

    def stop(self) -> None:
        self._publish(0.0, 0.0)

    def close(self) -> None:
        self.stop()
