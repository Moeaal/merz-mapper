# Proposal (D1) review checklist

**Deadline:** D1, Fri 13 Nov 2026, 14:00. **Status of this file:** checklist written 2026-11-05 against the repo's memory
files; the proposal draft itself is not in the repo, so every box below still needs ticking against the final Word/PDF.

Figures in this folder (regenerate with `python docs/proposal/figures/gantt.py` and
`python docs/proposal/figures/architecture.py`; only matplotlib is needed, already in `requirements-dev.txt`):

| File | Figure | Size |
| --- | --- | --- |
| `figures/architecture.png` / `.pdf` | Fig. 1, system architecture | 170 x 118 mm (A4 portrait text width) |
| `figures/gantt.png` / `.pdf` | Fig. 2, Gantt chart | 257 x 150 mm (A4 landscape inside 20 mm margins) |

Use the PDFs in Word where possible (vector, text stays sharp); the PNGs are 300 dpi.

---

## 1. Module requirements

### Length and format
- [ ] No more than **3 pages**. Check with the module handbook whether the cover page, references, figures and any
      appendix count towards the limit.
- [ ] **Page budget for Fig. 2.** The Gantt chart is sized for a full A4 landscape page, i.e. one third of the allowance.
      If that is too much, either (a) confirm that an appendix or a rotated page is allowed, or (b) reduce it: set
      `FIG_W`/`FIG_H` in `gantt.py` to the portrait text width (170 mm) and raise the font sizes, then re-check legibility
      (text below about 6 pt will not print clearly).
- [ ] Margins, font and font size as the handbook states; page numbers present.
- [ ] Name, student number, supervisor (Dr Wright), module code EEE3094 and title on the first page.

### Style
- [ ] **Third person throughout** - search for: `I `, `I'`, ` me `, ` my `, ` we `, ` our `, ` us `. OPEN_ISSUES #6
      ("I won't be available") was fixed in the 2026-11-03 draft; re-check the final text.
- [ ] **Formal style** - no contractions (`won't`, `don't`, `it's`, `can't`), no colloquialisms, no rhetorical questions.
- [ ] **UK English** - `localisation`, `colour`, `organise`, `metre`, `programme` (but `program` for software), `analyse`.
      Watch for US spellings pasted from datasheets or ROS documentation (`robot_localization` stays as the package name,
      in code font).
- [ ] Acronyms defined at first use: LIDAR, IMU, EKF, SLAM, ROS 2, OCR, YOLO, API, QR, TF.
- [ ] Tense consistent: planned work in future tense ("will be integrated"), not "has been".

### References (IEEE)
- [ ] Numbered in square brackets **in order of first citation** ([1], [2], ...), not alphabetical.
- [ ] Reference list matches citations one to one: no uncited entries, no citation without an entry.
- [ ] Each entry in IEEE format: initials before surname, title in quotes, journal/conference in italics, vol., no., pp.,
      month and year; for web sources and datasheets, `[Online]. Available: URL` and `Accessed: day Mon. year`.
- [ ] Datasheet claims cite the datasheet: D455 ideal range **0.6-6 m** (OPEN_ISSUES #7, fixed in draft), D455 built-in
      IMU, RPLIDAR S2 range. Use the sources already in `docs/RESEARCH_INDEX.md` before searching again.
- [ ] Software packages cited where they carry the method: SLAM Toolbox, Nav2, robot_localization, YOLO, PaddleOCR,
      and rf2o if scan matching is kept.

### Figures and tables
- [ ] Every figure and table is **numbered and captioned**: IEEE puts figure captions **below** ("Fig. 1.") and table
      captions **above** ("TABLE I"). Use one convention consistently.
- [ ] Every figure and table is **referred to in the text before it appears**.
- [ ] Suggested captions:
  - *Fig. 1. System architecture. The rover (solid outline) is the main contribution; the website (dashed outline) is a
    demonstrator that reads the building database produced by the rover. The odometry source is to be confirmed.*
  - *Fig. 2. Project plan, October 2026 to May 2027, showing gateways G1-G4 (diamonds), deliverables D1-D4 (triangles)
    and the planned leave period. D3 and D4 dates are to be confirmed.*
- [ ] Figures readable in greyscale print (both use outlines, labels and hatching, not colour alone).

### SMART objectives (O1-O8)
For each objective, check it is **S**pecific, **M**easurable (a number), **A**chievable, **R**elevant to the module brief
(autonomous rover + sensor fusion), and **T**ime-bound (a date that matches Fig. 2 and Table 1). Targets below are from
`docs/EXPERIMENTS.md`; the proposal and that file must agree.

| Obj. | Date (Fig. 2) | Measurable target to check in the text |
| --- | --- | --- |
| O1 | 18 Dec 2026 (G1) | All sensors publishing together; complete TF tree; one corridor map by manual driving; bag replays |
| O2 | 5 Mar 2027 | Autonomous coverage >= 90 % of corridor area; mean wall error <= 0.15 m (pass rule PROPOSED, #21) |
| O3 | 12 Mar 2027 | >= 85 % of signs read correctly |
| O4 | 19 Mar 2027 (G2) | Mean landmark position error <= 0.5 m (>= 20 landmarks) |
| O5 | 2 Apr 2027 | Access zones match a manual survey for all entrance-room pairs |
| O6 | 9 Apr 2027 | Every query < 1 s |
| O7 | 23 Apr 2027 (G3) | >= 9 of 10 routes correct |
| O8 | 7 May 2027 (G4) | Fused vs single-sensor comparison with 95 % CI (comparison PROPOSED, #21) |

- [ ] O4 is called "fused localisation" in Fig. 2; make sure the proposal's O4 title uses the same words.
- [ ] Each objective names its measurement method in one clause (e.g. "against a laser-meter survey").

### Gantt chart, gateways and deliverables
- [ ] Fig. 2 shows **G1-G4** and **D1-D4** with a legend - done in the figure; check the text and Table 1 use the same
      dates: D1 13 Nov, G1 18 Dec, D2 23 Feb, G2 19 Mar, G3 23 Apr, G4 7 May, D3/D4 May 2027 (TBC).
- [ ] Planned leave (19 Dec 2026 - 4 Feb 2027) is labelled "Unavailable - planned leave" and is explained in one
      third-person sentence in the text, e.g. *"The student is unavailable from 19 December 2026 to 4 February 2027;
      rosbags recorded before this period allow mapping work to continue on return."*
- [ ] **Easter shading uses approximate dates** (20 Mar - 18 Apr 2027, `EASTER` in `gantt.py`). Check the university
      calendar and update the constant. It is shown as a working period, not a break.
- [ ] O2-O8 start dates are planning choices made for the figure (they overlap). Confirm they are realistic, in
      particular O2-O4 starting immediately on return (5 Feb) in parallel with poster preparation.

---

## 2. OPEN_ISSUES items that affect the proposal

| # | Issue | What to check or write in the proposal |
| --- | --- | --- |
| 15 | "Wheel odometry" wording vs no-encoder plan (HIGH) | See section 3. Must be resolved or worded neutrally before submission. |
| 1 | Rover spec unknown (HIGH) | Do not state rover dimensions, controller or encoders as fact. One risk-table row. |
| 2 | JetPack / ROS 2 distro undecided (HIGH) | Write "ROS 2 (Humble proposed)" or name the distro only if confirmed. |
| 5 | Zero buffer between G1 and leave (HIGH) | Risk table: target first map by ~11 Dec; rosbags for offline work. |
| 17 | Scan matching may fail in plain corridors (HIGH) | Risk table row; mitigation: early corridor test, encoders as fallback. |
| 19, 20 | No stop path independent of the Jetson; no stair/drop detection (HIGH, safety) | Brief safety/risk statement: physical power cut, supervised testing on floors with no drops, keep-out zones. |
| 21 | O2 pass rule and O8 comparison not agreed | Word O2 and O8 so they match whatever is agreed; if not agreed by 12 Nov, keep the targets but avoid over-specific pass rules. |
| 14 | Floor plan for 0.15 m wall target | State the ground truth as "floor plan or laser-meter survey". |
| 13 | Frontier exploration package not chosen | Name "frontier exploration (explore_lite proposed)" rather than as fixed. |
| 11 | D2 is a Tuesday but slides say Friday | Use "23 February 2027" without a weekday until confirmed. |
| 12 | Report date in slides says 2026 | Write "May 2027 (date to be confirmed)" for D3 and D4. |
| 10 | Parts list missing items | If the proposal has a parts/cost table, list gamepad, mast, mounts, checkerboard, QR posters as "to order". |
| 6-9 | First person; D455 range; "existing computer"; checkpoint QR codes | Marked FIXED in the 2026-11-03 draft. Re-check each in the final version. |

---

## 3. The "wheel odometry" wording conflict

**Conflict.** The project text and proposal O1 refer to "wheel odometry", but decisions #10 (PROPOSED) records the
supervisor's suggestion of **no wheel encoders**, with heading from the D455 IMU gyro and linear motion from LIDAR scan
matching (rf2o, decisions #14, PROPOSED). The question is still open (meeting 2026-11-02, question 11; OPEN_ISSUES #15
"awaiting supervisor reply"). An IMU alone cannot give distance travelled: integrating the accelerometer drifts within
seconds, so the proposal must not imply "IMU-only odometry" either.

**Where to search the draft:** `wheel odometry`, `encoder`, `odometry`, `dead reckoning`, `O1`, `O8`, the
architecture/method section, and the risk table. Fig. 1 already uses the neutral label
"odometry (wheel encoders or LIDAR scan matching - TBC)".

**Recommendation:** use **Option A** if the supervisor confirms no encoders before 13 Nov; **Option C** if not confirmed
in time; Option B only if encoders are confirmed.

### Option A - no encoders (matches decisions #10 and the 2026-11-03 draft)
- **O1:** *"By 18 December 2026 (G1), the RPLIDAR S2, RealSense D455 (including its built-in IMU) and sign camera will
  be integrated on the rover under ROS 2, all publishing concurrently with a complete transform tree, and a first 2D
  occupancy map of a Merz Court corridor will be produced by manual driving, using LIDAR scan-matching odometry fused
  with the IMU yaw rate."*
- **Method:** *"The rover has no wheel encoders. Linear motion will therefore be estimated by LIDAR scan matching [n],
  and heading rate by the D455's built-in IMU; the two will be fused by an extended Kalman filter (robot_localization)
  [n]. An IMU alone is not used for distance, because integrating accelerometer data drifts within seconds."*
- **O8:** *"By 7 May 2027 (G4), landmark position error and wall error obtained with IMU and scan-matching fusion will be
  compared against scan-matching odometry alone, by replaying the same recorded runs through both configurations."*

### Option B - encoders confirmed
- **O1:** as Option A, replacing the last clause with *"... using wheel-encoder odometry fused with the IMU yaw rate."*
- **Method:** *"Wheel-encoder velocities will be fused with the D455 IMU yaw rate in an extended Kalman filter [n];
  because skid-steer wheels slip when turning, only forward velocity will be taken from the encoders."*
- **O8:** *"... fusion of wheel odometry, IMU and LIDAR scan matching will be compared against each source alone."*

### Option C - not yet confirmed at submission (neutral)
- **O1:** *"... a first 2D occupancy map will be produced by manual driving, using odometry from wheel encoders or LIDAR
  scan matching (to be confirmed once the rover is inspected), fused with the IMU yaw rate."*
- **Method:** *"The odometry source depends on whether the university-built rover provides wheel encoders. If it does
  not, linear motion will be estimated by LIDAR scan matching [n]. In either case, the IMU provides heading rate and an
  extended Kalman filter fuses the sources [n]."*
- **Risk table:** *"Scan-matching odometry may degrade in long, featureless corridors (likelihood: medium; impact:
  high). Mitigation: a corridor test recording before G1; wheel encoders as a fallback, subject to supervisor
  agreement."*

After the decision: update Fig. 1 (`odom` box text in `architecture.py`) to the confirmed source and remove the dashed
"TBC" border.
