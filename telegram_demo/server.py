"""Single-tester webhook server. Never import vision or expose model/data files."""
import hashlib
import hmac
import json
import os
import threading
import time
from collections import OrderedDict
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx
os.environ.setdefault('BARTER_NER_PATH',str(__import__('pathlib').Path(__file__).resolve().parent.parent/'ner'/'user_model'))
from telegram_demo.proposals import ProposalConversation as Conversation
from telegram_demo.groq_provider import transcribe, ProviderUnavailable

app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
conversation=Conversation()
lock=threading.Lock()
seen=OrderedDict()
last_message=0.0
TOKEN=os.getenv('TELEGRAM_BOT_TOKEN','')
SECRET=os.getenv('TELEGRAM_WEBHOOK_SECRET','') or (hashlib.sha256(('barter-webhook-v1:'+TOKEN).encode()).hexdigest() if TOKEN else '')
OWNER=os.getenv('TELEGRAM_OWNER_ID','')

@app.get('/')
@app.get('/health')
def health():
    return {'status':'test_simulation','production_ready':False,'vision_enabled':False,
            'private_tester_only':True,'configured':bool(TOKEN and SECRET and OWNER and os.getenv('GROQ_API_KEY')),
            'chatbot':'user_spacy_NER_Groq_draft_pricing_reference','generative_llm':bool(os.getenv('GROQ_API_KEY')),
            'voice_enabled':bool(os.getenv('GROQ_API_KEY')),'price_is_live_market':False}

@app.middleware('http')
async def body_limit(request,call_next):
    if request.method=='POST':
        size=request.headers.get('content-length')
        if size and (not size.isdigit() or int(size)>16000):
            return JSONResponse({'error':'body_too_large'},status_code=413)
        body=await request.body()
        if len(body)>16000:return JSONResponse({'error':'body_too_large'},status_code=413)
    return await call_next(request)

def authorized(request):
    supplied=request.headers.get('x-telegram-bot-api-secret-token','')
    return bool(SECRET and hmac.compare_digest(supplied,SECRET))

@app.post('/internal/check')
def internal_check(payload:dict,request:Request):
    if not authorized(request):return JSONResponse({'error':'forbidden'},status_code=403)
    # Stateless integration check, no Telegram send and no user conversation state.
    test=Conversation()
    replies=[]
    messages=payload.get('messages',[])
    if not isinstance(messages,list) or len(messages)>8:return JSONResponse({'error':'invalid_test'},status_code=400)
    with lock:
        if payload.get('voice_base64'):
            import base64
            audio=base64.b64decode(payload['voice_base64'],validate=True)
            if len(audio)>9000:return JSONResponse({'error':'test_audio_too_large'},status_code=400)
            replies.append(test.voice_preview('internal-test',transcribe(audio)))
        for text in messages:
            replies.append(test.reply('internal-test',text))
    return {'simulation':True,'sent_to_telegram':False,'replies':replies,
            'peak_rss_mb':round(__import__('resource').getrusage(__import__('resource').RUSAGE_SELF).ru_maxrss/1024,1)}

@app.post('/telegram/webhook')
def webhook(payload:dict,request:Request):
    global last_message
    if not authorized(request):return JSONResponse({'error':'forbidden'},status_code=403)
    msg=payload.get('message') or {}
    chat=msg.get('chat') or {}
    sender=msg.get('from') or {}
    if not OWNER or chat.get('type')!='private' or str(chat.get('id'))!=OWNER or str(sender.get('id'))!=OWNER:
        return {'ok':True}
    update_id=payload.get('update_id')
    if not isinstance(update_id,int):return {'ok':True}
    with lock:
        if update_id in seen:return {'ok':True}
        if not TOKEN:return JSONResponse({'error':'not_configured'},status_code=503)
        if time.monotonic()-last_message<0.7:
            return JSONResponse({'error':'retry_later'},status_code=429)
        state_key=int(OWNER)
        # Keep conversation transition atomic with delivery as far as a single process permits.
        import copy
        old=copy.deepcopy(conversation.sessions.get(state_key))
        try:
            voice=msg.get('voice')
            if voice:
                duration=voice.get('duration',999)
                size=voice.get('file_size',0)
                if not isinstance(duration,(float,int)) or duration>90 or size>5_000_000:
                    response='الفويس طويل للتجربة. ابعت لحد ٩٠ ثانية وحجم أقل من ٥ ميجا.'
                else:
                    audio=download_voice(voice.get('file_id',''))
                    response=conversation.voice_preview(state_key,transcribe(audio))
            else:
                response=conversation.reply(state_key,msg.get('text'))
        except ProviderUnavailable:
            response='خدمة الفويس أو الصياغة المجانية مش متاحة دلوقتي أو وصلت الحد. ابعت نص أو جرّب لاحقًا. ما اتنفذش نشر.'
        except (ValueError,OverflowError):
            response='القيمة مش مناسبة للتجربة. ابدأ /reset واكتب كمية وسعر بأرقام موجبة معقولة.'
        except Exception:
            response='في مشكلة داخلية مؤقتة في التجربة. ما اتسجلش طلب وما اتنفذش شراء. جرّب /reset.'
        try:
            with httpx.Client(timeout=15) as client:
                result=client.post('https://api.telegram.org/bot'+TOKEN+'/sendMessage',json={
                    'chat_id':int(OWNER),'text':response[:4000],
                    'link_preview_options':{'is_disabled':True},
                    'protect_content':True,
                })
            success=result.status_code==200 and result.json().get('ok') is True
        except Exception:
            success=False
        if not success:
            if old is None:conversation.sessions.pop(state_key,None)
            else:conversation.sessions[state_key]=old
            return JSONResponse({'error':'delivery_pending'},status_code=503)
        seen[update_id]=True
        while len(seen)>512:seen.popitem(last=False)
        last_message=time.monotonic()
    return {'ok':True}


def download_voice(file_id):
    """Read a bounded Telegram-owned audio object. Never log token URLs."""
    import re
    if not isinstance(file_id,str) or not file_id or len(file_id)>512:raise ValueError('bad_voice')
    try:
        with httpx.Client(timeout=20) as client:
            r=client.get('https://api.telegram.org/bot'+TOKEN+'/getFile',params={'file_id':file_id})
            if r.status_code!=200:raise ProviderUnavailable('telegram_audio_unavailable')
            info=r.json().get('result',{})
            path=info.get('file_path','')
            if not re.fullmatch(r'[A-Za-z0-9_./-]+',path) or '..' in path or info.get('file_size',0)>5_000_000:
                raise ValueError('bad_voice_file')
            data=bytearray()
            with client.stream('GET','https://api.telegram.org/file/bot'+TOKEN+'/'+path) as stream:
                if stream.status_code!=200:raise ProviderUnavailable('telegram_audio_unavailable')
                for chunk in stream.iter_bytes():
                    data.extend(chunk)
                    if len(data)>5_000_000:raise ValueError('voice_too_large')
            return bytes(data)
    except httpx.HTTPError:
        raise ProviderUnavailable('telegram_audio_unavailable') from None
