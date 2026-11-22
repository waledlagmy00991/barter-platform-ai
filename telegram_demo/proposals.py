"""Grounded ad drafts for private review, not publication or inventory lookup."""
import re
import time
from dataclasses import dataclass
from integration.pipeline import analyze_ad, AR_DIGITS, UNITS, map_material, detect_condition
from pricing.predict import estimate_reference
from telegram_demo.groq_provider import draft_proposal, ProviderUnavailable

HELP=('تجربة خاصة، مش منصة بيع فعلية ولا جاهزية إنتاجية.\n'
      'ابعت وصف الخامة كتابة أو فويس عربي لحد ٩٠ ثانية: الكمية والوحدة والحالة والمكان. '
      'هستخرج التفاصيل بموديل NER اللي بعتّه، وأسأل عن الناقص، ثم أقترح عنوان ووصف بذكاء اصطناعي وسعر مرجعي لو البيانات تدعمه. '
      'مش لازم تدخل سعر مطلوب. النص والفويس اللازمين للتجربة بيتم معالجتهم عبر Groq مع إيقاف حفظ محتوى الاستدلال. '
      'السعر من موديل تطويري على أسعار مصرية منشورة محفوظة، مش تسعير سوق مباشر. '
      'مفيش نشر أو بيع أو شراء، ومفيش فحص صور. راجع الاقتراح بنفسك.\n'
      '/reset طلب جديد. /search بحث في أمثلة مولّدة، مش مخزون حقيقي. /about شرح التجربة.')

@dataclass
class State:
    text:str=''
    pending:bool=False
    voice:str=''
    updated:float=0
    fields:dict=None
    needed:tuple=()

class ProposalConversation:
    def __init__(self):self.sessions={};self.search=None
    def voice_preview(self,chat_id,transcript):
        self.sessions[chat_id]=State(voice=transcript,updated=time.monotonic())
        return 'سمعت الفويس كده، راجع النص قبل أي تسعير:\n'+transcript+'\nلو صحيح اكتب تأكيد. لو فيه غلط ابعت الوصف مكتوب، أو /reset.'
    def reply(self,chat_id,text):
        if not isinstance(text,str) or not text.strip():return 'ابعت نص أو فويس عربي. فحص الصور مش متاح.'
        text=text.strip()
        if len(text)>1500:return 'اختصر الوصف لأقل من ١٥٠٠ حرف.'
        if text.startswith('/start') or text in ('/help','/about','مساعدة'):
            self.sessions.pop(chat_id,None);return HELP
        if text in ('/reset','ابدأ من جديد','ابدا من جديد'):
            self.sessions.pop(chat_id,None);return 'بدأنا طلب جديد. ابعت الوصف بالكمية والوحدة والحالة والمكان.'
        if text.startswith('/search'):
            if self.search is None:
                from telegram_demo.conversation import Conversation
                self.search=Conversation()
            return self.search.reply(chat_id,text)
        now=time.monotonic();state=self.sessions.get(chat_id)
        if state is None or now-state.updated>1800:state=State()
        if state.voice:
            if text in ('تأكيد','تاكيد','صح','نعم','تمام'):
                text=state.voice
            state=State()
        if text.startswith('/price'):text=text[len('/price'):].strip()
        if not state.pending:state=State()
        if state.pending:
            incoming=analyze_ad(text)['entities'] if text else {}
            if incoming.get('material_raw') and incoming.get('quantity_value'):
                state.text='';state.fields=None;state.needed=()
        state.text=(state.text+' '+text).strip();state.updated=now
        self.sessions[chat_id]=state
        result=analyze_ad(state.text);e=result['entities'];raw=result['raw_entities']
        if state.fields:
            # Keep a previously observed source span when appending an answer
            # changes the NER's labeling of the earlier part of the same text.
            previous=state.fields
            if not e['location'] and previous.get('location') and previous['location'] in state.text:
                e['location']=previous['location']
            if not e['material_raw'] and previous.get('material_raw') and previous['material_raw'] in state.text:
                for k in ['material_raw','material_canonical','material_assumed_generic']:e[k]=previous[k]
            if not e['quantity_value'] and previous.get('quantity_raw') and previous['quantity_raw'] in state.text:
                for k in ['quantity_raw','quantity_value','quantity_unit']:e[k]=previous[k]
        if state.needed==('location',) and not e['location'] and re.fullmatch(r'[ء-ي][ء-ي\s-]{1,50}',text) and not any(w in text for w in ['عارف','معرفش','اعرف','مش عارف']):
            e['location']=text
        state.fields=e.copy()

        # Multiple lots cannot be collapsed into the first NER entity.
        numeric_lots=re.findall(r'(?:\d+(?:\.\d+)?|خمسين|عشرين|تلاتين)\s*(?:طن|كيلو|كجم|لوح|شيكارة|متر)',state.text.translate(AR_DIGITS))
        if len(raw.get('MATERIAL',[]))>1 or len(raw.get('QUANTITY',[]))>1 or len(raw.get('LOCATION',[]))>1 or len(numeric_lots)>1:
            state.text='';state.pending=True
            return 'الوصف فيه أكتر من خامة أو كمية أو مكان. ابعت عرض واحد بس كامل، عشان ما أخلطش تفاصيلهم أو أسعارهم.'
        prompts=[]
        if not e['material_canonical'] or e['material_assumed_generic']:prompts.append('نوع الخامة بالتحديد، زي حديد تسليح أو حديد خردة أو خشب زان')
        if not e['quantity_value'] or not e['quantity_unit']:prompts.append('الكمية والوحدة مع بعض، زي ٣٠ طن')
        if not e['condition_detected']:prompts.append('حالة واحدة واضحة: جديد أو مستعمل أو خردة، ولو الوصف فيه تعارض صححه')
        if not e['location']:prompts.append('مكان الخامة، زي القاهرة أو المنصورة')
        if prompts:
            needed=[]
            if not e['material_canonical'] or e['material_assumed_generic']:needed.append('material')
            if not e['quantity_value'] or not e['quantity_unit']:needed.append('quantity')
            if not e['condition_detected']:needed.append('condition')
            if not e['location']:needed.append('location')
            state.needed=tuple(needed)
            state.pending=True
            return 'محتاج أوضّح: '+'؛ '.join(prompts)+'.\nابعت الوصف كامل بعد التصحيح، أو رد بالتفاصيل الناقصة.'
        facts={k:v for k,v in e.items() if k in ['material_canonical','material_raw','quantity_raw','quantity_value','quantity_unit','condition_detected','location']}
        try:proposal=draft_proposal(state.text,facts)
        except ProviderUnavailable:
            state.pending=True
            return 'استخرجت التفاصيل، لكن خدمة صياغة الإعلان المجانية مش متاحة دلوقتي أو وصلت حد الاستخدام. مش هبدّلها برد متولّد مزيف. جرّب لاحقًا أو /reset.'
        generated=proposal['title']+' '+proposal['description']
        generated_material,_=map_material(generated)
        generated_condition=detect_condition(generated)
        if generated_material!=e['material_canonical'] or (generated_condition is not None and generated_condition!=e['condition_detected']) or e['location'] not in generated:
            state.pending=True
            return 'المسودة ما عدّتش فحص تطابق الخامة والحالة والمكان مع وصفك. مش هعرض اقتراح فيه تفاصيل مختلفة. ابعت الوصف كامل تاني.'
        if proposal['consistency']=='conflict':
            state.text='';state.pending=True
            return 'في تعارض محتمل، مش هطلع سعر قبل توضيحه:\n'+'\n'.join(str(x)[:300] for x in proposal['issues'])+'\nابعت وصف واحد بعد التصحيح.'
        state.pending=False
        from pricing.predict import grade_from_text
        grade=grade_from_text(e['material_canonical'],e['condition_detected'],state.text)
        price=estimate_reference(e['material_canonical'],e['condition_detected'],e['location'],e['quantity_value'],
                                 quantity_unit=e['quantity_unit'],grade=grade,material_confirmed=not e['material_assumed_generic'])
        out='مسودة للمراجعة فقط، ما اتنشرتش.\nالعنوان: '+proposal['title']+'\nالوصف: '+proposal['description']
        out+='\n\nالتفاصيل المستخرجة: '+str(e['quantity_value'])+' '+e['quantity_unit']+' '+str(e['material_raw'])+'؛ الحالة المذكورة '+e['condition_detected']+'؛ المكان '+e['location']+'.'
        if price['supported']:
            out+=f"\nمرجع الموديل: {price['fair_unit_price_egp']:,.2f} جنيه/{price['price_unit']}، إجمالي {price['fair_total_price_egp']:,.2f} جنيه."
            if price['grade_is_default']:
                out+='\nمرجع على درجة/ماركة افتراضية في بيانات التدريب: '+price['grade_used']+'، مش صفة مثبتة لخامتك. اختلاف الدرجة أو الماركة ممكن يغيّر السعر.'
            else:out+='\nالدرجة/الماركة المستخدمة كما وردت في وصفك: '+price['grade_used']+'.'
            out+='\nده مرجع تطويري من أسعار مصرية منشورة محفوظة، مش سعر سوق حالي ولا إثبات عدالة سعر. المكان والمقاسات مش عوامل في موديل السعر، والكمية بتستخدم لحساب الإجمالي فقط. الحالة مش متحقّق منها بصورة.'
        else:out+='\nمش هخمن سعر للتركيبة أو الوحدة دي. سبب الامتناع: '+str(price['reason'])+'. وزن الشيكارة أو اللوح مش مفترض.'
        if proposal['issues']:out+='\nملاحظات للمراجعة: '+'؛ '.join(str(x)[:250] for x in proposal['issues'])
        out+='\nراجع كل التفاصيل، والتزم بفحص الخامة فعليًا قبل أي اتفاق. /reset لوصف جديد.'
        return out
