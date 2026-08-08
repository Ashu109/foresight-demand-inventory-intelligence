"""Verify Week 1 deliverables and generate a final checkpoint report/manifest."""

from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
DOCS = ROOT / "docs"


def csv_metadata(path: Path, compressed: bool = False) -> dict:
    opener = gzip.open if compressed else open
    with opener(path, "rt", newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        columns = next(reader)
        rows = sum(1 for _ in reader)
    return {"path": path.relative_to(ROOT).as_posix(), "rows": rows, "columns": columns, "bytes": path.stat().st_size}


def main() -> None:
    required = [
        PROCESSED / "clean_sales_transactions.csv",
        PROCESSED / "data_quality_report.json",
        PROCESSED / "eda_sku_performance.csv",
        PROCESSED / "eda_demand_time_series.csv",
        PROCESSED / "eda_demand_outliers.csv",
        PROCESSED / "ts_sku_weekly_demand.csv",
        PROCESSED / "ts_sku_diagnostics.csv",
        PROCESSED / "ts_weekly_decomposition.csv",
        PROCESSED / "features_daily_sku.csv.gz",
        PROCESSED / "feature_engineering_coverage.csv",
        PROCESSED / "baseline_holdout_forecasts.csv",
        PROCESSED / "baseline_forecast_metrics.csv",
        PROCESSED / "baseline_portfolio_forecast.svg",
    ]
    missing = [path.relative_to(ROOT).as_posix() for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required Week 1 artifacts: " + ", ".join(missing))

    quality = json.loads((PROCESSED / "data_quality_report.json").read_text(encoding="utf-8"))
    coverage = next(csv.DictReader((PROCESSED / "feature_engineering_coverage.csv").open(newline="", encoding="utf-8")))
    all_metrics = list(csv.DictReader((PROCESSED / "baseline_forecast_metrics.csv").open(newline="", encoding="utf-8")))
    metrics = sorted((row for row in all_metrics if row["level"] == "overall"), key=lambda row: float(row["wmape"]))
    best = metrics[0]
    manifest = {
        "checkpoint": "week_1_day_7",
        "status": "complete",
        "clean_dataset": csv_metadata(PROCESSED / "clean_sales_transactions.csv"),
        "feature_dataset": csv_metadata(PROCESSED / "features_daily_sku.csv.gz", compressed=True),
        "baseline_holdout": csv_metadata(PROCESSED / "baseline_holdout_forecasts.csv"),
        "quality_report": quality,
        "feature_coverage": coverage,
        "baseline_models_ranked_by_wmape": metrics,
        "assumptions": [
            "Demand is positive, non-return line quantity; cancellations and returns are excluded from forecasting demand.",
            "Exact duplicate raw lines are removed; invalid unit-price rows are rejected according to the Day 2 rules.",
            "Categories are UNMAPPED because no SKU-category master was supplied.",
            "Promotion, inventory, stockout, replenishment, and lead-time data are unavailable and are not inferred.",
            "Daily feature lags, rolling windows, and carry-forward price use only values known before the target date.",
            "Baseline evaluation is one-step-ahead over 2011-11-12 through 2011-12-09; partial boundary periods require care.",
        ],
    }
    manifest_path = PROCESSED / "week1_checkpoint_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    metric_table = "\n".join(["| Rank | Model | MAE | RMSE | WMAPE |", "| ---: | --- | ---: | ---: | ---: |"] + [
        f"| {index} | {row['model']} | {float(row['mae']):,.2f} | {float(row['rmse']):,.2f} | {float(row['wmape']):.2%} |"
        for index, row in enumerate(metrics, start=1)
    ])
    DOCS.joinpath("week1_checkpoint.md").write_text(f"""# Week 1 Checkpoint — Demand and Inventory Intelligence

## Completion status

Week 1 is complete. The cleaned sales dataset, EDA outputs, time-series diagnostics, feature-engineered dataset, baseline backtest, and reproducibility scripts are present and verified by `data/processed/week1_checkpoint_manifest.json`.

## Finalized cleaned dataset

`data/processed/clean_sales_transactions.csv` is the finalized analytical sales dataset for Week 1. It contains **{manifest['clean_dataset']['rows']:,} accepted transaction lines** and the standardized fields listed in the checkpoint manifest. The raw workbook remains unchanged.

Cleaning validation recorded **{quality['input_rows']:,}** raw rows, **{quality['exact_duplicates_removed']:,}** exact duplicates removed, **{quality['rejected_rows']:,}** rejected rows, and **{quality['return_rows']:,}** return/cancellation lines retained with flags. Returns are excluded only from demand modeling.

## Findings

- Demand covers 4,813 SKUs and is strongly long-tailed; a small set of SKUs accounts for a disproportionate share of units.
- November is the strongest recurring demand month and Thursday the strongest observed selling weekday in the Day 3 analysis.
- Demand contains material SKU-day spikes and intermittent patterns. These need promotion, bulk-order, and data-quality review before operational forecast use.
- The weekly portfolio series has lag-1 autocorrelation of 0.528, supporting temporal models, but SKU variability is substantial.
- The model-ready daily feature dataset has **{int(coverage['feature_rows']):,} rows** for **{int(coverage['eligible_skus']):,} SKUs**, after the 28-day feature warm-up.

## Initial baseline comparison

The 28-day rolling one-step-ahead holdout covers 2011-11-12 through 2011-12-09. The weekday seasonal-mean model is the current benchmark. WMAPE is high because demand is sparse and contains large spikes, so results should be monitored at both SKU and portfolio level.

{metric_table}

## Assumptions and limitations

- Demand means positive, non-return sales quantity. It does not represent fulfilled demand when a product was out of stock.
- The dataset is sales-only. It has no reliable category master, promotions, on-hand inventory, stockout flags, lead times, replenishment orders, or unit costs.
- `UNMAPPED` category values must not be interpreted as a genuine product category.
- The last source date is 2011-12-09; the final December period is incomplete.
- Feature and forecast evaluation procedures are time ordered. Random row-level train/test splitting is not valid for this dataset.

## Handoff and next steps

1. Supply SKU-category, promotion, and inventory/replenishment masters, then rerun feature generation with those joins.
2. Segment high-volume, seasonal, and intermittent SKUs; use separate forecasting approaches rather than one universal model.
3. Compare advanced models against the weekday seasonal-mean baseline with rolling-origin evaluation and WMAPE/MAE/RMSE.
4. Define inventory service-level and lead-time policies before converting forecasts into replenishment recommendations.

## Reproducibility

Run all Week 1 stages from the repository root in order:

```powershell
python -S scripts/clean_online_retail.py
python -S scripts/analyze_demand_eda.py
python -S scripts/analyze_time_series.py
python -S scripts/engineer_demand_features.py
python -S scripts/run_baseline_forecasts.py
python -S scripts/create_week1_checkpoint.py
```
""", encoding="utf-8")
    print(f"Week 1 checkpoint complete. Best baseline: {best['model']} ({float(best['wmape']):.2%} WMAPE).")


if __name__ == "__main__":
    main()
