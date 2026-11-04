"""The demonstrator website: read-only API over the robot's SQLite database, plus one mobile page.

Run with the sample data, from the web folder:
    python -m uvicorn app.main:app --reload
Use real data by setting MERZ_DB, MERZ_PHOTOS and MERZ_MAP (the map_saver .yaml) first.
"""
from __future__ import annotations

import math
import os
from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.grid_map import GridMap, load_grid_map
from app.routing import Junction, describe_steps, nearest_junction, shortest_path

WEB_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = WEB_ROOT / 'sample_data' / 'merz_sample.sqlite'
DEFAULT_PHOTOS = WEB_ROOT / 'sample_data' / 'photos'
DEFAULT_MAP = WEB_ROOT / 'sample_data' / 'merz_map.yaml'
STATIC = WEB_ROOT / 'static'


def create_app(database: str | Path = DEFAULT_DB, photo_dir: str | Path = DEFAULT_PHOTOS,
               map_yaml: str | Path | None = DEFAULT_MAP) -> FastAPI:
    database = Path(database).expanduser()
    photo_dir = Path(photo_dir).expanduser()
    map_yaml = Path(map_yaml).expanduser() if map_yaml else None
    app = FastAPI(title='Merz Mapper demonstrator')
    app.mount('/static', StaticFiles(directory=STATIC), name='static')
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

    @app.get('/', include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC / 'index.html')

    @app.get('/about', include_in_schema=False)
    def about() -> FileResponse:
        return FileResponse(STATIC / 'about.html')

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
        if not path.is_file():
            raise HTTPException(status_code=404, detail='Photo file is missing')
        return FileResponse(path)

    return app


app = create_app(os.environ.get('MERZ_DB', DEFAULT_DB), os.environ.get('MERZ_PHOTOS', DEFAULT_PHOTOS),
                 os.environ.get('MERZ_MAP', DEFAULT_MAP))
