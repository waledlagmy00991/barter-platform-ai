from ultralytics import YOLO
import json
m = YOLO("models/material_v2_best.pt")
r = m.val(data="data/dataset2.yaml", imgsz=320, device="cpu", plots=True)
per = {}
for i, name in enumerate(m.names.values()):
    try:
        p = float(r.box.p[i]); rec = float(r.box.r[i]); ap = float(r.box.ap50[i])
    except Exception: p=rec=ap=0.0
    per[name] = {"precision": round(p,3), "recall": round(rec,3), "ap50": round(ap,3)}
out = {"map50": round(float(r.box.map50),4), "map50_95": round(float(r.box.map),4),
       "precision": round(float(r.box.mp),4), "recall": round(float(r.box.mr),4),
       "val_images": 36, "per_class": per,
       "epochs": 30, "model": "yolov8n", "imgsz": 320, "classes": len(per)}
json.dump(out, open("metrics_v2.json","w"), indent=1)
print(json.dumps({k:v for k,v in out.items() if k!="per_class"}, indent=1))
for k,v in sorted(per.items(), key=lambda x:x[1]["ap50"]): print(k, v)
