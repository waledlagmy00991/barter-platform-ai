"""Fetch only the pinned licensed encoder at build time, never model training."""
import hashlib
import json
from pathlib import Path
from huggingface_hub import hf_hub_download

root=Path(__file__).resolve().parents[1]/'chatbot'/'encoder'
manifest=json.loads((root/'manifest.json').read_text())
for filename,digest in manifest['sha256'].items():
    path=Path(hf_hub_download(manifest['model'],filename,revision=manifest['revision'],local_dir=root))
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    if h.hexdigest()!=digest:raise RuntimeError('Downloaded encoder hash mismatch')
print('Pinned encoder artifacts verified. No training performed.')
