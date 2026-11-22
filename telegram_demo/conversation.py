"""Private Telegram test conversation. No generative model, no live inventory."""
import re
import time
from dataclasses import dataclass
from integration.pipeline import analyze_ad, AR_DIGITS
from chatbot.chatbot import search, answer_with_template

NOTICE='تجربة محاكاة فقط، مش منصة بيع فعلية ولا جاهزية إنتاجية.'
HELP=(NOTICE+'\nأنا بحث دلالي MiniLM + FAISS وردود بقوالب، مش موديل محادثة متدرّب ولا LLM.\n'
      'للبحث: عايز ٥ طن حديد تسليح جديد في القاهرة\n'
      'للسعر: /price عندي ٣٠ طن حديد تسليح جديد في القاهرة\n'
      'هسألك عن الإجمالي المطلوب بالجنيه. تقدير السعر تطويري، مش سعر سوق مباشر أو عرض بيع.\n'
      '/reset لبدء طلب جديد. الصور والتحقق منها مش متاحين. مفيش شراء أو تسجيل طلبات أو تنبيهات.')

@dataclass
class Session:
    text: str=''
    mode: str='search'
    pending: str=''
    updated: float=0

class Conversation:
    def __init__(self): self.sessions={}

    def reply(self, chat_id, text):
        if not isinstance(text,str) or not text.strip():
            return 'ابعت وصف الخامة في رسالة نصية. الصور والصوت مش مدعومين في التجربة.'
        if len(text)>1500: return 'الرسالة طويلة للتجربة. اختصرها لأقل من ١٥٠٠ حرف.'
        text=text.strip()
        if text.startswith('/start') or text in ('/help','مساعدة'):
            self.sessions.pop(chat_id,None)
            return HELP
        if text in ('/reset','ابدأ من جديد','ابدا من جديد'):
            self.sessions.pop(chat_id,None)
            return 'بدأنا طلب جديد. ابعت الخامة والكمية والوحدة والحالة والمكان.'
        if text in ('/about','استخدمت ايه','استخدمت إيه'):
            return HELP
        now=time.monotonic()
        state=self.sessions.get(chat_id)
        if state is None or now-state.updated>1800: state=Session()
        if text.startswith('/price'):
            state=Session(mode='price');text=text[len('/price'):].strip()
        elif text.startswith('/search'):
            state=Session();text=text[len('/search'):].strip()
        elif not state.pending and any(w in text for w in ('تسعير','بكام','حكم السعر','قيّم السعر','قيم السعر')):
            state=Session(mode='price')
        elif not state.pending:
            state=Session()
        state.updated=now
        self.sessions[chat_id]=state
        normalized=text.translate(AR_DIGITS)
        asking=None
        if state.pending=='asking':
            if re.fullmatch(r'\d+(?:\.\d+)?\s*(?:جنيه|ج\.م)?',normalized):
                asking=float(re.match(r'\d+(?:\.\d+)?',normalized).group())
            else:
                return 'اكتب الإجمالي فقط بالجنيه، زي 1200000. مش سعر الطن أو الكيلو. لو عايز تغيّر الوصف ابدأ /reset.'
        else:
            if text: state.text=(state.text+' '+text).strip()
        if not state.text:
            state.pending='description'
            return 'ابعت وصف الخامة والكمية والوحدة والحالة والمكان، مثال: عندي ٣٠ طن حديد تسليح جديد في القاهرة.'
        result=analyze_ad(state.text,asking_total_price=asking)
        e=result['entities']
        if not e['material_canonical'] or e['material_assumed_generic']:
            state.pending='material'
            # Remove an ambiguous prior description: retaining its first entity would prevent correction.
            state.text=''
            return 'حدّد نوع الخامة بوضوح وابعت الوصف كامل: حديد تسليح ولا حديد خردة؟ خشب زان ولا سويد؟ ما ينفعش أفترض النوع للتسعير.'
        for field,key,prompt in [
            ('quantity','quantity_value','الكمية كام وبأي وحدة؟ مثال: ٣٠ طن، أو ٥٠ كيلو، أو ١٠ ألواح.'),
            ('unit','quantity_unit','وحدة الكمية إيه؟ ابعت الكمية والوحدة مع بعض.'),
            ('condition','condition_detected','حالة الخامة إيه؟ جديد، مستعمل، ولا خردة؟ دي هتفضل حالة مذكورة منك، مش متحقّق منها بصورة.'),
            ('location','location','الخامة فين؟ اكتب المدينة أو المنطقة.')]:
            if not e[key]:
                state.pending=field
                return prompt
        if state.mode=='price':
            if asking is None:
                state.pending='asking'
                return ('فهمت: '+str(e['quantity_value'])+' '+str(e['quantity_unit'])+' '+e['material_canonical']+
                        '، الحالة '+e['condition_detected']+'، في '+e['location']+'.\nإجمالي السعر المطلوب كام بالجنيه؟ اكتب الإجمالي فقط، مش سعر الوحدة.')
            state.pending=''
            p=result['pricing']
            if not p or not p.get('supported'):
                return (NOTICE+'\nمش هطلع حكم سعر للتركيبة أو الوحدة دي. السبب: '+str((p or {}).get('reason','missing_fields'))+
                        '\nمش بنفترض وزن الشيكارة ولا بنحوّل الحجم لوزن. ابدأ /price بوصف جديد لو عايز تغيّره.')
            return (NOTICE+'\nتقدير موديل تطويري من أسعار مصرية منشورة محفوظة، مش سعر سوق مباشر.\n'
                    f"الخامة: {e['material_canonical']}، الحالة المذكورة: {e['condition_detected']}\n"
                    f"الكمية: {e['quantity_value']:g} {e['quantity_unit']}\n"
                    f"مرجع الموديل للوحدة: {p['fair_unit_price_egp']:,.2f} جنيه/{p['price_unit']}\n"
                    f"إجمالي مرجع الموديل: {p['fair_total_price_egp']:,.2f} جنيه\n"
                    f"الإجمالي اللي دخلته: {p['asking_total_price_egp']:,.2f} جنيه\n"
                    f"المقارنة داخل التجربة: {p['verdict']} بالنسبة لمرجع الموديل فقط، مش إثبات عدالة السعر.\n"
                    'الحالة والمكان مش متحققين ميدانيًا. دقة معاملات حقيقية مش مثبتة. /reset لطلب جديد.')
        state.pending=''
        candidates=search(state.text,k=20)
        matches=[m for m in candidates if m.get('material')==e['material_canonical'] and m.get('condition')==e['condition_detected'] and m.get('location')==e['location']][:2]
        if not matches:
            return (NOTICE+'\nمفيش مثال مولّد مطابق للخامة والحالة والمكان دول في عينة الديمو. ده مش معناه إن الخامة مش موجودة في السوق.\n'
                    'مفيش مخزون تجار متوصل ولا طلب اتسجل. /reset لطلب جديد أو /price لاختبار السعر.')
        response=answer_with_template(state.text,matches)
        return NOTICE+'\n'+response+'\nالأمثلة ممكن تختلف عن الكمية المطلوبة. لو عايز تختبر السعر ابدأ /price مع الوصف.'
