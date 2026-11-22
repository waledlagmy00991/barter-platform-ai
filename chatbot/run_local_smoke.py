#!/usr/bin/env python3
"""One offline demo-retrieval smoke query, not a relevance benchmark."""
import hashlib
import json
import os
from pathlib import Path
import sys

for key in ('HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE','HF_HUB_DISABLE_TELEMETRY'):
    os.environ[key]='1'
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))


def main():
    from chatbot.chatbot import answer,DEMO_NOTICE
    text,matches=answer('عايز ٢٠ طن حديد',k=3)
    assert len(matches)==3
    assert DEMO_NOTICE in text
    assert all(m['synthetic'] and not m['inventory_verified'] and not m['is_actionable'] for m in matches)
    paths=['chatbot/chatbot.py','chatbot/run_local_smoke.py','chatbot/data/synthetic_demo_ads.jsonl',
           'chatbot/index/synthetic_demo_ads_meta.json','chatbot/index/synthetic_demo_ads.faiss']
    result=dict(status='LOCAL_SYNTHETIC_DEMO_FLOW_WORKS',query_count=1,result_count=len(matches),
        external_network_disabled=True,external_llm_called=False,inventory_verified=False,
        generated_new_ads_or_prices=False,faiss_rebuilt=False,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        caveat='One end-to-end smoke query. Not a real-inventory relevance benchmark, price validation or production-readiness result.')
    (ROOT/'chatbot/local_smoke.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
