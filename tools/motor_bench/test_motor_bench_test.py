"""Checks the bench script's register writes and that it always leaves the motors stopped. No hardware."""
import pytest

import motor_bench_test as m


class FakeBus:
    def __init__(self):
        self.regs = {}

    def write_byte_data(self, address, register, value):
        assert 0 <= value <= 0xFF
        self.regs[(address, register)] = value

    def read_byte_data(self, address, register):
        return self.regs.get((address, register), 0)


def off_count(bus, address, channel):
    base = m.LED0_ON_L + 4 * channel
    return bus.regs[(address, base + 2)] | bus.regs[(address, base + 3)] << 8


def test_prescale_for_1khz():
    bus = FakeBus()
    m.PCA9685(bus, 0x40).set_frequency(1000)
    assert bus.regs[(0x40, m.PRESCALE)] == 5   # round(25e6 / (4096 * 1000)) - 1


@pytest.mark.parametrize('percent, in1, in2', [(30, 0, m.FULL), (-30, m.FULL, 0), (0, 0, 0)])
def test_direction_pins(percent, in1, in2):
    bus = FakeBus()
    board = m.PCA9685(bus, 0x41)
    m.run_motor(board, 'B', percent)
    assert off_count(bus, 0x41, 5) == int(m.FULL * abs(percent) / 100)
    assert (off_count(bus, 0x41, 3), off_count(bus, 0x41, 4)) == (in1, in2)


def test_speed_is_capped():
    with pytest.raises(SystemExit):
        m.main(['--dry-run', '--speed', '80', '--yes'])


def test_bus_is_required_on_hardware():
    with pytest.raises(SystemExit):
        m.main(['--yes'])


def test_motors_stop_even_after_an_error(monkeypatch):
    bus = FakeBus()
    monkeypatch.setattr(m, 'open_bus', lambda *_: bus)
    monkeypatch.setattr(m.time, 'sleep', lambda s: (_ for _ in ()).throw(RuntimeError('boom')) if s == 2.0 else None)
    with pytest.raises(RuntimeError):
        m.main(['--bus', '7', '--yes'])
    for address in (0x40, 0x41):
        for pwm, in1, in2 in m.MOTORS.values():
            assert off_count(bus, address, pwm) == 0 and off_count(bus, address, in1) == 0
