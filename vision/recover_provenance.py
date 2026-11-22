#!/usr/bin/env python3
"""Verify rename provenance candidates using fetched originals, without harvesting new samples."""
import csv
import hashlib
import json
from io import BytesIO
from pathlib import Path
import requests
from PIL import Image

ROOT=Path(__file__).resolve().parent

def digest(data):
    return hashlib.sha256(data).hexdigest()

def main():
    audit=json.loads((ROOT/'evaluation/integrity_audit.json').read_text())
    rows=list(csv.DictReader((ROOT/'data/provenance2.csv').open()))
    out=[]
    for split, filenames in audit['missing_provenance'].items():
        for name in filenames:
            suffix=name.split('_eg_')[-1]
            candidates=[r for r in rows if r['file'].endswith(suffix)]
            record=dict(split=split,filename=name,status='UNRESOLVED',candidates=[])
            local=ROOT/'data/yolo3/images'/split/name
            for row in candidates:
                item=dict(original_filename=row['file'],source_page=row['source_page'],image_url=row['image_url'])
                try:
                    response=requests.get(row['image_url'],timeout=(8,15))
                    item['http_status']=response.status_code
                    response.raise_for_status()
                    im=Image.open(BytesIO(response.content)).convert('RGB')
                    buf=BytesIO(); im.save(buf,format='JPEG',quality=90)
                    item['downloaded_original_sha256']=digest(response.content)
                    item['reencoded_sha256']=digest(buf.getvalue())
                    item['local_sha256']=digest(local.read_bytes())
                    item['exact_reencoded_match']=item['reencoded_sha256']==item['local_sha256']
                    if item['exact_reencoded_match']:
                        record['status']='VERIFIED_RENAME_BY_ORIGINAL_BYTES'
                except Exception as exc:
                    item['error_type']=type(exc).__name__
                record['candidates'].append(item)
            out.append(record)
    (ROOT/'evaluation/provenance_recovery.json').write_text(json.dumps(dict(records=out,
        caveat='Byte reconstruction verifies linkage to an image URL, not supplier identity, Egyptian origin, semantic label or reuse permission.'),ensure_ascii=False,indent=2))
    print(json.dumps([{k:v for k,v in r.items() if k!='candidates'} for r in out],indent=2))

if __name__=='__main__':
    main()
