"""Base driver logic with mock and fake hardware. These say nothing about whether the real rover stops."""
from pathlib import Path

import pytest
import yaml

from merz_base.backends import HBridgePins, JetsonGpioBackend, MockBackend, SerialBackend, make_backend
from merz_base.base_controller import BaseController, BaseLimits
from merz_base.kinematics import normalised, wheel_speeds

PACKAGE = Path(__file__).resolve().parents[1]
LIMITS = BaseLimits(max_linear_m_s=0.5, max_angular_rad_s=1.0, max_linear_accel_m_s2=1.0,
                    max_angular_accel_rad_s2=2.0, track_width_m=0.4, full_speed_m_s=1.0, command_timeout_s=0.5)


def controller() -> tuple[BaseController, MockBackend]:
    backend = MockBackend()
    return BaseController(LIMITS, backend), backend


# ---- kinematics
def test_straight_line_gives_equal_wheels():
    assert wheel_speeds(0.5, 0.0, 0.4) == (0.5, 0.5)


def test_positive_yaw_turns_left_so_the_right_wheel_is_faster():
    left, right = wheel_speeds(0.0, 1.0, 0.4)
    assert left == pytest.approx(-0.2) and right == pytest.approx(0.2)


def test_normalised_clamps_to_full_scale():
    assert normalised(0.5, 1.0) == 0.5
    assert normalised(3.0, 1.0) == 1.0
    assert normalised(-3.0, 1.0) == -1.0


# ---- timeout
def test_motors_stay_stopped_before_any_command():
    base, backend = controller()
    base.update(0.0)
    assert backend.commands == [] and backend.stop_count == 1 and base.timed_out


def test_command_timeout_stops_the_motors():
    base, backend = controller()
    base.on_command(0.5, 0.0, 0.0)
    base.update(0.1)
    assert backend.commands and not base.timed_out
    drives = len(backend.commands)
    base.update(0.5)                                # exactly at the limit: still fresh
    assert len(backend.commands) == drives + 1
    base.update(0.51)                               # just past it
    assert base.timed_out and backend.stop_count == 1
    assert len(backend.commands) == drives + 1


def test_stop_repeats_every_cycle_in_case_a_write_is_lost():
    base, backend = controller()
    for time_s in (1.0, 1.1, 1.2):
        base.update(time_s)
    assert backend.stop_count == 3


def test_timeout_stop_does_not_ramp():
    base, _backend = controller()
    base.on_command(0.5, 0.0, 0.0)
    for time_s in (0.1, 0.2, 0.3, 0.4, 0.5):
        base.update(time_s)
    assert base.current_velocity[0] > 0.3
    base.update(1.0)
    assert base.current_velocity == (0.0, 0.0)


def test_motion_after_a_timeout_restarts_from_rest_and_ignores_the_stale_target():
    base, backend = controller()
    base.on_command(0.5, 0.0, 0.0)
    base.update(0.1)
    base.update(5.0)                                # timed out
    backend.commands.clear()
    base.update(5.1)                                # no new command: must stay stopped
    assert backend.commands == []
    base.on_command(0.5, 0.0, 5.2)
    base.update(5.2)
    assert base.current_velocity[0] == pytest.approx(0.1)    # 0.1 s since the last update, at 1 m/s^2


def test_a_stalled_update_loop_cannot_jump_past_the_ramp():
    base, _backend = controller()
    base.update(0.0)
    base.on_command(0.5, 0.0, 3.0)
    base.update(3.0)    # 3 s since the last update, but the command is fresh
    assert base.current_velocity[0] == pytest.approx(0.2)    # 0.2 s cap, at 1 m/s^2; not the full 0.5 m/s


def test_only_new_commands_refresh_the_timeout():
    base, _backend = controller()
    base.on_command(0.2, 0.0, 0.0)
    for time_s in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6):
        base.update(time_s)
    assert base.timed_out


# ---- limits
def test_commands_are_clamped_to_the_speed_limits():
    base, _backend = controller()
    base.on_command(5.0, -9.0, 0.0)
    base.update(0.0)
    for tenths in range(1, 5):
        base.on_command(5.0, -9.0, tenths / 10)
        base.update(tenths / 10)
    base.on_command(5.0, -9.0, 1.0)
    for tenths in range(11, 15):
        base.on_command(5.0, -9.0, tenths / 10)
        base.update(tenths / 10)
    linear, angular = base.current_velocity
    assert linear == pytest.approx(0.5) and angular == pytest.approx(-1.0)


def test_acceleration_is_limited_up_and_down():
    base, _backend = controller()
    base.update(0.0)
    base.on_command(0.5, 0.0, 0.0)
    base.update(0.1)
    assert base.current_velocity[0] == pytest.approx(0.1)   # 1 m/s^2 for 0.1 s
    base.on_command(0.5, 0.0, 0.1)
    base.update(0.2)
    assert base.current_velocity[0] == pytest.approx(0.2)
    base.on_command(0.0, 0.0, 0.2)
    base.update(0.25)
    assert base.current_velocity[0] == pytest.approx(0.15)


def test_output_is_scaled_by_full_speed():
    backend = MockBackend()
    base = BaseController(BaseLimits(0.5, 1.0, 100.0, 100.0, 0.4, 2.0, 0.5), backend)
    base.update(0.0)
    base.on_command(0.5, 0.0, 0.0)
    base.update(0.1)
    assert backend.commands[-1] == pytest.approx((0.25, 0.25))


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), float('-inf')])
def test_bad_values_are_ignored_and_do_not_refresh_the_timeout(bad):
    base, backend = controller()
    base.on_command(bad, 0.0, 0.0)
    base.on_command(0.0, bad, 0.0)
    base.update(0.1)
    assert backend.commands == [] and base.timed_out


# ---- shutdown
def test_close_stops_once_and_blocks_further_output():
    base, backend = controller()
    base.on_command(0.5, 0.0, 0.0)
    base.update(0.1)
    drives = len(backend.commands)
    base.close()
    base.close()
    assert backend.closed and backend.stop_count == 1
    base.on_command(0.5, 0.0, 0.2)
    base.update(0.2)
    assert len(backend.commands) == drives


# ---- serial, with a fake port
class FakeSerialModule:
    last = None

    class Serial:
        def __init__(self, port, baud, timeout=None, write_timeout=None):
            self.port, self.baud, self.write_timeout = port, baud, write_timeout
            self.written = []
            self.closed = False
            FakeSerialModule.last = self

        def write(self, data):
            self.written.append(data)

        def close(self):
            self.closed = True


def test_serial_uses_the_configured_format():
    backend = SerialBackend('/dev/x', 9600, 'M {left:.2f} {right:.2f}\n', 'S\n', serial_module=FakeSerialModule)
    backend.drive(0.5, -0.25)
    backend.stop()
    assert FakeSerialModule.last.written == [b'M 0.50 -0.25\n', b'S\n']
    assert FakeSerialModule.last.baud == 9600


def test_serial_scale_and_integer_fields():
    backend = SerialBackend('/dev/x', 9600, '{left_int},{right_int};', 'S', scale=255.0, serial_module=FakeSerialModule)
    backend.drive(1.0, -0.5)
    assert FakeSerialModule.last.written == [b'255,-128;']


def test_serial_has_a_write_timeout_so_a_stalled_port_cannot_freeze_the_node():
    SerialBackend('/dev/x', 9600, '', '', serial_module=FakeSerialModule)
    assert FakeSerialModule.last.write_timeout > 0


def test_serial_close_sends_stop_and_closes_even_if_stop_fails():
    backend = SerialBackend('/dev/x', 9600, '', 'S', serial_module=FakeSerialModule)
    port = FakeSerialModule.last
    port.write = lambda _data: (_ for _ in ()).throw(OSError('unplugged'))
    with pytest.raises(OSError):
        backend.close()
    assert port.closed


# ---- GPIO, with a fake Jetson.GPIO
class FakePwm:
    def __init__(self, pin, frequency):
        self.pin, self.frequency = pin, frequency
        self.duties = []
        self.stopped = False

    def start(self, duty):
        self.duties.append(duty)

    def ChangeDutyCycle(self, duty):
        self.duties.append(duty)

    def stop(self):
        self.stopped = True


class FakeGpio:
    BOARD, OUT, HIGH, LOW = 'BOARD', 'OUT', 1, 0

    def __init__(self):
        self.mode = None
        self.outputs = {}
        self.pwms = {}
        self.cleaned = False

    def setmode(self, mode):
        self.mode = mode

    def setup(self, pins, direction, initial=None):
        for pin in pins if isinstance(pins, list) else [pins]:
            self.outputs[pin] = initial

    def output(self, pin, value):
        self.outputs[pin] = value

    def PWM(self, pin, frequency):
        self.pwms[pin] = FakePwm(pin, frequency)
        return self.pwms[pin]

    def cleanup(self):
        self.cleaned = True


LEFT, RIGHT = HBridgePins(10, 11, 12), HBridgePins(20, 21, 22)


def test_gpio_starts_with_motors_off():
    gpio = FakeGpio()
    JetsonGpioBackend(LEFT, RIGHT, 1000.0, gpio_module=gpio)
    assert gpio.mode == 'BOARD'
    assert gpio.pwms[10].duties == [0.0] and gpio.pwms[20].duties == [0.0]
    assert all(value == gpio.LOW for value in gpio.outputs.values())


def test_gpio_direction_and_duty():
    gpio = FakeGpio()
    backend = JetsonGpioBackend(LEFT, RIGHT, 1000.0, gpio_module=gpio)
    backend.drive(0.5, -0.25)
    assert (gpio.outputs[11], gpio.outputs[12]) == (gpio.HIGH, gpio.LOW)
    assert (gpio.outputs[21], gpio.outputs[22]) == (gpio.LOW, gpio.HIGH)
    assert gpio.pwms[10].duties[-1] == 50.0 and gpio.pwms[20].duties[-1] == 25.0


def test_gpio_cuts_pwm_before_changing_direction():
    gpio = FakeGpio()
    backend = JetsonGpioBackend(LEFT, RIGHT, 1000.0, gpio_module=gpio)
    backend.drive(0.5, 0.5)
    backend.drive(-0.5, 0.5)
    assert gpio.pwms[10].duties[-2:] == [0.0, 50.0]


def test_gpio_stop_clears_everything_and_close_releases_pins():
    gpio = FakeGpio()
    backend = JetsonGpioBackend(LEFT, RIGHT, 1000.0, gpio_module=gpio)
    backend.drive(0.5, 0.5)
    backend.close()
    assert gpio.pwms[10].duties[-1] == 0.0 and gpio.pwms[20].duties[-1] == 0.0
    assert all(value == gpio.LOW for value in gpio.outputs.values())
    assert gpio.pwms[10].stopped and gpio.cleaned


def test_gpio_refuses_placeholder_pins():
    with pytest.raises(ValueError, match='placeholders'):
        JetsonGpioBackend(HBridgePins(-1, -1, -1), RIGHT, 1000.0, gpio_module=FakeGpio())


# ---- config
def params() -> dict:
    return yaml.safe_load((PACKAGE / 'config' / 'base.yaml').read_text())['base_node']['ros__parameters']


def test_shipped_config_cannot_move_anything():
    config = params()
    assert config['backend'] == 'mock'
    assert config['gpio_left_pwm'] == -1 and config['gpio_right_pwm'] == -1


def test_shipped_config_respects_the_speed_limit_and_has_a_short_timeout():
    config = params()
    assert config['max_linear_m_s'] <= 0.5
    assert 0 < config['command_timeout_s'] <= 1.0


def test_yaml_gpio_config_is_refused_while_pins_are_placeholders():
    with pytest.raises(ValueError, match='placeholders'):
        make_backend('gpio', params(), module=FakeGpio())


def test_yaml_serial_config_works_with_a_fake_port():
    backend = make_backend('serial', params(), module=FakeSerialModule)
    backend.drive(0.1, 0.2)
    assert FakeSerialModule.last.written == [b'M 0.100 0.200\n']


def test_unknown_backend_is_refused():
    with pytest.raises(ValueError, match='Unknown backend'):
        make_backend('warp', params())
