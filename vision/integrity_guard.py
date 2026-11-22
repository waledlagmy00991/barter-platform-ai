"""Fail closed while the legacy dataset is under independent integrity review."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATUS = ROOT / 'evaluation' / 'execution_status.json'

def verify_snapshot():
    base = ROOT / 'evaluation/legacy62_v1'
    manifest = json.loads((base / 'manifest.json').read_text())
    expected = {'images': set(), 'labels': set()}
    for row in manifest['records']:
        for kind, filename, digest in (
            ('images', row['filename'], row['image_sha256']),
            ('labels', Path(row['filename']).stem + '.txt', row['label_sha256'])):
            expected[kind].add(filename)
            path = base / kind / filename
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise RuntimeError('Legacy snapshot changed: ' + str(path))
    for kind, names in expected.items():
        actual = {p.name for p in (base / kind).iterdir() if p.is_file()}
        if actual != names:
            raise RuntimeError('Unexpected snapshot membership in ' + kind)
    weights = ROOT / 'models/material_v2_best.pt'
    if hashlib.sha256(weights.read_bytes()).hexdigest() != manifest['deployed_weights_sha256']:
        raise RuntimeError('Deployed weights changed during integrity review')
    return manifest

def require_authorized_execution():
    verify_snapshot()
    status = json.loads(STATUS.read_text())
    if status.get('state') != 'INDEPENDENT_REVIEW_RELEASED':
        raise RuntimeError('Vision execution paused: integrity audit unresolved. See evaluation/README.md. No training, harvesting, dataset rebuild or metric overwrite is allowed.')
