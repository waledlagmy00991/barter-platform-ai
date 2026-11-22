from integrity_guard import require_authorized_execution
require_authorized_execution()
import random, shutil
from pathlib import Path
random.seed(7)
ROOT = Path(__file__).parent
RAW = ROOT/"data"/"raw2"; OUT = ROOT/"data"/"yolo2"
classes = sorted(d.name for d in RAW.iterdir() if d.is_dir())
if OUT.exists(): shutil.rmtree(OUT)
for split in ("train","val"):
    (OUT/"images"/split).mkdir(parents=True)
    (OUT/"labels"/split).mkdir(parents=True)
counts={}
for i,c in enumerate(classes):
    imgs = sorted(RAW.joinpath(c).glob("*.jpg"))
    random.shuffle(imgs)
    k = max(1, round(len(imgs)*0.15))
    val, train = imgs[:k], imgs[k:]
    counts[c]=(len(train),len(val))
    for split,files in (("train",train),("val",val)):
        for f in files:
            shutil.copy2(f, OUT/"images"/split/f"{c}__{f.name}")
            (OUT/"labels"/split/f"{c}__{f.stem}.txt").write_text(f"{i} 0.5 0.5 1.0 1.0\n")
yaml = "path: data/yolo2\ntrain: images/train\nval: images/val\nnames:\n" + "".join(f"  {i}: {c}\n" for i,c in enumerate(classes))
(ROOT/"data"/"dataset2.yaml").write_text(yaml)
print(len(classes),"classes"); print(counts)
