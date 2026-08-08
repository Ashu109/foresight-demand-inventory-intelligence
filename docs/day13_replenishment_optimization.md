# Week 2, Day 13 — Replenishment Optimization

## Policy and calculations

This run uses the latest **28 days** of actual demand in the forecast-validation set. For each SKU, daily demand mean and population standard deviation are calculated from that history. The selected **95% cycle service level** maps to a normal-distribution z-score of **1.645**.

- **Safety stock** = `z × daily demand standard deviation × √supplier lead time`
- **Reorder point** = `average daily demand × supplier lead time + safety stock`
- **Inventory position** = `on hand + on order − reserved`
- **Recommended reorder quantity** = `max(0, ceil(target stock − inventory position))`, where target stock covers lead time plus the **7-day** review period.

The supplier lead time is the largest populated `lead_time_days` value per SKU (or the **7-day** fallback), a conservative choice for multi-location/supplier snapshots. Recommendations: 2,152 SKUs to reorder now; 392,208 total units proposed.

## Outputs

- `data/processed/replenishment_recommendations.csv` — SKU-level safety stock, reorder point, target stock, and purchase recommendation.
- `data/processed/replenishment_summary.csv` — reorder counts and proposed units.

## Reproducibility

```powershell
python -S scripts/optimize_replenishment.py --inventory data/raw/inventory_snapshot.csv
```
