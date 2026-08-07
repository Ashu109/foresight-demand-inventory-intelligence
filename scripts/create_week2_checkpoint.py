"""Day 14: verify Week 2 outputs and publish SKU-level operational handoff."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"
DOC = ROOT / "docs" / "week2_checkpoint.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str] | None = None) -> None:
    fieldnames = fields or (list(rows[0]) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    required = [
        OUT / "forecast_model_comparison.csv", OUT / "deep_learning_forecast_metrics.csv",
        OUT / "deep_learning_validation_forecasts.csv", OUT / "sku_model_champions.csv",
        OUT / "sku_forecast_accuracy.csv", OUT / "inventory_risk_assessment.csv",
        OUT / "replenishment_recommendations.csv",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required Week 2 artifacts: " + ", ".join(missing))

    comparison = read_csv(OUT / "forecast_model_comparison.csv")
    # Do not combine overall and late-holdout scores in one ranking: their
    # populations differ. The overall scope is the common validation basis.
    ranked = sorted((row for row in comparison if row["scope"] == "overall"), key=lambda row: float(row["wmape"]))
    if not ranked:
        raise ValueError("Forecast comparison has no overall-scope model rows")
    champion = ranked[0]
    deep_metrics = read_csv(OUT / "deep_learning_forecast_metrics.csv")
    forecasts = read_csv(OUT / "deep_learning_validation_forecasts.csv")
    required_forecast_columns = {"date", "sku_id", "description", "actual_demand_units", "gru"}
    absent = required_forecast_columns - set(forecasts[0])
    if absent:
        raise ValueError("Forecast validation output lacks columns: " + ", ".join(sorted(absent)))
    invalid_forecasts = sum(
        float(row["actual_demand_units"]) < 0 or float(row["gru"]) < 0 for row in forecasts
    )
    if invalid_forecasts:
        raise ValueError(f"Forecast validation contains {invalid_forecasts} negative demand or GRU values")

    # Use the last 14 validation dates as the current planning signal. This is
    # explicitly a forecast-derived priority, not a substitute for stock data.
    latest_dates = sorted({row["date"] for row in forecasts})[-14:]
    latest = set(latest_dates)
    profiles: dict[str, dict[str, object]] = defaultdict(lambda: {"values": [], "description": "UNKNOWN"})
    for row in forecasts:
        if row["date"] in latest:
            profile = profiles[row["sku_id"].strip().upper()]
            profile["values"].append(float(row["gru"]))
            profile["description"] = row["description"]

    replenishment = {row["sku_id"].strip().upper(): row for row in read_csv(OUT / "replenishment_recommendations.csv") if row.get("sku_id")}
    # A successful Day 13 run produces one recommendation row per snapshot SKU.
    # Its older gap report may remain on disk, so artifact existence alone is not
    # evidence that the current replenishment run is blocked.
    inventory_gap = not replenishment
    recommendations = []
    for sku, profile in sorted(profiles.items()):
        reorder = replenishment.get(sku)
        average_forecast = sum(profile["values"]) / len(profile["values"])
        base = {
            "sku_id": sku, "description": profile["description"],
            "avg_daily_gru_forecast_units": f"{average_forecast:.4f}",
            "forecast_window_start": latest_dates[0], "forecast_window_end": latest_dates[-1],
        }
        if reorder:
            base.update({
                "recommendation_status": reorder["recommendation_status"],
                "recommended_reorder_quantity": reorder["recommended_reorder_quantity"],
                "safety_stock_units": reorder["safety_stock_units"],
                "reorder_point_units": reorder["reorder_point_units"],
                "supplier_lead_time_days": reorder["supplier_lead_time_days"],
                "recommendation_note": "Inventory-position-based recommendation from Day 13.",
            })
        else:
            base.update({
                "recommendation_status": "inventory_data_required",
                "recommended_reorder_quantity": "", "safety_stock_units": "", "reorder_point_units": "",
                "supplier_lead_time_days": "",
                "recommendation_note": "Supply on-hand, open-order, reserved, and supplier lead-time data before ordering.",
            })
        recommendations.append(base)
    fields = ["sku_id", "description", "avg_daily_gru_forecast_units", "forecast_window_start", "forecast_window_end", "recommendation_status", "recommended_reorder_quantity", "safety_stock_units", "reorder_point_units", "supplier_lead_time_days", "recommendation_note"]
    write_csv(OUT / "week2_sku_recommendations.csv", recommendations, fields)
    counts = Counter(row["recommendation_status"] for row in recommendations)
    summary = [{"recommendation_status": key, "sku_count": value} for key, value in sorted(counts.items())]
    write_csv(OUT / "week2_recommendation_summary.csv", summary, ["recommendation_status", "sku_count"])

    manifest = {
        "checkpoint": "week_2_day_14",
        "status": "complete_with_inventory_data_gap" if inventory_gap else "complete",
        "forecasting_pipeline": {"status": "complete", "validation_rows": len(forecasts), "sku_champions": len(read_csv(OUT / "sku_model_champions.csv"))},
        "forecast_accuracy": {"status": "validated", "selection_metric": "wmape", "best_model": champion, "models_compared": ranked, "negative_value_violations": invalid_forecasts},
        "inventory_optimization_engine": {"status": "awaiting_inventory_snapshot" if inventory_gap else "complete", "method": "safety stock + reorder point + lead-time review target"},
        "sku_recommendations": {"path": "data/processed/week2_sku_recommendations.csv", "sku_count": len(recommendations), "status_counts": dict(counts)},
    }
    (OUT / "week2_checkpoint_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    accuracy_rows = "\n".join(
        f"| {i} | {row['model']} | {float(row['mae']):,.2f} | {float(row['rmse']):,.2f} | {float(row['wmape']):.2%} |"
        for i, row in enumerate(ranked, 1)
    )
    inventory_status = "The replenishment engine is complete, but ordering remains blocked until an inventory snapshot is supplied." if inventory_gap else "Inventory-position-based reorder recommendations are available."
    DOC.write_text(f"""# Week 2 Checkpoint — Forecasting and Replenishment

## Completion status

The demand forecasting pipeline and its holdout validation are complete. {inventory_status} The SKU handoff contains **{len(recommendations):,}** forecasted SKUs.

## Forecast accuracy validation

Forecast validation contains **{len(forecasts):,}** SKU-date observations with no negative actual-demand or GRU forecast values. Models are ranked by WMAPE on the shared holdout; the current portfolio champion is **{champion['model']}** at **{float(champion['wmape']):.2%} WMAPE**, **{float(champion['mae']):.2f} MAE**, and **{float(champion['rmse']):.2f} RMSE**.

| Rank | Model | MAE | RMSE | WMAPE |
| ---: | --- | ---: | ---: | ---: |
{accuracy_rows}

## Inventory and SKU recommendations

Day 13 calculates safety stock as `z × daily demand standard deviation × √lead time`, then adds it to lead-time demand for the reorder point. Recommended quantity fills target stock for lead time plus the review period after subtracting inventory position (`on hand + on order − reserved`).

Current recommendation statuses: {", ".join(f"{status}: {count:,}" for status, count in sorted(counts.items()))}. When supply data is missing, a SKU is deliberately marked `inventory_data_required`; its forecast is useful for prioritization but must not be converted into a purchase order.

## Outputs

- `data/processed/week2_checkpoint_manifest.json` — verified completion status and forecast metrics.
- `data/processed/week2_sku_recommendations.csv` — SKU-level forecast and replenishment handoff.
- `data/processed/week2_recommendation_summary.csv` — counts by recommendation status.

## Reproducibility

```powershell
python -S scripts/create_week2_checkpoint.py
```
""", encoding="utf-8")
    print(f"Week 2 checkpoint complete. Champion: {champion['model']} ({float(champion['wmape']):.2%} WMAPE).")


if __name__ == "__main__":
    main()
