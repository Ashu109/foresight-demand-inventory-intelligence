"""Day 13: calculate safety stock, reorder points, and replenishment actions.

This script deliberately needs an inventory snapshot.  Forecast demand alone
cannot determine a purchase quantity, so no stock position is inferred when a
snapshot has not been supplied.
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path
from statistics import NormalDist, pstdev


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"
FORECAST = OUT / "deep_learning_validation_forecasts.csv"
DEFAULT_SNAPSHOT = ROOT / "data" / "raw" / "inventory_snapshot.csv"
DOC = ROOT / "docs" / "day13_replenishment_optimization.md"
REQUIRED = {"date", "sku_id", "location_id", "on_hand_quantity", "inventory_value"}


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def display_path(path: Path) -> str:
    """Show a project-relative path when possible, including relative inputs."""
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(path)


def demand_profile(horizon_days: int) -> dict[str, tuple[str, float, float]]:
    """Return description, average daily demand, and daily demand deviation."""
    with FORECAST.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    dates = set(sorted({row["date"] for row in rows})[-horizon_days:])
    values: dict[str, list[float]] = defaultdict(list)
    descriptions: dict[str, str] = {}
    for row in rows:
        if row["date"] in dates:
            sku = row["sku_id"].strip().upper()
            values[sku].append(max(0.0, float(row["actual_demand_units"])))
            descriptions[sku] = row["description"]
    return {
        sku: (descriptions[sku], sum(series) / len(series), pstdev(series) if len(series) > 1 else 0.0)
        for sku, series in values.items()
    }


def write_gap(snapshot: Path) -> None:
    row = {
        "status": "blocked",
        "reason": "inventory_snapshot_missing_or_empty",
        "expected_path": display_path(snapshot),
        "required_columns": ";".join(sorted(REQUIRED)),
        "action": "Populate data/raw/inventory_snapshot.csv from ERP/WMS, including supplier lead_time_days when available, then rerun Day 13.",
    }
    write_csv(OUT / "replenishment_data_gap.csv", list(row), [row])
    write_csv(OUT / "replenishment_recommendations.csv", ["sku_id", "recommendation_status"], [])
    DOC.write_text("""# Week 2, Day 13 — Replenishment Optimization

## Current status: inventory data required

Demand history can estimate a reorder point, but it cannot create a recommended purchase quantity without on-hand, open-order, and reserved inventory. Populate `data/raw/inventory_snapshot.csv` using the supplied template, then run the command below.

Supplier lead time is read from `lead_time_days` on each snapshot row. Add a `supplier_id` column if useful for traceability; the longest supplied lead time per SKU is used when multiple locations or suppliers are present, providing a conservative planning assumption.

```powershell
python -S scripts/optimize_replenishment.py --inventory data/raw/inventory_snapshot.csv
```
""", encoding="utf-8")
    print(f"Replenishment optimization blocked: no usable snapshot found at {snapshot}.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, default=DEFAULT_SNAPSHOT, help="CSV inventory snapshot")
    parser.add_argument("--demand-history-days", type=int, default=28, help="Recent actual-demand days for average and variability")
    parser.add_argument("--lead-time-days", type=int, default=7, help="Fallback supplier lead time")
    parser.add_argument("--service-level", type=float, default=0.95, help="Target cycle service level, exclusive of 0 and 1")
    parser.add_argument("--review-period-days", type=int, default=7, help="Days of demand covered above the reorder point")
    args = parser.parse_args()
    if not 0 < args.service_level < 1:
        raise ValueError("--service-level must be greater than 0 and less than 1")
    if not args.inventory.exists():
        write_gap(args.inventory)
        return
    with args.inventory.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        write_gap(args.inventory)
        return
    missing = REQUIRED - set(rows[0])
    if missing:
        raise ValueError(f"Inventory snapshot is missing required columns: {', '.join(sorted(missing))}")

    profile = demand_profile(args.demand_history_days)
    inventory: dict[str, dict[str, object]] = defaultdict(lambda: {"on_hand": 0.0, "on_order": 0.0, "reserved": 0.0, "locations": set(), "suppliers": set(), "lead_times": [], "dates": set()})
    for row in rows:
        sku = row["sku_id"].strip().upper()
        item = inventory[sku]
        item["on_hand"] += float(row["on_hand_quantity"])
        item["on_order"] += float(row.get("on_order_quantity") or 0)
        item["reserved"] += float(row.get("reserved_quantity") or 0)
        item["locations"].add(row["location_id"].strip().upper())
        item["dates"].add(row["date"])
        if row.get("supplier_id"):
            item["suppliers"].add(row["supplier_id"].strip())
        if row.get("lead_time_days"):
            item["lead_times"].append(float(row["lead_time_days"]))

    z_score = NormalDist().inv_cdf(args.service_level)
    results = []
    for sku, item in sorted(inventory.items()):
        description, average, deviation = profile.get(sku, ("UNKNOWN", 0.0, 0.0))
        lead_time = math.ceil(max(item["lead_times"], default=args.lead_time_days))
        inventory_position = float(item["on_hand"]) + float(item["on_order"]) - float(item["reserved"])
        # Safety stock protects the stated service level against daily demand
        # variation during the supplier lead time (independent daily demand).
        safety_stock = z_score * deviation * math.sqrt(lead_time)
        reorder_point = average * lead_time + safety_stock
        target_stock = average * (lead_time + args.review_period_days) + safety_stock
        reorder_triggered = inventory_position <= reorder_point
        # The target-stock quantity is an order-up-to recommendation only once
        # the continuous-review reorder point has been crossed.
        recommended = max(0, math.ceil(target_stock - inventory_position)) if reorder_triggered else 0
        status = "reorder_now" if reorder_triggered and recommended else "no_order_required"
        results.append({
            "snapshot_date": max(item["dates"]), "sku_id": sku, "description": description,
            "location_count": len(item["locations"]), "supplier_ids": ";".join(sorted(item["suppliers"])) or "UNSPECIFIED",
            "on_hand_quantity": f"{item['on_hand']:.4f}", "on_order_quantity": f"{item['on_order']:.4f}",
            "reserved_quantity": f"{item['reserved']:.4f}", "inventory_position_units": f"{inventory_position:.4f}",
            "avg_daily_demand_units": f"{average:.4f}", "daily_demand_stddev_units": f"{deviation:.4f}",
            "supplier_lead_time_days": lead_time, "service_level": f"{args.service_level:.2%}", "z_score": f"{z_score:.4f}",
            "safety_stock_units": f"{safety_stock:.4f}", "reorder_point_units": f"{reorder_point:.4f}",
            "target_stock_units": f"{target_stock:.4f}", "review_period_days": args.review_period_days,
            "recommended_reorder_quantity": recommended, "recommendation_status": status,
        })
    fields = list(results[0]) if results else ["sku_id", "recommendation_status"]
    write_csv(OUT / "replenishment_recommendations.csv", fields, results)
    summary = [{"recommendation_status": status, "sku_count": sum(row["recommendation_status"] == status for row in results), "recommended_units": sum(int(row["recommended_reorder_quantity"]) for row in results if row["recommendation_status"] == status)} for status in ("reorder_now", "no_order_required")]
    write_csv(OUT / "replenishment_summary.csv", list(summary[0]), summary)
    DOC.write_text(f"""# Week 2, Day 13 — Replenishment Optimization

## Policy and calculations

This run uses the latest **{args.demand_history_days} days** of actual demand in the forecast-validation set. For each SKU, daily demand mean and population standard deviation are calculated from that history. The selected **{args.service_level:.0%} cycle service level** maps to a normal-distribution z-score of **{z_score:.3f}**.

- **Safety stock** = `z × daily demand standard deviation × √supplier lead time`
- **Reorder point** = `average daily demand × supplier lead time + safety stock`
- **Inventory position** = `on hand + on order − reserved`
- **Recommended reorder quantity** = `max(0, ceil(target stock − inventory position))`, where target stock covers lead time plus the **{args.review_period_days}-day** review period.

The supplier lead time is the largest populated `lead_time_days` value per SKU (or the **{args.lead_time_days}-day** fallback), a conservative choice for multi-location/supplier snapshots. Recommendations: {sum(row['recommendation_status'] == 'reorder_now' for row in results):,} SKUs to reorder now; {sum(int(row['recommended_reorder_quantity']) for row in results):,} total units proposed.

## Outputs

- `data/processed/replenishment_recommendations.csv` — SKU-level safety stock, reorder point, target stock, and purchase recommendation.
- `data/processed/replenishment_summary.csv` — reorder counts and proposed units.

## Reproducibility

```powershell
python -S scripts/optimize_replenishment.py --inventory data/raw/inventory_snapshot.csv
```
""", encoding="utf-8")
    print(f"Wrote replenishment recommendations for {len(results):,} SKUs.")


if __name__ == "__main__":
    main()
