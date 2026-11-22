# -*- coding: utf-8 -*-
"""Local retrieval over a historical synthetic demo corpus, never live inventory."""
import hashlib
import os
import json
import sys
import threading
from pathlib import Path
import faiss
import numpy as np

ROOT=Path(__file__).parent
REPO=ROOT.parent
sys.path.insert(0,str(REPO))
_model=None
_index=None
_ads=None
_LOAD_LOCK=threading.Lock()
DEMO_NOTICE='دي أمثلة تجريبية مولّدة، مش عروض تجار فعلية. الأسعار مصطنعة للتجربة، مش عروض بيع أو أسعار تعتمد عليها.'


def _validate_query(query,k):
    if not isinstance(query,str) or not query.strip() or len(query)>10000:
        raise ValueError('query must contain 1 to 10000 characters')
    if isinstance(k,bool) or not isinstance(k,int) or not 1<=k<=20:
        raise ValueError('k must be an integer from 1 to 20')


def _load():
    global _model,_index,_ads
    with _LOAD_LOCK:
        if _model is None:
            meta=json.loads((ROOT/'index/synthetic_demo_ads_meta.json').read_text())
            if meta.get('data_origin')!='synthetic_demo':
                raise RuntimeError('Corpus origin is unverified; retrieval is disabled')
            corpus=ROOT/'data/synthetic_demo_ads.jsonl'
            index_path=ROOT/'index/synthetic_demo_ads.faiss'
            if hashlib.sha256(corpus.read_bytes()).hexdigest()!=meta.get('corpus_sha256'):
                raise RuntimeError('Demo corpus hash differs from index metadata')
            if hashlib.sha256(index_path.read_bytes()).hexdigest()!=meta.get('index_sha256'):
                raise RuntimeError('Demo index hash differs from metadata')
            ads=meta['ads']
            if ads!=[json.loads(line) for line in corpus.read_text().splitlines() if line.strip()]:
                raise RuntimeError('Demo corpus and metadata rows differ')
            if not all(a.get('synthetic') is True and a.get('inventory_verified') is False for a in ads):
                raise RuntimeError('Every demo record must be marked synthetic and non-actionable')
            index=faiss.read_index(str(ROOT/'index/synthetic_demo_ads.faiss'))
            if index.ntotal!=len(ads) or meta['n']!=len(ads):
                raise RuntimeError('Index and corpus counts differ')
            if os.getenv('BARTER_EMBEDDING_BACKEND') == 'onnx':
                from chatbot.onnx_encoder import OnnxEncoder
                model=OnnxEncoder()
            else:
                from sentence_transformers import SentenceTransformer
                model=SentenceTransformer(meta['model'],local_files_only=True)
            dimension = getattr(model,'get_embedding_dimension',None) or model.get_sentence_embedding_dimension
            if dimension()!=index.d:
                raise RuntimeError('Embedding model and index dimensions differ')
            _model,_index,_ads=model,index,ads
    return _model,_index,_ads


def search(query,k=5):
    """Demo retrieval. Scores rank examples, not verified offers or calibrated probabilities."""
    _validate_query(query,k)
    from integration.pipeline import MATERIAL_ALIASES
    model,index,ads=_load()
    q=model.encode([query],normalize_embeddings=True)
    scores,ids=index.search(np.asarray(q,dtype='float32'),len(ads))
    ranked=[]
    for score,i in zip(scores[0],ids[0]):
        if i<0:
            continue
        ad=ads[int(i)]
        bonus=0.0
        for alias,canonical in MATERIAL_ALIASES.items():
            if alias in query and canonical==ad['material']:
                bonus+=0.25
                break
        loc=ad.get('location') or ''
        norm=lambda s:s.replace('ة','ه').replace('ى','ي')
        for candidate in {loc,loc.removeprefix('ال'),norm(loc),norm(loc).removeprefix('ال')}-{''}:
            if candidate in query or candidate in norm(query):
                bonus+=0.10
                break
        ranked.append((float(score)+bonus,float(score),ad))
    ranked.sort(key=lambda x:x[0],reverse=True)
    result=[]
    for total,semantic,ad in ranked[:k]:
        row=dict(ad)
        row.update(data_origin='synthetic_demo',synthetic=True,inventory_verified=False,
            is_actionable=False,price_origin='synthetic_not_a_quote',display_notice=DEMO_NOTICE,
            score=round(semantic,4),score_boosted=round(total,4),score_is_probability=False)
        result.append(row)
    return result


def _format_ad(ad):
    return ('مثال ديمو #{id}: {text} | الخامة: {material} ({condition})، '
            'الكمية: {quantity} {unit}، المكان: {location}، '
            'سعر تجريبي مصطنع: {synthetic_demo_asking_total_egp:,} جنيه.').format(**ad)


def answer_with_template(query,matches):
    if not matches or matches[0].get('score_boosted',matches[0].get('score',0))<0.35:
        return DEMO_NOTICE+'\nمفيش مثال تجريبي قريب. تسجيل الطلبات والتنبيهات مش متفعلين، وما اتسجلش طلب أو تنبيه.'
    lines=[DEMO_NOTICE,f'أقرب {len(matches)} أمثلة في الديمو:']
    lines.extend('- '+_format_ad(m) for m in matches)
    lines.append('دي نتيجة استرجاع تجريبية، مش تأكيد توافر أو حكم سعر. تسجيل الطلبات والتنبيهات مش متفعلين.')
    return '\n'.join(lines)


def answer(query,k=5):
    """Deterministic local RAG. Environment API keys never trigger a paid external call."""
    matches=search(query,k=k)
    return answer_with_template(query,matches),matches


def ask(query,k=5):
    text,_=answer(query,k=k)
    return text


if __name__=='__main__':
    print(ask(' '.join(sys.argv[1:]) or 'عايز ٢٠ طن حديد في العاشر'))
