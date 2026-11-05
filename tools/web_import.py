"""Turn one rover run into the website's static data bundle. Works on Windows with no ROS installed.

    python tools/web_import.py PATH_TO_RUN                 # e.g. a copy of the rover's ~/merz_data
    python tools/web_import.py PATH_TO_RUN --run-id merz-court-2027-03 --name "Merz Court, first survey"

PATH_TO_RUN is laid out as the rover writes it (docs/software/database-schema.md, merz_bringup record_bag.launch.py):

    merz.sqlite          the database                       (required)
    maps/*.yaml + .pgm   saved maps; the most complete is used (required)
    photos/              junction photos and sign crops      (optional)
    bags/*/              rosbag2 folders, mcap or sqlite3    (optional: mission replay)
    eval/*.json, *.png   tools/eval outputs (--json/--plot)  (optional: results; never invented)

Output: web/data/<run_id>/ and web/data/index.json (this run becomes the default). Nothing in PATH_TO_RUN is changed;
the database is opened read-only.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import shutil
import sqlite3
import sys
from typing import Any, Optional

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'web'))

from app.routing import Junction, describe_steps_rich, nearest_junction, shortest_path  # noqa: E402

DATA_ROOT = REPO / 'web' / 'data'
FORMAT_VERSION = 1
UNKNOWN, FREE, OCCUPIED = 0, 127, 255          # values in the state images
PHOTO_WIDTH, THUMB_WIDTH = 1280, 480
TRAJECTORY_HZ = 5.0
SCAN_HZ = 1.0
SCAN_RAYS = 180
CLOUD_VOXEL_M = 0.1


# ------------------------------------------------------------------ small helpers
def rounded(value: Any, digits: int = 3) -> Any:
    """Round floats inside nested data, so the JSON stays small and stable."""
    if isinstance(value, float):
        return None if math.isnan(value) or math.isinf(value) else round(value, digits)
    if isinstance(value, dict):
        return {k: rounded(v, digits) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [rounded(v, digits) for v in value]
    return value


def write_json(path: Path, data: Any, digits: int = 3) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rounded(data, digits), separators=(',', ':'), ensure_ascii=False))


def slug(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-') or 'run'


def query(db: Path, sql: str, parameters: tuple = ()) -> list[dict]:
    connection = sqlite3.connect(f'file:{db.as_posix()}?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in connection.execute(sql, parameters)]
    finally:
        connection.close()


# ------------------------------------------------------------------ the map
class SavedMap:
    """A map_saver map, with cells as UNKNOWN/FREE/OCCUPIED and row 0 at the TOP (image order)."""

    def __init__(self, yaml_path: Path):
        from PIL import Image

        info = yaml.safe_load(yaml_path.read_text())
        with Image.open(yaml_path.parent / info['image']) as image:
            raw = np.asarray(image.convert('L'))
        negate = bool(info.get('negate', 0))
        probability = raw / 255.0 if negate else (255.0 - raw) / 255.0
        state = np.full(raw.shape, UNKNOWN, dtype=np.uint8)
        state[probability > float(info.get('occupied_thresh', 0.65))] = OCCUPIED
        state[probability < float(info.get('free_thresh', 0.25))] = FREE
        if info.get('mode', 'trinary') == 'trinary' and not negate:
            state[raw == 205] = UNKNOWN               # map_saver's unknown marker (see map_io.py)
        self.yaml_path = yaml_path
        self.state = state
        self.resolution = float(info['resolution'])
        origin = info.get('origin', [0.0, 0.0, 0.0])
        self.origin_x, self.origin_y = float(origin[0]), float(origin[1])
        self.height, self.width = state.shape

    @property
    def known_cells(self) -> int:
        return int(np.count_nonzero(self.state != UNKNOWN))


def choose_map(run: Path, explicit: Optional[Path]) -> SavedMap:
    if explicit:
        return SavedMap(explicit)
    candidates = sorted((run / 'maps').glob('*.yaml')) or sorted(run.glob('*.yaml'))
    maps = []
    for path in candidates:
        try:
            if 'image' in (yaml.safe_load(path.read_text()) or {}):
                maps.append(SavedMap(path))
        except (OSError, yaml.YAMLError, KeyError):
            continue
    if not maps:
        raise SystemExit(f'No map_saver .yaml + .pgm found in {run / "maps"}')
    # After several entrance runs the last map holds them all, so the most complete map is the one to show.
    return max(maps, key=lambda m: m.known_cells)


def downsample(state: np.ndarray, factor: int) -> np.ndarray:
    """Keep walls visible when shrinking: a block is occupied if any cell is, else free if any is, else unknown."""
    h, w = state.shape
    h2, w2 = -(-h // factor), -(-w // factor)
    padded = np.zeros((h2 * factor, w2 * factor), dtype=np.uint8)
    padded[:h, :w] = state
    blocks = padded.reshape(h2, factor, w2, factor)
    return blocks.max(axis=(1, 3))       # OCCUPIED (255) > FREE (127) > UNKNOWN (0)


def wall_boxes(saved: SavedMap) -> list[list[float]]:
    """Occupied cells merged into rectangles (map frame, metres), for extruding walls in 3D."""
    occupied = saved.state == OCCUPIED
    r = saved.resolution
    runs: dict[tuple[int, int], list[int]] = {}         # (col0, col1) -> rows, merged downwards
    boxes: list[list[float]] = []
    open_runs: dict[tuple[int, int], int] = {}            # run -> first row
    for row in range(saved.height + 1):
        current: set[tuple[int, int]] = set()
        if row < saved.height:
            line = occupied[row]
            padded = np.concatenate(([False], line, [False]))
            changes = np.flatnonzero(padded[1:] != padded[:-1])
            current = {(int(a), int(b)) for a, b in zip(changes[::2], changes[1::2])}
        for run, first in list(open_runs.items()):
            if run not in current:
                c0, c1 = run
                # Image row 0 is the highest y.
                boxes.append([saved.origin_x + c0 * r, saved.origin_y + (saved.height - row) * r,
                              saved.origin_x + c1 * r, saved.origin_y + (saved.height - first) * r])
                del open_runs[run]
        for run in current:
            open_runs.setdefault(run, row)
    del runs
    return boxes


# ------------------------------------------------------------------ bags
def bag_folders(run: Path) -> list[Path]:
    root = run / 'bags'
    folders = [p.parent for p in root.glob('*/metadata.yaml')] if root.is_dir() else []
    return sorted(folders)


def yaw_of(q) -> float:
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


def compose(a, b):
    ax, ay, at = a
    bx, by, bt = b
    return ax + math.cos(at) * bx - math.sin(at) * by, ay + math.sin(at) * bx + math.cos(at) * by, at + bt


def read_bag(folder: Path) -> dict:
    """Robot pose in the map frame (map->odom from SLAM composed with odom->base_link), scans and map snapshots."""
    from rosbags.highlevel import AnyReader

    poses: list[tuple[float, float, float, float]] = []
    scans: list[tuple[float, np.ndarray, float, float]] = []
    maps: list[tuple[float, np.ndarray, float, float, float, int, int]] = []
    laser_offset = (0.0, 0.0, 0.0)
    map_to_odom = None
    odom_to_base = None
    last_scan = -1e9
    with AnyReader([folder]) as reader:
        start = reader.start_time / 1e9
        wanted = [c for c in reader.connections if c.topic in ('/tf', '/tf_static', '/scan', '/map', '/odometry/filtered')]
        has_tf_odom = False
        for connection, timestamp, raw in reader.messages(connections=wanted):
            t = timestamp / 1e9
            msg = reader.deserialize(raw, connection.msgtype)
            if connection.topic in ('/tf', '/tf_static'):
                for transform in msg.transforms:
                    parent, child = transform.header.frame_id.lstrip('/'), transform.child_frame_id.lstrip('/')
                    v, q = transform.transform.translation, transform.transform.rotation
                    pose = (v.x, v.y, yaw_of(q))
                    if parent == 'map' and child == 'odom':
                        map_to_odom = pose
                    elif parent == 'odom' and child == 'base_link':
                        odom_to_base = pose
                        has_tf_odom = True
                    elif parent == 'base_link' and child in ('laser', 'laser_link', 'lidar_link'):
                        laser_offset = pose
            elif connection.topic == '/odometry/filtered' and not has_tf_odom:
                p = msg.pose.pose
                odom_to_base = (p.position.x, p.position.y, yaw_of(p.orientation))
            elif connection.topic == '/scan':
                if t - last_scan >= 1.0 / SCAN_HZ - 1e-3 and map_to_odom and odom_to_base:
                    pose = compose(compose(map_to_odom, odom_to_base), laser_offset)
                    ranges = np.asarray(msg.ranges, dtype=np.float32)
                    angles = msg.angle_min + np.arange(len(ranges)) * msg.angle_increment
                    scans.append((t, ranges, angles, pose))
                    last_scan = t
            elif connection.topic == '/map':
                info = msg.info
                maps.append((t, np.asarray(msg.data, dtype=np.int8).reshape(info.height, info.width),
                             info.origin.position.x, info.origin.position.y, info.resolution, info.width, info.height))
            if map_to_odom and odom_to_base and (not poses or t - poses[-1][0] >= 1.0 / TRAJECTORY_HZ - 1e-3):
                x, y, yaw = compose(map_to_odom, odom_to_base)
                poses.append((t, x, y, yaw))
    return {'start': start, 'poses': poses, 'scans': scans, 'maps': maps, 'folder': folder.name}


def mission_from_bags(bags: list[dict], saved: SavedMap, out: Path) -> Optional[dict]:
    """Concatenate entrance runs on one timeline, with a 4 s pause between them."""
    if not bags or not any(b['poses'] for b in bags):
        return None
    gap = 4.0
    offset = 0.0
    segments, trajectory, scan_meta, scan_ranges, snapshot_times = [], [], [], [], []
    reveal = np.zeros(saved.state.shape, dtype=np.uint8)
    cloud: dict[tuple[int, int], float] = {}
    all_maps = [(b, m) for b in bags for m in b['maps']]
    keep = set(np.linspace(0, len(all_maps) - 1, min(len(all_maps), 254)).round().astype(int).tolist()) if all_maps else set()
    snapshot_index = 0
    distance = 0.0
    for bag in bags:
        if not bag['poses']:
            continue
        t_start = bag['poses'][0][0]
        local = lambda t: offset + (t - t_start)  # noqa: E731
        previous = None
        for t, x, y, yaw in bag['poses']:
            if previous:
                step = math.hypot(x - previous[0], y - previous[1])
                distance += step if step < 2.0 else 0.0
            trajectory.append([local(t), x, y, yaw, distance])
            previous = (x, y)
        for t, ranges, angles, (lx, ly, lyaw) in bag['scans']:
            pick = np.linspace(0, len(ranges) - 1, SCAN_RAYS).round().astype(int)
            r = ranges[pick]
            centimetres = np.where(np.isfinite(r) & (r > 0), np.clip(r * 100, 0, 65000), 0).astype(np.uint16)
            scan_ranges.append(centimetres)
            scan_meta.append([local(t), lx, ly, lyaw, float(angles[pick[0]]), float(angles[pick[1]] - angles[pick[0]])])
            finite = np.isfinite(ranges) & (ranges > 0.05)
            hx = lx + ranges[finite] * np.cos(lyaw + angles[finite])
            hy = ly + ranges[finite] * np.sin(lyaw + angles[finite])
            for key in zip((hx / CLOUD_VOXEL_M).astype(int).tolist(), (hy / CLOUD_VOXEL_M).astype(int).tolist()):
                cloud.setdefault(key, local(t))
        for t, cells, ox, oy, res, w, h in bag['maps']:
            index = snapshot_index
            snapshot_index += 1
            if index not in keep or abs(res - saved.resolution) > 1e-6:
                continue
            snapshot_times.append(local(t))
            k = len(snapshot_times)
            col0 = int(round((ox - saved.origin_x) / res))
            row0 = int(round((oy - saved.origin_y) / res))         # in the snapshot, row 0 is the LOWEST y
            known = np.flipud(cells >= 0)                            # to image order
            top = saved.height - (row0 + h)
            r0, c0 = max(top, 0), max(col0, 0)
            r1, c1 = min(top + h, saved.height), min(col0 + w, saved.width)
            if r1 <= r0 or c1 <= c0:
                continue
            window = known[r0 - top:r1 - top, c0 - col0:c1 - col0]
            target = reveal[r0:r1, c0:c1]
            target[(target == 0) & window] = k
        segments.append({'name': bag['folder'], 'start_s': local(t_start), 'end_s': local(bag['poses'][-1][0])})
        offset = local(bag['poses'][-1][0]) + gap
    reveal[(reveal == 0) & (saved.state != UNKNOWN)] = len(snapshot_times) + 1 if snapshot_times else 1
    (out / 'mission').mkdir(parents=True, exist_ok=True)
    save_png(out / 'mission' / 'reveal.png', reveal)
    np.stack(scan_ranges).astype('<u2').tofile(out / 'mission' / 'scans.bin') if scan_ranges else None
    points = np.array([[kx * CLOUD_VOXEL_M + CLOUD_VOXEL_M / 2, ky * CLOUD_VOXEL_M + CLOUD_VOXEL_M / 2, t]
                       for (kx, ky), t in cloud.items()], dtype=np.float32).reshape(-1, 3)
    points = points[np.argsort(points[:, 2])]
    # x, y in centimetres and time in tenths of a second: 6 bytes a point.
    packed = np.column_stack([np.round(points[:, 0] * 100), np.round(points[:, 1] * 100),
                              np.clip(np.round(points[:, 2] * 10), 0, 65535) - 32768]).astype('<i2')
    packed.tofile(out / 'mission' / 'cloud.bin')
    return {
        'duration_s': offset - gap, 'segments': segments, 'distance_m': distance,
        'trajectory': trajectory, 'snapshot_times': snapshot_times,
        'scans': {'file': 'mission/scans.bin', 'count': len(scan_ranges), 'rays': SCAN_RAYS, 'units': 'cm',
                  'meta_fields': ['t', 'x', 'y', 'yaw', 'angle_min', 'angle_increment'], 'meta': scan_meta},
        'cloud': {'file': 'mission/cloud.bin', 'count': int(len(points)),
                  'encoding': 'int16 triples: x cm, y cm, t*10-32768 (s)'},
        'reveal': {'file': 'mission/reveal.png',
                   'encoding': 'cell value k: first known in snapshot k (1-based); 0 never known'},
    }


# ------------------------------------------------------------------ images
def save_png(path: Path, array: np.ndarray) -> None:
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(array).save(path, optimize=True)


def save_photo(source: Path, out: Path, stem: str) -> Optional[dict]:
    from PIL import Image

    if not source.is_file():
        return None
    with Image.open(source) as image:
        image = image.convert('RGB')
        full = image.copy()
        full.thumbnail((PHOTO_WIDTH, PHOTO_WIDTH * 2))
        thumb = image.copy()
        thumb.thumbnail((THUMB_WIDTH, THUMB_WIDTH * 2))
        (out / 'photos').mkdir(parents=True, exist_ok=True)
        full.save(out / 'photos' / f'{stem}.webp', 'WEBP', quality=78, method=6)
        thumb.save(out / 'photos' / f'{stem}_thumb.webp', 'WEBP', quality=72, method=6)
        return {'src': f'photos/{stem}.webp', 'thumb': f'photos/{stem}_thumb.webp', 'w': full.width, 'h': full.height}


# ------------------------------------------------------------------ objectives
OBJECTIVES = {
    'O2': ('Map coverage and wall accuracy', 'map_coverage', 'wall_error'),
    'O3': ('Door signs read', 'ocr_rate'),
    'O4': ('Landmark position error', 'landmark_error'),
    'O5': ('Access zones match the survey', 'access_zone_compare'),
    'O6': ('Route query time', 'route_timing'),
    'O7': ('Routes correct', 'route_timing'),
    'O8': ('Fused against single-sensor estimates', 'fusion_compare'),
}


def build_metrics(run: Path, out: Path) -> dict:
    """Only numbers written by tools/eval are used. A missing file means 'not yet measured', never a guess."""
    eval_dir = run / 'eval'
    found = {}
    if eval_dir.is_dir():
        for path in sorted(eval_dir.glob('*.json')):
            try:
                found[path.stem] = json.loads(path.read_text())
            except json.JSONDecodeError:
                continue
        for png in eval_dir.glob('*.png'):
            (out / 'eval').mkdir(parents=True, exist_ok=True)
            shutil.copyfile(png, out / 'eval' / png.name)

    def plot(tool):
        return f'eval/{tool}.png' if (out / 'eval' / f'{tool}.png').is_file() else None

    def measured(tool):
        return found.get(tool, {}).get('result')

    objectives = {}
    coverage, walls = measured('map_coverage'), measured('wall_error')
    o2 = {'title': OBJECTIVES['O2'][0], 'parts': []}
    if coverage:
        o2['parts'].append({'label': 'Corridor coverage', 'value': coverage['percent'], 'unit': '%',
                            'target': coverage['target_percent'], 'comparator': '>=',
                            'passed': found['map_coverage']['passed'], 'plot': plot('map_coverage'),
                            'detail': {'polygon_m2': coverage['polygon_m2'], 'free_m2': coverage['free_m2']}})
    if walls:
        o2['parts'].append({'label': 'Mean wall error', 'value': walls['stats']['mean'], 'unit': 'm',
                            'target': walls['target_m'], 'comparator': '<=', 'passed': found['wall_error']['passed'],
                            'plot': plot('wall_error'), 'stats': walls['stats'],
                            'histogram': {'bins': walls['histogram'], 'range_m': [0, walls['match_radius_m']]},
                            'detail': {'within_target_percent': walls['within_target_percent'],
                                       'excluded_percent': walls['excluded_percent']}})
    objectives['O2'] = o2
    ocr = measured('ocr_rate')
    objectives['O3'] = {'title': OBJECTIVES['O3'][0], 'parts': [] if not ocr else [{
        'label': 'Signs read correctly', 'value': ocr['percent'], 'unit': '%', 'target': ocr['target_percent'],
        'comparator': '>=', 'passed': found['ocr_rate']['passed'],
        'detail': {'signs': ocr['signs'], 'correct': ocr['correct'], 'missed': ocr['missed'],
                   'false_reads': ocr['false_reads']}}]}
    landmarks = measured('landmark_error')
    objectives['O4'] = {'title': OBJECTIVES['O4'][0], 'parts': [] if not landmarks else [{
        'label': 'Mean landmark error', 'value': landmarks['stats']['mean'], 'unit': 'm', 'target': landmarks['target_m'],
        'comparator': '<=', 'passed': found['landmark_error']['passed'], 'plot': plot('landmark_error'),
        'stats': landmarks['stats'], 'samples': [m['error_m'] for m in landmarks['matches']],
        'detail': {'unmatched': landmarks['unmatched'], 'matches': landmarks['matches']}}]}
    zones = measured('access_zone_compare')
    objectives['O5'] = {'title': OBJECTIVES['O5'][0], 'parts': [] if not zones else [{
        'label': 'Entrance-room pairs that agree', 'value': zones['agreement_percent'], 'unit': '%', 'target': 100.0,
        'comparator': '>=', 'passed': found['access_zone_compare']['passed'],
        'detail': {'pairs': zones['pairs'], 'only_in_map': zones['only_in_map'],
                   'only_in_survey': zones['only_in_survey']}}]}
    timing = measured('route_timing')
    objectives['O6'] = {'title': OBJECTIVES['O6'][0], 'parts': [] if not timing else [{
        'label': 'Slowest route query', 'value': timing['time_stats_s']['maximum'] * 1000.0, 'unit': 'ms',
        'target': timing['target_s'] * 1000.0, 'comparator': '<', 'passed': timing['o6_passed'],
        'plot': plot('route_timing'), 'samples': timing['times_ms'], 'stats': timing['time_stats_s'],
        'detail': {'measured_over': found['route_timing'].get('inputs', {}).get('url')}}]}
    objectives['O7'] = {'title': OBJECTIVES['O7'][0], 'parts': [] if not timing or not timing['routes_judged'] else [{
        'label': 'Routes correct', 'value': timing['routes_correct'], 'unit': f'of {timing["routes_judged"]}',
        'target': math.ceil(timing['target_correct'] * timing['routes_judged']), 'comparator': '>=',
        'passed': timing['o7_passed'], 'detail': {'routes': timing['routes']}}]}
    fusion = measured('fusion_compare')
    objectives['O8'] = {'title': OBJECTIVES['O8'][0], 'parts': [] if not fusion else [{
        'label': 'Mean improvement from fusing', 'value': fusion['improvement']['mean'], 'unit': 'm', 'target': 0.0,
        'comparator': '>', 'passed': found['fusion_compare']['passed'], 'plot': plot('fusion_compare'),
        'stats': fusion['improvement'], 'single': fusion['single'], 'fused': fusion['fused'],
        'detail': {'fused_better': fusion['fused_better'], 'pairs': fusion['pairs']}}]}
    for key, objective in objectives.items():
        parts = objective['parts']
        if not parts:
            objective['status'] = 'not_measured'
        elif any(p['passed'] is False for p in parts):
            objective['status'] = 'fail'
        elif all(p['passed'] is True for p in parts):
            objective['status'] = 'pass'
        else:
            objective['status'] = 'inconclusive'
        objective['sources'] = sorted({tool for tool in OBJECTIVES[key][1:] if tool in found})
    return {'objectives': objectives,
            'written_at': {k: v.get('written_at') for k, v in found.items()}}


# ------------------------------------------------------------------ the database
def build_places(db: Path, run: Path, out: Path, t0: float) -> dict:
    landmarks = query(db, 'SELECT * FROM landmarks ORDER BY id')
    observations = query(db, 'SELECT * FROM observations ORDER BY stamp, id')
    photos = {p['id']: p for p in query(db, 'SELECT * FROM photos')}
    entrances = query(db, 'SELECT * FROM entrances ORDER BY id')
    junctions = query(db, 'SELECT * FROM junctions ORDER BY id')
    edges = query(db, 'SELECT * FROM junction_edges')
    zone_rows = query(db, 'SELECT * FROM access_zones')
    zone_junction_rows = query(db, 'SELECT * FROM zone_junctions')
    photo_dir = run / 'photos'

    def photo(photo_id):
        if photo_id is None or photo_id not in photos:
            return None
        # Paths were stored on the robot, so only the file name is used.
        return save_photo(photo_dir / Path(photos[photo_id]['path'].replace('\\', '/')).name, out, f'p{photo_id}')

    def rel(t):
        return None if t is None else t - t0

    by_landmark: dict[int, list] = {}
    for o in observations:
        by_landmark.setdefault(o['landmark_id'], []).append([rel(o['stamp']), o['x'], o['y'], o['confidence']])
    landmark_out = []
    for lm in landmarks:
        landmark_out.append({
            'id': lm['id'], 'class': lm['class'], 'text': lm['text'], 'x': lm['x'], 'y': lm['y'], 'z': lm['z'],
            'sd': [math.sqrt(max(lm['var_x'], 0)), math.sqrt(max(lm['var_y'], 0))], 'confidence': lm['confidence'],
            'count': lm['observation_count'], 'first_seen_s': rel(lm['first_seen']), 'last_seen_s': rel(lm['last_seen']),
            'photo': photo(lm['photo_id']), 'observations': by_landmark.get(lm['id'], [])})
    junction_out = [{'id': j['id'], 'x': j['x'], 'y': j['y'], 'photo': photo(j['photo_id']),
                     'taken_s': rel(photos[j['photo_id']]['taken_at']) if j['photo_id'] in photos else None}
                    for j in junctions]
    zones = {e['id']: {'rooms': sorted({lm['text'] for lm in landmarks for z in zone_rows
                                         if z['entrance_id'] == e['id'] and z['landmark_id'] == lm['id'] and lm['text']}),
                       'landmarks': sorted(z['landmark_id'] for z in zone_rows if z['entrance_id'] == e['id']),
                       'junctions': sorted(z['junction_id'] for z in zone_junction_rows if z['entrance_id'] == e['id'])}
             for e in entrances}
    rooms = {}
    for lm in landmarks:
        if lm['text']:
            rooms.setdefault(lm['text'], {'room': lm['text'], 'x': lm['x'], 'y': lm['y'], 'landmark_id': lm['id'],
                                          'entrances': sorted(e for e, z in zones.items() if lm['id'] in z['landmarks'])})
    graph = {'entrances': [{k: e[k] for k in ('id', 'name', 'x', 'y', 'yaw')} for e in entrances],
             'junctions': junction_out, 'edges': [[e['a'], e['b'], e['length_m']] for e in edges],
             'zones': zones, 'rooms': sorted(rooms.values(), key=lambda r: r['room'])}
    routes = build_routes(graph, landmarks)
    return {'graph': graph, 'landmarks': landmark_out, 'routes': routes}


def build_routes(graph: dict, landmarks: list[dict]) -> dict:
    """Every reachable room from every entrance, with the same algorithm as the API's /route, so the static site and
    the server always agree. Rooms whose route cannot be found are listed, not hidden."""
    junction_by_id = {j['id']: j for j in graph['junctions']}
    edges = [tuple(e) for e in graph['edges']]
    features = [(lm['class'], lm['x'], lm['y']) for lm in landmarks]
    out: dict[str, dict] = {}
    for entrance in graph['entrances']:
        zone = graph['zones'][entrance['id']]
        allowed = [Junction(j, junction_by_id[j]['x'], junction_by_id[j]['y']) for j in zone['junctions']
                   if j in junction_by_id]
        start = nearest_junction(allowed, entrance['x'], entrance['y'])
        routes, unreachable = {}, []
        for room in graph['rooms']:
            if entrance['id'] not in room['entrances']:
                continue
            goal = nearest_junction(allowed, room['x'], room['y'])
            found = shortest_path(edges, {j.id for j in allowed}, start.id, goal.id) if start and goal else None
            if not found:
                unreachable.append(room['room'])
                continue
            ids, length = found
            path = [Junction(i, junction_by_id[i]['x'], junction_by_id[i]['y']) for i in ids]
            steps = describe_steps_rich(path, room['room'], (entrance['x'], entrance['y']), (room['x'], room['y']),
                                        features)
            previous = (entrance['x'], entrance['y'])
            out_steps = []
            for junction, step in zip(path, steps):
                out_steps.append({'junction_id': junction.id, 'x': junction.x, 'y': junction.y, **step,
                                  'distance_m': math.hypot(junction.x - previous[0], junction.y - previous[1]),
                                  'photo': junction_by_id[junction.id]['photo']})
                previous = (junction.x, junction.y)
            walk = math.hypot(entrance['x'] - path[0].x, entrance['y'] - path[0].y) + length + \
                math.hypot(room['x'] - path[-1].x, room['y'] - path[-1].y)
            routes[room['room']] = {'length_m': walk, 'graph_length_m': length, 'steps': out_steps,
                                    'turns': sum(1 for s in steps if s['turn'] in ('left', 'right', 'back')),
                                    'destination': {'x': room['x'], 'y': room['y']}}
        out[entrance['id']] = {'routes': routes, 'unreachable': unreachable}
    return out


# ------------------------------------------------------------------ main
def import_run(run: Path, out_root: Path = DATA_ROOT, run_id: Optional[str] = None, name: Optional[str] = None,
               map_yaml: Optional[Path] = None, make_default: bool = True) -> Path:
    run = run.expanduser().resolve()
    db = run / 'merz.sqlite'
    if not db.is_file():
        found = sorted(run.glob('*.sqlite'))
        if not found:
            raise SystemExit(f'No merz.sqlite in {run}')
        db = found[0]
    meta = {r['key']: r['value'] for r in query(db, 'SELECT key, value FROM meta')}
    sample = meta.get('sample_data') == 'true' or meta.get('synthetic_run') == 'true'
    name = name or meta.get('run_name') or run.name
    run_id = slug(run_id or name)
    out = out_root / run_id
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    saved = choose_map(run, map_yaml)
    bags = [read_bag(folder) for folder in bag_folders(run)]
    stamps = [r['first_seen'] for r in query(db, 'SELECT first_seen FROM landmarks WHERE first_seen IS NOT NULL')]
    t0 = min([b['poses'][0][0] for b in bags if b['poses']] or stamps or [0.0])
    # Offsets between the bag timeline (with runs placed back to back) and robot time, per run.
    mission = mission_from_bags(bags, saved, out)
    places = build_places(db, run, out, t0)
    if mission:
        place_on_timeline(places, mission, bags)

    # Map images: the full grid and two smaller levels for fast first paint on phones.
    levels = []
    for factor in (4, 2, 1):
        name_png = f'map/state_{factor}x.png'
        save_png(out / name_png, saved.state if factor == 1 else downsample(saved.state, factor))
        levels.append({'file': name_png, 'factor': factor})
    walls = wall_boxes(saved)
    write_json(out / 'map' / 'walls.json', walls, 3)
    map_info = {'resolution': saved.resolution, 'origin': [saved.origin_x, saved.origin_y], 'width': saved.width,
                'height': saved.height, 'levels': levels, 'walls': 'map/walls.json',
                'values': {'unknown': UNKNOWN, 'free': FREE, 'occupied': OCCUPIED}, 'source': saved.yaml_path.name}
    # The API (FastAPI) needs the original database and map, so keep a copy beside the bundle.
    api = out / 'api'
    api.mkdir()
    shutil.copyfile(db, api / 'merz.sqlite')
    info = yaml.safe_load(saved.yaml_path.read_text())
    shutil.copyfile(saved.yaml_path.parent / info['image'], api / 'map.pgm')
    info['image'] = 'map.pgm'
    (api / 'map.yaml').write_text(yaml.safe_dump(info, sort_keys=False))

    metrics = build_metrics(run, out)
    rooms = places['graph']['rooms']
    o4 = metrics['objectives']['O4']['parts']
    stats = {
        'metres_explored': mission['distance_m'] if mission else None,
        'duration_s': mission['duration_s'] if mission else None,
        'signs_read': sum(1 for lm in places['landmarks'] if lm['class'] == 'room_sign' and lm['text']),
        'rooms_mapped': len(rooms), 'landmarks': len(places['landmarks']), 'junctions': len(places['graph']['junctions']),
        'entrances': len(places['graph']['entrances']),
        'mapped_area_m2': float(np.count_nonzero(saved.state == FREE)) * saved.resolution ** 2,
        'landmark_error_m': o4[0]['value'] if o4 else None,
    }
    manifest = {
        'format': FORMAT_VERSION, 'run_id': run_id, 'name': name, 'sample': sample,
        'imported_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'recorded_at': datetime.fromtimestamp(t0, timezone.utc).isoformat(timespec='seconds') if t0 else None,
        'source': {'database': db.name, 'map': saved.yaml_path.name, 'bags': [b['folder'] for b in bags]},
        'stats': stats, 'map': map_info,
        'files': {'graph': 'graph.json', 'routes': 'routes.json', 'landmarks': 'landmarks.json',
                  'metrics': 'metrics.json', 'mission': 'mission.json' if mission else None},
    }
    write_json(out / 'graph.json', places['graph'])
    write_json(out / 'routes.json', places['routes'])
    write_json(out / 'landmarks.json', places['landmarks'])
    write_json(out / 'metrics.json', metrics, 4)
    if mission:
        write_json(out / 'mission.json', mission, 3)
    write_json(out / 'manifest.json', manifest, 4)
    update_index(out_root, manifest, make_default)
    return out


def place_on_timeline(places: dict, mission: dict, bags: list[dict]) -> None:
    """Database times are robot time; the replay uses the bag timeline with runs placed back to back."""
    windows = []
    for bag, segment in zip([b for b in bags if b['poses']], mission['segments']):
        windows.append((bag['poses'][0][0], bag['poses'][-1][0], segment['start_s']))
    t0 = min(w[0] for w in windows)

    def convert(rel_t):
        if rel_t is None:
            return None
        t = rel_t + t0
        for start, end, offset in windows:
            if start - 1 <= t <= end + 1:
                return offset + (t - start)
        return rel_t

    for lm in places['landmarks']:
        lm['first_seen_s'] = convert(lm['first_seen_s'])
        lm['last_seen_s'] = convert(lm['last_seen_s'])
        for o in lm['observations']:
            o[0] = convert(o[0])
    for j in places['graph']['junctions']:
        j['taken_s'] = convert(j['taken_s'])


def update_index(out_root: Path, manifest: dict, make_default: bool) -> None:
    index_path = out_root / 'index.json'
    index = json.loads(index_path.read_text()) if index_path.is_file() else {'default': None, 'runs': []}
    index['runs'] = [r for r in index['runs'] if r['id'] != manifest['run_id']]
    index['runs'].append({'id': manifest['run_id'], 'name': manifest['name'], 'sample': manifest['sample'],
                          'recorded_at': manifest['recorded_at']})
    index['runs'] = [r for r in index['runs'] if (out_root / r['id'] / 'manifest.json').is_file()]
    if make_default or not index['default']:
        index['default'] = manifest['run_id']
    write_json(index_path, index)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run', type=Path, help='Run folder (a copy of ~/merz_data)')
    parser.add_argument('--run-id', help='Folder name under web/data (default: from the run name)')
    parser.add_argument('--name', help='Name shown on the website')
    parser.add_argument('--map', type=Path, help='Use this map .yaml instead of the most complete one')
    parser.add_argument('--out', type=Path, default=DATA_ROOT, help='Bundle root (default web/data)')
    parser.add_argument('--keep-default', action='store_true', help='Do not make this run the default')
    args = parser.parse_args()
    out = import_run(args.run, args.out, args.run_id, args.name, args.map, not args.keep_default)
    size = sum(p.stat().st_size for p in out.rglob('*') if p.is_file()) / 1e6
    print(f'Wrote {out} ({size:.1f} MB)')


if __name__ == '__main__':
    main()
