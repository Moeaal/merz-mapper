# Hardware register

Only manufacturer- or datasheet-confirmed figures go in "Confirmed specs"; cite
RESEARCH_INDEX tags. Integration status: NOT ORDERED / ORDERED / RECEIVED /
DRIVER RUNNING / CALIBRATED / ON ROVER.

| Component | Confirmed specs | ROS 2 driver | Interface | Power | Integration status |
| --- | --- | --- | --- | --- | --- |
| Rover base | University-built 4-wheel rover (skid-steer); **12 V DC motors** x4 (student, 2026-11-09); **no encoders** (decisions #10). Battery: not chosen - 4S LiPo considered (decisions #30). Motor stall current, mass, mounting/CAD: UNKNOWN | `merz_base` (PCA9685 backend still to write, decisions #28) | 2x Waveshare Motor Driver HAT over I2C | 12 V motors; bench: mains 12 V supply (student, 2026-11-09) | RECEIVED 2026-11-09 |
| NVIDIA Jetson Orin Nano | **Orin Nano 8 GB Developer Kit**. Measured 2026-11-10: **L4T R36.4.7** (JetPack 6.2.x series; GCID 42132812, built 18 Sep 2025), **Ubuntu 22.04.5 LTS**. Firmware was already JetPack 6-compatible (JetPack 6 SD image booted directly) [H6]. Power mode: MAXN SUPER (student to confirm `nvpmodel -q`). CUDA/TensorRT versions: record (`dpkg -l \| grep -E "nvidia-jetpack\|tensorrt"`). Note: distro-decision planned L4T 36.5.x (6.2.3); 36.4.7 is what the SD image gave (OPEN_ISSUES #27) | - | - | dev-kit 19 V adapter (bench) | RECEIVED 2026-11-09; flashed (microSD), ROS 2 Humble installed 2026-11-10 |
| SLAMTEC RPLIDAR S2 | 0.05-30 m (90% reflect.), 0.05-10 m (10% reflect.); 10 Hz scan; 32 kHz sampling; ±30 mm accuracy [H1] | `sllidar_ros2` (SLAMTEC), source build (not in rosdistro); repo config `lidar_s2.yaml`, `lidar_model:=s2` (decisions #33); apt fallback `rplidar_ros` has `rplidar_s2_launch.py` [S26, S28] | UART 1 Mbaud via USB adapter board [H1] | 5 V; startup current up to 1.5 A, ~0.5 A running [H1] | ORDERED - on the way (student, 2026-11-09) |
| Intel RealSense D455 | Ideal depth range 0.6-6 m; min-Z ~0.52 m; <2% error at 4 m; depth FOV 87°x58°; BMI055 IMU [H2] | librealsense v2.59.1 (RSUSB source build) + realsense-ros 4.59.1 (decisions #21). Firmware: record it; never below 5.13.0.50. IMU on JetPack 6: known risk (OPEN_ISSUES #22) | USB-C 3.1 Gen 1 | USB bus powered; use powered hub [H3] | ORDERED - on the way (student, 2026-11-09) |
| Logitech C920 | 1080p, autofocus (vendor) | `usb_cam` or `v4l2_camera` | USB 2.0 UVC | USB bus powered | RECEIVED 2026-11-09 |
| SLAMTEC RPLIDAR C1 (**temporary**, until the S2 arrives) | 12 m (70% reflect.), 0.05 m blind range, 10 Hz, 5 kHz sampling, 0.72°, ±30 mm [H4] | `sllidar_ros2`; repo config `lidar_c1.yaml` (460800 baud, Standard), `lidar.launch.py lidar_model:=c1` (default) [H7] (decisions #33) | TTL UART via USB adapter; USB IDs: record (`udevadm info`) | 5 V, ~230 mA [H4] | RECEIVED 2026-11-09; DRIVER RUNNING on Jetson 2026-11-10 (student report; rate and 1 m check to log) |
| Waveshare Motor Driver HAT x2 | PCA9685 PWM + TB6612FNG dual H-bridge, 2 motors each, VIN 6-12 V, I2C address by 5 jumpers [H5]. Per-channel current: not stated by Waveshare | none yet (PCA9685 backend for `merz_base`, decisions #28) | I2C, jumper-wired to the Jetson header (3.3 V, GND, SDA, SCL) - not plugged on (decisions #28) | 12 V motor supply via kill switch (decisions #29) | RECEIVED 2026-11-09; I2C addresses: record |
| Powered USB 3.0 hub (4-port) | - | - | USB 3.0 | mains/rover supply - **must work on battery** | ORDERED by supervisor (Nov 2026; delivery date TBC) |
| NVMe SSD 256 GB+ | - | - | M.2 | - | ORDERED by supervisor (Nov 2026; delivery date TBC) |
| Wireless gamepad | - | `joy` + `teleop_twist_joy` | USB dongle/Bluetooth | - | OWNED by student (2026-11-09) |
| Mast + 3D-printed mounts | camera at ~1.5 m | - | - | - | Mast OWNED (2026-11-09); mounts to design from rover CAD |
| Calibration checkerboard | - | `camera_calibration` | - | - | OWNED by student (2026-11-09) |
| Laser distance meter | 40 m+ | - | - | battery | ORDERED by supervisor (Nov 2026; delivery date TBC) |

## Notes
- 2026-11-02: supervisor ordered everything on `Rover_Parts_List.xlsx`; delivery expected within a few days, rover arriving with the parts. Rover CAD to be shared by supervisor (for mount design). Gamepad, mast,
  mounts, checkerboard and QR posters were not on that list.
- Proposal Table 2 says D455 range "0.4-6 m"; Intel lists **0.6-6 m** ideal
  range (one distributor says 0.4 m). Use 0.6-6 m in submissions [H2].
- Powered hub on a moving rover needs a DC supply from the rover battery, not mains.
- Jetson power modes (JetPack 6.2, 8 GB): 15 W, 25 W, MAXN SUPER (4 GB: 10 W, 25 W, MAXN SUPER) [S15]. Record the power mode with every rate/FPS measurement.
- [S..] tags refer to the source table in `docs/research/distro-decision.md` §7.
- 2026-11-09: received Jetson Orin Nano 8 GB Dev Kit, rover, C920, RPLIDAR C1 (stand-in) and 2x Waveshare Motor Driver HAT. D455 and S2 on the way. Hub, NVMe and laser meter: student to confirm whether received.
- 2026-11-10: the Jetson user is `moe`, not `merz` as `hardware-arrival-plan.md` §3.1 assumed; `merz_perception/config/perception.yaml` paths use `/home/merz/` (OPEN_ISSUES #26).
