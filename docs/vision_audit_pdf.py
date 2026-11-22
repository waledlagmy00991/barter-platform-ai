#!/usr/bin/env python3
"""Current Arabic vision documentation. Historical metrics are not production claims."""
from pathlib import Path
import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

ROOT = Path(__file__).resolve().parent.parent
SECTIONS = [
    ('الحالة الحالية: متوقف للتدقيق',
     'الموديل مش جاهز للبرودكشن. المراجعة المستقلة أكدت إن بيانات التقييم ملوّثة ومفيش تقدير أداء صالح. التدريب وجمع صور جديدة وترقية الأوزان متوقفين لحد تحقق شروط تعافي البيانات. الأوزان الحالية محفوظة من غير تغيير.'),
    ('الموديل بيعمل إيه؟',
     'بيجرب يصنّف نوع الخامة من الصورة ضمن ٢٣ فئة. التعليم المستخدم مربع بيغطي الصورة كلها، فقياسه مش تقييم كشف أجسام حقيقي بحدود دقيقة. التعرف البصري على الصدأ أو التفريق بين جديد ومستعمل مش مدعوم.'),
    ('ليه الأرقام القديمة مش معتمدة؟',
     'كل أرقام الرؤية القديمة مسحوبة كدليل على التعميم أو تحديد مكان الخامة. المراجعة المستقلة أكدت تلوث مجموعة الاختيار، وصور متشابهة بين التدريب والتحقق، ومصادر مشتركة وتسميات غير مثبتة. ادعاء إن كل الصور مصرية اتسحب. مفيش دلوقتي مجموعة تدريب نظيفة ولا تقدير أداء صالح.'),
    ('العدّ الصحيح والأدلة المحفوظة',
     'النسخة الحالية فيها ٢٦٠ ملف تدريب و٦٢ ملف تحقق. اختبار المحمّل قرأ كل ملف مرة واحدة، من غير تحميل أوزان أو حساب أداء. عدد مجموعة التحقق زاد من ٦٠ إلى ٦٢ بإضافة صورتين، مع نقل تسمية صورة تالتة. تفسير إن صور الطوب قلت من عشرة لخمسة كان خلط بين العدّ المكرر والملفات الفعلية، واتسحب.'),
    ('احتمال تلوث التقييم بتدريب الأوزان',
     'المراجعة المستقلة أكدت إن بيانات الأوزان بتشير لمجموعة تدريب أقدم اسمها dataset2. فيه ٤٦ صورة تحقق حالية متطابقة بالبايت مع صور مجلد التدريب القديم المحتفظ به. المجلد نفسه مش سجل تاريخي مربوط تشفيريًا بالأوزان، لكن الأدلة دي تمنع اعتماد أي رقم تعميم حالي. فصل الملفات في التقسيم الجديد لوحده مش كفاية.'),
    ('مكان الأدلة',
     'صور التحقق وتسمياتها وبصماتها محفوظة في مجلد evaluation/legacy62_v1 داخل فولدر الرؤية. أدلة التدريب القديم في evaluation/retained_yolo2_evidence. تفاصيل المصدر وتاريخ العضوية في evaluation/README.md وسجلات التدقيق. دي ملفات أدلة محفوظة، مش بيانات مصدّق على صلاحيتها.'),
    ('الخطوات الجاية',
     'التعافي محتاج بيانات جديدة فعلًا، بحقوق استخدام واضحة، وتجميع حسب المصدر والمورد بأدلة، وتسميات مناسبة للمهمة يراجعها مستقلون. لو المطلوب تحديد مكان أجسام، لازم مربعات حقيقية مش مربع للصورة كلها. إصلاح المجموعة القديمة مش هيخليها اختبار نهائي جديد. الصورة المسماة صاج وهي خامة صلب سميكة تفضل في الحجر، مش تتصلح بالتخمين.'),
    ('تشغيل التطوير والحقوق',
     'الأوزان موجودة للتجربة المحلية فقط. ما تستخدمش النتيجة لقبول إعلان أو رفضه تلقائيًا. المستودع خاص، وصور البائعين ما تخرجش لديمو عام أو جمهور جديد. سجل المصدر مش إذن استخدام تجاري. مناقشة الجمعة ٢٧ نوفمبر ٢٠٢٦ نقطة مراجعة، مش نهاية تكليف الجاهزية للإنتاج.')
]

def build_vision_audit_pdf(path=None, sections=None, title_text=None, continuation_title=None):
    path = path or ROOT/'vision/docs/vision_model_doc.pdf'
    pdfmetrics.registerFont(TTFont('VisionAmiri','/tmp/Amiri-Regular.ttf'))
    style = ParagraphStyle('body',fontName='VisionAmiri',fontSize=11.5,leading=20,alignment=TA_RIGHT,spaceAfter=8)
    heading = ParagraphStyle('head',parent=style,fontSize=14,leading=23,spaceBefore=10,textColor='#0b5394')
    title = ParagraphStyle('title',parent=heading,fontSize=19,leading=28)
    shape=lambda s:get_display(arabic_reshaper.reshape(s))
    def body_paragraph(text):
        lines=[]
        words=[]
        for word in text.split():
            candidate=' '.join(words+[word])
            if words and pdfmetrics.stringWidth(shape(candidate),'VisionAmiri',style.fontSize)>475:
                lines.append(shape(' '.join(words)))
                words=[word]
            else:
                words.append(word)
        if words:
            lines.append(shape(' '.join(words)))
        return Paragraph('<br/>'.join(lines),style)
    story=[Paragraph(shape(title_text or 'موديل الرؤية: حالة التدقيق وحدود الاستخدام'),title),Paragraph(shape('تحديث ٢٢ نوفمبر ٢٠٢٦'),style),Spacer(1,8)]
    for i,(h,b) in enumerate(sections or SECTIONS):
        if i==4:
            story.extend([PageBreak(),Paragraph(shape(continuation_title or 'أدلة التدريب والخطوات الجاية'),title),Spacer(1,8)])
        story.extend([Paragraph(shape(h),heading),body_paragraph(b)])
    SimpleDocTemplate(str(path),pagesize=A4,rightMargin=54,leftMargin=54,topMargin=40,bottomMargin=40).build(story)
    print(path)

if __name__=='__main__':
    build_vision_audit_pdf()
