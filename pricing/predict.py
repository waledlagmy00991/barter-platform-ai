# -*- coding: utf-8 -*-
"""
Fair-price inference for the pricing model.

    from pricing.predict import fair_price, evaluate_ask

evaluate_ask() compares a seller's asking price with the model's fair
price and returns a verdict:
  - "عادل"            within +/-20%
  - "مبالغ فيه"       asking more than 20% above fair
  - "أقل من المتوقع"  asking more than 20% below fair (suspiciously cheap)
"""
import math
import os
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
FLAG_THRESHOLD = 0.20

_bundle = None


def _load():
    global _bundle
    if _bundle is None:
        _bundle = joblib.load(ROOT / "model" / "pricing_model.joblib")
    return _bundle


def _month_index(year, month):
    sy, sm = map(int, _load()["meta"]["start_month"].split("-"))
    return (year - sy) * 12 + (month - sm)


def fair_price(material, condition, location=None, quantity=1, on=None,
               grade=None):
    """Return the fair unit price (EGP) for one unit of the material.

    `location` is accepted for API compatibility: Egyptian published
    prices are national, so it is not a model feature. `grade` is the
    market grade/brand (e.g. عز, السويدي, زان روماني); when omitted,
    the material's most common grade in the real dataset is used.
    """
    bundle = _load()
    on = on or date.today()
    if grade is None:
        grade = bundle["meta"].get("grade_defaults", {}).get(material, "قياسي")
    row = pd.DataFrame([{
        "material": material, "grade": grade, "condition": condition,
        "months_since_start": _month_index(on.year, on.month),
    }])
    return float(np.exp(bundle["pipeline"].predict(row)[0]))


_COMBOS = None

def supported_combos():
    """(material, condition) pairs actually present in the real dataset.
    Condition is confounded with material in the published data (used/scrap
    rows exist only for scrap-market materials), so the model cannot price
    condition as a variable; unsupported combos must not get a verdict."""
    global _COMBOS
    if _COMBOS is None:
        df = pd.read_csv(os.path.join(os.path.dirname(__file__),
                                      'data', 'real_prices.csv'))
        _COMBOS = set(zip(df['material'], df['condition']))
    return _COMBOS


def evaluate_ask(material, condition, location, quantity, asking_total_price,
                 on=None, grade=None):
    if (material, condition) not in supported_combos():
        ref = None
        if (material, "جديد") in supported_combos():
            ref = round(fair_price(material, "جديد", location, quantity,
                                   on=on, grade=grade), 2)
        return {
            "fair_unit_price_egp": None,
            "fair_total_price_egp": None,
            "asking_total_price_egp": round(float(asking_total_price), 2),
            "ask_vs_fair_ratio": None,
            "is_fair": None,
            "verdict": None,
            "supported": False,
            "reference_new_unit_price_egp": ref,
            "warning": ("لا توجد بيانات منشورة لتركيبة الخامة والحالة دي؛ "
                        "لا يمكن إصدار حكم تسعير. الرقم المرجعي (إن وجد) "
                        "هو سعر الجديد فقط."),
        }
    unit = fair_price(material, condition, location, quantity, on=on,
                      grade=grade)
    fair_total = unit * float(quantity)
    ratio = asking_total_price / fair_total if fair_total else float("inf")
    if ratio > 1 + FLAG_THRESHOLD:
        verdict = "مبالغ فيه"
        fair = False
    elif ratio < 1 - FLAG_THRESHOLD:
        verdict = "أقل من المتوقع"
        fair = False
    else:
        verdict = "عادل"
        fair = True
    return {
        "fair_unit_price_egp": round(unit, 2),
        "fair_total_price_egp": round(fair_total, 2),
        "asking_total_price_egp": round(float(asking_total_price), 2),
        "ask_vs_fair_ratio": round(ratio, 3),
        "is_fair": fair,
        "verdict": verdict,
        "supported": True,
        "flag_threshold": FLAG_THRESHOLD,
    }
