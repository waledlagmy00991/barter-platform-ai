from ultralytics import YOLO
YOLO("runs/train/weights/last.pt").train(resume=True)
