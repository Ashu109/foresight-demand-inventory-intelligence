# Week 2, Day 9 — Deep Learning Forecasting

## Sequential, time-aware design

Each LSTM and GRU example is a **28-day** sequence of a SKU's preceding daily demand values, transformed with `log1p`; its target is the following day's demand. The models only train on windows whose targets precede **2011-11-12**. The final 28-day validation period uses **89,505 shared SKU-date rows** from Day 6, so every model in the comparison is scored on identical actuals. The remaining **207** Day 6 rows are not represented in the sequence-feature dataset and are excluded from every Day 9 metric.

For repeatable local runtime, training uses a seeded sample of **75,000** windows from **1,748,204** eligible pre-validation windows. Both models use one recurrent layer with 32 hidden units, four epochs, Adam optimization, and predictions are transformed back to units and clipped at zero.

## Comparable validation results

| Family | Model | MAE | RMSE | WMAPE |
| --- | --- | ---: | ---: | ---: |
| deep_learning | gru | 6.76 | 54.17 | 92.53% |
| deep_learning | lstm | 6.78 | 54.28 | 92.72% |
| baseline | weekday_seasonal_mean | 7.64 | 53.67 | 104.45% |
| baseline | moving_average_7 | 7.96 | 54.79 | 108.86% |
| baseline | seasonal_naive_lag_7 | 8.51 | 70.61 | 116.41% |
| baseline | naive_lag_1 | 9.45 | 72.43 | 129.32% |

## Outputs

- `data/processed/deep_learning_validation_forecasts.csv` — deep-learning and baseline forecasts on the same holdout rows.
- `data/processed/deep_learning_forecast_metrics.csv` — comparable MAE, RMSE, and WMAPE.

## Reproducibility

```powershell
python -m pip install -r requirements.txt
python scripts/run_deep_learning_forecasts.py
```
