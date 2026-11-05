"""Fine-tune a small YOLO model on the Merz Court photos. PROPOSED; not run (no labelled data exists yet).

    python train/train_yolo.py --data train/merz_landmarks.yaml            # laptop GPU or Google Colab
    python train/train_yolo.py --data train/merz_landmarks.yaml --device cpu --epochs 30   # slow smoke test

Starts from COCO-pretrained yolo11n.pt (the same model as tools/yolo_practice), so only the new classes are learnt.
Export to TensorRT is a separate step ON THE JETSON (engines are hardware- and TensorRT-version-specific;
RESEARCH_INDEX [N10]):
    yolo export model=best.pt format=engine quantize=16 imgsz=640
"""
from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--data', default='train/merz_landmarks.yaml')
    parser.add_argument('--model', default='yolo11n.pt', help='yolo11n.pt (fast) or yolo11s.pt (if n is too weak)')
    parser.add_argument('--epochs', type=int, default=100)
    parser.add_argument('--imgsz', type=int, default=640)
    parser.add_argument('--batch', type=int, default=16)
    parser.add_argument('--device', default=None, help='0 for the first GPU, cpu, or leave empty for auto')
    parser.add_argument('--name', default='merz_landmarks')
    args = parser.parse_args()

    from ultralytics import YOLO

    model = YOLO(args.model)
    model.train(data=args.data, epochs=args.epochs, imgsz=args.imgsz, batch=args.batch, device=args.device,
                patience=20,          # stop early if val mAP stops improving for 20 epochs
                fliplr=0.0,           # NO horizontal flips: they mirror the text on signs and exit arrows
                name=args.name)
    metrics = model.val()
    # Only classes that appear in the val set; Ultralytics fills the others with the mean, which misleads.
    present = [int(i) for i in metrics.box.ap_class_index]
    per_class = {model.names[i]: round(float(metrics.box.maps[i]), 3) for i in present}
    print('Per-class mAP50-95 (val classes only):', per_class)
    missing = sorted(set(model.names.values()) - {model.names[i] for i in present})
    if missing:
        print('No val examples for:', ', '.join(missing), '- collect more photos of these')
    print('Best weights: runs/detect/<name>/weights/best.pt')


if __name__ == '__main__':
    main()
