"""Run detection and OCR over a folder of images and write a CSV. No ROS needed.

    python -m merz_perception.offline_batch --images frames/ --out results.csv --weights merz.pt

Used for O3 on recorded frames. --no-detector treats each image as a sign crop, to test OCR on its own.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Optional

import numpy as np

from merz_perception.engines import Detection, DetectorEngine, clip_box, make_engine
from merz_perception.ocr import OcrEngine, make_ocr, prepare_crop, read_room_number
from merz_perception.room_numbers import RoomNumberValidator
from merz_perception.sharpness import variance_of_laplacian

CSV_COLUMNS = ['image', 'label', 'confidence', 'x_min', 'y_min', 'x_max', 'y_max', 'sharpness', 'sharp_enough',
               'raw_text', 'ocr_confidence', 'room_number']
IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.bmp'}
# TODO: measure on rover (real sign format). A trailing letter is deliberately not allowed yet: it would let a misread
# like "M2.1O" pass as valid instead of being repaired to "M2.10". If real signs have one, add it here and in the YAML.
DEFAULT_ROOM_REGEX = r'[A-Z]?\d{1,2}\.?\d{1,3}'


def process_image(image_name: str, image: np.ndarray, detector: Optional[DetectorEngine],
                  ocr: Optional[OcrEngine], validator: RoomNumberValidator, min_sharpness: float,
                  sign_label: str = 'room_sign') -> list[dict]:
    """Return one CSV row per detection. With no detector, the whole image counts as one sign."""
    height, width = image.shape[:2]
    detections = (detector.detect(image) if detector is not None
                  else [Detection(sign_label, 1.0, 0, 0, width, height)])
    rows = []
    for detection in detections:
        x0, y0, x1, y1 = clip_box(detection, width, height, margin=0.1)
        crop = image[y0:y1, x0:x1]
        row = {
            'image': image_name, 'label': detection.label, 'confidence': round(detection.confidence, 4),
            'x_min': detection.x_min, 'y_min': detection.y_min, 'x_max': detection.x_max, 'y_max': detection.y_max,
            'sharpness': '', 'sharp_enough': '', 'raw_text': '', 'ocr_confidence': '', 'room_number': '',
        }
        if detection.label == sign_label and crop.size:
            sharpness = variance_of_laplacian(crop)
            sharp = sharpness >= min_sharpness
            row.update(sharpness=round(sharpness, 1), sharp_enough=sharp)
            if sharp and ocr is not None:
                result, room = read_room_number(ocr, prepare_crop(crop), validator)
                if result is not None:
                    row.update(raw_text=result.text, ocr_confidence=round(result.confidence, 4),
                               room_number=room or '')
        rows.append(row)
    return rows


def process_folder(folder: Path, csv_path: Path, detector: Optional[DetectorEngine], ocr: Optional[OcrEngine],
                   validator: RoomNumberValidator, min_sharpness: float) -> int:
    """Process every image in the folder in name order. Returns the number of rows written."""
    import cv2

    images = sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
    count = 0
    with open(csv_path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for path in images:
            image = cv2.imread(str(path))
            if image is None:
                print(f'Skipped unreadable image: {path.name}')
                continue
            for row in process_image(path.name, image, detector, ocr, validator, min_sharpness):
                writer.writerow(row)
                count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--images', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--engine', default='ultralytics', choices=['ultralytics', 'tensorrt'])
    parser.add_argument('--weights', help='Model file. Required unless --no-detector is given.')
    parser.add_argument('--no-detector', action='store_true', help='Treat every image as a sign crop.')
    parser.add_argument('--ocr', default='auto', choices=['auto', 'paddle', 'rapid'])
    parser.add_argument('--regex', default=DEFAULT_ROOM_REGEX)
    parser.add_argument('--min-sharpness', type=float, default=100.0)
    args = parser.parse_args()
    if not args.no_detector and not args.weights:
        parser.error('--weights is required unless --no-detector is given')

    detector = None if args.no_detector else make_engine(args.engine, args.weights)
    rows = process_folder(args.images, args.out, detector, make_ocr(args.ocr), RoomNumberValidator(args.regex),
                          args.min_sharpness)
    print(f'Wrote {rows} rows to {args.out}')


if __name__ == '__main__':
    main()
