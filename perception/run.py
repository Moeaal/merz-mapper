"""Run the PROPOSED sign-reading prototype on images, a folder, or a webcam, and write JSON.

    python run.py --source samples/synthetic --out results.json
    python run.py --source samples/synthetic/crops --ocr rapid    # if PaddleOCR cannot download its models
    python run.py --source photo.jpg --detector yoloe
    python run.py --source 0 --detector yoloe --show          # webcam 0; q to quit
    python run.py --source frames/ --detector yolo --weights merz_landmarks.pt

Output: a JSON list with one record per image (or per processed webcam frame), each with its detections, OCR lines,
room candidates and the best room number. Not ROS: a later `sign_reader_node` would wrap SignPipeline.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from merz_signs.pipeline import CONFIG_PATH, SignPipeline, load_settings, make_detector  # noqa: E402

IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}


def list_images(source: Path) -> list[Path]:
    if source.is_dir():
        return sorted(p for p in source.rglob('*') if p.suffix.lower() in IMAGE_SUFFIXES)
    return [source]


def run_webcam(pipeline: SignPipeline, index: int, every_s: float, show: bool) -> list[dict]:
    import cv2

    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        raise RuntimeError(f'Could not open camera {index}')
    records, last = [], 0.0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            now = time.time()
            if now - last >= every_s:      # OCR is slow on a CPU; do not process every frame
                last = now
                record = pipeline.process(frame, f'webcam{index}@{now:.2f}')
                records.append(record)
                if record['room_number']:
                    print(json.dumps({'time': round(now, 2), 'room_number': record['room_number']}))
                if show:
                    for det in record['detections']:
                        x1, y1, x2, y2 = det['box']
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 200, 0), 2)
                        cv2.putText(frame, f"{det['label']} {det.get('room_number') or ''}", (x1, max(15, y1 - 5)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 0), 2)
            if show:
                cv2.imshow('merz signs (q to quit)', frame)
                if cv2.waitKey(1) & 0xFF in (ord('q'), 27):
                    break
    finally:
        cap.release()
        if show:
            cv2.destroyAllWindows()
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--source', required=True, help='image file, folder, or webcam index (e.g. 0)')
    parser.add_argument('--out', type=Path, default=Path('results.json'))
    parser.add_argument('--config', type=Path, default=CONFIG_PATH)
    parser.add_argument('--detector', choices=['none', 'yoloe', 'yolo'], help='override detector.mode in config')
    parser.add_argument('--weights', help='override detector.weights in config')
    parser.add_argument('--conf', type=float, help='override detector.confidence in config')
    parser.add_argument('--pattern', action='append', help='override room_patterns (repeatable)')
    parser.add_argument('--ocr', choices=['paddle', 'rapid', 'auto'], default='paddle',
                        help='OCR engine (rapid = PP-OCR models via ONNX Runtime, bundled in the pip wheel)')
    parser.add_argument('--no-raw-text', action='store_true',
                        help='do not store raw OCR lines (signs may carry staff names)')
    parser.add_argument('--every', type=float, default=1.0, help='webcam: seconds between processed frames')
    parser.add_argument('--show', action='store_true', help='webcam: show a preview window')
    args = parser.parse_args()

    settings = load_settings(args.config)
    if args.detector:
        settings.detector['mode'] = args.detector
    if args.weights:
        settings.detector['weights'] = args.weights
    if args.conf is not None:
        settings.detector['confidence'] = args.conf
    if args.pattern:
        settings.room_patterns = args.pattern
    settings.keep_raw_text = not args.no_raw_text

    from merz_signs.ocr import make_ocr
    pipeline = SignPipeline(settings, make_detector(settings), make_ocr(args.ocr))

    if args.source.isdigit():
        records = run_webcam(pipeline, int(args.source), args.every, args.show)
    else:
        import cv2

        records = []
        for path in list_images(Path(args.source)):
            image = cv2.imread(str(path))
            if image is None:
                print(f'skip (unreadable): {path}', file=sys.stderr)
                continue
            start = time.perf_counter()
            record = pipeline.process(image, path.name)
            record['seconds'] = round(time.perf_counter() - start, 3)
            records.append(record)
            print(f"{path.name}: {record['room_number']}  ({record['seconds']} s)")
    args.out.write_text(json.dumps(records, indent=2), encoding='utf-8')
    print(f'Wrote {len(records)} records to {args.out}')


if __name__ == '__main__':
    main()
