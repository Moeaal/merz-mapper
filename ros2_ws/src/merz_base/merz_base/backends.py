"""Motor output backends behind one interface, chosen in config/base.yaml. No ROS imports.

  pca9685 the rover's 2x Waveshare Motor Driver HAT (PCA9685 + TB6612FNG) over I2C (decisions #28, #34, #35)
  serial  a motor controller with a text command format set in YAML
  gpio    PWM to an H-bridge from the Jetson header, using Jetson.GPIO
  mock    records commands, for unit tests and for running the stack with the wheels disconnected

Hardware libraries are imported only when a backend is created, so that the mock runs anywhere.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol


class MotorBackend(Protocol):
    def drive(self, left: float, right: float) -> None:
        """Set the motors. Values are fractions of full speed, -1 to 1, positive forward."""
        ...

    def stop(self) -> None:
        """Stop the motors. Must be safe to call repeatedly."""
        ...

    def close(self) -> None:
        """Stop the motors and release the hardware."""
        ...


@dataclass
class MockBackend:
    """Records what it is told. Moves nothing."""

    commands: list[tuple[float, float]] = field(default_factory=list)
    stop_count: int = 0
    closed: bool = False

    def drive(self, left: float, right: float) -> None:
        self.commands.append((left, right))

    def stop(self) -> None:
        self.stop_count += 1

    def close(self) -> None:
        self.stop()
        self.closed = True


class SerialBackend:
    """Send a formatted text command over a serial port.

    drive_format and stop_command come from YAML, as they depend on the controller. For example, a controller expecting
    integers from -255 to 255 would use "M {left_int} {right_int}\\n" with scale 255. Available fields: left and right
    (scaled floats), left_int and right_int (rounded).
    """

    def __init__(self, port: str, baud: int, drive_format: str, stop_command: str, scale: float = 1.0,
                 serial_module: Any = None, write_timeout_s: float = 0.1) -> None:
        if serial_module is None:
            import serial as serial_module
        self._format = drive_format
        self._stop_command = stop_command
        self._scale = scale
        # A write timeout, as a stalled port must not freeze the node and with it the timeout check.
        self._port = serial_module.Serial(port, baud, timeout=0, write_timeout=write_timeout_s)

    def _send(self, text: str) -> None:
        self._port.write(text.encode('ascii'))

    def drive(self, left: float, right: float) -> None:
        scaled_left, scaled_right = left * self._scale, right * self._scale
        self._send(self._format.format(left=scaled_left, right=scaled_right, left_int=round(scaled_left),
                                       right_int=round(scaled_right)))

    def stop(self) -> None:
        self._send(self._stop_command)

    def close(self) -> None:
        try:
            self.stop()
        finally:
            self._port.close()


@dataclass(frozen=True)
class HBridgePins:
    """Physical (BOARD) pin numbers for one side of the H-bridge. Direction pins set the rotation, PWM sets the speed."""

    pwm: int
    forward: int
    reverse: int


class JetsonGpioBackend:
    """PWM to an H-bridge. Pins must be enabled with jetson-io and checked against NVIDIA's Orin Nano pinout first."""

    def __init__(self, left: HBridgePins, right: HBridgePins, frequency_hz: float, gpio_module: Any = None) -> None:
        for pins in (left, right):
            if min(pins.pwm, pins.forward, pins.reverse) < 0:
                raise ValueError('GPIO pins are still placeholders (-1). Set them in config/base.yaml after checking '
                                 "NVIDIA's Orin Nano pinout and enabling PWM with jetson-io.")
        if gpio_module is None:
            import Jetson.GPIO as gpio_module
        self._gpio = gpio_module
        self._sides = (left, right)
        self._gpio.setmode(self._gpio.BOARD)
        self._pwm = []
        for pins in self._sides:
            self._gpio.setup([pins.forward, pins.reverse], self._gpio.OUT, initial=self._gpio.LOW)
            self._gpio.setup(pins.pwm, self._gpio.OUT, initial=self._gpio.LOW)
            pwm = self._gpio.PWM(pins.pwm, frequency_hz)
            pwm.start(0.0)
            self._pwm.append(pwm)

    def _set_side(self, index: int, value: float) -> None:
        pins = self._sides[index]
        # The PWM goes to 0 before direction changes, so the bridge never switches direction under load.
        self._pwm[index].ChangeDutyCycle(0.0)
        self._gpio.output(pins.forward, self._gpio.HIGH if value > 0 else self._gpio.LOW)
        self._gpio.output(pins.reverse, self._gpio.HIGH if value < 0 else self._gpio.LOW)
        self._pwm[index].ChangeDutyCycle(min(abs(value), 1.0) * 100.0)

    def drive(self, left: float, right: float) -> None:
        self._set_side(0, left)
        self._set_side(1, right)

    def stop(self) -> None:
        self._set_side(0, 0.0)
        self._set_side(1, 0.0)

    def close(self) -> None:
        try:
            self.stop()
        finally:
            for pwm in self._pwm:
                pwm.stop()
            self._gpio.cleanup()


# ---- PCA9685 (Waveshare Motor Driver HAT). Channel map from the Waveshare manual [H5]: (pwm, in1, in2).
PCA9685_MOTOR_CHANNELS = {'A': (0, 1, 2), 'B': (5, 3, 4)}
_MODE1, _PRESCALE, _LED0_ON_L, _FULL, _OSC_HZ = 0x00, 0xFE, 0x06, 4095, 25_000_000


@dataclass(frozen=True)
class HatMotor:
    """One wheel motor: HAT I2C address, motor A or B, and whether "+" must be flipped to mean forward."""

    address: int
    motor: str
    inverted: bool = False


def parse_hat_motors(spec: str, inverted: str = '') -> list[HatMotor]:
    """'0x40:A,0x41:A' -> motors. inverted lists the same 'address:motor' names to flip, comma-separated."""
    flipped = {item.strip().upper() for item in inverted.split(',') if item.strip()}
    motors = []
    for item in (part.strip() for part in spec.split(',') if part.strip()):
        address, _, motor = item.partition(':')
        motor = motor.strip().upper()
        if motor not in PCA9685_MOTOR_CHANNELS:
            raise ValueError(f"'{item}': motor must be A or B, as in '0x40:A'")
        motors.append(HatMotor(int(address, 0), motor, item.upper() in flipped))
    if not motors:
        raise ValueError('No motors listed for a side')
    return motors


def i2c_address_owned_by_kernel(bus: int, address: int, sysfs: str = '/sys/bus/i2c/devices') -> bool:
    """i2cdetect's UU: a kernel driver uses this address. On the Jetson, bus 1 0x40 is an on-board chip."""
    return os.path.exists(os.path.join(sysfs, f'{bus}-{address:04x}', 'driver'))


class Pca9685Backend:
    """Skid-steer over the Waveshare HATs. Each side drives every motor listed for it with the same value.

    max_duty caps the PWM duty (0-1) whatever is commanded, as a first safety limit while the speed scaling is
    unmeasured. The PCA9685 keeps its last output if this process dies (Waveshare manual), so the motor supply
    switch is the real stop (decisions #29); this class stops every motor on stop() and close().
    """

    def __init__(self, bus: int, left: list[HatMotor], right: list[HatMotor], frequency_hz: float = 1000.0,
                 max_duty: float = 0.5, smbus_module: Any = None,
                 sysfs: str = '/sys/bus/i2c/devices') -> None:
        if not 0.0 < max_duty <= 1.0:
            raise ValueError('pca9685_max_duty must be in (0, 1]')
        if not 24.0 <= frequency_hz <= 1526.0:
            raise ValueError('pca9685_frequency_hz must be between 24 and 1526 Hz (PCA9685 range)')
        self._sides = (left, right)
        self._max_duty = max_duty
        addresses = sorted({m.address for side in self._sides for m in side})
        owned = [a for a in addresses if i2c_address_owned_by_kernel(bus, a, sysfs)]
        if owned:
            raise ValueError(f'I2C bus {bus}: {", ".join(hex(a) for a in owned)} belong to a kernel driver (UU), '
                             'not the HATs. Set pca9685_bus to the bus where i2cdetect shows the HATs.')
        if smbus_module is None:
            try:
                import smbus2 as smbus_module
            except ImportError:
                import smbus as smbus_module   # apt: python3-smbus
        self._bus = smbus_module.SMBus(bus)
        self._last = {}
        prescale = int(round(_OSC_HZ / (4096.0 * frequency_hz))) - 1
        for address in addresses:
            self._write(address, _MODE1, 0x00)
            old = self._bus.read_byte_data(address, _MODE1)
            self._write(address, _MODE1, (old & 0x7F) | 0x10)   # sleep to change the prescaler
            self._write(address, _PRESCALE, prescale)
            self._write(address, _MODE1, old)
            self._write(address, _MODE1, old | 0x80)            # restart (the 500 us oscillator wait is
            # covered by the I2C writes that follow)
        self.stop()

    def _write(self, address: int, register: int, value: int) -> None:
        self._bus.write_byte_data(address, register, value)

    def _set_channel(self, address: int, channel: int, off: int) -> None:
        base = _LED0_ON_L + 4 * channel
        for offset, value in enumerate((0, 0, off & 0xFF, off >> 8)):
            self._write(address, base + offset, value)

    def _set_motor(self, motor: HatMotor, value: float) -> None:
        value = max(-1.0, min(1.0, -value if motor.inverted else value))
        pwm, in1, in2 = PCA9685_MOTOR_CHANNELS[motor.motor]
        key = (motor.address, motor.motor)
        direction = (value > 0) - (value < 0)
        if self._last.get(key, 0) != direction:
            # PWM to zero before the direction pins change, so the bridge never reverses under load.
            self._set_channel(motor.address, pwm, 0)
            self._set_channel(motor.address, in1, _FULL if direction < 0 else 0)   # Waveshare: forward = IN1 low,
            self._set_channel(motor.address, in2, _FULL if direction > 0 else 0)   # IN2 high
            self._last[key] = direction
        self._set_channel(motor.address, pwm, int(_FULL * abs(value) * self._max_duty))

    def drive(self, left: float, right: float) -> None:
        for side, value in zip(self._sides, (left, right)):
            for motor in side:
                self._set_motor(motor, value)

    def stop(self) -> None:
        errors = []
        for side in self._sides:
            for motor in side:
                try:
                    self._set_motor(motor, 0.0)
                except OSError as error:   # keep stopping the others, then report
                    errors.append(error)
        if errors:
            raise errors[0]

    def close(self) -> None:
        try:
            self.stop()
        finally:
            self._bus.close()


def make_backend(name: str, config: dict, module: Optional[Any] = None) -> MotorBackend:
    """Create a backend from a flat config. module replaces the hardware library in tests."""
    if name == 'mock':
        return MockBackend()
    if name == 'pca9685':
        return Pca9685Backend(
            int(config['pca9685_bus']),
            parse_hat_motors(config['pca9685_left_motors'], config['pca9685_inverted']),
            parse_hat_motors(config['pca9685_right_motors'], config['pca9685_inverted']),
            float(config['pca9685_frequency_hz']), float(config['pca9685_max_duty']), smbus_module=module)
    if name == 'serial':
        return SerialBackend(config['serial_port'], int(config['serial_baud']), config['serial_drive_format'],
                             config['serial_stop_command'], float(config['serial_scale']), serial_module=module)
    if name == 'gpio':
        left = HBridgePins(int(config['gpio_left_pwm']), int(config['gpio_left_forward']),
                           int(config['gpio_left_reverse']))
        right = HBridgePins(int(config['gpio_right_pwm']), int(config['gpio_right_forward']),
                            int(config['gpio_right_reverse']))
        return JetsonGpioBackend(left, right, float(config['gpio_pwm_frequency_hz']), gpio_module=module)
    raise ValueError(f"Unknown backend '{name}'. Choose mock, pca9685, serial or gpio")
