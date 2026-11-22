# -*- coding: utf-8 -*-
"""UNSEEN generalization set for detect_condition - written after the fix,
disjoint phrasing from the 39 regression cases. Run once, no tuning."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pipeline import detect_condition

CASES = [
    ("عندي حديد قديم مستعمل من شغل تكسير", "مستعمل"),
    ("طن صاج مستعمل بحالته", "مستعمل"),
    ("مواسير استعمال شهرين بس", "مستعمل"),
    ("عدة بناء شبه جديدة", "مستعمل"),
    ("شدة معدنية شبه جديد", "مستعمل"),
    ("خلاطة رجيع", "مستعمل"),
    ("بضاعة مخزون قديم", "مستعمل"),
    ("حديد هالك للبيع بالطن", "هالك"),
    ("سكراب مصانع مختلط", "هالك"),
    ("خرده نحاس والومنيوم", "هالك"),
    ("سكرابه حديد زهر", "هالك"),
    ("خردة صاج مضلع", "هالك"),
    ("مواسير فيها صدأ تقيل", "صدأ"),
    ("حديد صدي تحت الشمس", "صدأ"),
    ("صاج عليه صدا خفيف", "صدأ"),
    ("طوب أحمر طازج من الفرن", None),
    ("أسمنت بورتلاندي عادي", None),
    ("رمل زلط توريد مواقع", None),
    ("كابلات السويدي", None),
    ("دهانات وعزل", None),
    ("حديد عز ١٦ مم", None),
    ("خشب أرو روسي", None),
    ("نحاس أحمر cathode", None),
    ("بلوك أبيض عازل", None),
    ("جبس بورد", None),
    ("حديد صدي ومستعمل مع بعض", "صدأ"),
    ("سكراب وخردة مخلوطة", "هالك"),
    ("معدات مستعملة وصدئة", "مستعمل"),
    ("زيرو لمسته من المعرض", "جديد"),
    ("بضاعة جديدة بالضمان", "جديد"),
]

if __name__ == "__main__":
    correct = 0; wrong = []
    for text, expected in CASES:
        got = detect_condition(text)
        if got == expected: correct += 1
        else: wrong.append({"text": text, "expected": expected, "got": got})
    print(json.dumps({"n": len(CASES), "accuracy": round(correct/len(CASES), 4), "wrong": wrong}, ensure_ascii=False, indent=1))
