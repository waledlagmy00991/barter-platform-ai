#!/usr/bin/env python3
"""Create a non-destructive quarantine ledger. This does not build or approve a training set."""
import collections
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse, unquote, parse_qsl, urlencode, urlunparse

ROOT=Path(__file__).resolve().parent

def page_key(url):
    p=urlparse(url)
    host=p.netloc.lower().removeprefix('www.')
    query=urlencode([(k,v) for k,v in parse_qsl(p.query) if not k.startswith('utm_')])
    return urlunparse(('https',host,unquote(p.path).rstrip('/'),'',query,''))

def main():
    audit=json.loads((ROOT/'evaluation/integrity_audit.json').read_text())
    recovered=json.loads((ROOT/'evaluation/provenance_recovery.json').read_text())
    aliases={r['filename']:r for r in recovered['records'] if r['status']=='VERIFIED_RENAME_BY_ORIGINAL_BYTES'}
    rows=[]
    for split, records in audit['records'].items():
        for record in records:
            record=dict(record,legacy_split=split)
            if record['filename'] in aliases:
                recovery=aliases[record['filename']]
                record['recovery_evidence']=recovery
                record['source_pages']=sorted({c['source_page'] for c in recovery['candidates'] if c.get('exact_reencoded_match')})
            rows.append(record)
    parent=list(range(len(rows)))
    def find(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]]; i=parent[i]
        return i
    def merge(a,b):
        parent[find(a)]=find(b)
    keys={}
    for i,row in enumerate(rows):
        group_keys=['image-sha256:'+row['image_sha256']]+['source-page:'+page_key(p) for p in row['source_pages']]
        for key in group_keys:
            if key in keys: merge(i,keys[key])
            else: keys[key]=i
    components=collections.defaultdict(list)
    for i,row in enumerate(rows): components[find(i)].append(row)
    out=[]
    for members in components.values():
        gid='source-component-'+hashlib.sha256('\n'.join(sorted(r['filename'] for r in members)).encode()).hexdigest()[:16]
        hashlabels=collections.defaultdict(set)
        for row in members: hashlabels[row['image_sha256']].add(row['material_class'])
        cross=len({r['legacy_split'] for r in members})>1
        for row in members:
            reasons=['EGYPTIAN_MARKET_ORIGIN_UNVERIFIED','SUPPLIER_IDENTITY_UNVERIFIED','COMMERCIAL_REUSE_PERMISSION_UNVERIFIED','INDEPENDENT_REVIEW_PENDING']
            if not row['source_pages']: reasons.append('SOURCE_UNRESOLVED')
            if len(hashlabels[row['image_sha256']])>1: reasons.append('IDENTICAL_BYTES_CONFLICTING_LABELS')
            if cross: reasons.append('SOURCE_COMPONENT_CROSSES_LEGACY_SPLIT')
            if row['legacy_split']=='val': reasons.append('LEGACY_ADAPTIVELY_REUSED_SELECTION_MEMBER')
            row.update(state='QUARANTINED',eligible_for_training=False,eligible_for_final_audit=False,
                reasons=reasons,source_component_id=gid,supplier_id=None,
                group_caveat='A source component is a conservative linkage, not a verified supplier identity. Distinct components are not proof of independence.')
            out.append(row)
    report=dict(status='NO_APPROVED_TRAINING_POOL',originals_moved=False,originals_deleted=False,
        count=len(out),source_components=len(components),eligible_for_training=0,
        policy='No origin, supplier identity, semantic label or reuse grant is inferred from a filename, domain or recovered URL. Preserve legacy snapshots. A reviewer must resolve evidence before release.',
        records=sorted(out,key=lambda r:r['filename']))
    (ROOT/'evaluation/quarantine_ledger.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='records'},indent=2))

if __name__=='__main__': main()
