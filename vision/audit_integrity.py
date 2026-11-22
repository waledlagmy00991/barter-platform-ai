#!/usr/bin/env python3
"""Record reproducible evaluation evidence without training or evaluating weights."""
import collections
import csv
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
SNAP = ROOT / 'evaluation' / 'legacy62_v1'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def provenance():
    rows = collections.defaultdict(list)
    with (ROOT / 'data/provenance2.csv').open() as f:
        for row in csv.DictReader(f):
            rows[row['file']].append(row)
    return rows

def inventory(split, prov):
    result = []
    base = ROOT / 'data/yolo3'
    for image in sorted((base / 'images' / split).glob('*.jpg')):
        label = base / 'labels' / split / (image.stem + '.txt')
        cls, original = image.name.split('__', 1)
        rows = prov.get(original, [])
        result.append(dict(filename=image.name, material_class=cls,
            image_sha256=sha(image), label_sha256=sha(label),
            label_text=label.read_text(), provenance=rows,
            source_pages=sorted({r['source_page'] for r in rows}),
            source_domains=sorted({urlparse(r['source_page']).netloc.lower() for r in rows}),
            supplier_identity='UNVERIFIED: source page/domain is not supplier identity'))
    return result

def historical_membership(commit):
    d = json.loads(subprocess.check_output(['git', 'show', commit + ':vision/data/split_v1.json'], cwd=ROOT))
    pairs = {(c, name) for c, parts in d.items() for name in parts['val']}
    return d, pairs

def main():
    prov = provenance()
    records = {s: inventory(s, prov) for s in ('train', 'val')}
    if not SNAP.exists():
        for category in ('images', 'labels'):
            (SNAP / category).mkdir(parents=True)
            for f in sorted((ROOT / 'data/yolo3' / category / 'val').iterdir()):
                if f.suffix in ('.jpg', '.txt'):
                    shutil.copy2(f, SNAP / category / f.name)
        manifest = dict(status='QUARANTINED_REPRODUCIBILITY_ONLY',
            reason='Legacy selection set is adaptively reused and has provenance/group integrity failures.',
            classes=sorted(json.loads((ROOT / 'data/split_v1.json').read_text())),
            deployed_weights_sha256=sha(ROOT / 'models/material_v2_best.pt'),
            records=records['val'])
        (SNAP / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    manifest = json.loads((SNAP / 'manifest.json').read_text())
    for r in manifest['records']:
        assert sha(SNAP / 'images' / r['filename']) == r['image_sha256']
        assert sha(SNAP / 'labels' / (Path(r['filename']).stem + '.txt')) == r['label_sha256']
    assert sha(ROOT / 'models/material_v2_best.pt') == manifest['deployed_weights_sha256']
    fields = {}
    for key in ('source_pages', 'source_domains', 'image_sha256'):
        maps = {}
        for s, rows in records.items():
            m = collections.defaultdict(list)
            for r in rows:
                for value in (r[key] if isinstance(r[key], list) else [r[key]]):
                    m[value].append(r['filename'])
            maps[s] = m
        fields[key + '_overlap'] = [dict(value=v, train=maps['train'][v], val=maps['val'][v])
                                     for v in sorted(maps['train'].keys() & maps['val'].keys())]
        if key == 'image_sha256':
            fields['within_split_byte_duplicates'] = {s: [names for names in m.values() if len(names)>1] for s,m in maps.items()}
    history = []
    prev = None
    for commit in ('02766e7','cdd8e0c','f055f40','8fbc1ff','ddba5ab'):
        d, pairs = historical_membership(commit)
        history.append(dict(commit=commit, listed_entries=sum(len(p['val']) for p in d.values()),
            unique_examples=len(pairs), added=sorted(pairs-prev) if prev is not None else [],
            removed=sorted(prev-pairs) if prev is not None else []))
        prev = pairs
    report = dict(status='BLOCKED', counts={s:len(r) for s,r in records.items()},
        missing_provenance={s:[r['filename'] for r in rows if not r['provenance']] for s,rows in records.items()},
        overlap=fields, membership_history=history, records=records,
        deployed_weights_sha256=sha(ROOT / 'models/material_v2_best.pt'))
    (ROOT / 'evaluation/integrity_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='records'}, indent=2))

if __name__ == '__main__':
    main()
