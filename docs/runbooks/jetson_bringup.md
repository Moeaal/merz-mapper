# Jetson Orin Nano bring-up runbook: from flashing to all sensors publishing

**Status: PLANNED. Nothing in this runbook has been run on the Merz Mapper hardware.** Expect some commands, versions and topic
names to need correcting. When a step is done, write the result in `docs/logbook/` (date, exact versions, command, output,
pass/fail). Only then may anything be called TESTED.

**Assumes the PROPOSED platform** in `docs/research/distro_decision.md`: JetPack 6.2.x (newest 6.2.3 / L4T 36.5.2) + Ubuntu
22.04 + ROS 2 Humble. It is not yet confirmed with Dr Wright (OPEN_ISSUES #2). Where option B (JetPack 7.2.1 + Jazzy) differs,
a note says so.

**Markers**
- **[ROVER]**: depends on the rover, which is still UNKNOWN (OPEN_ISSUES #1). Do not guess: inspect the rover first.
- **[SKU]**: depends on which Jetson arrived (Developer Kit or third-party carrier; 4 GB or 8 GB). See distro_decision section 6.
- **[MISSING]**: the part is not on the parts list (gamepad, mast, mounts, checkerboard: OPEN_ISSUES #10).
- **Gate**: a step that must pass before you go on. If a gate fails, stop and log it; do not debug several things at once.

Source tags such as [S16] refer to the source table in `docs/research/distro_decision.md`. Tags such as [H1] refer to
`docs/RESEARCH_INDEX.md`.

Order of work: 1 inventory -> 2 flash -> 3 system set-up -> 4 ROS 2 + workspace -> 5 udev -> 6 one sensor at a time ->
7 rosbags. Sections 8-10 are reference: powered hub, pitfalls, rover-dependent steps.

---

## 1. Inventory and version record (about 30 min)

1. Unpack on an anti-static surface. Photograph every label: Jetson module and carrier, D455, RPLIDAR S2 and its USB adapter board,
   C920, hub, NVMe SSD.
2. Write down **[SKU]**: is it an NVIDIA Orin Nano Developer Kit (or "Super" Dev Kit), or a module on another carrier? Memory
   4 GB or 8 GB? This decides the flashing route (section 2) and the power modes [S15].
3. Check that the camera really is a **D455** (not a D455f). The firmware downgrade in 6.3 is only allowed for the D455, and never below
   5.13.0.50 [S20, S23].
4. Start a logbook entry from `docs/logbook/TEMPLATE.md`. Copy this table into it and fill it in as you go:

| Item | Value |
| --- | --- |
| Jetson SKU / carrier / RAM | |
| L4T (`cat /etc/nv_tegra_release`) | |
| JetPack (`apt-cache show nvidia-jetpack \| grep Version`) | |
| CUDA (`nvcc --version`, or `/usr/local/cuda/version.json`) | |
| TensorRT (`dpkg -l \| grep -i tensorrt`) | |
| Power mode (`sudo nvpmodel -q`) | |
| ROS 2 distro and `ros-humble-ros-base` version | |
| librealsense tag / realsense-ros tag | |
| D455 firmware (`rs-enumerate-devices \| grep -i firmware`) | |
| D455 serial number | |
| RPLIDAR S2 firmware/hardware (printed by `sllidar_node` at start-up) | |
| Commit of each third-party repo (`vcs log -l1` or `git -C <dir> rev-parse HEAD`) | |

---

## 2. Flashing to the NVMe SSD

Boot **and** data both go on the NVMe: bags are large (BUILD_GUIDE; perception skill). Fit the NVMe SSD in the carrier's M.2
slot **before** flashing. Pick **one** route. The student's laptop runs Windows and has no Linux install (decisions #11), so
route 2.2 is the expected one unless the department has a PC for route 2.1.

### 2.1 Route A1: SDK Manager from an x86_64 Ubuntu PC (most reliable, if one is available)
SDK Manager needs an **x86_64** Ubuntu host (20.04 or 22.04 for JetPack 6) [S13]. The Raspberry Pi 5 is arm64 and does not count.
1. On the host, install NVIDIA SDK Manager (needs a free NVIDIA developer account).
2. Put the Jetson in Force Recovery mode **[SKU]**: on the Developer Kit, by bridging the FC REC and GND pins on the button header while
   powering on. Check the pins in NVIDIA's Developer Kit user guide for your board revision.
3. Connect the Jetson's USB-C port to the host. Check that `lsusb` on the host shows an NVIDIA device.
4. In SDK Manager pick Jetson Orin Nano, **JetPack 6.2.3** (or the newest 6.2.x listed), storage **NVMe**, and let it flash
   the QSPI firmware as well. Install the "Jetson SDK Components" (CUDA, cuDNN, TensorRT) in the same session.

### 2.2 Route A2: no Linux host (Windows laptop only)
Uses NVIDIA's microSD image to update the firmware, then puts the same image on the NVMe. The second half is a **community-reported
method, not NVIDIA-documented** [S12]. If it fails, use route 2.1 or the fallback in 2.3.
1. **[SKU]** Developer Kit only: download the JetPack 6.2.x microSD card image for the Orin Nano Developer Kit from NVIDIA's
   JetPack page. Write it to a 64 GB+ microSD card with balenaEtcher on Windows.
2. Boot the Jetson from the microSD card (NVMe removed or blank). Finish the Ubuntu first-boot set-up.
3. **Firmware gate:** reboot and read the UEFI firmware version on the boot splash (press Esc for the UEFI menu if it goes past too
   fast). The kit must reach 36.x firmware. If it was on JetPack 5-era firmware, follow NVIDIA's Orin Nano "JetPack 6.x update path", which may take more than one
   reboot [S11, S12].
4. Put the NVMe in a USB-to-M.2 NVMe enclosure, plug it into the Windows laptop and write the **same** microSD image to it with balenaEtcher.
   Alternatively, write it from the running Jetson to the NVMe in its M.2 slot. A forum user reports that this boots JetPack 6.2.1 from NVMe [S12].
5. Fit the NVMe, remove the microSD card and power on.
6. Grow the root partition to fill the SSD if it did not grow itself: check with `df -h /`. If needed, use `sudo growpart /dev/nvme0n1 1`
   then `sudo resize2fs /dev/nvme0n1p1`. Check the partition number with `lsblk` first: the APP partition is usually `p1`, but check.

### 2.3 Fallback if 2.2 does not boot from NVMe
Run from the microSD card for now (slower, and it wears out faster) and keep bags on the NVMe mounted as a data disk:
`sudo mkfs.ext4 /dev/nvme0n1` (this **erases** the SSD: check `lsblk` first), mount it at `/mnt/nvme`, add it to `/etc/fstab`,
and point `directory:=` in `record_bag.launch.py` at it. Then arrange route 2.1 with Dr Wright.

### 2.4 Option B note (only if JetPack 7.2.1 + Jazzy is chosen)
Write the **Jetson ISO** to a USB stick of 16 GB or more, boot it, and install straight to the NVMe; the installer updates the QSPI
firmware itself. The kit must already have JetPack 6-era firmware (step 2.2.3) [S11]. There is no microSD image for 7.2 [S10, S11].

### 2.5 Gate: first-boot checks
```bash
cat /etc/nv_tegra_release                 # L4T: expect R36 (revision 5.x for JetPack 6.2.2/6.2.3)
findmnt -n -o SOURCE /                    # must be /dev/nvme0n1p<N> (not mmcblk = microSD)
lsb_release -a                            # Ubuntu 22.04
df -h /                                   # most of the SSD is available
sudo apt update && sudo apt full-upgrade  # NVIDIA's L4T apt source brings the JetPack point release
sudo apt install -y nvidia-jetpack        # CUDA, cuDNN, TensorRT, if not installed by SDK Manager
```
Record the values in the section 1 table.

---

## 3. System set-up (about 1 h)

1. **Power mode [SKU].** List the modes and pick the highest stable one. Do not assume the mode number [S15]:
   ```bash
   sudo nvpmodel -q                                # current mode
   grep POWER_MODEL /etc/nvpmodel.conf             # every mode with its ID and name
   sudo nvpmodel -m <ID>                           # e.g. the 25 W or MAXN SUPER ID from that list
   sudo jetson_clocks             # benchmarks only (perception skill)
   ```
   Record the mode with every FPS or rate figure.
2. **Power from the rover battery [ROVER].** For now use the Developer Kit's own supply on the bench. Do not wire the Jetson to the
   rover battery until the DC-DC converter rating has been checked against the Jetson's input requirement and the battery (BUILD_GUIDE §1).
3. **Disable USB autosuspend.** It is a common cause of RealSense drop-outs; one reporter tried it [S21]. Treat it as cheap insurance, not a known fix:
   ```bash
   cat /sys/module/usbcore/parameters/autosuspend      # 2 by default on most kernels; -1 = off
   # make it permanent: add usbcore.autosuspend=-1 to the APPEND line in /boot/extlinux/extlinux.conf, then reboot
   ```
   Keep a copy of `extlinux.conf` before editing: a mistake there can stop the Jetson booting.
4. **SSH and hostname** so that it can run headless on the rover (`HARDWARE_ARRIVAL_PLAN.md` §3.4): `sudo hostnamectl set-hostname merz-jetson`,
   check `sudo systemctl status ssh`.
5. **Clock.** Bags and TF need a correct clock: check `timedatectl` shows "System clock synchronized: yes" on the university network.
6. **Monitoring.** `tegrastats` is built in. `jtop` (pip `jetson-stats`) is optional; one report says it shows the JetPack
   version as missing on a fresh 6.2.2 flash, which is only a display problem (search result, anecdotal).
7. **Swap.** Building librealsense and the workspace can run out of memory on a 4 GB module **[SKU]**. NVIDIA's zram swap is usually on (`swapon --show`).
   If builds are killed, add a swap file on the NVMe, or build with `-j2` / `--parallel-workers 2`.

---

## 4. ROS 2 Humble and the workspace (about 1 day, mostly librealsense)

### 4.1 ROS 2 Humble from apt
These steps follow the Humble install page's source on the `humble` branch of `ros2/ros2_documentation` (fetched 2026-11-05).
Re-read the page itself (docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html) before running them; it changes.
```bash
locale    # must be UTF-8; if not, follow the locale step on the install page
sudo apt install -y software-properties-common && sudo add-apt-repository universe
sudo apt update && sudo apt install -y curl
export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F'"' '{print $4}')
curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo ${UBUNTU_CODENAME:-${VERSION_CODENAME}})_all.deb"
sudo dpkg -i /tmp/ros2-apt-source.deb
sudo apt update && sudo apt upgrade      # the page warns: update systemd/udev first on 22.04, or packages can be removed
sudo apt install -y ros-humble-ros-base ros-dev-tools
echo 'source /opt/ros/humble/setup.bash' >> ~/.bashrc && source ~/.bashrc
sudo rosdep init && rosdep update
```
`ros-humble-desktop` (with RViz) is optional on the Jetson: RViz can run on another machine on the same network.
Option B: replace `humble` with `jazzy` throughout.

**Gate:** `ros2 topic pub /chatter std_msgs/msg/String "{data: hi}"` in one terminal and `ros2 topic echo /chatter` in another
(`demo_nodes_cpp` comes with `ros-humble-desktop`, not `ros-base`).

### 4.2 librealsense from source, RSUSB backend (OPEN_ISSUES #3)
Why source and RSUSB: the ROS apt `librealsense2` uses the native V4L2 backend [S18], which on Jetson needs kernel patching [S16], and
on JetPack 6 the IMU depends on that kernel path [S21, S24]. The RSUSB build is what RealSense staff recommend for JetPack 6 [S24].
Use **v2.59.1** with **realsense-ros 4.59.1**: the wrapper's CMake asks for `realsense2 2.59.0` or newer [S19].
```bash
# Unplug the D455 first.
sudo apt install -y git cmake build-essential libssl-dev libusb-1.0-0-dev libudev-dev pkg-config libgtk-3-dev
git clone https://github.com/realsenseai/librealsense.git ~/librealsense
cd ~/librealsense && git checkout v2.59.1
sudo cp config/99-realsense-libusb.rules /etc/udev/rules.d/ && sudo udevadm control --reload-rules && sudo udevadm trigger
mkdir build && cd build
cmake .. -DFORCE_RSUSB_BACKEND=ON -DBUILD_WITH_CUDA=ON -DCMAKE_BUILD_TYPE=Release \
         -DBUILD_EXAMPLES=ON -DBUILD_GRAPHICAL_EXAMPLES=ON -DBUILD_TOOLS=ON
make -j$(($(nproc)-1)) && sudo make install
```
- These option names are in v2.59.1's `CMake/lrs_options.cmake`. `BUILD_WITH_CUDA` needs CUDA installed (step 2.5).
- Do **not** also install `ros-humble-librealsense2` or Intel's apt packages: two copies cause version clashes (the realsense-ros README says to choose only one install option [S19]).
- `BUILD_PYTHON_BINDINGS` is off by default. Turn it on only if a Python tool needs `pyrealsense2`.

**Gate:** plug the D455 straight into a Jetson USB 3 port (not the hub yet) and run
```bash
rs-enumerate-devices -s     # lists the D455 with its serial and firmware
rs-enumerate-devices | grep -i "usb type"   # must say 3.x, not 2.x
```

### 4.3 Workspace (repo) and realsense-ros
```bash
cd ~ && git clone https://github.com/Moeaal/merz-mapper.git
cd ~/merz-mapper/ros2_ws
vcs import src < merz.repos
git clone -b 4.59.1 https://github.com/realsenseai/realsense-ros.git src/third_party/realsense-ros
rosdep install --from-paths src --ignore-src -r -y --skip-keys "librealsense2"
```
Record every third-party commit in the logbook (`merz.repos` uses branch names, except the m-explore pin).

### 4.4 Build check, one package at a time first
```bash
cd ~/merz-mapper/ros2_ws
colcon build --packages-select rf2o_laser_odometry         # decisions #14: Humble support proved only in the cloud so far
colcon build --packages-select sllidar_ros2
colcon build --packages-up-to realsense2_camera            # slow; add --parallel-workers 2 on a 4 GB module
colcon build --packages-up-to explore_lite                 # pinned commit 926033f (decisions #19)
colcon build --symlink-install                             # everything
source install/setup.bash && echo "source ~/merz-mapper/ros2_ws/install/setup.bash" >> ~/.bashrc
colcon test && colcon test-result --verbose
```
**Extra check (do not change `merz.repos` yet):** in a scratch workspace, test whether `m-explore-ros2` **`main`** now builds on apt Humble.
Humble's geometry2 has had the `tf2_ros/*.hpp` headers since 0.25.16 (July 2025), and the current release is 0.25.24
(distro_decision §3.3) [S29]. If it builds, propose replacing the pin in decisions #19, which would bring back upstream #51.
```bash
mkdir -p ~/scratch_ws/src && cd ~/scratch_ws/src && git clone https://github.com/robo-friends/m-explore-ros2.git
cd ~/scratch_ws && colcon build --packages-select explore_lite && git -C src/m-explore-ros2 rev-parse HEAD
```

### 4.5 Python packages (only what bring-up needs)
`pip3 install --user pyserial` (for `merz_base`). Leave YOLO/TensorRT and OCR until after G1 (`HARDWARE_ARRIVAL_PLAN.md` week 7).
Notes for later, from distro_decision §3: JetPack 6 Python is 3.10; use the Jetson PyTorch wheel, not the pip default [S30];
`paddlepaddle` has aarch64 wheels on PyPI only up to **3.2.2** [S35]; the fallback is RapidOCR on ONNX Runtime.

---

## 5. udev rules (stable device names)
The repo's rules are in `ros2_ws/src/merz_bringup/udev/`. **Check each ID on the real device first**: the C920 product ID varies by
revision, and the gamepad rule is commented out **[MISSING]**.
```bash
lsusb                                                         # note the IDs of each device
udevadm info -a -n /dev/ttyUSB0 | grep -E 'idVendor|idProduct|serial' | head    # RPLIDAR adapter (CP210x, 10c4:ea60 expected)
cd ~/merz-mapper/ros2_ws/src/merz_bringup/udev
sudo cp 99-merz-*.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
ls -l /dev/rplidar /dev/c920                                  # both symlinks exist
v4l2-ctl --list-devices                                       # /dev/c920 points at the capture node
```
- `99-merz-rplidar.rules` matches any CP210x. If a second CP210x appears (for example a motor controller **[ROVER]**), add `ATTRS{serial}`.
- `99-merz-d455.rules` and librealsense's `99-realsense-libusb.rules` (step 4.2) both give user access; keep both.
- The user must be in `plugdev` and `dialout`: `sudo usermod -aG plugdev,dialout $USER`, then log out and in.

**Gate:** unplug and replug each device; the symlinks come back.

---

## 6. One sensor at a time

Rules for this section:
- **Bench first**, sensors on the desk, rover not involved. Motors stay **unpowered** throughout section 6.
- One device per step. Log the command, rate, CPU (`tegrastats`) and any warning.
- The pass rates below are what the configs in `merz_bringup/config` ask for. They are targets to check, not measured values.
- Useful on every step: `ros2 topic list`, `ros2 topic info -v <topic>` (QoS and publishers), `ros2 topic hz <topic>`,
  `ros2 topic echo --once <topic>`.

### 6.1 RPLIDAR S2
Plug the USB adapter into the **powered hub** (start-up current up to 1.5 A at 5 V [H1]).
```bash
ros2 launch merz_bringup lidar.launch.py
ros2 topic hz /scan                                   # expect about 10 Hz (S2 typical scan rate [H1])
ros2 topic echo --once /scan --field header           # frame_id must be 'laser'
ros2 topic echo --once /scan --field ranges | head    # numbers, not all inf
```
**Pass:** about 10 Hz for 5 minutes with no timeout errors; the room outline looks right in RViz (fixed frame `laser`), and a hand at
1 m appears at 1 m. Known reports: `SL_RESULT_OPERATION_TIMEOUT` and scans that "just stop" (sllidar_ros2 issues #6, #47, both open):
check the cable, the adapter's power and the baud rate (1000000 for S2 [N8]). If `sllidar_ros2` will not run, the apt fallback is
`ros-humble-rplidar-ros` with `rplidar_s2_launch.py` [S28].

### 6.2 D455 depth and colour
Start on a **direct Jetson USB 3 port** with a short, good USB-C cable (BUILD_GUIDE §1). Move it to the hub only after this passes.
```bash
ros2 launch merz_bringup d455.launch.py
ros2 topic list | grep camera                                       # 4.54+ gives /camera/camera/... (d455.yaml note)
ros2 topic hz /camera/camera/color/image_raw                        # expect about 15 Hz (d455.yaml: 640x480x15)
ros2 topic hz /camera/camera/aligned_depth_to_color/image_raw       # expect about 15 Hz (848x480x15, aligned)
ros2 topic hz /camera/camera/depth/color/points                     # point cloud is on (pointcloud.enable: true)
```
**Pass:** rates hold for 10 minutes; `tegrastats` CPU is not saturated. A flat wall at 2.00 m (laser meter) reads about 2.0 m in the
depth image centre. Write down the reading; the full 1-4 m wall test is in BUILD_GUIDE §5. If CPU is short, set `pointcloud.enable: false`
for manual mapping (it is in `d455.yaml` as a comment).

### 6.3 D455 IMU: GO / NO-GO gate (the biggest O1 risk)
The D455 IMU often fails on JetPack 6 (distro_decision §3.1) [S20-S24], and the no-encoder plan relies on it for heading (decisions #2, #10).
**Time-box: one working day.**
```bash
rs-enumerate-devices | grep -i -E "gyro|accel|motion"      # the Motion Module must be listed
rs-motion                                                  # if built: values change when the camera is tilted
ros2 launch merz_bringup d455.launch.py
ros2 topic hz /camera/camera/imu                           # united topic; expect a steady rate near gyro_fps (200 in d455.yaml)
ros2 topic echo /camera/camera/imu --field angular_velocity   # rotate the camera about its vertical axis by hand
```
**Pass:** a steady IMU rate for 10 minutes with no `control_transfer returned error` lines and no "No HID info provided, IMU is disabled".
Turning the camera changes the angular velocity on the expected axis; still, it reads near zero.
**If it fails, in this order (distro_decision §5):**
1. Check the firmware: `rs-fw-update -l` lists the camera, its serial and firmware. Log that version first, so it can be put back.
   Download the signed 5.13.0.50 image from RealSense's firmware page, close every other RealSense program, then run
   `rs-fw-update -s <serial> -f <image>.bin` (usage from librealsense `tools/fw-update/readme.md`). D455 only, and **never lower than
   5.13.0.50** [S20, S23].
2. Rebuild librealsense once (clean `build/`) and retest. Then stop.
3. Go on with section 6.4 onwards and with mapping **without the IMU** (scan odometry only), log the deviation, and raise the IMU fallback
   with Dr Wright (distro_decision §6 question 5).
**Known wrapper quirk:** `unite_imu_method: 2` acts like 1 (copy) in realsense-ros 4.59.1 [S32]. It still publishes `/camera/camera/imu`; just
note it in the logbook. Check the timestamps are increasing: `ros2 topic echo /camera/camera/imu --field header.stamp`.

### 6.4 Logitech C920
Plug into the **hub** (USB 2 device).
```bash
v4l2-ctl -d /dev/c920 --list-formats-ext | grep -A3 MJPG    # 1920x1080 must be offered in MJPG
ros2 launch merz_bringup c920.launch.py
ros2 topic hz /sign_cam/image_raw                          # expect about 10 Hz (c920.yaml framerate: 10.0)
ros2 topic hz /sign_cam/image_raw/compressed               # what the bags record, if image_transport plugins are installed
```
**Pass:** about 10 Hz at 1920x1080 for 5 minutes; a printed door-sign mock-up is readable on screen at about 1.5 m. If
`/sign_cam/image_raw/compressed` is missing, install `ros-humble-image-transport-plugins`.

### 6.5 Gamepad [MISSING]
Not yet bought (OPEN_ISSUES #10). When it arrives: fill in the IDs in `99-merz-gamepad.rules`, then
```bash
ros2 run joy joy_enumerate_devices        # lists the pad
ros2 launch merz_bringup teleop.launch.py
ros2 topic echo /joy                      # find the deadman button and axes; fix teleop.yaml
ros2 topic echo /cmd_vel_mux              # moves only while the deadman (enable_button) is held
```
**Pass:** no `/cmd_vel_mux` message moves the robot unless the deadman is held. Then test **link loss** (docs/REVIEW.md: untested
wireless-gamepad link loss is a High finding): switch the pad off while holding the stick; output must go to zero.

### 6.6 URDF and TF [ROVER]
```bash
ros2 launch merz_description description.launch.py rviz:=true include_d455_internal_frames:=true
ros2 run tf2_tools view_frames            # one tree: base_link -> laser, camera_link, sign_camera ...
```
**[ROVER]** `sensor_poses.yaml` holds placeholders until the mast and mounts exist **[MISSING]**. On the bench, a check that the tree is
connected is enough. Real poses come in BUILD_GUIDE §2 once the rover CAD and mounts are known.

### 6.7 Everything together: 20 minutes
Move the D455 to the powered hub only if 6.2 passed on the direct port. Then:
```bash
ros2 launch merz_bringup sensors.launch.py
ros2 topic hz /scan & ros2 topic hz /camera/camera/imu & ros2 topic hz /sign_cam/image_raw &
tegrastats --interval 5000 --logfile ~/merz_data/tegrastats_$(date +%F_%H%M).log
```
**Pass:** each rate stays within about 10% of its single-sensor rate for 20 minutes; no USB reset lines in `sudo dmesg -w`; record the
peak temperature from `tegrastats`. If the D455 drops out only on the hub, put it back on a direct port and note it (section 8).

---

## 7. Recording rosbags
Use the repo launch file: it records MCAP to `~/merz_data/bags/<time>_<name>` (`record_bag.launch.py`), so `~/merz_data` must be on the
NVMe.
```bash
mkdir -p ~/merz_data/bags
ros2 launch merz_bringup record_bag.launch.py name:=bench_sensors              # core topics only
ros2 launch merz_bringup record_bag.launch.py name:=bench_images images:=true  # adds colour, aligned depth, C920 compressed (large)
ros2 bag info ~/merz_data/bags/<time>_bench_sensors                           # check message counts and duration
ros2 bag play ~/merz_data/bags/<time>_bench_sensors                           # replay; then ros2 topic hz /scan
```
- **Gate before G1:** a 2-minute bag replays and `/scan` replays at about 10 Hz.
- Check the write rate keeps up: `ros2 bag info` message counts divided by duration should match the live rates in section 6.
- Check free space before each run (`df -h ~/merz_data`). Images are "tens of GB per hour" (`record_bag.launch.py` docstring).
- **Copy bags off the Jetson before 19 Dec** (OPEN_ISSUES #5): mapping work can continue from them during the leave.

---

## 8. Powered USB hub notes
- **Power source [ROVER]:** on the rover the hub must run from the rover battery through a DC-DC converter, not mains
  (HARDWARE_REGISTER notes). Check the hub's input voltage and current on its label before choosing the converter.
- **What goes where (BUILD_GUIDE §1):** D455 on a direct Jetson USB 3 port; RPLIDAR adapter, C920 and gamepad dongle on the hub.
- **Budget:** the RPLIDAR S2 can draw up to 1.5 A at start-up and about 0.5 A running [H1]. Start the LIDAR first, or alone, if the hub
  cuts out at power-on, and measure the real current with a USB meter. The D455 and C920 currents are not in the register yet: measure them
  (O1 power budget).
- **Check it is USB 3:** `lsusb -t` shows the speed of each port (5000M or more = USB 3). The D455 must show as USB 3.x in
  `rs-enumerate-devices`.
- **Carrier hubs [SKU]:** one D455 report on an Orin Nano carrier traced USB 3 failures to the carrier's own VIA VL822 hub firmware, and
  an external hub worked around it (community report, not confirmed by RealSense) [S23b]. Check with `lsusb -d 2109:0822 -v` if the D455
  will not enumerate on USB 3.

---

## 9. Known Jetson + RealSense pitfalls
| Symptom | Likely cause | What to try | Source |
| --- | --- | --- | --- |
| IMU missing: "No HID info provided, IMU is disabled"; `rs-motion` finds no IMU | JetPack 6 removed `hiddraw`, used by the IMU | RSUSB build, then firmware 5.13.0.50 | [S21, S24] (anecdotal) |
| IMU shows "No Frames Received" / prints once then stops | Firmware on JetPack 6 | Downgrade D455 to 5.13.0.50 (never lower) | [S20] (anecdotal; fixed for that user) |
| `control_transfer returned error ... Resource temporarily unavailable` once the IMU is on | IMU access on JetPack 6 | As above; if unfixed, plan B in 6.3 | [S22] (anecdotal) |
| Device enumerates but `pipeline.start()` says "No device connected" | Backend / firmware | RSUSB build; firmware 5.13.0.50 | [S23] (anecdotal) |
| D455 only on USB 2, or not seen on USB 3 | Cable, port, or a carrier hub's firmware | Short certified cable, direct port; check `lsusb -d 2109:0822 -v`; try an external hub | [S23b] (anecdotal) |
| No per-frame metadata on JetPack 6 over USB 3 | Native backend without patched modules | Tracked by RealSense (RSDSO-21463) in the patch script; the RSUSB build avoids the kernel path | [S17] |
| The patch script says "Unsupported JetPack revision" | v2.59.1 knows L4T 36.5 but not 36.5.2 (JetPack 6.2.3), and 39.2 but not 39.2.1 (JetPack 7.2.1) | Use the RSUSB build instead (no L4T check) | [S17] |
| Version clash, or a camera that worked yesterday no longer opens | Two librealsense installs (source + apt) | Remove one; choose only one install option | [S19] |
| `unite_imu_method: 2` gives copied accel values | Wrapper bug in 4.x up to 4.59.1 | Note in the logbook; little effect on a gyro-yaw EKF | [S32] (verified in source) |
| Jazzy arm64 `ros-jazzy-realsense2-camera` returns 404 (option B only) | Missing arm64 debs (seen June 2025) | Build realsense-ros from source (this runbook does anyway) | [S25] (anecdotal) |
| D455 drops out under load | USB bandwidth or power | Lower streams in `d455.yaml`; turn off the point cloud; direct port | BUILD_GUIDE §7 |
| Topic names differ (`/camera/...` vs `/camera/camera/...`) | Wrapper version | `ros2 topic list`; the repo expects `/camera/camera/...` | `d455.yaml` comment |
| Builds killed with no error | Out of memory on a 4 GB module | Swap file; `--parallel-workers 2`; `make -j2` | step 3.7 |

---

## 10. Steps that depend on the unknown rover [ROVER]
| Step | What is unknown | What to do now |
| --- | --- | --- |
| 3.2, 8 Power from the battery | Battery voltage and capacity, spare outputs, the DC-DC converters | Bench supplies only; fill HARDWARE_REGISTER when the rover is inspected |
| 5 udev | Whether the motor controller is a second CP210x or other USB serial device | Add `ATTRS{serial}` to the LIDAR rule if it clashes |
| 6.6 URDF / TF | Sensor poses, `base_link` position, footprint | Bench check only; measure on the rover (BUILD_GUIDE §2) |
| Mounting (all sensors) | Mast, mounts and where the LIDAR can see 360° clear **[MISSING]** | Rover CAD from the supervisor; 3D-print mounts |
| Motors (`merz_base`) | Controller interface, encoders, stop path (decisions #19 R1, OPEN_ISSUES #19) | Not part of sensor bring-up. Wheels off the ground, physical power cut within reach, before any motion |
| First manual map | Whether the rover can be driven by G1 | `mapping.launch.py base:=false` lets the sensor rig be **pushed by hand** to make the first map (see `o1_checklist.md`) |
