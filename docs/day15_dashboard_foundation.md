# Week 3, Day 15 — Dashboard Foundation

## Delivered application

The Streamlit dashboard has three pages:

- **Executive overview** — portfolio KPIs, selected forecast model, reorder volume, and top replenishment actions.
- **Forecast accuracy** — common-holdout model ranking by WMAPE, MAE, and RMSE.
- **Replenishment actions** — searchable SKU queue with inventory position, safety stock, reorder point, lead time, and suggested units.

The application reads only processed project outputs. It does not recalculate forecasts or change source data. The sidebar includes an explicit warning whenever `data/raw/inventory_snapshot.csv` contains the generated `synthetic_demo` data source.

## Run locally

```powershell
streamlit run app.py
```

Before launching, refresh the operational outputs if inputs have changed:

```powershell
python -S scripts/optimize_replenishment.py --inventory data/raw/inventory_snapshot.csv
python -S scripts/create_week2_checkpoint.py
```

## Data connections

- `data/processed/week2_checkpoint_manifest.json` — portfolio forecast champion and validation status.
- `data/processed/forecast_model_comparison.csv` — model-comparison table.
- `data/processed/replenishment_recommendations.csv` — SKU-level replenishment actions.
- `data/processed/week2_sku_recommendations.csv` — consolidated forecast and recommendation handoff.

Replace simulated inventory with an ERP/WMS export before treating dashboard orders as operational purchase decisions.
