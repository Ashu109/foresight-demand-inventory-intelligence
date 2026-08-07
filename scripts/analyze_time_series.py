"""Create reproducible Day 4 SKU-level time-series analysis outputs.

Demand is positive, non-return quantity.  Weekly series include zero-demand
weeks; this is essential for intermittency and variability diagnostics.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "clean_sales_transactions.csv"
OUT = ROOT / "data" / "processed"
DOC = ROOT / "docs" / "day4_time_series_analysis.md"


def monday(value: date) -> date:
    return value - timedelta(days=value.weekday())


def sample_std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = mean(values)
    return math.sqrt(sum((value - avg) ** 2 for value in values) / (len(values) - 1))


def correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) < 3:
        return None
    left_mean, right_mean = mean(left), mean(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right))
    denominator = math.sqrt(sum((x - left_mean) ** 2 for x in left) * sum((y - right_mean) ** 2 for y in right))
    return numerator / denominator if denominator else None


def slope(values: list[float]) -> float:
    """Ordinary least-squares units per week."""
    count = len(values)
    x_mean, y_mean = (count - 1) / 2, mean(values)
    denominator = sum((index - x_mean) ** 2 for index in range(count))
    return sum((index - x_mean) * (value - y_mean) for index, value in enumerate(values)) / denominator if denominator else 0.0


def centered_moving_average(values: list[float], width: int = 13) -> list[float | None]:
    radius = width // 2
    result: list[float | None] = []
    for index in range(len(values)):
        if index < radius or index + radius >= len(values):
            result.append(None)
        else:
            result.append(mean(values[index - radius:index + radius + 1]))
    return result


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def format_table(rows: list[dict], columns: list[tuple[str, str, str]]) -> str:
    header = "| " + " | ".join(label for _, label, _ in columns) + " |"
    rule = "| " + " | ".join("---:" if align == "right" else "---" for _, _, align in columns) + " |"
    lines = [header, rule]
    for row in rows:
        lines.append("| " + " | ".join(str(row[key]) for key, _, _ in columns) + " |")
    return "\n".join(lines)


def main() -> None:
    sku_daily: dict[tuple[str, str], int] = defaultdict(int)
    sku_meta: dict[str, str] = {}
    first_day: date | None = None
    last_day: date | None = None
    input_lines = demand_lines = 0

    with INPUT.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            input_lines += 1
            quantity = int(row["quantity"])
            if row["is_return"].lower() == "true" or quantity <= 0:
                continue
            demand_lines += 1
            day = datetime.fromisoformat(row["invoice_date"]).date()
            day_key, sku_id = day.isoformat(), row["sku_id"]
            sku_daily[(sku_id, day_key)] += quantity
            sku_meta[sku_id] = row["description"]
            first_day = day if first_day is None or day < first_day else first_day
            last_day = day if last_day is None or day > last_day else last_day

    assert first_day is not None and last_day is not None
    first_week, last_week = monday(first_day), monday(last_day)
    weeks: list[date] = []
    candidate = first_week
    while candidate <= last_week:
        weeks.append(candidate)
        candidate += timedelta(days=7)

    sku_weekly: dict[tuple[str, date], int] = defaultdict(int)
    daily_rows = []
    for (sku_id, day_key), units in sorted(sku_daily.items(), key=lambda item: (item[0][0], item[0][1])):
        day = date.fromisoformat(day_key)
        week = monday(day)
        sku_weekly[(sku_id, week)] += units
        daily_rows.append({"sku_id": sku_id, "description": sku_meta[sku_id], "date": day_key, "week_start": week.isoformat(), "demand_units": units})
    write_csv(OUT / "ts_sku_daily_demand.csv", ["sku_id", "description", "date", "week_start", "demand_units"], daily_rows)

    weekly_rows = []
    series_by_sku: dict[str, list[int]] = {}
    for sku_id in sorted(sku_meta):
        values = [sku_weekly[(sku_id, week)] for week in weeks]
        series_by_sku[sku_id] = values
        for week, units in zip(weeks, values):
            weekly_rows.append({"sku_id": sku_id, "description": sku_meta[sku_id], "week_start": week.isoformat(), "demand_units": units})
    write_csv(OUT / "ts_sku_weekly_demand.csv", ["sku_id", "description", "week_start", "demand_units"], weekly_rows)

    # Omit partial boundary weeks from metrics: the dataset begins/ends mid-week.
    analysis_weeks = weeks[1:-1]
    metrics = []
    for sku_id, full_values in series_by_sku.items():
        values = full_values[1:-1]
        positive_weeks = sum(value > 0 for value in values)
        average, std = mean(values), sample_std(values)
        first_13, last_13 = mean(values[:13]), mean(values[-13:])
        change = ((last_13 - first_13) / first_13 * 100) if first_13 else None
        lag1 = correlation(values[:-1], values[1:])
        metrics.append({
            "sku_id": sku_id, "description": sku_meta[sku_id], "analysis_weeks": len(values),
            "positive_demand_weeks": positive_weeks, "zero_demand_week_pct": f"{(1 - positive_weeks / len(values)) * 100:.2f}",
            "mean_weekly_demand": f"{average:.2f}", "std_weekly_demand": f"{std:.2f}",
            "coefficient_of_variation": f"{(std / average) if average else 0:.3f}",
            "average_demand_interval_weeks": f"{(len(values) / positive_weeks) if positive_weeks else 0:.2f}",
            "lag_1_autocorrelation": "" if lag1 is None else f"{lag1:.3f}",
            "first_13_week_average": f"{first_13:.2f}", "last_13_week_average": f"{last_13:.2f}",
            "trend_slope_units_per_week": f"{slope(values):.3f}",
            "recent_vs_initial_13_week_change_pct": "" if change is None else f"{change:.2f}",
        })
    metrics.sort(key=lambda row: row["sku_id"])
    write_csv(OUT / "ts_sku_diagnostics.csv", list(metrics[0]), metrics)

    decomposition_rows = []
    def append_decomposition(series: str, description: str, values: list[int]) -> dict[int, float]:
        trend = centered_moving_average(values)
        # Additive seasonal factors by ISO week after removing local trend.
        detrended_by_week = defaultdict(list)
        for week, actual, local_trend in zip(weeks, values, trend):
            if local_trend is not None:
                detrended_by_week[week.isocalendar().week].append(actual - local_trend)
        seasonal = {week_number: mean(items) for week_number, items in detrended_by_week.items()}
        seasonal_mean = mean(seasonal.values())
        seasonal = {week_number: value - seasonal_mean for week_number, value in seasonal.items()}
        for week, actual, local_trend in zip(weeks, values, trend):
            season = seasonal.get(week.isocalendar().week)
            fitted = (local_trend + season) if local_trend is not None and season is not None else None
            decomposition_rows.append({
                "series": series, "description": description, "week_start": week.isoformat(), "demand_units": actual,
                "trend_13_week_centered_ma": "" if local_trend is None else f"{local_trend:.2f}",
                "seasonal_component": "" if season is None else f"{season:.2f}",
                "residual": "" if fitted is None else f"{actual - fitted:.2f}",
            })
        return seasonal

    total_values = [sum(series_by_sku[sku][index] for sku in series_by_sku) for index in range(len(weeks))]
    seasonal = append_decomposition("ALL_SKUS", "All products", total_values)
    for sku_id in sorted(series_by_sku, key=lambda key: -sum(series_by_sku[key]))[:10]:
        append_decomposition(sku_id, sku_meta[sku_id], series_by_sku[sku_id])
    write_csv(OUT / "ts_weekly_decomposition.csv", list(decomposition_rows[0]), decomposition_rows)

    eligible = [row for row in metrics if int(row["positive_demand_weeks"]) >= 52 and float(row["mean_weekly_demand"]) >= 50]
    # Percentage comparisons from an almost-zero base are not decision-useful.
    # Keep a meaningful initial baseline for the growth table; diagnostics still
    # retain every SKU and its absolute OLS slope.
    strongest_growth = sorted((row for row in eligible if row["recent_vs_initial_13_week_change_pct"] and float(row["first_13_week_average"]) >= 20), key=lambda row: -float(row["recent_vs_initial_13_week_change_pct"]))[:10]
    sharpest_decline = sorted((row for row in eligible if row["recent_vs_initial_13_week_change_pct"]), key=lambda row: float(row["recent_vs_initial_13_week_change_pct"]))[:10]
    most_variable = sorted(eligible, key=lambda row: -float(row["coefficient_of_variation"]))[:10]
    highest_persistence = sorted((row for row in eligible if row["lag_1_autocorrelation"]), key=lambda row: -float(row["lag_1_autocorrelation"]))[:10]

    aggregate_analysis = total_values[1:-1]
    aggregate_lag1 = correlation(aggregate_analysis[:-1], aggregate_analysis[1:])
    aggregate_seasonal = sorted(seasonal.items(), key=lambda item: -item[1])[:8]
    seasonal_table = "\n".join(["| ISO week | Additive seasonal component (units) |", "| ---: | ---: |"] + [f"| {week_number} | {value:,.0f} |" for week_number, value in aggregate_seasonal])
    summary_columns = [("sku_id", "SKU", "left"), ("description", "Description", "left"), ("mean_weekly_demand", "Mean weekly units", "right"), ("recent_vs_initial_13_week_change_pct", "13-week change", "right")]
    variability_columns = [("sku_id", "SKU", "left"), ("description", "Description", "left"), ("coefficient_of_variation", "CV", "right"), ("average_demand_interval_weeks", "ADI weeks", "right"), ("lag_1_autocorrelation", "Lag-1 ACF", "right")]

    DOC.write_text(f"""# Week 1, Day 4 — Time-Series Analysis

## Scope and construction

This analysis aggregates the cleaned sales data from **{first_day.isoformat()} to {last_day.isoformat()}** into SKU-day and SKU-week demand series. Demand is positive, non-return quantity; all missing SKU-week combinations are explicitly represented as zero. The weekly calendar spans **{len(weeks)} weeks**; the first and final partial weeks are excluded from diagnostics, leaving **{len(analysis_weeks)} comparable weeks**.

## Outputs

- `data/processed/ts_sku_daily_demand.csv` — sparse SKU-day demand (only days with demand).
- `data/processed/ts_sku_weekly_demand.csv` — complete SKU-week panel including zero-demand weeks.
- `data/processed/ts_sku_diagnostics.csv` — trend, variability, intermittency, and lag-1 autocorrelation per SKU.
- `data/processed/ts_weekly_decomposition.csv` — additive decomposition of the all-SKU series and the 10 highest-volume SKUs.

## Aggregate trend and seasonality

Across the comparable weeks, total weekly demand averages **{mean(aggregate_analysis):,.0f} units** (standard deviation **{sample_std(aggregate_analysis):,.0f}**). The portfolio's lag-1 autocorrelation is **{aggregate_lag1:.3f}**, indicating that adjacent weeks have meaningful persistence, though promotion and bulk-order spikes remain material.

The additive decomposition uses a centered 13-week moving average for local trend. Seasonal components are calculated by ISO week after removing that trend and are normalized to average zero. It is produced for the full portfolio and the 10 highest-volume SKUs. This is exploratory—not a substitute for a forecasting model—and the boundary weeks lack a centered trend estimate.

Highest positive seasonal components:

{seasonal_table}

## SKU trend diagnostics

The growth and decline lists require at least 52 positive-demand weeks and mean weekly demand of at least 50 units. The growth list also requires at least 20 units per week in the initial window so tiny launch-period baselines do not create misleading percentage growth. Trend compares the most recent 13 full weeks with the first 13 full weeks, so it should be read alongside seasonality and business events.

### Strongest recent growth

{format_table(strongest_growth, summary_columns)}

### Sharpest recent decline

{format_table(sharpest_decline, summary_columns)}

## Demand variability and autocorrelation

Coefficient of variation (CV) is standard deviation divided by mean weekly demand; higher values indicate greater relative variability. Average demand interval (ADI) is total weeks divided by positive-demand weeks; it quantifies intermittency. Lag-1 autocorrelation measures similarity to the immediately preceding week.

### Most variable eligible SKUs

{format_table(most_variable, variability_columns)}

### Strongest week-to-week persistence

{format_table(highest_persistence, variability_columns)}

## Interpretation for forecasting

- Use weekly models for intermittent products or aggregate low-volume SKUs before forecasting.
- Treat high-CV/long-ADI SKUs as candidates for intermittent-demand approaches rather than ordinary seasonal models.
- Include calendar/promotion features when modeling high seasonal-component weeks and review the Day 3 spike queue before training.
- The source ends on 2011-12-09; do not treat that partial period as a normal December forecast target.

## Reproducibility

Run from the repository root:

```powershell
python -S scripts/analyze_time_series.py
```
""", encoding="utf-8")
    print(f"Wrote SKU daily/weekly series for {len(sku_meta):,} SKUs and diagnostics over {len(analysis_weeks)} full weeks.")


if __name__ == "__main__":
    main()
