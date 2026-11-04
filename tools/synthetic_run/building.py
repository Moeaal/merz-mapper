"""The made-up building used for the synthetic run. EVERYTHING HERE IS INVENTED: it is not Merz Court.

Two zones split by locked doors (as in the real plan for one map with several entrances), an atrium with pillars,
29 rooms with open or closed doors, lifts, stairs and exit signs. Units are metres in the map frame.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import random

import numpy as np

RESOLUTION = 0.05                       # m per cell, as slam.yaml
EXTENT = (-54.0, -20.0, 10.0, 40.0)     # x0, y0, x1, y1 of the simulated world
HALF_WIDTH = 1.2                        # corridor half width
WALL = 0.15                             # partition wall thickness
ROOM_DEPTH = 5.0
ROOM_WIDTH = 4.6


@dataclass
class Room:
    number: str
    zone: str
    x: float                     # door centre
    corridor_y: float
    side: int                    # +1 north of the corridor, -1 south
    open: bool
    width: float = ROOM_WIDTH

    @property
    def sign_xy(self) -> tuple[float, float]:
        """The door plate sits on the corridor wall, just right of the door, facing the corridor."""
        return self.x + 0.85, self.corridor_y + self.side * (HALF_WIDTH - 0.05)

    @property
    def door_xy(self) -> tuple[float, float]:
        return self.x, self.corridor_y + self.side * (HALF_WIDTH - 0.05)

    def box(self) -> tuple[float, float, float, float]:
        near = self.corridor_y + self.side * (HALF_WIDTH + WALL)
        far = near + self.side * ROOM_DEPTH
        return self.x - self.width / 2, min(near, far), self.x + self.width / 2, max(near, far)


@dataclass
class TruthLandmark:
    cls: str
    text: str
    x: float
    y: float
    z: float


@dataclass
class Building:
    free_rects: list[tuple[float, float, float, float]] = field(default_factory=list)
    solid_rects: list[tuple[float, float, float, float]] = field(default_factory=list)
    rooms: list[Room] = field(default_factory=list)
    landmarks: list[TruthLandmark] = field(default_factory=list)
    junctions: dict[str, tuple[float, float]] = field(default_factory=dict)
    edges: list[tuple[str, str]] = field(default_factory=list)
    zones: dict[str, list[str]] = field(default_factory=dict)
    entrances: dict[str, tuple[str, float, float, float]] = field(default_factory=dict)
    tours: dict[str, list[tuple[float, float]]] = field(default_factory=dict)


def corridor(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float, float, float]:
    return (min(a[0], b[0]) - HALF_WIDTH, min(a[1], b[1]) - HALF_WIDTH,
            max(a[0], b[0]) + HALF_WIDTH, max(a[1], b[1]) + HALF_WIDTH)


def make_building(seed: int = 3094) -> Building:
    rng = random.Random(seed)
    b = Building()
    # Outside: a strip of pavement the lidar can see through the entrance doors.
    b.free_rects.append((1.5, -6.0, 8.0, 26.0))
    door_gap = 0.075
    segments = [
        ((4.0, 20.0), (-48.0, 20.0)), ((4.0, 0.0), (-48.0, 0.0)),                       # north and south corridors
        ((-14.0, 20.0), (-14.0, 10.0 + door_gap + HALF_WIDTH)),                        # cross corridors, each split
        ((-14.0, 0.0), (-14.0, 10.0 - door_gap - HALF_WIDTH)),                         # by a locked door at y = 10
        ((-40.0, 20.0), (-40.0, 10.0 + door_gap + HALF_WIDTH)),
        ((-40.0, 0.0), (-40.0, 10.0 - door_gap - HALF_WIDTH)),
        ((-26.0, 20.0), (-26.0, 28.5)),                                                # north wing to the atrium
        ((-30.0, 0.0), (-30.0, -10.0)), ((-30.0, -10.0), (-44.0, -10.0)),              # south wing and lab corridor
    ]
    b.free_rects += [corridor(p, q) for p, q in segments]
    b.free_rects.append((-34.0, 28.0, -18.0, 37.0))                                    # atrium
    b.solid_rects.append((1.5, 9.0, 8.0, 11.0))     # railings outside between the entrances (keeps zones apart)
    for px, py in [(-30.0, 31.0), (-22.0, 31.0), (-30.0, 34.5), (-22.0, 34.5)]:          # atrium pillars
        b.solid_rects.append((px - 0.3, py - 0.3, px + 0.3, py + 0.3))
    for bx, by, w, h in [(-27.5, 35.8, 3.0, 0.5), (-24.0, 29.0, 0.6, 0.6)]:              # benches, a planter
        b.solid_rects.append((bx, by, bx + w, by + h))

    layout = [  # (corridor y, side, zone, door x positions)
        (20.0, +1, 'north', [-4, -9, -14, -19, -33, -38, -45]),
        (20.0, -1, 'north', [-4, -9, -19, -24, -29, -34, -45]),
        (0.0, +1, 'south', [-4, -9, -19, -24, -34, -45]),
        (0.0, -1, 'south', [-4, -9, -14, -19, -24, -36, -45]),
        (-10.0, -1, 'south', [-35, -41]),
    ]
    counters = {'north': 0, 'south': 0}
    for corridor_y, side, zone, xs in layout:
        for x in sorted(xs, reverse=True):
            counters[zone] += 1
            number = f"S{1 if zone == 'north' else 2}.{counters[zone]:02d}"
            b.rooms.append(Room(number, zone, float(x), corridor_y, side, rng.random() < 0.5,
                                5.0 if corridor_y == -10.0 else ROOM_WIDTH))
    for room in b.rooms:
        x0, y0, x1, y1 = room.box()
        b.free_rects.append((x0, y0, x1, y1))
        if room.open:
            wall_y0 = room.corridor_y + room.side * HALF_WIDTH
            wall_y1 = wall_y0 + room.side * (WALL + 0.01)
            b.free_rects.append((room.x - 0.45, min(wall_y0, wall_y1), room.x + 0.45, max(wall_y0, wall_y1)))
        for _ in range(rng.randint(1, 3)):                                                # desks and cupboards
            fx, fy = rng.uniform(x0 + 0.4, x1 - 1.8), rng.uniform(y0 + 0.6, y1 - 1.4)
            b.solid_rects.append((fx, fy, fx + rng.uniform(1.0, 1.6), fy + rng.uniform(0.6, 0.9)))
        sx, sy = room.sign_xy
        b.landmarks.append(TruthLandmark('room_sign', room.number, sx, sy, 1.5))
        dx, dy = room.door_xy
        b.landmarks.append(TruthLandmark('door', '', dx, dy, 1.0))
    for x, y in [(-12.4, 18.95), (-37.0, 1.05), (-21.5, 18.95), (-6.6, -1.05)]:            # bins against walls
        b.solid_rects.append((x, y - 0.2, x + 0.4, y + 0.2))
    b.landmarks += [
        TruthLandmark('lift', '', -29.0, 21.15, 1.2), TruthLandmark('lift', '', -27.5, -1.15, 1.2),
        TruthLandmark('stairs', '', -49.15, 20.0, 1.0), TruthLandmark('stairs', '', -49.15, 0.0, 1.0),
        TruthLandmark('exit_sign', '', 0.8, 21.15, 2.3), TruthLandmark('exit_sign', '', 0.8, 1.15, 2.3),
    ]
    b.junctions = {
        'A': (-1.5, 20.0), 'B': (-14.0, 20.0), 'C': (-26.0, 20.0), 'D': (-40.0, 20.0), 'E': (-26.0, 28.5),
        'F': (-47.0, 20.0), 'G': (-26.0, 32.5),
        'H': (-1.5, 0.0), 'I': (-14.0, 0.0), 'K': (-30.0, 0.0), 'L': (-40.0, 0.0), 'M': (-47.0, 0.0),
        'N': (-30.0, -10.0), 'O': (-43.0, -10.0),
    }
    b.edges = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'F'), ('C', 'E'), ('E', 'G'),
               ('H', 'I'), ('I', 'K'), ('K', 'L'), ('L', 'M'), ('K', 'N'), ('N', 'O')]
    b.zones = {'north': list('ABCDEFG'), 'south': list('HIKLMNO')}
    b.entrances = {'north': ('North entrance', 3.0, 20.0, np.pi), 'south': ('South entrance', 3.0, 0.0, np.pi)}
    b.tours = {
        'north': [(4.0, 20.0), (-14.0, 20.0), (-14.0, 11.6), (-14.0, 20.0), (-26.0, 20.0), (-26.0, 28.5),
                  (-26.0, 32.5), (-31.0, 33.0), (-31.0, 35.6), (-21.0, 35.6), (-21.0, 30.0), (-26.0, 29.0),
                  (-26.0, 20.0), (-40.0, 20.0), (-40.0, 11.6), (-40.0, 20.0), (-47.6, 20.0), (-1.5, 20.0),
                  (3.0, 20.0)],
        'south': [(4.0, 0.0), (-14.0, 0.0), (-14.0, 8.4), (-14.0, 0.0), (-30.0, 0.0), (-30.0, -10.0),
                  (-44.2, -10.0), (-30.0, -10.0), (-30.0, 0.0), (-40.0, 0.0), (-40.0, 8.4), (-40.0, 0.0),
                  (-47.6, 0.0), (-1.5, 0.0), (3.0, 0.0)],
    }
    return b


def rasterise(b: Building) -> tuple[np.ndarray, float, float]:
    """Return the true occupancy (True = solid), row 0 at the lowest y, and the grid origin."""
    x0, y0, x1, y1 = EXTENT
    width, height = round((x1 - x0) / RESOLUTION), round((y1 - y0) / RESOLUTION)
    solid = np.ones((height, width), dtype=bool)

    def cells(rect):
        rx0, ry0, rx1, ry1 = rect
        c0, c1 = int(round((rx0 - x0) / RESOLUTION)), int(round((rx1 - x0) / RESOLUTION))
        r0, r1 = int(round((ry0 - y0) / RESOLUTION)), int(round((ry1 - y0) / RESOLUTION))
        return slice(max(r0, 0), max(r1, 0)), slice(max(c0, 0), max(c1, 0))

    for rect in b.free_rects:
        solid[cells(rect)] = False
    for rect in b.solid_rects:
        solid[cells(rect)] = True
    return solid, x0, y0


def wall_segments(b: Building) -> list[tuple[float, float, float, float]]:
    """Approximate floor-plan walls for wall_error.py: the outline of every room, the atrium and every pillar."""
    segments = []
    rects = [r.box() for r in b.rooms] + [(-34.0, 28.0, -18.0, 37.0)] + b.solid_rects[:4]
    for x0, y0, x1, y1 in rects:
        segments += [(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)]
    # Corridor side walls, taken along each straight corridor.
    for (y, xa, xb) in [(20.0, -49.2, 1.35), (0.0, -49.2, 1.35), (-10.0, -45.2, -28.8)]:
        segments += [(xa, y - HALF_WIDTH, xb, y - HALF_WIDTH), (xa, y + HALF_WIDTH, xb, y + HALF_WIDTH)]
    return segments
