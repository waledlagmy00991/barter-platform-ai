# -*- coding: utf-8 -*-
"""
End-to-end tests: sentences written BY HAND, outside the training data,
run through the full pipeline (NER -> parsing -> pricing -> final JSON).

Run from the repo root:  python -m pytest tests/ -v
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from integration.pipeline import analyze_ad, parse_quantity  # noqa: E402

# Handwritten sentences that do NOT come from the training generator.
OOD_CASES = [
    ("عندي حوالي ٣٠ طن حديد تسليح في مدينة بدر عايز ابيعهم",
     "حديد تسليح", 30.0, "طن", "بدر"),
    ("مطلوب خشب سويد ١٢ متر مكعب للشراء بمدينة السادات",
     "خشب سويد", 12.0, "متر مكعب", "السادات"),
    ("يا جماعه عايز ٥٠ شيكاره اسمنت في العاشر ضروري",
     "أسمنت", 50.0, "شيكارة", "العاشر"),
    ("معايا ٢ طن نحاس احمر في شبرا الخيمه",
     "نحاس", 2.0, "طن", "شبرا الخيمه"),
    ("عايز ٥ الاف طوب احمر في برج العرب",
     "طوب أحمر", 5.0, "ألف", "برج العرب"),
    ("محتاج ١٠ طن بلاستيك مجروش في الزقازيق بسرعه",
     "بلاستيك مجروش", 10.0, "طن", "الزقازيق"),
    ("فيه ٣ طن سكراب حديد عندنا في حلوان",
     "حديد خردة", 3.0, "طن", "حلوان"),
    ("عندي ٢٥ متر مكعب رمل ناعم في دمياط الجديده",
     "رمل", 25.0, "متر مكعب", "دمياط الجديده"),
    ("ابيع ٤٠ لوح ام دي اف في ٦ اكتوبر",
     "MDF", 40.0, "لوح", "٦ اكتوبر"),
    ("متوفر ١٥ طن صاج مجلفن في مدينة العبور",
     "صاج", 15.0, "طن", "العبور"),
]


@pytest.mark.parametrize("text,mat,qty,unit,loc", OOD_CASES)
def test_ood_sentence(text, mat, qty, unit, loc):
    r = analyze_ad(text)
    ents = r["entities"]
    assert ents["material_canonical"] == mat, \
        f"material: {ents['material_canonical']} != {mat} ({text})"
    assert ents["quantity_value"] == qty, \
        f"qty: {ents['quantity_value']} != {qty} ({text})"
    assert ents["quantity_unit"] == unit, \
        f"unit: {ents['quantity_unit']} != {unit} ({text})"
    assert ents["location"] is not None and loc in ents["location"], \
        f"location: {ents['location']} missing {loc} ({text})"


def test_quantity_parser():
    assert parse_quantity("٥٠ طن") == (50.0, "طن")
    assert parse_quantity("خمسين كيلو") == (50.0, "كيلو")
    assert parse_quantity("٢٫٥ طن") == (2.5, "طن")
    assert parse_quantity("خمسة ونص متر مكعب") == (5.5, "متر مكعب")
    assert parse_quantity("150 ألف") == (150.0, "ألف")
    assert parse_quantity("تلتمية شيكارة") == (300.0, "شيكارة")


def test_pricing_flags_overpriced():
    r = analyze_ad("عندي ٣٠ طن حديد تسليح جديد في العاشر من رمضان",
                   asking_total_price=1_900_000)
    assert r["pricing"]["verdict"] == "مبالغ فيه"
    assert not r["pricing"]["is_fair"]


def test_pricing_accepts_fair():
    from pricing.predict import fair_price
    unit = fair_price("حديد تسليح", "جديد", "العاشر من رمضان", 30)
    r = analyze_ad("عندي ٣٠ طن حديد تسليح جديد في العاشر من رمضان",
                   asking_total_price=unit * 30 * 1.05)
    assert r["pricing"]["verdict"] == "عادل"
    assert r["pricing"]["is_fair"]


def test_missing_fields_warn_not_crash():
    r = analyze_ad("عايز ابيع شوية حاجات عندي")
    assert r["entities"]["material_canonical"] is None
    assert r["pricing"] is None
    assert r["warnings"]


def test_final_json_shape():
    r = analyze_ad("مطلوب ٢٠ طن أسمنت في السويس", asking_total_price=50000)
    assert set(r) >= {"input_text", "entities", "pricing", "warnings"}
    assert set(r["entities"]) >= {"material_canonical", "quantity_value",
                                  "quantity_unit", "location"}
    assert set(r["pricing"]) >= {"fair_total_price_egp", "verdict",
                                 "is_fair"}
