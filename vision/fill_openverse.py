# -*- coding: utf-8 -*-
"""Fill missing classes from the Openverse API (CC-licensed images,
aggregates Wikimedia/Flickr/etc.). Same provenance CSV."""
import csv
import io
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw"
UA = {"User-Agent": "barter-ai-university-project/1.0 (educational)"}

TARGETS = {
    "wood_used": ["old wood planks", "scrap wood", "weathered boards",
                  "wood waste"],
    "plastic_new": ["plastic granules", "plastic pellets",
                    "polymer pellets", "plastic resin"],
    "plastic_scrap": ["plastic waste", "plastic bales recycling",
                      "PET bottles compressed", "plastic scrap"],
}
NEED = 24


def get(url, tries=4):
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=15) as f:
                return f.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and a < tries - 1:
                time.sleep(8 * (a + 1))
            else:
                raise


prov_path = ROOT / "data" / "provenance.csv"
prov_f = open(prov_path, "a", newline="", encoding="utf-8")
prov_w = csv.DictWriter(prov_f, fieldnames=["class", "file", "source_page",
                                            "image_url", "license", "query"])
for cls, queries in TARGETS.items():
    cdir = RAW / cls
    cdir.mkdir(parents=True, exist_ok=True)
    got = len(list(cdir.glob("*.jpg")))
    for q in queries:
        if got >= NEED:
            break
        try:
            u = ("https://api.openverse.org/v1/images/?" +
                 urllib.parse.urlencode({"q": q, "per_page": 20,
                                         "license_type": "all"}))
            data = json.loads(get(u))
        except Exception as e:
            print(cls, q, "search failed:", e)
            continue
        for item in data.get("results", []):
            if got >= NEED:
                break
            if not (item.get("thumbnail") or item.get("url")):
                continue
            try:
                blob = get(item.get("thumbnail") or item["url"])
                img = Image.open(io.BytesIO(blob)).convert("RGB")
                if min(img.size) < 150:
                    continue
                img.thumbnail((800, 800))
                name = f"{cls}_{got:03d}.jpg"
                img.save(cdir / name, quality=90)
                prov_w.writerow({
                    "class": cls, "file": name,
                    "source_page": item.get("foreign_landing_url"),
                    "image_url": item.get("url"),
                    "license": item.get("license"),
                    "query": "openverse: " + q})
                prov_f.flush()
                got += 1
                time.sleep(0.3)
            except Exception as e:
                print(cls, "skip:", e)
    print(cls, "->", got)
prov_f.close()
