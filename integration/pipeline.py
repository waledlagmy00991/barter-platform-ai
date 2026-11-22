# -*- coding: utf-8 -*-
"""
Integration pipeline: one code path from raw ad text to backend-ready JSON.

    from integration.pipeline import analyze_ad
    result = analyze_ad("عندي ٣٠ طن حديد في العاشر", asking_total_price=1_500_000)

Chains: NER model -> text normalization/parsing -> pricing model.
Optional: vision model verification when an image path is given.

The returned dict is the final JSON the backend consumes.
"""
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "pricing"))

import spacy  # noqa: E402

# ------------------------------------------------------------------ models
_NER = None
_VISION = None

CONDITION_KEYWORDS = {
    "هالك": "هالك", "صدأ": "صدأ", "صدي": "صدأ", "مستعمل": "مستعمل",
    "استعمال": "مستعمل", "جديد": "جديد", "جداد": "جديد", "زيرو": "جديد",
    "شبه جديد": "مستعمل", "رجيع": "مستعمل", "مخزون": "مستعمل",
}

# alias substring -> canonical pricing material (longest match wins)
MATERIAL_ALIASES = {
    "حديد تسليح": "حديد تسليح", "حديد مسلح": "حديد تسليح",
    "حديد عز": "حديد تسليح", "حديد المصريين": "حديد تسليح",
    "حدبد": "حديد تسليح", "حديد": "حديد تسليح", "الحديد": "حديد تسليح",
    "حديد خردة": "حديد خردة", "خردة حديد": "حديد خردة",
    "حديد سكراب": "حديد خردة", "سكراب حديد": "حديد خردة",
    "خردة": "حديد خردة", "خرده": "حديد خردة",
    "صاج": "صاج", "الصاج": "صاج",
    "استانلس": "استانلس ستيل", "ستانلس": "استانلس ستيل",
    "خشب زان": "خشب زان", "خشب سويد": "خشب سويد", "خشب موسكي": "خشب موسكي",
    "خشب أرو": "خشب سويد", "خشب ارو": "خشب سويد", "خشب أرز": "خشب زان",
    "خشب ارز": "خشب زان", "خشب أبيض": "خشب سويد", "خشب ابيض": "خشب سويد",
    "خشب": "خشب سويد", "الخشب": "خشب سويد",
    "أبلكاش": "أبلكاش", "ابليكاش": "أبلكاش", "البلكاش": "أبلكاش",
    "ابلكاش": "أبلكاش",
    "MDF": "MDF", "mdf": "MDF", "ام دي اف": "MDF", "أم دي أف": "MDF",
    "بلاستيك": "بلاستيك مجروش", "بلاستك": "بلاستيك مجروش",
    "مجروش": "بلاستيك مجروش", "خرازة": "بلاستيك مجروش", "pet": "بلاستيك مجروش",
    "ألومنيوم": "ألومنيوم", "الومنيوم": "ألومنيوم", "ألمونيوم": "ألومنيوم",
    "المونيوم": "ألومنيوم", "المونيا": "ألومنيوم",
    "نحاس": "نحاس", "النحاس": "نحاس",
    "رصاص": "رصاص", "الرصاص": "رصاص",
    "أسمنت أبيض": "أسمنت أبيض", "اسمنت ابيض": "أسمنت أبيض",
    "أسمنت": "أسمنت", "اسمنت": "أسمنت",
    "جبس": "جبس", "الجبس": "جبس",
    "رمل": "رمل", "الرمل": "رمل", "رملة": "رمل",
    "زلط": "زلط", "الزلط": "زلط", "سن": "زلط",
    "طوب أبيض": "طوب أبيض", "طوب ابيض": "طوب أبيض",
    "طوب": "طوب أحمر", "الطوب": "طوب أحمر", "بلوكات": "طوب أحمر",
}
_GENERIC_DEFAULTS = {"خشب": "خشب سويد", "خشب أبيض": "خشب سويد",
                     "خشب ابيض": "خشب سويد", "طوب": "طوب أحمر",
                     "بلاستيك": "بلاستيك مجروش", "بلاستك": "بلاستيك مجروش",
                     "حديد": "حديد تسليح", "حدبد": "حديد تسليح"}

AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789.")
NUM_WORDS = {
    "واحد": 1, "واحدة": 1, "اتنين": 2, "اثنين": 2, "تلاتة": 3, "ثلاثة": 3,
    "أربعة": 4, "اربعة": 4, "أربع": 4, "خمسة": 5, "خمس": 5, "ستة": 6,
    "ست": 6, "سبعة": 7, "سبع": 7, "تمانية": 8, "ثمانية": 8, "تمنية": 8,
    "تسعة": 9, "تسع": 9, "عشرة": 10, "عشر": 10, "حداشر": 11,
    "اتناشر": 12, "اثناشر": 12, "تلاتاشر": 13, "أربعتاشر": 14,
    "اربعتاشر": 14, "خمستاشر": 15, "ستاشر": 16, "سبعتاشر": 17,
    "تمنتاشر": 18, "تسعتاشر": 19, "عشرين": 20, "تلاتين": 30,
    "ثلاثين": 30, "أربعين": 40, "اربعين": 40, "خمسين": 50, "ستين": 60,
    "سبعين": 70, "تمانين": 80, "ثمانين": 80, "تسعين": 90, "مية": 100,
    "مائة": 100, "مائتين": 200, "ميتين": 200, "تلتمية": 300,
    "ثلثمية": 300, "ربعمية": 400, "خمسمية": 500, "ستمية": 600,
    "سبعمية": 700, "تمنمية": 800, "ثمنمية": 800, "تسعمية": 900,
    "ألف": 1000, "الف": 1000, "ألفين": 2000, "الفين": 2000,
}
UNITS = ["طن", "كيلو جرام", "كيلوجرام", "كيلو", "كجم", "متر مكعب",
         "متر طولي", "متر", "لوح", "ألواح", "الواح", "شيكارة", "شكارة",
         "شكاير", "شيكاير", "شيكاره", "شكاره", "ألف", "الف", "آلاف",
         "الاف"]
UNIT_CANON = {"كيلو جرام": "كيلو", "كيلوجرام": "كيلو", "كجم": "كيلو",
              "ألواح": "لوح", "الواح": "لوح", "شكارة": "شيكارة",
              "شكاير": "شيكارة", "شيكاير": "شيكارة", "شيكاره": "شيكارة",
              "شكاره": "شيكارة", "آلاف": "ألف",
              "الاف": "ألف", "الف": "ألف", "متر طولي": "متر"}


def _load_ner():
    global _NER
    if _NER is None:
        _NER = spacy.load(ROOT / "ner" / "model")
    return _NER


def parse_quantity(text):
    """Parse a QUANTITY span like '٥٠ طن', 'خمسين كيلو', '٢٫٥ طن',
    'خمسة ونص متر مكعب', '١٥٠ ألف' -> (value, unit)."""
    t = text.strip().translate(AR_DIGITS)
    t = t.replace("ونص", "ونص")
    unit = None
    for u in sorted(UNITS, key=len, reverse=True):
        if u in t:
            unit = UNIT_CANON.get(u, u)
            t = t.replace(u, " ")
            break
    half = 0.5 if "ونص" in t or "و نص" in t else 0.0
    t = t.replace("ونص", " ").replace("و نص", " ")
    m = re.search(r"\d+(?:\.\d+)?", t)
    if m:
        value = float(m.group(0))
    else:
        total = 0.0
        found = False
        for tok in t.split():
            if tok in NUM_WORDS:
                total += NUM_WORDS[tok]
                found = True
        if not found:
            return None, unit
        value = total
    value += half
    return value, unit


def detect_condition(text):
    for kw, cond in CONDITION_KEYWORDS.items():
        if kw in text:
            return cond
    return "جديد"


def map_material(material_text):
    t = material_text.strip()
    if t in MATERIAL_ALIASES:
        return MATERIAL_ALIASES[t], t in _GENERIC_DEFAULTS
    for alias in sorted(MATERIAL_ALIASES, key=len, reverse=True):
        if alias in t:
            return MATERIAL_ALIASES[alias], alias in _GENERIC_DEFAULTS
    return None, False


def analyze_ad(text, asking_total_price=None, image_path=None):
    """Full pipeline: text (+ optional price, + optional image) -> JSON."""
    nlp = _load_ner()
    doc = nlp(text)
    raw = {"MATERIAL": [], "QUANTITY": [], "LOCATION": []}
    for e in doc.ents:
        raw.setdefault(e.label_, []).append(e.text)

    material_raw = (raw.get("MATERIAL") or [None])[0]
    quantity_raw = (raw.get("QUANTITY") or [None])[0]
    location = (raw.get("LOCATION") or [None])[0]

    material, assumed_material = (None, False)
    if material_raw:
        material, assumed_material = map_material(material_raw)

    qty_value, qty_unit = (None, None)
    if quantity_raw:
        qty_value, qty_unit = parse_quantity(quantity_raw)

    condition = detect_condition(text)

    result = {
        "input_text": text,
        "entities": {
            "material_raw": material_raw,
            "material_canonical": material,
            "material_assumed_generic": bool(assumed_material),
            "quantity_raw": quantity_raw,
            "quantity_value": qty_value,
            "quantity_unit": qty_unit,
            "location": location,
            "condition_detected": condition,
        },
        "pricing": None,
        "verification": None,
        "warnings": [],
    }

    if not material_raw:
        result["warnings"].append("لم يتم استخراج الخامة من النص")
    elif not material:
        result["warnings"].append(
            "الخامة المستخرجة غير معروفة: " + str(material_raw))
    if not quantity_raw:
        result["warnings"].append("لم يتم استخراج الكمية من النص")
    if not location:
        result["warnings"].append("لم يتم استخراج المكان من النص")

    if asking_total_price is not None:
        if material and qty_value:
            from pricing.predict import evaluate_ask
            result["pricing"] = evaluate_ask(
                material, condition, location or "القاهرة",
                qty_value, asking_total_price)
            if assumed_material:
                result["warnings"].append(
                    "الخامة عامة، تم الافتراض: " + material)
        else:
            result["warnings"].append(
                "لا يمكن التسعير بدون خامة وكمية واضحتين")

    if image_path:
        result["verification"] = verify_image(image_path, material)

    return result


def verify_image(image_path, expected_material=None):
    """Run the YOLOv8 model on an ad photo and compare with the NLP result."""
    global _VISION
    weights = ROOT / "vision" / "model" / "best.pt"
    if not weights.exists():
        return {"available": False,
                "note": "نموذج الرؤية غير مدرّب بعد"}
    if _VISION is None:
        from ultralytics import YOLO
        _VISION = YOLO(str(weights))
    preds = _VISION.predict(str(image_path), verbose=False)[0]
    if not len(preds.boxes):
        return {"available": True, "detected": None,
                "match": None, "note": "لم يتم رصد خامة في الصورة"}
    box = max(preds.boxes, key=lambda b: float(b.conf))
    cls = preds.names[int(box.cls)]
    conf = round(float(box.conf), 3)
    detected_material = cls.split("_")[0]
    match = None
    if expected_material:
        mat_map = {"steel": "حديد", "wood": "خشب", "plastic": "بلاستيك"}
        ar = mat_map.get(detected_material, detected_material)
        match = ar in (expected_material or "") or \
            any(ar in a for a in MATERIAL_ALIASES
                if MATERIAL_ALIASES[a] == expected_material)
    return {"available": True, "detected_class": cls,
            "confidence": conf, "match": match}
