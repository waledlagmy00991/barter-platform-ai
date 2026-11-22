from integrity_guard import require_authorized_execution
require_authorized_execution()
import json, shutil
from pathlib import Path
from ultralytics import YOLO
ROOT = Path(__file__).parent
m = YOLO(str(ROOT/"runs/train/weights/best.pt"))
metrics = m.val(data=str(ROOT/"data/dataset.yaml"), imgsz=320, device="cpu")
res = {"model":"yolov8n fine-tuned","imgsz":320,
 "map50":round(float(metrics.box.map50),4),
 "map50_95":round(float(metrics.box.map),4),
 "precision":round(float(metrics.box.mp),4),
 "recall":round(float(metrics.box.mr),4),
 "per_class":{m.names[i]:round(float(v),4) for i,v in enumerate(metrics.box.ap50)}}
(ROOT/"results").mkdir(exist_ok=True)
json.dump(res, open(ROOT/"results/metrics.json","w"), ensure_ascii=False, indent=2)
(ROOT/"model").mkdir(exist_ok=True)
shutil.copy(ROOT/"runs/train/weights/best.pt", ROOT/"model/best.pt")
print(json.dumps(res, ensure_ascii=False))
