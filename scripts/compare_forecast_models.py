"""Day 10: compare statistical, ML, and deep-learning SKU forecasts.

All model families are evaluated only after an inner join on SKU/date.  This
avoids giving a model credit for an easier (or larger) validation population.
The SKU-champion combination is selected on the first 14 holdout days and
evaluated on the final 14 days, so its reported score is not an oracle result.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"
DOC = ROOT / "docs" / "day10_forecast_model_comparison.md"
INPUTS = {
    "statistical": OUT / "baseline_holdout_forecasts.csv",
    "machine_learning": OUT / "ml_validation_forecasts.csv",
    "deep_learning": OUT / "deep_learning_validation_forecasts.csv",
}
FAMILY_BY_MODEL = {
    "naive_lag_1": "statistical", "moving_average_7": "statistical",
    "seasonal_naive_lag_7": "statistical", "weekday_seasonal_mean": "statistical",
    "xgboost": "machine_learning", "lightgbm": "machine_learning",
    "lstm": "deep_learning", "gru": "deep_learning",
}


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def metric(actual: list[float], forecast: list[float]) -> tuple[float, float, float]:
    errors = [abs(a - f) for a, f in zip(actual, forecast)]
    mae = sum(errors) / len(errors)
    rmse = math.sqrt(sum((a - f) ** 2 for a, f in zip(actual, forecast)) / len(actual))
    wmape = sum(errors) / sum(actual) if sum(actual) else 0.0
    return mae, rmse, wmape


def load_forecasts(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {(row["sku_id"], row["date"]): row for row in csv.DictReader(handle)}


def choose_model(rows: list[dict[str, object]], models: list[str]) -> str:
    """Choose by WMAPE, breaking ties with MAE then stable model name."""
    scored = []
    for model in models:
        actual = [float(row["actual_demand_units"]) for row in rows]
        values = [float(row[model]) for row in rows]
        mae, _, wmape = metric(actual, values)
        scored.append((wmape, mae, model))
    return min(scored)[2]


def main() -> None:
    loaded = {family: load_forecasts(path) for family, path in INPUTS.items()}
    shared_keys = set.intersection(*(set(rows) for rows in loaded.values()))
    if not shared_keys:
        raise ValueError("Forecast inputs have no shared SKU-date records. Run Days 6, 8, and 9 first.")

    models = sorted({name for rows in loaded.values() for row in rows.values() for name in row if name in FAMILY_BY_MODEL})
    joined: list[dict[str, object]] = []
    for sku_id, current_date in sorted(shared_keys, key=lambda key: (key[1], key[0])):
        source_rows = [rows[(sku_id, current_date)] for rows in loaded.values()]
        actuals = [float(row["actual_demand_units"]) for row in source_rows]
        if max(actuals) - min(actuals) > 1e-9:
            raise ValueError(f"Actual-demand mismatch for SKU {sku_id} on {current_date}.")
        base = source_rows[0]
        record: dict[str, object] = {"date": current_date, "sku_id": sku_id, "description": base["description"], "actual_demand_units": f"{actuals[0]:.4f}"}
        for row in source_rows:
            record.update({model: row[model] for model in models if model in row})
        joined.append(record)
    if any(any(model not in row for model in models) for row in joined):
        raise ValueError("A forecast model is missing from one or more shared records.")

    dates = sorted({str(row["date"]) for row in joined})
    split_date = dates[len(dates) // 2]
    selection_rows = [row for row in joined if str(row["date"]) < split_date]
    evaluation_rows = [row for row in joined if str(row["date"]) >= split_date]
    actual = [float(row["actual_demand_units"]) for row in joined]
    overall: list[dict[str, object]] = []
    for model in models:
        mae, rmse, wmape = metric(actual, [float(row[model]) for row in joined])
        overall.append({"scope": "overall", "model_family": FAMILY_BY_MODEL[model], "model": model,
                        "observations": len(joined), "mae": f"{mae:.4f}", "rmse": f"{rmse:.4f}", "wmape": f"{wmape:.4f}"})
    overall.sort(key=lambda row: (float(row["wmape"]), float(row["mae"]), str(row["model"])))

    by_sku: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in joined:
        by_sku[str(row["sku_id"])].append(row)
    sku_metrics: list[dict[str, object]] = []
    sku_champions: list[dict[str, object]] = []
    selected_by_sku: dict[str, str] = {}
    for sku_id, sku_rows in sorted(by_sku.items()):
        for model in models:
            mae, rmse, wmape = metric([float(row["actual_demand_units"]) for row in sku_rows], [float(row[model]) for row in sku_rows])
            sku_metrics.append({"scope": "sku", "model_family": FAMILY_BY_MODEL[model], "model": model, "sku_id": sku_id,
                                "description": sku_rows[0]["description"], "observations": len(sku_rows), "mae": f"{mae:.4f}", "rmse": f"{rmse:.4f}", "wmape": f"{wmape:.4f}"})
        training_rows = [row for row in sku_rows if str(row["date"]) < split_date]
        if not training_rows:
            # This SKU begins only in the late period and cannot be selected
            # without looking at its evaluation outcomes.
            continue
        selected = choose_model(training_rows, models)
        selected_by_sku[sku_id] = selected
        sku_champions.append({"sku_id": sku_id, "description": sku_rows[0]["description"], "selected_model": selected,
                              "model_family": FAMILY_BY_MODEL[selected], "selection_observations": len(training_rows)})

    combination_evaluation_rows = [row for row in evaluation_rows if str(row["sku_id"]) in selected_by_sku]
    combination_actual = [float(row["actual_demand_units"]) for row in combination_evaluation_rows]
    combination_forecast = [float(row[selected_by_sku[str(row["sku_id"])]]) for row in combination_evaluation_rows]
    combo_mae, combo_rmse, combo_wmape = metric(combination_actual, combination_forecast)
    combo_row = {"scope": "late_holdout", "model_family": "combination", "model": "sku_champion_combination",
                "observations": len(combination_evaluation_rows), "mae": f"{combo_mae:.4f}", "rmse": f"{combo_rmse:.4f}", "wmape": f"{combo_wmape:.4f}"}
    late_model_rows = []
    for model in models:
        mae, rmse, wmape = metric(combination_actual, [float(row[model]) for row in combination_evaluation_rows])
        late_model_rows.append({"scope": "late_holdout", "model_family": FAMILY_BY_MODEL[model], "model": model,
                                "observations": len(combination_evaluation_rows), "mae": f"{mae:.4f}", "rmse": f"{rmse:.4f}", "wmape": f"{wmape:.4f}"})

    write_csv(OUT / "forecast_model_comparison.csv", list(overall[0]), overall + late_model_rows + [combo_row])
    write_csv(OUT / "sku_forecast_accuracy.csv", list(sku_metrics[0]), sku_metrics)
    write_csv(OUT / "sku_model_champions.csv", list(sku_champions[0]), sku_champions)
    forecast_fields = ["date", "sku_id", "description", "actual_demand_units", "selected_model", "selected_forecast"]
    combination_rows = [{"date": row["date"], "sku_id": row["sku_id"], "description": row["description"], "actual_demand_units": row["actual_demand_units"], "selected_model": selected_by_sku[str(row["sku_id"])], "selected_forecast": row[selected_by_sku[str(row["sku_id"])]]} for row in combination_evaluation_rows]
    write_csv(OUT / "sku_champion_late_holdout_forecasts.csv", forecast_fields, combination_rows)

    best_global = overall[0]
    family_counts = defaultdict(int)
    for row in sku_champions:
        family_counts[str(row["model_family"])] += 1
    ranking = "\n".join(["| Family | Model | MAE | RMSE | WMAPE |", "| --- | --- | ---: | ---: | ---: |"] + [f"| {row['model_family']} | {row['model']} | {float(row['mae']):,.2f} | {float(row['rmse']):,.2f} | {float(row['wmape']):.2%} |" for row in overall])
    DOC.write_text(f"""# Week 2, Day 10 — Forecast Model Comparison

## Comparable validation population

Statistical, machine-learning, and deep-learning forecasts were inner-joined by SKU and date before scoring. This leaves **{len(joined):,} SKU-date observations** across **{len(by_sku):,} SKUs** on **{dates[0]} through {dates[-1]}**. All results below therefore use identical actual demand values.

## Overall model ranking

{ranking}

The overall champion is **{best_global['model']}** ({best_global['model_family']}) at **{float(best_global['wmape']):.2%} WMAPE**.

## SKU-level selection

`sku_forecast_accuracy.csv` contains MAE, RMSE, and WMAPE for every SKU/model pair. To test a usable model combination without selecting on the same observations it is scored on, each SKU's champion is selected using the first 14 validation days (through {(datetime.fromisoformat(split_date).date()).isoformat()}) and evaluated on the final 14 days. SKUs without an early-period observation are excluded from this combination test. The resulting SKU-champion combination achieves **{combo_wmape:.2%} WMAPE**, **{combo_mae:.2f} MAE**, and **{combo_rmse:.2f} RMSE** on **{len(combination_evaluation_rows):,}** late-holdout observations.

SKU assignments span: {", ".join(f"{family.replace('_', ' ')} {count:,}" for family, count in sorted(family_counts.items()))}. Use the global champion where operational simplicity matters; use the SKU-champion assignment where per-SKU model governance is available. Revalidate both choices on a future holdout before production rollout.

## Outputs

- `data/processed/forecast_model_comparison.csv` — common-population overall ranking and late-holdout comparison.
- `data/processed/sku_forecast_accuracy.csv` — SKU-level accuracy by model.
- `data/processed/sku_model_champions.csv` — selected model for each SKU.
- `data/processed/sku_champion_late_holdout_forecasts.csv` — unbiased late-holdout combination forecasts.

## Reproducibility

```powershell
python scripts/compare_forecast_models.py
```
""", encoding="utf-8")
    print(f"Compared {len(models)} models on {len(joined):,} shared SKU-date rows. Overall champion: {best_global['model']} ({float(best_global['wmape']):.2%} WMAPE); late-holdout SKU combination: {combo_wmape:.2%} WMAPE.")


if __name__ == "__main__":
    main()
