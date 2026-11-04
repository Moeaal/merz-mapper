"""The demonstrator website: a read-only API over the robot's SQLite database, and the built site in web/dist.

Run from the web folder:
    python -m uvicorn app.main:app --reload
By default the API reads the current data bundle (web/data/index.json, made by tools/web_import.py), falling back to
web/sample_data. MERZ_DB, MERZ_PHOTOS and MERZ_MAP (the map_saver .yaml) override it.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.grid_map import GridMap, load_grid_map
from app.routing import Junction, describe_steps, nearest_junction, shortest_path

WEB_ROOT = Path(__file__).resolve().parents[1]
DATA = WEB_ROOT / 'data'
DIST = WEB_ROOT / 'dist'
SAMPLE_DB = WEB_ROOT / 'sample_data' / 'merz_sample.sqlite'
SAMPLE_PHOTOS = WEB_ROOT / 'sample_data' / 'photos'
SAMPLE_MAP = WEB_ROOT / 'sample_data' / 'merz_map.yaml'
# Pages of the single-page site. Anything else that is not a file or an API route gets the site's 404 page.
SITE_ROUTES = {'', 'find', 'mission', 'results', 'about'}


def current_bundle() -> Path | None:
    """The default run in web/data, if one has been imported."""
    try:
        default = json.loads((DATA / 'index.json').read_text())['default']
    except (OSError, ValueError, KeyError):
        return None
    bundle = DATA / default
    return bundle if (bundle / 'api' / 'merz.sqlite').is_file() else None


BUNDLE = current_bundle()
DEFAULT_DB = BUNDLE / 'api' / 'merz.sqlite' if BUNDLE else SAMPLE_DB
DEFAULT_PHOTOS = SAMPLE_PHOTOS
DEFAULT_MAP = BUNDLE / 'api' / 'map.yaml' if BUNDLE else SAMPLE_MAP


def create_app(database: str | Path = DEFAULT_DB, photo_dir: str | Path = DEFAULT_PHOTOS,
               map_yaml: str | Path | None = DEFAULT_MAP, bundle: Path | None = BUNDLE,
               site: Path | None = DIST) -> FastAPI:
    database = Path(database).expanduser()
    photo_dir = Path(photo_dir).expanduser()
    map_yaml = Path(map_yaml).expanduser() if map_yaml else None
    app = FastAPI(title='Merz Mapper demonstrator')
    if DATA.is_dir():
        app.mount('/data', StaticFiles(directory=DATA), name='data')
    if site and (site / 'assets').is_dir():
        app.mount('/assets', StaticFiles(directory=site / 'assets'), name='assets')
    grid_cache: dict[str, object] = {}

    def grid() -> GridMap | None:
        """The occupancy grid, loaded once and reloaded only when the file changes. None when there is no map."""
        if map_yaml is None or not map_yaml.is_file():
            return None
        stamp = map_yaml.stat().st_mtime_ns
        if grid_cache.get('stamp') != stamp:
            grid_cache['stamp'], grid_cache['map'] = stamp, load_grid_map(map_yaml)
        return grid_cache['map']

    def query(sql: str, parameters: tuple = ()) -> list[dict]:
        # Read-only by construction: the website can never alter what the robot recorded.
        connection = sqlite3.connect(f'file:{database.as_posix()}?mode=ro', uri=True)
        connection.row_factory = sqlite3.Row
        try:
            return [dict(row) for row in connection.execute(sql, parameters)]
        finally:
            connection.close()

    def entrance_or_404(entrance: str) -> dict:
        rows = query('SELECT * FROM entrances WHERE id = ?', (entrance,))
        if not rows:
            raise HTTPException(status_code=404, detail=f"Unknown entrance '{entrance}'")
        return rows[0]

    @app.get('/map')
    def map_info() -> dict:
        """Where the occupancy-grid image sits in the map frame, so the page can draw routes on top of it."""
        found = grid()
        if found is None:
            return {'available': False}
        return {'available': True, 'image_url': '/map.png', 'resolution': found.resolution,
                'origin': [found.origin_x, found.origin_y], 'width': found.width, 'height': found.height}

    @app.get('/map.png', include_in_schema=False)
    def map_image() -> Response:
        found = grid()
        if found is None:
            raise HTTPException(status_code=404, detail='No map has been loaded')
        return Response(found.png, media_type='image/png', headers={'Cache-Control': 'no-cache'})

    @app.get('/entrances')
    def entrances() -> dict:
        is_sample = query("SELECT value FROM meta WHERE key = 'sample_data'")
        return {
            'sample_data': bool(is_sample) and is_sample[0]['value'] == 'true',
            'entrances': [{'id': r['id'], 'name': r['name']}
                          for r in query('SELECT id, name FROM entrances ORDER BY name')],
        }

    @app.get('/rooms')
    def rooms(entrance: str) -> dict:
        """Only rooms reachable from this entrance: a visitor is never offered a room behind a locked door."""
        entrance_or_404(entrance)
        rows = query("""SELECT DISTINCT l.text AS room FROM landmarks l
                        JOIN access_zones z ON z.landmark_id = l.id
                        WHERE z.entrance_id = ? AND l.text <> '' ORDER BY l.text""", (entrance,))
        return {'entrance': entrance, 'rooms': [row['room'] for row in rows]}

    @app.get('/route')
    def route(entrance: str, room: str) -> dict:
        start = entrance_or_404(entrance)
        targets = query("""SELECT l.x, l.y FROM landmarks l JOIN access_zones z ON z.landmark_id = l.id
                           WHERE z.entrance_id = ? AND l.text = ?""", (entrance, room))
        if not targets:
            raise HTTPException(status_code=404, detail=f"Room '{room}' is not reachable from '{entrance}'")
        rows = query("""SELECT j.id, j.x, j.y, j.photo_id FROM junctions j
                        JOIN zone_junctions z ON z.junction_id = j.id WHERE z.entrance_id = ?""", (entrance,))
        junctions = [Junction(r['id'], r['x'], r['y']) for r in rows]
        first = nearest_junction(junctions, start['x'], start['y'])
        last = nearest_junction(junctions, targets[0]['x'], targets[0]['y'])
        if first is None or last is None:
            raise HTTPException(status_code=404, detail='No junctions are recorded for this entrance')
        edges = [(r['a'], r['b'], r['length_m']) for r in query('SELECT a, b, length_m FROM junction_edges')]
        found = shortest_path(edges, {j.id for j in junctions}, first.id, last.id)
        if found is None:
            raise HTTPException(status_code=404, detail=f"No route found to '{room}' from '{entrance}'")
        ids, length = found
        by_id = {j.id: j for j in junctions}
        photos = {r['id']: r['photo_id'] for r in rows}
        instructions = describe_steps([by_id[i] for i in ids], room, (start['x'], start['y']))
        steps, previous = [], (start['x'], start['y'])
        for i, text in zip(ids, instructions):
            here = by_id[i]
            steps.append({
                'junction_id': i,
                'instruction': text,
                'photo_url': f'/photos/{photos[i]}' if photos[i] is not None else None,
                'x': here.x,
                'y': here.y,
                # Straight-line distance from the previous point: a guide for the visitor, not a measured walk.
                'distance_m': round(math.hypot(here.x - previous[0], here.y - previous[1]), 1),
            })
            previous = (here.x, here.y)
        return {
            'entrance': entrance,
            'room': room,
            'length_m': round(length, 1),
            'start': {'id': start['id'], 'name': start['name'], 'x': start['x'], 'y': start['y']},
            'destination': {'room': room, 'x': targets[0]['x'], 'y': targets[0]['y']},
            'steps': steps,
        }

    @app.get('/photos/{photo_id}', include_in_schema=False)
    def photo(photo_id: int) -> FileResponse:
        rows = query('SELECT path FROM photos WHERE id = ?', (photo_id,))
        if not rows:
            raise HTTPException(status_code=404, detail='Unknown photo')
        # Paths were stored on the robot, so only the file name is used. It also keeps requests inside photo_dir.
        path = photo_dir / Path(rows[0]['path'].replace('\\', '/')).name
        if not path.is_file() and bundle is not None:
            path = bundle / 'photos' / f'p{photo_id}.webp'      # the importer's compressed copy
        if not path.is_file():
            raise HTTPException(status_code=404, detail='Photo file is missing')
        return FileResponse(path)

    @app.get('/{page:path}', include_in_schema=False)
    def site_page(page: str, request: Request) -> Response:
        """The built website. Its pages are handled in the browser, so they all return index.html."""
        if site is None or not (site / 'index.html').is_file():
            raise HTTPException(status_code=404, detail='The website has not been built: see web/README.md')
        target = (site / page).resolve()
        if page and target.is_file() and site.resolve() in target.parents:
            return FileResponse(target)
        status = 200 if page.strip('/') in SITE_ROUTES else 404
        return FileResponse(site / 'index.html', status_code=status, headers={'Cache-Control': 'no-cache'})

    return app


app = create_app(os.environ.get('MERZ_DB', DEFAULT_DB), os.environ.get('MERZ_PHOTOS', DEFAULT_PHOTOS),
                 os.environ.get('MERZ_MAP', DEFAULT_MAP))
