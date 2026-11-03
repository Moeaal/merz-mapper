"""Website tests on the sample database. No ROS needed."""
import importlib.util
from pathlib import Path
import sys
import time

import pytest

WEB = Path(__file__).resolve().parent
sys.path.insert(0, str(WEB))
sys.path.insert(0, str(WEB.parent / 'ros2_ws' / 'src' / 'merz_semantic_map'))

from app.routing import Junction, describe_steps, nearest_junction, shortest_path, turn_direction  # noqa: E402

fastapi_client = pytest.importorskip('fastapi.testclient')

_spec = importlib.util.spec_from_file_location('make_sample_db', WEB / 'sample_data' / 'make_sample_db.py')
make_sample_db = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(make_sample_db)

_spec = importlib.util.spec_from_file_location('qr_posters', WEB / 'qr_posters.py')
qr_posters = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(qr_posters)


@pytest.fixture(scope='module')
def sample(tmp_path_factory):
    """Build a fresh sample in a temporary folder, so the tests also prove the sample builder works."""
    root = tmp_path_factory.mktemp('sample')
    make_sample_db.build(root / 'merz.sqlite', root / 'photos')
    return root


@pytest.fixture(scope='module')
def client(sample):
    from app.main import create_app
    return fastapi_client.TestClient(create_app(sample / 'merz.sqlite', sample / 'photos'))


# ---- routing
EDGES = [(1, 2, 1.0), (2, 3, 1.0), (1, 3, 5.0), (3, 4, 1.0), (5, 6, 1.0)]


def test_shortest_path_prefers_the_shorter_way():
    assert shortest_path(EDGES, {1, 2, 3, 4}, 1, 4) == ([1, 2, 3, 4], 3.0)


def test_edges_work_in_both_directions():
    assert shortest_path(EDGES, {1, 2, 3, 4}, 4, 1) == ([4, 3, 2, 1], 3.0)


def test_route_avoids_junctions_outside_the_zone():
    assert shortest_path(EDGES, {1, 3, 4}, 1, 4) == ([1, 3, 4], 6.0)


def test_goal_outside_the_zone_or_disconnected_gives_none():
    assert shortest_path(EDGES, {1, 2, 3}, 1, 4) is None
    assert shortest_path(EDGES, {1, 2, 3, 4, 5, 6}, 1, 6) is None


def test_start_equals_goal():
    assert shortest_path(EDGES, {1}, 1, 1) == ([1], 0.0)


@pytest.mark.parametrize('after, expected', [
    ((2.0, 0.0), 'straight'), ((1.0, 1.0), 'left'), ((1.0, -1.0), 'right'), ((0.0, 0.0), 'back'), ((2.0, 0.2), 'straight'),
])
def test_turn_direction_heading_east(after, expected):
    assert turn_direction((0.0, 0.0), (1.0, 0.0), after) == expected


def test_turn_direction_does_not_depend_on_heading():
    # Heading north, a turn towards -x is a left turn.
    assert turn_direction((0.0, 0.0), (0.0, 1.0), (-1.0, 1.0)) == 'left'


def test_describe_steps_ends_at_the_room():
    path = [Junction(1, 0, 0), Junction(2, 10, 0), Junction(3, 10, 10)]
    assert describe_steps(path, 'S1', (-5.0, 0.0)) == ['Continue straight on.', 'Turn left.', 'Room S1 is close to this junction.']


def test_nearest_junction():
    assert nearest_junction([Junction(1, 0, 0), Junction(2, 5, 5)], 4, 4).id == 2
    assert nearest_junction([], 4, 4) is None


# ---- API
def test_entrances_are_listed_and_marked_as_sample(client):
    body = client.get('/entrances').json()
    assert {e['id'] for e in body['entrances']} == {'north', 'south'}
    assert body['sample_data'] is True


def test_rooms_depend_on_the_entrance(client):
    north = set(client.get('/rooms', params={'entrance': 'north'}).json()['rooms'])
    south = set(client.get('/rooms', params={'entrance': 'south'}).json()['rooms'])
    assert north == {'S1.01', 'S1.02', 'S1.03', 'S1.04', 'S1.05'}
    assert south == {'S2.01', 'S2.02', 'S2.03'}


def test_route_is_correct_in_the_sample(client):
    body = client.get('/route', params={'entrance': 'north', 'room': 'S1.04'}).json()
    assert [step['junction_id'] for step in body['steps']] == [1, 2, 3]
    assert body['length_m'] == 22.0
    assert body['steps'][-1]['instruction'] == 'Room S1.04 is close to this junction.'


def test_route_to_a_room_behind_the_locked_door_is_refused(client):
    response = client.get('/route', params={'entrance': 'north', 'room': 'S2.01'})
    assert response.status_code == 404
    assert 'not reachable' in response.json()['detail']


@pytest.mark.parametrize('path, params', [
    ('/rooms', {'entrance': 'nowhere'}), ('/route', {'entrance': 'nowhere', 'room': 'S1.01'}),
    ('/route', {'entrance': 'north', 'room': 'NOPE'}),
])
def test_unknown_names_give_404(client, path, params):
    assert client.get(path, params=params).status_code == 404


def test_sql_in_a_parameter_is_treated_as_text(client):
    assert client.get('/rooms', params={'entrance': "north' OR '1'='1"}).status_code == 404


def test_route_step_photos_load(client):
    body = client.get('/route', params={'entrance': 'south', 'room': 'S2.02'}).json()
    response = client.get(body['steps'][0]['photo_url'])
    assert response.status_code == 200 and response.headers['content-type'] == 'image/png'


def test_unknown_photo_gives_404(client):
    assert client.get('/photos/999').status_code == 404


def test_page_is_served(client):
    response = client.get('/')
    assert response.status_code == 200 and '<title>Merz Mapper directions</title>' in response.text


def test_every_room_query_is_under_one_second(client):
    body = client.get('/entrances').json()
    for entrance in body['entrances']:
        for room in client.get('/rooms', params={'entrance': entrance['id']}).json()['rooms']:
            start = time.perf_counter()
            assert client.get('/route', params={'entrance': entrance['id'], 'room': room}).status_code == 200
            assert time.perf_counter() - start < 1.0


def test_sample_database_and_photos_are_in_the_repository():
    """The file in git must exist, so that the website opens straight after cloning."""
    assert (WEB / 'sample_data' / 'merz_sample.sqlite').is_file()
    assert (WEB / 'sample_data' / 'photos' / 'junction_1.png').is_file()


# ---- QR posters
def test_entrance_url_is_encoded():
    assert qr_posters.entrance_url('http://a:8000/', 'east door') == 'http://a:8000/?entrance=east+door'


def test_poster_qr_code_decodes_back_to_the_url(sample, tmp_path):
    cv2 = pytest.importorskip('cv2')
    paths = qr_posters.make_all(sample / 'merz.sqlite', 'http://localhost:8000', tmp_path)
    assert {p.name for p in paths} == {'poster_north.png', 'poster_south.png'}
    decoded, _points, _code = cv2.QRCodeDetector().detectAndDecode(cv2.imread(str(tmp_path / 'poster_north.png')))
    assert decoded == 'http://localhost:8000/?entrance=north'
