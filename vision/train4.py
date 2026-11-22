from ultralytics import YOLO
m = YOLO("yolov8n.pt")
m.train(data="data/dataset3.yaml", epochs=30, imgsz=320, batch=8, workers=1,
        device="cpu", project="runs", name="train4", exist_ok=True,
        lr0=0.003, lrf=0.01, mosaic=1.0, fliplr=0.5, seed=3)
