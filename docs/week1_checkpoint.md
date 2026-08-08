# Week 1 Checkpoint — Demand and Inventory Intelligence

## Completion status

Week 1 is complete. The cleaned sales dataset, EDA outputs, time-series diagnostics, feature-engineered dataset, baseline backtest, and reproducibility scripts are present and verified by `data/processed/week1_checkpoint_manifest.json`.

## Finalized cleaned dataset

`data/processed/clean_sales_transactions.csv` is the finalized analytical sales dataset for Week 1. It contains **1,033,031 accepted transaction lines** and the standardized fields listed in the checkpoint manifest. The raw workbook remains unchanged.

Cleaning validation recorded **1,067,371** raw rows, **34,335** exact duplicates removed, **5** rejected rows, and **22,497** return/cancellation lines retained with flags. Returns are excluded only from demand modeling.

## Findings

- Demand covers 4,813 SKUs and is strongly long-tailed; a small set of SKUs accounts for a disproportionate share of units.
- November is the strongest recurring demand month and Thursday the strongest observed selling weekday in the Day 3 analysis.
- Demand contains material SKU-day spikes and intermittent patterns. These need promotion, bulk-order, and data-quality review before operational forecast use.
- The weekly portfolio series has lag-1 autocorrelation of 0.528, supporting temporal models, but SKU variability is substantial.
- The model-ready daily feature dataset has **1,952,558 rows** for **3,301 SKUs**, after the 28-day feature warm-up.

## Initial baseline comparison

The 28-day rolling one-step-ahead holdout covers 2011-11-12 through 2011-12-09. The weekday seasonal-mean model is the current benchmark. WMAPE is high because demand is sparse and contains large spikes, so results should be monitored at both SKU and portfolio level.

| Rank | Model | MAE | RMSE | WMAPE |
| ---: | --- | ---: | ---: | ---: |
| 1 | weekday_seasonal_mean | 7.66 | 53.64 | 104.40% |
| 2 | moving_average_7 | 7.98 | 54.75 | 108.77% |
| 3 | seasonal_naive_lag_7 | 8.52 | 70.54 | 116.08% |
| 4 | naive_lag_1 | 9.49 | 72.37 | 129.29% |

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
