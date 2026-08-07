"""Day 8: gradient-boosted demand forecasts using leakage-safe SKU features.

The final 28 calendar dates are reserved for validation.  Features were built
before this script runs and contain only information available before each
target date; rows are never randomly shuffled across the time boundary.
"""

from __future__ import annotations

import csv
import gzip
import importlib.util
import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "features_daily_sku.csv.gz"
OUT = ROOT / "data" / "processed"
DOC = ROOT / "docs" / "day8_ml_forecasting.md"
VALIDATION_DAYS = 28
MAX_TRAINING_ROWS = 250_000
TARGET = "target_demand_units"
FEATURES = (
    "sku_code", "days_since_series_start", "lag_1_demand", "lag_7_demand",
    "lag_14_demand", "lag_28_demand", "rolling_7d_avg_demand",
    "rolling_28d_avg_demand", "last_observed_unit_price", "price_age_days",
    "day_of_week", "day_of_month", "week_of_year", "month", "quarter",
    "is_weekend", "day_of_year_sin", "day_of_year_cos", "day_of_week_sin",
    "day_of_week_cos",
)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def metrics(actual: np.ndarray, predicted: np.ndarray) -> tuple[float, float, float]:
    errors = np.abs(actual - predicted)
    mae = float(errors.mean())
    rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))
    wmape = float(errors.sum() / actual.sum()) if actual.sum() else 0.0
    return mae, rmse, wmape


def load_rows() -> tuple[np.ndarray, np.ndarray, list[dict[str, str]], date, date]:
    """Load model features and determine a global calendar validation boundary."""
    sku_codes: dict[str, int] = {}
    raw_rows: list[dict[str, str]] = []
    dates: list[date] = []
    with gzip.open(INPUT, "rt", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            raw_rows.append(row)
            dates.append(datetime.fromisoformat(row["date"]).date())
            sku_codes.setdefault(row["sku_id"], len(sku_codes))
    if not raw_rows:
        raise ValueError(f"No feature rows found in {INPUT}")
    last_date = max(dates)
    validation_start = last_date - timedelta(days=VALIDATION_DAYS - 1)
    values = np.empty((len(raw_rows), len(FEATURES)), dtype=np.float32)
    target = np.empty(len(raw_rows), dtype=np.float32)
    for index, row in enumerate(raw_rows):
        target[index] = float(row[TARGET])
        for column, name in enumerate(FEATURES):
            if name == "sku_code":
                values[index, column] = sku_codes[row["sku_id"]]
            else:
                value = row[name]
                values[index, column] = float(value) if value else np.nan
    return values, target, raw_rows, validation_start, last_date


def available_models() -> dict[str, object]:
    models: dict[str, object] = {}
    if importlib.util.find_spec("xgboost"):
        from xgboost import XGBRegressor
        models["xgboost"] = XGBRegressor(
            objective="reg:squarederror", n_estimators=150, learning_rate=0.05,
            max_depth=6, min_child_weight=5, subsample=0.8, colsample_bytree=0.8,
            reg_lambda=1.0, random_state=42, n_jobs=4, tree_method="hist",
        )
    if importlib.util.find_spec("lightgbm"):
        from lightgbm import LGBMRegressor
        models["lightgbm"] = LGBMRegressor(
            objective="regression", n_estimators=150, learning_rate=0.05,
            num_leaves=63, min_child_samples=20, subsample=0.8,
            colsample_bytree=0.8, reg_lambda=1.0, random_state=42, n_jobs=4,
            verbosity=-1,
        )
    return models


def main() -> None:
    features, target, rows, validation_start, last_date = load_rows()
    validation_mask = np.array([
        datetime.fromisoformat(row["date"]).date() >= validation_start for row in rows
    ])
    train_mask = ~validation_mask
    if not train_mask.any() or not validation_mask.any():
        raise ValueError("Time split produced an empty training or validation set.")
    # Keep the most recent training history when the wide SKU panel would make
    # an interactive training run unreasonably large. This is still wholly
    # before the validation boundary and is deterministic.
    train_indexes = np.flatnonzero(train_mask)
    if len(train_indexes) > MAX_TRAINING_ROWS:
        train_indexes = np.array(sorted(train_indexes, key=lambda index: rows[index]["date"], reverse=True)[:MAX_TRAINING_ROWS])
    models = available_models()
    if not models:
        raise RuntimeError("Install xgboost and/or lightgbm first: python -m pip install -r requirements.txt")

    predictions: dict[str, np.ndarray] = {}
    for name, model in models.items():
        model.fit(features[train_indexes], target[train_indexes])
        predictions[name] = np.maximum(0.0, model.predict(features[validation_mask]))

    validation_indexes = np.flatnonzero(validation_mask)
    forecast_rows: list[dict[str, object]] = []
    for local_index, global_index in enumerate(validation_indexes):
        source = rows[global_index]
        output: dict[str, object] = {
            "date": source["date"], "sku_id": source["sku_id"],
            "description": source["description"], "actual_demand_units": f"{target[global_index]:.4f}",
        }
        output.update({name: f"{values[local_index]:.4f}" for name, values in predictions.items()})
        forecast_rows.append(output)
    fields = ["date", "sku_id", "description", "actual_demand_units", *predictions]
    write_csv(OUT / "ml_validation_forecasts.csv", fields, forecast_rows)

    metric_rows: list[dict[str, object]] = []
    for name, prediction in predictions.items():
        mae, rmse, wmape = metrics(target[validation_mask], prediction)
        metric_rows.append({"level": "overall", "model": name, "observations": len(prediction),
                            "mae": f"{mae:.4f}", "rmse": f"{rmse:.4f}", "wmape": f"{wmape:.4f}"})
    write_csv(OUT / "ml_forecast_metrics.csv", ["level", "model", "observations", "mae", "rmse", "wmape"], metric_rows)

    metric_table = "\n".join(["| Model | MAE | RMSE | WMAPE |", "| --- | ---: | ---: | ---: |"] + [
        f"| {row['model']} | {float(row['mae']):,.2f} | {float(row['rmse']):,.2f} | {float(row['wmape']):.2%} |"
        for row in sorted(metric_rows, key=lambda item: float(item["wmape"]))
    ])
    DOC.write_text(f"""# Week 2, Day 8 — Machine Learning Forecasting

## Time-aware validation

The model training rows end before **{validation_start.isoformat()}**. The final **{VALIDATION_DAYS} calendar dates** ({validation_start.isoformat()} through {last_date.isoformat()}) are a held-out validation period with **{validation_mask.sum():,} SKU-date rows**. No random row split is used. The runner trains on the most recent **{len(train_indexes):,}** pre-validation rows (capped at {MAX_TRAINING_ROWS:,}) to make local execution practical.

Lag and rolling features come from `features_daily_sku.csv.gz`; they are calculated before the target date. SKU is ordinal-encoded only to identify each demand series, and missing prior-price values remain missing for tree handling.

## Models and validation results

Both available gradient-boosting regressors are trained on the same feature set with a fixed random seed. Predictions are clipped to zero because negative unit demand is not valid.

{metric_table}

## Outputs

- `data/processed/ml_validation_forecasts.csv` — held-out actual demand and each model forecast.
- `data/processed/ml_forecast_metrics.csv` — overall MAE, RMSE, and WMAPE.

## Reproducibility

```powershell
python -m pip install -r requirements.txt
python scripts/run_ml_forecasts.py
```
""", encoding="utf-8")
    best = min(metric_rows, key=lambda item: float(item["wmape"]))
    print(f"Wrote {len(forecast_rows):,} validation forecasts; best ML model: {best['model']} ({float(best['wmape']):.2%} WMAPE).")


if __name__ == "__main__":
    main()
