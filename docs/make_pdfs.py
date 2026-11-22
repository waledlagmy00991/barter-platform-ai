# -*- coding: utf-8 -*-
"""Generate the per-model Arabic documentation PDFs (RTL, Amiri font)."""
import json
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT

ROOT = Path(__file__).parent.parent
pdfmetrics.registerFont(TTFont("Amiri", "/tmp/Amiri-Regular.ttf"))

TITLE = ParagraphStyle("t", fontName="Amiri", fontSize=18, leading=26,
                       alignment=TA_RIGHT, textColor="#0b5394")
H = ParagraphStyle("h", fontName="Amiri", fontSize=13.5, leading=20,
                   alignment=TA_RIGHT, textColor="#0b5394",
                   spaceBefore=10)
B = ParagraphStyle("b", fontName="Amiri", fontSize=11.5, leading=18,
                   alignment=TA_RIGHT)


def ar(text):
    """Shape + reorder Arabic for reportlab, line by line."""
    out = []
    for line in text.split("\n"):
        out.append(get_display(arabic_reshaper.reshape(line)))
    return "<br/>".join(out)


def build(path, title, sections):
    doc = SimpleDocTemplate(str(path), pagesize=A4,
                            rightMargin=2 * cm, leftMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm)
    story = [Paragraph(ar(title), TITLE), Spacer(1, 12)]
    for head, body in sections:
        story.append(Paragraph(ar(head), H))
        for para in body.split("\n"):
            if para.strip():
                story.append(Paragraph(ar(para.strip()), B))
    doc.build(story)
    print("wrote", path)


def metrics(p):
    return json.load(open(p, encoding="utf-8"))


ner_m = metrics(ROOT / "ner/results/metrics.json")
pr_m = metrics(ROOT / "pricing/results/metrics.json")
vi_m = metrics(ROOT / "vision/results/metrics.json")

build(ROOT / "ner/docs/ner_model_doc.pdf",
      "موديل الـ NLP لتحليل إعلانات التجار (NER)",
      [("١. الهدف",
        "التاجر بيكتب إعلانه بشكل عشوائي (صوت أو نص) بالعامية المصرية، زي: "
        "«أنا عندي ٥٠ طن حديد سايب كده». المطلوب موديل يقرأ الجملة ويطلّع "
        "منها ٣ كيانات: الخامة (Material)، الكمية لوحدتها (Quantity)، "
        "والمكان (Location). ده أول موديل في السلسلة وأولوية قصوى."),
       ("٢. مصدر الداتا وتجميعها",
        f"جمعنا {ner_m['n_train'] + ner_m['n_dev'] + ner_m['n_test']} جملة "
        "إعلان بالعامية المصرية مولّدة بأنماط السوق الحقيقية: أخطاء إملائية "
        "شائعة (ى/ي، ة/ه، الهمزة)، اختصارات السوق (شيكارة، سن، مجروش، "
        "سكراب، خرازة، أبلكاش)، أرقام عربية (٥٠) وإنجليزية (50) وبالحروف "
        "(خمسين، تلتمية)، وصيغ بيع وشراء مختلفة. التعليم (Annotation) "
        "اتعمل برمجيًا بحساب مواضع الكيانات أثناء التوليد، فدقته ١٠٠٪، "
        "ومتاح أيضًا بصيغة Label Studio في data/labelstudio_tasks.json. "
        f"التقسيم: {ner_m['n_train']} تدريب / {ner_m['n_dev']} تحقق / "
        f"{ner_m['n_test']} اختبار."),
       ("٣. بناء الموديل والتدريب",
        "استخدمنا مكتبة SpaCy: نموذج عربي فاضي spacy.blank('ar') + مكوّن "
        "NER بثلاث تسميات MATERIAL وQUANTITY وLOCATION. التدريب "
        f"{ner_m['epochs']} دورة (Epochs) مع Dropout بقيمة "
        f"{ner_m['dropout']} ودفعات minibatch، ونحتفظ بأفضل نموذج على "
        "مجموعة التحقق. إعادة التدريب: python ner/train.py"),
       ("٤. النتائج المقاسة",
        f"على مجموعة الاختبار المنفصلة: الدقة P = "
        f"{ner_m['splits']['test']['ents_p']:.4f}، الاستدعاء R = "
        f"{ner_m['splits']['test']['ents_r']:.4f}، ومقياس F = "
        f"{ner_m['splits']['test']['ents_f']:.4f} (المطلوب كان ٨٥٪ على الأقل). "
        "وفي اختبار أقسى: جمل مكتوبة يدويًا من خارج بيانات التدريب تمامًا "
        "(اختبارات tests/test_integration.py) نجح الموديل في استخراج "
        "الخامة والكمية والمكان صح في الغالبية العظمى منها."),
       ("٥. الاستخدام",
        "النموذج المدرّب في ner/model/ ويُحمّل بـ spacy.load('ner/model'). "
        "الاستخدام الفعلي يمر عبر integration/pipeline.py اللي بيحوّل "
        "الكيانات الخام لقيم مهيكلة (مثلاً «٥٠ طن» تتحول لقيمة 50 ووحدة «طن»).")])

build(ROOT / "pricing/docs/pricing_model_doc.pdf",
      "موديل التسعير الذكي (Pricing Model)",
      [("١. الهدف",
        "بعد ما الموديل الأول يعرف إن التاجر بيعرض «حديد»، عايزين نعرف إن "
        "السعر اللي طالبه «لقطة» ولا «مبالغ فيه» ولا «عادل». الموديل "
        "بياخد مواصفات الإعلان ويتوقع السعر العادل، ولو سعر العميل بعيد "
        "عن التوقع بأكتر من ٢٠٪ بيطلع تنبيه إن السعر محتاج مراجعة."),
       ("٢. مصدر الداتا",
        "٦٠٠٠ صف أسعار لخامات السوق المصري (حديد تسليح وخردة، خشب زان "
        "وسويد وموسكي، بلاستيك مجروش، ألومنيوم، نحاس، رصاص، صاج، استانلس، "
        "أسمنت، جبس، رمل، زلط، طوب أحمر وأبيض، أبلكاش، MDF) على مدار ٢٤ "
        "شهر. الداتا مولّدة على أساس نطاقات الأسعار المنشورة في الصحافة "
        "المصرية (نوفمبر ٢٠٢٦: الحديد ~٣٧-٤٠ ألف ج/طن، الخشب ~١٥٫٥-٣٣٫٥ "
        "ألف ج/م³) مع ترند زمني صاعد، وتأثير الحالة (جديد/مستعمل/صدأ/هالك) "
        "والمحافظة وخصم الكميات، وضوضاء سوق واقعية. الملف: "
        "pricing/data/prices.csv"),
       ("٣. بناء الموديل والتدريب",
        "موديل كلاسيكي XGBoost (Regression) - زي ما الوثيقة طلبت - "
        "بـ ٤٠٠ شجرة وعمق ٦. الخصائص: الخامة والحالة والمكان (One-Hot) "
        "والكمية ورقم الشهر، والهدف: سعر الوحدة بالجنيه (بمقياس لوغاريتمي). "
        "التقسيم زمني: التدريب على كل الشهور ما عدا آخر ٣ شهور تُترك "
        "للاختبار، عشان نحاكي سؤال «سعر النهاردة العادل كام»."),
       ("٤. النتائج المقاسة",
        f"على آخر ٣ شهور (محجوبة تمامًا): R² = {pr_m['r2']}، متوسط الخطأ "
        f"النسبي MAPE = {pr_m['mape_pct']}٪، متوسط الخطأ المطلق "
        f"{pr_m['mae_egp']:.0f} جنيه. مثال حي: ٣٠ طن حديد تسليح جديد في "
        "العاشر من رمضان سعره العادل ~١٫١٢٥ مليون؛ طلب ١٫٩ مليون يتعلّم "
        "«مبالغ فيه»، وطلب ٥٪ زيادة يتقيّم «عادل»."),
       ("٥. الاستخدام",
        "الموديل في pricing/model/pricing_model.joblib. الدالة "
        "evaluate_ask(material, condition, location, quantity, "
        "asking_total_price) بترجع السعر العادل والنسبة والحكم بالعربي. "
        "إعادة التدريب: python pricing/train.py")])

build(ROOT / "vision/docs/vision_model_doc.pdf",
      "موديل الرؤية للتحقق والمطابقة (YOLOv8)",
      [("١. الهدف",
        "العميل كاتب إنه بيبيع «حديد جديد»، بس رافع صورة «حديد مصدّي». "
        "الموديل بيحلل الصورة ويتأكد إنها مطابقة للكلام: بيكتشف نوع "
        "الخامة وحالتها (Object Detection) ويطابق النتيجة مع نتيجة "
        "موديل الـ NLP."),
       ("٢. مصدر الداتا",
        "١٤٤ صورة حقيقية (٢٤ لكل فئة × ٦ فئات: steel_new، steel_rusted، "
        "wood_new، wood_used، plastic_new، plastic_scrap) من Wikimedia "
        "Commons وOpenverse برخص مفتوحة (CC). كل صورة موثّقة برابط "
        "مصدرها ورخصتها في vision/data/provenance.csv. التعليم: مربع "
        "إحاطة واحد يغطي الصورة كلها، لأن صور الإعلانات عادة بيبقى فيها "
        "خامة واحدة."),
       ("٣. بناء الموديل والتدريب",
        "YOLOv8n (أخف إصدار، مناسب للتشغيل على CPU) مع fine-tuning: "
        "٣٠ دورة، حجم صورة ٣٢٠، دفعة ٨، lr0=0.003 مع تناقص جيب تمامي "
        "وتعزيز بيانات (mosaic + قلب أفقي). التقسيم ١٢٠ تدريب / ٢٤ "
        "تحقق. إعادة التدريب: python vision/train.py"),
       ("٤. النتائج المقاسة",
        f"على مجموعة التحقق المنفصلة: mAP@50 = {vi_m['map50']}، "
        f"mAP@50-95 = {vi_m['map50_95']}، دقة P = {vi_m['precision']}، "
        f"استدعاء R = {vi_m['recall']}. لكل فئة: "
        + "، ".join(f"{k} {v}" for k, v in vi_m["per_class"].items())
        + ". ملحوظة بصراحة: الداتا صغيرة (٢٤ صورة/فئة) والفئات المتشابهة "
        "بصريًا (wood_used مقابل wood_new) هي الأصعب؛ زيادة الصور لكل "
        "فئة هي الخطوة التالية المخططة لرفع الدقة أكثر."),
       ("٥. الاستخدام",
        "الأوزان في vision/model/best.pt. الدالة "
        "verify_image(image_path, expected_material) في "
        "integration/pipeline.py بترجع الفئة المكتشفة ونسبة الثقة "
        "وهل هي مطابقة لنتيجة الـ NLP ولا لأ.")])

build(ROOT / "chatbot/docs/chatbot_doc.pdf",
      "البحث الدلالي والشات بوت (RAG)",
      [("١. إيه اللي عايزين نعمله",
        "حاجتين من الوثيقة: محرك بحث دلالي (Semantic Search) بيفهم "
        "المعنى مش الحروف، وشات بوت (AI Chatbot) بيسجّل طلب العميل لو "
        "الحاجة مش موجودة ويقترح بدائل، ويرد بس من داتا المنصة."),
       ("٢. الخطوات بالترتيب",
        "أولاً: جهزنا قاعدة إعلانات (٦٠٠ إعلان) مولّدة من نفس قواميس "
        "موديل الـ NER ومسعّرة بموديل التسعير الفعلي، فالداتا متسقة مع "
        "باقي النظام (chatbot/generate_ads.py). "
        "ثانيًا: حوّلنا كل إعلان لأرقام (Embeddings) بنموذج "
        "paraphrase-multilingual-MiniLM-L12-v2 المتعدد اللغات اللي "
        "بيفهم العربي والعامية (chatbot/build_index.py). "
        "ثالثًا: خزنّا الأرقام في Vector DB نوعه FAISS "
        "(chatbot/index/ads.faiss). "
        "رابعًا: الرد بيتولّد RAG: بنسترجع أقرب الإعلانات وبنجاوب من "
        "بياناتها الحقيقية فقط - كل رقم في الرد مصدره إعلان مسجل، مفيش "
        "هلوسة."),
       ("٣. تحسين مهم: استرجاع هجين",
        "الـ embeddings لوحدها ممكن تتلخبط في العامية المصرية، فضفنا "
        "تعزيزًا بالكلمات المفتاحية: لو الاستعلام فيه اسم خامة معروفة "
        "(من قاموس مرادفات الـ pipeline) أو اسم محافظة، الإعلانات "
        "المطابقة بتتقدّم. النتيجة: استعلام «عايز حديد» مبيرجعش "
        "إعلانات أسمنت أبدًا."),
       ("٤. الـ LLM اختياري",
        "الشات بوت شغال كامل offline بصياغة منظمة (deterministic). لو "
        "اتوفّر مفتاح Gemini في متغير البيئة GEMINI_API_KEY، الرد "
        "بيتصاغ بلغة طبيعية أحسن - بس برضه مقيد بالإعلانات المسترجعة "
        "بس (RAG حقيقي)."),
       ("٥. الاستخدام",
        "from chatbot.chatbot import ask ثم ask('عايز ٢٠ طن حديد في "
        "العاشر'). البحث المباشر: search(query, k=5). لو الطلب مش موجود "
        "بيرد إنه هيسجّل الطلب وينبّه العميل - زي ما الوثيقة طلبت.")])
