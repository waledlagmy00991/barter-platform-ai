from ultralytics import YOLO
YOLO("runs/detect/runs/train4/weights/last.pt").train(resume=True)
