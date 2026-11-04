"""Tests for tools/web_import.py, the eval --json outputs and the static export. No ROS needed.

A small run is built in exactly the rover's formats: a short simulated drive written as an mcap rosbag2 (/scan, /tf,
/tf_static, /odometry/filtered, /map), a map_saver map, and a database written with merz_semantic_map.database.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'tools'))
sys.path.insert(0, str(REPO / 'tools' / 'synthetic_run'))
sys.path.insert(0, str(REPO / 'ros2_ws' / 'src' / 'merz_semantic_map'))
sys.path.insert(0, str(REPO / 'web'))

pytest.importorskip('rosbags')
pytest.importorskip('PIL')

import web_import  # noqa: E402
from building import make_building, rasterise  # noqa: E402
from make_synthetic_run import save_map, write_bag  # noqa: E402
from simulate import World, odometry, simulate_run  # noqa: E402

T0 = 1_796_379_300.0


@pytest.fixture(scope='module')
def run(tmp_path_factory):
    """A 20 m drive from the north entrance, then a database, photos and one eval result."""
    from PIL import Image
    from merz_semantic_map.database import MerzDatabase

    root = tmp_path_factory.mktemp('run')
    b = make_building()
    b.tours['north'] = [(4.0, 20.0), (-14.0, 20.0), (-14.0, 13.0)]
    world = World(*rasterise(b))
    log = simulate_run('north', b, world, T0, seed=1)
    odom = odometry(log.poses, 1, start=(0.0, 0.0, 0.0))
    write_bag(root / 'bags' / 'test_north', log, odom)
    _t, cells, ox, oy = log.maps[-1]
    maps = root / 'maps'
    save_map(maps / 'run_north', cells, ox, oy)
    # A smaller, older map: the importer must pick the more complete one.
    save_map(maps / 'aaa_partial', cells[:40, :40], ox, oy)
    photos = root / 'photos'
    photos.mkdir()
    for name in ('junction_1_0.jpg', 'junction_2_0.jpg', 'sign_1_0.jpg'):
        Image.new('RGB', (800, 500), (120, 130, 140)).save(photos / name)
    with MerzDatabase(root / 'merz.sqlite') as db:
        db.set_meta('sample_data', 'true')
        db.upsert_entrance('north', 'North entrance', 3.0, 20.0, math.pi)
        p1 = db.add_photo('/home/merz/merz_data/photos/junction_1_0.jpg', -1.5, 20.0, None, T0 + 10)
        p2 = db.add_photo('C:\\robot\\photos\\junction_2_0.jpg', -14.0, 20.0, None, T0 + 40)
        p3 = db.add_photo('/home/merz/merz_data/photos/sign_1_0.jpg', -9.0, 21.0, None, T0 + 20)
        j1 = db.add_junction(-1.5, 20.0, p1)
        j2 = db.add_junction(-14.0, 20.0, p2)
        db.add_junction_edge(j1, j2, 12.5)
        db.upsert_landmark(1, 'room_sign', 'S1.02', (-8.15, 21.15, 1.5), (0.01, 0.02, 0.01), 0.9, 2,
                           first_seen=T0 + 20, last_seen=T0 + 21, photo_id=p3)
        db.upsert_landmark(2, 'lift', '', (-13.0, 21.1, 1.2), (0.01, 0.01, 0.01), 0.8, 1, first_seen=T0 + 30, last_seen=T0 + 30)
        db.add_observation(1, (-8.1, 21.1, 1.5), confidence=0.9, stamp=T0 + 20)
        db.add_observation(1, (-8.2, 21.2, 1.5), confidence=0.9, stamp=T0 + 21)
        db.add_observation(2, (-13.0, 21.1, 1.2), confidence=0.8, stamp=T0 + 30)
        db.set_access_zone('north', [1, 2], [j1, j2])
    sys.path.insert(0, str(REPO / 'tools' / 'eval'))
    from common import write_json
    write_json(root / 'eval' / 'map_coverage.json', 'O2', 'map_coverage', True,
               {'polygon_m2': 100.0, 'free_m2': 95.0, 'percent': 95.0, 'target_percent': 90.0}, {})
    return {'root': root, 'log': log}


@pytest.fixture(scope='module')
def bundle(run, tmp_path_factory):
    out_root = tmp_path_factory.mktemp('data')
    out = web_import.import_run(run['root'], out_root, run_id='Test Run')
    return out


def load(path: Path):
    return json.loads(path.read_text())


def test_bundle_has_every_file(bundle):
    manifest = load(bundle / 'manifest.json')
    assert bundle.name == 'test-run' and manifest['run_id'] == 'test-run'
    assert manifest['sample'] is True
    for name in manifest['files'].values():
        assert (bundle / name).is_file(), name
    for level in manifest['map']['levels']:
        assert (bundle / level['file']).is_file()
    for name in ('api/merz.sqlite', 'api/map.yaml', 'api/map.pgm', 'mission/reveal.png', 'mission/scans.bin',
                 'mission/cloud.bin', 'map/walls.json'):
        assert (bundle / name).is_file(), name
    index = load(bundle.parent / 'index.json')
    assert index['default'] == 'test-run' and index['runs'][0]['sample'] is True


def test_most_complete_map_is_used(bundle):
    manifest = load(bundle / 'manifest.json')
    assert manifest['map']['source'] == 'run_north.yaml'


def test_map_levels_keep_walls(bundle):
    from PIL import Image

    manifest = load(bundle / 'manifest.json')
    m = manifest['map']
    full = np.asarray(Image.open(bundle / 'map/state_1x.png'))
    quarter = np.asarray(Image.open(bundle / 'map/state_4x.png'))
    assert full.shape == (m['height'], m['width'])
    assert quarter.shape == (-(-m['height'] // 4), -(-m['width'] // 4))
    assert set(np.unique(full)) <= {0, 127, 255}
    # Thin walls survive downsampling: every occupied block of the full map is occupied in the quarter map.
    assert (quarter == 255).sum() >= (full == 255).sum() / 16


def test_downsample_rule():
    state = np.array([[0, 127, 0, 0], [0, 0, 255, 0]], dtype=np.uint8)
    assert web_import.downsample(state, 2).tolist() == [[127, 255]]


def test_trajectory_is_in_the_map_frame(run, bundle):
    """map->odom (SLAM) composed with odom->base_link (EKF) must give the true pose, although odometry drifted."""
    mission = load(bundle / 'mission.json')
    truth = run['log'].poses
    t0 = truth[0].t
    by_time = {round(s.t - t0, 1): s for s in truth}
    checked = 0
    for t, x, y, yaw, _d in mission['trajectory'][::10]:
        s = by_time.get(round(t, 1))
        if s is None:
            continue
        assert math.hypot(x - s.x, y - s.y) < 0.01
        assert abs(math.atan2(math.sin(yaw - s.yaw), math.cos(yaw - s.yaw))) < 0.01
        checked += 1
    assert checked > 20
    assert mission['distance_m'] == pytest.approx(25.0, abs=1.5)


def test_reveal_and_scans(bundle):
    from PIL import Image

    mission = load(bundle / 'mission.json')
    reveal = np.asarray(Image.open(bundle / 'mission/reveal.png'))
    state = np.asarray(Image.open(bundle / 'map/state_1x.png'))
    known = state != 0
    assert reveal[known].min() >= 1                      # every known cell appears at some point
    assert reveal.max() <= len(mission['snapshot_times']) + 1
    assert mission['snapshot_times'] == sorted(mission['snapshot_times'])
    scans = np.fromfile(bundle / 'mission/scans.bin', dtype='<u2')
    assert scans.size == mission['scans']['count'] * mission['scans']['rays']
    cloud = np.fromfile(bundle / 'mission/cloud.bin', dtype='<i2').reshape(-1, 3)
    assert len(cloud) == mission['cloud']['count'] > 100


def test_places_routes_and_photos(bundle):
    graph = load(bundle / 'graph.json')
    landmarks = load(bundle / 'landmarks.json')
    routes = load(bundle / 'routes.json')
    assert [r['room'] for r in graph['rooms']] == ['S1.02']
    sign = next(lm for lm in landmarks if lm['class'] == 'room_sign')
    assert sign['photo']['src'].endswith('.webp') and (bundle / sign['photo']['src']).is_file()
    assert sign['first_seen_s'] == pytest.approx(20.0, abs=0.2)
    assert len(sign['observations']) == 2
    route = routes['north']['routes']['S1.02']
    assert [s['junction_id'] for s in route['steps']] == [1, 2]      # S1.02 is nearer junction 2
    # A Windows-style stored path still finds the photo by file name.
    junctions = {j['id']: j for j in graph['junctions']}
    assert junctions[2]['photo'] is not None


def test_metrics_never_invent_numbers(bundle):
    metrics = load(bundle / 'metrics.json')['objectives']
    assert metrics['O2']['status'] == 'pass' and metrics['O2']['parts'][0]['value'] == 95.0
    for key in ('O3', 'O4', 'O5', 'O6', 'O7', 'O8'):
        assert metrics[key]['status'] == 'not_measured' and metrics[key]['parts'] == [], key
    stats = load(bundle / 'manifest.json')['stats']
    assert stats['landmark_error_m'] is None


def test_eval_json_flag(run, tmp_path):
    """The eval scripts' --json output is what the importer reads."""
    polygon = tmp_path / 'corridor.csv'
    polygon.write_text('x,y\n0,18.8\n0,21.2\n-14,21.2\n-14,18.8\n')
    out = tmp_path / 'cov.json'
    subprocess.run([sys.executable, str(REPO / 'tools' / 'eval' / 'map_coverage.py'), '--map',
                    str(run['root'] / 'maps' / 'run_north.yaml'), '--polygon', str(polygon), '--json', str(out)],
                   check=True, stdout=subprocess.DEVNULL)
    data = load(out)
    assert data['objective'] == 'O2' and data['tool'] == 'map_coverage'
    assert 0 < data['result']['percent'] <= 100 and data['passed'] == (data['result']['percent'] >= 90)


def test_static_export(tmp_path, monkeypatch):
    import web_export

    if not (web_export.DIST / 'index.html').is_file() or not (web_export.DATA / 'index.json').is_file():
        pytest.skip('site or data bundle not built')
    out = web_export.export(tmp_path / 'site', '/merz-mapper/')
    html = (out / 'index.html').read_text()
    assert '<base href="/merz-mapper/">' in html
    for page in ('find', 'mission', 'results', 'about'):
        assert (out / page / 'index.html').is_file()
    assert (out / '404.html').is_file() and (out / '.nojekyll').is_file()
    index = load(out / 'data' / 'index.json')
    assert (out / 'data' / index['default'] / 'manifest.json').is_file()
    assert not (out / 'data' / index['default'] / 'api').exists()


def test_committed_sample_bundle_is_consistent():
    """The bundle in git must agree with itself: every route uses junctions and rooms of its own entrance."""
    index_path = REPO / 'web' / 'data' / 'index.json'
    if not index_path.is_file():
        pytest.skip('no bundle')
    root = REPO / 'web' / 'data' / load(index_path)['default']
    graph = load(root / 'graph.json')
    routes = load(root / 'routes.json')
    for entrance, zone in routes.items():
        allowed = set(graph['zones'][entrance]['junctions'])
        for room, route in zone['routes'].items():
            assert room in graph['zones'][entrance]['rooms']
            assert {s['junction_id'] for s in route['steps']} <= allowed, (entrance, room)
