# JetPack, Ubuntu and ROS 2 distro for the Jetson Orin Nano (OPEN_ISSUES #2)

**Status: PROPOSED, not agreed.** Written 2026-11-05 for the student and Dr Wright. Nothing in this file has been run on the
Merz Mapper hardware: every support claim below comes from upstream sources, release indexes or third-party reports, each
cited with its date. Status words follow `docs/MERZ_MAPPER_STATE.md`.

**How the evidence was gathered.** This session's network blocked docs.ros.org, docs.nvidia.com, developer.nvidia.com,
forums.developer.nvidia.com, index.ros.org, packages.ros.org and docs.ultralytics.com. So:
- ROS facts were read **directly from source** on GitHub: the `ros/rosdistro` release index, REP 2000, the ROS 2 docs source,
  the buildfarm configuration, and each driver's own repository at a named commit or tag.
- NVIDIA facts (JetPack versions, CUDA/TensorRT versions, install method) come **from web-search summaries of NVIDIA pages
  and forum posts**, which could not be opened directly. These rows are marked *(search)*. Check them against the NVIDIA page
  before quoting them in a submission.
- GitHub issues are user reports. Treat them as **anecdotal** (brain skill, section 5), even when a maintainer replied.

Sources are tagged [S1]-[S40] and listed at the end. All were accessed on 2026-11-05.

---

## 1. Short answer

**PROPOSED: JetPack 6.2.x (newest point release: 6.2.3 / Jetson Linux 36.5.2) + Ubuntu 22.04 + ROS 2 Humble.**
This keeps decisions #6, but adds three conditions that the evidence makes necessary:

1. **A D455 IMU go/no-go test on bring-up day 1** (runbook step 6.3). On JetPack 6 the D455 IMU often fails to stream.
   The known fix (an RSUSB source build, then firmware 5.13.0.50) works "in most cases", but not all [S20-S24].
   The IMU carries the heading in the no-encoder plan (decisions #2, #10), so this is the largest single risk to O1.
2. **A fallback that is decided now**, not on 17 December: if the IMU still fails after one working day, use the order in
   section 5.
3. **Accept that Humble ends in May 2027** [S1], the same month as D3/D4. That is enough for this project, but it leaves no
   margin. The project must not depend on post-May-2027 updates.

**Main reason:** the code is already written for Humble. Every Nav2, SLAM Toolbox, robot_localization and rf2o key has been
checked against Humble source (RESEARCH_INDEX [C1-C7]), and a cloud Humble `colcon build` + `colcon test` has passed
(BUILD_PROGRESS). With six working weeks to G1 (18 Dec 2026) and a zero buffer before leave (OPEN_ISSUES #5), moving
everything to new versions carries more risk than any gain JetPack 7.2 + Jazzy offers. Jazzy's one clear practical advantage,
a host-free NVMe install, is handled for JetPack 6 in runbook section 2.

**Fallback (option B): JetPack 7.2.1 + Ubuntu 24.04 + ROS 2 Jazzy.** It is a sound platform: NVIDIA itself supports it on
Orin (Isaac ROS 4.6) [S14], and it gets support until May 2029. Choose it if the supervisor wants the longer support window,
or if the department has no Ubuntu x86 PC and the host-free JetPack 6 NVMe route fails. Do **not** choose it to fix the
D455 IMU: no source found shows whether the IMU works better on JetPack 7.2 (section 3.2).

---

## 2. Options considered

| # | JetPack (L4T) | Ubuntu | ROS 2 | Verdict |
| --- | --- | --- | --- | --- |
| A | 6.2.3 (36.5.2), Aug 2026 [S8]; or 6.2.2 (36.5) [S6] | 22.04 | Humble | **PROPOSED** |
| B | 7.2.1 (39.2.1), 11 Aug 2026 [S10]; or 7.2 (39.2), Jun 2026 [S9] | 24.04 | Jazzy | Fallback |
| C | 6.2.x | 22.04 | Jazzy (source build or Docker) | Rejected: REP 2000 lists no arm64 support for Jazzy on Jammy (amd64 is Tier 3 only) [S2]. Everything would be a source build |
| D | 7.2.x | 24.04 | Humble in Docker | Rejected: REP 2000 does not list Ubuntu Noble for Humble [S2]. It adds a container layer between the drivers, the GPU and USB |
| E | 7.2.x | 24.04 | Kilted | Rejected: end of life **December 2026** [S1], before G2 |
| F | - | 26.04 | Lyrical | Rejected: Lyrical targets Ubuntu 26.04 "resolute" [S3]. No JetPack release uses 26.04 |

### 2.1 Platform facts
| Item | A: JetPack 6.2.x + Humble | B: JetPack 7.2.x + Jazzy |
| --- | --- | --- |
| Kernel / Ubuntu | 5.15 / 22.04 [S6] *(search)* | 6.8 / 24.04 [S9] *(search)* |
| CUDA / cuDNN / TensorRT | 12.6 / 9.3 / 10.3 [S7] *(search)* | 13.2.1 / 9.20.0 / 10.16.2 [S9] *(search)* |
| System Python | 3.10 (the Jetson wheels are cp310) [S30] | 3.12 (the Jetson wheels are cp312) [S30] |
| Orin Nano install | microSD image, or SDK Manager from an **x86_64 Ubuntu 20.04/22.04 host** [S12, S13] *(search)* | **Jetson ISO on a USB stick (16 GB+) installs straight to NVMe; no host PC.** No microSD image any more [S11] *(search)* |
| Firmware precondition | SD image route handles the QSPI update [S12] | Needs JetPack 6-generation UEFI/QSPI first. An old kit goes through the JetPack 6 update path first [S11] |
| Power modes (8 GB) | 15 W, 25 W, MAXN SUPER (from 6.2) [S15] *(search)* | ISO uses the Super configuration by default [S10] *(search)* |
| ROS 2 Tier 1 on arm64 | Humble on Jammy arm64: Tier 1 [S2] | Jazzy on Noble arm64: Tier 1 [S2] |
| NVIDIA's own ROS stack on Orin | Isaac ROS 3.2 + JetPack 6.1/6.2 + Humble [S14] *(search)* | Isaac ROS 4.6 (18 Aug 2026) + JetPack 7.2 + Jazzy [S14] *(search)* |
| Maturity on Orin Nano | JetPack 6 production release since May 2024 (JetsonHacks, https://jetsonhacks.com/2024/05/06/jetpack-6-production-release/, *search*); most Jetson+RealSense reports are on it [S20-S25] | Orin support first arrived in 7.2 (June 2026), so about five months of field use [S9] |

### 2.2 End-of-life dates
| Item | Date | Source |
| --- | --- | --- |
| ROS 2 Humble | May 2027 | [S1], REP 2000 heading "May 2022 - May 2027" [S2] |
| ROS 2 Jazzy | May 2029 | [S1], [S2] |
| ROS 2 Kilted | December 2026 | [S1] |
| ROS 2 Lyrical | May 2031 (released 22 May 2026) | [S1] |
| Ubuntu 22.04 standard security maintenance | May 2027 (ESM to May 2032) | [S5] |
| Ubuntu 24.04 standard security maintenance | May 2029 (ESM to May 2034) | [S5] |
| JetPack 5 | EoL Q3 2026 (NVIDIA notice) | [S13] *(search)* |
| JetPack 6 / 7 | **No published end-of-life date found.** JetPack 6 still received 6.2.3 in Aug 2026 [S8] | [S13] *(search)* |

Project dates for comparison: G1 18 Dec 2026, O2-O8 to 7 May 2027, D3/D4 May 2027 (`MERZ_MAPPER_STATE.md`).

---

## 3. Driver and package support

Key: **apt** = released binary in the rosdistro index for that distro [S3]; **src** = not released, build from source;
version numbers are the released package versions in `ros/rosdistro` master on 2026-11-05 [S3].

| Need | Package | A: Humble (Jammy arm64) | B: Jazzy (Noble arm64) | Notes |
| --- | --- | --- | --- | --- |
| RPLIDAR S2 | `sllidar_ros2` (Slamtec) | src. Last commit `3430009`, 2024-06-17. README lists rolling, humble, galactic, foxy [S26] | src. Not listed in README; one report of a Jazzy build on a Pi 5 with warnings only, runtime not reported [S27] | Not in rosdistro for any distro. Fallback: `rplidar_ros` **apt** 2.1.4 (Humble) / 2.1.0 (Jazzy), which has `rplidar_s2_launch.py` [S28] |
| D455 depth + colour | `realsense2_camera` 4.59.1 + `librealsense2` 2.59.1 (both 2026-10-11) [S3, S17] | apt or src. README: Humble on 22.04 [S19] | apt or src. README: Jazzy on 24.04 [S19]. Jazzy arm64 wrapper debs returned 404 in June 2025; the user built from source [S25] | The ROS apt `librealsense2` is built with no RSUSB flag, so it uses the native V4L2 backend [S18]. On Jetson that needs the kernel patch script, so **use a source RSUSB build on either option** [S16] |
| D455 IMU | same | **Known problem** [S20-S24]: see 3.1 | **UNKNOWN**: no reports found either way. See 3.2 | Highest risk in this table |
| Jetson kernel patch route (optional) | `patch-realsense-ubuntu-L4T.sh` v2.59.1 | Accepts L4T 36.3, 36.4, 36.4.3, 36.4.4, 36.4.7, **36.5**. Does **not** list 36.5.2 (JetPack 6.2.3) [S17] | Accepts 38.2-38.2.2, 38.4, **39.2**. Does **not** list 39.2.1 (JetPack 7.2.1) [S17] | Only matters for the native backend. The RSUSB build does not check the L4T version |
| C920 | `usb_cam` | apt 0.8.1 [S3] | apt 0.8.1 [S3] | The repo uses `usb_cam` (`c920.launch.py`) |
| C920 (alt.) | `v4l2_camera` | apt 0.6.2 [S3] | apt 0.7.3 [S3] | |
| SLAM | `slam_toolbox` | apt 2.6.10 [S3] | apt 2.8.5 [S3] | Repo `slam.yaml` checked against 2.6.10 (RESEARCH_INDEX [C5]) |
| Navigation | `navigation2` | apt 1.1.20 [S3] | apt 1.3.14 [S3] | Repo `nav2.yaml` checked against Humble (RESEARCH_INDEX [C1]). Jazzy would need the check again. `enable_stamped_cmd_vel` exists from Jazzy, default `false` [S36] |
| EKF | `robot_localization` | apt 3.5.5 [S3] | apt 3.8.4 [S3] | Repo `ekf.yaml` checked against `humble-devel` ([C6]) |
| Frontier exploration | `m-explore-ros2` (`explore_lite`) | src. Repo pins `926033f`. **New finding:** see 3.3 | src. Upstream CI builds humble, jazzy and kilted [S31] | Alternative `roadmap_explorer`: apt 1.0.0 on Humble only; Jazzy entry is source-only [S3] |
| Scan-matching odometry | `rf2o_laser_odometry` (`ros2` branch) | src. Last commit `b38c68e`, 2023-04-28 [S33]. **Builds on Humble** (cloud check, BUILD_PROGRESS) | src. Jazzy runtime report: "Waiting for laser_scans..." with `ros2 run`; works when started by its launch file (Mar 2026, anecdotal) [S34] | Not in rosdistro for any distro. Repo launches it from `merz_bringup` |
| Teleop | `joy` (joystick_drivers), `teleop_twist_joy`, `twist_mux` | apt 3.3.0 / 2.4.8 / 4.3.0 [S3] | apt 3.3.0 / 2.6.5 / 4.5.0 [S3] | |
| Bags | `rosbag2` + `rosbag2_storage_mcap` | apt 0.15.17 [S3] | apt 0.26.11 [S3] | |
| Calibration | `camera_calibration` (image_pipeline) | apt 3.0.9 [S3] | apt 5.0.13 [S3] | |
| TensorRT YOLO | Ultralytics `format="engine"` | TensorRT 10.3. Ultralytics benchmarked Orin Nano Super on JetPack 6.1; cp310 torch 2.10.0 wheel + cuDSS fix [S30] | TensorRT 10.16.2. Ultralytics gives a native JetPack 7.2 path: torch from the `cu130` index, onnxruntime-gpu 1.24.0 cp312 [S30] | Engines must be built on the target (Ultralytics; RESEARCH_INDEX [N10]). "Keep the supported TensorRT 10.x runtime on JetPack 6/7" [S30] |
| PaddleOCR (GPU) | `paddlepaddle-gpu` | **No official aarch64 GPU wheel for JetPack 6** [S37, S38]; community build only [S39] | No official aarch64 GPU wheel either (PyPI `paddlepaddle-gpu` has x86_64/Windows only) [S35] | GPU OCR is not needed: OCR runs on a few crops per minute (perception skill) |
| PaddleOCR (CPU) | `paddlepaddle` + `paddleocr` 3.7.0 | `paddlepaddle` **3.2.2** (2025-11-19) has `manylinux2014_aarch64` wheels for cp39-cp313 on PyPI. 3.3.x (latest 3.3.1) has **none** [S35] | as A (cp312) [S35] | Pin `paddlepaddle==3.2.2` on the Jetson, or use the fallback below |
| OCR fallback | RapidOCR (PaddleOCR models in ONNX Runtime) | `onnxruntime` 1.31.1 has aarch64 wheels [S35] | same | Repo already supports `ocr_engine: rapid` via `rapidocr_onnxruntime`, whose last release is 1.4.4 (2025-01-17); the maintained package is now `rapidocr` 3.10.0 (2026-10-08) [S35] |

### 3.1 The D455 IMU on JetPack 6 (option A)
- A RealSense maintainer, in several 2025-2026 threads: "JP6 removed a component called hiddraw that the IMU-equipped
  RealSense camera models depended on." Advice: a libuvc/RSUSB source build, then firmware 5.13.0.50 if needed [S21, S22, S24].
- Orin Nano, JetPack 6.2 (R36.4.4), librealsense 2.55.1, RSUSB: IMU showed "No Frames Received". **Fixed by downgrading the
  camera firmware to 5.13.0.50** (July 2025) [S20].
- Orin NX, JetPack 6.2, librealsense 2.57.7, RSUSB: IMU not detected ("No HID info provided, IMU is disabled"). **No
  confirmed fix** (Apr-Oct 2026) [S21].
- Orin Nano, JetPack 6.2.1, wrapper 4.55.1: `control_transfer returned error` once the IMU was on. The user moved to an
  external IMU (Dec 2025) [S22].
- **Do not downgrade a D455 below 5.13.0.50**, or "it will stop working" [S20, S23]. Newer models (D455f etc.) must not be
  downgraded at all [S23]. Check the label: the register says D455.
- Separate wrapper bug, verified in the 4.59.1 source: `unite_imu_method: 2` (linear interpolation) is ignored on the
  motion-sensor callback path, which calls `imu_callback_sync(frame)` with its default `COPY` (`rs_node_setup.cpp` line 150;
  default in `base_realsense_node.h` line 324) [S19, S32]. The repo's `d455.yaml` sets 2. Effect: accelerometer samples are
  copied, not interpolated. The EKF mainly uses gyro yaw rate, so the effect should be small, but the O8 write-up should
  state it. Not a reason to change distro (it affects every distro).

### 3.2 The D455 IMU on JetPack 7.2 (option B)
No issue, success report or maintainer statement was found for a RealSense IMU on JetPack 7.x on any Orin (GitHub issue
search, 2026-11-05). librealsense supports L4T 39.2 in its patch script from 2026-06-24 [S17], and its Jetson guide says the
native backend was verified on Thor with JetPack 7.0 "(beta level)" [S16]. Whether JetPack 7's kernel 6.8 restores what the
IMU needs is **UNKNOWN**. Do not count it as a fix.

### 3.3 Frontier exploration: the Humble pin may no longer be needed
The repo pins `m-explore-ros2` to `926033f` because `main` (from `96d1888`, 2026-01-13) includes `tf2_ros/buffer.hpp`, which
failed on the cloud RoboStack Humble build (BUILD_PROGRESS). However, Humble's `geometry2` gained the `.hpp` headers in commit
`0b54e91` (2025-07-24, "Change tf2_ros C to C++ headers (backport #807)"), first in tag 0.25.16 (2025-07-25). The current Humble
release is **0.25.24** [S3, S29]. Upstream `m-explore-ros2` CI also builds Humble [S31]. So `main` (now `326cf8a`, 2026-06-02,
which includes upstream #51) **probably builds on apt Humble on the Jetson**; the RoboStack build most likely had an older
geometry2. This is an inference: test it on the Jetson (runbook step 4.4) before changing decisions #19.

---

## 4. Comparison against what the project needs

| Criterion (why it matters) | A: 6.2.x + Humble | B: 7.2.1 + Jazzy |
| --- | --- | --- |
| G1 by 18 Dec with zero buffer (OPEN_ISSUES #5) | Matches all existing code, configs and the build check | Every config must be checked again (Nav2 1.1 -> 1.3, SLAM Toolbox 2.6 -> 2.8, robot_localization 3.5 -> 3.8); the build check must be redone |
| D455 IMU (decisions #2, #10, O1, O8) | Known failure mode with a known fix that works in most cases [S20-S24] | Unknown; no evidence |
| Support until project end (May 2027) | Just enough: Humble and Ubuntu 22.04 both end May 2027 [S1, S5] | Comfortable: May 2029 |
| Flashing to NVMe with the student's kit (Windows laptop + Pi 5; no Linux x86 PC, decisions #11) | Host-free route exists but NVMe needs an extra step (runbook 2.2); SDK Manager needs an x86_64 Ubuntu host [S12, S13] | **Simplest**: ISO on USB installs straight to NVMe [S11] |
| Community evidence on Orin Nano + RealSense | Most | Little (five months) |
| TensorRT YOLO (O3) | Documented, Orin Nano benchmarked [S30] | Documented native path [S30] |
| PaddleOCR (O3) | CPU via `paddlepaddle==3.2.2`; RapidOCR fallback | Same |
| Matches the Raspberry Pi 5 practice set-up | Distro still to confirm (`MERZ_MAPPER_STATE.md`): if the Pi runs Ubuntu 22.04 + Humble, A matches it | If the Pi runs 24.04 + Jazzy, B matches it |

---

## 5. Fallback order if the D455 IMU fails on JetPack 6 (decide now)

Time-box: one working day after the RSUSB build is running (runbook 6.3). Then, in order:
1. **Firmware 5.13.0.50** (not lower) with the RSUSB build. This is the documented fix [S20, S24].
2. **Rebuild and retest once, then stop debugging.** Record the exact versions and errors in the logbook.
3. **For G1 only:** make the first manual map with scan-matching odometry alone (rf2o into the EKF, IMU off). SLAM Toolbox
   can map from scans; O1 asks for sensors and a first manual map, not for the fused estimate. Record it as a deviation.
4. **Ask Dr Wright for a separate small IMU** (USB or I2C) to fuse instead of the D455 IMU. That reverses decisions #2, so it
   needs approval. No part is proposed here, as no part has been researched yet.
5. Only then consider moving to option B, on a **second** storage device so that the working option A install is kept.

---

## 6. Questions to confirm with Dr Wright
1. **Distro:** is JetPack 6.2.x + Ubuntu 22.04 + Humble acceptable, given that Humble's end of life (May 2027) is the same month
   as D3/D4? Or does the department prefer JetPack 7.2.1 + Jazzy for its longer support?
2. **Which Jetson exactly:** an NVIDIA Orin Nano **Developer Kit** (or Super Dev Kit), or a module on a third-party carrier?
   4 GB or 8 GB? This changes the flashing steps, the power modes [S15] and the USB hub on the carrier (one RealSense report
   blames a carrier's VIA VL822 USB hub for USB 3 failures [S23b]).
3. **An x86_64 Ubuntu 20.04/22.04 PC for SDK Manager:** does the department have one the student may use? If not, the
   host-free routes in runbook section 2 apply.
4. **What firmware is the kit on now?** (JetPack 5-era kits need the JetPack 6 update path first [S11, S12].)
5. **IMU fallback:** if the D455 IMU will not stream on the Jetson, may the project add a small separate IMU (reverses
   decisions #2), or should it go ahead with scan-only odometry and change the O8 comparison?
6. **The Raspberry Pi 5 distro:** which Ubuntu and ROS 2 are on it? Practice should match the Jetson's distro.
7. **Does the rover already carry a computer or an OS image** that fixes the distro (decisions #6 notes this dependency)?

Confirm with Dr Wright: JetPack 6.2.x + Humble (PROPOSED), the Jetson SKU/carrier, and the IMU fallback in section 5.

---

## 7. Sources (all accessed 2026-11-05)
*(search)* = known only from a web-search summary; the page itself was blocked here.

| Tag | Source | What it supports |
| --- | --- | --- |
| S1 | ROS 2 docs source, `ros2/ros2_documentation` `rolling` branch, `source/Releases.rst`, https://github.com/ros2/ros2_documentation/blob/rolling/source/Releases.rst | Release and EOL dates: Lyrical May 2031, Kilted Dec 2026, Jazzy May 2029, Humble May 2027 |
| S2 | REP 2000, https://github.com/ros-infrastructure/rep/blob/master/rep-2000.rst | Humble: Jammy arm64 Tier 1; Jazzy: Noble arm64 Tier 1; Jazzy on Jammy: amd64 Tier 3 only |
| S3 | `ros/rosdistro` master: `humble/`, `jazzy/`, `kilted/`, `lyrical/distribution.yaml`, https://github.com/ros/rosdistro | Released package versions in section 3; Lyrical platform Ubuntu "resolute"; geometry2 Humble 0.25.24 |
| S4 | ROS buildfarm config, `release-ubuntu-arm64-build.yaml` for humble and jazzy, https://github.com/ros2/ros_buildfarm_config | RealSense packages are not on the arm64 exclusion list (they are excluded only on RHEL) |
| S5 | Ubuntu release cycle, https://ubuntu.com/about/release-cycle | 22.04 standard support to May 2027; 24.04 to May 2029 |
| S6 | NVIDIA forum "JetPack 6.2.2/Jetson Linux 36.5 is now live", https://forums.developer.nvidia.com/t/jetpack-6-2-2-jetson-linux-36-5-is-now-live/359623 ; JetsonHacks, https://jetsonhacks.com/2026/02/06/jetpack-6-2-2-for-jetson-orin/ *(search)* | JetPack 6.2.2 = L4T 36.5, kernel 5.15, Ubuntu 22.04 |
| S7 | NVIDIA JetPack 6.2 / 6.2.2 pages, https://developer.nvidia.com/embedded/jetpack-sdk-62 , https://developer.nvidia.com/embedded/jetpack-sdk-622 *(search)* | CUDA 12.6, TensorRT 10.3, cuDNN 9.3 |
| S8 | NVIDIA forum "JetPack 6.2.3/Jetson Linux 36.5.2 is now live", https://forums.developer.nvidia.com/t/jetpack-6-2-3-jetson-linux-36-5-2-is-now-live/379873 ; https://developer.nvidia.com/embedded/jetson-linux-r3652 *(search)* | JetPack 6.2.3 = L4T 36.5.2 (Aug 2026), same components as 6.2.2, supports Orin Nano Dev Kit |
| S9 | NVIDIA forum "JetPack 7.2 ... Jetson Linux 39.2", https://forums.developer.nvidia.com/t/jetpack-7-2-jetson-software-goes-agentic-with-jetson-linux-39-2/372060 ; archive https://developer.nvidia.com/embedded/jetpack/downloads/archive-7.2 ; OE4T notes https://github.com/OE4T/meta-tegra/blob/master/docs/release-notes/JetPack-7.2-L4T-R39.2.0-Notes.md *(search)* | JetPack 7.2 adds Orin incl. Orin Nano; Ubuntu 24.04, kernel 6.8; CUDA 13.2.1, cuDNN 9.20.0, TensorRT 10.16.2; Orin Nano boot-overlay known issue |
| S10 | NVIDIA archive 7.2.1, https://developer.nvidia.com/embedded/jetpack/downloads/archive-7.2.1 ; JetsonHacks https://jetsonhacks.com/2026/08/12/jetpack-7-2-1-released/ *(search)* | JetPack 7.2.1 = L4T 39.2.1, 11 Aug 2026; ISO uses Super config by default; no SD image |
| S11 | Orin Nano Dev Kit Quick Start Guide, https://docs.nvidia.com/jetson/orin-nano-devkit/user-guide/latest/quick_start.html *(search)* | ISO to USB (16 GB+), install to NVMe; JetPack 6-generation firmware required first |
| S12 | RidgeRun "Upgrade Orin Nano without a Linux host", https://developer.ridgerun.com/wiki/index.php/JetPack_6_Migration_and_Developer_Guide/Migrating_from_JetPack_5_to_JetPack_6/Upgrade_Orin_Nano_without_a_Linux_host ; NVIDIA forum "Can I create a bootable Jetpack SSD with Balena Etcher?", https://forums.developer.nvidia.com/t/can-i-create-a-bootable-jetpack-ssd-with-balena-etcher/371188 *(search, anecdotal)* | Host-free firmware update via SD image; SD image written to NVMe reported to boot (6.2.1) |
| S13 | SDK Manager system requirements, https://docs.nvidia.com/sdk-manager/2.1.0/system-requirements/index.html ; NVIDIA forum "JetPack 5 upcoming End-of-Life notice", https://forums.developer.nvidia.com/t/jetpack-5-upcoming-end-of-life-notice/357716 *(search)* | SDK Manager host: x86_64 Ubuntu; JetPack 5 EoL Q3 2026; no JetPack 6 EoL found |
| S14 | NVIDIA forum "Roadmap for Isaac ROS Jazzy on Orin Devices", https://forums.developer.nvidia.com/t/roadmap-for-isaac-ros-jazzy-on-orin-devices/375982 *(search)* | Isaac ROS 4.6 (18 Aug 2026) + JetPack 7.2 + Jazzy on Orin; Isaac ROS 3.2 + JetPack 6.1/6.2 + Humble |
| S15 | JetPack 6.2 release notes, https://docs.nvidia.com/jetson/archives/jetpack-archived/jetpack-62/release-notes/index.html *(search)* | Orin Nano 8 GB: 15 W, 25 W, MAXN SUPER; 4 GB: 10 W, 25 W, MAXN SUPER |
| S16 | librealsense `doc/installation_jetson.md` (last changed 2026-06-24), https://github.com/realsenseai/librealsense/blob/master/doc/installation_jetson.md | RSUSB via `scripts/libuvc_installation.sh`; native backend needs the L4T patch script; Thor JP 7.0 "beta level" |
| S17 | librealsense v2.59.1 (2026-10-11), `scripts/patch-realsense-ubuntu-L4T.sh`; commit `e5cf313e3` (2026-06-24) "Support L4T R39.2 (JetPack 7.2)" | L4T versions accepted by the patch script |
| S18 | librealsense v2.59.1 `CMake/unix_config.cmake`; ROS release repo `ros2-gbp/librealsense2-release`, tag `debian/ros-humble-librealsense2_2.59.1-1_jammy`, `debian/rules` | Native V4L2 backend unless `FORCE_RSUSB_BACKEND`; the ROS Debian build passes no RSUSB flag |
| S19 | realsense-ros 4.59.1 (2026-10-11) README, https://github.com/realsenseai/realsense-ros | Humble on 22.04, Jazzy/Kilted on 24.04; Jetson users follow the librealsense Jetson guide; `/camera/camera/imu` topic |
| S20 | librealsense issue #14111 (Jul 2025), https://github.com/realsenseai/librealsense/issues/14111 (anecdotal) | Orin Nano JP 6.2 D455 IMU fixed by firmware 5.13.0.50; never below 5.13.0.50 |
| S21 | librealsense issue #14911 (Apr-Oct 2026), https://github.com/realsenseai/librealsense/issues/14911 (anecdotal) | JP6 removed hiddraw; IMU not detected; no confirmed fix |
| S22 | realsense-ros issue #3465 (Dec 2025), https://github.com/realsenseai/realsense-ros/issues/3465 (anecdotal) | Orin Nano JP 6.2.1 IMU `control_transfer` errors; user moved to an external IMU |
| S23 | librealsense issue #14548 (Dec 2025-Jan 2026), https://github.com/realsenseai/librealsense/issues/14548 (anecdotal) | Orin Nano JP 6.0 D455 pipeline failure; newer models must not be downgraded |
| S23b | librealsense issue #14929 (Apr-Oct 2026), https://github.com/realsenseai/librealsense/issues/14929 (anecdotal) | D455 not detected on USB 3.2 on an Orin Nano carrier; VL822 hub firmware blamed; external hub as workaround |
| S24 | librealsense issue #14392 (Oct 2025), https://github.com/realsenseai/librealsense/issues/14392 (anecdotal) | libuvc build "successful in most cases" on JP6; then firmware 5.13.0.50 |
| S25 | realsense-ros issue #3366 (Jun 2025), https://github.com/realsenseai/realsense-ros/issues/3366 (anecdotal) | Jazzy arm64 wrapper debs missing then; built from source |
| S26 | `Slamtec/sllidar_ros2` `main` at `3430009` (2024-06-17), README and `launch/sllidar_s2_launch.py`, https://github.com/Slamtec/sllidar_ros2 | Distros named in README; S2 launch file |
| S27 | sllidar_ros2 issue #54 (Oct 2025), https://github.com/Slamtec/sllidar_ros2/issues/54 (anecdotal) | Jazzy build on Pi 5 finishes with warnings |
| S28 | `Slamtec/rplidar_ros` `ros2` branch (`24cc9b6`, 2025-04-27), https://github.com/Slamtec/rplidar_ros | Has `launch/rplidar_s2_launch.py` |
| S29 | `ros2/geometry2` `humble` branch, commit `0b54e91` (2025-07-24), tag 0.25.16 (2025-07-25), https://github.com/ros2/geometry2/tree/humble | `tf2_ros/*.hpp` headers exist in Humble from 0.25.16 |
| S30 | Ultralytics NVIDIA Jetson guide, `docs/en/guides/nvidia-jetson.md` on `main`, https://github.com/ultralytics/ultralytics/blob/main/docs/en/guides/nvidia-jetson.md | JP6 cp310 / JP7.2 cp312 wheels; Orin Nano Super tested on JP 6.1; TensorRT 10.x; engines device-specific |
| S31 | `robo-friends/m-explore-ros2` `main` at `326cf8a` (2026-06-02), `.github/workflows/build_test.yaml`, https://github.com/robo-friends/m-explore-ros2 | CI: humble/jammy, jazzy/noble, kilted/noble |
| S32 | realsense-ros issue #3578 (Oct 2026), https://github.com/realsenseai/realsense-ros/issues/3578, checked against the 4.59.1 source | `unite_imu_method: 2` falls back to COPY on the motion callback |
| S33 | `MAPIRlab/rf2o_laser_odometry` `ros2` at `b38c68e` (2023-04-28), https://github.com/MAPIRlab/rf2o_laser_odometry | Last upstream change |
| S34 | rf2o issue #43 (Mar 2026), https://github.com/MAPIRlab/rf2o_laser_odometry/issues/43 (anecdotal) | Jazzy: "Waiting for laser_scans" with `ros2 run`; works via launch file |
| S35 | PyPI JSON API for `paddlepaddle`, `paddlepaddle-gpu`, `paddleocr`, `rapidocr`, `rapidocr-onnxruntime`, `onnxruntime`, `onnxruntime-gpu`, https://pypi.org/ | Wheel platforms and latest versions in section 3 |
| S36 | Nav2 docs source, `ros-navigation/docs.nav2.org`, migration guides `iron/Iron.md`, `jazzy/Jazzy.md`, and `setup_odom.md`, https://github.com/ros-navigation/docs.nav2.org | `enable_stamped_cmd_vel` added with default `false`; default `true` after Jazzy |
| S37 | PaddleOCR issue #17327 (Dec 2025-May 2026), https://github.com/PaddlePaddle/PaddleOCR/issues/17327 (anecdotal) | No official JetPack 6 GPU wheel |
| S38 | Paddle issues #75117 and #74126 (2025), https://github.com/PaddlePaddle/Paddle/issues/75117 (anecdotal) | Requests for JetPack 6 GPU wheels; no official link |
| S39 | Community build, https://github.com/SidaWang12/paddle3.0-jetson-jetpack6-build (unverified) | Paddle Inference GPU wheel built for JetPack 6.2 |
| S40 | Merz repo: `docs/BUILD_PROGRESS.md`, RESEARCH_INDEX [C1-C7], `ros2_ws/merz.repos`, `merz_bringup/config/d455.yaml` | What the project has already checked against Humble |
