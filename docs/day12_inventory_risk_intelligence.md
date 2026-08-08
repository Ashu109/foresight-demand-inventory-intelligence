# Week 2, Day 12 — Inventory Risk Intelligence

## Current status: inventory data required

The transactional source has demand history but no on-hand inventory, open purchase orders, reserved stock, supplier lead time, or category master. No stockout, excess, or days-of-supply values are inferred from sales alone.

`data/processed/inventory_risk_data_gap.csv` records the current block. `inventory_risk_assessment.csv` is still produced for every forecasted SKU, but its supply fields and risk flags are blank and its risk level is `data_unavailable`. Supply a CSV at `data/raw/inventory_snapshot.csv` (or pass `--inventory`) with at least:

`date, sku_id, location_id, on_hand_quantity, inventory_value`

Optional columns: `on_order_quantity`, `reserved_quantity`, `lead_time_days`, and `category`. After validating it with Day 2, rerun:

```powershell
python -S scripts/analyze_inventory_risk.py --inventory path/to/inventory_snapshot.csv
```

The runner will calculate available supply, forecast daily demand, days of supply, potential stockouts, excess/slow-moving flags, and SKU risk levels.
