# merz_base

**Status: IMPLEMENTED - not yet built or tested on hardware.** The rover is not yet known, so **no backend has driven a real
motor**, and the serial command format and GPIO pins are placeholders. Passing unit tests do not show the rover is safe to drive.

Takes `/cmd_vel_mux` and drives the motors.

## Choosing a backend
Set `backend` in `config/base.yaml`. The default is `mock`, so nothing moves until this is changed on purpose.
| Backend | Use when | Must be filled in first |
| --- | --- | --- |
| `serial` | The rover has a motor controller board | Port, baud, command format, stop command, scale: from its manual |
| `gpio` | Bare H-bridge | Pins, after checking the Orin Nano pinout and enabling PWM with `jetson-io`. Install `Jetson.GPIO` |
| `mock` | Tests, and running the stack with no motors | Nothing |

If the rover already has its own computer or a ROS driver, it may be better to use that and retire this package. Ask first.

## Safety behaviour
- **Command timeout:** no command for `command_timeout_s` stops the motors immediately, using the monotonic clock rather
  than ROS time, so that a stopped ROS clock cannot defeat it.
- **Limits:** commands are clamped to the speed limits, and acceleration is limited in both directions.
- **Bad input:** NaN and infinity are ignored, and so count towards the timeout.
- **Shutdown:** Ctrl-C stops the motors before exit.

**What this does not cover:** if the process or Jetson dies outright, nothing sends a stop. A serial controller with its own
watchdog would handle that, but a GPIO PWM output may stay at its last value. Check this with the wheels off the ground, and
keep a physical power cut within reach. Test each behaviour above on the real rover, using the checklist in `merz_bringup`.

## Steps once the rover arrives
1. Inspect it and fill in `docs/HARDWARE_REGISTER.md`. Is there an existing controller or computer?
2. Fill in `config/base.yaml`, with the wheels **off the ground**.
3. Send small commands, and check direction and sign: forward first, then positive yaw must turn **left** (REP 103).
4. Measure `full_speed_m_s` and the effective `track_width_m`.

## Unit tests that pass on Windows
`test/test_base_core.py`: kinematics, limits, acceleration ramp, timeout stop, bad input, shutdown, serial output format with a
fake port, and GPIO pin logic with a fake `Jetson.GPIO`. **Real serial and GPIO hardware are not covered**, nor is `base_node`.
