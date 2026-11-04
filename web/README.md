# Demonstrator website

**Status: IMPLEMENTED - not yet built or tested on hardware.** It runs on the Windows laptop with **made-up sample data**.
It has not yet used data from the robot, and it has not been tested on real phones.

A small read-only app showing what the robot's map can do. It is a demonstrator and is the first thing to cut if time runs
short (decisions #5). A visitor scans the QR code at an entrance, chooses a room and follows photo directions (decisions #12).

## Run it on Windows (3 commands)
From the repository root, in PowerShell:
```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r web\requirements.txt
.venv\Scripts\python -m uvicorn app.main:app --app-dir web --reload
```
Then open <http://localhost:8000/?entrance=north>. Try `south` too: the rooms differ, because the sample has a locked door.
For a phone on the same Wi-Fi, add `--host 0.0.0.0` and use the laptop's IP address. (For the unit tests, install
`requirements-dev.txt` instead and run `.venv\Scripts\python -m pytest web`.)

## What the page does
| Screen | Notes |
| --- | --- |
| Entrance (`/?entrance=X`, from the QR code) | "You are here" sign, then a searchable list of **only the rooms reachable from X**. Enter opens the first match. |
| Route (`/?entrance=X&room=Y`) | Pan/zoom map (drag, pinch, wheel, +/-, arrow keys) with the route, entrance, destination and numbered junctions. Photo cards swipe left/right; tapping a number, a card arrow or a junction on the map moves both the cards and the map to that step. |
| About (`/about`) | The rover in plain words, with photo slots (see `static/photos/README.md`). |
| Problems | Unknown entrance in the QR code, room not reachable from this entrance, search with no match, missing photo, no map file, server not answering (with "Try again"). |

Design: building-signage style (navy sign panel, yellow signal band, Atkinson Hyperlegible). Route, entrance and destination
colours were checked with a colour-blindness validator in light and dark themes, and also differ by shape. Text contrast is
at least 4.5:1, touch targets are at least 44 px, everything works by keyboard, and screen readers get labels and step
announcements. The map's text alternative is the step list. The font loads from Google Fonts when online; offline, the
system font is used.

## API
| Request | Returns |
| --- | --- |
| `GET /entrances` | All entrances, and whether this is sample data |
| `GET /rooms?entrance=X` | Rooms reachable from X only |
| `GET /route?entrance=X&room=Y` | Steps: junction, instruction, photo, position (m) and distance from the previous point; also `start` and `destination` positions. 404 if not reachable |
| `GET /map` | Where the occupancy-grid image sits in the map frame (`origin`, `resolution`, `width`, `height`), or `{"available": false}` |
| `GET /map.png` | The occupancy grid as a PNG: floor, walls, and transparent unknown space |

Routes are the shortest path over the junction graph **inside that entrance's zone**, so they never pass through a door the
visitor cannot open. All database access is read-only, and the map files are only read.

## Replacing the sample data with real rover data
The website needs three things, all made by the robot. Point the server at them with environment variables:

| Variable | What | Where the robot writes it |
| --- | --- | --- |
| `MERZ_DB` | The SQLite database (rooms, junctions, access zones) | `~/merz_data/merz.sqlite` (`docs/DATABASE_SCHEMA.md`) |
| `MERZ_PHOTOS` | Folder of junction photos named in the `photos` table | `junction_photo_node` output folder |
| `MERZ_MAP` | The map_saver `.yaml` (its `.pgm` must sit next to it) | `~/merz_data/maps/<entrance>_<time>.yaml`: use the **last** run, which holds the merged map frame |

1. Copy the three from the Jetson to the laptop, e.g. into `C:\merz_data\`.
2. Start the server with them:
   ```powershell
   $env:MERZ_DB = "C:\merz_data\merz.sqlite"; $env:MERZ_PHOTOS = "C:\merz_data\photos"; $env:MERZ_MAP = "C:\merz_data\maps\final.yaml"
   .venv\Scripts\python -m uvicorn app.main:app --app-dir web --host 0.0.0.0
   ```
3. Check that the "Sample data" ribbon has gone (the robot does not set `sample_data` in `meta`), open each entrance, and
   compare a few routes with the building before printing posters (O7).

Without `MERZ_MAP` the site still works: it draws the route on a plain background and says the map is not available. The
map, junctions and rooms must share one map frame (`docs/DATABASE_SCHEMA.md`, "One map frame"), or the route will not line up.

Rebuild the sample (database, 11 junction photos, `merz_map.pgm/.yaml`) with:
```powershell
.venv\Scripts\python web\sample_data\make_sample_db.py
```
The sample is made up: the layout and room numbers are not Merz Court.

## QR posters
```powershell
.venv\Scripts\python web\qr_posters.py --database web\sample_data\merz_sample.sqlite --base-url http://<reachable-address>:8000 --out posters
```
Writes one A4 PNG per entrance and `posters.pdf` with all of them (print at 100 % scale), in the same design as the site.
Scan a printed poster with a real phone before relying on it.

## Limitations
- Turn directions come from straight lines between junctions, so a curving corridor could give the wrong word. The photos
  are the main guide.
- A room's nearest junction is by straight-line distance, which could be on the far side of a wall.
- "Distance from the last junction" is a straight line, and walking time assumes about 70 m a minute.
- Visitors need the server to be reachable; hosting for the demo is still to be decided.
- Not yet tried with a real screen reader or on real phones: only in a headless browser at phone and desktop sizes.

## Unit tests that pass
`test_web.py`: shortest paths including zone limits, turn directions, all API routes on the sample database, room and route
restrictions by entrance, route positions and distances, map metadata and PNG, map classification (map_server rules),
the site working without a map, every junction on open floor in the sample map, static pages, no API text inserted as HTML,
query time under 1 s (in-process), QR codes decoded back to the right URL, and the combined A4 PDF.
