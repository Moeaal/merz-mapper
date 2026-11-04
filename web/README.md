# Demonstrator website

**Status: IMPLEMENTED - not yet built or tested on hardware.** It runs on the Windows laptop with **made-up sample data**.
It has not yet used data from the robot, and it has not been tested on real phones.

A small read-only app showing what the robot's map can do. It is a demonstrator and is the first thing to cut if time runs
short (decisions #5). A visitor scans the QR code at an entrance, chooses a room and follows photo directions (decisions #12).

## Open it now (Windows)
From the repository root:
```powershell
.venv\Scripts\python -m pip install -r requirements-dev.txt
cd web
..\.venv\Scripts\python -m uvicorn app.main:app --reload
```
Then open <http://localhost:8000/?entrance=north>. Try `south` too: the rooms differ, since the sample has a locked door.
For a phone on the same Wi-Fi, add `--host 0.0.0.0` and use the laptop's IP address.

## API
| Request | Returns |
| --- | --- |
| `GET /entrances` | All entrances, and whether this is sample data |
| `GET /rooms?entrance=X` | Rooms reachable from X only |
| `GET /route?entrance=X&room=Y` | Steps: junction, instruction and photo. 404 if not reachable |

Routes are the shortest path over the junction graph **inside that entrance's zone**, so they never pass through a door the
visitor cannot open. All database access is read-only.

## Real data
```powershell
$env:MERZ_DB = "C:\path\merz.sqlite"; $env:MERZ_PHOTOS = "C:\path\photos"
..\.venv\Scripts\python -m uvicorn app.main:app
```
Rebuild the sample with `python web/sample_data/make_sample_db.py`.

## QR posters
```powershell
python web/qr_posters.py --database web/sample_data/merz_sample.sqlite --base-url http://<reachable-address>:8000 --out posters
```
Scan a printed poster with a real phone before relying on it.

## Limitations
- Turn directions come from straight lines between junctions, so a curving corridor could give the wrong word. The photos
  are the main guide.
- A room's nearest junction is by straight-line distance, which could be on the far side of a wall.
- Visitors need the server to be reachable; hosting for the demo is still to be decided.

## Unit tests that pass on Windows
`test_web.py`: shortest paths including zone limits, turn directions, all API routes on the sample database, room and route
restrictions by entrance, query time under 1 s (on this laptop, in-process), and QR codes decoded back to the right URL.
