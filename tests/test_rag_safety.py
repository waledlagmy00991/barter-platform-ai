"""Safety checks for demo retrieval, not retrieval relevance or production evaluation."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pytest
from chatbot import chatbot as rag
from chatbot import generate_ads

ROOT=Path(__file__).resolve().parents[1]/'chatbot'


def demo_rows():
    return [json.loads(line) for line in (ROOT/'data/synthetic_demo_ads.jsonl').read_text().splitlines()]


def test_demo_artifacts_are_explicit_and_consistent():
    rows=demo_rows()
    assert len(rows)==600
    meta=json.loads((ROOT/'index/synthetic_demo_ads_meta.json').read_text())
    assert rows==meta['ads']
    assert meta['data_origin']=='synthetic_demo'
    assert meta['inventory_verified'] is False
    for row in rows:
        assert row['synthetic'] is True
        assert row['inventory_verified'] is False
        assert row['is_actionable'] is False
        assert 'synthetic' in row['price_origin']
        assert 'total_price_egp' not in row
        assert 'fair_total_price_egp' not in row
        assert 'synthetic_demo_asking_total_egp' in row
    assert hashlib.sha256((ROOT/'data/synthetic_demo_ads.jsonl').read_bytes()).hexdigest()==meta['corpus_sha256']
    assert hashlib.sha256((ROOT/'index/synthetic_demo_ads.faiss').read_bytes()).hexdigest()==meta['index_sha256']
    migration=json.loads((ROOT/'data/synthetic_label_migration.json').read_text())
    assert meta['index_sha256']==migration['prior_files_sha256']['chatbot/index/ads.faiss']


@pytest.mark.parametrize('query,k',[('',5),(' ',5),('x'*10001,5),(None,5),('حديد',0),('حديد',21),('حديد',True),('حديد',1.2)])
def test_invalid_retrieval_input_rejected_before_model_load(query,k):
    with pytest.raises(ValueError):rag.search(query,k)


def test_search_results_cannot_look_like_verified_inventory(monkeypatch):
    rows=demo_rows()[:2]
    class Model:
        def encode(self,*args,**kwargs):return np.zeros((1,4))
    class Index:
        def search(self,*args,**kwargs):return np.array([[0.9,0.7]]),np.array([[0,1]])
    monkeypatch.setattr(rag,'_load',lambda:(Model(),Index(),rows))
    results=rag.search('حديد',2)
    assert len(results)==2
    for result in results:
        assert result['synthetic'] is True
        assert result['is_actionable'] is False
        assert result['score_is_probability'] is False
        assert result['display_notice']==rag.DEMO_NOTICE


def test_answers_explain_synthetic_prices_and_no_notifications(monkeypatch):
    matches=[dict(demo_rows()[0],score=0.9)]
    monkeypatch.setattr(rag,'search',lambda *a,**kw:matches)
    text,returned=rag.answer('حديد')
    assert rag.DEMO_NOTICE in text
    assert 'سعر تجريبي مصطنع' in text
    assert 'مش متفعلين' in text
    assert returned==matches


def test_no_match_does_not_claim_a_request_was_registered():
    text=rag.answer_with_template('حديد',[])
    assert 'ما اتسجلش طلب أو تنبيه' in text
    assert 'هننبهك' not in text


def test_environment_key_does_not_trigger_external_llm(monkeypatch):
    import urllib.request
    monkeypatch.setenv('GEMINI_API_KEY','not-a-real-key')
    def forbidden(*args,**kwargs):raise AssertionError('External LLM must not be called')
    monkeypatch.setattr(urllib.request,'urlopen',forbidden)
    monkeypatch.setattr(rag,'search',lambda *a,**kw:[])
    assert rag.DEMO_NOTICE in rag.ask('حديد')


def test_synthetic_generator_is_disabled_without_writing():
    corpus=ROOT/'data/synthetic_demo_ads.jsonl'
    before=corpus.read_bytes()
    with pytest.raises(RuntimeError,match='disabled'):
        generate_ads.main(1)
    assert corpus.read_bytes()==before
