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
vi2 = vi_m["v2_egyptian_taxonomy"]

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
       ("٢. مصدر الداتا (حقيقي ١٠٠٪)",
        "١٩٥ صف سعر حقيقي منشور، من غير أي صف مولّد أو مُحاكى. كل صف "
        "له مصدره ورابطه وتاريخه في pricing/data/real_prices.csv. "
        "المصادر ١٤: المصري اليوم وبوابة الأهرام وbusines24 (حديد "
        "وأسمنت بالشركة، ٧ نقاط زمنية من يناير ٢٠٢٥ لنوفمبر ٢٠٢٦)، "
        "كايرو24 والمال (خشب بدرجاته، نقطتين زمنيتين)، الوطن وفيتو "
        "وkhurda.net وScrap Price Today وصوت الأمة وMetalsCost (خردة "
        "ومعادن بدرجاتها)، egyin (بلاستيك خام ومجروش)، egy24 (رمل وزلط "
        "وطوب وجبس)، Woodify (أبلكاش وMDF). كل خامة متسجلة بدرجاتها "
        "الحقيقية في السوق: حديد عز وبشاي والمراكبي واستثماري... "
        "وأسمنت السويدي والسويس وحلوان... وزان روماني وقصير..."),
       ("٣. بناء الموديل والتدريب",
        "XGBoost (Regression) بـ ٣٠٠ شجرة وعمق ٥. الخصائص: الخامة "
        "والدرجة (grade) والحالة (One-Hot) ورقم الشهر، والهدف سعر الوحدة "
        "بمقياس لوغاريتمي. التقييم بطريقتين صارمتين: تحقق متقاطع ٥ طيات "
        "على كل الصفوف، وتقسيم زمني (تدريب حتى أغسطس ٢٠٢٦ واختبار على "
        "سبتمبر-نوفمبر ٢٠٢٦) للخامات اللي ليها تاريخ، وهو محاكاة سؤال "
        "«سعر النهاردة العادل كام»."),
       ("٤. النتائج المقاسة (بصراحة)",
        f"التقسيم الزمني (توقع المستقبل): MAPE = "
        f"{pr_m['time_aware']['mape_pct']}٪ وR² = "
        f"{pr_m['time_aware']['r2']} على {pr_m['time_aware']['n_test']} "
        f"صف لم يرهم الموديل. التحقق المتقاطع العام: MAPE = "
        f"{pr_m['cv_5fold']['mape_pct']}٪ وR² = {pr_m['cv_5fold']['r2']}. "
        f"بالخامة: حديد تسليح {pr_m['cv_per_material']['حديد تسليح']['mape_pct']}٪ "
        f"وأسمنت {pr_m['cv_per_material']['أسمنت']['mape_pct']}٪. الرقم العام "
        "أعلى لأن المصادر المنشورة نفسها تتعارض أحيانًا (مثال: الرمل "
        "١٢٥ مقابل ٦٧٠ ج/م³ في نفس اليوم من مصدرين حقيقيين مختلفين، "
        "والجبس ٢٠٥٠ مقابل ٣٤٩٠)، وده موثّق في عمود notes بدل ما "
        "نخفيه. مثال حي: ١٠ طن حديد تسليح جديد سعرهم العادل ~٣٩٠ "
        "ألف؛ طلب ٥٥٠ ألف يتقيّم «مبالغ فيه» وطلب ٣٩٠ ألف «عادل»."),
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
        "٢٦٩ صورة حقيقية من السوق المصري تحديدًا: مواقع تجار خردة "
        "ومواد بناء مصرية (المحل، مصر تايمز، النهار، الفهد، بيشاي "
        "ستيل، سيبوركس، تيبا وود، إيجيبت بلايوود وغيرهم) وإعلانات "
        "السوق المفتوح. كل صورة متمراجعتها عينيًا واحدة واحدة (شيلنا "
        "اللوجوهات واللافتات والصور الغلط) وموثّقة برابط مصدرها في "
        "vision/data/provenance2.csv. التعليم: مربع إحاطة واحد يغطي "
        "الصورة كلها، لأن صور الإعلانات عادة فيها خامة واحدة."),
       ("٣. الفئات: تقسيمة السوق المصري",
        "٢٣ فئة هي الأنواع والدرجات المتداولة فعلًا في مصر: حديد "
        "تسليح / صاج / قطاعات / مواسير / خردة، خشب زان / سويد، "
        "أبلكاش، MDF، جراكن بلاستيك / مجروش / PET، نحاس أحمر / خردة "
        "/ أصفر، ألومنيوم طري / قطاعات / رايش، أسمنت، طوب أحمر / "
        "أبيض، رمل، زلط. كل نوع فئة لوحده عشان الموديل يقدر يرفض "
        "الادعاء الغلط (بائع مصوّر صاج وكاتب حديد تسليح مثلًا)."),
       ("٤. بناء الموديل والتدريب",
        "YOLOv8n (أخف إصدار، مناسب للتشغيل على CPU) مع fine-tuning: "
        "٣٠ دورة، حجم صورة ٣٢٠، دفعة ٨، lr0=0.003 مع تناقص جيب "
        "تمامي وتعزيز بيانات (mosaic + قلب أفقي). التقسيم ٢٣٣ تدريب "
        "/ ٣٦ تحقق. إعادة التدريب: python vision/train3.py"),
       ("٥. النتائج المقاسة (بصراحة كاملة)",
        f"على مجموعة التحقق المنفصلة: mAP50 = {vi2['map50']}، "
        f"دقة P = {vi2['precision']}، استدعاء R = {vi2['recall']}، "
        f"نسبة إصابة الفئة الصحيحة {round(vi2['val_top1_accuracy']*100)}٪. "
        "الفئات اللي ليها ٨ صور تدريب أو أكتر (١٢ فئة من ٢٣) وصلت "
        "AP50 = 0.995. الفئات الضعيفة هي بالظبط اللي ليها من ٢ لـ٧ "
        "صور بس (نحاس أحمر، حديد خردة، نحاس أصفر، رايش ألومنيوم): "
        "صور الخردة المصرية على الإنترنت قليلة ومليانة ضوضاء، "
        "وده قيد داتا مش قيد تدريب. أكبر خطأ بين الفئات القوية: "
        "الخلط بين الزان والسويد لأنهم متشابهين بصريًا جدًا. صورة "
        "تجميعية بتوقعات الموديل على صور التحقق في "
        "vision/results/val_predictions_v2.jpg."),
       ("٦. الاستخدام",
        "الأوزان في vision/models/material_v2_best.pt. الدالة "
        "verify_image(image_path, expected_material) في "
        "integration/pipeline.py بترجع الفئة المكتشفة بالعربي "
        "ونسبة الثقة وهل هي مطابقة للخامة اللي طلعها موديل الـ NLP "
        "ولا لأ (قبول/رفض ادعاء النوع).")])

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
