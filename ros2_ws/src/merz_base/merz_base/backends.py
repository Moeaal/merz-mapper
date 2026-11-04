"""Motor output backends behind one interface, chosen in config/base.yaml. No ROS imports.

The rover's motor interface is not yet known (OPEN_ISSUES #1), so this covers both likely cases:
  serial  a motor controller with a text command format set in YAML
  gpio    PWM to an H-bridge from the Jetson header, using Jetson.GPIO
  mock    records commands, for unit tests and for running the stack with the wheels disconnected

Hardware libraries are imported only when a backend is created, so that the mock runs anywhere.
"""
from __future__ import annotations

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


def make_backend(name: str, config: dict, module: Optional[Any] = None) -> MotorBackend:
    """Create a backend from a flat config. module replaces the hardware library in tests."""
    if name == 'mock':
        return MockBackend()
    if name == 'serial':
        return SerialBackend(config['serial_port'], int(config['serial_baud']), config['serial_drive_format'],
                             config['serial_stop_command'], float(config['serial_scale']), serial_module=module)
    if name == 'gpio':
        left = HBridgePins(int(config['gpio_left_pwm']), int(config['gpio_left_forward']),
                           int(config['gpio_left_reverse']))
        right = HBridgePins(int(config['gpio_right_pwm']), int(config['gpio_right_forward']),
                            int(config['gpio_right_reverse']))
        return JetsonGpioBackend(left, right, float(config['gpio_pwm_frequency_hz']), gpio_module=module)
    raise ValueError(f"Unknown backend '{name}'. Choose mock, serial or gpio")
