# -*- coding: utf-8 -*-
"""Independent labeled test for detect_condition (text keyword extraction).
Labels are hand-written ground truth, one condition per ad."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pipeline import detect_condition

CASES = [
    # (ad text, expected condition)
    ("حديد تسليح جديد ١٠ طن", "جديد"),
    ("صاج جديد لمسته متر ونص", "جديد"),
    ("مواسير جداد استيراد", "جديد"),
    ("ألومنيوم زيرو من المصنع", "جديد"),
    ("طوب أحمر جديد من المحرق", "جديد"),
    ("خشب سويد استعمال مرة واحدة", "مستعمل"),
    ("سقالات مستعملة بحالة كويسة", "مستعمل"),
    ("حديد مستعمل من هدم عمارة", "مستعمل"),
    ("أوناش ومعدات مستعملة", "مستعمل"),
    ("شدات شبه جديد للبيع", "مستعمل"),
    ("بلاطات رجيع مصنع", "مستعمل"),
    ("حديد مخزون قديم", "مستعمل"),
    ("مواسير زهر شبه جديد", "مستعمل"),
    ("سكراب حديد ٥ طن", "هالك"),
    ("حديد هالك من مصانع", "هالك"),
    ("هالك حديد مخلوط نحاس", "هالك"),
    ("صاج صدأ قديم", "صدأ"),
    ("حديد صدي من المخازن", "صدأ"),
    ("مواسير عليها صدأ", "صدأ"),
    ("خردة نحاس أحمر", "هالك"),
    ("كابلات ألومنيوم", None),
    ("رمل أحمر نظيف", None),
    ("طوب سيبوركس أبيض", None),
    ("أسمنت مقاوم شكاير", None),
    ("حديد تسليح ١٢ مم", None),
    ("خشب زان ألواح", None),
    ("غرابيل وهزازات", None),
    ("بلاستيك مجروش PET", None),
    ("سلوك نحاس", None),
    ("معدات ورشة خراطة", None),
    ("بويات مستعملة", "مستعمل"),
    ("نحاس أصفر هالك", "هالك"),
    ("ألومنيوم بروفايل مستعمل", "مستعمل"),
    ("جيركون بلاستيك مستعمل", "مستعمل"),
    ("طوب أبيض جديد عازل", "جديد"),
    ("حديد جديد معتمد", "جديد"),
    ("خردة استانلس", "هالك"),
    ("صاج استانلس معجن", None),
    ("مواسير بلاستيك جديدة", "جديد"),
]

def run():
    rows = []
    correct = 0
    for text, expected in CASES:
        got = detect_condition(text)
        ok = (got == expected)
        correct += ok
        rows.append({"text": text, "expected": expected, "got": got, "ok": ok})
    acc = correct / len(CASES)
    out = {"n_cases": len(CASES), "accuracy": round(acc, 4),
           "wrong": [r for r in rows if not r["ok"]]}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return out

if __name__ == "__main__":
    run()
