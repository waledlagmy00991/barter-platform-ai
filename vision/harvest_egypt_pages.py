#!/usr/bin/env python3
"""Harvest material photos from specific Egyptian web pages (news albums, supplier galleries, listings).
Usage: python3 harvest_egypt_pages.py <plan.json>
plan.json: [{"cls": "cement_bags", "url": "...", "must": ["اسمنت"|url-substring...], "deny": ["logo"...]}]
Downloads into vision/data/raw2/<cls>/, appends provenance to vision/data/provenance2.csv.
Idempotent: skips image URLs already in provenance2.csv.
"""
import json, os, re, sys, csv, hashlib
import requests
from urllib.parse import urljoin, urlparse

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, 'data', 'raw2')
PROV = os.path.join(BASE, 'data', 'provenance2.csv')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36',
      'Accept-Language': 'ar-EG,ar;q=0.9'}
IMG_RE = re.compile(r'(?:src|data-src|data-lazy-src|data-original)\s*=\s*["\']([^"\']+\.(?:jpg|jpeg|png|webp))(?:\?[^"\']*)?["\']', re.I)
OG_RE = re.compile(r'property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', re.I)
SRCSET_RE = re.compile(r'srcset=["\']([^"\']+)["\']', re.I)

def img_urls(html, base):
    urls = set()
    for m in IMG_RE.finditer(html):
        urls.add(urljoin(base, m.group(1)))
    for m in OG_RE.finditer(html):
        urls.add(m.group(1))
    for m in SRCSET_RE.finditer(html):
        for part in m.group(1).split(','):
            u = part.strip().split(' ')[0]
            if u: urls.add(urljoin(base, u))
    return urls

def main():
    plan = json.load(open(sys.argv[1]))
    seen = set()
    if os.path.exists(PROV):
        with open(PROV, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                seen.add(row.get('image_url', ''))
    prov_f = open(PROV, 'a', newline='', encoding='utf-8')
    prov_w = csv.writer(prov_f)
    if os.path.getsize(PROV) == 0 if os.path.exists(PROV) else True:
        prov_w.writerow(['class', 'filename', 'source_page', 'image_url', 'license'])
    for item in plan:
        cls, url = item['cls'], item['url']
        deny = item.get('deny', ['logo', 'icon', 'avatar', 'sprite', 'favicon', 'banner', 'ad-', '/ads/'])
        try:
            r = requests.get(url, headers=UA, timeout=(5,10))
            print(f'[{cls}] GET {url} -> {r.status_code} ({len(r.text)}b)')
            if r.status_code != 200: continue
        except Exception as e:
            print(f'[{cls}] GET fail {url}: {e}'); continue
        d = os.path.join(RAW, cls); os.makedirs(d, exist_ok=True)
        got = 0
        for u in img_urls(r.text, url):
            if got >= 10: break
            if u in seen: continue
            low = u.lower()
            if any(k in low for k in deny): continue
            try:
                ir = requests.get(u, headers=UA, timeout=(5,8))
                if ir.status_code != 200 or len(ir.content) < 12000: continue
                from io import BytesIO
                from PIL import Image
                im = Image.open(BytesIO(ir.content)); im.load()
                if im.width < 200 or im.height < 200: continue
                fn = f'{cls}_eg_{hashlib.md5(u.encode()).hexdigest()[:8]}.jpg'
                im.convert('RGB').save(os.path.join(d, fn), quality=90)
                prov_w.writerow([cls, fn, url, u, 'page-image'])
                seen.add(u); got += 1
            except Exception:
                continue
        prov_f.flush()
        print(f'[{cls}] +{got} from {urlparse(url).netloc}')
    prov_f.close()

if __name__ == '__main__':
    main()
