#!/usr/bin/env python3
"""Reconcile historical source-component counts. No data mutation or certification."""
import json
from pathlib import Path
from prepare_remediation import page_key

ROOT=Path(__file__).resolve().parent

def main():
    audit=json.loads((ROOT/'evaluation/integrity_audit.json').read_text())
    recovered=json.loads((ROOT/'evaluation/provenance_recovery.json').read_text())
    aliases={r['filename']:r for r in recovered['records'] if r['status']=='VERIFIED_RENAME_BY_ORIGINAL_BYTES'}
    rows=[row for split,records in audit['records'].items() for row in records]
    variants=[]
    for normalize in (False,True):
        for use_recovery in (False,True):
            parent=list(range(len(rows)));known={}
            def find(i):
                while parent[i]!=i:
                    parent[i]=parent[parent[i]];i=parent[i]
                return i
            for i,row in enumerate(rows):
                pages=row['source_pages']
                if use_recovery and row['filename'] in aliases:
                    pages=[r['source_page'] for r in aliases[row['filename']]['candidates'] if r.get('exact_reencoded_match')]
                keys=['sha:'+row['image_sha256']]+['page:'+(page_key(p) if normalize else p) for p in pages]
                for key in keys:
                    if key in known:parent[find(i)]=find(known[key])
                    else:known[key]=i
            variants.append(dict(normalized_pages=normalize,recovered_aliases_included=use_recovery,
                components=len({find(i) for i in range(len(rows))})))
    report=dict(variants=variants,explanation='The four-component reduction comes from four original-byte-verified provenance aliases, not URL normalization. None of these components establishes supplier identity.',
        perceptual_duplicate_constraints_not_merged_in_this_bookkeeping_count=True)
    (ROOT/'evaluation/grouping_reconciliation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
