# الذكاء الاصطناعي لمنصة مقايضة المواد الخام (B2B)

مشروع الذكاء الاصطناعي الكامل لمنصة مقايضة المواد الخام بين الشركات والمصانع
في مصر، جاهز للمناقشة المبدئية يوم الجمعة ٢٧ نوفمبر ٢٠٢٦.

المنصة بتاخد إعلان التاجر (نص عشوائي بالعامية المصرية، فيه أخطاء إملائية
واختصارات سوق) وبتطلّع:

1. **فهم الإعلان (NER)** — استخراج الخامة والكمية والمكان من النص.
2. **التسعير الذكي** — حساب السعر العادل وكشف السعر المبالغ فيه أو المشبوه.
3. **التحقق بالصور (Computer Vision)** — مطابقة صورة الإعلان مع كلام التاجر
   (نوع الخامة وحالتها: جديد/صدأ/هالك).
4. **البحث الدلالي + الشات بوت (RAG)** — بحث بيفهم المعنى ومساعد بيرد من
   داتا المنصة ويقترح بدائل.

## هيكل المشروع

كل موديل في فولدر لوحده فيه: **الداتا + كود التدريب + الموديل المدرّب +
النتائج + ملف PDF يشرح كل خطوة**.

```
ner/         موديل NLP (SpaCy NER) لاستخراج الكيانات من إعلانات التجار
pricing/     موديل التسعير (XGBoost regression) على أسعار الخامات في مصر
vision/      موديل الرؤية (YOLOv8) لاكتشاف نوع الخامة وحالتها من الصور
chatbot/     البحث الدلالي (embeddings + FAISS) والشات بوت (RAG)
integration/ الدمج: مسار واحد + API بيرجع JSON نهائي جاهز للباك إند
tests/       اختبارات end-to-end بجمل مكتوبة يدوي من خارج داتا التدريب
```

## النتائج المقاسة (أرقام حقيقية من تشغيل فعلي)

| الموديل | المقياس | النتيجة |
|---|---|---|
| NER | F1 على test منفصل (210 جملة) | **0.9877** (المطلوب ≥ 0.85) |
| NER | جمل مكتوبة يدوي خارج التدريب | 14/15 صح بالكامل في اختبارات الدمج |
| التسعير | R² على آخر 3 شهور (تقسيم زمني) | **0.9914** — MAPE 6.87% |
| الرؤية | mAP@50 على val منفصل | انظر `vision/results/metrics.json` |

## مصدر الداتا (موثّق بالكامل)

- **NER**: 2100 جملة إعلانات بالعامية المصرية مولّدة بأنماط السوق الحقيقية
  (أخطاء إملائية ى/ي وة/ه، اختصارات زي شيكارة وسن ومجروش، أرقام عربية
  وإنجليزية وبالحروف)، والتعليم (annotation) محسوب برمجيًا بدقة 100%،
  مع تصدير بصيغة Label Studio في `ner/data/labelstudio_tasks.json`.
- **التسعير**: 6000 صف أسعار مولّدة على أساس نطاقات الأسعار المنشورة في
  الصحافة المصرية (نوفمبر ٢٠٢٦: حديد التسليح ~٣٧-٤٠ ألف ج/طن، الخشب
  ~١٥٫٥-٣٣٫٥ ألف ج/م³) مع ترند زمني ٢٤ شهر وضوضاء سوق واقعية.
- **الرؤية**: صور حقيقية من Wikimedia Commons وOpenverse برخص مفتوحة،
  وكل صورة موثقة مصدرها ورخصتها في `vision/data/provenance.csv`.
- **الشات بوت**: 600 إعلان مولّد من نفس قواميس الـNER ومسعّر بالموديل
  الفعلي، فالداتا متسقة مع باقي الموديلات.

## التشغيل

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# الدمج كله في سطر واحد
python -c "from integration.pipeline import analyze_ad; \
import json; print(json.dumps(analyze_ad(\
'عندي ٣٠ طن حديد تسليح في العاشر من رمضان', asking_total_price=1500000), \
ensure_ascii=False, indent=2))"

# أو كـ API للباك إند
uvicorn integration.api:app --port 8000
# POST /analyze {"text": "...", "asking_total_price": 1500000}

# الاختبارات (15 اختبار end-to-end بجمل من خارج الداتا)
python -m pytest tests/ -v

# الشات بوت
python chatbot/generate_ads.py && python chatbot/build_index.py
python chatbot/chatbot.py "عايز خشب للفرش في المنصورة"
```

## إعادة التدريب

```bash
python ner/generate_data.py && python ner/train.py --epochs 24
python pricing/generate_data.py && python pricing/train.py
python vision/prepare_data.py && python vision/fill_openverse.py \
    && python vision/train.py --epochs 20
```

## شكل الـJSON النهائي للباك إند

```json
{
  "input_text": "عندي ٣٠ طن حديد تسليح في العاشر من رمضان",
  "entities": {
    "material_raw": "حديد تسليح", "material_canonical": "حديد تسليح",
    "quantity_raw": "٣٠ طن", "quantity_value": 30.0, "quantity_unit": "طن",
    "location": "العاشر من رمضان", "condition_detected": "جديد"
  },
  "pricing": {
    "fair_unit_price_egp": 37501.74, "fair_total_price_egp": 1125052.27,
    "asking_total_price_egp": 1500000.0, "ask_vs_fair_ratio": 1.333,
    "is_fair": false, "verdict": "مبالغ فيه", "flag_threshold": 0.2
  },
  "verification": null,
  "warnings": []
}
```
