#!/usr/bin/env python3
"""Cleanup pass for vision/data/raw2/<cls>/:
1. drop corrupt/unreadable/tiny images
2. dedupe by content hash (average hash, hamming <= 4)
3. render per-class contact sheets into vision/data/review/<cls>_gridN.jpg for visual QA
Usage: python3 cleanup_review.py [--apply]   (without --apply: report only, still renders grids)
"""
import os, sys, argparse
from PIL import Image

RAW = os.path.join(os.path.dirname(__file__), 'data', 'raw2')
REVIEW = os.path.join(os.path.dirname(__file__), 'data', 'review')
MIN_DIM = 120

def ahash(img, size=16):
    g = img.convert('L').resize((size, size))
    px = list(g.getdata())
    avg = sum(px) / len(px)
    bits = 0
    for i, p in enumerate(px):
        if p > avg: bits |= (1 << i)
    return bits

def ham(a, b): return bin(a ^ b).count('1')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    os.makedirs(REVIEW, exist_ok=True)
    total_removed = 0
    for cls in sorted(os.listdir(RAW)):
        d = os.path.join(RAW, cls)
        if not os.path.isdir(d): continue
        files = sorted(f for f in os.listdir(d) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')))
        kept, hashes = [], []
        removed = []
        for f in files:
            p = os.path.join(d, f)
            try:
                im = Image.open(p); im.load()
                if im.width < MIN_DIM or im.height < MIN_DIM:
                    removed.append((f, 'tiny')); continue
                h = ahash(im)
                if any(ham(h, hh) <= 4 for hh in hashes):
                    removed.append((f, 'dupe')); continue
                hashes.append(h); kept.append((f, im.size))
            except Exception:
                removed.append((f, 'corrupt'))
        if args.apply:
            for f, why in removed:
                os.remove(os.path.join(d, f))
        total_removed += len(removed)
        print(f'{cls}: kept {len(kept)} removed {len(removed)}')
        # render grids of kept files (20 per sheet) with filename labels
        from PIL import ImageDraw
        per = 20; cols = 5; cell = 260; lab = 22
        for si in range(0, len(kept), per):
            chunk = kept[si:si+per]
            rows = (len(chunk) + cols - 1) // cols
            sheet = Image.new('RGB', (cols * cell, rows * (cell + lab)), 'white')
            dr = ImageDraw.Draw(sheet)
            for i, (f, _) in enumerate(chunk):
                try:
                    im = Image.open(os.path.join(d, f)).convert('RGB')
                    im.thumbnail((cell, cell))
                    cx = (i % cols) * cell; cy = (i // cols) * (cell + lab)
                    x = cx + (cell - im.width) // 2
                    y = cy + (cell - im.height) // 2
                    sheet.paste(im, (x, y))
                    dr.text((cx + 4, cy + cell + 4), f[:38], fill='black')
                except Exception: pass
            sheet.save(os.path.join(REVIEW, f'{cls}_grid{si//per+1}.jpg'), quality=85)
    print('TOTAL removed:', total_removed, '(apply=%s)' % args.apply)

if __name__ == '__main__':
    main()
