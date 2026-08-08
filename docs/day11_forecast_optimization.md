# Week 2, Day 11 — Forecast Optimization

## Time-series cross-validation and tuning

Four leakage-safe demand blends were tuned with **3 expanding, time-ordered folds**, each validating the next **14 calendar days**. Their hyperparameters are the weights for prior-day demand, prior-week demand, and 7-/28-day trailing averages. Every input is available before its target date. The final 28 days (**2011-11-12 through 2011-12-09**) were excluded from selection.

| Candidate | Mean MAE | Mean RMSE | Mean WMAPE |
| --- | ---: | ---: | ---: |
| smoothed_history | 7.27 | 36.16 | 113.45% |
| balanced_history | 7.35 | 37.23 | 114.58% |
| seasonal_history | 7.45 | 39.18 | 116.20% |
| recent_demand | 7.49 | 38.25 | 116.75% |

The selected configuration is **smoothed_history**. Its independent final-holdout result is **103.86% WMAPE**, **7.64 MAE**, and **52.61 RMSE**. Compare it against the Day 10 GRU champion on the common validation population before changing the production recommendation.

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
