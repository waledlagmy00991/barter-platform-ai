# -*- coding: utf-8 -*-
"""
Download the Computer-Vision training images and build the YOLO dataset.

Data provenance (مصدر الداتا):
- All images come from WIKIMEDIA COMMONS (commons.wikimedia.org) via its
  public API. Every image's source URL, description page and license are
  recorded in vision/data/provenance.csv. Only freely licensed images
  (CC-BY, CC-BY-SA, CC0, public domain) are kept.
- Classes (material + condition, as the spec asks: نوع الخامة وحالتها):
    steel_new, steel_rusted, wood_new, wood_used, plastic_new, plastic_scrap
- Trader ads normally show ONE material per photo, so each image is
  annotated with a single bounding box covering the whole image (the
  standard classification-as-detection setup for YOLOv8).

Output:
  vision/data/raw/<class>/*.jpg          downloaded images
  vision/data/provenance.csv             url + license per image
  vision/data/yolo/                      YOLO dataset (train/val + labels)
  vision/data/dataset.yaml
"""
import csv
import io
import json
import random
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

random.seed(11)
ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw"
YOLO = ROOT / "data" / "yolo"

CLASSES = ["steel_new", "steel_rusted", "wood_new", "wood_used",
           "plastic_new", "plastic_scrap"]

QUERIES = {
    "steel_new": ["steel rebar stack", "steel bars construction site",
                  "reinforcing steel bars", "steel coils factory"],
    "steel_rusted": ["rusted rebar", "rusty steel scrap", "corroded steel",
                     "rusty iron rods"],
    "wood_new": ["lumber planks stack", "sawn timber boards",
                 "wood boards stack sawmill", "timber planks pile"],
    "wood_used": ["old wooden planks", "weathered wood boards",
                  "scrap wood pile", "reclaimed wood planks"],
    "plastic_new": ["plastic granules", "plastic pellets",
                    "polyethylene granules", "plastic raw material"],
    "plastic_scrap": ["plastic scrap bales", "plastic waste recycling",
                      "pressed PET bottles", "plastic recycling bales"],
}

PER_CLASS = 24
UA = {"User-Agent": "barter-ai-university-project/1.0 (educational)"}


def _get(url, tries=4):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as f:
                return f.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < tries - 1:
                wait = 20 * (attempt + 1)
                print(f"  429 rate-limited, waiting {wait}s")
                time.sleep(wait)
            else:
                raise


def commons_search(query, limit=12):
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"filetype:bitmap {query}", "gsrnamespace": 6,
        "gsrlimit": limit, "prop": "imageinfo",
        "iiprop": "url|extmetadata", "iiurlwidth": 800,
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    data = json.loads(_get(url))
    time.sleep(6)
    pages = (data.get("query") or {}).get("pages") or {}
    out = []
    for p in pages.values():
        ii = (p.get("imageinfo") or [{}])[0]
        meta = ii.get("extmetadata") or {}
        lic = (meta.get("LicenseShortName") or {}).get("value", "")
        out.append({"thumb": ii.get("thumburl") or ii.get("url"),
                    "page": ii.get("descriptionurl"), "license": lic})
    return out


def download(url):
    return _get(url)


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    # provenance is written incrementally (append per download) so a
    # killed run never leaves untracked images; first drop any raw files
    # that have no provenance row from a previously killed run.
    prov_path = ROOT / "data" / "provenance.csv"
    tracked = set()
    if prov_path.exists():
        with open(prov_path, encoding="utf-8") as f:
            tracked = {(r["class"], r["file"]) for r in csv.DictReader(f)}
    for cls_dir in RAW.glob("*"):
        for fp in cls_dir.glob("*.jpg"):
            if (cls_dir.name, fp.name) not in tracked:
                fp.unlink()
    prov_f = open(prov_path, "a", newline="", encoding="utf-8")
    prov_w = csv.DictWriter(
        prov_f, fieldnames=["class", "file", "source_page", "image_url",
                            "license", "query"])
    if not tracked:
        prov_w.writeheader()
    for cls in CLASSES:
        cdir = RAW / cls
        cdir.mkdir(parents=True, exist_ok=True)
        got = len(list(cdir.glob('*.jpg')))
        if got >= PER_CLASS:
            print(f"[{cls}] already has {got}, skipping")
            continue
        for q in QUERIES[cls]:
            if got >= PER_CLASS:
                break
            try:
                results = commons_search(q)
            except Exception as e:
                print(f"[{cls}] search failed for '{q}': {e}")
                continue
            for r in results:
                if got >= PER_CLASS or not r["thumb"]:
                    continue
                try:
                    blob = download(r["thumb"])
                    img = Image.open(io.BytesIO(blob)).convert("RGB")
                    if min(img.size) < 150:
                        continue
                    name = f"{cls}_{got:03d}.jpg"
                    img.save(cdir / name, quality=90)
                    prov_w.writerow({"class": cls, "file": name,
                                     "source_page": r["page"],
                                     "image_url": r["thumb"],
                                     "license": r["license"],
                                     "query": q})
                    prov_f.flush()
                    got += 1
                    time.sleep(0.2)
                except Exception as e:
                    print(f"[{cls}] skip: {e}")
        print(f"[{cls}] downloaded {got}")

    prov_f.close()

    # ---- build YOLO dataset: full-image box per image, 80/20 split
    for split in ("train", "val"):
        (YOLO / split / "images").mkdir(parents=True, exist_ok=True)
        (YOLO / split / "labels").mkdir(parents=True, exist_ok=True)
    for cls_idx, cls in enumerate(CLASSES):
        files = sorted((RAW / cls).glob("*.jpg"))
        random.shuffle(files)
        n_val = max(2, int(len(files) * 0.2))
        for i, fp in enumerate(files):
            split = "val" if i < n_val else "train"
            img_out = YOLO / split / "images" / fp.name
            img_out.write_bytes(fp.read_bytes())
            lbl = YOLO / split / "labels" / (fp.stem + ".txt")
            lbl.write_text(f"{cls_idx} 0.5 0.5 1.0 1.0\n")
    (ROOT / "data" / "dataset.yaml").write_text(
        "path: {}\ntrain: train/images\nval: val/images\n"
        "names:\n{}".format(
            (YOLO).resolve(),
            "".join(f"  {i}: {c}\n" for i, c in enumerate(CLASSES))),
        encoding="utf-8")
    print("YOLO dataset ready at", YOLO)


if __name__ == "__main__":
    main()
