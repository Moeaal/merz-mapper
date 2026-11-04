"""Believable placeholder photos for the synthetic run: corridor views at junctions and door-sign crops.

They are rendered from a simple 3D corridor (one-point perspective) with doors, ceiling lights, lift doors, notice boards
and exit signs, then given camera noise, vignetting and blur. Each image carries a small "SYNTHETIC" mark.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH, HEIGHT = 1280, 800
FOCAL = WIDTH * 0.52
CAM_H = 1.05                    # camera height on the mast (assumed)
HALF = 1.2
CEILING = 2.7
FAR = 26.0
BOLD = ['AtkinsonHyperlegible-Bold.ttf', 'arialbd.ttf', 'DejaVuSans-Bold.ttf', 'LiberationSans-Bold.ttf']
REGULAR = ['AtkinsonHyperlegible-Regular.ttf', 'arial.ttf', 'DejaVuSans.ttf', 'LiberationSans-Regular.ttf']


def font(size: int, bold: bool = False):
    for name in BOLD if bold else REGULAR:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


@dataclass
class Features:
    left_opening: tuple[float, float] | None = None     # depth range of a side corridor on the left
    right_opening: tuple[float, float] | None = None
    end_open: bool = False                               # corridor continues beyond the far end
    lift: str | None = None                              # 'left' or 'right'
    noticeboard: str | None = None
    exit_sign: bool = False
    stairs: bool = False
    doors: int = 4
    plates: tuple[str, ...] = ()
    tint: tuple[int, int, int] = (226, 224, 216)


def project(x: float, y: float, z: float, cx: float, cy: float) -> tuple[float, float]:
    return cx + FOCAL * x / z, cy - FOCAL * (y - CAM_H) / z


def quad(draw, pts3, cx, cy, fill, outline=None):
    draw.polygon([project(*p, cx, cy) for p in pts3], fill=fill, outline=outline)


def shade(colour, k):
    return tuple(max(0, min(255, int(c * k))) for c in colour)


def corridor_photo(path: Path, features: Features, seed: int, label: str) -> None:
    rng = random.Random(seed)
    cx = WIDTH / 2 + rng.uniform(-30, 30)
    cy = HEIGHT * 0.47 + rng.uniform(-12, 12)
    base = Image.new('RGB', (WIDTH, HEIGHT), (40, 40, 40))
    draw = ImageDraw.Draw(base)
    wall = features.tint
    floor = (rng.randint(150, 170), rng.randint(146, 160), rng.randint(136, 150))
    z0 = 0.35
    # Far end wall (or a dark continuation).
    end = (90, 92, 96) if features.end_open else shade(wall, 0.86)
    quad(draw, [(-HALF, 0, FAR), (HALF, 0, FAR), (HALF, CEILING, FAR), (-HALF, CEILING, FAR)], cx, cy, end)
    # Floor, ceiling and walls in strips, so lighting falls off with distance.
    strips = np.geomspace(z0, FAR, 60)
    for za, zb in zip(strips, strips[1:]):
        k = 0.78 + 0.22 * (1 - (zb / FAR) ** 0.5)
        quad(draw, [(-HALF, 0, za), (HALF, 0, za), (HALF, 0, zb), (-HALF, 0, zb)], cx, cy, shade(floor, k))
        quad(draw, [(-HALF, CEILING, za), (HALF, CEILING, za), (HALF, CEILING, zb), (-HALF, CEILING, zb)], cx, cy,
             shade((238, 238, 234), 0.85 + 0.15 * k))
        for side, opening in ((-1, features.left_opening), (1, features.right_opening)):
            if opening and opening[0] <= za <= opening[1]:
                continue
            quad(draw, [(side * HALF, 0, za), (side * HALF, CEILING, za), (side * HALF, CEILING, zb),
                        (side * HALF, 0, zb)], cx, cy, shade(wall, k * (0.93 if side > 0 else 1.0)))
    # Side openings: a darker corridor running away to the side.
    for side, opening in ((-1, features.left_opening), (1, features.right_opening)):
        if not opening:
            continue
        za, zb = opening
        quad(draw, [(side * HALF, 0, za), (side * HALF, 2.4, za), (side * HALF, 2.4, zb), (side * HALF, 0, zb)],
             cx, cy, shade(wall, 0.62))
        quad(draw, [(side * HALF, 0, zb), (side * HALF * 4, 0, zb), (side * HALF * 4, 2.4, zb), (side * HALF, 2.4, zb)],
             cx, cy, shade(wall, 0.72))
        quad(draw, [(side * HALF, 0, za), (side * HALF * 4, 0, za), (side * HALF * 4, 0, zb), (side * HALF, 0, zb)],
             cx, cy, shade(floor, 0.8))
    # Skirting boards.
    for side in (-1, 1):
        quad(draw, [(side * HALF, 0, z0), (side * HALF, 0.1, z0), (side * HALF, 0.1, FAR), (side * HALF, 0, FAR)],
             cx, cy, (70, 70, 74))
    # Doors and their plates.
    door_colours = [(122, 86, 58), (58, 88, 120), (138, 110, 74)]
    door_colour = rng.choice(door_colours)
    plates = list(features.plates)
    for i in range(features.doors):
        side = -1 if i % 2 == 0 else 1
        za = 2.2 + i * rng.uniform(2.6, 3.6)
        opening = features.left_opening if side < 0 else features.right_opening
        if za + 1.0 > FAR or (opening and opening[0] - 1.2 <= za <= opening[1] + 0.2):
            continue
        quad(draw, [(side * HALF, 0, za - 0.05), (side * HALF, 2.18, za - 0.05), (side * HALF, 2.18, za + 0.98),
                    (side * HALF, 0, za + 0.98)], cx, cy, (92, 92, 96))
        quad(draw, [(side * HALF, 0, za), (side * HALF, 2.12, za), (side * HALF, 2.12, za + 0.92),
                    (side * HALF, 0, za + 0.92)], cx, cy, door_colour)
        quad(draw, [(side * HALF, 1.45, za + 0.08), (side * HALF, 1.85, za + 0.08), (side * HALF, 1.85, za + 0.5),
                    (side * HALF, 1.45, za + 0.5)], cx, cy, (190, 210, 220))       # vision panel
        quad(draw, [(side * HALF, 1.35, za + 1.06), (side * HALF, 1.6, za + 1.06), (side * HALF, 1.6, za + 1.46),
                    (side * HALF, 1.35, za + 1.46)], cx, cy, (24, 38, 64))          # room plate
        if plates and za < 7:
            px, py = project(side * HALF, 1.5, za + 1.26, cx, cy)
            size = max(8, int(150 / (za + 1.26)))
            draw.text((px, py), plates.pop(0), fill=(240, 240, 240), anchor='mm', font=font(size, True))
    # Ceiling light panels.
    lights = Image.new('L', (WIDTH, HEIGHT), 0)
    lights_draw = ImageDraw.Draw(lights)
    for z in np.arange(1.6, FAR, 3.2):
        quad(lights_draw, [(-0.35, CEILING - 0.01, z), (0.35, CEILING - 0.01, z), (0.35, CEILING - 0.01, z + 1.2),
                           (-0.35, CEILING - 0.01, z + 1.2)], cx, cy, 255)
    # Floor reflections of the lights.
    reflections = Image.new('L', (WIDTH, HEIGHT), 0)
    reflections_draw = ImageDraw.Draw(reflections)
    for z in np.arange(1.6, FAR, 3.2):
        quad(reflections_draw, [(-0.3, 0.001, z), (0.3, 0.001, z), (0.3, 0.001, z + 1.0), (-0.3, 0.001, z + 1.0)],
             cx, cy, 120)
    base.paste((255, 255, 250), mask=lights)
    glow = lights.filter(ImageFilter.GaussianBlur(18))
    base = Image.composite(Image.new('RGB', base.size, (255, 252, 240)), base, glow.point(lambda v: int(v * 0.45)))
    base = Image.composite(Image.new('RGB', base.size, (238, 236, 228)), base,
                           reflections.filter(ImageFilter.GaussianBlur(9)).point(lambda v: int(v * 0.5)))
    draw = ImageDraw.Draw(base)
    # Notable objects that the walk-through instructions refer to.
    if features.lift:
        side = -1 if features.lift == 'left' else 1
        za = 3.0
        quad(draw, [(side * HALF, 0, za), (side * HALF, 2.25, za), (side * HALF, 2.25, za + 1.5),
                    (side * HALF, 0, za + 1.5)], cx, cy, (120, 124, 128))
        for k in (0.02, 0.76):
            quad(draw, [(side * HALF, 0.02, za + k), (side * HALF, 2.15, za + k), (side * HALF, 2.15, za + k + 0.72),
                        (side * HALF, 0.02, za + k + 0.72)], cx, cy, (176, 182, 188))
        quad(draw, [(side * HALF, 1.0, za + 1.62), (side * HALF, 1.25, za + 1.62), (side * HALF, 1.25, za + 1.72),
                    (side * HALF, 1.0, za + 1.72)], cx, cy, (40, 40, 44))
    if features.noticeboard:
        side = -1 if features.noticeboard == 'left' else 1
        za = 5.5
        quad(draw, [(side * HALF, 1.0, za), (side * HALF, 2.0, za), (side * HALF, 2.0, za + 1.8),
                    (side * HALF, 1.0, za + 1.8)], cx, cy, (176, 128, 84))
        for _ in range(9):
            a, h = rng.uniform(0.05, 1.45), rng.uniform(1.1, 1.75)
            colour = rng.choice([(245, 245, 240), (250, 230, 120), (180, 220, 250), (250, 190, 190)])
            quad(draw, [(side * HALF, h, za + a), (side * HALF, h + 0.22, za + a), (side * HALF, h + 0.22, za + a + 0.2),
                        (side * HALF, h, za + a + 0.2)], cx, cy, colour)
    if features.exit_sign:
        quad(draw, [(-0.3, 2.3, FAR - 0.5), (0.3, 2.3, FAR - 0.5), (0.3, 2.5, FAR - 0.5), (-0.3, 2.5, FAR - 0.5)],
             cx, cy, (20, 160, 80))
        quad(draw, [(-0.6, 2.25, 6.0), (0.6, 2.25, 6.0), (0.6, 2.55, 6.0), (-0.6, 2.55, 6.0)], cx, cy, (16, 150, 72))
        px, py = project(0, 2.4, 6.0, cx, cy)
        draw.text((px, py), 'EXIT  ➜', fill=(240, 255, 240), anchor='mm', font=font(26, True))
    if features.stairs:
        for k in range(8):
            y = 0.17 * k
            quad(draw, [(-HALF, y, FAR - 3 + k * 0.28), (HALF, y, FAR - 3 + k * 0.28), (HALF, y + 0.17, FAR - 3 + k * 0.28),
                        (-HALF, y + 0.17, FAR - 3 + k * 0.28)], cx, cy, shade((150, 150, 150), 0.8 + 0.03 * k))
    finish(base, label).save(path, quality=88)


def finish(image: Image.Image, label: str) -> Image.Image:
    """Camera look: soft focus, sensor noise, vignette, a slight colour cast, and the synthetic mark."""
    image = image.filter(ImageFilter.GaussianBlur(0.8))
    data = np.asarray(image).astype(np.float32)
    h, w = data.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot((xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2))
    data *= (1.0 - 0.28 * np.clip(r - 0.35, 0, None) ** 1.6)[..., None]
    data += np.random.default_rng(int(data.sum()) % 2 ** 32).normal(0, 4.5, data.shape)
    data[..., 2] *= 1.03
    image = Image.fromarray(np.clip(data, 0, 255).astype(np.uint8))
    draw = ImageDraw.Draw(image)
    draw.text((w - 18, h - 16), f'SYNTHETIC · {label}', fill=(255, 255, 255), anchor='rs', font=font(18, True))
    return image


ROOM_NAMES = ['Seminar room', 'Teaching lab', 'Meeting room', 'Office', 'Project lab', 'Study space', 'Workshop',
              'Robotics lab', 'Computer cluster', 'Tutorial room']


def sign_crop(path: Path, number: str, seed: int) -> None:
    """A door plate photographed by the sign camera: perspective, motion blur, noise."""
    rng = random.Random(seed)
    w, h = 520, 330
    wall = Image.new('RGB', (w, h), (rng.randint(205, 225), rng.randint(203, 220), rng.randint(195, 210)))
    plate = Image.new('RGB', (360, 200), (22, 38, 66) if rng.random() < 0.6 else (245, 245, 242))
    dark = plate.getpixel((0, 0))[0] < 100
    draw = ImageDraw.Draw(plate)
    ink = (245, 245, 245) if dark else (20, 30, 45)
    draw.rectangle([0, 0, 359, 199], outline=(140, 150, 160), width=4)
    draw.text((180, 86), number, fill=ink, anchor='mm', font=font(78, True))
    draw.text((180, 154), rng.choice(ROOM_NAMES), fill=ink, anchor='mm', font=font(26))
    wall.paste(plate, (80, 65))
    skew = rng.uniform(-30, 30)
    wall = wall.transform((w, h), Image.QUAD, (0 + skew, 0, 0 - skew, h, w + skew * 0.4, h, w - skew * 0.4, 0),
                          Image.BICUBIC)
    wall = wall.filter(ImageFilter.GaussianBlur(rng.uniform(0.6, 1.4)))
    data = np.asarray(wall).astype(np.float32)
    data += np.random.default_rng(seed).normal(0, 6, data.shape)
    finish_image = Image.fromarray(np.clip(data, 0, 255).astype(np.uint8))
    ImageDraw.Draw(finish_image).text((w - 10, h - 8), 'SYNTHETIC', fill=(255, 255, 255), anchor='rs',
                                      font=font(14, True))
    finish_image.save(path, quality=88)
