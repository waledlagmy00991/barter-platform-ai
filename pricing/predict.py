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


def fair_price(material, condition, location, quantity, on=None):
    """Return the fair unit price (EGP) for one unit of the material."""
    bundle = _load()
    on = on or date.today()
    row = pd.DataFrame([{
        "material": material, "condition": condition, "location": location,
        "quantity": float(quantity),
        "months_since_start": _month_index(on.year, on.month),
    }])
    return float(np.exp(bundle["pipeline"].predict(row)[0]))


def evaluate_ask(material, condition, location, quantity, asking_total_price,
                 on=None):
    unit = fair_price(material, condition, location, quantity, on=on)
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
        "flag_threshold": FLAG_THRESHOLD,
    }
