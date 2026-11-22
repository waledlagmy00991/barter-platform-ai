from integrity_guard import require_authorized_execution
require_authorized_execution()
from ultralytics import YOLO
YOLO("runs/detect/runs/train6/weights/last.pt").train(resume=True)
