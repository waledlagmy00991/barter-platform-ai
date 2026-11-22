# -*- coding: utf-8 -*-
"""
Top-up harvester: Wikimedia Commons + khurda.net images for the new
Egyptian-market class taxonomy.

Classes (Egyptian market types/grades — each type its own class so the
model can verify or reject a seller's claimed type):
  steel_rebar (حديد تسليح)      steel_sheet (صاج/لفائف)
  steel_sections (كمر/زوايا)    steel_pipes (مواسير حديد)
  steel_scrap (حديد خردة)
  wood_zan (خشب زان)            wood_swed (خشب سويد/موسكي)
  plywood (أبلكاش)              mdf (MDF)
  plastic_jerrican (جراكن)      plastic_shredded (بلاستيك مجروش)
  plastic_pet (بلاستيك شفاف PET)
  copper_red (نحاس أحمر)        copper_scrap (نحاس خردة/مخلوط)
  brass (نحاس أصفر)
  aluminum_soft (طري/كانز)      aluminum_profile (ناشف/قطاعات)
  aluminum_shavings (رايش)
  cement_bags (شكاير أسمنت)     brick_red (طوب أحمر)
  brick_white (طوب أبيض)        sand (رمل)     gravel (زلط/سن)

Sources per image are recorded in vision/data/provenance2.csv with the
exact source page URL, image URL, license and the query used. Commons
images are CC/PD-licensed; khurda.net images come from an Egyptian
scrap-price site (editorial photos of the Egyptian market) and are used
for training only, flagged license=site-editorial.

Egyptian-market listing photos (openSooq) are harvested separately via
harvest_opensooq results JSON and merged by build_dataset.py.
"""
import csv
import io
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw2"
PROV = ROOT / "data" / "provenance2.csv"

CLASSES = ["steel_rebar", "steel_sheet", "steel_sections", "steel_pipes",
           "steel_scrap", "wood_zan", "wood_swed", "plywood", "mdf",
           "plastic_jerrican", "plastic_shredded", "plastic_pet",
           "copper_red", "copper_scrap", "brass", "aluminum_soft",
           "aluminum_profile", "aluminum_shavings", "cement_bags",
           "brick_red", "brick_white", "sand", "gravel"]

# Commons search queries per class (English works best there)
QUERIES = {
    "steel_rebar": ["rebar bundle", "steel reinforcement bars stack",
                    "rebar construction", "reinforcing steel rods pile",
                    "rebar cage construction site", "steel rebar rust"],
    "steel_sheet": ["steel coils", "steel sheet roll factory",
                    "galvanized steel coil"],
    "steel_sections": ["steel beams stack", "H-beam steel",
                       "angle iron steel bars", "steel girders yard",
                       "I-beam stack"],
    "steel_pipes": ["steel pipes stack", "metal pipes pile yard",
                    "steel tubes warehouse", "black steel pipes"],
    "steel_scrap": ["scrap iron", "steel scrap yard", "iron scrap heap",
                    "scrap metal pile", "ferrous scrap"],
    "wood_zan": ["beech wood planks", "beech lumber stack",
                 "beech boards", "beech timber"],
    "wood_swed": ["pine planks stack", "pine boards lumber",
                  "spruce lumber stack", "pine timber planks",
                  "softwood boards stack"],
    "plywood": ["plywood sheets stack", "plywood boards pile",
                "plywood panels stack"],
    "mdf": ["MDF boards", "medium density fibreboard stack",
            "MDF panels stack"],
    "plastic_jerrican": ["plastic jerrycans", "plastic jerrican pile",
                         "used plastic containers cans"],
    "plastic_shredded": ["shredded plastic", "plastic flakes recycling",
                         "plastic granules recycled"],
    "plastic_pet": ["PET bottles bales", "plastic bottles recycling bale",
                    "compressed PET bottles"],
    "copper_red": ["bright copper wire scrap", "copper wire coil bare",
                   "copper rods", "copper cathode"],
    "copper_scrap": ["copper scrap", "copper scrap metal yard",
                     "mixed copper scrap"],
    "brass": ["brass scrap", "brass fittings", "brass taps",
              "brass valves"],
    "aluminum_soft": ["aluminium cans scrap", "aluminum cans bale",
                      "aluminium pots"],
    "aluminum_profile": ["aluminium extrusion profiles stack",
                         "aluminium profiles warehouse",
                         "aluminium extrusion factory"],
    "aluminum_shavings": ["metal swarf aluminium", "aluminium turnings",
                          "metal shavings machining", "swarf pile"],
    "cement_bags": ["cement bags", "cement sacks stack",
                    "cement bags warehouse"],
    "brick_red": ["red bricks stack", "clay bricks pile",
                  "red bricks Egypt"],
    "brick_white": ["sand-lime bricks stack", "aerated concrete blocks",
                    "autoclaved aerated concrete blocks",
                    "concrete blocks stack"],
    "sand": ["sand pile construction", "sand quarry pile",
             "building sand heap"],
    "gravel": ["gravel pile", "crushed stone aggregate pile",
               "construction aggregate", "aggregate quarry pile"],
}

PER_CLASS = 40
UA = {"User-Agent": "barter-ai-university-project/1.0 (educational)"}

KHURDA_PAGES = {  # Egyptian scrap-market editorial photos
    # NOTE: /scrap-copper/ and /scrap-aluminum/ URLs are unverified;
    # re-enable after checking they exist (khurda image downloads hung once).
    "steel_scrap": [],
    "copper_red": [],
    "copper_scrap": [],
    "aluminum_soft": [],
    "plastic_shredded": [],
}


def _get(url, tries=4):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as f:
                return f.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < tries - 1:
                wait = 8 * (attempt + 1)
                print(f"  429 rate-limited, waiting {wait}s")
                time.sleep(wait)
            else:
                raise


def commons_search(query, limit=20):
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"filetype:bitmap {query}", "gsrnamespace": 6,
        "gsrlimit": limit, "prop": "imageinfo",
        "iiprop": "url|extmetadata", "iiurlwidth": 800,
    }
    url = ("https://commons.wikimedia.org/w/api.php?"
           + urllib.parse.urlencode(params))
    data = json.loads(_get(url))
    time.sleep(2.5)
    pages = (data.get("query") or {}).get("pages") or {}
    out = []
    for p in pages.values():
        ii = (p.get("imageinfo") or [{}])[0]
        meta = ii.get("extmetadata") or {}
        lic = (meta.get("LicenseShortName") or {}).get("value", "")
        out.append({"thumb": ii.get("thumburl") or ii.get("url"),
                    "page": ii.get("descriptionurl"), "license": lic})
    return out


def khurda_images(page_url):
    html = _get(page_url).decode("utf-8", "ignore")
    srcs = re.findall(r'<img[^>]+src="([^"]+)"', html)
    out = []
    for s in srcs:
        if s.startswith("/"):
            s = "https://khurda.net" + s
        if "khurda.net" in s and re.search(r"\.(jpe?g|png|webp)", s, re.I):
            if any(b in s for b in ("logo", "icon", "avatar")):
                continue
            out.append(s)
    return out


def save_image(blob, path):
    img = Image.open(io.BytesIO(blob)).convert("RGB")
    if min(img.size) < 150:
        return False
    img.save(path, quality=90)
    return True


def main():
    import sys
    start = time.time()
    budget = float(sys.argv[1]) if len(sys.argv) > 1 else 100.0
    only = sys.argv[2].split(",") if len(sys.argv) > 2 else None
    RAW.mkdir(parents=True, exist_ok=True)
    new_prov = not PROV.exists()
    prov_f = open(PROV, "a", newline="", encoding="utf-8")
    prov_w = csv.DictWriter(prov_f, fieldnames=[
        "class", "file", "source_page", "image_url", "license", "query"])
    if new_prov:
        prov_w.writeheader()

    # never re-fetch a URL we have ever harvested (incl. deleted junk)
    seen = set()
    if PROV.exists():
        with open(PROV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                u = row.get("image_url")
                if u:
                    seen.add(u)
    print(f"seen-urls loaded: {len(seen)}")
    for cls in CLASSES:
        if only and cls not in only:
            continue
        if time.time() - start > budget:
            print(f"time budget reached, stopping before {cls}")
            break
        cdir = RAW / cls
        cdir.mkdir(parents=True, exist_ok=True)
        got = len(list(cdir.glob("*.jpg")))
        target = PER_CLASS
        # khurda.net first (Egyptian market look)
        for page in KHURDA_PAGES.get(cls, []):
            if got >= target:
                break
            try:
                for img_url in khurda_images(page):
                    if got >= target:
                        break
                    try:
                        blob = _get(img_url)
                        name = f"{cls}_k{got:03d}.jpg"
                        if save_image(blob, cdir / name):
                            prov_w.writerow({
                                "class": cls, "file": name,
                                "source_page": page, "image_url": img_url,
                                "license": "site-editorial",
                                "query": "khurda.net"})
                            prov_f.flush()
                            got += 1
                            time.sleep(0.3)
                    except Exception:
                        continue
            except Exception as e:
                print(f"[{cls}] khurda failed {page}: {e}")
        # Commons top-up
        for q in QUERIES[cls]:
            if got >= target:
                break
            try:
                results = commons_search(q)
            except Exception as e:
                print(f"[{cls}] search failed '{q}': {e}")
                continue
            for r in results:
                if got >= target or not r["thumb"]:
                    continue
                if r["thumb"] in seen:
                    continue
                if time.time() - start > budget:
                    break
                try:
                    blob = _get(r["thumb"])
                    name = f"{cls}_c{got:03d}.jpg"
                    if save_image(blob, cdir / name):
                        prov_w.writerow({
                            "class": cls, "file": name,
                            "source_page": r["page"],
                            "image_url": r["thumb"],
                            "license": r["license"], "query": q})
                        prov_f.flush()
                        got += 1
                        time.sleep(0.2)
                except Exception:
                    continue
        print(f"[{cls}] total {got}")
    prov_f.close()


if __name__ == "__main__":
    main()
