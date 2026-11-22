# -*- coding: utf-8 -*-
"""Build only a clearly labeled synthetic demo index using a cached local model.

This does not ingest production inventory or generate new ads/prices.
"""
import hashlib
import json
from pathlib import Path
import faiss
import numpy as np

ROOT=Path(__file__).parent
MODEL_NAME='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'


def search_view(ad):
    if ad.get('synthetic') is not True or ad.get('inventory_verified') is not False:
        raise ValueError('This builder accepts explicitly synthetic demo records only')
    return (f"{ad['text']} | {ad['material']} {ad['quantity']} {ad['unit']} "
            f"{ad['location']} {ad['condition']} {ad['synthetic_demo_asking_total_egp']} جنيه")


def main():
    from sentence_transformers import SentenceTransformer
    corpus=ROOT/'data/synthetic_demo_ads.jsonl'
    ads=[json.loads(line) for line in corpus.read_text().splitlines() if line.strip()]
    views=[search_view(ad) for ad in ads]
    if not views:
        raise ValueError('Demo corpus is empty')
    model=SentenceTransformer(MODEL_NAME,local_files_only=True)
    embeddings=np.asarray(model.encode(views,normalize_embeddings=True,show_progress_bar=True),dtype='float32')
    index=faiss.IndexFlatIP(embeddings.shape[1]); index.add(embeddings)
    out=ROOT/'index'; out.mkdir(parents=True,exist_ok=True)
    temporary=out/'synthetic_demo_ads.faiss.tmp'
    faiss.write_index(index,str(temporary))
    meta=dict(model=MODEL_NAME,n=len(ads),ads=ads,data_origin='synthetic_demo',synthetic=True,
        inventory_verified=False,is_actionable=False,notifications_implemented=False,
        price_origin='synthetic_model_generated_not_a_quote',
        display_notice='ديمو مولّد، مش مخزون تجار أو عروض بيع.',
        corpus_sha256=hashlib.sha256(corpus.read_bytes()).hexdigest(),
        index_sha256=hashlib.sha256(temporary.read_bytes()).hexdigest())
    tmpmeta=out/'synthetic_demo_ads_meta.json.tmp'; tmpmeta.write_text(json.dumps(meta,ensure_ascii=False))
    temporary.replace(out/'synthetic_demo_ads.faiss'); tmpmeta.replace(out/'synthetic_demo_ads_meta.json')
    print('Indexed synthetic demo only:',len(ads))


if __name__=='__main__':main()
