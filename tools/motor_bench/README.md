# Motor bench test (not ROS)

Spins each of the four wheels on its own, slowly, so the student can record which HAT channel drives which wheel and
which way "+" turns it. Status: **IMPLEMENTED** (unit tests with a fake I2C bus only). Not yet run on hardware.

Before running: wheels off the ground, bench-supply output button within reach (decisions #29), HATs wired with
**SDA, SCL and GND only** (decisions #28), 12 V on both HAT VIN terminals (the HAT's I2C logic is powered from VIN).

```bash
sudo apt install -y i2c-tools python3-smbus
i2cdetect -y -r <bus>                        # expect 40 and 41
python3 tools/motor_bench/motor_bench_test.py --bus <bus>
```

Options: `--speed` (percent, default 30, max 50), `--seconds` (default 2), `--freq` (PWM Hz, default 1000),
`--dry-run` (no hardware). Ctrl+C or any error stops every motor. Results go in the logbook and HARDWARE_REGISTER,
then into the PCA9685 backend in `merz_base`.
