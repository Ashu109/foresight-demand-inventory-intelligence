"""Day 9: LSTM and GRU demand forecasts with time-ordered sequence windows."""

from __future__ import annotations

import csv
import gzip
import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
FEATURES_INPUT = ROOT / "data" / "processed" / "features_daily_sku.csv.gz"
BASELINE_INPUT = ROOT / "data" / "processed" / "baseline_holdout_forecasts.csv"
OUT = ROOT / "data" / "processed"
DOC = ROOT / "docs" / "day9_deep_learning_forecasting.md"
WINDOW_DAYS = 28
VALIDATION_DAYS = 28
MAX_TRAINING_WINDOWS = 75_000
EPOCHS = 4
BATCH_SIZE = 1_024
SEED = 42


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def metrics(actual: np.ndarray, predicted: np.ndarray) -> tuple[float, float, float]:
    errors = np.abs(actual - predicted)
    return (
        float(errors.mean()),
        float(np.sqrt(np.mean((actual - predicted) ** 2))),
        float(errors.sum() / actual.sum()) if actual.sum() else 0.0,
    )


def load_baseline_rows() -> tuple[dict[tuple[str, str], dict[str, str]], date]:
    rows: dict[tuple[str, str], dict[str, str]] = {}
    with BASELINE_INPUT.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows[(row["sku_id"], row["date"])] = row
    if not rows:
        raise ValueError(f"No baseline forecasts found in {BASELINE_INPUT}")
    return rows, min(datetime.fromisoformat(key[1]).date() for key in rows)


def create_sequential_windows(
    baseline_rows: dict[tuple[str, str], dict[str, str]],
) -> tuple[np.ndarray, np.ndarray, list[dict[str, str]], list[dict[str, str]]]:
    """Return log-demand windows split by the fixed, calendar-time holdout.

    A window ending at date t contains demand through t-1 and predicts demand
    at t. Validation records are restricted to existing Day 6 baseline rows.
    """
    series: dict[str, list[dict[str, str]]] = defaultdict(list)
    baseline_skus = {sku_id for sku_id, _ in baseline_rows}
    with gzip.open(FEATURES_INPUT, "rt", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["sku_id"] in baseline_skus:
                series[row["sku_id"]].append(row)
    validation_start = min(datetime.fromisoformat(key[1]).date() for key in baseline_rows)
    training_windows: list[np.ndarray] = []
    training_targets: list[float] = []
    validation_windows: list[np.ndarray] = []
    validation_metadata: list[dict[str, str]] = []
    for sku_id, rows in series.items():
        rows.sort(key=lambda row: row["date"])
        demand = np.array([float(row["target_demand_units"]) for row in rows], dtype=np.float32)
        for index in range(WINDOW_DAYS, len(rows)):
            target_row = rows[index]
            window = np.log1p(demand[index - WINDOW_DAYS:index]).reshape(WINDOW_DAYS, 1)
            target_day = datetime.fromisoformat(target_row["date"]).date()
            if target_day < validation_start:
                training_windows.append(window)
                training_targets.append(math.log1p(float(demand[index])))
            elif (sku_id, target_row["date"]) in baseline_rows:
                validation_windows.append(window)
                validation_metadata.append(target_row)
    if not training_windows or not validation_windows:
        raise ValueError("Sequence creation produced an empty training or validation set.")
    return (
        np.stack(training_windows), np.asarray(training_targets, dtype=np.float32),
        validation_metadata, validation_windows,
    )


def train_and_predict(model, train_x, train_y, validation_x, torch) -> np.ndarray:
    """Train a sequence regressor on pre-validation windows only."""
    dataset = torch.utils.data.TensorDataset(torch.from_numpy(train_x), torch.from_numpy(train_y))
    loader = torch.utils.data.DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True, generator=torch.Generator().manual_seed(SEED))
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    loss_function = torch.nn.MSELoss()
    model.train()
    for _ in range(EPOCHS):
        for batch_x, batch_y in loader:
            optimizer.zero_grad()
            loss = loss_function(model(batch_x), batch_y)
            loss.backward()
            optimizer.step()
    model.eval()
    with torch.no_grad():
        log_predictions = model(torch.from_numpy(validation_x)).numpy()
    return np.maximum(0.0, np.expm1(log_predictions))


def main() -> None:
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("Install PyTorch first: python -m pip install -r requirements.txt") from exc

    torch.manual_seed(SEED)
    np.random.seed(SEED)
    baseline_rows, validation_start = load_baseline_rows()
    all_train_x, all_train_y, validation_metadata, validation_windows = create_sequential_windows(baseline_rows)
    validation_x = np.stack(validation_windows).astype(np.float32)
    sample_size = min(MAX_TRAINING_WINDOWS, len(all_train_x))
    sampled = np.random.default_rng(SEED).choice(len(all_train_x), size=sample_size, replace=False)
    train_x, train_y = all_train_x[sampled], all_train_y[sampled]

    class DemandRNN(torch.nn.Module):
        def __init__(self, recurrent_layer):
            super().__init__()
            self.recurrent = recurrent_layer(1, 32, batch_first=True)
            self.output = torch.nn.Linear(32, 1)

        def forward(self, inputs):
            sequence_output, _ = self.recurrent(inputs)
            return self.output(sequence_output[:, -1, :]).squeeze(1)

    predictions = {
        "lstm": train_and_predict(DemandRNN(torch.nn.LSTM), train_x, train_y, validation_x, torch),
        "gru": train_and_predict(DemandRNN(torch.nn.GRU), train_x, train_y, validation_x, torch),
    }
    actual = np.array([float(baseline_rows[(row["sku_id"], row["date"])]["actual_demand_units"]) for row in validation_metadata])
    baseline_models = ("naive_lag_1", "moving_average_7", "seasonal_naive_lag_7", "weekday_seasonal_mean")
    baseline_predictions = {
        name: np.array([float(baseline_rows[(row["sku_id"], row["date"])][name]) for row in validation_metadata])
        for name in baseline_models
    }
    forecast_rows: list[dict[str, object]] = []
    for index, row in enumerate(validation_metadata):
        baseline = baseline_rows[(row["sku_id"], row["date"])]
        forecast_rows.append({
            "date": row["date"], "sku_id": row["sku_id"], "description": row["description"],
            "actual_demand_units": f"{actual[index]:.4f}",
            **{name: f"{values[index]:.4f}" for name, values in predictions.items()},
            **{name: baseline[name] for name in baseline_models},
        })
    write_csv(OUT / "deep_learning_validation_forecasts.csv", ["date", "sku_id", "description", "actual_demand_units", *predictions, *baseline_models], forecast_rows)

    metric_rows: list[dict[str, object]] = []
    for name, values in {**predictions, **baseline_predictions}.items():
        mae, rmse, wmape = metrics(actual, values)
        metric_rows.append({"model_family": "deep_learning" if name in predictions else "baseline", "model": name,
                            "observations": len(actual), "mae": f"{mae:.4f}", "rmse": f"{rmse:.4f}", "wmape": f"{wmape:.4f}"})
    write_csv(OUT / "deep_learning_forecast_metrics.csv", list(metric_rows[0]), metric_rows)
    table = "\n".join(["| Family | Model | MAE | RMSE | WMAPE |", "| --- | --- | ---: | ---: | ---: |"] + [
        f"| {row['model_family']} | {row['model']} | {float(row['mae']):,.2f} | {float(row['rmse']):,.2f} | {float(row['wmape']):.2%} |"
        for row in sorted(metric_rows, key=lambda row: float(row["wmape"]))
    ])
    DOC.write_text(f"""# Week 2, Day 9 — Deep Learning Forecasting

## Sequential, time-aware design

Each LSTM and GRU example is a **{WINDOW_DAYS}-day** sequence of a SKU's preceding daily demand values, transformed with `log1p`; its target is the following day's demand. The models only train on windows whose targets precede **{validation_start.isoformat()}**. The final {VALIDATION_DAYS}-day validation period uses **{len(actual):,} shared SKU-date rows** from Day 6, so every model in the comparison is scored on identical actuals. The remaining **{len(baseline_rows) - len(actual):,}** Day 6 rows are not represented in the sequence-feature dataset and are excluded from every Day 9 metric.

For repeatable local runtime, training uses a seeded sample of **{len(train_x):,}** windows from **{len(all_train_x):,}** eligible pre-validation windows. Both models use one recurrent layer with 32 hidden units, four epochs, Adam optimization, and predictions are transformed back to units and clipped at zero.

## Comparable validation results

{table}

## Outputs

- `data/processed/deep_learning_validation_forecasts.csv` — deep-learning and baseline forecasts on the same holdout rows.
- `data/processed/deep_learning_forecast_metrics.csv` — comparable MAE, RMSE, and WMAPE.

## Reproducibility

```powershell
python -m pip install -r requirements.txt
python scripts/run_deep_learning_forecasts.py
```
""", encoding="utf-8")
    best = min(metric_rows, key=lambda row: float(row["wmape"]))
    print(f"Wrote {len(actual):,} aligned validation forecasts; best model: {best['model']} ({float(best['wmape']):.2%} WMAPE).")


if __name__ == "__main__":
    main()
