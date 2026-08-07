# Week 2, Day 10 — Forecast Model Comparison

## Comparable validation population

Statistical, machine-learning, and deep-learning forecasts were inner-joined by SKU and date before scoring. This leaves **89,505 SKU-date observations** across **3,204 SKUs** on **2011-11-12 through 2011-12-09**. All results below therefore use identical actual demand values.

## Overall model ranking

| Family | Model | MAE | RMSE | WMAPE |
| --- | --- | ---: | ---: | ---: |
| deep_learning | gru | 6.76 | 54.17 | 92.53% |
| deep_learning | lstm | 6.78 | 54.28 | 92.72% |
| statistical | weekday_seasonal_mean | 7.64 | 53.67 | 104.45% |
| statistical | moving_average_7 | 7.96 | 54.79 | 108.86% |
| machine_learning | lightgbm | 8.08 | 52.51 | 110.52% |
| machine_learning | xgboost | 8.38 | 52.85 | 114.67% |
| statistical | seasonal_naive_lag_7 | 8.51 | 70.61 | 116.41% |
| statistical | naive_lag_1 | 9.45 | 72.43 | 129.32% |

The overall champion is **gru** (deep_learning) at **92.53% WMAPE**.

## SKU-level selection

`sku_forecast_accuracy.csv` contains MAE, RMSE, and WMAPE for every SKU/model pair. To test a usable model combination without selecting on the same observations it is scored on, each SKU's champion is selected using the first 14 validation days (through 2011-11-26) and evaluated on the final 14 days. SKUs without an early-period observation are excluded from this combination test. The resulting SKU-champion combination achieves **100.94% WMAPE**, **6.95 MAE**, and **68.44 RMSE** on **44,786** late-holdout observations.

SKU assignments span: deep learning 896, machine learning 245, statistical 2,058. Use the global champion where operational simplicity matters; use the SKU-champion assignment where per-SKU model governance is available. Revalidate both choices on a future holdout before production rollout.

## Outputs

- `data/processed/forecast_model_comparison.csv` — common-population overall ranking and late-holdout comparison.
- `data/processed/sku_forecast_accuracy.csv` — SKU-level accuracy by model.
- `data/processed/sku_model_champions.csv` — selected model for each SKU.
- `data/processed/sku_champion_late_holdout_forecasts.csv` — unbiased late-holdout combination forecasts.

## Reproducibility

```powershell
python scripts/compare_forecast_models.py
```
