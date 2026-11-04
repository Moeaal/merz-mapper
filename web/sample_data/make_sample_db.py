"""Build the sample database, placeholder junction photos and a sample occupancy-grid map, so the website can be opened
before any robot data exists.

    python web/sample_data/make_sample_db.py

EVERYTHING HERE IS MADE UP. The layout and room numbers are not Merz Court, and it is marked as sample data in the page.
The map imitates what the robot will save (map_saver's trinary .pgm + .yaml), so the website reads it the same way.

Layout (metres, map frame). Two zones split by a locked door; S2.xx rooms can only be reached from the south entrance.

    J11 -- J3 ----------- J2 --- J1 --- [north entrance]      zone: north
            |             |
            J8 ---------- J7   (north wing, a loop)
                          |
                    (locked door, x = -12, y = 6)
                          |
    J10 -- J6 ----------- J5 --- J4 --- [south entrance]      zone: south
                          |
                          J9   (south wing)

(The north wing is drawn below the north corridor here only to keep the sketch short: it is at y = 22, above it.)
"""
from __future__ import annotations

import math
from pathlib import Path
import random
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'ros2_ws' / 'src' / 'merz_semantic_map'))

from merz_semantic_map.database import MerzDatabase  # noqa: E402

DATABASE = HERE / 'merz_sample.sqlite'
PHOTOS = HERE / 'photos'
MAP_YAML = HERE / 'merz_map.yaml'

ENTRANCES = [('north', 'North entrance', 2.0, 12.0, 3.14159), ('south', 'South entrance', 2.0, 0.0, 3.14159)]
#            id      x      y         Junctions 1-6 are unchanged from the first sample, so its tests still hold.
JUNCTIONS = {1: (-2.0, 12.0), 2: (-12.0, 12.0), 3: (-24.0, 12.0), 4: (-2.0, 0.0), 5: (-12.0, 0.0), 6: (-24.0, 0.0),
             7: (-12.0, 22.0), 8: (-24.0, 22.0), 9: (-12.0, -10.0), 10: (-32.0, 0.0), 11: (-32.0, 12.0)}
EDGES = [(1, 2, 10.0), (2, 3, 12.0), (4, 5, 10.0), (5, 6, 12.0),
         (2, 7, 10.0), (7, 8, 12.0), (3, 8, 10.0), (3, 11, 8.0), (5, 9, 10.0), (6, 10, 8.0)]
#          text      x      y     zone     door open when the robot passed (open rooms show their inside on the map)
ROOMS = [('S1.01', -3.0, 13.5, 'north', True), ('S1.02', -8.0, 10.5, 'north', False),
         ('S1.03', -15.0, 13.5, 'north', True), ('S1.04', -21.0, 13.5, 'north', False),
         ('S1.05', -25.0, 10.5, 'north', True), ('S1.06', -10.5, 16.0, 'north', True),
         ('S1.07', -15.0, 20.5, 'north', False), ('S1.08', -20.0, 23.5, 'north', True),
         ('S1.09', -19.5, 20.5, 'north', False), ('S1.10', -31.0, 13.5, 'north', True),
         ('S1.11', -33.0, 10.5, 'north', False),
         ('S2.01', -3.0, 1.5, 'south', True), ('S2.02', -15.0, -1.5, 'south', False),
         ('S2.03', -23.0, 1.5, 'south', True), ('S2.04', -10.5, -4.5, 'south', True),
         ('S2.05', -13.5, -8.5, 'south', False), ('S2.06', -10.5, -11.5, 'south', True),
         ('S2.07', -31.0, 1.5, 'south', False), ('S2.08', -33.0, -1.5, 'south', True),
         ('S2.09', -5.0, -1.5, 'south', False)]
ZONES = {'north': [1, 2, 3, 7, 8, 11], 'south': [4, 5, 6, 9, 10]}
LOCKED_DOOR = (-12.0, 6.0)

# Occupancy grid. 0.1 m cells keep the sample small; the robot's maps will be 0.05 m (slam.yaml).
RESOLUTION = 0.1
MAP_ORIGIN = (-38.0, -16.0)
MAP_SIZE_M = (42.0, 44.0)
FREE, OCCUPIED, UNKNOWN = 254, 0, 205          # map_saver trinary pixel values
CORRIDOR_HALF_WIDTH = 1.2
WALL = 0.2


class Grid:
    """A tiny raster in world coordinates. Pixel row 0 is the highest y, as in a saved .pgm."""

    def __init__(self) -> None:
        from PIL import Image, ImageDraw

        self.width = round(MAP_SIZE_M[0] / RESOLUTION)
        self.height = round(MAP_SIZE_M[1] / RESOLUTION)
        self.image = Image.new('L', (self.width, self.height), UNKNOWN)
        self.draw = ImageDraw.Draw(self.image)

    def pixel(self, x: float, y: float) -> tuple[int, int]:
        return round((x - MAP_ORIGIN[0]) / RESOLUTION), round(self.height - (y - MAP_ORIGIN[1]) / RESOLUTION)

    def rect(self, x0: float, y0: float, x1: float, y1: float, value: int) -> None:
        (c0, r0), (c1, r1) = self.pixel(min(x0, x1), max(y0, y1)), self.pixel(max(x0, x1), min(y0, y1))
        self.draw.rectangle([c0, r0, c1 - 1, r1 - 1], fill=value)


def corridor_box(a: tuple[float, float], b: tuple[float, float], half: float) -> tuple[float, float, float, float]:
    return min(a[0], b[0]) - half, min(a[1], b[1]) - half, max(a[0], b[0]) + half, max(a[1], b[1]) + half


def nearest_corridor(x: float, y: float) -> tuple[str, float]:
    """Return ('h' or 'v', the corridor's fixed coordinate) for the corridor a door sign is on."""
    best = None
    for a, b, _length in EDGES:
        (ax, ay), (bx, by) = JUNCTIONS[a], JUNCTIONS[b]
        if ay == by:
            distance = abs(y - ay) + max(0.0, min(ax, bx) - x, x - max(ax, bx))
            candidate = (distance, 'h', ay)
        else:
            distance = abs(x - ax) + max(0.0, min(ay, by) - y, y - max(ay, by))
            candidate = (distance, 'v', ax)
        best = min(best, candidate) if best else candidate
    return best[1], best[2]


def make_map(yaml_path: Path) -> None:
    """Draw a plausible SLAM map: corridors along the junction graph, rooms off them, a closed door between zones."""
    rng = random.Random(3094)
    grid = Grid()
    offset = CORRIDOR_HALF_WIDTH + WALL
    room_depth, room_width = 3.6, 3.6
    doors = []
    # Rooms first, so corridor walls are drawn over their shared side.
    for _text, x, y, _zone, is_open in ROOMS:
        axis, fixed = nearest_corridor(x, y)
        if axis == 'h':
            side = 1 if y > fixed else -1
            near, far = fixed + side * CORRIDOR_HALF_WIDTH, fixed + side * (CORRIDOR_HALF_WIDTH + room_depth)
            box = (x - room_width / 2, min(near, far), x + room_width / 2, max(near, far))
            door = (x - 0.5, min(near, near + side * WALL * 2), x + 0.5, max(near, near + side * WALL * 2))
        else:
            side = 1 if x > fixed else -1
            near, far = fixed + side * CORRIDOR_HALF_WIDTH, fixed + side * (CORRIDOR_HALF_WIDTH + room_depth)
            box = (min(near, far), y - room_width / 2, max(near, far), y + room_width / 2)
            door = (min(near, near + side * WALL * 2), y - 0.5, max(near, near + side * WALL * 2), y + 0.5)
        grid.rect(box[0] - WALL, box[1] - WALL, box[2] + WALL, box[3] + WALL, OCCUPIED)
        grid.rect(*box, FREE if is_open else UNKNOWN)
        if is_open:
            doors.append(door)
            for _ in range(rng.randint(1, 3)):     # desks and cupboards seen through the door
                fx, fy = rng.uniform(box[0] + 0.4, box[2] - 1.4), rng.uniform(box[1] + 0.4, box[3] - 1.0)
                grid.rect(fx, fy, fx + rng.uniform(0.5, 1.0), fy + rng.uniform(0.4, 0.6), OCCUPIED)
    # Corridors: walls, then floor, so junctions merge into one open space.
    segments = [(JUNCTIONS[a], JUNCTIONS[b]) for a, b, _ in EDGES]
    segments += [((-2.0, 12.0), (3.5, 12.0)), ((-2.0, 0.0), (3.5, 0.0))]           # entrance lobbies
    door_x, door_y = LOCKED_DOOR
    stubs = [((door_x, 12.0), (door_x, door_y + 0.1)), ((door_x, 0.0), (door_x, door_y - 0.1))]
    for a, b in segments + stubs:
        grid.rect(*corridor_box(a, b, offset), OCCUPIED)
    for a, b in segments + stubs:
        grid.rect(*corridor_box(a, b, CORRIDOR_HALF_WIDTH), FREE)
    grid.rect(door_x - offset, door_y - 0.1, door_x + offset, door_y + 0.1, OCCUPIED)   # the locked door
    for door in doors:
        grid.rect(*door, FREE)
    # Outside the entrances the lidar sees a little of the street, then nothing.
    grid.rect(0.0, -1.2, 4.0, 13.2, UNKNOWN)
    for y in (12.0, 0.0):
        grid.rect(0.0, y - 1.0, 3.5, y + 1.0, FREE)
    grid.rect(-0.2, -1.6, 0.0, 13.6, OCCUPIED)                                          # outer wall
    for y in (12.0, 0.0):
        grid.rect(-0.25, y - 0.9, 0.05, y + 0.9, FREE)                                  # entrance doors, open
    # Scan noise: a few stray hits along corridor walls, like people and bins.
    for (ax, ay), (bx, by) in segments:
        for _ in range(int(math.hypot(bx - ax, by - ay) / 3)):
            t = rng.random()
            px, py = ax + t * (bx - ax), ay + t * (by - ay)
            dx, dy = (0.0, rng.choice((-1, 1)) * rng.uniform(0.6, 1.0)) if ay == by else \
                     (rng.choice((-1, 1)) * rng.uniform(0.6, 1.0), 0.0)
            grid.rect(px + dx, py + dy, px + dx + 0.2, py + dy + 0.2, OCCUPIED)
    pgm = yaml_path.with_suffix('.pgm')
    grid.image.save(pgm)
    yaml_path.write_text(
        f'image: {pgm.name}\nmode: trinary\nresolution: {RESOLUTION}\n'
        f'origin: [{MAP_ORIGIN[0]}, {MAP_ORIGIN[1]}, 0.0]\nnegate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.25\n')


def make_photo(path: Path, junction_id: int) -> None:
    """Draw a placeholder in place of a real junction photo: a corridor in perspective with doors either side."""
    from PIL import Image, ImageDraw, ImageFont

    rng = random.Random(junction_id)
    width, height = 800, 520
    vx0, vx1, vy0, vy1 = 330, 470, 170, 300            # the far end of the corridor
    image = Image.new('RGB', (width, height), '#d9dcd8')
    draw = ImageDraw.Draw(image)
    draw.polygon([(0, 0), (width, 0), (vx1, vy0), (vx0, vy0)], fill='#eef0ec')                     # ceiling
    draw.polygon([(0, height), (width, height), (vx1, vy1), (vx0, vy1)], fill='#a3a8a2')           # floor
    draw.polygon([(0, 0), (vx0, vy0), (vx0, vy1), (0, height)], fill='#e3e5e0')                    # left wall
    draw.polygon([(width, 0), (vx1, vy0), (vx1, vy1), (width, height)], fill='#d6d9d3')            # right wall
    draw.rectangle([vx0, vy0, vx1, vy1], fill='#f7f7f4')
    for t in (0.18, 0.55):                                                                         # ceiling lights
        y = vy0 * (1 - t) + 0 * t
        draw.line([(vx0 + (0 - vx0) * t * 0.3 + 140 * t, y + 10), (vx1 - 140 * t, y + 10)], fill='#ffffff', width=6)
    for side in (-1, 1):                                                                           # doors
        for t in sorted(rng.sample([0.25, 0.45, 0.62, 0.78], 2)):
            x_edge = 0 if side < 0 else width
            vx = vx0 if side < 0 else vx1
            x0, x1 = x_edge + (vx - x_edge) * t, x_edge + (vx - x_edge) * (t + 0.09)
            top0, top1 = (vy0 * 0.55) * t + 70 * (1 - t), (vy0 * 0.55) * (t + 0.09) + 70 * (1 - t - 0.09)
            bottom0 = height - (height - vy1) * t
            bottom1 = height - (height - vy1) * (t + 0.09)
            draw.polygon([(x0, top0 + 40), (x1, top1 + 40), (x1, bottom1), (x0, bottom0)], fill='#8a6f52')
    draw.line([(vx0, vy1), (0, height)], fill='#8d928c', width=2)
    draw.line([(vx1, vy1), (width, height)], fill='#8d928c', width=2)
    # Label strip, so nobody mistakes the placeholder for a real photo.
    draw.rectangle([0, height - 64, width, height], fill='#13233a')
    draw.text((24, height - 32), f'Junction {junction_id}', fill='#ffffff', anchor='lm', font=ImageFont.load_default(size=28))
    draw.text((width - 24, height - 32), 'Sample image - the rover photo goes here', fill='#c9d3df', anchor='rm',
              font=ImageFont.load_default(size=20))
    image.save(path, optimize=True)


def build(database_path: Path = DATABASE, photo_dir: Path = PHOTOS, map_yaml: Path | None = None) -> None:
    database_path.unlink(missing_ok=True)
    photo_dir.mkdir(parents=True, exist_ok=True)
    with MerzDatabase(database_path) as database:
        database.set_meta('sample_data', 'true')
        for entrance in ENTRANCES:
            database.upsert_entrance(*entrance)
        for junction_id, (x, y) in JUNCTIONS.items():
            name = f'junction_{junction_id}.png'
            make_photo(photo_dir / name, junction_id)
            photo_id = database.add_photo(name, x, y)
            database.connection.execute('INSERT INTO junctions (id, x, y, photo_id) VALUES (?, ?, ?, ?)',
                                        (junction_id, x, y, photo_id))
        for a, b, length in EDGES:
            database.add_junction_edge(a, b, length)
        zone_landmarks: dict[str, list[int]] = {zone: [] for zone in ZONES}
        for landmark_id, (text, x, y, zone, _open) in enumerate(ROOMS, start=1):
            database.upsert_landmark(landmark_id, 'room_sign', text, (x, y, 1.5), confidence=0.9, observation_count=5)
            zone_landmarks[zone].append(landmark_id)
        for zone, junction_ids in ZONES.items():
            database.set_access_zone(zone, zone_landmarks[zone], junction_ids)
    make_map(map_yaml or database_path.parent / 'merz_map.yaml')


if __name__ == '__main__':
    build(DATABASE, PHOTOS, MAP_YAML)
    print(f'Wrote {DATABASE}, {MAP_YAML.name} and {len(JUNCTIONS)} photos')
