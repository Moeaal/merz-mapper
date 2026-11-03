"""Build the sample database and placeholder photos, so the website can be opened before any robot data exists.

    python web/sample_data/make_sample_db.py

EVERYTHING HERE IS MADE UP. The layout and room numbers are not Merz Court, and it is marked as sample data in the page.

Layout (metres). Two zones split by a locked door; S2.xx rooms can only be reached from the south entrance.

    J3 --- J2 --- J1 --- [north entrance]         zone: north
            |
         (locked door)
            |
    J6 --- J5 --- J4 --- [south entrance]         zone: south
"""
from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'ros2_ws' / 'src' / 'merz_semantic_map'))

from merz_semantic_map.database import MerzDatabase  # noqa: E402

DATABASE = HERE / 'merz_sample.sqlite'
PHOTOS = HERE / 'photos'

ENTRANCES = [('north', 'North entrance', 2.0, 12.0, 3.14159), ('south', 'South entrance', 2.0, 0.0, 3.14159)]
#            id     x      y
JUNCTIONS = {1: (-2.0, 12.0), 2: (-12.0, 12.0), 3: (-24.0, 12.0), 4: (-2.0, 0.0), 5: (-12.0, 0.0), 6: (-24.0, 0.0)}
EDGES = [(1, 2, 10.0), (2, 3, 12.0), (4, 5, 10.0), (5, 6, 12.0)]
#         text     x      y     zone
ROOMS = [('S1.01', -3.0, 13.5, 'north'), ('S1.02', -8.0, 10.5, 'north'), ('S1.03', -13.0, 13.5, 'north'),
         ('S1.04', -23.0, 13.5, 'north'), ('S1.05', -25.0, 10.5, 'north'),
         ('S2.01', -3.0, 1.5, 'south'), ('S2.02', -13.0, -1.5, 'south'), ('S2.03', -23.0, 1.5, 'south')]
ZONES = {'north': [1, 2, 3], 'south': [4, 5, 6]}


def make_photo(path: Path, title: str) -> None:
    """Draw a simple placeholder in place of a real junction photo."""
    from PIL import Image, ImageDraw, ImageFont

    width, height = 640, 400
    image = Image.new('RGB', (width, height), '#cfd5da')
    draw = ImageDraw.Draw(image)
    # A corridor in perspective: floor, walls and a vanishing end.
    draw.polygon([(0, height), (width, height), (390, 220), (250, 220)], fill='#9aa3aa')
    draw.polygon([(0, 0), (250, 110), (250, 220), (0, height)], fill='#e6e9eb')
    draw.polygon([(width, 0), (390, 110), (390, 220), (width, height)], fill='#dde1e4')
    draw.rectangle([250, 110, 390, 220], fill='#f4f5f6')
    font = ImageFont.load_default(size=28)
    draw.text((width / 2, 34), title, fill='#1c2329', anchor='mm', font=font)
    draw.text((width / 2, 70), 'Sample image', fill='#5c6770', anchor='mm', font=ImageFont.load_default(size=20))
    image.save(path, optimize=True)


def build(database_path: Path = DATABASE, photo_dir: Path = PHOTOS) -> None:
    database_path.unlink(missing_ok=True)
    photo_dir.mkdir(parents=True, exist_ok=True)
    with MerzDatabase(database_path) as database:
        database.set_meta('sample_data', 'true')
        for entrance in ENTRANCES:
            database.upsert_entrance(*entrance)
        for junction_id, (x, y) in JUNCTIONS.items():
            name = f'junction_{junction_id}.png'
            make_photo(photo_dir / name, f'Junction {junction_id}')
            photo_id = database.add_photo(name, x, y)
            database.connection.execute('INSERT INTO junctions (id, x, y, photo_id) VALUES (?, ?, ?, ?)',
                                        (junction_id, x, y, photo_id))
        for a, b, length in EDGES:
            database.add_junction_edge(a, b, length)
        zone_landmarks: dict[str, list[int]] = {zone: [] for zone in ZONES}
        for landmark_id, (text, x, y, zone) in enumerate(ROOMS, start=1):
            database.upsert_landmark(landmark_id, 'room_sign', text, (x, y, 1.5), confidence=0.9, observation_count=5)
            zone_landmarks[zone].append(landmark_id)
        for zone, junction_ids in ZONES.items():
            database.set_access_zone(zone, zone_landmarks[zone], junction_ids)


if __name__ == '__main__':
    build()
    print(f'Wrote {DATABASE} and {len(JUNCTIONS)} photos')
