# Merz Mapper website (demonstrator)

**Status: IMPLEMENTED - not yet built or tested on hardware.** Everything shown comes from a data bundle made from a rover
run. Until the rover has run, the bundle comes from a **synthetic run** (an invented building and simulated robot, in the
rover's real file formats), and the site says so on every page. The website is a demonstrator and is the first thing to
cut if time runs short (decisions #5); the robot is the project.

Design brief: `docs/WEBSITE_DESIGN.md`. Pages: landing and story (`/`), wayfinding from a QR code (`/?entrance=X`, `/find`),
mission replay (`/mission`), results for objectives O2-O8 (`/results`), about (`/about`).

## Run it on Windows (3 commands)
From the repository root, in PowerShell (Python 3.12; no Node.js needed, the built site is committed in `web/dist`):
```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r web\requirements.txt
.venv\Scripts\python -m uvicorn app.main:app --app-dir web
```
Open <http://localhost:8000/>, or <http://localhost:8000/?entrance=north> as a QR poster would. For phones on the same
Wi-Fi, add `--host 0.0.0.0` and use the laptop's IP address.

## Import a real rover run (1 command)
Copy the rover's `~/merz_data` folder (or the parts below) to the laptop, then:
```powershell
.venv\Scripts\python tools\web_import.py C:\path\to\merz_data
```
It writes `web/data/<run-id>/` and makes it the default; restart the server and the site shows the real run. Install
`requirements-dev.txt` first (the importer reads rosbags with the pure-Python `rosbags` library, so no ROS is needed).

| In the run folder | Written by | Used for |
| --- | --- | --- |
| `merz.sqlite` | `landmark_node`, `junction_photo_node`, access zone code | rooms, landmarks, sightings, junctions, zones, routes |
| `maps/*.yaml` + `.pgm` | `mission_node` (slam_toolbox `save_map`) | the map; the most complete one is used (`--map` to choose) |
| `photos/` | `junction_photo_node` (and sign crops, if `landmarks.photo_id` is set) | junction photos, gallery; converted to WebP + thumbnails |
| `bags/*/` | `record_bag.launch.py` (mcap or sqlite3) | mission replay: `/tf` (map->odom->base_link), `/scan`, `/map` snapshots |
| `eval/*.json`, `*.png` | `tools/eval/*.py --json ... --plot ...` | results page; an objective without a file shows "not yet measured" |

Nothing is invented: if a part is missing, that part of the site says so. Real runs have no `sample_data` flag, so the
"Sample" badge disappears. Note: the rover code does not yet store sign crops (`landmarks.photo_id` stays empty), so
real signs show without photos until that is added (PROPOSED).

Score a run before importing it (procedures and pass rules: `docs/EXPERIMENTS.md`), for example:
```powershell
.venv\Scripts\python tools\eval\map_coverage.py --map run\maps\run_south.yaml --polygon corridor.csv --json run\eval\map_coverage.json --plot run\eval\map_coverage.png
```

### The synthetic sample run
```powershell
.venv\Scripts\python tools\synthetic_run\make_synthetic_run.py data\synthetic_run
.venv\Scripts\python tools\web_import.py data\synthetic_run --run-id sample
```
About 45 s. It simulates two entrance runs (lidar ray casting, drifting odometry corrected by a SLAM-like map->odom,
camera sightings with systematic and random error, OCR slips), writes them in the rover's formats, computes access zones
with the rover's own `merz_exploration` code, and scores them with the real `tools/eval` scripts. The numbers describe
the simulator, not the robot. The raw run goes in `data/` (not in git); the bundle in `web/data/sample` is committed.

## Rebuild the frontend (only after changing `web/frontend`)
Needs Node.js 20+:
```powershell
cd web\frontend
npm ci
npm run build
```
This type-checks and writes `web/dist`; commit `web/dist` so the site still runs with Python only. `npm run dev` serves
a live-reloading copy that reads data from the FastAPI server on port 8000.

Stack: Vite + TypeScript, three.js (map, 3D walls, replay), GSAP (motion), self-hosted Archivo / Geist / Geist Mono
(OFL). No other runtime dependencies.

## Export and deploy to GitHub Pages
```powershell
.venv\Scripts\python tools\web_export.py --out _site --base /merz-mapper/
```
`_site` is a complete static site (no server), with the data bundle and a copy of the page for each route and for 404s.
The workflow `.github/workflows/pages.yml` does this on every push to `main` that changes the site or data, and
publishes to `https://<user>.github.io/merz-mapper/`. One-off setup: repository Settings -> Pages -> Source: GitHub
Actions. QR posters can then point there:
```powershell
.venv\Scripts\python web\qr_posters.py --database web\data\sample\api\merz.sqlite --base-url https://<user>.github.io/merz-mapper --out posters
```
Add `--theme light` for the paper version (much less ink). Writes one A4 PNG per entrance and `posters.pdf`. Scan a
printed poster with a real phone before relying on it.

## API (FastAPI)
The browser reads only the static bundle, so the site works the same from Pages. The API stays for the O6/O7 route
timing test (`tools/eval/route_timing.py`) and other tools. By default it reads the current bundle's `api/` copy of
the database and map; `MERZ_DB`, `MERZ_PHOTOS` and `MERZ_MAP` override it.

| Request | Returns |
| --- | --- |
| `GET /entrances` | All entrances, and whether this is sample data |
| `GET /rooms?entrance=X` | Rooms reachable from X only |
| `GET /route?entrance=X&room=Y` | Steps (junction, instruction, photo, position, distance), start, destination. 404 if not reachable |
| `GET /map`, `GET /map.png` | Where the occupancy grid sits in the map frame, and the grid as a PNG |
| `/data/...` | The static bundle |

Routes are shortest paths over the junction graph inside the entrance's access zone, so they never pass a locked door.
The importer pre-computes every route with the same code (`web/app/routing.py`), adding the nearest lift, stairs or
exit sign to the instruction ("Turn left at the lift.").

## Accessibility and performance
Contrast >= 4.5:1 for text (checked; values in the design brief), touch targets >= 44 px, full keyboard use (map:
arrows, + and -, Q/E rotate, W/S tilt; walk-through: arrows, space, Escape), screen-reader labels and live
announcements, a text alternative for every map and chart (step lists, mission log, data tables), reduced motion
respected (no autoplay, instant camera), and a 2D map when WebGL is unavailable. three.js loads after the page text;
render loops pause when idle or hidden. First load is about 300 kB of JavaScript (gzip) plus fonts and the map.

## Tests
`web/test_web.py` (API, routing, posters, served site) and `tools/test_web_import.py` (importer from a simulated mcap
bag, TF composition, map levels, reveal, metrics never invented, eval `--json`, static export, bundle consistency):
```powershell
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest web tools
```
Not yet done: tests on real phones, with a real screen reader, and with real rover data.

`web/sample_data/` is the small fixture database the API tests build; the website itself uses `web/data`.
