# Week 2 Checkpoint — Forecasting and Replenishment

## Completion status

The demand forecasting pipeline and its holdout validation are complete. Inventory-position-based reorder recommendations are available. The SKU handoff contains **3,204** forecasted SKUs.

## Forecast accuracy validation

Forecast validation contains **89,505** SKU-date observations with no negative actual-demand or GRU forecast values. Models are ranked by WMAPE on the shared holdout; the current portfolio champion is **gru** at **92.53% WMAPE**, **6.76 MAE**, and **54.17 RMSE**.

| Rank | Model | MAE | RMSE | WMAPE |
| ---: | --- | ---: | ---: | ---: |
| 1 | gru | 6.76 | 54.17 | 92.53% |
| 2 | lstm | 6.78 | 54.28 | 92.72% |
| 3 | weekday_seasonal_mean | 7.64 | 53.67 | 104.45% |
| 4 | moving_average_7 | 7.96 | 54.79 | 108.86% |
| 5 | lightgbm | 8.08 | 52.51 | 110.52% |
| 6 | xgboost | 8.38 | 52.85 | 114.67% |
| 7 | seasonal_naive_lag_7 | 8.51 | 70.61 | 116.41% |
| 8 | naive_lag_1 | 9.45 | 72.43 | 129.32% |

## Inventory and SKU recommendations

Day 13 calculates safety stock as `z × daily demand standard deviation × √lead time`, then adds it to lead-time demand for the reorder point. Recommended quantity fills target stock for lead time plus the review period after subtracting inventory position (`on hand + on order − reserved`).

Current recommendation statuses: no_order_required: 1,052, reorder_now: 2,152. When supply data is missing, a SKU is deliberately marked `inventory_data_required`; its forecast is useful for prioritization but must not be converted into a purchase order.

## Outputs

- `data/processed/week2_checkpoint_manifest.json` — verified completion status and forecast metrics.
- `data/processed/week2_sku_recommendations.csv` — SKU-level forecast and replenishment handoff.
- `data/processed/week2_recommendation_summary.csv` — counts by recommendation status.

## Reproducibility

```powershell
python -S scripts/create_week2_checkpoint.py
```
