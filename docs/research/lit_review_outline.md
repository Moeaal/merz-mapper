# Literature review outline (EEE3094 technical report)

**Status:** PROPOSED structure, 2026-11-05. Sources are the `LB-x.y` entries in `docs/research/literature_base.md`;
check every UNVERIFIED field there before citing. Write the final text in the third person with IEEE numbered
references.

## Word budget
The report is 6000 words. A literature review of about **1100–1300 words** (roughly 20%) leaves room for method,
results and discussion, which carry most of the marks for a robot project. The budget per subsection is given
below. Aim for 25–35 cited sources in total; not every LB entry needs to appear.

## Proposed structure

### 2.1 Introduction to the review (≈80 words)
- Scope: what a robot needs to map a building floor autonomously and turn it into something a visitor can use.
- Order of the review follows the system pipeline: map → explore → perceive → place landmarks → serve visitors →
  evaluate.

### 2.2 2D LIDAR SLAM (≈200 words) — O1, O2
- Graph formulation [LB-1.2] against particle filters [LB-1.1]; survey context [LB-1.8].
- Cartographer [LB-1.4] and SLAM Toolbox [LB-1.5], with Karto/SPA as SLAM Toolbox's origin [LB-1.3].
- What comparisons show [LB-1.6], [LB-1.7], and that real-robot, peer-reviewed SLAM Toolbox comparisons are scarce
  (LB gap note; LB-6.8 is the exception).
- Close on the justification: SLAM Toolbox is the ROS 2 default with Nav2 [LB-2.9], supports lifelong mapping, and
  is maintained.

### 2.3 Odometry without wheel encoders and sensor fusion (≈180 words) — O1, O8
- Why odometry matters to SLAM; an IMU gives heading rate but not distance [LB-6.1].
- Scan-matching odometry: range flow (RF2O) [LB-6.3], PLICP [LB-6.4], correlative matching [LB-6.5]; LIDAR-only SLAM
  precedent [LB-1.9].
- Corridor degeneracy as the known failure case [LB-6.6] (links to OPEN_ISSUES #17).
- EKF fusion in ROS [LB-6.2], [LB-6.9]; evidence that fusion gains depend on environment and SLAM backend
  [LB-6.8], [LB-6.7]. Sets up O8 as a genuine question, not a foregone conclusion.

### 2.4 Autonomous exploration (≈150 words) — O2
- Frontiers [LB-2.1]; comparisons of strategies [LB-2.2], [LB-2.3]; survey [LB-2.7].
- Alternatives: sampling and information gain [LB-2.4], RRT-based frontier detection [LB-2.5].
- Interaction with graph SLAM loop closures [LB-2.6]; recent cost-function improvements [LB-2.8].
- Justify `explore_lite`: simple, works on a 2D grid with Nav2, adequate for corridors.

### 2.5 Semantic mapping and sign reading (≈250 words) — O3, O4, O5
- Semantic mapping surveys [LB-3.1], [LB-3.2]; place and room labelling from range data [LB-3.3], [LB-3.4];
  object-level maps [LB-3.5].
- **Closest prior work:** sign reading for semantic maps [LB-3.6] and placard localisation [LB-3.7]; LIDAR + YOLO
  semantic maps [LB-3.8]. State what each did and did not do (see the gap below).
- OCR: survey [LB-4.1]; CRNN [LB-4.2] and DB detection [LB-4.3] as the parts of PP-OCR [LB-4.4], [LB-4.5];
  Tesseract as the document-oriented alternative [LB-4.7]; fair evaluation of recognisers [LB-4.6].
- Same YOLO + PaddleOCR + fuzzy-match pipeline used for room signs on phones [LB-4.8].

### 2.6 Detection and landmark localisation on an embedded GPU (≈170 words) — O3, O4, O8
- YOLO [LB-5.1], [LB-5.2]; current versions [LB-5.3], [LB-5.4].
- Jetson benchmarks and TensorRT speed-ups [LB-5.5], [LB-5.6], [LB-5.7].
- Placing detections in the map: depth + pose with per-object filtering [LB-7.1]; fused against single-sensor object
  mapping [LB-7.2]; the stronger joint-optimisation alternative [LB-7.3].
- Error sources: depth error [LB-7.4] and calibration [LB-7.5].

### 2.7 Indoor wayfinding for visitors (≈150 words) — O5, O6, O7
- Surveys of indoor positioning and human navigation [LB-8.1], [LB-8.2], [LB-8.3]: most need installed radio
  infrastructure or a site survey.
- Marker and QR approaches [LB-8.4], [LB-8.7], with user evidence [LB-8.8]; AR systems that start from a QR code but
  need a hand-made 3D model [LB-8.9].
- Photos and landmarks as directions [LB-8.5], [LB-8.6].

### 2.8 Evaluation methods (≈100 words) — O2, O4, O8
- Map accuracy against ground truth [LB-1.7], [LB-9.1]; without ground truth [LB-9.4]; topology-based comparison
  [LB-9.5].
- Trajectory error definitions and alignment [LB-9.2], [LB-9.3].
- Experimental practice and uncertainty [LB-9.6], [LB-9.7]: fix pass rules before runs, repeat runs, state
  uncertainty.

### 2.9 Research gap and how this project addresses it (≈120 words)
See below. End the section by mapping each part of the gap to an objective.

## Research gap

**Wording for the report (draft, third person):**

> Earlier robots have read door signs to label their maps [LB-3.6], [LB-3.7] and placed detected objects on
> LIDAR maps [LB-3.8], [LB-7.1], but in the work reviewed the output was a map for the robot rather than directions
> for a person. Conversely, visitor wayfinding systems that avoid radio infrastructure rely on QR codes or signs
> together with a building model or route data prepared by hand [LB-8.4], [LB-8.8], [LB-8.9], [LB-4.8]. No
> reviewed system uses a single autonomous mapping run to produce both a labelled map and entrance-specific
> directions, nor records which rooms are actually reachable from each entrance given the doors' states. This
> project addresses that gap with a low-cost rover that has no wheel encoders, relying on LIDAR scan matching and an
> IMU [LB-6.3], [LB-6.2], and it measures each stage against ground truth.

**Elements of the gap, and the objective that tests each:**

| Gap element | Evidence that it is open (in the sources reviewed) | Objective |
| --- | --- | --- |
| Autonomous floor mapping on a rover with no wheel encoders | Fusion gains depend on the environment, and corridors degrade scan matching [LB-6.6], [LB-6.8]; most comparisons assume wheel odometry [LB-1.6], [LB-1.7] | O1, O2, O8 |
| Door-sign reading on board an embedded GPU during exploration | [LB-3.6] predates deep OCR; [LB-3.7] is a preprint processing recorded RGB-D video; [LB-4.8] runs on a phone held by a person | O3 |
| Landmark positions with measured metric error on low-cost hardware | [LB-3.8] reports error in simulation; [LB-7.1], [LB-7.2] use different sensors or known environments | O4, O8 |
| Entrance access zones (reachability given door states) | Room segmentation [LB-3.4] and topology [LB-9.5] exist, but no reviewed source records per-entrance reachability for visitors | O5 |
| Infrastructure-free visitor directions generated from the robot's own data | Wayfinding systems need radio hardware [LB-8.3] or hand-built models [LB-8.9] | O6, O7 |

**Cautions when writing this up:**
- The claim is "not found in the sources reviewed", not "never done". Say so explicitly; one more targeted search on
  "robot-built maps for human wayfinding" before submission is recommended (RESEARCH_INDEX "To find").
- Do not overclaim novelty for parts that are standard (SLAM Toolbox, explore_lite, YOLO, PaddleOCR). The
  contribution is the integration, the encoder-free odometry choice, the access-zone output, and the evaluation.
- LB-3.7, LB-4.4, LB-4.5, LB-5.7 are preprints; label them "[Online]" preprints and do not rest a key claim on them
  alone.
