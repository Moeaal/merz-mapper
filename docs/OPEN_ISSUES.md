# Open issues

Severity: **HIGH** (blocks an objective/deadline), **MED** (risk to a target),
**LOW** (tidy-up). Status: OPEN / ASK SUPERVISOR / DONE. Move DONE items to the
bottom; don't delete them.

| # | Issue | Severity | Proposed solution | Status |
| --- | --- | --- | --- | --- |
| 1 | Rover is university-built; spec unknown until received (controller interface, encoders, battery, mounting, existing computer) | HIGH (blocks O1) | Arriving with parts (expected early Nov); CAD from supervisor; inspect on arrival and fill HARDWARE_REGISTER | OPEN |
| 2 | JetPack / ROS 2 distro undecided | HIGH (blocks O1) | JetPack 6.2 (Ubuntu 22.04) + ROS 2 Humble: mature, apt-installable on Jetson; Humble support ends May 2027, which covers the project. JetPack 7.2 + Jazzy is newer but less proven on Orin Nano | DONE: Humble + JetPack 6.x (decisions #21) |
| 3 | RealSense on JetPack 6 often needs a source build (RSUSB/libuvc backend) and gets USB power/detection errors | MED | Budget a full day; build librealsense with RSUSB; use powered hub; check firmware version; log exact versions | OPEN |
| 4 | Glass walls/doors are invisible or noisy to the 2D LIDAR | MED (O2 wall accuracy, safety) | Keep-out zones (already in spec) + depth camera into Nav2 costmap; mark glass in evaluation | OPEN |
| 5 | Zero buffer: G1 is 18 Dec, leave starts 19 Dec | HIGH | Aim for first manual map by ~11 Dec; record rosbags so mapping work can continue offline after return | OPEN |
| 6 | Proposal s.6 uses first person ("I won't be available") - brief requires third person | MED (D1) | Rewrite: "The student is unavailable from..." | FIXED in draft 2026-11-03 |
| 7 | Proposal says D455 range 0.4-6 m; Intel states 0.6-6 m ideal range | LOW (D1) | Change to 0.6-6 m | FIXED in draft 2026-11-03 |
| 8 | Proposal says hardware "runs on the rover's existing computer" but the parts list orders a Jetson | LOW (D1) | Make wording match whatever the rover actually has | FIXED in draft 2026-11-03 |
| 9 | Proposal spec adds "checkpoint QR codes at junctions" - more website scope than the entrance-QR design | LOW | Mark as stretch goal or remove | FIXED in draft 2026-11-03 |
| 10 | Parts list is missing gamepad, mast, mounts, checkerboard, QR posters | MED | Add to list and order | OPEN |
| 11 | Poster date: slides say "Friday 23 Feb 2027" but it is a Tuesday | LOW | Confirm with module leader | ASK SUPERVISOR |
| 12 | Slides say report submission "May 2026" (clearly 2027) | LOW | Confirm date | OPEN |
| 13 | Frontier exploration package not chosen | MED (O2) | Test explore_lite first in sim; fall back to frontier_exploration_ros2 | OPEN |
| 15 | No-encoder plan: an IMU gives good yaw rate but NOT distance travelled (integrating accelerometer drifts within seconds). Linear motion must come from LIDAR scan matching. Proposal O1 and project text still say "wheel odometry" | HIGH (D1 wording, O1, O8) | Confirm with supervisor; use scan-matching odometry (e.g. rf2o, verify Humble support) + IMU in EKF; update proposal before 13 Nov; O8 comparison becomes IMU+scan fusion vs scan-only | DONE: no encoders, scan matching + D455 IMU (decisions #22); check the proposal says no "wheel odometry" |
| 14 | Ground truth for 0.15 m wall target: need a floor plan of Merz Court | MED (O2, O8) | Ask estates/supervisor for a CAD/PDF plan; else laser-meter survey of chosen corridors | ASK SUPERVISOR |
| 16 | Code written without ROS: nothing has been through `colcon build`, and Nav2, driver and message_filters usage is unproven | HIGH (O1) | `colcon build` + `colcon test` on the Pi first, then the bring-up in BUILD_GUIDE; expect corrections. 2026-11-04: cloud Humble build + test passed (BUILD_PROGRESS); Pi/Jetson build and run still to do | OPEN |
| 17 | Long plain corridors can defeat scan matching (nothing for rf2o or SLAM to lock on to), with no encoders as a backup | HIGH (O1, O2) | Test early on a real corridor bag. No encoders (decisions #22), so fallbacks are: slower speed, fusing rf2o vyaw, keeping doors open for features, and as a last resort D455 visual odometry as a second velocity source in the EKF (PROPOSED) | OPEN |
| 18 | The robot does not stop for signs, so motion blur may reject most crops at speed | MED (O3) | Log the `sharp_enough` rate from a real run; slow down or add stops if low | OPEN |
| 19 | A crashed process or Jetson sends no stop, and a GPIO PWM output may hold its last value | HIGH (safety) | Physical power cut within reach; test on blocks; prefer a controller with its own watchdog | OPEN |
| 20 | The robot cannot detect stairs or drops: the LIDAR is level and the D455 is not configured for floor edges | HIGH (safety) | Test only on floors with no drops, or keep-out zones around them; never unattended | OPEN |
| 21 | O2 wall pass rule and O8 primary comparison are PROPOSED in EXPERIMENTS, and must be fixed before the runs | MED (O2, O8) | Agree both at the next meeting | ASK SUPERVISOR |
