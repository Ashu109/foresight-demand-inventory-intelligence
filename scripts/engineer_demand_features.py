"""Build leakage-safe daily SKU features for demand forecasting.

Only information known before the forecast date is used in lag, rolling, and
price features. The source has no promotion or inventory data; availability
flags make that limitation explicit rather than imputing business values.
"""

from __future__ import annotations

import csv
import gzip
import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "clean_sales_transactions.csv"
OUT = ROOT / "data" / "processed"
DOC = ROOT / "docs" / "day5_feature_engineering.md"
MIN_ACTIVE_DAYS = 30
WARMUP_DAYS = 28


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    # Aggregate demand and a unit-weighted daily sale price at SKU-date grain.
    demand = defaultdict(int)
    price_numerator = defaultdict(float)
    active_days = defaultdict(set)
    descriptions: dict[str, str] = {}
    categories: dict[str, str] = {}
    first_day_by_sku: dict[str, date] = {}
    end_day: date | None = None

    with INPUT.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            quantity = int(row["quantity"])
            if row["is_return"].lower() == "true" or quantity <= 0:
                continue
            sku_id = row["sku_id"]
            current_day = datetime.fromisoformat(row["invoice_date"]).date()
            key = (sku_id, current_day)
            demand[key] += quantity
            price_numerator[key] += float(row["unit_price"]) * quantity
            active_days[sku_id].add(current_day)
            descriptions[sku_id] = row["description"]
            categories[sku_id] = row["category"]
            first_day_by_sku[sku_id] = min(first_day_by_sku.get(sku_id, current_day), current_day)
            end_day = current_day if end_day is None or current_day > end_day else end_day

    assert end_day is not None
    eligible_skus = sorted(sku for sku, days in active_days.items() if len(days) >= MIN_ACTIVE_DAYS)
    excluded_skus = len(active_days) - len(eligible_skus)
    fields = [
        "date", "sku_id", "description", "category", "target_demand_units", "days_since_series_start",
        "lag_1_demand", "lag_7_demand", "lag_14_demand", "lag_28_demand",
        "rolling_7d_avg_demand", "rolling_28d_avg_demand",
        "last_observed_unit_price", "price_age_days",
        "day_of_week", "day_of_month", "week_of_year", "month", "quarter", "is_weekend",
        "day_of_year_sin", "day_of_year_cos", "day_of_week_sin", "day_of_week_cos",
        "promotion_data_available", "promotion_flag", "inventory_data_available", "on_hand_quantity",
    ]
    output = OUT / "features_daily_sku.csv.gz"
    row_count = 0
    with gzip.open(output, "wt", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for sku_id in eligible_skus:
            start_day = first_day_by_sku[sku_id]
            history: list[int] = []
            last_price: float | None = None
            last_price_date: date | None = None
            current_day = start_day
            while current_day <= end_day:
                key = (sku_id, current_day)
                target = demand[key]
                # The current day is written before its demand/price enter the
                # feature state, preventing target and price leakage.
                if len(history) >= WARMUP_DAYS:
                    iso = current_day.isocalendar()
                    day_of_year_angle = 2 * math.pi * current_day.timetuple().tm_yday / 365.25
                    weekday_angle = 2 * math.pi * current_day.weekday() / 7
                    writer.writerow({
                        "date": current_day.isoformat(), "sku_id": sku_id, "description": descriptions[sku_id],
                        "category": categories[sku_id], "target_demand_units": target,
                        "days_since_series_start": len(history),
                        "lag_1_demand": history[-1], "lag_7_demand": history[-7],
                        "lag_14_demand": history[-14], "lag_28_demand": history[-28],
                        "rolling_7d_avg_demand": f"{sum(history[-7:]) / 7:.4f}",
                        "rolling_28d_avg_demand": f"{sum(history[-28:]) / 28:.4f}",
                        "last_observed_unit_price": "" if last_price is None else f"{last_price:.4f}",
                        "price_age_days": "" if last_price_date is None else (current_day - last_price_date).days,
                        "day_of_week": current_day.weekday(), "day_of_month": current_day.day,
                        "week_of_year": iso.week, "month": current_day.month,
                        "quarter": (current_day.month - 1) // 3 + 1, "is_weekend": int(current_day.weekday() >= 5),
                        "day_of_year_sin": f"{math.sin(day_of_year_angle):.6f}",
                        "day_of_year_cos": f"{math.cos(day_of_year_angle):.6f}",
                        "day_of_week_sin": f"{math.sin(weekday_angle):.6f}",
                        "day_of_week_cos": f"{math.cos(weekday_angle):.6f}",
                        "promotion_data_available": 0, "promotion_flag": 0,
                        "inventory_data_available": 0, "on_hand_quantity": "",
                    })
                    row_count += 1
                history.append(target)
                if target:
                    last_price = price_numerator[key] / target
                    last_price_date = current_day
                current_day += timedelta(days=1)

    coverage = [{
        "source": INPUT.relative_to(ROOT).as_posix(), "first_sales_date": min(first_day_by_sku.values()).isoformat(),
        "last_sales_date": end_day.isoformat(), "all_skus": len(active_days), "eligible_skus": len(eligible_skus),
        "excluded_skus_below_min_active_days": excluded_skus, "min_active_sales_days": MIN_ACTIVE_DAYS,
        "warmup_days_excluded_per_sku": WARMUP_DAYS, "feature_rows": row_count,
        "promotion_data_available": "false", "inventory_data_available": "false",
    }]
    write_csv(OUT / "feature_engineering_coverage.csv", list(coverage[0]), coverage)

    DOC.write_text(f"""# Week 1, Day 5 — Feature Engineering

## Model-ready dataset

`data/processed/features_daily_sku.csv.gz` is a compressed, daily SKU-level training table with **{row_count:,} rows** across **{len(eligible_skus):,} SKUs**. It includes SKUs with at least **{MIN_ACTIVE_DAYS} active sales days**; **{excluded_skus:,}** lower-history SKUs are excluded from this first daily model dataset to avoid training on insufficient history. Each SKU series begins on its first observed demand date, fills subsequent no-sale days with zero demand, and omits its first {WARMUP_DAYS} days because 28-day features are not yet available.

The target is `target_demand_units`. Every lag, rolling average, and price feature uses information available strictly before the target date.

## Features

| Group | Features | Notes |
| --- | --- | --- |
| Lags | `lag_1_demand`, `lag_7_demand`, `lag_14_demand`, `lag_28_demand` | Daily demand; zero sales are explicit zeros. |
| Rolling demand | `rolling_7d_avg_demand`, `rolling_28d_avg_demand` | Prior days only; no target leakage. |
| Calendar | day/week/month/quarter, day of week, day of month, weekend | Suitable for tree models or encoded linear models. |
| Seasonal cycles | sine/cosine transforms for day of year and day of week | Preserves circular calendar relationships. |
| Price | `last_observed_unit_price`, `price_age_days` | Weighted sale price carried forward from prior sales only. |
| Promotion | `promotion_data_available`, `promotion_flag` | Both 0: the source has no promotion data. |
| Inventory | `inventory_data_available`, `on_hand_quantity` | Availability is 0/blank: no inventory snapshot was supplied. |

All categories remain `UNMAPPED`, so category is retained for schema compatibility but should not yet be treated as a useful model signal.

## Data limitations and next steps

- Join a dated promotion calendar on SKU and date to populate `promotion_flag` before testing promotional uplift.
- Join a daily SKU-location inventory snapshot to add on-hand, stockout, in-transit, and reorder features. Current sales-only data cannot distinguish zero demand from an unavailable item.
- Preserve the `price_age_days` feature or replace the carry-forward price with a validated price-history master when available.
- Use time-based validation splits; do not randomly split rows from this table.

## Reproducibility

```powershell
python -S scripts/engineer_demand_features.py
```

Coverage and availability metadata are in `data/processed/feature_engineering_coverage.csv`.
""", encoding="utf-8")
    print(f"Wrote {row_count:,} feature rows for {len(eligible_skus):,} eligible SKUs to {output.name}.")


if __name__ == "__main__":
    main()
