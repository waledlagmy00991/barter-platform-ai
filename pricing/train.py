# -*- coding: utf-8 -*-
"""
Train the fair-price regression model (XGBoost) on REAL market data only.

Dataset: pricing/data/real_prices.csv — 100% real published Egyptian
market prices, one row per published price point, each with its source
name, URL and date. No synthetic or interpolated rows: the client
requirement is zero simulated data.

- Features: material, grade (e.g. عز / بشاي / السويدي / زان روماني),
  condition, months_since_start. Target: unit_price_egp (log-space).
- Evaluation, honest for a small real dataset:
  * 5-fold cross-validation over all rows (primary metric).
  * Time-aware split: train <= 2026-08, test >= 2026-09 (secondary,
    the realistic "predict today's fair price" setup).
- Output: pricing/model/pricing_model.joblib (pipeline + metadata) and
  pricing/results/metrics.json.

Also exposes fair_price() and evaluate_ask() used by the integration API.
"""
import json
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor

ROOT = Path(__file__).parent
START = (2025, 1)  # earliest real price point


def month_index(year, month):
    return (year - START[0]) * 12 + (month - START[1])


def load_data():
    df = pd.read_csv(ROOT / "data" / "real_prices.csv")
    df["months_since_start"] = [month_index(y, m)
                                for y, m in zip(df["year"], df["month"])]
    return df


FEATURES = ["material", "grade", "condition", "months_since_start"]


def build_pipeline():
    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"),
         ["material", "grade", "condition"]),
        ("num", "passthrough", ["months_since_start"]),
    ])
    model = XGBRegressor(
        n_estimators=300, max_depth=5, learning_rate=0.08,
        subsample=0.9, colsample_bytree=0.9, reg_lambda=1.0,
        objective="reg:squarederror", random_state=7, n_jobs=2)
    return Pipeline([("pre", pre), ("model", model)])


def score(y_true, pred):
    return {
        "mae_egp": round(float(mean_absolute_error(y_true, pred)), 2),
        "mape_pct": round(float(np.mean(np.abs(y_true - pred) / y_true) * 100), 2),
        "r2": round(float(r2_score(y_true, pred)), 4),
    }


def main():
    df = load_data()
    X, y = df[FEATURES], np.log(df["unit_price_egp"])

    # --- primary: 5-fold cross-validation over all real rows ---
    kf = KFold(n_splits=5, shuffle=True, random_state=7)
    cv_pred = np.zeros(len(df))
    for tr, te in kf.split(df):
        pipe = build_pipeline()
        pipe.fit(X.iloc[tr], y.iloc[tr])
        cv_pred[te] = pipe.predict(X.iloc[te])
    cv = score(df["unit_price_egp"], np.exp(cv_pred))

    # --- secondary: time-aware split (train on the past, test on Sep-Nov
    # 2026), restricted to materials that exist in the training window —
    # testing a material the model never saw would measure nothing.
    split_idx = month_index(2026, 9)
    tr_mask = df["months_since_start"] < split_idx
    seen = set(df.loc[tr_mask, "material"])
    te_mask = (~tr_mask) & df["material"].isin(seen)
    time_metrics, n_time_test = None, int(te_mask.sum())
    if tr_mask.sum() > 20 and te_mask.sum() > 5:
        pipe_t = build_pipeline()
        pipe_t.fit(X[tr_mask], y[tr_mask])
        pred_t = np.exp(pipe_t.predict(X[te_mask]))
        time_metrics = score(df.loc[te_mask, "unit_price_egp"], pred_t)

    # --- per-material CV error, for an honest per-material report ---
    df["cv_pred"] = np.exp(cv_pred)
    per_material = {}
    for mat, g in df.groupby("material"):
        if len(g) < 3:
            continue
        per_material[mat] = {
            "n": int(len(g)),
            "mape_pct": round(float(np.mean(
                np.abs(g["unit_price_egp"] - g["cv_pred"])
                / g["unit_price_egp"]) * 100), 2),
            "real_range_egp": [float(g["unit_price_egp"].min()),
                               float(g["unit_price_egp"].max())],
        }

    # --- final model on all rows ---
    pipe = build_pipeline()
    pipe.fit(X, y)
    grade_mode = {mat: Counter(g["grade"]).most_common(1)[0][0]
                  for mat, g in df.groupby("material")}
    meta = {
        "features": FEATURES,
        "start_month": f"{START[0]}-{START[1]:02d}",
        "trained_until": "%d-%02d" % max(zip(df["year"], df["month"])),
        "n_rows": int(len(df)),
        "n_materials": int(df["material"].nunique()),
        "n_sources": int(df["source_url"].nunique()),
        "data": "100% real published Egyptian market prices "
                "(pricing/data/real_prices.csv, per-row source URL). "
                "No synthetic or interpolated rows.",
        "grade_defaults": grade_mode,
    }
    model_dir = ROOT / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": pipe, "meta": meta}, model_dir / "pricing_model.joblib")

    results = {
        "model": "XGBRegressor(n_estimators=300, max_depth=5, lr=0.08)",
        "target": "unit_price_egp (log-space)",
        "data_provenance": meta["data"],
        "cv_5fold": {"split": "5-fold CV, all real rows", "n": len(df), **cv},
        "cv_per_material": per_material,
    }
    if time_metrics:
        results["time_aware"] = {
            "split": "train <= 2026-08, test >= 2026-09",
            "n_train": int(tr_mask.sum()), "n_test": n_time_test,
            **time_metrics}
    out = ROOT / "results" / "metrics.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
