# Week 2, Day 8 — Machine Learning Forecasting

## Time-aware validation

The model training rows end before **2011-11-12**. The final **28 calendar dates** (2011-11-12 through 2011-12-09) are a held-out validation period with **92,282 SKU-date rows**. No random row split is used. The runner trains on the most recent **250,000** pre-validation rows (capped at 250,000) to make local execution practical.

Lag and rolling features come from `features_daily_sku.csv.gz`; they are calculated before the target date. SKU is ordinal-encoded only to identify each demand series, and missing prior-price values remain missing for tree handling.

## Models and validation results

Both available gradient-boosting regressors are trained on the same feature set with a fixed random seed. Predictions are clipped to zero because negative unit demand is not valid.

| Model | MAE | RMSE | WMAPE |
| --- | ---: | ---: | ---: |
| lightgbm | 8.13 | 52.17 | 110.59% |
| xgboost | 8.42 | 52.49 | 114.53% |

## Outputs

- `data/processed/ml_validation_forecasts.csv` — held-out actual demand and each model forecast.
- `data/processed/ml_forecast_metrics.csv` — overall MAE, RMSE, and WMAPE.

## Reproducibility

```powershell
python -m pip install -r requirements.txt
python scripts/run_ml_forecasts.py
```
