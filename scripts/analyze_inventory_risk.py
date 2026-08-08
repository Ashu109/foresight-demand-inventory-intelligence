"""Day 12: inventory risk intelligence from an on-hand inventory snapshot.

The sales source contains no inventory ledger. This runner therefore produces
no invented stock positions: without a snapshot it writes a data-gap report;
with one it combines on-hand supply with the GRU demand forecast.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"
DEFAULT_SNAPSHOT = ROOT / "data" / "raw" / "inventory_snapshot.csv"
FORECAST = OUT / "deep_learning_validation_forecasts.csv"
DOC = ROOT / "docs" / "day12_inventory_risk_intelligence.md"
REQUIRED = {"date", "sku_id", "location_id", "on_hand_quantity", "inventory_value"}


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_forecast(horizon_days: int) -> dict[str, tuple[str, float]]:
    """Return SKU descriptions and recent average daily GRU forecasts."""
    rows = list(csv.DictReader(FORECAST.open(newline="", encoding="utf-8")))
    dates = sorted({row["date"] for row in rows})[-horizon_days:]
    dates_set = set(dates)
    values: dict[str, list[float]] = defaultdict(list)
    descriptions: dict[str, str] = {}
    for row in rows:
        if row["date"] in dates_set:
            values[row["sku_id"]].append(float(row["gru"]))
            descriptions[row["sku_id"]] = row["description"]
    return {sku: (descriptions[sku], sum(series) / len(series)) for sku, series in values.items()}


def risk_level(days_supply: float | None, supply: float, daily_forecast: float, lead_time: int, excess_days: int, slow_threshold: float) -> tuple[str, str]:
    if supply <= 0 and daily_forecast > 0:
        return "critical", "no_supply_with_forecast_demand"
    if daily_forecast <= slow_threshold and supply > 0:
        return "slow_moving", "very_low_forecast_demand"
    if days_supply is None:
        return "low", "no_forecast_demand"
    if days_supply <= lead_time:
        return "critical", "supply_within_lead_time"
    if days_supply <= lead_time + 7:
        return "high", "supply_below_lead_time_plus_week"
    if days_supply > excess_days:
        return "excess", "supply_above_excess_threshold"
    if days_supply <= 28:
        return "medium", "supply_below_28_days"
    return "low", "adequate_supply"


def data_gap_report(snapshot: Path) -> None:
    rows = [{"status": "blocked", "reason": "inventory_snapshot_missing_or_empty", "expected_path": str(snapshot.relative_to(ROOT)), "required_columns": ";".join(sorted(REQUIRED)), "action": "Populate the snapshot template or export a dated SKU-location inventory snapshot from ERP/WMS, validate it, then rerun this script."}]
    write_csv(OUT / "inventory_risk_data_gap.csv", list(rows[0]), rows)
    # Preserve a SKU-level output even when inventory is unavailable. Forecast
    # demand remains useful for collecting the missing stock snapshot, but all
    # supply-dependent measures are deliberately left blank.
    forecast = load_forecast(14)
    assessment = [{"snapshot_date": "", "sku_id": sku, "description": description, "category": "UNMAPPED", "location_count": "",
                   "on_hand_quantity": "", "on_order_quantity": "", "reserved_quantity": "", "available_supply_quantity": "", "inventory_value": "",
                   "avg_daily_forecast_units": f"{daily:.4f}", "lead_time_days": "", "reorder_point_units": "", "days_of_supply": "",
                   "potential_stockout": "", "excess_inventory": "", "slow_moving": "", "risk_level": "data_unavailable", "risk_reason": "inventory_snapshot_missing_or_empty"}
                  for sku, (description, daily) in sorted(forecast.items())]
    fields = list(assessment[0]) if assessment else ["sku_id", "risk_level"]
    write_csv(OUT / "inventory_risk_assessment.csv", fields, assessment)
    write_csv(OUT / "inventory_risk_summary.csv", ["risk_level", "sku_count"], [{"risk_level": "data_unavailable", "sku_count": len(assessment)}])
    DOC.write_text(f"""# Week 2, Day 12 — Inventory Risk Intelligence

## Current status: inventory data required

The transactional source has demand history but no on-hand inventory, open purchase orders, reserved stock, supplier lead time, or category master. No stockout, excess, or days-of-supply values are inferred from sales alone.

`data/processed/inventory_risk_data_gap.csv` records the current block. `inventory_risk_assessment.csv` is still produced for every forecasted SKU, but its supply fields and risk flags are blank and its risk level is `data_unavailable`. Supply a CSV at `{snapshot.relative_to(ROOT).as_posix()}` (or pass `--inventory`) with at least:

`date, sku_id, location_id, on_hand_quantity, inventory_value`

Optional columns: `on_order_quantity`, `reserved_quantity`, `lead_time_days`, and `category`. After validating it with Day 2, rerun:

```powershell
python -S scripts/analyze_inventory_risk.py --inventory path/to/inventory_snapshot.csv
```

The runner will calculate available supply, forecast daily demand, days of supply, potential stockouts, excess/slow-moving flags, and SKU risk levels.
""", encoding="utf-8")
    print(f"Inventory risk analysis blocked: no usable snapshot found at {snapshot}.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, default=DEFAULT_SNAPSHOT, help="CSV inventory snapshot")
    parser.add_argument("--horizon-days", type=int, default=14, help="Recent forecast days used for average daily demand")
    parser.add_argument("--lead-time-days", type=int, default=7, help="Fallback replenishment lead time")
    parser.add_argument("--excess-days", type=int, default=56, help="Days of supply classed as excess")
    parser.add_argument("--slow-demand-threshold", type=float, default=0.10, help="Units/day at or below which stocked SKUs are slow moving")
    args = parser.parse_args()
    if not args.inventory.exists():
        data_gap_report(args.inventory)
        return
    with args.inventory.open(newline="", encoding="utf-8-sig") as handle:
        snapshot_rows = list(csv.DictReader(handle))
    if not snapshot_rows:
        data_gap_report(args.inventory)
        return
    headers = set(snapshot_rows[0]) if snapshot_rows else set()
    missing = REQUIRED - headers
    if missing:
        raise ValueError(f"Inventory snapshot is missing required columns: {', '.join(sorted(missing))}")
    forecast = load_forecast(args.horizon_days)
    inventory: dict[str, dict[str, object]] = defaultdict(lambda: {"on_hand": 0.0, "on_order": 0.0, "reserved": 0.0, "value": 0.0, "locations": set(), "lead_times": [], "categories": set(), "snapshot_dates": set()})
    for row in snapshot_rows:
        sku = row["sku_id"].strip().upper()
        record = inventory[sku]
        record["on_hand"] += float(row["on_hand_quantity"])
        record["on_order"] += float(row.get("on_order_quantity") or 0)
        record["reserved"] += float(row.get("reserved_quantity") or 0)
        record["value"] += float(row["inventory_value"])
        record["locations"].add(row["location_id"].strip().upper())
        record["snapshot_dates"].add(row["date"])
        if row.get("lead_time_days"):
            record["lead_times"].append(float(row["lead_time_days"]))
        if row.get("category"):
            record["categories"].add(row["category"])
    results = []
    for sku, record in sorted(inventory.items()):
        description, daily = forecast.get(sku, ("UNKNOWN", 0.0))
        lead_time = math.ceil(max(record["lead_times"], default=args.lead_time_days))
        supply = float(record["on_hand"]) + float(record["on_order"]) - float(record["reserved"])
        days_supply = supply / daily if daily > 0 else None
        reorder_point = daily * lead_time
        level, reason = risk_level(days_supply, supply, daily, lead_time, args.excess_days, args.slow_demand_threshold)
        results.append({"snapshot_date": max(record["snapshot_dates"]), "sku_id": sku, "description": description, "category": ";".join(sorted(record["categories"])) or "UNMAPPED", "location_count": len(record["locations"]), "on_hand_quantity": f"{record['on_hand']:.4f}", "on_order_quantity": f"{record['on_order']:.4f}", "reserved_quantity": f"{record['reserved']:.4f}", "available_supply_quantity": f"{supply:.4f}", "inventory_value": f"{record['value']:.2f}", "avg_daily_forecast_units": f"{daily:.4f}", "lead_time_days": lead_time, "reorder_point_units": f"{reorder_point:.4f}", "days_of_supply": "" if days_supply is None else f"{days_supply:.2f}", "potential_stockout": str(level in {"critical", "high"}).lower(), "excess_inventory": str(level == "excess").lower(), "slow_moving": str(level == "slow_moving").lower(), "risk_level": level, "risk_reason": reason})
    write_csv(OUT / "inventory_risk_assessment.csv", list(results[0]) if results else ["sku_id"], results)
    counts: dict[str, int] = defaultdict(int)
    for row in results:
        counts[str(row["risk_level"])] += 1
    summary = [{"risk_level": level, "sku_count": count} for level, count in sorted(counts.items())]
    write_csv(OUT / "inventory_risk_summary.csv", ["risk_level", "sku_count"], summary)
    DOC.write_text(f"""# Week 2, Day 12 — Inventory Risk Intelligence

## Snapshot-based risk assessment

The assessment joins the supplied inventory snapshot to the recent **{args.horizon_days}-day average GRU forecast**. Available supply is `on hand + on order - reserved`; days of supply is available supply divided by forecast daily demand. The fallback lead time is **{args.lead_time_days} days** and excess is over **{args.excess_days} days** of supply.

Potential stockout = critical or high risk. Slow-moving means stocked supply with forecast demand at or below **{args.slow_demand_threshold} units/day**. Risk counts: {", ".join(f"{level} {count}" for level, count in sorted(counts.items())) or "no snapshot rows"}.

## Outputs

- `data/processed/inventory_risk_assessment.csv` — SKU supply, days of supply, risk flags, and classification.
- `data/processed/inventory_risk_summary.csv` — counts by risk level.

## Reproducibility

```powershell
python -S scripts/analyze_inventory_risk.py --inventory path/to/inventory_snapshot.csv
```
""", encoding="utf-8")
    print(f"Wrote inventory risk assessment for {len(results):,} SKUs.")


if __name__ == "__main__":
    main()
