"""Build the Gazebo world (SDF) from the floor layout YAML, and check the layout. No ROS imports.

The layout is a list of straight walls with door gaps (worlds/merz_floor.yaml), which is far easier to read and change
than hundreds of lines of SDF. The SDF is generated at launch, for the chosen Gazebo version.

    python3 -m merz_sim.world_gen worlds/merz_floor.yaml --gz fortress -o /tmp/merz_floor.sdf
"""
from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
import math
from pathlib import Path
from xml.sax.saxutils import escape

import yaml

from merz_sim import gz_compat

CLOSED_DOOR_THICKNESS = 0.05   # m
CLOSED_DOOR_HEIGHT = 2.0       # m


@dataclass(frozen=True)
class Box:
    """An axis-aligned or rotated box resting on the floor."""
    name: str
    x: float
    y: float
    length: float   # along its own x
    width: float    # along its own y
    height: float
    yaw: float = 0.0
    kind: str = 'wall'   # wall, closed_door or obstacle (colour only)


@dataclass(frozen=True)
class Entrance:
    key: str
    x: float
    y: float
    yaw: float
    name: str


def load_layout(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text())


def _wall_pieces(start: tuple[float, float], end: tuple[float, float], doors: list[dict]) -> tuple[list, list]:
    """Split one wall at its doors. Returns ([(a, b) solid stretches], [(centre, width, closed)]) as distances along it."""
    length = math.dist(start, end)
    solid, gaps = [], []
    cursor = 0.0
    for door in sorted(doors, key=lambda d: d['at']):
        half = door['width'] / 2.0
        a, b = door['at'] - half, door['at'] + half
        if a < cursor - 1e-9 or b > length + 1e-9:
            raise ValueError(f'door at {door["at"]} m (width {door["width"]}) does not fit wall {start}->{end}')
        if a > cursor:
            solid.append((cursor, a))
        gaps.append((door['at'], door['width'], bool(door.get('closed', False))))
        cursor = b
    if cursor < length:
        solid.append((cursor, length))
    return solid, gaps


def boxes(layout: dict) -> list[Box]:
    """Every wall stretch, closed door panel and obstacle as a box."""
    thickness = layout['wall']['thickness']
    height = layout['wall']['height']
    result = []
    for index, wall in enumerate(layout['walls']):
        (x0, y0), (x1, y1) = wall['from'], wall['to']
        length = math.dist((x0, y0), (x1, y1))
        if length <= 0.0:
            raise ValueError(f'wall {index} has zero length')
        ux, uy = (x1 - x0) / length, (y1 - y0) / length
        yaw = math.atan2(uy, ux)
        solid, gaps = _wall_pieces((x0, y0), (x1, y1), wall.get('doors', []))
        for piece, (a, b) in enumerate(solid):
            # Solid stretches that reach a wall end are extended by half a thickness, so corners close.
            a_ext = a - thickness / 2 if a <= 1e-9 else a
            b_ext = b + thickness / 2 if b >= length - 1e-9 else b
            mid = (a_ext + b_ext) / 2
            result.append(Box(f'wall_{index}_{piece}', x0 + ux * mid, y0 + uy * mid, b_ext - a_ext, thickness,
                              height, yaw))
        for door, (centre, width, closed) in enumerate(gaps):
            if closed:
                result.append(Box(f'door_{index}_{door}', x0 + ux * centre, y0 + uy * centre, width,
                                  CLOSED_DOOR_THICKNESS, CLOSED_DOOR_HEIGHT, yaw, kind='closed_door'))
    for item in layout.get('obstacles', []):
        sx, sy, sz = item['size']
        result.append(Box(item['name'], item['centre'][0], item['centre'][1], sx, sy, sz, item.get('yaw', 0.0),
                          kind='obstacle'))
    return result


def entrances(layout: dict) -> dict[str, Entrance]:
    return {key: Entrance(key, float(e['x']), float(e['y']), float(e['yaw']), str(e.get('name', key)))
            for key, e in layout['entrances'].items()}


# ---------------------------------------------------------------- checks (used by the tests and by make_world)

def occupancy(layout: dict, resolution: float = 0.1, margin: float = 2.0):
    """Rasterise the boxes. Returns (grid of bools, origin_x, origin_y, resolution); True = occupied."""
    items = boxes(layout)
    corners = [_corners(b) for b in items]
    xs = [p[0] for c in corners for p in c]
    ys = [p[1] for c in corners for p in c]
    ox, oy = min(xs) - margin, min(ys) - margin
    nx = int(math.ceil((max(xs) + margin - ox) / resolution))
    ny = int(math.ceil((max(ys) + margin - oy) / resolution))
    grid = [[False] * nx for _ in range(ny)]
    for box in items:
        c, s = math.cos(box.yaw), math.sin(box.yaw)
        bx = [p[0] for p in _corners(box)]
        by = [p[1] for p in _corners(box)]
        for j in range(max(0, int((min(by) - oy) / resolution)), min(ny, int((max(by) - oy) / resolution) + 2)):
            for i in range(max(0, int((min(bx) - ox) / resolution)), min(nx, int((max(bx) - ox) / resolution) + 2)):
                px, py = ox + (i + 0.5) * resolution - box.x, oy + (j + 0.5) * resolution - box.y
                lx, ly = c * px + s * py, -s * px + c * py
                if abs(lx) <= box.length / 2 + resolution / 2 and abs(ly) <= box.width / 2 + resolution / 2:
                    grid[j][i] = True
    return grid, ox, oy, resolution


def _corners(box: Box) -> list[tuple[float, float]]:
    c, s = math.cos(box.yaw), math.sin(box.yaw)
    return [(box.x + c * dx - s * dy, box.y + s * dx + c * dy)
            for dx in (-box.length / 2, box.length / 2) for dy in (-box.width / 2, box.width / 2)]


def reachable(grid, ox: float, oy: float, resolution: float, x: float, y: float, clearance: float = 0.0):
    """Flood-fill free cells from (x, y), keeping `clearance` metres from anything occupied.

    Returns (set of (i, j) cells, touches_border). touches_border True means the area is open to the outside of the
    layout, so a frontier explorer would never finish.
    """
    ny, nx = len(grid), len(grid[0])
    radius = int(math.ceil(clearance / resolution))
    blocked = [row[:] for row in grid]
    if radius:
        offsets = [(di, dj) for di in range(-radius, radius + 1) for dj in range(-radius, radius + 1)
                   if di * di + dj * dj <= radius * radius]
        for j in range(ny):
            for i in range(nx):
                if grid[j][i]:
                    for di, dj in offsets:
                        if 0 <= j + dj < ny and 0 <= i + di < nx:
                            blocked[j + dj][i + di] = True
    start = (int((x - ox) / resolution), int((y - oy) / resolution))
    if blocked[start[1]][start[0]]:
        return set(), False
    seen, queue, border = {start}, deque([start]), False
    while queue:
        i, j = queue.popleft()
        if i in (0, nx - 1) or j in (0, ny - 1):
            border = True
        for ni, nj in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
            if 0 <= ni < nx and 0 <= nj < ny and not blocked[nj][ni] and (ni, nj) not in seen:
                seen.add((ni, nj))
                queue.append((ni, nj))
    return seen, border


# ---------------------------------------------------------------- SDF

_COLOURS = {'wall': '0.85 0.83 0.78 1', 'closed_door': '0.45 0.28 0.15 1', 'obstacle': '0.35 0.45 0.55 1'}


def _box_sdf(box: Box) -> str:
    size = f'{box.length:.4f} {box.width:.4f} {box.height:.4f}'
    colour = _COLOURS[box.kind]
    return f'''      <collision name="{box.name}_collision">
        <pose>{box.x:.4f} {box.y:.4f} {box.height / 2:.4f} 0 0 {box.yaw:.6f}</pose>
        <geometry><box><size>{size}</size></box></geometry>
      </collision>
      <visual name="{box.name}_visual">
        <pose>{box.x:.4f} {box.y:.4f} {box.height / 2:.4f} 0 0 {box.yaw:.6f}</pose>
        <geometry><box><size>{size}</size></box></geometry>
        <material><ambient>{colour}</ambient><diffuse>{colour}</diffuse></material>
      </visual>
'''


def world_sdf(layout: dict, gz_version: str = 'fortress', step_size: float = 0.002) -> str:
    """Return the complete SDF world. The robot is not in it; the launch file spawns it."""
    gz = gz_compat.version(gz_version)
    plugins = []
    for library, cls in gz_compat.WORLD_SYSTEMS:
        filename, name = gz_compat.system_plugin(gz, library, cls)
        body = '<render_engine>ogre2</render_engine>' if cls == 'Sensors' else ''
        plugins.append(f'    <plugin filename="{filename}" name="{name}">{body}</plugin>')
    geometry = ''.join(_box_sdf(b) for b in boxes(layout))
    return f'''<?xml version="1.0"?>
<!-- GENERATED by merz_sim/world_gen.py from {escape(Path(layout.get("_source", "merz_floor.yaml")).name)}. Edit the YAML, not this file. -->
<sdf version="1.8">
  <world name="{gz_compat.WORLD_NAME}">
    <physics name="default_physics" type="ignored">
      <max_step_size>{step_size}</max_step_size>
      <real_time_factor>1.0</real_time_factor>
    </physics>
{chr(10).join(plugins)}
    <scene>
      <ambient>0.6 0.6 0.6 1</ambient>
      <background>0.7 0.7 0.75 1</background>
      <shadows>false</shadows>
    </scene>
    <light type="directional" name="sun">
      <cast_shadows>false</cast_shadows>
      <pose>0 0 10 0 0 0</pose>
      <diffuse>0.9 0.9 0.9 1</diffuse>
      <specular>0.2 0.2 0.2 1</specular>
      <direction>-0.4 0.2 -0.9</direction>
    </light>
    <model name="ground_plane">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry><plane><normal>0 0 1</normal><size>200 200</size></plane></geometry>
        </collision>
        <visual name="visual">
          <geometry><plane><normal>0 0 1</normal><size>200 200</size></plane></geometry>
          <material><ambient>0.5 0.5 0.5 1</ambient><diffuse>0.5 0.5 0.5 1</diffuse></material>
        </visual>
      </link>
    </model>
    <model name="building">
      <static>true</static>
      <link name="link">
{geometry}      </link>
    </model>
  </world>
</sdf>
'''


def write_world(layout_file: str | Path, out_file: str | Path, gz_version: str = 'fortress') -> Path:
    layout = load_layout(layout_file)
    layout['_source'] = str(layout_file)
    out = Path(out_file).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(world_sdf(layout, gz_version))
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description='Write the Merz simulation world as SDF.')
    parser.add_argument('layout', nargs='?', help='layout YAML (default: the installed worlds/merz_floor.yaml)')
    parser.add_argument('--gz', default='fortress', choices=sorted(gz_compat.VERSIONS))
    parser.add_argument('-o', '--output', default='merz_floor.sdf')
    args = parser.parse_args(argv)
    layout = args.layout
    if layout is None:
        from ament_index_python.packages import get_package_share_directory   # only when run from ROS
        layout = Path(get_package_share_directory('merz_sim')) / 'worlds' / 'merz_floor.yaml'
    print(write_world(layout, args.output, args.gz))


if __name__ == '__main__':
    main()
