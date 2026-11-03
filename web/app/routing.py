"""Shortest routes over the junction graph, and turn directions. No web or database code here."""
from __future__ import annotations

from dataclasses import dataclass
import heapq
import math
from typing import Iterable, Optional


@dataclass(frozen=True)
class Junction:
    id: int
    x: float
    y: float


def nearest_junction(junctions: Iterable[Junction], x: float, y: float) -> Optional[Junction]:
    return min(junctions, key=lambda j: math.hypot(j.x - x, j.y - y), default=None)


def shortest_path(edges: Iterable[tuple[int, int, float]], allowed: set[int], start: int,
                  goal: int) -> Optional[tuple[list[int], float]]:
    """Dijkstra's algorithm, only passing through allowed junctions. Returns (junction ids, length) or None.

    Restricting to allowed junctions is what stops a route passing through a door the visitor cannot open.
    """
    if start not in allowed or goal not in allowed:
        return None
    neighbours: dict[int, list[tuple[int, float]]] = {}
    for a, b, length in edges:
        if a in allowed and b in allowed:
            neighbours.setdefault(a, []).append((b, length))
            neighbours.setdefault(b, []).append((a, length))
    best = {start: 0.0}
    previous: dict[int, int] = {}
    queue = [(0.0, start)]
    while queue:
        distance, node = heapq.heappop(queue)
        if node == goal:
            path = [goal]
            while path[-1] != start:
                path.append(previous[path[-1]])
            return path[::-1], distance
        if distance > best[node]:
            continue
        for neighbour, length in neighbours.get(node, []):
            candidate = distance + length
            if candidate < best.get(neighbour, math.inf):
                best[neighbour] = candidate
                previous[neighbour] = node
                heapq.heappush(queue, (candidate, neighbour))
    return None


def turn_direction(before: tuple[float, float], at: tuple[float, float], after: tuple[float, float],
                   straight_tolerance_deg: float = 30.0) -> str:
    """Return "left", "right", "straight" or "back". The map frame has y to the left of x, so positive angles are left."""
    heading_in = math.atan2(at[1] - before[1], at[0] - before[0])
    heading_out = math.atan2(after[1] - at[1], after[0] - at[0])
    change = math.degrees(math.atan2(math.sin(heading_out - heading_in), math.cos(heading_out - heading_in)))
    if abs(change) <= straight_tolerance_deg:
        return 'straight'
    if abs(change) >= 180.0 - straight_tolerance_deg:
        return 'back'
    return 'left' if change > 0 else 'right'


def describe_steps(path: list[Junction], room: str, start_xy: tuple[float, float]) -> list[str]:
    """Return one instruction per junction on the path. The start position gives the first heading."""
    instructions = []
    for index, junction in enumerate(path):
        if index == len(path) - 1:
            instructions.append(f'Room {room} is close to this junction.')
            continue
        before = (path[index - 1].x, path[index - 1].y) if index else start_xy
        if before == (junction.x, junction.y):
            instructions.append('Head towards the next junction shown.')
            continue
        direction = turn_direction(before, (junction.x, junction.y), (path[index + 1].x, path[index + 1].y))
        instructions.append({'straight': 'Continue straight on.', 'left': 'Turn left.', 'right': 'Turn right.',
                             'back': 'Turn around.'}[direction])
    return instructions
