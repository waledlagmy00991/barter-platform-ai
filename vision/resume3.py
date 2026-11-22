from ultralytics import YOLO
YOLO("runs/detect/runs/train3/weights/last.pt").train(resume=True)
