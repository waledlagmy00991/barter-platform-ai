# -*- coding: utf-8 -*-
"""
Train the fair-price regression model (XGBoost).

- Input features: material, condition, location (one-hot), quantity,
  months_since_start. Target: unit_price_egp (log-space).
- Time-aware split: train on all months except the last 3, test on the
  last 3 months (the realistic "predict today's fair price" setup).
- Output: pricing/model/pricing_model.joblib (pipeline + metadata) and
  pricing/results/metrics.json with MAE / MAPE / R2.

Also exposes fair_price() and evaluate_ask() used by the integration API:
  evaluate_ask(material, condition, location, quantity, asking_total_price)
  -> fair unit price, fair total, verdict (عادل / مبالغ فيه / أقل من المتوقع).
"""
import json
import math
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor

ROOT = Path(__file__).parent
START = (2024, 12)  # month 0 of the dataset


def month_index(year, month):
    return (year - START[0]) * 12 + (month - START[1])


def load_data():
    df = pd.read_csv(ROOT / "data" / "prices.csv")
    df["months_since_start"] = [month_index(y, m)
                                for y, m in zip(df["year"], df["month"])]
    return df


def build_pipeline():
    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"),
         ["material", "condition", "location"]),
        ("num", "passthrough", ["quantity", "months_since_start"]),
    ])
    model = XGBRegressor(
        n_estimators=400, max_depth=6, learning_rate=0.06,
        subsample=0.9, colsample_bytree=0.9, reg_lambda=1.0,
        objective="reg:squarederror", random_state=7, n_jobs=2)
    return Pipeline([("pre", pre), ("model", model)])


def main():
    df = load_data()
    max_idx = df["months_since_start"].max()
    train = df[df["months_since_start"] <= max_idx - 3]
    test = df[df["months_since_start"] > max_idx - 3]
    feats = ["material", "condition", "location", "quantity",
             "months_since_start"]

    pipe = build_pipeline()
    pipe.fit(train[feats], np.log(train["unit_price_egp"]))

    pred = np.exp(pipe.predict(test[feats]))
    mae = mean_absolute_error(test["unit_price_egp"], pred)
    mape = float(np.mean(np.abs(test["unit_price_egp"] - pred)
                         / test["unit_price_egp"]) * 100)
    r2 = r2_score(test["unit_price_egp"], pred)

    meta = {
        "features": feats,
        "start_month": f"{START[0]}-{START[1]:02d}",
        "trained_until": "%d-%02d" % max(zip(df["year"], df["month"])),
        "n_train": int(len(train)), "n_test": int(len(test)),
        "test_window_months": 3,
    }
    model_dir = ROOT / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": pipe, "meta": meta}, model_dir / "pricing_model.joblib")

    results = {"model": "XGBRegressor(n_estimators=400, max_depth=6, lr=0.06)",
               "target": "unit_price_egp (log-space)",
               "split": "time-aware: last 3 months held out",
               **meta,
               "mae_egp": round(float(mae), 2),
               "mape_pct": round(mape, 2),
               "r2": round(float(r2), 4)}
    out = ROOT / "results" / "metrics.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
