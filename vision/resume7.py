from ultralytics import YOLO
YOLO("runs/detect/runs/train7/weights/last.pt").train(resume=True)
