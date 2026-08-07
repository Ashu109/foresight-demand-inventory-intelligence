# Week 1, Day 6 — Baseline Forecasting

## Backtest design

This evaluation uses the final **28 calendar days** (**2011-11-12 through 2011-12-09**) as a one-step-ahead holdout. A SKU is eligible when it has at least **30 active demand days before the holdout**, yielding **3,204 SKUs** and **89,712 SKU-day forecasts**. Demand is positive, non-return quantity.

Naive, moving-average, and seasonal-naive forecasts use only preceding actuals at each test date, consistent with rolling one-step operational forecasts. The weekday seasonal-mean model is fitted exclusively on pre-holdout history.

## Models and results

| Model | Method |
| --- | --- |
| `naive_lag_1` | Previous day's actual demand. |
| `moving_average_7` | Mean demand over the preceding seven days. |
| `seasonal_naive_lag_7` | Actual demand from the same weekday one week earlier. |
| `weekday_seasonal_mean` | Statistical seasonal baseline: pre-holdout mean demand for each weekday. |

| Model | MAE | RMSE | WMAPE |
| --- | ---: | ---: | ---: |
| weekday_seasonal_mean | 7.66 | 53.64 | 104.40% |
| moving_average_7 | 7.98 | 54.75 | 108.77% |
| seasonal_naive_lag_7 | 8.52 | 70.54 | 116.08% |
| naive_lag_1 | 9.49 | 72.37 | 129.29% |

The lowest-WMAPE baseline is **weekday_seasonal_mean** at **104.40% WMAPE**. Use it as the minimum benchmark for more advanced models; assess SKU-level results in the metrics output rather than relying only on the portfolio aggregate.

## Visual validation

The chart below aggregates the holdout across all eligible SKUs. It is also saved as `data/processed/baseline_portfolio_forecast.svg`.

![Portfolio actual demand versus forecasts](../data/processed/baseline_portfolio_forecast.svg)

## Outputs

- `data/processed/baseline_holdout_forecasts.csv` — SKU-date actuals and all four forecast values.
- `data/processed/baseline_forecast_metrics.csv` — overall and per-SKU MAE, RMSE, and WMAPE.
- `data/processed/baseline_portfolio_forecast.csv` — portfolio-level holdout series.
- `data/processed/baseline_portfolio_forecast.svg` — portfolio chart.

## Reproducibility

```powershell
python -S scripts/run_baseline_forecasts.py
```
