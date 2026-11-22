import os
os.environ.setdefault('BARTER_EMBEDDING_BACKEND','onnx')
from fastapi.testclient import TestClient
from telegram_demo import server
from telegram_demo.conversation import Conversation
import pytest

@pytest.fixture(autouse=True)
def legacy_ner_for_legacy_conversation(monkeypatch):
    # These baseline tests preserve the original saved model's behavior.
    # The replacement model is tested separately in test_telegram_proposals.
    import spacy
    import integration.pipeline as pipeline
    monkeypatch.setattr(pipeline,'_NER',spacy.load(pipeline.ROOT/'ner'/'model'))


def test_start_discloses_approach_and_simulation():
    out=Conversation().reply(1,'/start')
    assert 'FAISS' in out and 'محاكاة' in out and 'مش موديل محادثة' in out


def test_price_multiturn():
    c=Conversation()
    assert 'إجمالي' in c.reply(1,'/price عندي ٣٠ طن حديد تسليح جديد في القاهرة')
    out=c.reply(1,'1200000')
    assert '1,200,000' in out and '1,158,733' in out
    assert 'مش سعر سوق مباشر' in out


def test_missing_condition_not_assumed():
    c=Conversation()
    assert 'حالة الخامة' in c.reply(1,'/price عندي ٣٠ طن حديد تسليح في القاهرة')
    assert 'إجمالي' in c.reply(1,'مستعمل')
    assert 'condition_unsupported' in c.reply(1,'1200000')


def test_kg_conversion():
    c=Conversation()
    c.reply(1,'/price عندي ٥٠ كيلو حديد خردة هالك في القاهرة')
    out=c.reply(1,'1000')
    assert '1,024.52' in out


def test_bag_mass_never_guessed():
    c=Conversation();c.reply(1,'/price عندي ٥٠ شيكارة اسمنت جديد في القاهرة')
    assert 'quantity_unit_missing_or_unsupported' in c.reply(1,'20000')


def test_unknown_material_asks():
    assert 'حدّد نوع' in Conversation().reply(1,'عايز ٥ طن خشب')


def test_unsupported_media_does_not_run_vision():
    assert 'مش مدعومين' in Conversation().reply(1,None)


def test_total_only_rejects_per_unit():
    c=Conversation();c.reply(1,'/price عندي ٣٠ طن حديد تسليح جديد في القاهرة')
    assert 'الإجمالي فقط' in c.reply(1,'40000 للطن')


def test_two_sessions_isolated():
    c=Conversation();c.reply(1,'/price عندي ٣٠ طن حديد تسليح جديد في القاهرة')
    assert 'حدّد نوع' in c.reply(2,'1200000')
    assert '1,200,000' in c.reply(1,'1200000')


def test_no_matched_demo_is_not_no_stock():
    c=Conversation();out=c.reply(1,'عايز ٥ متر مكعب خشب زان مستعمل في القاهرة')
    assert 'ده مش معناه' in out
    assert 'مثال ديمو #' not in out


def test_auth_private_and_duplicate(monkeypatch):
    monkeypatch.setattr(server,'SECRET','test-secret')
    monkeypatch.setattr(server,'OWNER','123')
    monkeypatch.setattr(server,'TOKEN','not-a-live-token')
    monkeypatch.setattr(server,'last_message',0)
    server.seen.clear()
    sent=[]
    class Response:
        status_code=200
        def json(self):return {'ok':True}
    class Client:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def post(self,url,**kwargs):sent.append(kwargs['json']);return Response()
    monkeypatch.setattr(server.httpx,'Client',Client)
    c=TestClient(server.app)
    msg={'update_id':777,'message':{'chat':{'id':123,'type':'private'},'from':{'id':123},'text':'/start'}}
    assert c.post('/telegram/webhook',json=msg).status_code==403
    headers={'x-telegram-bot-api-secret-token':'test-secret'}
    other={'update_id':778,'message':{'chat':{'id':124,'type':'private'},'from':{'id':124},'text':'/start'}}
    assert c.post('/telegram/webhook',json=other,headers=headers).json()=={'ok':True}
    assert not sent
    assert c.post('/telegram/webhook',json=msg,headers=headers).status_code==200
    assert len(sent)==1 and sent[0]['protect_content'] is True
    assert c.post('/telegram/webhook',json=msg,headers=headers).status_code==200
    assert len(sent)==1


def test_internal_check_protected():
    c=TestClient(server.app)
    assert c.post('/internal/check',json={'messages':['/start']}).status_code==403
    assert c.get('/health').json()['production_ready'] is False


def test_body_limit():
    assert TestClient(server.app).post('/telegram/webhook',content='x'*16001).status_code==413
