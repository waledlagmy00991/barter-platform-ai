from ultralytics import YOLO
YOLO("runs/detect/runs/train6/weights/last.pt").train(resume=True)
