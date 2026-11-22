import os
os.environ['BARTER_NER_PATH']='ner/user_model'
os.environ['BARTER_EMBEDDING_BACKEND']='onnx'
from fastapi.testclient import TestClient
from telegram_demo import proposals,server
from integration.pipeline import analyze_ad,map_material
from pricing.predict import estimate_reference,grade_from_text

def fake_draft(original,facts):
    return dict(title=facts['material_raw'],description=original,evidence=[original],issues=[],consistency='consistent')

def test_user_model_separate_quantity_unit():
    e=analyze_ad('عندي ٣٠ طن حديد تسليح جديد في القاهرة')['entities']
    assert e['quantity_value']==30 and e['quantity_unit']=='طن'

def test_copper_scrap_not_iron():
    assert map_material('نحاس خردة')==('نحاس',False)
    p=estimate_reference('نحاس','هالك','المنصورة',50,quantity_unit='كيلو')
    assert p['grade_used']=='خردة' and 14000<p['fair_total_price_egp']<24000

def test_feature_price_no_ask(monkeypatch):
    monkeypatch.setattr(proposals,'draft_proposal',fake_draft)
    r=proposals.ProposalConversation().reply(1,'عندي ٣٠ طن حديد تسليح جديد في القاهرة')
    assert '1,158,733' in r and 'إجمالي السعر المطلوب' not in r
    assert 'مش سعر سوق حالي' in r and 'ما اتنشرتش' in r and 'افتراضية' in r

def test_missing_no_provider(monkeypatch):
    def forbidden(*args):raise AssertionError('provider must not run')
    monkeypatch.setattr(proposals,'draft_proposal',forbidden)
    r=proposals.ProposalConversation().reply(1,'عندي حديد في القاهرة')
    assert 'محتاج أوضّح' in r and 'مرجع الموديل' not in r

def test_bag_and_used_abstentions(monkeypatch):
    monkeypatch.setattr(proposals,'draft_proposal',fake_draft)
    c=proposals.ProposalConversation()
    assert 'quantity_unit_missing_or_unsupported' in c.reply(1,'عندي ٥٠ شيكارة اسمنت جديد في القاهرة')
    assert 'condition_unsupported' in c.reply(2,'عندي ٥ طن حديد تسليح مستعمل في القاهرة')

def test_multi_lot_stops_before_llm(monkeypatch):
    def forbidden(*args):raise AssertionError('provider must not run')
    monkeypatch.setattr(proposals,'draft_proposal',forbidden)
    assert 'أكتر من' in proposals.ProposalConversation().reply(1,'عندي ١٠ طن حديد تسليح جديد في القاهرة و٢٠ طن في الجيزة')

def test_voice_requires_confirmation(monkeypatch):
    called=[]
    def draft(*a):called.append(True);return fake_draft(*a)
    monkeypatch.setattr(proposals,'draft_proposal',draft)
    c=proposals.ProposalConversation()
    out=c.voice_preview(1,'عندي ٣٠ طن حديد تسليح جديد في القاهرة')
    assert not called and 'تأكيد' in out
    assert 'مرجع الموديل' in c.reply(1,'تأكيد') and len(called)==1

def test_different_material_rejected(monkeypatch):
    def bad(*a):return dict(title='نحاس',description='نحاس جديد في القاهرة',evidence=['القاهرة'],issues=[],consistency='consistent')
    monkeypatch.setattr(proposals,'draft_proposal',bad)
    assert 'ما عدّتش' in proposals.ProposalConversation().reply(1,'عندي ٣٠ طن حديد تسليح جديد في القاهرة')

def test_explicit_brand_only():
    assert grade_from_text('حديد تسليح','جديد','عندي ٣٠ طن حديد تسليح عز جديد في القاهرة')=='عز'
    assert grade_from_text('حديد تسليح','جديد','عندي ٣٠ طن حديد تسليح جديد في القاهرة') is None

def test_unauthorized_voice_never_downloads(monkeypatch):
    monkeypatch.setattr(server,'SECRET','test-secret');monkeypatch.setattr(server,'OWNER','123')
    def forbidden(*a):raise AssertionError('must reject before file download or provider')
    monkeypatch.setattr(server,'download_voice',forbidden);monkeypatch.setattr(server,'transcribe',forbidden)
    payload={'update_id':12345,'message':{'chat':{'id':999,'type':'private'},'from':{'id':999},'voice':{'file_id':'dummy','duration':1}}}
    r=TestClient(server.app).post('/telegram/webhook',json=payload,headers={'x-telegram-bot-api-secret-token':'test-secret'})
    assert r.status_code==200 and r.json()=={'ok':True}

def test_groups_and_spoofed_sender_never_download(monkeypatch):
    monkeypatch.setattr(server,'SECRET','test-secret');monkeypatch.setattr(server,'OWNER','123')
    def forbidden(*a):raise AssertionError('must reject')
    monkeypatch.setattr(server,'download_voice',forbidden)
    for ch,sender in [({'id':123,'type':'group'},123),({'id':123,'type':'private'},999)]:
        r=TestClient(server.app).post('/telegram/webhook',json={'update_id':456,'message':{'chat':ch,'from':{'id':sender},'voice':{'file_id':'dummy'}}},headers={'x-telegram-bot-api-secret-token':'test-secret'})
        assert r.json()=={'ok':True}

def test_owner_voice_retry_and_confirmation_stage(monkeypatch):
    monkeypatch.setattr(server,'SECRET','test-secret');monkeypatch.setattr(server,'OWNER','123')
    monkeypatch.setattr(server,'TOKEN','dummy');monkeypatch.setattr(server,'last_message',0)
    monkeypatch.setattr(server,'conversation',proposals.ProposalConversation());server.seen.clear()
    downloads=[];transcriptions=[];sends=[]
    def download(file_id):downloads.append(file_id);return b'test audio'
    def transcribe(audio):transcriptions.append(audio);return 'عندي ٣٠ طن حديد تسليح جديد في القاهرة'
    monkeypatch.setattr(server,'download_voice',download);monkeypatch.setattr(server,'transcribe',transcribe)
    class Response:
        status_code=200
        def json(self):return {'ok':True}
    class Client:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def post(self,url,**kwargs):sends.append(kwargs['json']);return Response()
    monkeypatch.setattr(server.httpx,'Client',Client)
    c=TestClient(server.app);headers={'x-telegram-bot-api-secret-token':'test-secret'}
    payload={'update_id':998877,'message':{'chat':{'id':123,'type':'private'},'from':{'id':123},'voice':{'file_id':'fixture','duration':4,'file_size':3451}}}
    assert c.post('/telegram/webhook',json=payload,headers=headers).status_code==200
    assert len(sends)==len(downloads)==len(transcriptions)==1
    assert 'تأكيد' in sends[0]['text'] and 'مرجع الموديل' not in sends[0]['text']
    assert c.post('/telegram/webhook',json=payload,headers=headers).status_code==200
    assert len(sends)==len(downloads)==len(transcriptions)==1

def test_too_long_voice_before_download(monkeypatch):
    monkeypatch.setattr(server,'SECRET','test-secret');monkeypatch.setattr(server,'OWNER','123');monkeypatch.setattr(server,'TOKEN','dummy');monkeypatch.setattr(server,'last_message',0);server.seen.clear()
    def forbidden(*a):raise AssertionError('must reject over limit before download')
    monkeypatch.setattr(server,'download_voice',forbidden)
    sent=[]
    class Response:
        status_code=200
        def json(self):return {'ok':True}
    class Client:
        def __init__(self,**kw):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def post(self,url,**kw):sent.append(kw['json']);return Response()
    monkeypatch.setattr(server.httpx,'Client',Client)
    p={'update_id':998878,'message':{'chat':{'id':123,'type':'private'},'from':{'id':123},'voice':{'file_id':'fixture','duration':91}}}
    assert TestClient(server.app).post('/telegram/webhook',json=p,headers={'x-telegram-bot-api-secret-token':'test-secret'}).status_code==200
    assert len(sent)==1 and '٩٠' in sent[0]['text']
