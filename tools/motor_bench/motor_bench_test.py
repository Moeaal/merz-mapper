#!/usr/bin/env python3
"""Spin each rover wheel on its own, slowly, to find which motor is which and which way it turns. Not ROS.

RUN ON THE JETSON, WHEELS OFF THE GROUND, bench supply output button within reach (decisions #29).

Hardware: 2x Waveshare Motor Driver HAT (PCA9685 + TB6612FNG) at I2C 0x40 and 0x41 (decisions #28).
Channel map from the Waveshare manual [H5]: motor A = PWMA 0, AIN1 1, AIN2 2; motor B = PWMB 5, BIN1 3, BIN2 4.
The PCA9685 keeps its last output when a program stops, so this script stops every motor on exit, on Ctrl+C
and on any error.

    python3 motor_bench_test.py --bus 7               # bus number from `i2cdetect -l` / `i2cdetect -y -r 7`
    python3 motor_bench_test.py --bus 7 --speed 25    # duty in percent, capped at 50
    python3 motor_bench_test.py --dry-run             # no hardware: prints what it would do
"""
from __future__ import annotations

import argparse
import os
import signal
import sys
import time

MODE1, PRESCALE, LED0_ON_L = 0x00, 0xFE, 0x06
OSC_HZ = 25_000_000
FULL = 4095
MAX_SPEED_PERCENT = 50
MOTORS = {'A': (0, 1, 2), 'B': (5, 3, 4)}   # name: (pwm, in1, in2)


class PCA9685:
    """Just enough of the PCA9685 to drive a TB6612FNG. `bus` is an smbus/smbus2 SMBus or a fake for tests."""

    def __init__(self, bus, address: int) -> None:
        self.bus, self.address = bus, address
        self.bus.write_byte_data(self.address, MODE1, 0x00)

    def set_frequency(self, hz: float) -> None:
        prescale = int(round(OSC_HZ / (4096.0 * hz))) - 1
        old = self.bus.read_byte_data(self.address, MODE1)
        self.bus.write_byte_data(self.address, MODE1, (old & 0x7F) | 0x10)   # sleep to change the prescaler
        self.bus.write_byte_data(self.address, PRESCALE, prescale)
        self.bus.write_byte_data(self.address, MODE1, old)
        time.sleep(0.005)
        self.bus.write_byte_data(self.address, MODE1, old | 0x80)            # restart

    def set_pwm(self, channel: int, on: int, off: int) -> None:
        base = LED0_ON_L + 4 * channel
        for offset, value in enumerate((on & 0xFF, on >> 8, off & 0xFF, off >> 8)):
            self.bus.write_byte_data(self.address, base + offset, value)

    def set_duty(self, channel: int, percent: float) -> None:
        self.set_pwm(channel, 0, int(FULL * max(0.0, min(100.0, percent)) / 100))

    def set_level(self, channel: int, high: bool) -> None:
        self.set_pwm(channel, 0, FULL if high else 0)


def run_motor(board: PCA9685, motor: str, percent: float) -> None:
    """percent > 0 turns one way (IN1 low, IN2 high, as in the Waveshare demo), < 0 the other, 0 stops."""
    pwm, in1, in2 = MOTORS[motor]
    board.set_duty(pwm, abs(percent))
    board.set_level(in1, percent < 0)
    board.set_level(in2, percent > 0)


def stop_all(boards: list[PCA9685]) -> None:
    for board in boards:
        for motor in MOTORS:
            try:
                run_motor(board, motor, 0)
            except OSError:
                pass   # keep trying the others


class DryBus:
    def write_byte_data(self, address, register, value):
        pass

    def read_byte_data(self, address, register):
        return 0


def kernel_owns(bus_number: int, address: int, sysfs: str = '/sys/bus/i2c/devices') -> bool:
    """True if a kernel driver already uses this address (i2cdetect shows UU). Never write to such a device:
    on the Jetson, bus 1 address 0x40 is an on-board chip, not a HAT (found 2026-11-16)."""
    return os.path.exists(os.path.join(sysfs, f'{bus_number}-{address:04x}', 'driver'))


def other_motor_programs(proc: str = '/proc') -> list[str]:
    """Running merz_base base_node processes. Two programs driving the same HATs fight: on 2026-11-16 a forgotten
    base_node sent "stop" 20 times a second and the bench test could not move any wheel."""
    found = []
    for entry in os.listdir(proc):
        if not entry.isdigit() or int(entry) == os.getpid():
            continue
        try:
            with open(os.path.join(proc, entry, 'cmdline'), 'rb') as handle:
                cmdline = handle.read().replace(b'\0', b' ').decode(errors='replace')
        except OSError:
            continue
        if 'merz_base/base_node' in cmdline:
            found.append(f'{entry}: {cmdline.strip()[:100]}')
    return found


def open_bus(bus_number: int, dry_run: bool):
    if dry_run:
        return DryBus()
    try:
        from smbus2 import SMBus
    except ImportError:
        from smbus import SMBus   # apt: python3-smbus
    return SMBus(bus_number)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--bus', type=int, default=None, help='I2C bus number (from i2cdetect)')
    parser.add_argument('--addresses', default='0x40,0x41', help='comma-separated HAT addresses')
    parser.add_argument('--speed', type=float, default=30.0, help=f'duty in percent (max {MAX_SPEED_PERCENT})')
    parser.add_argument('--seconds', type=float, default=2.0, help='run time per direction')
    parser.add_argument('--freq', type=float, default=1000.0, help='PWM frequency in Hz (PCA9685: about 24-1526)')
    parser.add_argument('--dry-run', action='store_true', help='no hardware')
    parser.add_argument('--yes', action='store_true', help='do not wait for Enter between wheels (dry run / tests)')
    args = parser.parse_args(argv)
    if args.bus is None and not args.dry_run:
        parser.error('--bus is required (run `i2cdetect -l`)')
    if not 0 < args.speed <= MAX_SPEED_PERCENT:
        parser.error(f'--speed must be in (0, {MAX_SPEED_PERCENT}]')

    addresses = [int(a, 0) for a in args.addresses.split(',')]
    if not args.dry_run:
        others = other_motor_programs()
        if others:
            parser.error('base_node is already driving the motors. Stop it first (Ctrl+C in its window, or '
                         'kill -INT <pid>):\n  ' + '\n  '.join(others))
        owned = [a for a in addresses if kernel_owns(args.bus, a)]
        if owned:
            parser.error(f'bus {args.bus} address(es) {", ".join(hex(a) for a in owned)} belong to a kernel driver '
                         '(UU in i2cdetect), so they are not the HATs. Use the bus where i2cdetect shows 40 and 41.')
    bus = open_bus(args.bus or 0, args.dry_run)
    boards = [PCA9685(bus, a) for a in addresses]
    signal.signal(signal.SIGINT, lambda *_: (stop_all(boards), sys.exit(130)))
    results = []
    try:
        for board in boards:
            board.set_frequency(args.freq)
        stop_all(boards)
        print('WHEELS OFF THE GROUND? Supply button in reach? Ctrl+C stops everything.')
        for board in boards:
            for motor in MOTORS:
                label = f'board 0x{board.address:02x} motor {motor}'
                if not args.yes:
                    input(f'\n{label}: press Enter to spin it (+{args.speed:.0f}% then -{args.speed:.0f}%)...')
                for sign in (+1, -1):
                    print(f'  {label}: {sign * args.speed:+.0f}% for {args.seconds:.1f} s')
                    run_motor(board, motor, sign * args.speed)
                    time.sleep(args.seconds)
                    run_motor(board, motor, 0)
                    time.sleep(0.5)
                if not args.yes:
                    note = input('  Which wheel was it (FL/FR/RL/RR) and which way did "+" turn it (fwd/back)? ')
                    results.append(f'{label}: {note}')
    finally:
        stop_all(boards)
        print('\nAll motors stopped.')
    if results:
        print('\nCopy this into the logbook:')
        print('\n'.join(results))
    return 0


if __name__ == '__main__':
    sys.exit(main())
