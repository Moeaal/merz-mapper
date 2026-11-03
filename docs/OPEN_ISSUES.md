# Open issues

Severity: **HIGH** (blocks an objective/deadline), **MED** (risk to a target),
**LOW** (tidy-up). Status: OPEN / ASK SUPERVISOR / DONE. Move DONE items to the
bottom; don't delete them.

| # | Issue | Severity | Proposed solution | Status |
| --- | --- | --- | --- | --- |
| 1 | Rover is university-built; spec unknown until received (controller interface, encoders, battery, mounting, existing computer) | HIGH (blocks O1) | Arriving with parts (expected early Nov); CAD from supervisor; inspect on arrival and fill HARDWARE_REGISTER | OPEN |
| 2 | JetPack / ROS 2 distro undecided | HIGH (blocks O1) | JetPack 6.2 (Ubuntu 22.04) + ROS 2 Humble: mature, apt-installable on Jetson; Humble support ends May 2027, which covers the project. JetPack 7.2 + Jazzy is newer but less proven on Orin Nano | ASK SUPERVISOR |
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
| 15 | No-encoder plan: an IMU gives good yaw rate but NOT distance travelled (integrating accelerometer drifts within seconds). Linear motion must come from LIDAR scan matching. Proposal O1 and project text still say "wheel odometry" | HIGH (D1 wording, O1, O8) | Confirm with supervisor; use scan-matching odometry (e.g. rf2o, verify Humble support) + IMU in EKF; update proposal before 13 Nov; O8 comparison becomes IMU+scan fusion vs scan-only | Draft 2026-11-03 uses scan-matching + IMU; awaiting supervisor reply |
| 14 | Ground truth for 0.15 m wall target: need a floor plan of Merz Court | MED (O2, O8) | Ask estates/supervisor for a CAD/PDF plan; else laser-meter survey of chosen corridors | ASK SUPERVISOR |
