"""The simulated base uses merz_base's BaseController, so its limits and timeout are the rover's."""
import pytest

from merz_base.base_controller import BaseController, BaseLimits
from merz_base.kinematics import normalised_pair, wheel_speeds
from merz_sim.twist_backend import body_velocity, TwistBackend

LIMITS = BaseLimits(max_linear_m_s=0.5, max_angular_rad_s=1.0, max_linear_accel_m_s2=0.5,
                    max_angular_accel_rad_s2=1.0, track_width_m=0.44, full_speed_m_s=1.0, command_timeout_s=0.5)


@pytest.mark.parametrize('v, w', [(0.3, 0.0), (0.0, 1.0), (0.4, -0.7), (-0.2, 0.3)])
def test_body_velocity_inverts_wheel_speeds(v, w):
    left, right = normalised_pair(*wheel_speeds(v, w, 0.44), 1.0)
    assert body_velocity(left, right, 1.0, 0.44) == pytest.approx((v, w))


def run(commands, until_s, step_s=0.05):
    sent = []
    controller = BaseController(LIMITS, TwistBackend(lambda v, w: sent.append((v, w)), 1.0, 0.44))
    t = 0.0
    while t <= until_s + 1e-9:
        for at, v, w in commands:
            if abs(at - t) < step_s / 2:
                controller.on_command(v, w, t)
        controller.update(t)
        t += step_s
    return sent


def test_a_fast_command_is_clamped_to_0_5_m_s():
    commands = [(t * 0.1, 2.0, 0.0) for t in range(40)]   # 2 m/s asked, every 0.1 s for 4 s
    sent = run(commands, 4.0)
    assert max(v for v, _ in sent) == pytest.approx(0.5)


def test_it_stops_when_commands_stop():
    sent = run([(0.0, 0.3, 0.0), (0.1, 0.3, 0.0)], 2.0)
    assert sent[-1] == (0.0, 0.0)


def test_stop_and_close_send_zero():
    sent = []
    backend = TwistBackend(lambda v, w: sent.append((v, w)), 1.0, 0.44)
    backend.stop()
    backend.close()
    assert sent == [(0.0, 0.0), (0.0, 0.0)]
