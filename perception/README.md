# perception/ - sign-reading prototype for O3 (PROPOSED)

**Status: PROPOSED prototype, not robot code, no ROS.** It has run only on SYNTHETIC images in a cloud container
(CPU, RapidOCR). It has not run on Merz Court photos, a webcam, PaddleOCR's own models or the Jetson. Plan, datasets
and results: `docs/research/perception-plan.md`. Photo walk: `PHOTO_CHECKLIST.md`.

Pipeline: image or webcam frame -> detector (none / YOLOE zero-shot / fine-tuned YOLO) -> crop each sign (+10%) ->
OCR (PaddleOCR, or RapidOCR with the same PP-OCR models) -> re-read rows split by the text detector -> regex room
number (patterns in `config/sign_formats.yaml`) -> JSON. `score_ocr.py` compares the JSON with a ground-truth CSV:
this is the proposed O3 measurement.

| File | What it does |
| --- | --- |
| `run.py` | CLI: images, a folder or a webcam index -> `results.json` |
| `score_ocr.py` | Per-photo and per-sign read rate, false reads, PASS/FAIL against 85% |
| `merz_signs/room_parser.py` | Normalise, regex, lookalike repair, row merging, fragment suppression (pure Python) |
| `merz_signs/ocr.py` | PaddleOCR / RapidOCR wrappers and result parsing |
| `merz_signs/detector.py` | Whole-image, YOLOE (text prompts) and YOLO detectors |
| `merz_signs/pipeline.py` | Joins the parts; `SignPipeline.process(image) -> dict` |
| `config/sign_formats.yaml` | Room-number regexes (placeholder until the real format is seen), detector settings |
| `samples/make_synthetic_signs.py` | SYNTHETIC sign images + truth CSVs + YOLO labels, for testing only |
| `train/` | Dataset YAML, area-based train/val split, fine-tune script (Ultralytics) |
| `tests/` | 33 unit tests, no models needed |

## Set up (laptop, Python 3.12; PaddleOCR lists 3.8-3.12)
```bash
python -m venv .venv && .venv/bin/pip install -r perception/requirements.txt
```
On Windows use `.venv\Scripts\pip`. The first PaddleOCR run downloads its models. If that fails, use `--ocr rapid`
(the models ship in the pip wheel).

### Windows (PowerShell), one command per line
PowerShell 5 does not accept `&&`, and the paths use `\Scripts\` instead of `/bin/`. From inside `perception\`:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt     # if paddlepaddle/paddleocr fail, they are not needed for --ocr rapid
python samples\make_synthetic_signs.py
```
`samples/synthetic/` is generated, not committed: run `make_synthetic_signs.py` before the commands below.

**Webcam (`--show`) needs the GUI build of OpenCV.** `requirements.txt` installs `opencv-python-headless`, which
has no preview window. `opencv-python` and `opencv-python-headless` share one `cv2` folder, so uninstalling one breaks
the other (`module 'cv2' has no attribute 'VideoCapture'`). Remove all variants, then install one cleanly:
```powershell
pip uninstall -y opencv-python opencv-python-headless opencv-contrib-python opencv-contrib-python-headless
pip install --force-reinstall --no-cache-dir opencv-python
python run.py --source 0 --detector none --ocr rapid --show
```
Re-running `pip install -r requirements.txt` brings the headless build back; repeat the two lines above if it does.

## Run
```bash
cd perception
python -m pytest
python samples/make_synthetic_signs.py
python run.py --source samples/synthetic/crops --ocr rapid --out results.json
python score_ocr.py --truth samples/synthetic/truth_crops.csv --results results.json
python run.py --source samples/synthetic/scenes --detector yoloe --conf 0.1 --out results_scenes.json
python run.py --source 0 --detector yoloe --show
```
The YOLOE run downloads `yoloe-11s-seg.pt` (28 MB) and a 572 MB text encoder on first use. The webcam command (the
last one; `q` quits) was not run in this session.

## Measuring O3 on real photos
1. Photo walk (`PHOTO_CHECKLIST.md`) and a `signs.csv` with `image,text,sign_id`.
2. `python run.py --source <photos> --detector yolo --weights best.pt --out results.json`
3. `python score_ocr.py --truth signs.csv --results results.json --json score.json`

On the robot the equivalent is `tools/eval/ocr_rate.py` against the SQLite database. This scorer is per photo, so it
can be used before the robot exists.

## Known limits
- The room regex is a placeholder: the real Merz Court sign format is UNKNOWN.
- The sharpness gate is off (`min_sharpness: 0`) until thresholds are measured on real crops.
- `PaddleEngine.recognise` (recognition-only re-read with PaddleOCR 3.x) has not been run; only the RapidOCR path ran.
- The two-reads agreement rule of the ROS `sign_reader_node` is not reproduced here; scoring uses a per-sign vote
  instead.
