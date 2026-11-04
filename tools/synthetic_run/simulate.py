"""Drive a simulated rover through the made-up building and record what the real rover code would record.

Lidar: ray cast into the true building (RPLIDAR S2-like: 15 m used, sigma 15 mm, 1 degree). The map is built from those
scans with the true pose plus a little registration noise, as a stand-in for SLAM Toolbox. Odometry drifts, and the
map->odom transform corrects it, as SLAM would. Landmarks are seen by a forward camera within range and line of sight,
with position noise. None of this claims to model the real sensors' performance; it only produces believable data in
the real formats so the website and importer can be built and tested before the rover runs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import random

import numpy as np

from building import RESOLUTION, Building

SPEED = 0.45            # m/s
TURN_RATE = 1.0         # rad/s
DT = 0.1                # s
SCAN_EVERY = 2          # scans at 5 Hz
RAYS = 360
MAX_RANGE = 15.0
RANGE_SIGMA = 0.015
MAP_EVERY_S = 10.0      # /map publishing period
LASER_OFFSET = (0.10, 0.0, 0.18)
CAMERA_FOV = math.radians(40)
CAMERA_RANGE = 5.0


@dataclass
class Observation:
    truth_index: int
    x: float
    y: float
    z: float
    depth: float
    confidence: float
    stamp: float


@dataclass
class Sample:
    t: float
    x: float
    y: float
    yaw: float
    vx: float
    wz: float


@dataclass
class RunLog:
    name: str
    poses: list[Sample] = field(default_factory=list)
    scans: list[tuple[float, np.ndarray]] = field(default_factory=list)          # (t, ranges)
    maps: list[tuple[float, np.ndarray, float, float]] = field(default_factory=list)   # (t, cells int8, ox, oy)
    observations: list[Observation] = field(default_factory=list)
    junction_visits: list[tuple[str, float, float, float, float]] = field(default_factory=list)


def tour_samples(waypoints: list[tuple[float, float]], start_yaw: float, t0: float, rng: random.Random) -> list[Sample]:
    """Constant-speed straight legs with turns on the spot, plus a small side-to-side wander."""
    out: list[Sample] = []
    t, yaw = t0, start_yaw
    x, y = waypoints[0]
    for (ax, ay), (bx, by) in zip(waypoints, waypoints[1:]):
        heading = math.atan2(by - ay, bx - ax)
        turn = math.atan2(math.sin(heading - yaw), math.cos(heading - yaw))
        steps = int(abs(turn) / (TURN_RATE * DT))
        for _ in range(steps):
            yaw += math.copysign(TURN_RATE * DT, turn)
            out.append(Sample(t, x, y, yaw, 0.0, math.copysign(TURN_RATE, turn)))
            t += DT
        yaw = heading
        length = math.hypot(bx - ax, by - ay)
        n = max(1, int(length / (SPEED * DT)))
        phase = rng.uniform(0, 6.28)
        for i in range(1, n + 1):
            s = i / n
            wobble = 0.07 * math.sin(phase + i * DT * 0.9) * math.sin(math.pi * s)
            x = ax + (bx - ax) * s - math.sin(heading) * wobble
            y = ay + (by - ay) * s + math.cos(heading) * wobble
            out.append(Sample(t, x, y, heading, SPEED, 0.0))
            t += DT
        x, y = bx, by
    for _ in range(20):                       # a short pause at the end, as the mission node saves the map
        out.append(Sample(t, x, y, yaw, 0.0, 0.0))
        t += DT
    return out


class World:
    def __init__(self, solid: np.ndarray, origin_x: float, origin_y: float):
        self.solid = solid
        self.ox, self.oy = origin_x, origin_y
        self.h, self.w = solid.shape
        self.steps = np.arange(1, int(MAX_RANGE / RESOLUTION) + 1) * RESOLUTION
        self.angles = -math.pi + np.arange(RAYS) * (2 * math.pi / RAYS)
        self.hits = np.zeros(solid.size, dtype=np.int32)
        self.misses = np.zeros(solid.size, dtype=np.int32)

    def cast(self, x: float, y: float, yaw: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return ranges (inf where nothing), and the flat cell indices of the samples along each ray."""
        a = yaw + self.angles
        px = x + np.cos(a)[:, None] * self.steps[None, :]
        py = y + np.sin(a)[:, None] * self.steps[None, :]
        cols = np.clip(((px - self.ox) / RESOLUTION).astype(np.int32), 0, self.w - 1)
        rows = np.clip(((py - self.oy) / RESOLUTION).astype(np.int32), 0, self.h - 1)
        flat = rows * self.w + cols
        blocked = self.solid.ravel()[flat]
        any_hit = blocked.any(axis=1)
        first = np.where(any_hit, blocked.argmax(axis=1), len(self.steps))
        ranges = np.where(any_hit, self.steps[np.minimum(first, len(self.steps) - 1)], np.inf)
        return ranges, flat, first

    def integrate(self, x: float, y: float, yaw: float, ranges: np.ndarray) -> None:
        """Update hit/miss counts from a scan taken at a (slightly wrong) pose, like a SLAM map update."""
        a = yaw + self.angles
        finite = np.isfinite(ranges)
        n = np.where(finite, (ranges / RESOLUTION).astype(np.int32), len(self.steps))
        px = x + np.cos(a)[:, None] * self.steps[None, :]
        py = y + np.sin(a)[:, None] * self.steps[None, :]
        cols = ((px - self.ox) / RESOLUTION).astype(np.int32)
        rows = ((py - self.oy) / RESOLUTION).astype(np.int32)
        inside = (cols >= 0) & (cols < self.w) & (rows >= 0) & (rows < self.h)
        flat = rows * self.w + cols
        index = np.arange(len(self.steps))[None, :]
        # Rays with no return (dropouts, open space) clear nothing, as in SLAM Toolbox.
        free = inside & (index < (n[:, None] - 1)) & finite[:, None]
        hit = inside & (index == (n[:, None] - 1)) & finite[:, None]
        self.misses += np.bincount(flat[free], minlength=self.solid.size).astype(np.int32)
        self.hits += np.bincount(flat[hit], minlength=self.solid.size).astype(np.int32)

    def occupancy(self) -> np.ndarray:
        """int8 grid in the OccupancyGrid convention: -1 unknown, 0 free, 100 occupied. Row 0 is the lowest y."""
        total = self.hits + self.misses
        cells = np.full(self.solid.size, -1, dtype=np.int8)
        with np.errstate(invalid='ignore', divide='ignore'):
            ratio = np.where(total > 0, self.hits / np.maximum(total, 1), 0)
        cells[(self.misses > 0)] = 0
        cells[(self.hits >= 2) & (ratio > 0.25)] = 100
        return cells.reshape(self.h, self.w)

    def line_of_sight(self, x0: float, y0: float, x1: float, y1: float) -> bool:
        length = math.hypot(x1 - x0, y1 - y0)
        n = max(2, int(length / (RESOLUTION / 2)))
        ts = np.linspace(0.0, 1.0, n)[:-3]          # stop just short of the wall the landmark is fixed to
        cols = ((x0 + (x1 - x0) * ts - self.ox) / RESOLUTION).astype(np.int32)
        rows = ((y0 + (y1 - y0) * ts - self.oy) / RESOLUTION).astype(np.int32)
        return not self.solid[rows, cols].any()


def cropped(cells: np.ndarray, ox: float, oy: float, margin_cells: int = 20) -> tuple[np.ndarray, float, float]:
    """Crop to the known area, as SLAM Toolbox's map grows from the start point."""
    known = np.argwhere(cells >= 0)
    if known.size == 0:
        return cells[:1, :1], ox, oy
    r0, c0 = np.maximum(known.min(axis=0) - margin_cells, 0)
    r1, c1 = np.minimum(known.max(axis=0) + margin_cells + 1, cells.shape)
    return cells[r0:r1, c0:c1].copy(), ox + c0 * RESOLUTION, oy + r0 * RESOLUTION


def simulate_run(name: str, b: Building, world: World, t0: float, seed: int) -> RunLog:
    rng = random.Random(seed)
    nrng = np.random.default_rng(seed)
    label, sx, sy, syaw = b.entrances[name]
    samples = tour_samples(b.tours[name], syaw, t0, rng)
    log = RunLog(name, poses=samples)
    zone_junctions = {j: b.junctions[j] for j in b.zones[name]}
    seen_junctions: set[str] = set()
    # Systematic errors that averaging cannot remove: a camera yaw offset for the run (extrinsics) and a fixed offset
    # per landmark (where the box centre falls on the sign). These make the fused error realistic, not near zero.
    camera_yaw_error = nrng.normal(0.0, math.radians(1.5))
    landmark_bias = nrng.normal(0.0, 0.14, (len(b.landmarks), 2))
    next_map = t0 + 2.0
    for i, s in enumerate(samples):
        if i % SCAN_EVERY == 0:
            lx = s.x + math.cos(s.yaw) * LASER_OFFSET[0]
            ly = s.y + math.sin(s.yaw) * LASER_OFFSET[0]
            ranges, _flat, _first = world.cast(lx, ly, s.yaw)
            noisy = ranges + nrng.normal(0, RANGE_SIGMA, ranges.shape)
            noisy[nrng.random(ranges.shape) < 0.01] = np.inf          # dropouts (dark or glancing surfaces)
            log.scans.append((s.t, noisy.astype(np.float32)))
            jitter = nrng.normal(0, [0.012, 0.012, 0.004])
            world.integrate(lx + jitter[0], ly + jitter[1], s.yaw + jitter[2], noisy)
            if s.t >= next_map:
                cells, ox, oy = cropped(world.occupancy(), world.ox, world.oy)
                log.maps.append((s.t, cells, ox, oy))
                next_map += MAP_EVERY_S
        for jid, (jx, jy) in zone_junctions.items():
            if jid not in seen_junctions and math.hypot(s.x - jx, s.y - jy) < 0.35:
                seen_junctions.add(jid)
                log.junction_visits.append((jid, s.t, s.x, s.y, s.yaw))
        if i % 5 == 0:                                                  # the detector runs at 2 Hz
            for index, lm in enumerate(b.landmarks):
                dx, dy = lm.x - s.x, lm.y - s.y
                distance = math.hypot(dx, dy)
                if distance > CAMERA_RANGE or distance < 0.6:
                    continue
                bearing = math.atan2(dy, dx) - s.yaw
                if abs(math.atan2(math.sin(bearing), math.cos(bearing))) > CAMERA_FOV:
                    continue
                if rng.random() > 0.55 or not world.line_of_sight(s.x, s.y, lm.x, lm.y):
                    continue
                along = nrng.normal(0.06, 0.05 + 0.03 * distance)         # depth error grows with range
                across = nrng.normal(0, 0.06 + 0.015 * distance)
                across += distance * math.sin(camera_yaw_error)
                ux, uy = dx / distance, dy / distance
                bx, by = landmark_bias[index]
                log.observations.append(Observation(
                    index, lm.x + ux * along - uy * across + bx, lm.y + uy * along + ux * across + by,
                    lm.z + nrng.normal(0, 0.05), distance + along, float(np.clip(nrng.normal(0.82, 0.08), 0.4, 0.99)),
                    s.t))
    cells, ox, oy = cropped(world.occupancy(), world.ox, world.oy)
    log.maps.append((samples[-1].t, cells, ox, oy))
    return log


def odometry(samples: list[Sample], seed: int, start: tuple[float, float, float] | None = None
             ) -> list[tuple[float, float, float]]:
    """Dead-reckoned pose with a scale error and heading drift: what the EKF might report without SLAM."""
    rng = np.random.default_rng(seed)
    x, y, yaw = start if start else (samples[0].x, samples[0].y, samples[0].yaw)
    out = []
    previous = samples[0]
    for s in samples:
        dx, dy = s.x - previous.x, s.y - previous.y
        step = math.hypot(dx, dy) * 1.012
        dyaw = math.atan2(math.sin(s.yaw - previous.yaw), math.cos(s.yaw - previous.yaw)) * 1.01
        dyaw += 0.004 * step + rng.normal(0, 0.0004)
        direction = math.atan2(dy, dx) - previous.yaw if step > 0 else 0.0
        yaw += dyaw
        x += step * math.cos(yaw - dyaw + direction)
        y += step * math.sin(yaw - dyaw + direction)
        out.append((x, y, yaw))
        previous = s
    return out
