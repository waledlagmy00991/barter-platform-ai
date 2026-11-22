from ultralytics import YOLO
YOLO("runs/detect/runs/train2/weights/last.pt").train(resume=True)
