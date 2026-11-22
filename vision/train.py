# -*- coding: utf-8 -*-
"""
Train the YOLOv8 material + condition detector.

- Base: yolov8n.pt (nano, CPU-friendly), fine-tuned on vision/data/yolo.
- Classes: steel_new, steel_rusted, wood_new, wood_used, plastic_new,
  plastic_scrap.
- Output: vision/model/best.pt + vision/results/metrics.json (real mAP
  from YOLO validation on the held-out val split).

Run:  python train.py [--epochs 20] [--imgsz 320]
"""
import argparse
import json
import shutil
from pathlib import Path

from ultralytics import YOLO

ROOT = Path(__file__).parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--imgsz", type=int, default=320)
    ap.add_argument("--batch", type=int, default=8)
    args = ap.parse_args()

    model = YOLO("yolov8n.pt")
    model.train(data=str(ROOT / "data" / "dataset.yaml"),
                epochs=args.epochs, imgsz=args.imgsz, batch=args.batch,
                workers=1, device="cpu", project=str(ROOT / "runs"),
                name="train", exist_ok=True)

    metrics = model.val(data=str(ROOT / "data" / "dataset.yaml"),
                        imgsz=args.imgsz, device="cpu")
    results = {
        "model": "yolov8n fine-tuned",
        "epochs": args.epochs, "imgsz": args.imgsz,
        "map50": round(float(metrics.box.map50), 4),
        "map50_95": round(float(metrics.box.map), 4),
        "precision": round(float(metrics.box.mp), 4),
        "recall": round(float(metrics.box.mr), 4),
        "per_class": {model.names[i]: round(float(v), 4)
                      for i, v in enumerate(metrics.box.ap50)},
    }
    out = ROOT / "results"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    best = ROOT / "runs" / "train" / "weights" / "best.pt"
    (ROOT / "model").mkdir(parents=True, exist_ok=True)
    shutil.copy(best, ROOT / "model" / "best.pt")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
