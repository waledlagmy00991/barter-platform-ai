"""Concise, stateful private ad review. Never publishes or supplies seller contacts."""
import html
import re
import time
import uuid
from dataclasses import dataclass, field
from integration.pipeline import analyze_ad, AR_DIGITS, parse_quantity, map_material, detect_condition
from pricing.predict import estimate_reference, grade_from_text
from telegram_demo.groq_provider import draft_proposal, ProviderUnavailable

WELCOME=('أهلاً 👋 ابعت الخامة اللي عندك كتابة أو فويس، وأنا أظبط لك الإعلان.\n\n'
         'دي تجربة خاصة للمراجعة، بدون نشر. السعر تقديري مش تسعير سوق مباشر. '
         'النص والفويس بيتعالجوا عبر Groq بدون حفظ محتوى الاستدلال. /about للتفاصيل.')
ABOUT=('بنجمع تفاصيل عرض واحد، وبعدها نقترح عنوان ووصف وسعر تقديري لو البيانات تدعمه. '
       'السعر من نموذج تطويري على أسعار مصرية منشورة، مش معاملات بيع مؤكدة أو سوق مباشر. '
       'الدرجة الافتراضية بتظهر مع السعر. المكان والمقاسات مش عوامل في نموذج السعر. '
       'الفويس لحد ٩٠ ثانية، وبتأكد نصه الأول. مفيش فحص صور أو نشر أو بيع. '
       'المحادثة مؤقتة وبتتمسح عند إعادة تشغيل الخدمة. /reset لإعلان جديد.')
PHONE=re.compile(r'(?<!\d)(?:\+?20[\s-]?)?0?1[0125](?:[\s-]?\d){8}(?!\d)')
SKIP={'بدون رقم','من غير رقم','بلاش رقم','تخطي','تخطى','مش عايز رقم','لا','skip'}
CONFIRM={'تأكيد','تاكيد','صح','نعم','تمام','موافق'}
SLOT_LABELS={'material':'الخامة','quantity':'الكمية','condition':'الحالة','location':'المكان','phone':'التواصل',
             'title':'العنوان','description':'الوصف','asking':'السعر'}

def escape(value):return html.escape(str(value),quote=False)

def phone_from(text):
    found=PHONE.findall(text.translate(AR_DIGITS))
    return re.sub(r'[\s-]','',found[0]) if len(found)==1 else None

class Reply(str):
    def __new__(cls,text,buttons=None):
        obj=str.__new__(cls,text);obj.buttons=buttons or [];obj.parse_mode='HTML';return obj
    def telegram(self):
        out={'text':str(self),'parse_mode':'HTML'}
        if self.buttons:out['reply_markup']={'inline_keyboard':self.buttons}
        return out

@dataclass
class State:
    text:str=''
    fields:dict=field(default_factory=dict)
    raw:dict=field(default_factory=dict)
    pending:str=''
    voice:str=''
    updated:float=0
    phone:str=''
    contact_done:bool=False
    proposal:dict=field(default_factory=dict)
    price:dict=field(default_factory=dict)
    grade:str=None
    asking:float=None
    confirmed:bool=False
    revision:str=field(default_factory=lambda:uuid.uuid4().hex[:8])

class ProposalConversation:
    def __init__(self):self.sessions={};self.search=None
    def _buttons(self,state,rows):
        return [[{'text':label,'callback_data':'ad:'+state.revision+':'+action} for label,action in row] for row in rows]
    def _reply(self,state,text,rows=()):return Reply(text,self._buttons(state,rows))
    def voice_preview(self,chat_id,transcript):
        old=self.sessions.get(chat_id)
        state=old if old and time.monotonic()-old.updated<1800 else State()
        state.voice=transcript;state.updated=time.monotonic();self.sessions[chat_id]=state
        return self._reply(state,'🎙 '+escape(transcript)+'\n\nسمعته صح؟',[[('أيوه، كمّل','voice_yes'),('هكتب التصحيح','voice_edit')]])
    def _ask(self,state,slot):
        state.pending=slot
        text={'material':'الخامة إيه بالتحديد؟ زي حديد تسليح أو نحاس خردة.',
              'quantity':'الكمية قد إيه وبأي وحدة؟',
              'condition':'حالتها إيه؟',
              'location':'الخامة موجودة فين؟',
              'phone':'تحب تحط رقم تواصل في الإعلان؟ ابعته أو اختار من غير رقم.',
              'title':'اكتب العنوان اللي تفضله.',
              'description':'اكتب الوصف الجديد.',
              'asking':'اكتب السعر الإجمالي بالجنيه اللي تحب تعرضه، أو اختار اقتراح النموذج.'}[slot]
        rows=[]
        if slot=='condition':rows=[[('جديد','set_new'),('مستعمل','set_used'),('خردة','set_scrap')]]
        if slot=='phone':rows=[[('من غير رقم','skip_phone')]]
        if slot=='asking':rows=[[('اقتراح النموذج','suggested_price')]]
        return self._reply(state,text,rows)
    def _next(self,state):
        e=state.fields
        if not e.get('material_canonical') or e.get('material_assumed_generic'):return self._ask(state,'material')
        if not e.get('quantity_value') or not e.get('quantity_unit'):return self._ask(state,'quantity')
        if not e.get('condition_detected'):return self._ask(state,'condition')
        if not e.get('location'):return self._ask(state,'location')
        if not state.contact_done:return self._ask(state,'phone')
        state.pending=''
        return self._generate(state)
    def _compose_source(self,state):
        e=state.fields
        pieces=[str(e.get('quantity_raw') or e.get('quantity_value') or ''),str(e.get('quantity_unit') or ''),
                str(e.get('material_raw') or ''),str(e.get('condition_detected') or ''),str(e.get('location') or '')]
        if state.grade:pieces.append(state.grade)
        # Keep declared non-contact attributes when changing a core field.
        for key,values in state.raw.items():
            if key not in {'MATERIAL','QUANTITY','UNIT','LOCATION','CONDITION','PHONE','PHONE_NUMBER','PRICE','CURRENCY'}:
                pieces.extend(values)
        return ' '.join(x for x in pieces if x)
    def _begin(self,state,text):
        state.proposal={};state.price={};state.asking=None;state.confirmed=False
        contact=phone_from(text)
        # Contact never goes to the language provider or quantity extractor.
        source=PHONE.sub('',text.translate(AR_DIGITS))
        if contact:source=re.sub(r'(?:للتواصل|للاتصال|واتساب|تليفون|هاتف|رقم\s*(?:التواصل|الموبايل|الهاتف|التليفون)?)\s*[:：]?\s*$','',source).strip()
        result=analyze_ad(source);e=result['entities'];raw=result['raw_entities']
        numeric_lots=re.findall(r'(?:\d+(?:\.\d+)?|خمسين|عشرين|تلاتين|ثلاثين)\s*(?:طن|كيلو|كجم|لوح|شيكارة|متر)',source)
        if len(set(raw.get('MATERIAL',[])))>1 or len(raw.get('QUANTITY',[]))>1 or len(set(raw.get('LOCATION',[])))>1 or len(numeric_lots)>1:
            state.pending='restart'
            return self._reply(state,'خلّينا في عرض واحد. ابعت خامة واحدة بكمية ومكان واحد.')
        state.text=source;state.fields=e.copy();state.raw=raw
        state.phone=contact or '';state.contact_done=bool(contact)
        state.grade=grade_from_text(e.get('material_canonical'),e.get('condition_detected'),source) if e.get('material_canonical') else None
        match=re.search(r'(?:بإجمالي|باجمالي|إجمالي|اجمالي|الإجمالي|الاجمالي)\s*(?:السعر\s*)?[:：]?\s*(\d{1,12}(?:\.\d{1,2})?)\s*(?:جنيه|ج\.م)(?!\w)',source)
        if match and float(match.group(1))>0:state.asking=float(match.group(1))
        return self._next(state)
    def _apply(self,state,slot,text):
        e=state.fields
        if slot=='phone':
            if text in SKIP:state.phone='';state.contact_done=True
            else:
                phone=phone_from(text)
                if not phone:return self._reply(state,'ابعت رقم موبايل مصري صحيح، أو اختار من غير رقم.',[[('من غير رقم','skip_phone')]])
                state.phone=phone;state.contact_done=True
            state.confirmed=False
            if state.proposal:return self._card(state)
            return self._next(state)
        if slot in ('title','description'):
            if not 1<=len(text)<= (100 if slot=='title' else 700):return self._reply(state,'اختصره شوية واكتب النص تاني.')
            if not state.proposal:return self._next(state)
            material,_=map_material(text);condition=detect_condition(text)
            revised=analyze_ad(text)['entities']
            conflicts=(revised.get('location') and revised['location']!=e['location']) or (revised.get('quantity_value') and (revised['quantity_value']!=e['quantity_value'] or revised.get('quantity_unit')!=e['quantity_unit']))
            if conflicts:return self._reply(state,'التعديل بيغيّر المكان أو الكمية. عدّل التفاصيل الأول عشان السعر يفضل مناسب.',[[('تعديل التفاصيل','edit')]])
            if (material and material!=e['material_canonical']) or (condition and condition!=e['condition_detected']):
                return self._reply(state,'التعديل بيغيّر الخامة أو الحالة. عدّل التفاصيل الأول عشان السعر يفضل مناسب.',[[('تعديل التفاصيل','edit')]])
            # A manual edit is displayed as the user's edit, never passed off as a model claim.
            state.proposal[slot]=text;state.confirmed=False
            return self._card(state)
        if slot=='asking':
            value=text.translate(AR_DIGITS).replace(',','').replace('٬','')
            match=re.fullmatch(r'\s*(\d{1,12}(?:\.\d{1,2})?)\s*(?:جنيه|ج\.م)?\s*',value)
            if not match or float(match.group(1))<=0:return self._reply(state,'اكتب الإجمالي بالجنيه كرقم موجب، من غير سعر للطن أو الكيلو.')
            state.asking=float(match.group(1));state.confirmed=False
            return self._card(state)
        if slot=='condition':
            value=detect_condition(text)
            if not value:return self._reply(state,'اختار حالة واحدة واضحة.',[[('جديد','set_new'),('مستعمل','set_used'),('خردة','set_scrap')]])
            e['condition_detected']=value
            if e.get('material_canonical')=='حديد تسليح' and value=='هالك' and e.get('material_assumed_generic'):
                e.update(material_canonical='حديد خردة',material_raw='حديد خردة',material_assumed_generic=False)
        elif slot=='location':
            value=text.strip()
            value=re.sub(r'^(?:المكان|موجودة?|الخامة|في|فى)\s*[:：]?\s*','',value).strip()
            if value in {'تمام','ماشي','نعم','لا','اه','أه','اوكي','شكرا','شكرًا'} or not re.fullmatch(r'[ء-يA-Za-z][ء-يA-Za-z0-9٠-٩\s،,.\-/]{1,90}',value) or any(x in value for x in ('مش عارف','معرفش','أي مكان','اي مكان','فين','كام','ازاي','؟')):
                return self._reply(state,'اكتب المدينة أو المنطقة اللي الخامة موجودة فيها.')
            e['location']=value
        elif slot=='quantity':
            q,u=parse_quantity(text)
            if q and not u and e.get('quantity_unit'):u=e['quantity_unit']
            if u and not q and e.get('quantity_value'):q=e['quantity_value']
            if not q or not u:return self._reply(state,'اكتب الكمية والوحدة مع بعض، زي ٣٠ طن أو ٥٠ كيلو.')
            e.update(quantity_raw=f'{q:g}',quantity_value=q,quantity_unit=u)
        elif slot=='material':
            result=analyze_ad(text);incoming=result['entities']
            material,assumed=map_material(text)
            if not material or assumed:return self._reply(state,'حدّد نوع الخامة أكتر، زي خشب زان أو حديد تسليح.')
            e.update(material_canonical=material,material_raw=incoming.get('material_raw') or text,material_assumed_generic=False)
            # If the clarifying answer supplies another missing field, keep it too.
            for key in ('quantity_raw','quantity_value','quantity_unit','condition_detected','location'):
                if incoming.get(key) is not None and not e.get(key):e[key]=incoming[key]
            state.grade=grade_from_text(material,e.get('condition_detected'),text)
        if e.get('material_canonical') and not e.get('material_assumed_generic'):e['material_raw']=e['material_canonical']
        state.text=self._compose_source(state);state.proposal={};state.price={};state.confirmed=False
        return self._next(state)
    def _generate(self,state):
        e=state.fields
        facts={k:e.get(k) for k in ('material_canonical','material_raw','quantity_raw','quantity_value','quantity_unit','condition_detected','location')}
        facts['price_mentions']=[];facts['currency_mentions']=[]
        try:proposal=draft_proposal(state.text,facts)
        except ProviderUnavailable:
            state.pending='retry'
            return self._reply(state,'خدمة الصياغة مش متاحة دلوقتي. تفاصيلك لسه موجودة، جرّب تاني بعد شوية.',[[('حاول تاني','retry')]])
        generated=proposal['title']+' '+proposal['description']
        generated_material,_=map_material(generated);generated_condition=detect_condition(generated)
        if generated_material!=e['material_canonical'] or (generated_condition and generated_condition!=e['condition_detected']) or e['location'] not in generated:
            state.pending='retry'
            return self._reply(state,'الصياغة محتاجة مراجعة عشان تفضل مطابقة لتفاصيلك.',[[('أعد الصياغة','retry'),('عدّل التفاصيل','edit')]])
        if proposal['consistency']=='conflict':
            state.pending='restart'
            return self._reply(state,'في تفاصيل متعارضة في العرض. ابعت وصف واحد بعد تصحيحها.')
        state.proposal=proposal
        state.price=estimate_reference(e['material_canonical'],e['condition_detected'],e['location'],e['quantity_value'],
                                      quantity_unit=e['quantity_unit'],grade=state.grade,material_confirmed=not e['material_assumed_generic'])
        state.pending=''
        return self._card(state)
    def _card(self,state):
        state.pending='';state.revision=uuid.uuid4().hex[:8]
        e=state.fields;p=state.price;proposal=state.proposal
        condition={'هالك':'خردة'}.get(e['condition_detected'],e['condition_detected'])
        out='📦 <b>'+escape(proposal['title'])+'</b>\n\n'+escape(proposal['description'])
        out+='\n\n📍 '+escape(e['location'])+'  ·  '+escape(f"{e['quantity_value']:g} {e['quantity_unit']}")+'  ·  '+escape(condition)
        if state.phone:out+='\n📞 <code>'+escape(state.phone)+'</code>'
        if state.asking is not None:
            amount=f'{state.asking:,.2f}'.rstrip('0').rstrip('.')
            out+='\n\n💰 <b>السعر المحدد منك: '+amount+' جنيه إجمالي</b>'
        if p.get('supported'):
            unit=p['price_unit'];unit_label={'طن':'للطن','كيلو':'للكيلو','متر مكعب':'للمتر المكعب','ألف':'لكل ألف'}.get(unit,'لكل '+unit)
            if state.asking is None:out+=f"\n\n💰 <b>السعر المقترح تقديريًا: {p['fair_total_price_egp']:,.0f} جنيه إجمالي</b>"
            else:out+=f"\nتقدير النموذج: {p['fair_total_price_egp']:,.0f} جنيه إجمالي"
            out+=f"\n{p['fair_unit_price_egp']:,.0f} جنيه {escape(unit_label)}"
            note='مرجع أسعار منشورة، مش سوق مباشر'
            if p.get('grade_is_default'):note+=' · درجة افتراضية: '+str(p['grade_used'])
            elif p.get('grade_used'):note+=' · '+str(p['grade_used'])
            out+='\n<i>'+escape(note)+'</i>'
        else:
            reason=str(p.get('reason',''))
            note='محتاج بيانات أنسب عشان أقترح سعر موثوق.'
            if 'quantity_unit' in reason:note='مفيش تقدير للوحدة دي، ومش هفترض وزنها.'
            elif 'condition' in reason:note='مفيش بيانات كفاية للحالة دي.'
            elif 'range' in reason:note='التقدير خارج نطاق الأسعار المرصودة، فمش هعرضه.'
            out+='\n\n💰 <b>السعر المقترح: غير متاح</b>\n'+note
        if state.confirmed:out+='\n\n✓ <b>تم اعتماد النسخة هنا فقط.</b>'
        rows=[[('✏️ تعديل','edit'),('✓ اعتماد النسخة','confirm')],[('＋ إعلان جديد','new')]]
        return self._reply(state,out,rows)
    def callback(self,chat_id,data):
        state=self.sessions.get(chat_id)
        if not state or time.monotonic()-state.updated>1800:
            return Reply('الجلسة خلصت. ابعت وصف الخامة نبدأ من جديد.')
        parts=data.split(':',2) if isinstance(data,str) else []
        if len(parts)!=3 or parts[0]!='ad' or parts[1]!=state.revision:
            return Reply('استخدم الأزرار في آخر رسالة.')
        action=parts[2];state.updated=time.monotonic()
        if action=='new':
            self.sessions[chat_id]=State(updated=time.monotonic())
            return Reply('ابعت وصف الخامة الجديدة.')
        if action=='voice_edit':state.voice='';return Reply('اكتب التصحيح، وأنا أكمّل من التفاصيل اللي عندي.')
        if action=='voice_yes':
            if not state.voice:return Reply('الفويس اتراجع بالفعل. كمّل من آخر رسالة.')
            text=state.voice;state.voice=''
            if state.pending in ('material','quantity','condition','location','phone','title','description','asking'):return self._apply(state,state.pending,text)
            return self._begin(state,text)
        if action=='skip_phone' and state.pending=='phone':return self._apply(state,'phone','بدون رقم')
        if action in ('set_new','set_used','set_scrap') and state.pending=='condition':
            return self._apply(state,'condition',{'set_new':'جديد','set_used':'مستعمل','set_scrap':'خردة'}[action])
        if action=='retry' and state.pending=='retry':return self._next(state)
        if action=='confirm' and state.proposal:
            state.confirmed=True;return self._card(state)
        if action=='edit':
            rows=[[(label,'edit_'+slot) for slot,label in [('material','الخامة'),('quantity','الكمية'),('condition','الحالة')]],
                  [(label,'edit_'+slot) for slot,label in [('location','المكان'),('phone','التواصل'),('asking','السعر')]],
                  [('العنوان','edit_title'),('الوصف','edit_description')]]
            return self._reply(state,'تحب تعدّل إيه؟',rows)
        if action.startswith('edit_') and action[5:] in SLOT_LABELS:return self._ask(state,action[5:])
        if action=='suggested_price' and state.pending=='asking':state.asking=None;return self._card(state)
        return self._reply(state,'كمّل من آخر سؤال أو اختار تعديل.',[[('تعديل','edit'),('إعلان جديد','new')]])
    def reply(self,chat_id,text):
        if not isinstance(text,str) or not text.strip():return Reply('ابعت نص أو فويس عربي. الصور مش متاحة دلوقتي.')
        text=text.strip()
        if len(text)>1500:return Reply('اختصر الوصف لأقل من ١٥٠٠ حرف.')
        if text.startswith('/start') or text=='/help':self.sessions.pop(chat_id,None);return Reply(escape(WELCOME))
        if text in ('/about','مساعدة'):return Reply(escape(ABOUT))
        if text in ('/reset','ابدأ من جديد','ابدا من جديد'):self.sessions.pop(chat_id,None);return Reply('ابعت وصف الخامة الجديدة.')
        if text.startswith('/search'):
            if self.search is None:
                from telegram_demo.conversation import Conversation
                self.search=Conversation()
            return Reply(escape(self.search.reply(chat_id,text)))
        now=time.monotonic();state=self.sessions.get(chat_id)
        if not state or now-state.updated>1800:state=State()
        state.updated=now;self.sessions[chat_id]=state
        if state.voice:
            if text in CONFIRM:return self.callback(chat_id,'ad:'+state.revision+':voice_yes')
            state.voice=''
        if text.startswith('/price'):text=text[len('/price'):].strip()
        if state.pending in SLOT_LABELS:return self._apply(state,state.pending,text)
        if state.pending=='retry':return self._next(state)
        if state.proposal:
            if text in CONFIRM:state.confirmed=True;return self._card(state)
            incoming=analyze_ad(PHONE.sub('',text.translate(AR_DIGITS)))['entities']
            if incoming.get('material_raw') and incoming.get('quantity_value'):
                state=State(updated=now);self.sessions[chat_id]=state
                return self._begin(state,text)
            return self._reply(state,'تحب تعدّل إيه في الإعلان؟',[[('تعديل','edit'),('إعلان جديد','new')]])
        return self._begin(state,text)
