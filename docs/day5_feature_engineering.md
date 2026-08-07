# Week 1, Day 5 — Feature Engineering

## Model-ready dataset

`data/processed/features_daily_sku.csv.gz` is a compressed, daily SKU-level training table with **1,952,558 rows** across **3,301 SKUs**. It includes SKUs with at least **30 active sales days**; **1,512** lower-history SKUs are excluded from this first daily model dataset to avoid training on insufficient history. Each SKU series begins on its first observed demand date, fills subsequent no-sale days with zero demand, and omits its first 28 days because 28-day features are not yet available.

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
