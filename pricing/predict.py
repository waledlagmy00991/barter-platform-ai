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
    if (material, condition) not in supported_combos():
        raise ValueError("Unsupported material and condition; no fair-price estimate is available")
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


def supported_units(material):
    df = pd.read_csv(ROOT / 'data' / 'real_prices.csv')
    return set(df.loc[df['material'] == material, 'unit'])


def evaluate_ask(material, condition, location, quantity, asking_total_price,
                 on=None, grade=None, quantity_unit=None, material_confirmed=True):
    if isinstance(quantity, bool) or not math.isfinite(float(quantity)) or float(quantity) <= 0:
        raise ValueError('quantity must be finite and positive')
    if isinstance(asking_total_price, bool) or not math.isfinite(float(asking_total_price)) or float(asking_total_price) <= 0:
        raise ValueError('asking_total_price must be finite and positive')
    quantity = float(quantity)
    asking_total_price = float(asking_total_price)
    units = supported_units(material)
    price_unit = next(iter(units)) if len(units) == 1 else None
    normalized_quantity = None
    if quantity_unit == price_unit and price_unit is not None:
        normalized_quantity = quantity
    elif quantity_unit == 'كيلو' and price_unit == 'طن':
        normalized_quantity = quantity / 1000

    reason = None
    if not material_confirmed:
        reason = 'material_assumed'
    elif condition is None:
        reason = 'condition_unknown'
    elif (material, condition) not in supported_combos():
        reason = 'condition_unsupported'
    elif normalized_quantity is None:
        reason = 'quantity_unit_missing_or_unsupported'

    common = {
        'asking_total_price_egp': round(asking_total_price, 2),
        'input_quantity': quantity,
        'input_quantity_unit': quantity_unit,
        'price_unit': price_unit,
        'pricing_quantity': normalized_quantity,
        'condition_used': condition,
        'production_validated': False,
    }
    if reason is not None:
        ref = None
        if (material, 'جديد') in supported_combos():
            ref = round(fair_price(material, 'جديد', location, on=on, grade=grade), 2)
        return dict(common, fair_unit_price_egp=None, fair_total_price_egp=None,
            ask_vs_fair_ratio=None, is_fair=None, verdict=None, supported=False,
            reason=reason, reference_new_unit_price_egp=ref,
            reference_price_unit=price_unit, reference_material=material,
            warning='الخامة أو الحالة أو وحدة الكمية غير كافية لحكم تسعير. المرجع إن وجد سعر الجديد لكل وحدة منشورة فقط، مش حكم عدالة سعر. وزن الشيكارة لا يتم افتراضه.')
    unit = fair_price(material, condition, location, on=on, grade=grade)
    fair_total = unit * normalized_quantity
    if not math.isfinite(fair_total) or fair_total <= 0:
        raise ValueError('calculated total is outside the supported numeric range')
    ratio = asking_total_price / fair_total
    if not math.isfinite(ratio):
        raise ValueError('price ratio is outside the supported numeric range')
    if ratio > 1 + FLAG_THRESHOLD:
        verdict, fair = 'مبالغ فيه', False
    elif ratio < 1 - FLAG_THRESHOLD:
        verdict, fair = 'أقل من المتوقع', False
    else:
        verdict, fair = 'عادل', True
    return dict(common, fair_unit_price_egp=round(unit, 2),
        fair_total_price_egp=round(fair_total, 2), ask_vs_fair_ratio=round(ratio, 3),
        is_fair=fair, verdict=verdict, supported=True, flag_threshold=FLAG_THRESHOLD,
        warning='تقدير تطويري من أسعار منشورة، مش تقييم إنتاجي مستقل ولا عرض بيع مؤكد.')
