from ultralytics import YOLO
m = YOLO("models/material_v2_best.pt")
m.train(data="data/dataset3.yaml", epochs=40, imgsz=320, batch=8, workers=1,
        device="cpu", project="runs", name="train7", exist_ok=True,
        lr0=0.001, lrf=0.01, mosaic=1.0, fliplr=0.5, seed=3)
