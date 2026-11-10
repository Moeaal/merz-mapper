# Merz Mapper build guide

**Not yet verified on hardware.** None of these steps has been run. Expect some commands, topic names and parameter names to
need correcting, and fix this guide as you go. Log every test in `docs/logbook/`. Keep to the safety checklist in
`ros2_ws/src/merz_bringup/README.md` before any motion.

Assumes JetPack 6.x + Ubuntu 22.04 + ROS 2 Humble (decisions #6, still to be confirmed with Dr Wright).

## 1. Parts and connections
| Device | Connects to | Cable or link | Power | Notes |
| --- | --- | --- | --- | --- |
| Jetson Orin Nano | - | - | Rover battery via DC-DC (rating: check against the Jetson supply) | The computer |
| NVMe SSD | Jetson M.2 slot | - | From Jetson | Boot and data disk |
| RealSense D455 | Jetson USB 3 port, **direct, not via the hub** | USB-C 3.1 cable (short, good quality) | USB bus | Must show as USB 3.x |
| Powered USB hub | Jetson USB port | USB 3 | Rover battery via DC-DC, **not mains** | Must work on battery |
| RPLIDAR S2 adapter | Hub | USB + adapter board | 5 V: start-up current up to 1.5 A, about 0.5 A running [H1] | `/dev/rplidar` |
| Logitech C920 | Hub | USB | USB bus | `/dev/c920` |
| Gamepad dongle | Hub | USB | - | Not yet bought |
| Motor controller or H-bridge | See `merz_base` | Unknown until the rover arrives | Rover battery | Keep motor power separate from logic |

```
                    Rover battery ---[power cut]---+------> Motor controller / H-bridge --> Motors
                                                   |
                                                   +--[DC-DC]--> Jetson Orin Nano
                                                   |              |  |  M.2: NVMe SSD
                                                   |              |  +--USB 3--> RealSense D455 (direct)
                                                   |              +-----USB 3--> Powered hub
                                                   |                              |- RPLIDAR adapter -> RPLIDAR S2
                                                   +--[DC-DC]--> Powered hub      |- Logitech C920
                                                                                  +- Gamepad dongle
                     Jetson <-- USB serial or GPIO --> Motor controller (see merz_base)
```
Do not fit the DC-DC converters until their input and output ratings are checked against the battery and each load. Add up the
power budget once the rover's battery is known, and measure the real current draw (O1).

**GPIO pins:** only for the `merz_base` GPIO backend. See `ros2_ws/src/merz_base/config/base.yaml`. Check each pin against
NVIDIA's Orin Nano pinout, enable PWM with `jetson-io`, and share a ground. Never power a motor from the header.

## 2. Mechanical
- **Mast:** C920 at about 1.5 m, so that it sees door signs. Stiff enough not to sway when the rover stops.
- **LIDAR:** level, at a height clear of the chassis, mast and cables, with an unobstructed view. Any part of the rover in its
  plane appears as a permanent obstacle. Check with a spirit level.
- **D455:** forward-facing, level, with nothing in its view.
- **Measure each pose and fill in `merz_description/config/sensor_poses.yaml`:**
  1. Mark `base_link` on the floor beneath the rover's centre of rotation (midway between the wheels on a skid-steer base).
  2. Measure with a ruler or laser meter, along x (forward), y (left) and z (up) from that point:
     - `laser`: to the centre of the LIDAR's optical window.
     - `camera_link`: to the D455's reference point, as shown on its datasheet.
     - `sign_camera`: to the C920's lens.
  3. Measure any tilt as an angle: a C920 pitched downwards has a positive pitch. Use the CAD of the printed mounts where possible.
  4. Check it in RViz (`description.launch.py rviz:=true include_d455_internal_frames:=true`), then record the date and
     measurement uncertainty in the logbook. **Pose error goes straight into landmark error (O4).**

## 3. Jetson setup
**Flash JetPack 6.x to the NVMe** using NVIDIA SDK Manager from an Ubuntu host (the laptop has no Linux: decisions #11; ask the
department or use the Pi only if SDK Manager supports it). Record JetPack, L4T, CUDA and TensorRT versions in
`HARDWARE_REGISTER.md`.

**Power mode:**
```bash
sudo nvpmodel -q              # see the current mode
sudo nvpmodel -m 0            # check first that mode 0 is the highest one on your module
sudo jetson_clocks            # for benchmarks
```

**ROS 2 Humble:**
```bash
sudo apt update && sudo apt install -y software-properties-common curl
sudo add-apt-repository universe
# Add the ROS 2 apt repository, following the current instructions at docs.ros.org/en/humble/Installation/Ubuntu-Install-Debians.html
sudo apt install -y ros-humble-ros-base python3-colcon-common-extensions python3-rosdep python3-vcstool
echo 'source /opt/ros/humble/setup.bash' >> ~/.bashrc && source ~/.bashrc
sudo rosdep init && rosdep update
```

**librealsense with the RSUSB backend (OPEN_ISSUES #3).** Budget a full day. Check the steps in Intel's Jetson install doc [H3]
as you go, as they change with versions:
```bash
sudo apt install -y git cmake build-essential libssl-dev libusb-1.0-0-dev libudev-dev pkg-config libgtk-3-dev
git clone https://github.com/IntelRealSense/librealsense.git ~/librealsense
cd ~/librealsense
git checkout <release recommended for the realsense-ros version you will use>
sudo cp config/99-realsense-libusb.rules /etc/udev/rules.d/ && sudo udevadm control --reload-rules && sudo udevadm trigger
mkdir build && cd build
cmake .. -DFORCE_RSUSB_BACKEND=ON -DBUILD_WITH_CUDA=ON -DCMAKE_BUILD_TYPE=Release -DBUILD_EXAMPLES=true
make -j$(nproc) && sudo make install
rs-enumerate-devices          # must list the D455, on USB 3.x
```
Update the camera's firmware to the version in that release's notes. Log the exact versions.

**Workspace:**
```bash
cd ~ && git clone https://github.com/Moeaal/merz-mapper.git
cd ~/merz-mapper/ros2_ws
vcs import src < merz.repos
git clone -b <tag matching your librealsense> https://github.com/IntelRealSense/realsense-ros.git src/third_party/realsense-ros
rosdep install --from-paths src --ignore-src -r -y --skip-keys "librealsense2"
pip3 install --user numpy pyyaml pyserial
colcon build --symlink-install
source install/setup.bash && echo "source ~/merz-mapper/ros2_ws/install/setup.bash" >> ~/.bashrc
colcon test && colcon test-result --verbose
```
First build `rf2o_laser_odometry` by itself: Humble support is not stated upstream (decisions #14). If it fails, use the Adlink
fork noted in decisions #14 and record the outcome.

**udev rules:**
```bash
cd ~/merz-mapper/ros2_ws/src/merz_bringup/udev
sudo cp 99-merz-*.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
ls -l /dev/rplidar /dev/c920
```

## 4. Bring-up checks, one device at a time
Do these with the rover on blocks, and log each one. A failure at one step stops you: do not go on and debug it all at once.
| Device | Command | What "working" looks like |
| --- | --- | --- |
| LIDAR | `ros2 launch merz_bringup lidar.launch.py` (C1 stand-in; add `lidar_model:=s2` for the S2, decisions #33) | `ros2 topic hz /scan` about 10 Hz. In RViz (fixed frame `laser`), the room outline looks right |
| D455 | `ros2 launch merz_bringup d455.launch.py` | Image and depth appear in RViz; depth about 15 Hz; a flat wall at a known distance measures correctly |
| D455 IMU | same | `ros2 topic hz /camera/camera/imu` near the gyro rate. Rotating by hand changes the angular velocity on the expected axis |
| C920 | `ros2 launch merz_bringup c920.launch.py` | `/sign_cam/image_raw` about 10 Hz. A door sign is readable in the image at working distance |
| URDF | `ros2 launch merz_description description.launch.py rviz:=true` | Frames in the right places. `ros2 run tf2_tools view_frames` shows one tree |
| Gamepad | `ros2 launch merz_bringup teleop.launch.py` | `ros2 topic echo /cmd_vel_mux` moves only while the deadman is held. Fix the axis numbers in `teleop.yaml` |
| Motors, **wheels off the ground** | `ros2 launch merz_base base.launch.py` + teleop | Right direction and sign. Kill teleop with the wheels turning: they stop within `command_timeout_s` |
| All at once | `ros2 launch merz_bringup sensors.launch.py` | All rates hold together for 20 minutes. Watch `tegrastats` for heat and USB errors |

## 5. Calibration
**C920 intrinsics, with the checkerboard** (not yet bought):
```bash
v4l2-ctl -d /dev/c920 --set-ctrl=focus_automatic_continuous=0     # control names vary by driver; list them with --list-ctrls
ros2 run camera_calibration cameracalibrator --size 8x6 --square 0.025 \
  --ros-args -r image:=/sign_cam/image_raw -p camera:=/sign_cam
```
Set `--size` (inner corners) and `--square` (metres) to the real board. Save the result as `merz_bringup/config/c920_camera_info.yaml`,
keeping `camera_name: sign_camera`. Autofocus alters the intrinsics, so the C920 is used for reading and for matching text to signs,
and not for measuring position.

**IMU noise, 60 s stationary:**
```bash
ros2 bag record -s mcap -o imu_still /camera/camera/imu     # 60 s, rover still, motors off
```
Calculate the mean (gyro bias) and SD of `angular_velocity.z`. Compare the variance with the covariance in the messages, and log
both. A large bias would drift the heading, so consider also fusing vyaw from scan matching in `ekf.yaml`.

**Scan odometry noise:** drive a measured straight line by teleop, and compare `/odom_scan` distance with the laser meter. Set `vx_std`
from the differences.

**EKF check, square path:** drive a 2 m square back to the start mark, three times each way:
```bash
ros2 launch merz_bringup mapping.launch.py     # compare /odometry/filtered at the start and at the end
```
Use `/odometry/filtered`, not the map pose: SLAM would hide the odometry drift being measured.
Report the position and heading error at the end. Tune `process_noise_covariance` only if there is a clear reason, one change at a
time, logging each. Also measure `track_width_m` here: command a fixed turn rate, and compare with the IMU.

**D455 check:** flat wall at 1, 2, 3 and 4 m, measured by laser. Compare with the depth image. Do not recalibrate unless there is a clear error.

## 6. Running
**Manual mapping (G1, by 18 Dec 2026; aim for ~11 Dec):**
```bash
ros2 launch merz_bringup mapping.launch.py                        # terminal 1
ros2 launch merz_bringup record_bag.launch.py name:=first_map     # terminal 2
# Drive slowly, with gentle turns. Close a loop if possible. Watch /map in RViz. Then:
ros2 run nav2_map_server map_saver_cli -f ~/merz_data/maps/first_map
```
**Back up the bags before the leave on 19 Dec:** mapping can continue offline from them.

**Exploration from an entrance.** Read the safety checklist, and test with a person beside it and reduced speed:
```bash
# First entrance creates the map frame. Until a model is trained, add perception:=false
ros2 launch merz_bringup explore_from_entrance.launch.py entrance:=east entrance_name:="East door" perception:=false
# To end early:
ros2 service call /mission_node/finish std_srvs/srv/Trigger
# Later entrance: continue from the saved posegraph, giving the start pose in that map frame
ros2 launch merz_bringup explore_from_entrance.launch.py entrance:=west entrance_name:="West door" \
  posegraph:=~/merz_data/maps/east_<time> start_x:=12.0 start_y:=3.5 start_yaw:=1.57
```
Record door states at every run (O5).

**Perception:** record bags with `images:=true`; extract frames with `tools/extract_frames.py`; label a few hundred; train a small
YOLO model. Hold one corridor back for testing. Export using `tools/export_tensorrt.md`, then set `weights` and `engine` in
`merz_perception/config/perception.yaml`, and the `room_regex` to the real sign format.

**Database:** written to `~/merz_data/merz.sqlite`. See `docs/software/database-schema.md`. To recompute zones offline:
`python -m merz_exploration.compute_access_zones --map <map.yaml> --database merz.sqlite --entrance east --start 0 0`

**Evaluation:** `docs/planning/experiments.md`, using `tools/eval/`.

**Website:**
```bash
cd ~/merz-mapper/web && pip3 install -r requirements.txt
MERZ_DB=~/merz_data/merz.sqlite MERZ_PHOTOS=~/merz_data/photos python3 -m uvicorn app.main:app --host 0.0.0.0
python3 qr_posters.py --database ~/merz_data/merz.sqlite --base-url http://<reachable-address>:8000 --out posters
```

## 7. Troubleshooting (known risks, from `docs/OPEN_ISSUES.md`)
| Symptom | Likely cause | Try |
| --- | --- | --- |
| D455 not detected, or on USB 2 | Cable, port, power or kernel backend (#3) | Direct USB 3 port, short cable, RSUSB build, check firmware, `rs-enumerate-devices` |
| D455 drops out under load | USB bandwidth or power | Lower the streams in `d455.yaml`; turn off `pointcloud.enable` |
| No `/camera/camera/...` topics | Driver version | `ros2 topic list`. Older versions use `/camera/...`: search for `/camera/camera` and change each one |
| EKF gives nothing from the IMU | QoS or missing TF to the IMU frame | `ros2 topic info -v`; check `camera_imu_optical_frame` exists in TF |
| Two publishers of `odom->base_link` | rf2o or a driver also publishing it | `publish_tf: false` in `scan_odometry.yaml`; only the EKF may do it |
| Heading drifts when still | Gyro bias, no magnetometer (#15) | Measure the bias; try fusing scan vyaw |
| Position stops in long corridors | Scan matching has nothing to lock on to (#15) | Slow down; open doors for features; check `/odom_scan`; consider encoders with Dr Wright |
| "Dropped implausible scan odometry" | rf2o jumped | Check the bag; raise the limit only with evidence |
| Walls doubled or map skewed | Fast turns, wrong laser pose, or poor odometry | Slow the turns; check `sensor_poses.yaml`; re-run SLAM from the bag |
| SLAM Toolbox complains about scan size | The driver's reading count varies | Keep `angle_compensate: true`; check the rate; see the slam_toolbox issues |
| Robot aims at glass, or the map is noisy near it (#4) | LIDAR sees through or reflects off glass | Keep-out mask (`merz_bringup/maps/README.md`); lower `max_laser_range`; mark glass in evaluation |
| Exploration stops too early | `min_frontier_size`, or mission timeout | Check `/explore/frontiers` in RViz; check the mission log's end reason |
| Mission never ends, or ends at once | The marker assumption in `mission_node` is wrong | Echo `/explore/frontiers`; correct the `_on_frontiers` count |
| Access zone too large | A door was open, or a stale map (`docs/software/database-schema.md`) | Check logged door states; run the entrance in a fresh map and compare |
| Access zone empty | Start pose wrong, or map YAML path | Check `start_x/y` against the map; re-run `compute_access_zones` |
| OCR rejects everything | Blur threshold or regex | Look at the `sharpness` CSV column; set `min_sharpness` and `room_regex` from real data |
| PaddleOCR will not install on the Jetson | aarch64 + GPU | `ocr_engine: rapid` with `rapidocr-onnxruntime`, or CPU |
| FPS falls over time | Thermal throttling | `tegrastats`; improve airflow; log the power mode |
| Motors keep running after a crash | No process left to send a stop | Physical power cut. Fix this before more runs (`merz_base/README.md`) |
| Rover runs out of power, or the hub cuts out | Budget, or start-up current | Measure the draw; check the DC-DC ratings; stagger start-up |
| Zero buffer before leave (#5) | G1 on 18 Dec, leave on 19 Dec | Target ~11 Dec; bags backed up to OneDrive |
| No wall-accuracy reference (#14) | No floor plan | Ask estates or Dr Wright; otherwise a laser survey of the chosen corridors |
