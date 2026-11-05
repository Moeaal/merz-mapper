"""Make SYNTHETIC door-sign photos to exercise the pipeline before real Merz Court photos exist. PROPOSED.

    python samples/make_synthetic_signs.py --out samples/synthetic

Writes <out>/scenes/*.jpg + YOLO .txt labels (a sign on a wall/door background, 3 views per sign: varied size, tilt,
blur, lighting),
<out>/crops/*.jpg (the sign alone) and <out>/truth_scenes.csv, <out>/truth_crops.csv (columns image,text,sign_id).
The room-number style (letter, digit, dot, two digits) is a GUESS, not the real Merz Court format. Results on these
images say nothing about O3; they only show that the code runs end to end.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import random

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONTS = ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
         '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf']
SUBTITLES = ['Seminar Room', 'Teaching Laboratory', 'Office', 'Meeting Room', 'Store', 'Computer Cluster', '']


def font(size: int, i: int = 0) -> ImageFont.FreeTypeFont:
    for path in FONTS[i:] + FONTS[:i]:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def make_sign(room: str, subtitle: str, rng: random.Random) -> np.ndarray:
    w, h = 420, 200
    bg = rng.choice([(245, 245, 240), (30, 60, 110), (40, 40, 40)])
    fg = (20, 20, 20) if sum(bg) > 400 else (250, 250, 250)
    img = Image.new('RGB', (w, h), bg)
    d = ImageDraw.Draw(img)
    d.rectangle([4, 4, w - 5, h - 5], outline=fg, width=3)
    d.text((24, 22), room, font=font(88, rng.randrange(3)), fill=fg)
    if subtitle:
        d.text((26, 140), subtitle, font=font(34, 1), fill=fg)
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def place_on_wall(sign: np.ndarray, rng: random.Random, scale: float, tilt_deg: float, blur: int,
                  gain: float) -> tuple[np.ndarray, list[str]]:
    H, W = 720, 960
    wall = np.full((H, W, 3), rng.choice([(200, 205, 210), (180, 190, 175), (215, 210, 200)]), np.uint8)
    wall = cv2.add(wall, np.random.default_rng(rng.randrange(1 << 30)).integers(0, 12, (H, W, 3), dtype=np.uint8))
    cv2.rectangle(wall, (520, 120), (860, 720), (90, 70, 50), -1)          # a door to the right
    cv2.circle(wall, (560, 430), 10, (160, 160, 160), -1)
    sh, sw = int(sign.shape[0] * scale), int(sign.shape[1] * scale)
    small = cv2.resize(sign, (sw, sh), interpolation=cv2.INTER_AREA)
    # Perspective: a sign seen from the side is narrower on the far edge.
    k = np.tan(np.radians(tilt_deg)) * 0.35
    src = np.float32([[0, 0], [sw, 0], [sw, sh], [0, sh]])
    dst = np.float32([[0, 0], [sw, sh * k], [sw, sh * (1 - k)], [0, sh]]) if k >= 0 else \
        np.float32([[0, -sh * k], [sw, 0], [sw, sh], [0, sh * (1 + k)]])
    warped = cv2.warpPerspective(small, cv2.getPerspectiveTransform(src, dst), (sw, sh),
                                 borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
    mask = cv2.warpPerspective(np.full((sh, sw), 255, np.uint8), cv2.getPerspectiveTransform(src, dst), (sw, sh))
    x0, y0 = rng.randint(40, max(41, 500 - sw)), rng.randint(150, max(151, 450 - sh))
    roi = wall[y0:y0 + sh, x0:x0 + sw]
    roi[mask > 0] = warped[mask > 0]
    if blur > 1:
        wall = cv2.GaussianBlur(wall, (blur | 1, blur | 1), 0)
    # YOLO labels (class cx cy w h, normalised) using train/merz_landmarks.yaml ids: 0 door, 4 door_sign.
    labels = [f'0 {690 / W:.5f} {420 / H:.5f} {340 / W:.5f} {600 / H:.5f}',
              f'4 {(x0 + sw / 2) / W:.5f} {(y0 + sh / 2) / H:.5f} {sw / W:.5f} {sh / H:.5f}']
    return np.clip(wall.astype(np.float32) * gain, 0, 255).astype(np.uint8), labels


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, default=Path(__file__).resolve().parent / 'synthetic')
    parser.add_argument('--signs', type=int, default=12)
    parser.add_argument('--seed', type=int, default=3094)
    args = parser.parse_args()
    rng = random.Random(args.seed)
    (args.out / 'scenes').mkdir(parents=True, exist_ok=True)
    (args.out / 'crops').mkdir(parents=True, exist_ok=True)
    rooms = sorted({f"M{rng.randint(1, 4)}.{rng.randint(1, 40):02d}" for _ in range(args.signs * 3)})[:args.signs]
    # Views roughly match the checklist: near/straight, mid/angled, far/dim (+blur).
    views = [(0.9, 0, 1, 1.0), (0.6, 25, 3, 0.85), (0.4, -35, 5, 0.6)]
    scene_rows, crop_rows = [], []
    for i, room in enumerate(rooms):
        sign = make_sign(room, rng.choice(SUBTITLES), rng)
        crop_name = f'sign{i:02d}.jpg'
        cv2.imwrite(str(args.out / 'crops' / crop_name), sign)
        crop_rows.append([crop_name, room, f's{i:02d}'])
        for v, (scale, tilt, blur, gain) in enumerate(views):
            name = f'sign{i:02d}_view{v}.jpg'
            scene, labels = place_on_wall(sign, rng, scale, tilt, blur, gain)
            cv2.imwrite(str(args.out / 'scenes' / name), scene)
            (args.out / 'scenes' / name).with_suffix('.txt').write_text('\n'.join(labels) + '\n', encoding='utf-8')
            scene_rows.append([name, room, f's{i:02d}'])
    for fname, rows in (('truth_scenes.csv', scene_rows), ('truth_crops.csv', crop_rows)):
        with open(args.out / fname, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerows([['image', 'text', 'sign_id'], *rows])
    print(f'Wrote {len(crop_rows)} crops and {len(scene_rows)} scenes to {args.out} (SYNTHETIC)')


if __name__ == '__main__':
    main()
