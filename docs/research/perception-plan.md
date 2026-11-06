# Perception plan for O3: landmark detection and door-sign OCR

**Status: PROPOSED** (2026-11-05, branch `perception-prototype`). Nothing here is agreed with the supervisor.
Nothing has run on Merz Court photos, the C920, the D455 or the Jetson. The prototype is in `perception/`.

O3 target (proposal, `docs/planning/experiments.md`): **at least 85% of the door signs in the test area read correctly.**

## 1. Summary
1. No pretrained model covers all five classes. Doors and stairs exist in Open Images V7 [1], [2]. Lifts, exit signs
   and door signs are missing from both COCO and Open Images V7. Merz Court photos are needed for every class anyway.
2. **Recommended route: label 400-600 photos of Merz Court only, then fine-tune `yolo11n.pt`.** Open datasets are
   optional and mostly overkill (section 3).
3. The OCR uses pretrained PaddleOCR PP-OCR models [5]. Training our own OCR is overkill: the signs are printed text.
4. The prototype found a real failure mode on synthetic signs. PP-OCR's text detector can split "M1.14" into two
   overlapping pieces, "M1.1" and "14". Picking the most confident line then returns "14", which the placeholder regex
   accepts as a valid room number. The prototype fixes this by re-reading the merged row and dropping fragments. This
   took the synthetic crop score from 8/12 to 12/12 (section 6). The ROS `merz_perception` package has the same
   weakness (section 8).
5. For the YOLOE zero-shot detector as a stopgap, accuracy on real signs is UNKNOWN.

## 2. Class coverage by existing pretrained models
| Class | COCO (e.g. `yolo11n.pt`, supervisor's practice script) | Open Images V7 (`yolov8n-oiv7.pt` etc.) | YOLOE text prompts |
| --- | --- | --- | --- |
| door | No | **Yes**, "Door" (and "Door handle") [2], [3] | Prompt "door"; not measured on real doors |
| lift | No | **No** ("Elevator" is not a class) [2], [3] | Prompt "elevator door"; not measured |
| stairs | No | **Yes**, "Stairs" [2], [3] | Prompt "staircase"; not measured |
| exit sign | No | **No** (only "Traffic sign", "Stop sign", "Billboard") [2] | Prompt "exit sign"; not measured |
| door sign | No | **No** | Prompt "door sign": 15/36 synthetic scenes at conf 0.25, 31/36 at 0.10 (section 6) |

- COCO: the 80 COCO classes contain none of the five classes (already noted in `tools/yolo_practice/README.md`).
- Open Images V7 YOLOv8 models: Ultralytics lists `yolov8n-oiv7.pt` (mAP50-95 18.4) up to `yolov8x-oiv7.pt` (36.3)
  over 600 classes [3]. These figures average over 600 classes. Door/Stairs accuracy indoors is UNKNOWN. A 600-class
  head is also wasted work on the Jetson. Useful only as a quick sanity check, not for the robot.
- YOLOE [4]: an open-vocabulary YOLO. `set_classes([...])` needs a text encoder: `mobileclip_blt.ts`, 572 MB,
  downloaded in this session for YOLOE-11. Afterwards the classes are baked into the weights and can be exported to
  TensorRT [4]. It is useful **before** any labelling, for example to pre-label photos or demo the pipeline. It is not
  a substitute for a fine-tuned model until it has been measured on real photos.

## 3. Open datasets (each checked on 2026-11-05)
| Dataset | Classes of interest | Size | Licence | Link | Verdict |
| --- | --- | --- | --- | --- | --- |
| Open Images V7 [1], [2] | Door, Door handle, Stairs, Window | 600 boxable classes; 1,743,042 train images with boxes; Ultralytics' full download needs >= 561 GB [3] | Annotations CC BY 4.0 (Google). Images listed as CC BY 2.0, but Google gives no warranty per image [1] | https://storage.googleapis.com/openimages/web/factsfigures_v7.html | Optional. A door/stairs subset only (FiftyOne or the OIDv4 toolkit can filter by class). **Full download is overkill** |
| DoorDetect [6] | door, handle, cabinet door, refrigerator door | 1,213 images, YOLO `.txt` labels (from Open Images V4 + MCIndoor20000) | **No licence file** in the repo (checked). The authors ask to be cited. Treat as research use only and ask the authors before redistributing | https://github.com/MiguelARD/DoorDetect-Dataset | Optional pre-training for `door`. Cite [6] if used |
| MCIndoor20000 [7] | doors, stairs, hospital signs | > 20,000 images | "Freely available for academic, educational and research purposes" (no formal licence) | https://github.com/bircatmcri/MCIndoor20000 | **Not usable: the repo says the data is no longer available for download** |
| Roboflow Universe projects (exit signs, lifts) | e.g. "exit-sign-Extended version" (KIT), "personal_exitSign", "Things" (door, elevator, junction), "elevator-mshv5" | **UNVERIFIED** | Search snippets say CC BY 4.0. **The pages could not be opened** (universe.roboflow.com is blocked in this cloud session), so licence, size and label quality are unchecked | https://universe.roboflow.com/kit-g1foh/exit-sign-extended-version, https://universe.roboflow.com/cps-laboratory/things-srzfq, https://universe.roboflow.com/marayas-workspace/elevator-mshv5 | Check each page by hand before use; licence can change. Probably unnecessary |

No open dataset of UK university door signs was found. **Door signs must come from Merz Court.** That is also the
class O3 depends on.

**Recommendation (PROPOSED):** start with Merz Court photos only. Add DoorDetect or an Open Images door/stairs subset
only if the val results (section 4.4) show door or stairs recall below about 0.8 after one round of extra Merz photos.
Mixing datasets adds licence bookkeeping and class-name mapping, and the robot only has to work in one building.

## 4. Minimal custom-data plan
### 4.1 Photos (phone, then robot frames)
Checklist: `perception/PHOTO_CHECKLIST.md`. Targets for **round 1** (about 2 hours in Merz Court):

| Class | Photos (instances) | Note |
| --- | --- | --- |
| door_sign | every sign in the chosen corridors x 3-4 views; aim for 150-250 | the O3 class; the test corridor is photographed **separately** (4.3) |
| door | comes free with the sign photos; add 30-50 doors without signs | |
| lift | 30-50 (every lift, every floor visited, doors open and shut) | few lifts in the building, so vary angle and distance |
| stairs | 30-50 (every stairwell, from top and bottom) | |
| exit_sign | 50-100 | ceiling and over-door signs, lit and unlit |
| background | about 10% of the total: corridors with none of the above | reduces false detections |

These numbers are a starting heuristic, not a verified rule (Ultralytics' training-tips page could not be opened from
this session). The rule that matters is: **train, look at per-class val results, then photograph more of the weak
class.** Once the robot runs, add frames from the D455/C920 rosbags (`tools/extract_frames.py`). Phone photos are
sharper and higher-resolution than robot frames, so expect a drop when moving to robot frames, and measure it.

### 4.2 Labelling
- **Label Studio** (open source, Apache-2.0 [8]). Install with `pip install label-studio`, then run `label-studio`.
  Use the "Object Detection with Bounding Boxes" template with the five class names from
  `perception/train/merz_landmarks.yaml`. Export as "YOLO". A second-hand report says the YOLO export may leave out
  the images, so keep the originals and copy the `.txt` files next to them. CVAT also exports Ultralytics YOLO and is
  a fine alternative; its licence scope was not checked here.
- Box rule for `door_sign`: the whole plate including its border, not just the number. One box per plate. Signs too
  small to read by eye still get a box, since the detector should learn them; leave them out of the OCR truth list.
- Optional shortcut: pre-label with YOLOE (`run.py --detector yoloe`) and correct the boxes by hand. Only worth it
  above about 300 photos.
- Ground truth for O3: a separate `signs.csv` (`image,text,sign_id`), written on foot from the sign itself, never
  from the OCR output.

### 4.3 Train/val/test split
- **Split by area, never by photo.** Near-duplicate views of one sign would otherwise appear in both sets
  (`perception/train/split_dataset.py`; name files `<area>_<sign>_<nn>.jpg`).
- **train** about 80%, **val** about 20% (one or two whole areas held out).
- **O3 test corridor**: photographed and driven **only for testing**, never labelled for training
  (`docs/planning/experiments.md` O3 threats: "hold back one corridor").

### 4.4 Fine-tuning
- `python perception/train/train_yolo.py --data perception/train/merz_landmarks.yaml`. This starts from COCO
  `yolo11n.pt`, the same family as the practice script, with imgsz 640, up to 100 epochs, early stop after 20, and
  **horizontal flip off** (it mirrors text and arrows).
- Train on the laptop GPU or Google Colab, not the Jetson.
- If `door_sign` recall on val is low, try `yolo11s.pt` before collecting much more data, and check the detection
  speed on the Jetson afterwards.
- Accept the model on **end-to-end O3 score** (`perception/score_ocr.py`) on the val area, not just on mAP.

### 4.5 TensorRT on the Jetson (later, G2 onwards)
- Export on the Jetson itself, since engines are tied to the GPU and the TensorRT version (RESEARCH_INDEX [N10]):
  `yolo export model=best.pt format=engine quantize=16 imgsz=640`. `quantize` replaces the deprecated
  `half`/`int8` arguments, as confirmed in the installed Ultralytics 8.4.202 `default.yaml`.
- **Re-score the exported model; do not assume it matches the `.pt`.** In this session's synthetic smoke test, the
  ONNX export of a 10-epoch model missed 2 of 6 small signs that the `.pt` found (section 6). The likely causes are a
  fixed 640x640 input against `.pt` rectangular letterboxing, and a weak model near threshold. This is not
  investigated further.
- FP16 is enough. INT8 calibration is overkill unless the Jetson is too slow at 2-3 Hz.

## 5. OCR and room-number parsing
- **OCR:** PaddleOCR 3.x (Apache-2.0 [5]; 3.7.0 is current and lists Python 3.8-3.12). Orientation and unwarping
  models are off. Fallback: **RapidOCR** (`rapidocr_onnxruntime`), which runs PP-OCR models through ONNX Runtime and
  ships them inside the pip wheel. This matters on the Jetson and offline. In this cloud session PaddleOCR installed
  but could not download its models (its hosts are blocked here), so **every OCR result below used RapidOCR**.
- **Crop:** the sign box plus 10% per side, upscaled to at least 96 px tall. Sharpness (variance of Laplacian) is
  logged; the gate is off until real thresholds are measured (OPEN_ISSUES #18).
- **Split-row repair:** text pieces that sit side by side on one row are merged and the union is re-read in
  recognition-only mode. A candidate that is a substring of a longer candidate ("14" of "M1.14") is dropped.
- **Regex:** configurable in `perception/config/sign_formats.yaml`. It holds a list of patterns, each a full match
  after normalising, with lookalike repair (O->0, I->1, ...) everywhere except the prefix letter. The placeholder is
  the same as the ROS config: `[A-Z]?\d{1,2}\.?\d{1,3}`. **The real Merz Court format is UNKNOWN.** Record it during
  the photo walk, then tighten the pattern. Requiring the prefix letter, if signs have one, would block bare
  fragments.
- **Camera:** text from the C920, position from the D455 (decisions #17, PROPOSED). The prototype is camera-agnostic.

## 6. What was run (2026-11-05, cloud Linux container, CPU only, Python 3.12)
Every image below is **SYNTHETIC**. The generator is `perception/samples/make_synthetic_signs.py`, with a guessed
"M1.05"-style format, clean fonts and plain walls. These results show that the code runs end to end. **They say
nothing about O3 on real signs.**

| Run | Result |
| --- | --- |
| Unit tests `cd perception && python -m pytest` | 33 passed |
| 12 sign crops, detector `none`, RapidOCR, **before** split-row repair | 8/12 correct; 4 false reads ("14", "33", "10", "11") |
| Same, **after** split-row repair | 12/12 correct, 0 false reads; about 0.3-0.5 s per crop on CPU |
| 36 scenes (3 views x 12 signs: 1 m-like/straight, mid/25 degrees/blur, far/-35 degrees/dim/blur), whole image to OCR | 36/36 photos, 12/12 signs |
| 36 scenes, YOLOE-11s zero-shot "door sign", conf 0.25 | detector found 15/36 (all 15 read correctly); 12/12 signs by plurality vote |
| Same, conf 0.10 | 31/36 photos, 0 false reads |
| Smoke fine-tune `yolo11n.pt`, 10 epochs, CPU, 30 train / 6 val synthetic scenes (split by sign) | pipeline ran; `.pt` model: 6/6 val photos read |
| ONNX export of that model | export ran; 4/6 read (missed the 2 smallest signs) |

**Not run:** PaddleOCR itself (models blocked; only parsing of its result format is unit-tested), PaddleOCR's
recognition-only path (`PaddleEngine.recognise`), webcam mode (no camera in the container), TensorRT export and
anything on the Jetson, any real Merz Court photo, timing on the Jetson, and the Open Images / DoorDetect / Roboflow
data.

Note on the scorer: the sign-level score is a plurality vote over that sign's photos, so a sign seen correctly once
and missed twice counts as read. This matches a robot that gets several looks per sign. The per-photo rate and the
false-read count are reported alongside because they are stricter.

## 7. Decisions needed (for `docs/decisions.md`, PROPOSED)
1. Class name for signs: the ROS config uses `room_sign`, the prototype `door_sign`. Pick one before labelling.
2. Room-number pattern(s): set from the photo walk.
3. Port the split-row repair and fragment suppression into `ros2_ws/src/merz_perception` (section 8).
4. Whether to keep RapidOCR as the default on the Jetson (simpler install) with PaddleOCR as the option, or the
   reverse.

## 8. Same weakness in the ROS package (not changed: outside this task's scope)
`ros2_ws/src/merz_perception/merz_perception/ocr.py::_best` keeps only the single most confident line. In the
synthetic case this is "14" (0.9999) rather than "M1.1" (0.992). `room_numbers.RoomNumberValidator` then accepts "14"
under the same placeholder regex, giving a false room. The `ReadAgreement` 2-read rule does not help, because the
same split repeats on every frame. Proposed fix: port `row_groups`, `RapidEngine.recognise` and the substring
suppression from `perception/merz_signs/`.

## 9. Flagged as overkill for this project
- Training or fine-tuning an OCR model, or any OCR dataset (ICDAR, TextOCR). Printed signs are read well by
  pretrained PP-OCR; measure first.
- Downloading full Open Images (>= 561 GB) or using the 600-class OIV7 models on the robot.
- Running YOLOE with its text encoder on the Jetson. Bake the classes and export instead, or better, use the
  fine-tuned model.
- Segmentation models, tracking and synthetic-data training. The synthetic generator is a test fixture only.
- INT8 calibration, DeepStream, or a custom TensorRT pipeline. Ultralytics `format=engine` FP16 first.
- More than about 600 photos before the first training round.

## References
[1] Google, "Open Images V7 - Facts and figures," https://storage.googleapis.com/openimages/web/factsfigures_v7.html (accessed 5 Nov. 2026).
[2] Google, "oidv7-class-descriptions-boxable.csv," https://storage.googleapis.com/openimages/v7/oidv7-class-descriptions-boxable.csv (accessed 5 Nov. 2026).
[3] Ultralytics, "Open Images V7 dataset" docs and `open-images-v7.yaml`, https://github.com/ultralytics/ultralytics/blob/main/docs/en/datasets/detect/open-images-v7.md (accessed 5 Nov. 2026).
[4] Ultralytics, "YOLOE" docs, https://github.com/ultralytics/ultralytics/blob/main/docs/en/models/yoloe.md (accessed 5 Nov. 2026).
[5] PaddlePaddle, "PaddleOCR" README (v3.7.0, Apache-2.0), https://github.com/PaddlePaddle/PaddleOCR (accessed 5 Nov. 2026).
[6] M. Arduengo, C. Torras and L. Sentis, "Robust and adaptive door operation with a mobile robot," *Intelligent Service Robotics*, 2021; dataset https://github.com/MiguelARD/DoorDetect-Dataset (accessed 5 Nov. 2026).
[7] F. A. Bashiri, E. LaRose, P. Peissig and A. P. Tafti, "MCIndoor20000: A fully-labeled image dataset to advance indoor objects detection," *Data in Brief*, 2018; https://github.com/bircatmcri/MCIndoor20000 (accessed 5 Nov. 2026).
[8] HumanSignal, Label Studio LICENSE (Apache-2.0), https://github.com/HumanSignal/label-studio (accessed 5 Nov. 2026).
