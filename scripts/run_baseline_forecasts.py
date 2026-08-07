"""Day 6: leakage-safe baseline demand forecasts and backtest artifacts.

The evaluation is a one-step-ahead rolling-origin backtest for the final 28
calendar dates. Each naive/MA/seasonal-naive forecast may use actual demand up
to the preceding date, never the target date. The weekday-mean model is fit on
the pre-holdout history only.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "clean_sales_transactions.csv"
OUT = ROOT / "data" / "processed"
DOC = ROOT / "docs" / "day6_baseline_forecasting.md"
HOLDOUT_DAYS = 28
MIN_TRAINING_ACTIVE_DAYS = 30
MODELS = ("naive_lag_1", "moving_average_7", "seasonal_naive_lag_7", "weekday_seasonal_mean")


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def metrics(actual: list[float], predicted: list[float]) -> tuple[float, float, float]:
    errors = [abs(a - p) for a, p in zip(actual, predicted)]
    mae = sum(errors) / len(errors)
    rmse = math.sqrt(sum((a - p) ** 2 for a, p in zip(actual, predicted)) / len(actual))
    wmape = sum(errors) / sum(actual) if sum(actual) else 0.0
    return mae, rmse, wmape


def svg_chart(rows: list[dict], output: Path) -> None:
    width, height, margin = 1100, 480, 65
    values = [float(row[key]) for row in rows for key in ("actual_demand_units",) + MODELS]
    maximum = max(values) * 1.1 or 1
    colors = {"actual_demand_units": "#111827", "naive_lag_1": "#2563eb", "moving_average_7": "#16a34a", "seasonal_naive_lag_7": "#ea580c", "weekday_seasonal_mean": "#9333ea"}
    labels = {"actual_demand_units": "Actual", "naive_lag_1": "Naive", "moving_average_7": "7-day MA", "seasonal_naive_lag_7": "Seasonal naive", "weekday_seasonal_mean": "Weekday mean"}
    def point(index: int, value: float) -> str:
        x = margin + index * (width - 2 * margin) / (len(rows) - 1)
        y = height - margin - value * (height - 2 * margin) / maximum
        return f"{x:.1f},{y:.1f}"
    paths = []
    for key in ("actual_demand_units",) + MODELS:
        points = " ".join(point(index, float(row[key])) for index, row in enumerate(rows))
        stroke_width = 3 if key == "actual_demand_units" else 2
        paths.append(f'<polyline fill="none" stroke="{colors[key]}" stroke-width="{stroke_width}" points="{points}"/>')
    grid = []
    for step in range(5):
        value = maximum * step / 4
        y = height - margin - value * (height - 2 * margin) / maximum
        grid.append(f'<line x1="{margin}" y1="{y:.1f}" x2="{width-margin}" y2="{y:.1f}" stroke="#e5e7eb"/>')
        grid.append(f'<text x="8" y="{y + 4:.1f}" font-size="12" fill="#374151">{value:,.0f}</text>')
    legend = "".join(f'<text x="{margin + index * 190}" y="28" font-size="13" fill="{colors[key]}">● {labels[key]}</text>' for index, key in enumerate(("actual_demand_units",) + MODELS))
    date_labels = "".join(f'<text x="{margin + index * (width - 2 * margin) / (len(rows)-1):.1f}" y="{height-28}" text-anchor="middle" font-size="11" fill="#374151">{row["date"][5:]}</text>' for index, row in enumerate(rows) if index % 4 == 0 or index == len(rows)-1)
    output.write_text(f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Actual and baseline portfolio demand forecasts">
<rect width="100%" height="100%" fill="white"/><text x="{margin}" y="52" font-size="16" font-weight="bold" fill="#111827">Portfolio demand: holdout actual vs baseline forecasts</text>{legend}{''.join(grid)}{''.join(paths)}{date_labels}</svg>''', encoding="utf-8")


def main() -> None:
    daily = defaultdict(int)
    description: dict[str, str] = {}
    active_training_days = defaultdict(set)
    first_date: date | None = None
    last_date: date | None = None
    with INPUT.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            quantity = int(row["quantity"])
            if row["is_return"].lower() == "true" or quantity <= 0:
                continue
            current_date = datetime.fromisoformat(row["invoice_date"]).date()
            sku_id = row["sku_id"]
            daily[(sku_id, current_date)] += quantity
            description[sku_id] = row["description"]
            first_date = current_date if first_date is None or current_date < first_date else first_date
            last_date = current_date if last_date is None or current_date > last_date else last_date
    assert first_date and last_date
    holdout_start = last_date - timedelta(days=HOLDOUT_DAYS - 1)
    for (sku_id, current_date), units in daily.items():
        if current_date < holdout_start and units:
            active_training_days[sku_id].add(current_date)
    eligible = sorted(sku for sku, days in active_training_days.items() if len(days) >= MIN_TRAINING_ACTIVE_DAYS)
    dates = []
    current = first_date
    while current <= last_date:
        dates.append(current)
        current += timedelta(days=1)
    test_indexes = [index for index, current_date in enumerate(dates) if current_date >= holdout_start]

    model_actual = {model: [] for model in MODELS}
    model_prediction = {model: [] for model in MODELS}
    forecast_rows = []
    sku_metric_rows = []
    portfolio = {current_date: {"actual_demand_units": 0.0, **{model: 0.0 for model in MODELS}} for current_date in dates if current_date >= holdout_start}
    for sku_id in eligible:
        values = [daily[(sku_id, current_date)] for current_date in dates]
        train_values = values[:test_indexes[0]]
        weekday_means = {}
        for weekday in range(7):
            subset = [value for value, current_date in zip(train_values, dates[:test_indexes[0]]) if current_date.weekday() == weekday]
            weekday_means[weekday] = sum(subset) / len(subset) if subset else 0.0
        per_model_actual = {model: [] for model in MODELS}
        per_model_prediction = {model: [] for model in MODELS}
        for index in test_indexes:
            actual = values[index]
            forecasts = {
                "naive_lag_1": values[index - 1],
                "moving_average_7": sum(values[index - 7:index]) / 7,
                "seasonal_naive_lag_7": values[index - 7],
                "weekday_seasonal_mean": weekday_means[dates[index].weekday()],
            }
            row = {"date": dates[index].isoformat(), "sku_id": sku_id, "description": description[sku_id], "actual_demand_units": actual}
            for model, prediction in forecasts.items():
                row[model] = f"{prediction:.4f}"
                model_actual[model].append(actual)
                model_prediction[model].append(prediction)
                per_model_actual[model].append(actual)
                per_model_prediction[model].append(prediction)
                portfolio[dates[index]][model] += prediction
            portfolio[dates[index]]["actual_demand_units"] += actual
            forecast_rows.append(row)
        for model in MODELS:
            mae, rmse, wmape = metrics(per_model_actual[model], per_model_prediction[model])
            sku_metric_rows.append({"level": "sku", "model": model, "sku_id": sku_id, "description": description[sku_id], "observations": len(test_indexes), "mae": f"{mae:.4f}", "rmse": f"{rmse:.4f}", "wmape": f"{wmape:.4f}"})
    write_csv(OUT / "baseline_holdout_forecasts.csv", ["date", "sku_id", "description", "actual_demand_units", *MODELS], forecast_rows)

    overall_rows = []
    for model in MODELS:
        mae, rmse, wmape = metrics(model_actual[model], model_prediction[model])
        overall_rows.append({"level": "overall", "model": model, "sku_id": "", "description": "", "observations": len(model_actual[model]), "mae": f"{mae:.4f}", "rmse": f"{rmse:.4f}", "wmape": f"{wmape:.4f}"})
    write_csv(OUT / "baseline_forecast_metrics.csv", list(overall_rows[0]), overall_rows + sku_metric_rows)
    portfolio_rows = [{"date": current_date.isoformat(), **{key: f"{value:.4f}" for key, value in values.items()}} for current_date, values in sorted(portfolio.items())]
    write_csv(OUT / "baseline_portfolio_forecast.csv", ["date", "actual_demand_units", *MODELS], portfolio_rows)
    svg_chart(portfolio_rows, OUT / "baseline_portfolio_forecast.svg")

    best = min(overall_rows, key=lambda row: float(row["wmape"]))
    metric_table = "\n".join(["| Model | MAE | RMSE | WMAPE |", "| --- | ---: | ---: | ---: |"] + [f"| {row['model']} | {float(row['mae']):,.2f} | {float(row['rmse']):,.2f} | {float(row['wmape']):.2%} |" for row in sorted(overall_rows, key=lambda row: float(row["wmape"]))])
    DOC.write_text(f"""# Week 1, Day 6 — Baseline Forecasting

## Backtest design

This evaluation uses the final **{HOLDOUT_DAYS} calendar days** (**{holdout_start.isoformat()} through {last_date.isoformat()}**) as a one-step-ahead holdout. A SKU is eligible when it has at least **{MIN_TRAINING_ACTIVE_DAYS} active demand days before the holdout**, yielding **{len(eligible):,} SKUs** and **{len(forecast_rows):,} SKU-day forecasts**. Demand is positive, non-return quantity.

Naive, moving-average, and seasonal-naive forecasts use only preceding actuals at each test date, consistent with rolling one-step operational forecasts. The weekday seasonal-mean model is fitted exclusively on pre-holdout history.

## Models and results

| Model | Method |
| --- | --- |
| `naive_lag_1` | Previous day's actual demand. |
| `moving_average_7` | Mean demand over the preceding seven days. |
| `seasonal_naive_lag_7` | Actual demand from the same weekday one week earlier. |
| `weekday_seasonal_mean` | Statistical seasonal baseline: pre-holdout mean demand for each weekday. |

{metric_table}

The lowest-WMAPE baseline is **{best['model']}** at **{float(best['wmape']):.2%} WMAPE**. Use it as the minimum benchmark for more advanced models; assess SKU-level results in the metrics output rather than relying only on the portfolio aggregate.

## Visual validation

The chart below aggregates the holdout across all eligible SKUs. It is also saved as `data/processed/baseline_portfolio_forecast.svg`.

![Portfolio actual demand versus forecasts](../data/processed/baseline_portfolio_forecast.svg)

## Outputs

- `data/processed/baseline_holdout_forecasts.csv` — SKU-date actuals and all four forecast values.
- `data/processed/baseline_forecast_metrics.csv` — overall and per-SKU MAE, RMSE, and WMAPE.
- `data/processed/baseline_portfolio_forecast.csv` — portfolio-level holdout series.
- `data/processed/baseline_portfolio_forecast.svg` — portfolio chart.

## Reproducibility

```powershell
python -S scripts/run_baseline_forecasts.py
```
""", encoding="utf-8")
    print(f"Wrote {len(forecast_rows):,} holdout forecasts; best WMAPE baseline: {best['model']} ({float(best['wmape']):.2%}).")


if __name__ == "__main__":
    main()
