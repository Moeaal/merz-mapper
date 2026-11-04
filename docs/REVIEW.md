# Safety and bug review of `ros2_ws` (2026-11-04)

**Scope:** every package in `ros2_ws/src`, with most attention on the motion path:
gamepad -> `joy_node` -> `teleop_twist_joy` -> `twist_mux` <- Nav2 (`controller_server` -> `velocity_smoother`) ->
`/cmd_vel_mux` -> `merz_base` -> motor backend. Also checked: QoS on every topic pair, TF ownership, threading.

**Verification level reached:** L0-L1 only. Static reading of the code and configs, and the pure-Python unit tests
run on Linux (Python 3.13, no ROS installed). No `colcon build`, no ROS graph, no hardware. Nothing below shows that
the real rover stops; the safety checklist in `ros2_ws/src/merz_bringup/README.md` still applies in full.

**Severity:** **High** = could make the rover move when it should not, or fail to stop. **Medium** = wrong behaviour
or a weaker safety margin, with another layer still in place. **Low** = robustness or tidiness.

## Fixed in this branch (with regression tests)

| # | Severity | Where | Problem | Fix | Test |
| --- | --- | --- | --- | --- | --- |
| F1 | High | `merz_base/base_controller.py` `BaseLimits` | Limits were not checked. A negative speed limit (a sign slip in `base.yaml`) inverts the clamp: `max(0.5, min(-0.5, v))` is 0.5 for every `v`, so a **zero command drove the rover forward at 0.5 m/s**. `full_speed_m_s: 0` crashed the update loop (division by zero); an infinite `command_timeout_s` disabled the timeout; `update_rate_hz: 0` crashed start-up | `BaseLimits.__post_init__` refuses any limit that is not a finite number above zero; `check_update_rate` does the same for the timer rate. The node now refuses to start instead | `test_limits_that_are_not_finite_and_positive_are_refused` (28 cases), `test_a_negative_speed_limit_cannot_reach_the_controller`, `test_bad_update_rates_are_refused` |
| F2 | Medium | `merz_base/kinematics.py`, `base_controller.py` | Each wheel was clamped to full scale on its own. When one wheel saturated, the left/right ratio changed, so the rover drove a **tighter or wider arc than Nav2 or the operator asked for**, which can clip a wall Nav2 had planned around. Reachable as soon as the measured `full_speed_m_s` is below `max_linear + max_angular * track / 2` | `normalised_pair` scales both wheels by the same factor, which keeps the arc and only slows the rover | `test_saturated_wheels_are_scaled_together_so_the_turn_radius_is_kept`, `test_controller_output_keeps_the_commanded_arc_when_a_wheel_saturates` |
| F3 | Medium (O4) | `merz_semantic_map/landmark_node.py` | `lookup_transform(..., timeout=0.2 s)` runs inside a callback of a single-threaded node, but `TransformListener` was created without `spin_thread=True`, so its TF subscriptions share that same blocked executor. No new transform can arrive during the wait: any image newer than the last TF message blocks the node for 0.2 s and is then rejected. Expected effect: most landmark observations dropped, and detections queued behind the stalls | `TransformListener(..., spin_thread=True)` | `test_tf_listener_threads.py`: static check that any file in the package that waits for TF gives its listener its own thread (fails on the old code) |

`spin_thread` is a keyword of `tf2_ros.TransformListener` in rclpy from Humble onwards, according to its source; this
has not yet been checked against the installed package. First check on the Pi/Jetson: `colcon build`, then
`pytest ros2_ws/src/merz_semantic_map/test/test_ros_landmark_node.py`.

## Open findings (not changed: they need a decision, a measurement or hardware)

| # | Severity | Where | Finding | Proposed action |
| --- | --- | --- | --- | --- |
| R1 | **High** | Motor path, hardware | **No stop path independent of `base_node` and the Jetson.** `command_timeout_s` is enforced inside `base_node`. If that process dies (uncaught exception, `SIGKILL`, out-of-memory kill), or the Jetson hangs or browns out, nothing sends a stop: a serial controller keeps its last command unless it has its own watchdog, and with the GPIO backend the PWM duty set through the Jetson's PWM hardware is expected to persist after the process dies (to be confirmed on the bench). The README checklist item "killing the base node ... stops the motors within `command_timeout_s`" can only pass if the motor controller has its own command timeout | Hardware decision for the student (decisions.md #18, PROPOSED): a motor controller with a serial command watchdog, or a heartbeat-fed enable line (charge pump / relay) for an H-bridge, plus the physical power cut already on the checklist. Then test it with the wheels off the ground by `kill -9` on `base_node` |
| R2 | **High** | `config/teleop.yaml`, gamepad | **Wireless gamepad link loss while the deadman is held.** `joy_node` republishes the last state at `autorepeat_rate` (20 Hz). Some wireless receivers keep reporting the last button and axis state when the pad goes out of range or its battery dies, so the teleop input would stay fresh with the deadman "held" and a stick deflected. No timeout downstream would catch this | Before buying the pad, or on arrival: hold the deadman with the stick forward, switch the pad off / walk out of range, wheels off the ground, and watch `/cmd_vel_teleop`. If it keeps publishing, use a wired pad or one whose receiver reports a disconnect |
| R3 | Medium | `merz_base/base_node.py` | An exception from the backend in the timer callback (`serial.SerialTimeoutException`, `OSError` when USB drops) ends `rclpy.spin`. The `finally` block then tries to stop the motors, but over the same failed link, and the node exits without respawn. Combined with R1 this leaves the last command on the motors | Decide the intended behaviour: either catch backend errors in `_on_timer`, log, retry `stop()` every cycle and keep running, or exit loudly and rely on R1's watchdog. Not changed, as both are defensible and depend on the controller |
| R4 | Medium | `config/nav2.yaml` `velocity_smoother.velocity_timeout: 1.0` | The smoother keeps republishing its last output until no command has arrived for `velocity_timeout`. If `controller_server` dies, `/cmd_vel` stays fresh for up to 1.0 s, so twist_mux and the base timeout (0.5 s each) do not trip for that time; at 0.5 m/s that is up to ~0.5 m extra travel plus the 0.5 s base timeout | Set `velocity_timeout` to 0.5 s or less (`controller_frequency` is 20 Hz, so this leaves 10 cycles of margin). Confirm against the installed Nav2 smoother source |
| R5 | Medium | `config/twist_mux.yaml` | **No latched software e-stop.** Autonomy is halted only while the operator keeps holding the deadman; on release, Nav2 regains control within the 0.5 s mux timeout and the rover moves again. twist_mux `locks` are not used | Add a twist_mux lock (priority 255) on an e-stop topic latched by a gamepad button, and cancel the Nav2 goal when it engages. The physical power cut remains the real stop |
| R6 | Medium | `config/nav2.yaml` | **No collision monitor.** Nothing between the controller and the motors checks for obstacles at short range at sensor rate; DWB only sees the local costmap, updated at 5 Hz. The teleop path bypasses all obstacle checks by design | Add `nav2_collision_monitor` (available on Humble) with a stop polygon from `/scan`, between `velocity_smoother` and twist_mux. Its parameters need the measured footprint |
| R7 | Medium | Distro (decisions #6) | On **Jazzy**, `nav2_bringup/navigation_launch.py` also starts `collision_monitor` and `docking_server` under the lifecycle manager and moves the velocity chain to `cmd_vel_smoothed` -> collision monitor -> `cmd_vel`. `nav2.yaml` configures neither, so bring-up would be expected to fail at configure. Later distros move to `TwistStamped`, which `merz_base` and twist_mux settings do not handle | Only if the distro becomes Jazzy or later: add both node configs (or a custom launch) and check stamped/unstamped `cmd_vel` end to end |
| R8 | Low | `merz_base/backends.py` `_set_side` | The GPIO backend sets the duty cycle to 0 before every update, even without a change of direction, so each 20 Hz cycle has a brief drop in drive (torque ripple, noise) | Cut the PWM only when the direction changes. Keep the existing test of the direction-change case |
| R9 | Low | `merz_base/base_controller.py` | Freshness is taken from arrival time, as `Twist` has no stamp. A command delayed in DDS (for example teleop from a laptop over Wi-Fi) counts as fresh on arrival | Acceptable while every motion source runs on the Jetson. Revisit if remote teleop is used |
| R10 | Low | `merz_exploration/mission_node.py` | `wait_for_service(timeout_sec=5.0)` blocks a worker thread inside a coroutine; and the `_ended` check-then-set in `_on_timer` is not atomic with a reentrant group on a `MultiThreadedExecutor` (needs a >1 s stall to matter) | Put the timer in its own `MutuallyExclusiveCallbackGroup`, or guard `_ended` with a `threading.Lock` |
| R11 | Low | `merz_exploration/junction_photo_node.py` | Uses the latest TF (`Time()`) rather than the scan stamp, so the junction position lags by the TF latency. Junctions are not in O4, so the error (a few cm at 0.5 m/s) is acceptable | Use the scan stamp with a short timeout, and `spin_thread=True` as in F3, if junction positions matter later |
| R12 | Low | `config/teleop.yaml` | Axis, button and scale values are guesses until the pad arrives; a wrong `enable_button` or axis sign would be found only by driving | Already on the README checklist; check with `ros2 topic echo /joy` with the wheels off the ground before the first drive |

## Checked and found consistent (no action)

- **cmd_vel limits:** DWB `max_vel_x` 0.5, smoother 0.5, base clamp 0.5 m/s, teleop scale 0.3 m/s, no turbo; no
  reversing in DWB or the smoother; Spin/BackUp recoveries removed. All values are still placeholders until measured.
- **Timeouts:** twist_mux inputs 0.5 s, base `command_timeout_s` 0.5 s with an immediate (un-ramped) stop, `stop()`
  resent every cycle, `time.monotonic()` used so ROS clock jumps cannot affect it. NaN/inf commands ignored.
- **Deadman:** `require_enable_button: true`, turbo disabled; teleop priority 100 above navigation 10.
- **QoS pairs:** every pair checked is compatible. Best-effort subscribers (`qos_profile_sensor_data`) on reliable
  camera/scan publishers; `/map` transient-local from slam_toolbox to the static layer and explore_lite; reliable
  `cmd_vel`, `odom_rf2o`/`odom_scan`, detections and sign readings on both sides.
- **TF ownership:** URDF owns `base_link` -> `laser`, `camera_link`, `sign_camera`(+optical); the RealSense driver owns
  the D455 internal frames (URDF copies off by default); EKF owns `odom` -> `base_link`; slam_toolbox owns `map` ->
  `odom`; rf2o has `publish_tf: false`. `base_link` sits on the floor, so the costmap height limits are heights above
  the floor.

## Next checks on hardware (in order, wheels off the ground)

1. `colcon build`; run the ROS tests in `merz_base` and `merz_semantic_map`.
2. R2 gamepad link-loss test; R12 axis mapping.
3. Kill `base_node` with `kill -9` while driving: if the wheels keep turning, R1 is confirmed and the rover must not
   run autonomously until a watchdog exists.
4. Stop `controller_server` mid-goal and time how long the wheels keep turning (R4).
