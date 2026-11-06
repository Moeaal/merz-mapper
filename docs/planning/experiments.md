# Experiments

Procedure for each objective. **Status: PLANNED. No experiment has been run.** Rules marked PROPOSED need agreeing with
Dr Wright before the run: a pass rule chosen after seeing the results is not a valid test.

## For every run, record in the logbook
Date and time, lighting, people present, door states, software commit, parameter files, rosbag name, power mode, battery
state. Run three times or more, or take 20 or more samples, where practical. Report mean, SD, max, RMSE and 95% CI, and
show the per-sample distribution, not only the mean.

Ground truth must be 3-5 times more accurate than the target. Laser meter: note the accuracy on its datasheet when it
arrives (HARDWARE_REGISTER has none yet).

## O1: sensors and first manual map (G1, by 18 Dec 2026)
- **Measure:** each sensor at its expected rate; TF tree complete; one map of a corridor by manual driving.
- **Procedure:** `docs/runbooks/build-guide.md` sections 4-6, recording a bag.
- **Pass:** all sensors publishing at the same time; a map saved; the bag replays. Aim for ~11 Dec (OPEN_ISSUES #5).
- **Threats:** battery and USB power under full load; IMU frame wrong (check by rotating by hand).

## O2: map coverage and wall accuracy
- **Hypothesis:** autonomous exploration covers >=90% of the corridor area, with walls within 0.15 m.
- **Ground truth:** Merz Court floor plan (OPEN_ISSUES #14) or laser-meter survey of the chosen corridors; the corridor
  polygon, agreed **before** the runs.
- **Procedure:** three exploration runs from one entrance. Align the plan to each map by a rigid transform from named
  corners, and record the transform. Then run:
  ```
  python tools/eval/map_coverage.py --map run.yaml --polygon corridor.csv --plot coverage.png
  python tools/eval/wall_error.py --map run.yaml --walls walls.csv --match-radius 0.5 --plot wall_error.png
  ```
- **Pass (PROPOSED):** coverage >=90% on every run; mean wall error <=0.15 m on every run. Report the share within 0.15 m
  and the share excluded. `--match-radius` is fixed before the runs.
- **Threats:** glass (mark glass sections, and report with and without them); aligning the plan to the map can hide error;
  furniture; a floor plan that does not match the building as built.

## O3: sign reading
- **Hypothesis:** at least 85% of the signs in the test area are read correctly.
- **Ground truth:** a manual list of every sign in the area, written on foot **before** the run: `signs.csv`, column `text`.
- **Procedure:** three runs. `python tools/eval/ocr_rate.py --truth signs.csv --database merz.sqlite`
- **Pass:** >=85% exact matches after normalisation. False reads are reported alongside, and each is examined.
- **Threats:** robot speed and blur (the robot does not stop for signs: see the `sharp_enough` CSV column); lighting; the
  training set overlapping the test signs, which would flatter results. Hold back one corridor from training.

## O4: landmark position error
- **Hypothesis:** mean landmark error is <=0.5 m.
- **Ground truth:** laser-meter distances from two known wall corners for each landmark, at least 20 landmarks. Estimated
  uncertainty is recorded with them. `truth.csv`: class,text,x,y, in the map frame.
- **Procedure:** three runs. `python tools/eval/landmark_error.py --truth truth.csv --database merz.sqlite --plot err.png`
- **Pass:** mean <=0.5 m. Unmatched landmarks are reported, and not treated as zero error.
- **Error budget to discuss:** robot pose, depth (<2% at 4 m [H2]), bbox centre, extrinsics, time offset.
- **Threats:** the truth's own frame alignment; `--gate` must be fixed before the run.

## O5: access zones
- **Hypothesis:** the zones computed from the map match a manual survey.
- **Ground truth:** walk from each entrance with doors as found, and fill in `survey.csv` (entrance,room,reachable) on the
  same day, recording the door states. Do this **without looking at the robot's results**.
- **Procedure:** one run per entrance. `python tools/eval/access_zone_compare.py --survey survey.csv --database merz.sqlite`
- **Pass:** all pairs match. Each mismatch is explained. "Only in map" is the serious one: it sends a visitor to a locked door.
- **Threats:** access-controlled doors that happen to be open; doors changing between entrance runs; glass.

## O6: query time, and O7: route correctness
- **Hypothesis:** every query is under 1 s; at least 9 of 10 routes are correct.
- **Ground truth:** ten entrance-room pairs chosen in advance; the expected junction sequence walked by hand, without
  looking at the website's answer. `routes.csv`: entrance,room,expected.
- **Procedure:** start the website on the demo machine, then:
  `python tools/eval/route_timing.py --url http://<host>:8000 --routes routes.csv --repeats 20 --plot times.png`
- **Pass:** max query time <1 s, over the same network as the demo; >=9/10 routes correct.
- **Also:** ask someone new to the building to follow two routes by phone, and note where the photos mislead (qualitative).
- **Threats:** server-side timing leaves out mobile network and photo loading, so report those separately if used.

## O8: fused against single-sensor comparison
- **Hypothesis:** fusion lowers landmark error compared with one sensor or one observation.
- **Comparison (PROPOSED - confirm with Dr Wright):** since there are no encoders (decisions #10, OPEN_ISSUES #15), two
  comparisons are possible:
  1. **Landmarks:** one observation against the mean of all observations, from the same run:
     `python tools/eval/fusion_compare.py --truth truth.csv --database merz.sqlite --plot fusion.png`
  2. **Pose:** replay one bag through the EKF, once with IMU + scan odometry and once with scan odometry only, and compare
     wall error and landmark error. Bags make this repeatable without new runs. Change `imu0` in `ekf.yaml` for the second.
- **Pass (PROPOSED):** the mean paired improvement is above zero and its 95% CI excludes zero. If not, report that honestly:
  no significant benefit is still a valid result.
- **Threats:** comparison 1 only shows the benefit of averaging, which does nothing for systematic errors like extrinsics.

## Results
Log results in `docs/logbook/`. Only then may an objective be called TESTED.
