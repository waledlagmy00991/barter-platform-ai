from ultralytics import YOLO
from pathlib import Path
from PIL import Image, ImageDraw
import shutil
m = YOLO("models/material_v2_best.pt")
val = sorted(Path("data/yolo3/images/val").glob("*.jpg"))
rows=[]
for f in val:
    true = f.name.split("__")[0]
    r = m.predict(str(f), imgsz=320, verbose=False)[0]
    if len(r.boxes):
        b = r.boxes[0]
        pred = m.names[int(b.cls)]; conf = float(b.conf)
    else: pred, conf = "NO_DET", 0.0
    rows.append((f, true, pred, conf))
ok = sum(1 for _,t,p,_ in rows if t==p)
print(f"VAL TOP-1: {ok}/{len(rows)}")
cell=200; cols=6; import math
grid = Image.new("RGB",(cols*cell, math.ceil(len(rows)/cols)*cell),"white")
d = ImageDraw.Draw(grid)
for i,(f,t,p,c) in enumerate(rows):
    im = Image.open(f).convert("RGB"); im.thumbnail((cell,cell-24))
    x,y=(i%cols)*cell,(i//cols)*cell
    grid.paste(im,(x,y))
    mark = "OK" if t==p else "X"
    d.text((x+3,y+cell-22), f"{mark} T:{t[:14]} P:{p[:14]} {c:.2f}", fill="green" if t==p else "red")
grid.save("data/review/val_predictions_v4.jpg", quality=85)
for _,t,p,c in rows:
    if t!=p: print("MISS", t, "->", p, round(c,2))
