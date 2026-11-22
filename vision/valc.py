from ultralytics import YOLO
import json, sys, os
m = YOLO(sys.argv[1] if len(sys.argv)>1 else "runs/detect/runs/train5/weights/best.pt")
r = m.val(data="data/dataset3.yaml", imgsz=320, device="cpu")
per = {}
for i, name in enumerate(m.names.values()):
    try: p=float(r.box.p[i]); rec=float(r.box.r[i]); ap=float(r.box.ap50[i])
    except Exception: p=rec=ap=0.0
    per[name] = {"precision": round(p,3), "recall": round(rec,3), "ap50": round(ap,3)}
out = {"map50": round(float(r.box.map50),4), "map50_95": round(float(r.box.map),4),
       "precision": round(float(r.box.mp),4), "recall": round(float(r.box.mr),4),
       "val_images": len(os.listdir("data/yolo3/images/val")),
       "model_file": sys.argv[1] if len(sys.argv)>1 else "train5/best.pt",
       "model": "yolov8n", "imgsz": 320, "classes": len(per), "per_class": per}
json.dump(out, open("metrics_candidate.json","w"), indent=1)
print(json.dumps({k:v for k,v in out.items() if k!="per_class"}, indent=1))
for k,v in sorted(per.items(), key=lambda x:x[1]["ap50"]): print(k, v)
