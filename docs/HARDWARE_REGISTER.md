# Hardware register

Only manufacturer- or datasheet-confirmed figures go in "Confirmed specs"; cite
RESEARCH_INDEX tags. Integration status: NOT ORDERED / ORDERED / RECEIVED /
DRIVER RUNNING / CALIBRATED / ON ROVER.

| Component | Confirmed specs | ROS 2 driver | Interface | Power | Integration status |
| --- | --- | --- | --- | --- | --- |
| Rover base | University-built simple rover; spec to inspect on receipt (motors, controller, encoders?, battery, mounting) | UNKNOWN | UNKNOWN | UNKNOWN battery | NOT RECEIVED |
| NVIDIA Jetson Orin Nano | JetPack 6.2.x = L4T 36.5.x, kernel 5.15, Ubuntu 22.04; CUDA 12.6, TensorRT 10.3, cuDNN 9.3 (NVIDIA, via search; distro-decision [S6-S8]). SKU (Dev Kit or carrier), RAM and measured versions: record once flashed [J1] | - | - | per rover/dev-kit supply | ORDERED by supervisor (Nov 2026; delivery date TBC) |
| SLAMTEC RPLIDAR S2 | 0.05-30 m (90% reflect.), 0.05-10 m (10% reflect.); 10 Hz scan; 32 kHz sampling; ±30 mm accuracy [H1] | `sllidar_ros2` (SLAMTEC), source build (not in rosdistro); apt fallback `rplidar_ros` has `rplidar_s2_launch.py` [S26, S28] | UART 1 Mbaud via USB adapter board [H1] | 5 V; startup current up to 1.5 A, ~0.5 A running [H1] | ORDERED by supervisor (Nov 2026; delivery date TBC) |
| Intel RealSense D455 | Ideal depth range 0.6-6 m; min-Z ~0.52 m; <2% error at 4 m; depth FOV 87°x58°; BMI055 IMU [H2] | librealsense v2.59.1 (RSUSB source build) + realsense-ros 4.59.1 (decisions #21). Firmware: record it; never below 5.13.0.50. IMU on JetPack 6: known risk (OPEN_ISSUES #22) | USB-C 3.1 Gen 1 | USB bus powered; use powered hub [H3] | ORDERED by supervisor (Nov 2026; delivery date TBC) |
| Logitech C920 | 1080p, autofocus (vendor) | `usb_cam` or `v4l2_camera` | USB 2.0 UVC | USB bus powered | ORDERED by supervisor (Nov 2026; delivery date TBC) |
| Powered USB 3.0 hub (4-port) | - | - | USB 3.0 | mains/rover supply - **must work on battery** | ORDERED by supervisor (Nov 2026; delivery date TBC) |
| NVMe SSD 256 GB+ | - | - | M.2 | - | ORDERED by supervisor (Nov 2026; delivery date TBC) |
| Wireless gamepad | - | `joy` + `teleop_twist_joy` | USB dongle/Bluetooth | - | **missing from parts list** |
| Mast + 3D-printed mounts | camera at ~1.5 m | - | - | - | **missing from parts list** |
| Calibration checkerboard | - | `camera_calibration` | - | - | **missing from parts list** |
| Laser distance meter | 40 m+ | - | - | battery | ORDERED by supervisor (Nov 2026; delivery date TBC) |

## Notes
- 2026-11-02: supervisor ordered everything on `Rover_Parts_List.xlsx`; delivery expected within a few days, rover arriving with the parts. Rover CAD to be shared by supervisor (for mount design). Gamepad, mast,
  mounts, checkerboard and QR posters were not on that list.
- Proposal Table 2 says D455 range "0.4-6 m"; Intel lists **0.6-6 m** ideal
  range (one distributor says 0.4 m). Use 0.6-6 m in submissions [H2].
- Powered hub on a moving rover needs a DC supply from the rover battery, not mains.
- Jetson power modes (JetPack 6.2, 8 GB): 15 W, 25 W, MAXN SUPER (4 GB: 10 W, 25 W, MAXN SUPER) [S15]. Record the power mode with every rate/FPS measurement.
- [S..] tags refer to the source table in `docs/research/distro-decision.md` §7.
