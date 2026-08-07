"""Day 11: tune a leakage-safe demand blend with time-series CV."""

from __future__ import annotations

import csv
import gzip
import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"
FEATURES = OUT / "features_daily_sku.csv.gz"
DAY10_FORECASTS = OUT / "sku_champion_late_holdout_forecasts.csv"
DOC = ROOT / "docs" / "day11_forecast_optimization.md"
VALIDATION_DAYS, FOLDS = 14, 3
CANDIDATES = (
    ("recent_demand", (0.20, 0.35, 0.35, 0.10)),
    ("balanced_history", (0.10, 0.30, 0.30, 0.30)),
    ("seasonal_history", (0.05, 0.50, 0.20, 0.25)),
    ("smoothed_history", (0.05, 0.15, 0.30, 0.50)),
)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def scores(actual: list[float], predicted: list[float]) -> tuple[float, float, float]:
    errors = [abs(a - p) for a, p in zip(actual, predicted)]
    mae = sum(errors) / len(errors)
    rmse = math.sqrt(sum((a - p) ** 2 for a, p in zip(actual, predicted)) / len(actual))
    return mae, rmse, sum(errors) / sum(actual) if sum(actual) else 0.0


def prediction(row: dict[str, str], weights: tuple[float, float, float, float]) -> float:
    """All components are features available before this target date."""
    return max(0.0, sum(weight * float(row[column]) for weight, column in zip(
        weights, ("lag_1_demand", "lag_7_demand", "rolling_7d_avg_demand", "rolling_28d_avg_demand")
    )))


def stream_window(start: date, end: date, weights: tuple[float, float, float, float]) -> tuple[list[float], list[float]]:
    actual, predicted = [], []
    with gzip.open(FEATURES, "rt", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            current = date.fromisoformat(row["date"])
            if start <= current < end:
                actual.append(float(row["target_demand_units"]))
                predicted.append(prediction(row, weights))
    return actual, predicted


def add_error(bucket: list[float], actual: float, predicted: float) -> None:
    bucket[0] += 1
    bucket[1] += actual
    bucket[2] += abs(actual - predicted)
    bucket[3] += (actual - predicted) ** 2


def bucket_scores(bucket: list[float]) -> tuple[float, float, float]:
    return bucket[2] / bucket[0], math.sqrt(bucket[3] / bucket[0]), bucket[2] / bucket[1] if bucket[1] else 0.0


def error_analysis() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    with DAY10_FORECASTS.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            grouped[row["sku_id"]].append(row)
    sku_rows, categories = [], defaultdict(list)
    for sku_id, rows in grouped.items():
        actual = [float(row["actual_demand_units"]) for row in rows]
        forecast = [float(row["selected_forecast"]) for row in rows]
        mae, rmse, wmape = scores(actual, forecast)
        item = {"sku_id": sku_id, "description": rows[0]["description"], "category": "UNMAPPED", "selected_model": rows[0]["selected_model"],
                "observations": len(rows), "actual_units": f"{sum(actual):.4f}", "forecast_units": f"{sum(forecast):.4f}", "bias_units": f"{sum(forecast) - sum(actual):.4f}",
                "mae": f"{mae:.4f}", "rmse": f"{rmse:.4f}", "wmape": f"{wmape:.4f}"}
        sku_rows.append(item)
        categories[item["category"]].extend(rows)
    category_rows = []
    for category, rows in categories.items():
        actual = [float(row["actual_demand_units"]) for row in rows]
        forecast = [float(row["selected_forecast"]) for row in rows]
        mae, rmse, wmape = scores(actual, forecast)
        category_rows.append({"category": category, "sku_count": len({row["sku_id"] for row in rows}), "observations": len(rows), "actual_units": f"{sum(actual):.4f}", "forecast_units": f"{sum(forecast):.4f}", "bias_units": f"{sum(forecast) - sum(actual):.4f}", "mae": f"{mae:.4f}", "rmse": f"{rmse:.4f}", "wmape": f"{wmape:.4f}"})
    return sorted(sku_rows, key=lambda row: float(row["mae"]), reverse=True), category_rows


def main() -> None:
    # The final date is read once; the data remains entirely on disk while CV runs.
    last_date: date | None = None
    with gzip.open(FEATURES, "rt", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            current = date.fromisoformat(row["date"])
            last_date = current if last_date is None or current > last_date else last_date
    assert last_date
    final_start = last_date - timedelta(days=27)
    windows = [(fold, final_start - timedelta(days=VALIDATION_DAYS * (FOLDS - fold + 1)), final_start - timedelta(days=VALIDATION_DAYS * (FOLDS - fold))) for fold in range(1, FOLDS + 1)]
    buckets = {(name, fold): [0.0, 0.0, 0.0, 0.0] for name, _ in CANDIDATES for fold, _, _ in windows}
    # One pass scores every candidate/fold; no random shuffle or future rows.
    with gzip.open(FEATURES, "rt", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            current = date.fromisoformat(row["date"])
            matching = next(((fold, start, end) for fold, start, end in windows if start <= current < end), None)
            if matching:
                fold, _, _ = matching
                actual = float(row["target_demand_units"])
                for name, weights in CANDIDATES:
                    add_error(buckets[(name, fold)], actual, prediction(row, weights))
    cv_rows, summaries = [], []
    candidate_scores: dict[str, list[tuple[float, float, float]]] = defaultdict(list)
    for fold, validation_start, validation_end in windows:
        for name, _ in CANDIDATES:
            bucket = buckets[(name, fold)]
            mae, rmse, wmape = bucket_scores(bucket)
            candidate_scores[name].append((mae, rmse, wmape))
            cv_rows.append({"candidate": name, "fold": fold, "training_end_exclusive": validation_start.isoformat(), "validation_start": validation_start.isoformat(), "validation_end_exclusive": validation_end.isoformat(), "validation_rows": int(bucket[0]), "mae": f"{mae:.4f}", "rmse": f"{rmse:.4f}", "wmape": f"{wmape:.4f}"})
    for name, values in candidate_scores.items():
        summaries.append({"candidate": name, "folds": len(values), "mean_mae": f"{sum(v[0] for v in values) / len(values):.4f}", "mean_rmse": f"{sum(v[1] for v in values) / len(values):.4f}", "mean_wmape": f"{sum(v[2] for v in values) / len(values):.4f}"})
    summaries.sort(key=lambda row: (float(row["mean_wmape"]), float(row["mean_mae"])))
    best = summaries[0]
    weights = next(values for name, values in CANDIDATES if name == best["candidate"])
    forecasts = []
    final_bucket = [0.0, 0.0, 0.0, 0.0]
    with gzip.open(FEATURES, "rt", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if date.fromisoformat(row["date"]) >= final_start:
                forecast = prediction(row, weights)
                add_error(final_bucket, float(row["target_demand_units"]), forecast)
                forecasts.append({"date": row["date"], "sku_id": row["sku_id"], "description": row["description"], "category": row["category"], "actual_demand_units": row["target_demand_units"], "tuned_demand_blend": f"{forecast:.4f}"})
    final_mae, final_rmse, final_wmape = bucket_scores(final_bucket)
    sku_errors, category_errors = error_analysis()
    write_csv(OUT / "timeseries_cv_results.csv", list(cv_rows[0]), cv_rows)
    write_csv(OUT / "timeseries_cv_summary.csv", list(summaries[0]), summaries)
    write_csv(OUT / "tuned_demand_blend_validation_forecasts.csv", list(forecasts[0]), forecasts)
    write_csv(OUT / "sku_forecast_error_analysis.csv", list(sku_errors[0]), sku_errors)
    write_csv(OUT / "category_forecast_error_analysis.csv", list(category_errors[0]), category_errors)
    table = "\n".join(["| Candidate | Mean MAE | Mean RMSE | Mean WMAPE |", "| --- | ---: | ---: | ---: |"] + [f"| {row['candidate']} | {float(row['mean_mae']):.2f} | {float(row['mean_rmse']):.2f} | {float(row['mean_wmape']):.2%} |" for row in summaries])
    DOC.write_text(f"""# Week 2, Day 11 — Forecast Optimization

## Time-series cross-validation and tuning

Four leakage-safe demand blends were tuned with **{FOLDS} expanding, time-ordered folds**, each validating the next **{VALIDATION_DAYS} calendar days**. Their hyperparameters are the weights for prior-day demand, prior-week demand, and 7-/28-day trailing averages. Every input is available before its target date. The final 28 days (**{final_start} through {last_date}**) were excluded from selection.

{table}

The selected configuration is **{best['candidate']}**. Its independent final-holdout result is **{final_wmape:.2%} WMAPE**, **{final_mae:.2f} MAE**, and **{final_rmse:.2f} RMSE**. Compare it against the Day 10 GRU champion on the common validation population before changing the production recommendation.

## Error analysis

SKU diagnostics use the Day 10 selected-model forecasts on the late holdout and report actuals, forecasts, bias, MAE, RMSE, and WMAPE. The data currently assigns every product to **UNMAPPED**, so category analysis correctly produces one portfolio category; enrich product-category master data before applying category policies.

## Outputs

- `data/processed/timeseries_cv_results.csv` and `timeseries_cv_summary.csv` — fold and aggregate tuning results.
- `data/processed/tuned_demand_blend_validation_forecasts.csv` — final-holdout forecasts.
- `data/processed/sku_forecast_error_analysis.csv` and `category_forecast_error_analysis.csv` — SKU/category errors and bias.

## Reproducibility

```powershell
python -S scripts/optimize_forecasts.py
```
""", encoding="utf-8")
    print(f"Selected {best['candidate']} via {FOLDS}-fold time-series CV ({float(best['mean_wmape']):.2%} mean WMAPE); final holdout: {final_wmape:.2%} WMAPE.")


if __name__ == "__main__":
    main()
