# -*- coding: utf-8 -*-
"""
Download openSooq Egypt gallery images collected by the browser crawl
(JSON files passed as argv), into vision/data/raw2/<class>/, appending
provenance rows (source = the actual Egyptian listing URL) to
vision/data/provenance2.csv.
"""
import csv
import io
import json
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw2"
PROV = ROOT / "data" / "provenance2.csv"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) barter-ai-project/1.0"}


def main():
    new_prov = not PROV.exists()
    prov_f = open(PROV, "a", newline="", encoding="utf-8")
    prov_w = csv.DictWriter(prov_f, fieldnames=[
        "class", "file", "source_page", "image_url", "license", "query"])
    if new_prov:
        prov_w.writeheader()
    existing = set()
    with open(PROV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            existing.add(r["image_url"])

    for path in sys.argv[1:]:
        data = json.load(open(path, encoding="utf-8"))
        for cls, v in data.items():
            cdir = RAW / cls
            cdir.mkdir(parents=True, exist_ok=True)
            got = len(list(cdir.glob("*.jpg")))
            n_new = 0
            for lst in v["listings"]:
                for url in lst.get("gallery", []):
                    if url in existing:
                        continue
                    try:
                        req = urllib.request.Request(url, headers=UA)
                        with urllib.request.urlopen(req, timeout=30) as f:
                            blob = f.read()
                        img = Image.open(io.BytesIO(blob)).convert("RGB")
                        if min(img.size) < 150:
                            continue
                        name = f"{cls}_os{got:03d}.jpg"
                        img.save(cdir / name, quality=90)
                        prov_w.writerow({
                            "class": cls, "file": name,
                            "source_page": lst["href"], "image_url": url,
                            "license": "opensooq-listing-photo",
                            "query": "opensooq: " + (lst.get("alt") or "")[:60]})
                        prov_f.flush()
                        existing.add(url)
                        got += 1
                        n_new += 1
                        time.sleep(0.15)
                    except Exception:
                        continue
            print(f"[{cls}] +{n_new} (total {got})")
    prov_f.close()


if __name__ == "__main__":
    main()
