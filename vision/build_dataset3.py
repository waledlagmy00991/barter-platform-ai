# Group-aware frozen split: images from the same source_page stay in the
# same split (no near-duplicate leakage between train and test).
import csv, json, random, shutil
from pathlib import Path
random.seed(11)
ROOT = Path(__file__).parent
RAW = ROOT/"data"/"raw2"; OUT = ROOT/"data"/"yolo3"
MANIFEST = ROOT/"data"/"split_v1.json"
classes = sorted(d.name for d in RAW.iterdir() if d.is_dir())
# file -> group (source_page)
groups = {}
with open(ROOT/"data"/"provenance2.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        groups[r["file"]] = r["source_page"]
if OUT.exists(): shutil.rmtree(OUT)
for split in ("train","val"):
    (OUT/"images"/split).mkdir(parents=True)
    (OUT/"labels"/split).mkdir(parents=True)
prev = {}
if MANIFEST.exists():
    prev = json.loads(MANIFEST.read_text())
# Global frozen assignment: a file that was val in ANY class stays val even
# if it moved class folders; a train file never becomes val.
prev_val_global = set()
for c, parts in prev.items():
    prev_val_global.update(parts.get("val", []))
prev_val_global = set(prev_val_global)  # dedupe (older manifests doubled entries)
manifest = {}
for i,c in enumerate(classes):
    by_group = {}
    for img in sorted(RAW.joinpath(c).glob("*.jpg")):
        by_group.setdefault(groups.get(img.name, "unknown:"+img.name), []).append(img)
    gnames = sorted(by_group)
    random.shuffle(gnames)
    # hold out ~20% of images, by whole groups (at least 1 group if class has 2+)
    n = sum(len(v) for v in by_group.values())
    cap = max(2, round(n*0.25))
    random.shuffle(gnames)
    gnames.sort(key=lambda g: len(by_group[g]))  # smallest groups first
    val_g = []
    vtot = 0
    for g in list(gnames):
        gs = len(by_group[g])
        remaining = n - vtot - gs
        if vtot == 0 or (vtot + gs <= cap and remaining >= max(4, vtot + gs)):
            val_g.append(g); vtot += gs
        if vtot >= cap: break
    train = [im for g in gnames for im in by_group[g]]
    val = [im for g in val_g for im in by_group[g]]
    if prev:  # frozen: keep prior assignments, new files go to train
        allf = {im.name: im for im in train}  # 'train' currently holds every file
        val = [im for name, im in sorted(allf.items()) if name in prev_val_global]
        train = [im for name, im in sorted(allf.items()) if name not in prev_val_global]
        val_g = sorted({groups.get(im.name, "unknown:"+im.name) for im in val})
    if not train and val:  # tiny class: keep one for train
        train, val = val[:1], val[1:]
    manifest[c] = {"train": sorted(im.name for im in train),
                   "val": sorted(im.name for im in val),
                   "val_groups": sorted(val_g)}
    for split,files in (("train",train),("val",val)):
        for f in files:
            shutil.copy2(f, OUT/"images"/split/f"{c}__{f.name}")
            (OUT/"labels"/split/f"{c}__{f.stem}.txt").write_text(f"{i} 0.5 0.5 1.0 1.0\n")
yaml = "path: data/yolo3\ntrain: images/train\nval: images/val\nnames:\n" + "".join(f"  {i}: {c}\n" for i,c in enumerate(classes))
(ROOT/"data"/"dataset3.yaml").write_text(yaml)
MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
print(len(classes), "classes; val per class:", {c: len(v["val"]) for c,v in manifest.items()})
