from ultralytics import YOLO
YOLO("runs/detect/runs/train5/weights/last.pt").train(resume=True)
