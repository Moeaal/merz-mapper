# merz_semantic_map

**Status: IMPLEMENTED - not yet built or tested on hardware.**

Works out where each detected landmark is in the map (O4) and stores it in SQLite (O6). Schema: `docs/DATABASE_SCHEMA.md`.

## How it works
For each detection from the D455:
1. **Median depth** in the central half of the box. The median ignores outliers, and the central part avoids the wall
   behind the object. Anything outside 0.6-6 m is rejected, as this is Intel's ideal range.
2. **Deproject** the box centre to a 3D point using the camera intrinsics.
3. **Transform to `map`** using TF **at the image's timestamp**. If no pose is available for that moment, the
   observation is dropped, as a pose from the wrong time would directly add landmark error.
4. **Associate** with the nearest landmark of the same class within `gate_m`, or create a new one.
5. **Running mean** across observations, which reduces random error; the variance is kept as well.

Sign text is joined by geometry. The C920 reads the text and the D455 gives the position, so each known sign is
projected into the C920 image, and the sign falling inside the OCR box gets the text. If none does, nothing is
attached, rather than guessing.

## O8 comparison
`fusion_mode: fused` is the running mean; `single_observation` keeps only the first observation. Every raw observation is
stored in the `observations` table in both modes, so `tools/eval/fusion_compare.py` compares them from one run.

## Known limitations
- **Doors nearer than `gate_m` merge** into one landmark. Measure the real door spacing and set the gate below it.
- Association uses class and distance only. Text is unknown when a D455 observation arrives, because it comes later
  from the C920, so two nearby signs can merge before they are read.
- `attach_text` depends on the C920 pose in `sensor_poses.yaml` and its intrinsics, both placeholders until measured.
- The `photo_path` and `photo_id` of landmarks are not yet filled in. Website route photos come from junctions.

## Unit tests that pass on Windows
`test/test_semantic_core.py`: synthetic detections with known geometry, checking positions to within 1 cm (identity,
translated and rotated cameras, full pipeline); median depth with invalid pixels; depth range limits; association;
running mean and variance; both fusion modes; text attachment; database round trip and constraints.
**Not covered on Windows:** `landmark_node` itself (message sync, TF, cv_bridge).
