#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Discover Egyptian news price-article pages per material via DuckDuckGo HTML,
harvest article images into vision/data/raw2/<cls>/ with provenance.
Idempotent: skips image URLs already in provenance2.csv. Budget-limited."""
import csv, io, json, os, re, sys, time
import requests
from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, 'data', 'raw2')
PROV = os.path.join(BASE, 'data', 'provenance2.csv')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36',
      'Accept-Language': 'ar-EG,ar;q=0.9'}
DOMAINS = ['youm7.com', 'masrawy.com', 'elwatannews.com', 'cairo24.com',
           'almalnews.com', 'almasryalyoum.com', 'vetogate.com', 'egyin.com',
           'elfagr.org', 'misr365.com', 'akhbarelyom.com', 'aldostornews.com']
DENY = ['logo', 'icon', 'avatar', 'sprite', 'favicon', 'banner', '/ads/', 'ad-', 'whatsapp', 'facebook', 'twitter', 'youtube', 'play-badge', 'app-store']
IMG_RE = re.compile(r'(?:src|data-src|data-lazy-src|data-original)\s*=\s*["\']([^"\']+\.(?:jpg|jpeg|png|webp))(?:\?[^"\']*)?["\']', re.I)
OG_RE = re.compile(r'(?:property|name)=["\'](?:og:image|twitter:image)["\']\s+content=["\']([^"\']+)["\']', re.I)
RES_RE = re.compile(r'class="result__a"[^>]*href="([^"]+)"', re.I)

from urllib.parse import urljoin, urlparse, parse_qs

def ddg(q):
    try:
        r = requests.get('https://html.duckduckgo.com/html/', params={'q': q}, headers=UA, timeout=(5, 12))
        if r.status_code != 200:
            print('  ddg', r.status_code); return []
    except Exception as e:
        print('  ddg err', e); return []
    out = []
    for m in RES_RE.finditer(r.text):
        u = m.group(1)
        if 'uddg=' in u:
            u = parse_qs(urlparse(u).query).get('uddg', [u])[0]
        if any(d in u for d in DOMAINS):
            out.append(u)
    return out

def imgs_of(html, base):
    urls = []
    for rx in (OG_RE, IMG_RE):
        for m in rx.finditer(html):
            u = urljoin(base, m.group(1))
            if not any(b in u.lower() for b in DENY):
                urls.append(u)
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u); out.append(u)
    return out

def main():
    plan = json.load(open(sys.argv[1]))   # {"cls": ["query", ...]}
    budget = float(sys.argv[2]) if len(sys.argv) > 2 else 90
    start = time.time()
    seen = set()
    if os.path.exists(PROV):
        with open(PROV, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                seen.add(row.get('image_url', ''))
    prov_f = open(PROV, 'a', newline='', encoding='utf-8')
    prov_w = csv.writer(prov_f)
    for cls, queries in plan.items():
        cdir = os.path.join(RAW, cls); os.makedirs(cdir, exist_ok=True)
        pages = []
        for q in queries:
            if time.time() - start > budget: break
            pages += ddg(q); time.sleep(1.5)
        pages = list(dict.fromkeys(pages))[:4]
        print(f'[{cls}] pages={len(pages)}')
        for p in pages:
            if time.time() - start > budget:
                print('budget out'); prov_f.close(); return
            try:
                r = requests.get(p, headers=UA, timeout=(5, 12))
                if r.status_code != 200:
                    print('  page', r.status_code, urlparse(p).netloc); continue
            except Exception:
                continue
            got = 0
            for u in imgs_of(r.text, p):
                if got >= 8 or time.time() - start > budget: break
                if u in seen: continue
                try:
                    b = requests.get(u, headers=UA, timeout=(5, 12)).content
                    img = Image.open(io.BytesIO(b)).convert('RGB')
                    if min(img.size) < 200: continue
                    name = f'{cls}_nw_{len(os.listdir(cdir)):04d}.jpg'
                    img.save(os.path.join(cdir, name), quality=90)
                    prov_w.writerow([cls, name, p, u, 'news-editorial'])
                    prov_f.flush(); seen.add(u); got += 1
                    time.sleep(0.3)
                except Exception:
                    continue
            print(f'  +{got} {urlparse(p).netloc}')
            time.sleep(1)
    prov_f.close()

if __name__ == '__main__':
    main()
