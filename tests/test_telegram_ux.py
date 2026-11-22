import os
os.environ['BARTER_NER_PATH']='ner/user_model'
from telegram_demo import proposals,server
from fastapi.testclient import TestClient
import pytest


def fake_draft(original,facts):
    return {'title':facts['material_raw']+' للبيع','description':f"متاح {facts['quantity_value']:g} {facts['quantity_unit']} {facts['material_raw']} {facts['condition_detected']} في {facts['location']}.",
            'evidence':[facts['material_raw']],'issues':[],'consistency':'consistent'}

@pytest.fixture
def c(monkeypatch):
    monkeypatch.setattr(proposals,'draft_proposal',fake_draft)
    return proposals.ProposalConversation()

def action(c,name):
    state=c.sessions[1]
    return c.callback(1,'ad:'+state.revision+':'+name)

def complete(c):
    assert 'رقم تواصل' in c.reply(1,'عندي ٣٠ طن حديد تسليح جديد في القاهرة')
    return c.reply(1,'بدون رقم')

def test_one_question_at_a_time_and_memory(c):
    assert c.reply(1,'عندي ٣٠ طن حديد تسليح')=='حالتها إيه؟'
    assert c.reply(1,'جديد')=='الخامة موجودة فين؟'
    assert 'رقم تواصل' in c.reply(1,'المنصورة')
    card=c.reply(1,'من غير رقم')
    assert 'المنصورة' in card and '30 طن' in card and 'جديد' in card and '📞' not in card
    assert c.sessions[1].fields['quantity_value']==30

def test_material_clarification_preserves_quantity_location(c):
    assert 'الخامة إيه' in c.reply(1,'عندي ٣٠ طن حديد جديد في القاهرة')
    assert 'رقم تواصل' in c.reply(1,'حديد تسليح')
    assert '1,158,733' in c.reply(1,'بدون رقم')

def test_contact_explicit_and_not_sent_to_llm(c,monkeypatch):
    calls=[]
    def draft(original,facts):
        calls.append((original,facts));return fake_draft(original,facts)
    monkeypatch.setattr(proposals,'draft_proposal',draft)
    c.reply(1,'عندي ٣٠ طن حديد تسليح جديد في القاهرة')
    card=c.reply(1,'01012345678')
    assert '01012345678' in card
    assert '01012345678' not in str(calls)

def test_initial_phone_kept_but_not_quantity(c):
    card=c.reply(1,'عندي ٣٠ طن حديد تسليح جديد في القاهرة للتواصل 01012345678')
    assert '01012345678' in card and c.sessions[1].fields['quantity_value']==30

def test_phone_never_defaults_to_owner(c):
    c.reply(1,'عندي ٣٠ طن حديد تسليح جديد في القاهرة')
    assert c.sessions[1].phone=='' and not c.sessions[1].contact_done
    assert 'صحيح' in c.reply(1,'تمام')

def test_condition_buttons_progress(c):
    c.reply(1,'عندي ٣٠ طن حديد تسليح')
    assert action(c,'set_used')=='الخامة موجودة فين؟'
    assert c.sessions[1].fields['condition_detected']=='مستعمل'

def test_edit_and_confirm_do_not_publish(c):
    complete(c)
    assert 'تعدّل' in action(c,'edit')
    assert 'المدينة' not in action(c,'edit_location')
    card=c.reply(1,'المنصورة')
    assert 'المنصورة' in card and 'القاهرة' not in card
    confirmed=action(c,'confirm')
    assert 'هنا فقط' in confirmed and 'نشر الإعلان' not in confirmed
    assert c.sessions[1].confirmed

def test_edit_quantity_reprices_and_keeps_contact(c):
    c.reply(1,'عندي ٣٠ طن حديد تسليح جديد في القاهرة');c.reply(1,'01012345678')
    action(c,'edit_quantity')
    card=c.reply(1,'١٠ طن')
    assert '10 طن' in card and '01012345678' in card and '386,244' in card

def test_stale_callback_cannot_mutate(c):
    complete(c);old=c.sessions[1].revision
    action(c,'confirm')
    before=c.sessions[1].fields.copy()
    assert 'آخر رسالة' in c.callback(1,'ad:'+old+':edit_location')
    assert c.sessions[1].fields==before

def test_new_ad_no_stale_previous_proposal(c):
    complete(c)
    c.reply(1,'عندي ٥٠ كيلو نحاس خردة في المنصورة')
    card=c.reply(1,'بدون رقم')
    assert 'نحاس' in card and 'حديد تسليح' not in card and '50 كيلو' in card

def test_manual_price_is_labeled_user_choice(c):
    complete(c);action(c,'edit_asking')
    assert 'الإجمالي' in c.reply(1,'40000 للطن')
    card=c.reply(1,'١٢٠٠٠٠٠')
    assert 'السعر المحدد منك' in card and 'تقدير النموذج' in card

def test_html_is_escaped_for_manual_title(c):
    complete(c);action(c,'edit_title')
    out=c.reply(1,'حديد تسليح <script>')
    assert '&lt;script&gt;' in out and '<script>' not in out

def test_conflicting_manual_material_not_accepted(c):
    complete(c);action(c,'edit_title')
    assert 'بيغيّر الخامة' in c.reply(1,'نحاس جديد للبيع')

def test_no_llm_until_voice_and_fields_confirmed(c):
    c.voice_preview(1,'عندي ٣٠ طن حديد تسليح جديد')
    assert action(c,'voice_yes')=='الخامة موجودة فين؟'
    assert 'رقم تواصل' in c.reply(1,'القاهرة')
    assert 'السعر المقترح' in action(c,'skip_phone')

def test_callbacks_owner_only_before_ack_or_model(monkeypatch):
    monkeypatch.setattr(server,'SECRET','test-secret');monkeypatch.setattr(server,'OWNER','123')
    class Forbidden:
        def __init__(self,*a,**k):raise AssertionError('No outbound calls for outsiders')
    monkeypatch.setattr(server.httpx,'Client',Forbidden)
    payload={'update_id':98701,'callback_query':{'id':'outside','from':{'id':999},'data':'ad:x:confirm',
             'message':{'message_id':99,'chat':{'id':123,'type':'private'}}}}
    assert TestClient(server.app).post('/telegram/webhook',json=payload,headers={'x-telegram-bot-api-secret-token':'test-secret'}).json()=={'ok':True}

def test_owner_callback_edits_with_native_buttons_and_dedupes(c,monkeypatch):
    complete(c)
    monkeypatch.setattr(server,'conversation',c);monkeypatch.setattr(server,'SECRET','test-secret')
    monkeypatch.setattr(server,'OWNER','1');monkeypatch.setattr(server,'TOKEN','dummy');monkeypatch.setattr(server,'last_message',0)
    server.seen.clear();sent=[]
    class Response:
        status_code=200
        def json(self):return {'ok':True,'result':{'message_id':88}}
    class Client:
        def __init__(self,**kw):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def post(self,url,**kw):sent.append((url,kw['json']));return Response()
    monkeypatch.setattr(server.httpx,'Client',Client)
    data='ad:'+c.sessions[1].revision+':confirm'
    p={'update_id':98702,'callback_query':{'id':'owner-callback','from':{'id':1},'data':data,'message':{'message_id':88,'chat':{'id':1,'type':'private'}}}}
    client=TestClient(server.app);h={'x-telegram-bot-api-secret-token':'test-secret'}
    assert client.post('/telegram/webhook',json=p,headers=h).status_code==200
    assert len(sent)==2 and sent[0][0].endswith('/answerCallbackQuery') and sent[1][0].endswith('/editMessageText')
    assert sent[1][1]['parse_mode']=='HTML' and sent[1][1]['reply_markup']['inline_keyboard']
    assert client.post('/telegram/webhook',json=p,headers=h).status_code==200 and len(sent)==2
