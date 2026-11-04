"""Make a realistic SYNTHETIC rover run, in exactly the formats the rover code writes, so the website importer can be
built and tested before the rover has run. Nothing here is a measurement.

    python tools/synthetic_run/make_synthetic_run.py data/synthetic_run
    python tools/web_import.py data/synthetic_run

The output folder looks like the rover's ~/merz_data after two entrance runs:

    merz.sqlite                   docs/DATABASE_SCHEMA.md (written with merz_semantic_map.database)
    maps/run_north.yaml + .pgm    map_saver / slam_toolbox save_map format
    maps/run_south.yaml + .pgm
    photos/junction_<sec>_<nsec>.jpg, photos/sign_<id>_<sec>.jpg
    bags/<stamp>_<entrance>/      rosbag2, mcap storage: /scan /tf /tf_static /odometry/filtered /map
    ground_truth/*.csv            inputs for tools/eval (made from the invented building)
    eval/*.json + *.png           outputs of tools/eval --json --plot, run on this data

Access zones are computed with the rover's own merz_exploration.compute_access_zones code on the saved maps, and the
objective numbers come from the real tools/eval scripts. They describe the simulator, not the robot.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import math
from pathlib import Path
import random
import shutil
import socket
import subprocess
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / 'ros2_ws' / 'src' / 'merz_semantic_map'))
sys.path.insert(0, str(REPO / 'ros2_ws' / 'src' / 'merz_exploration'))
sys.path.insert(0, str(REPO / 'web'))

from building import RESOLUTION, Building, make_building, rasterise, wall_segments  # noqa: E402
from photos import Features, corridor_photo, sign_crop  # noqa: E402
from simulate import LASER_OFFSET, RunLog, World, odometry, simulate_run  # noqa: E402

START = datetime(2026, 12, 4, 10, 15, tzinfo=timezone.utc).timestamp()     # an invented date for the invented run
ROBOT_PHOTO_DIR = '/home/merz/merz_data/photos'                              # paths are stored as the robot saw them


# ------------------------------------------------------------------ geometry helpers
def compose(a, b):
    ax, ay, at = a
    bx, by, bt = b
    return ax + math.cos(at) * bx - math.sin(at) * by, ay + math.sin(at) * bx + math.cos(at) * by, at + bt


def invert(a):
    x, y, t = a
    return -math.cos(t) * x - math.sin(t) * y, math.sin(t) * x - math.cos(t) * y, -t


# ------------------------------------------------------------------ rosbag2 writing
def write_bag(folder: Path, log: RunLog, odom: list[tuple[float, float, float]]) -> None:
    from rosbags.rosbag2 import StoragePlugin, Writer
    from rosbags.typesys import Stores, get_typestore

    ts = get_typestore(Stores.ROS2_HUMBLE)
    T = ts.types
    Time, Header = T['builtin_interfaces/msg/Time'], T['std_msgs/msg/Header']
    Vector3, Quaternion = T['geometry_msgs/msg/Vector3'], T['geometry_msgs/msg/Quaternion']
    Point, Pose = T['geometry_msgs/msg/Point'], T['geometry_msgs/msg/Pose']

    def stamp(t: float):
        sec = int(t)
        return Time(sec=sec, nanosec=int(round((t - sec) * 1e9)) % 1_000_000_000)

    def quat(yaw: float):
        return Quaternion(x=0.0, y=0.0, z=math.sin(yaw / 2), w=math.cos(yaw / 2))

    def tf(t, parent, child, x, y, z, yaw):
        return T['geometry_msgs/msg/TransformStamped'](
            header=Header(stamp=stamp(t), frame_id=parent), child_frame_id=child,
            transform=T['geometry_msgs/msg/Transform'](translation=Vector3(x=x, y=y, z=z), rotation=quat(yaw)))

    def ns(t: float) -> int:
        return int(round(t * 1e9))

    if folder.exists():
        shutil.rmtree(folder)
    with Writer(folder, version=8, storage_plugin=StoragePlugin.MCAP) as writer:
        c_scan = writer.add_connection('/scan', 'sensor_msgs/msg/LaserScan', typestore=ts)
        c_tf = writer.add_connection('/tf', 'tf2_msgs/msg/TFMessage', typestore=ts)
        c_static = writer.add_connection('/tf_static', 'tf2_msgs/msg/TFMessage', typestore=ts)
        c_odom = writer.add_connection('/odometry/filtered', 'nav_msgs/msg/Odometry', typestore=ts)
        c_map = writer.add_connection('/map', 'nav_msgs/msg/OccupancyGrid', typestore=ts)
        TF = T['tf2_msgs/msg/TFMessage']
        t0 = log.poses[0].t
        writer.write(c_static, ns(t0), ts.serialize_cdr(TF(transforms=[
            tf(t0, 'base_link', 'laser', *LASER_OFFSET, 0.0),
            tf(t0, 'base_link', 'camera_link', 0.12, 0.0, 0.95, 0.0)]), 'tf2_msgs/msg/TFMessage'))
        events = [(s.t, 'pose', i) for i, s in enumerate(log.poses)]
        events += [(t, 'scan', i) for i, (t, _r) in enumerate(log.scans)]
        events += [(m[0], 'map', i) for i, m in enumerate(log.maps)]
        events.sort(key=lambda e: (e[0], e[1]))
        Odometry = T['nav_msgs/msg/Odometry']
        for t, kind, i in events:
            if kind == 'pose':
                s = log.poses[i]
                ox, oy, oyaw = odom[i]
                map_to_odom = compose((s.x, s.y, s.yaw), invert((ox, oy, oyaw)))
                writer.write(c_tf, ns(t), ts.serialize_cdr(TF(transforms=[
                    tf(t, 'map', 'odom', map_to_odom[0], map_to_odom[1], 0.0, map_to_odom[2]),
                    tf(t, 'odom', 'base_link', ox, oy, 0.0, oyaw)]), 'tf2_msgs/msg/TFMessage'))
                covariance = np.zeros(36)
                covariance[[0, 7, 35]] = [0.02, 0.02, 0.01]
                msg = Odometry(
                    header=Header(stamp=stamp(t), frame_id='odom'), child_frame_id='base_link',
                    pose=T['geometry_msgs/msg/PoseWithCovariance'](
                        pose=Pose(position=Point(x=ox, y=oy, z=0.0), orientation=quat(oyaw)), covariance=covariance),
                    twist=T['geometry_msgs/msg/TwistWithCovariance'](
                        twist=T['geometry_msgs/msg/Twist'](linear=Vector3(x=s.vx, y=0.0, z=0.0),
                                                           angular=Vector3(x=0.0, y=0.0, z=s.wz)),
                        covariance=np.zeros(36)))
                writer.write(c_odom, ns(t), ts.serialize_cdr(msg, 'nav_msgs/msg/Odometry'))
            elif kind == 'scan':
                ranges = log.scans[i][1]
                msg = T['sensor_msgs/msg/LaserScan'](
                    header=Header(stamp=stamp(t), frame_id='laser'), angle_min=-math.pi,
                    angle_max=math.pi - 2 * math.pi / len(ranges), angle_increment=2 * math.pi / len(ranges),
                    time_increment=0.0, scan_time=0.1, range_min=0.05, range_max=15.0, ranges=ranges,
                    intensities=np.zeros(0, dtype=np.float32))
                writer.write(c_scan, ns(t), ts.serialize_cdr(msg, 'sensor_msgs/msg/LaserScan'))
            else:
                _t, cells, ox, oy = log.maps[i]
                h, w = cells.shape
                msg = T['nav_msgs/msg/OccupancyGrid'](
                    header=Header(stamp=stamp(t), frame_id='map'),
                    info=T['nav_msgs/msg/MapMetaData'](map_load_time=stamp(t), resolution=RESOLUTION, width=w,
                                                       height=h, origin=Pose(position=Point(x=ox, y=oy, z=0.0),
                                                                             orientation=quat(0.0))),
                    data=cells.ravel().astype(np.int8))
                writer.write(c_map, ns(t), ts.serialize_cdr(msg, 'nav_msgs/msg/OccupancyGrid'))


# ------------------------------------------------------------------ map_saver output
def save_map(prefix: Path, cells: np.ndarray, ox: float, oy: float) -> Path:
    from PIL import Image

    pixels = np.full(cells.shape, 205, dtype=np.uint8)
    pixels[cells == 0] = 254
    pixels[cells == 100] = 0
    prefix.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.flipud(pixels)).save(prefix.with_suffix('.pgm'))
    yaml_path = prefix.with_suffix('.yaml')
    yaml_path.write_text(f'image: {prefix.name}.pgm\nmode: trinary\nresolution: {RESOLUTION}\n'
                         f'origin: [{ox:.3f}, {oy:.3f}, 0]\nnegate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.25\n')
    return yaml_path


# ------------------------------------------------------------------ database
def write_database(out: Path, b: Building, logs: dict[str, RunLog], maps: dict[str, Path], rng: random.Random) -> None:
    from merz_exploration.compute_access_zones import store_zone
    from merz_semantic_map.database import MerzDatabase

    db_path = out / 'merz.sqlite'
    db_path.unlink(missing_ok=True)
    photo_dir = out / 'photos'
    photo_dir.mkdir(parents=True, exist_ok=True)
    room_signs = [i for i, lm in enumerate(b.landmarks) if lm.cls == 'room_sign']
    misread = {room_signs[5]: 'S1.O6', room_signs[22]: 'S2.1l'}           # letter O and lower-case l: classic OCR
    unread = {room_signs[17]}
    letter_to_id: dict[str, int] = {}
    with MerzDatabase(db_path) as db:
        db.set_meta('sample_data', 'true')
        db.set_meta('synthetic_run', 'true')
        db.set_meta('run_name', 'Synthetic two-entrance survey')
        for name in ('north', 'south'):
            log = logs[name]
            for jid, t, x, y, yaw in log.junction_visits:
                sec, nsec = int(t), int((t % 1) * 1e9)
                path = f'{ROBOT_PHOTO_DIR}/junction_{sec}_{nsec}.jpg'
                photo_id = db.add_photo(path, round(x, 3), round(y, 3), None, t)
                letter_to_id[jid] = db.add_junction(round(x, 3), round(y, 3), photo_id)
                junction_features = features_for(b, jid, yaw, rng)
                corridor_photo(photo_dir / Path(path).name, junction_features, seed=sum(map(ord, jid)) * 7,
                               label=f'junction {letter_to_id[jid]}')
            for a, c in b.edges:
                if a in letter_to_id and c in letter_to_id and a in b.zones[name]:
                    ja, jc = b.junctions[a], b.junctions[c]
                    db.add_junction_edge(letter_to_id[a], letter_to_id[c], round(math.hypot(ja[0] - jc[0], ja[1] - jc[1]), 2))
        # Landmarks, numbered in the order they were first seen, as landmark_node does.
        observations = sorted([o for name in ('north', 'south') for o in logs[name].observations], key=lambda o: o.stamp)
        order: list[int] = []
        for o in observations:
            if o.truth_index not in order:
                order.append(o.truth_index)
        for landmark_id, truth_index in enumerate(order, start=1):
            truth = b.landmarks[truth_index]
            seen = [o for o in observations if o.truth_index == truth_index]
            xyz = np.array([[o.x, o.y, o.z] for o in seen])
            mean = xyz.mean(axis=0)
            var = xyz.var(axis=0) / len(seen) + 0.0025
            text = truth.text
            if truth_index in misread:
                text = misread[truth_index]
            elif truth_index in unread:
                text = ''
            photo_id = None
            if truth.cls == 'room_sign':
                sec = int(seen[0].stamp)
                path = f'{ROBOT_PHOTO_DIR}/sign_{landmark_id}_{sec}.jpg'
                sign_crop(photo_dir / Path(path).name, truth.text, seed=landmark_id)
                photo_id = db.add_photo(path, float(mean[0]), float(mean[1]), None, seen[0].stamp)
            db.upsert_landmark(landmark_id, truth.cls, text, tuple(float(v) for v in mean),
                               tuple(float(v) for v in var), float(np.mean([o.confidence for o in seen])), len(seen),
                               first_seen=seen[0].stamp, last_seen=seen[-1].stamp, photo_id=photo_id)
            for o in seen:
                db.add_observation(landmark_id, (o.x, o.y, o.z), depth_m=o.depth, confidence=o.confidence,
                                   stamp=o.stamp)
    # Access zones with the rover's own code, on the map saved at the end of each entrance run.
    for name in ('north', 'south'):
        label, x, y, yaw = b.entrances[name]
        store_zone(maps[name], db_path, name, label, x, y, yaw)


def features_for(b: Building, jid: str, yaw: float, rng: random.Random) -> Features:
    """What a camera facing along the robot's heading would see at this junction."""
    jx, jy = b.junctions[jid]
    left = right = None
    for a, c in b.edges:
        if jid not in (a, c):
            continue
        other = b.junctions[c if a == jid else a]
        bearing = math.atan2(other[1] - jy, other[0] - jx) - yaw
        bearing = math.atan2(math.sin(bearing), math.cos(bearing))
        if 0.6 < bearing < 2.5:
            left = (0.9, 3.3)
        elif -2.5 < bearing < -0.6:
            right = (0.9, 3.3)
    near = [lm for lm in b.landmarks if math.hypot(lm.x - jx, lm.y - jy) < 6.0]
    lift = next((lm for lm in near if lm.cls == 'lift'), None)
    lift_side = None
    if lift:
        bearing = math.atan2(lift.y - jy, lift.x - jx) - yaw
        lift_side = 'left' if math.sin(bearing) > 0 else 'right'
    plates = tuple(lm.text for lm in sorted(near, key=lambda lm: math.hypot(lm.x - jx, lm.y - jy))
                   if lm.cls == 'room_sign')[:2]
    return Features(left_opening=left, right_opening=right, end_open=rng.random() < 0.4, lift=lift_side,
                    noticeboard=None if lift_side else rng.choice(['left', 'right', None]),
                    exit_sign=any(lm.cls == 'exit_sign' for lm in near),
                    stairs=any(lm.cls == 'stairs' for lm in near), doors=rng.randint(3, 6), plates=plates,
                    tint=rng.choice([(226, 224, 216), (214, 222, 226), (230, 222, 206), (220, 226, 214)]))


# ------------------------------------------------------------------ ground truth and evaluation
def write_ground_truth(out: Path, b: Building, junction_ids: dict[str, int]) -> Path:
    folder = out / 'ground_truth'
    folder.mkdir(parents=True, exist_ok=True)

    def write(name, header, rows):
        with open(folder / name, 'w', newline='') as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(rows)

    write('corridor.csv', ['x', 'y'], [(0.0, 18.8), (0.0, 21.2), (-49.2, 21.2), (-49.2, 18.8)])
    write('walls.csv', ['x1', 'y1', 'x2', 'y2'], [tuple(round(v, 3) for v in s) for s in wall_segments(b)])
    write('signs.csv', ['text'], [(r.number,) for r in b.rooms])
    write('truth.csv', ['class', 'text', 'x', 'y'], [(lm.cls, lm.text, lm.x, lm.y) for lm in b.landmarks])
    write('survey.csv', ['entrance', 'room', 'reachable'],
          [(e, r.number, 'yes' if r.zone == e else 'no') for e in ('north', 'south') for r in b.rooms])
    # Ten routes "walked by hand": shortest paths over the invented corridor graph, by junction id.
    from app.routing import Junction, nearest_junction, shortest_path
    picks = [('north', 'S1.03'), ('north', 'S1.07'), ('north', 'S1.10'), ('north', 'S1.13'), ('north', 'S1.14'),
             ('south', 'S2.02'), ('south', 'S2.08'), ('south', 'S2.12'), ('south', 'S2.15'), ('south', 'S2.10')]
    rows = []
    for entrance, number in picks:
        room = next(r for r in b.rooms if r.number == number)
        allowed = [Junction(junction_ids[j], *b.junctions[j]) for j in b.zones[entrance]]
        _label, ex, ey, _yaw = b.entrances[entrance]
        first = nearest_junction(allowed, ex, ey)
        last = nearest_junction(allowed, *room.sign_xy)
        edges = [(junction_ids[a], junction_ids[c], 1.0 * math.dist(b.junctions[a], b.junctions[c])) for a, c in b.edges]
        path, _length = shortest_path(edges, {j.id for j in allowed}, first.id, last.id)
        rows.append((entrance, number, ' '.join(map(str, path))))
    write('routes.csv', ['entrance', 'room', 'expected'], rows)
    return folder


def free_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def run_evaluation(out: Path, truth: Path, final_map: Path) -> None:
    eval_dir = out / 'eval'
    eval_dir.mkdir(exist_ok=True)
    tools = REPO / 'tools' / 'eval'
    db = out / 'merz.sqlite'
    jobs = [
        ['map_coverage.py', '--map', final_map, '--polygon', truth / 'corridor.csv'],
        ['wall_error.py', '--map', final_map, '--walls', truth / 'walls.csv', '--match-radius', '0.5'],
        ['ocr_rate.py', '--truth', truth / 'signs.csv', '--database', db],
        ['landmark_error.py', '--truth', truth / 'truth.csv', '--database', db, '--gate', '2.0'],
        ['access_zone_compare.py', '--survey', truth / 'survey.csv', '--database', db],
        ['fusion_compare.py', '--truth', truth / 'truth.csv', '--database', db, '--gate', '2.0'],
    ]
    for job in jobs:
        stem = job[0].removesuffix('.py')
        extra = ['--json', eval_dir / f'{stem}.json']
        if stem not in ('ocr_rate', 'access_zone_compare'):
            extra += ['--plot', eval_dir / f'{stem}.png']
        subprocess.run([sys.executable, tools / job[0], *map(str, job[1:]), *map(str, extra)], check=True,
                       stdout=subprocess.DEVNULL)
    # O6/O7 need the website running, as in docs/EXPERIMENTS.md. Here it runs on this machine, over localhost.
    port = free_port()
    env = {**__import__('os').environ, 'MERZ_DB': str(db), 'MERZ_PHOTOS': str(out / 'photos'), 'MERZ_MAP': str(final_map)}
    server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--port', str(port), '--log-level',
                               'warning'], cwd=REPO / 'web', env=env)
    try:
        from urllib.request import urlopen
        for _ in range(300):
            try:
                with urlopen(f'http://127.0.0.1:{port}/entrances', timeout=1) as reply:
                    if reply.status == 200:
                        break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError('The website did not start for the route timing test')
        result = subprocess.run([sys.executable, tools / 'route_timing.py', '--url', f'http://127.0.0.1:{port}',
                                 '--routes', str(truth / 'routes.csv'), '--repeats', '20', '--json',
                                 str(eval_dir / 'route_timing.json'), '--plot', str(eval_dir / 'route_timing.png')],
                                capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(f'route_timing.py failed:\n{result.stdout}\n{result.stderr}')
    finally:
        server.terminate()
        server.wait(timeout=10)


# ------------------------------------------------------------------ main
def build(out: Path, evaluate: bool = True, seed: int = 3094) -> Path:
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    b = make_building(seed)
    solid, ox, oy = rasterise(b)
    world = World(solid, ox, oy)
    logs: dict[str, RunLog] = {}
    maps: dict[str, Path] = {}
    t0 = START
    for k, name in enumerate(('north', 'south')):
        print(f'Simulating the {name} entrance run...')
        log = simulate_run(name, b, world, t0, seed + k)
        logs[name] = log
        odom = odometry(log.poses, seed + k, start=(0.0, 0.0, 0.0))
        stamp = datetime.fromtimestamp(log.poses[0].t, timezone.utc).strftime('%Y%m%d_%H%M%S')
        write_bag(out / 'bags' / f'{stamp}_{name}', log, odom)
        _t, cells, mx, my = log.maps[-1]
        maps[name] = save_map(out / 'maps' / f'run_{name}', cells, mx, my)
        t0 = log.poses[-1].t + 900.0           # carried to the next entrance: 15 minutes later
    print('Writing the database, photos and access zones...')
    write_database(out, b, logs, maps, rng)
    from merz_semantic_map.database import MerzDatabase
    with MerzDatabase(out / 'merz.sqlite') as db:
        positions = {(round(j['x'], 3), round(j['y'], 3)): j['id'] for j in db.junctions()}
    junction_ids = {}
    for name in ('north', 'south'):
        for jid, _t, x, y, _yaw in logs[name].junction_visits:
            junction_ids[jid] = positions[(round(x, 3), round(y, 3))]
    truth = write_ground_truth(out, b, junction_ids)
    if evaluate:
        print('Running tools/eval on the synthetic data...')
        run_evaluation(out, truth, maps['south'])
    (out / 'README.txt').write_text('SYNTHETIC rover run made by tools/synthetic_run/make_synthetic_run.py.\n'
                                    'The building, the robot and every number here are invented.\n')
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('out', type=Path, nargs='?', default=REPO / 'data' / 'synthetic_run')
    parser.add_argument('--no-eval', action='store_true', help='Skip running tools/eval (faster).')
    args = parser.parse_args()
    started = time.time()
    build(args.out, evaluate=not args.no_eval)
    print(f'Wrote {args.out} in {time.time() - started:.0f} s')


if __name__ == '__main__':
    main()
