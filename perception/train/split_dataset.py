"""Split labelled photos into train/val by AREA, not by photo. PROPOSED.

    python train/split_dataset.py --src labelled/ --out ../data/merz_landmarks --val-areas F3-east

Why by area: photos of the same sign from 1 m and 2 m are near-duplicates. A random photo split puts one in train and
one in val, so the val score flatters the model (docs/planning/experiments.md, O3 threats: "hold back one corridor").

Expects photo names that start with an area tag, as in the checklist: <area>_<sign-or-landmark>_<nn>.jpg
(e.g. F3-east_M3.12_04.jpg), with a YOLO .txt label next to each image (Label Studio "YOLO" export or CVAT
"YOLO 1.1"). Images with no .txt are treated as background (no objects) and get an empty label file.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil

IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png'}


def area_of(image: Path) -> str:
    return image.stem.split('_', 1)[0]


def split(images: list[Path], val_areas: set[str]) -> tuple[list[Path], list[Path]]:
    val = [p for p in images if area_of(p) in val_areas]
    train = [p for p in images if area_of(p) not in val_areas]
    return train, val


def copy_split(paths: list[Path], out: Path, name: str) -> None:
    (out / 'images' / name).mkdir(parents=True, exist_ok=True)
    (out / 'labels' / name).mkdir(parents=True, exist_ok=True)
    for image in paths:
        shutil.copy2(image, out / 'images' / name / image.name)
        label = image.with_suffix('.txt')
        target = out / 'labels' / name / label.name
        if label.exists():
            shutil.copy2(label, target)
        else:
            target.write_text('', encoding='utf-8')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--src', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--val-areas', nargs='+', required=True, help='area tags held out for validation')
    args = parser.parse_args()
    images = sorted(p for p in args.src.rglob('*') if p.suffix.lower() in IMAGE_SUFFIXES)
    train, val = split(images, set(args.val_areas))
    if not train or not val:
        raise SystemExit(f'Empty split (train {len(train)}, val {len(val)}): check the area tags in file names')
    copy_split(train, args.out, 'train')
    copy_split(val, args.out, 'val')
    areas = sorted({area_of(p) for p in images})
    print(f'{len(train)} train / {len(val)} val images ({100 * len(val) / len(images):.0f}% val); areas: {areas}')


if __name__ == '__main__':
    main()
