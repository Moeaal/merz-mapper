"""Limits and the command timeout. All time is passed in, so behaviour can be tested exactly. No ROS imports."""
from __future__ import annotations

import math
from dataclasses import dataclass, fields
from typing import Optional

from merz_base.backends import MotorBackend
from merz_base.kinematics import normalised_pair, wheel_speeds

MAX_RAMP_STEP_S = 0.2   # the longest time one update may count towards the acceleration ramp


@dataclass(frozen=True)
class BaseLimits:
    max_linear_m_s: float            # spec limit: 0.5 m/s
    max_angular_rad_s: float
    max_linear_accel_m_s2: float
    max_angular_accel_rad_s2: float
    track_width_m: float             # effective width on a skid-steer rover
    full_speed_m_s: float            # wheel speed at full motor output
    command_timeout_s: float

    def __post_init__(self) -> None:
        # Every limit must be a finite number above zero. A negative speed limit would invert the clamp and drive the
        # rover at that speed whatever was commanded; zero full speed would crash the update loop; zero or negative
        # timeout would never let a command through, and an infinite one would never stop the motors.
        for item in fields(self):
            value = getattr(self, item.name)
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0.0:
                raise ValueError(f'{item.name} must be a finite number above zero, not {value!r}')


def check_update_rate(rate_hz: float) -> float:
    """Return the timer period in seconds, or raise if the rate is not a finite number above zero."""
    if not isinstance(rate_hz, (int, float)) or not math.isfinite(rate_hz) or rate_hz <= 0.0:
        raise ValueError(f'update_rate_hz must be a finite number above zero, not {rate_hz!r}')
    return 1.0 / rate_hz


def _clamp(value: float, limit: float) -> float:
    return max(-limit, min(limit, value))


def _approach(current: float, target: float, max_step: float) -> float:
    """Move current towards target by no more than max_step."""
    return current + _clamp(target - current, max_step)


class BaseController:
    """Turns velocity commands into motor outputs at a fixed rate.

    Safety behaviour, in order of importance:
      * If no command arrives within command_timeout_s, the motors stop at once, without an acceleration ramp. This covers
        a crashed Nav2 or teleop, or a dropped connection. Stopping does not ramp as the rover must not coast on.
      * Commands are clamped to the speed limits.
      * The ramp limits the rate of change of speed, up and down, to protect the drivetrain and reduce wheel slip.
      * NaN and infinity are ignored as if the command never arrived.
    """

    def __init__(self, limits: BaseLimits, backend: MotorBackend) -> None:
        self._limits = limits
        self._backend = backend
        self._target_linear = 0.0
        self._target_angular = 0.0
        self._linear = 0.0
        self._angular = 0.0
        self._last_command_s: Optional[float] = None
        self._last_update_s: Optional[float] = None
        self._stopped = True
        self._closed = False

    @property
    def timed_out(self) -> bool:
        return self._stopped

    @property
    def current_velocity(self) -> tuple[float, float]:
        return self._linear, self._angular

    def on_command(self, linear_m_s: float, angular_rad_s: float, now_s: float) -> None:
        if not all(abs(v) < float('inf') for v in (linear_m_s, angular_rad_s)):   # False for NaN and for infinity
            return
        self._target_linear = _clamp(linear_m_s, self._limits.max_linear_m_s)
        self._target_angular = _clamp(angular_rad_s, self._limits.max_angular_rad_s)
        self._last_command_s = now_s

    def update(self, now_s: float) -> None:
        """Call this at a fixed rate. It sends one output to the backend."""
        if self._closed:
            return
        previous = self._last_update_s if self._last_update_s is not None else now_s
        self._last_update_s = now_s
        fresh = (self._last_command_s is not None
                 and now_s - self._last_command_s <= self._limits.command_timeout_s)
        if not fresh:
            self._linear = self._angular = 0.0
            self._target_linear = self._target_angular = 0.0
            self._stopped = True
            self._backend.stop()   # sent every cycle, in case one write to the controller is lost
            return
        self._stopped = False
        # Capped, so a stall in this loop (the Jetson pausing, say) cannot make the speed jump past the ramp.
        elapsed = min(max(0.0, now_s - previous), MAX_RAMP_STEP_S)
        self._linear = _approach(self._linear, self._target_linear, self._limits.max_linear_accel_m_s2 * elapsed)
        self._angular = _approach(self._angular, self._target_angular, self._limits.max_angular_accel_rad_s2 * elapsed)
        left, right = wheel_speeds(self._linear, self._angular, self._limits.track_width_m)
        self._backend.drive(*normalised_pair(left, right, self._limits.full_speed_m_s))

    def close(self) -> None:
        """Stop and release the hardware. Safe to call twice."""
        if not self._closed:
            self._closed = True
            self._backend.close()
