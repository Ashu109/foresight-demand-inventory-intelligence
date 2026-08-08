"""Create reproducible Day 3 exploratory-demand-analysis outputs.

The demand measures in this report use positive, non-return sales lines.  Returns
remain in the cleaned dataset but are deliberately excluded from demand because
they are not future demand signals.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "clean_sales_transactions.csv"
OUTPUT = ROOT / "data" / "processed"
DOC = ROOT / "docs" / "day3_exploratory_data_analysis.md"


def percentile(sorted_values: list[float], fraction: float) -> float:
    """Linear-interpolated percentile without third-party dependencies."""
    if not sorted_values:
        return 0.0
    index = (len(sorted_values) - 1) * fraction
    lower, upper = math.floor(index), math.ceil(index)
    if lower == upper:
        return sorted_values[lower]
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * (index - lower)


def money(value: float) -> str:
    return f"{value:,.2f}"


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    sku = defaultdict(lambda: {"description": "UNKNOWN", "category": "UNMAPPED", "units": 0, "revenue": 0.0, "lines": 0, "days": set()})
    category = defaultdict(lambda: {"units": 0, "revenue": 0.0, "lines": 0, "skus": set()})
    daily = defaultdict(lambda: {"units": 0, "revenue": 0.0, "lines": 0})
    weekly = defaultdict(lambda: {"units": 0, "revenue": 0.0, "lines": 0})
    monthly = defaultdict(lambda: {"units": 0, "revenue": 0.0, "lines": 0})
    sku_daily = defaultdict(int)
    accepted_lines = demand_lines = 0
    first_date = last_date = None

    with INPUT.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            accepted_lines += 1
            quantity = int(row["quantity"])
            if row["is_return"].lower() == "true" or quantity <= 0:
                continue
            demand_lines += 1
            timestamp = datetime.fromisoformat(row["invoice_date"])
            date_key = timestamp.date().isoformat()
            week_key = timestamp.date().isoformat() if timestamp.weekday() == 0 else (timestamp.date()).fromordinal(timestamp.date().toordinal() - timestamp.weekday()).isoformat()
            month_key = timestamp.strftime("%Y-%m")
            revenue = float(row["line_revenue"])
            sku_id, category_id = row["sku_id"], row["category"]
            details = sku[sku_id]
            details["description"] = row["description"]
            details["category"] = category_id
            details["units"] += quantity
            details["revenue"] += revenue
            details["lines"] += 1
            details["days"].add(date_key)
            bucket = category[category_id]
            bucket["units"] += quantity
            bucket["revenue"] += revenue
            bucket["lines"] += 1
            bucket["skus"].add(sku_id)
            for collection, key in ((daily, date_key), (weekly, week_key), (monthly, month_key)):
                collection[key]["units"] += quantity
                collection[key]["revenue"] += revenue
                collection[key]["lines"] += 1
            sku_daily[(sku_id, date_key)] += quantity
            first_date = date_key if first_date is None or date_key < first_date else first_date
            last_date = date_key if last_date is None or date_key > last_date else last_date

    sku_rows = []
    for sku_id, value in sku.items():
        sku_rows.append({
            "sku_id": sku_id, "description": value["description"], "category": value["category"],
            "demand_units": value["units"], "sales_revenue": f"{value['revenue']:.2f}",
            "sales_lines": value["lines"], "active_demand_days": len(value["days"]),
        })
    sku_rows.sort(key=lambda item: (-item["demand_units"], item["sku_id"]))
    write_csv(OUTPUT / "eda_sku_performance.csv", list(sku_rows[0]), sku_rows)

    category_rows = [{
        "category": key, "demand_units": value["units"], "sales_revenue": f"{value['revenue']:.2f}",
        "sales_lines": value["lines"], "unique_skus": len(value["skus"]),
    } for key, value in category.items()]
    category_rows.sort(key=lambda item: -item["demand_units"])
    write_csv(OUTPUT / "eda_category_performance.csv", list(category_rows[0]), category_rows)

    time_rows = []
    for grain, collection in (("daily", daily), ("weekly", weekly), ("monthly", monthly)):
        for period, value in sorted(collection.items()):
            time_rows.append({"grain": grain, "period_start": period, "demand_units": value["units"], "sales_revenue": f"{value['revenue']:.2f}", "sales_lines": value["lines"]})
    write_csv(OUTPUT / "eda_demand_time_series.csv", list(time_rows[0]), time_rows)

    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday_summary = defaultdict(lambda: {"units": 0, "revenue": 0.0, "days": 0})
    calendar_month_summary = defaultdict(lambda: {"units": 0, "revenue": 0.0, "days": 0})
    for date_key, value in daily.items():
        date_value = datetime.fromisoformat(date_key)
        weekday = weekday_names[date_value.weekday()]
        month = date_value.strftime("%m")
        for summary, key in ((weekday_summary, weekday), (calendar_month_summary, month)):
            summary[key]["units"] += value["units"]
            summary[key]["revenue"] += value["revenue"]
            summary[key]["days"] += 1
    seasonality_rows = []
    for weekday in weekday_names:
        value = weekday_summary[weekday]
        if value["days"]:
            seasonality_rows.append({"dimension": "weekday", "period": weekday, "observed_demand_days": value["days"], "demand_units": value["units"], "average_units_per_observed_day": f"{value['units'] / value['days']:.2f}", "sales_revenue": f"{value['revenue']:.2f}"})
    for month in map(lambda n: f"{n:02d}", range(1, 13)):
        value = calendar_month_summary[month]
        if value["days"]:
            seasonality_rows.append({"dimension": "calendar_month", "period": month, "observed_demand_days": value["days"], "demand_units": value["units"], "average_units_per_observed_day": f"{value['units'] / value['days']:.2f}", "sales_revenue": f"{value['revenue']:.2f}"})
    write_csv(OUTPUT / "eda_demand_seasonality.csv", list(seasonality_rows[0]), seasonality_rows)

    # A robust daily-SKU spike rule: values beyond Q3 + 1.5*IQR, with at least
    # eight active days.  It intentionally compares only active selling days;
    # this avoids interpreting normal zero-sales days as demand spikes.
    per_sku_values = defaultdict(list)
    per_sku_days = defaultdict(list)
    for (sku_id, date_key), units in sku_daily.items():
        per_sku_values[sku_id].append(units)
        per_sku_days[sku_id].append((date_key, units))
    outliers = []
    for sku_id, values in per_sku_values.items():
        if len(values) < 8:
            continue
        ordered = sorted(values)
        q1, q3 = percentile(ordered, 0.25), percentile(ordered, 0.75)
        iqr = q3 - q1
        threshold = q3 + 1.5 * iqr
        # When IQR is zero, a product's usual order is constant. Require a
        # material step-up to avoid reporting routine repeats as anomalies.
        if iqr == 0:
            threshold = max(q3 * 2, q3 + 20)
        typical = median(ordered)
        for date_key, units in per_sku_days[sku_id]:
            if units > threshold:
                outliers.append({
                    "date": date_key, "sku_id": sku_id, "description": sku[sku_id]["description"],
                    "demand_units": units, "median_active_day_units": f"{typical:.2f}",
                    "q1_units": f"{q1:.2f}", "q3_units": f"{q3:.2f}",
                    "spike_threshold_units": f"{threshold:.2f}", "multiple_of_median": f"{(units / typical) if typical else 0:.2f}",
                })
    outliers.sort(key=lambda item: (-int(item["demand_units"]), item["date"], item["sku_id"]))
    write_csv(OUTPUT / "eda_demand_outliers.csv", list(outliers[0]), outliers)

    total_units = sum(item["demand_units"] for item in sku_rows)
    total_revenue = sum(float(item["sales_revenue"]) for item in sku_rows)
    sku_unit_values = sorted(item["demand_units"] for item in sku_rows)
    top_units = sku_rows[:10]
    top_revenue = sorted(sku_rows, key=lambda item: (-float(item["sales_revenue"]), item["sku_id"]))[:10]
    # Restrict the "worst" view to products seen on at least 30 demand days,
    # avoiding a misleading ranking of newly launched/one-off SKUs.
    established = [item for item in sku_rows if item["active_demand_days"] >= 30]
    worst_established = sorted(established, key=lambda item: (item["demand_units"], item["sku_id"]))[:10]
    busiest_days = sorted(daily.items(), key=lambda item: (-item[1]["units"], item[0]))[:10]
    strongest_weeks = sorted(weekly.items(), key=lambda item: (-item[1]["units"], item[0]))[:5]
    strongest_months = sorted(monthly.items(), key=lambda item: (-item[1]["units"], item[0]))[:12]
    strongest_weekdays = sorted(weekday_summary.items(), key=lambda item: (-(item[1]["units"] / item[1]["days"]), item[0]))
    strongest_calendar_months = sorted(calendar_month_summary.items(), key=lambda item: (-(item[1]["units"] / item[1]["days"]), item[0]))

    def product_table(rows: list[dict], metric: str) -> str:
        lines = ["| SKU | Description | Demand units | Revenue | Active days |", "| --- | --- | ---: | ---: | ---: |"]
        for item in rows:
            lines.append(f"| {item['sku_id']} | {item['description']} | {item['demand_units']:,} | {money(float(item['sales_revenue']))} | {item['active_demand_days']:,} |")
        return "\n".join(lines)

    def period_table(rows: list[tuple[str, dict]]) -> str:
        lines = ["| Period start | Demand units | Revenue | Sales lines |", "| --- | ---: | ---: | ---: |"]
        for period, value in rows:
            lines.append(f"| {period} | {value['units']:,} | {money(value['revenue'])} | {value['lines']:,} |")
        return "\n".join(lines)

    def seasonality_table(rows: list[tuple[str, dict]], label: str) -> str:
        lines = [f"| {label} | Observed demand days | Total units | Avg. units / observed day |", "| --- | ---: | ---: | ---: |"]
        for period, value in rows:
            lines.append(f"| {period} | {value['days']:,} | {value['units']:,} | {value['units'] / value['days']:,.0f} |")
        return "\n".join(lines)

    DOC.write_text(f"""# Week 1, Day 3 — Exploratory Data Analysis

## Scope and method

This analysis uses `{INPUT.relative_to(ROOT).as_posix()}` and covers **{first_date} through {last_date}**. Demand is defined as the quantity on positive, non-return sales lines; return/cancellation lines are excluded because they are not future demand. Revenue is the corresponding positive-line sales revenue. The source contains **{accepted_lines:,}** cleaned lines, of which **{demand_lines:,}** are included in demand.

The dataset has no SKU-category master: all demand is assigned to the cleanup placeholder `UNMAPPED`. Category performance is therefore available as a completeness check only, not as a product-family comparison. Add a validated SKU-category master before using category-level results for planning.

## Demand distribution

- **{len(sku_rows):,} SKUs** generated **{total_units:,} units** and **{money(total_revenue)}** in positive-line revenue.
- SKU demand is strongly long-tailed: median **{percentile(sku_unit_values, 0.50):,.0f}** units per SKU; 75th percentile **{percentile(sku_unit_values, 0.75):,.0f}**; 95th percentile **{percentile(sku_unit_values, 0.95):,.0f}**.
- The top 10 SKUs represent **{sum(row['demand_units'] for row in top_units) / total_units:.1%}** of all units. Prioritize these products for forecast accuracy and service-level review.

## Best-performing products

Ranked by demand units:

{product_table(top_units, 'demand_units')}

Ranked by positive-line revenue:

{product_table(top_revenue, 'sales_revenue')}

## Lowest-demand established products

To avoid treating a one-off or newly introduced SKU as a poor performer, this list includes only SKUs active on at least 30 distinct demand days. These are candidates for assortment, pricing, or data-quality review—not automatic delist recommendations.

{product_table(worst_established, 'demand_units')}

## Daily, weekly, and monthly demand patterns

The daily, week-start (Monday), and calendar-month series are written to `data/processed/eda_demand_time_series.csv` for charting and forecasting. The highest-volume periods are below.

### Highest-demand days

{period_table(busiest_days)}

### Highest-demand weeks

{period_table(strongest_weeks)}

### Highest-demand months

{period_table(strongest_months)}

### Recurring seasonality

Average demand is calculated per observed selling day, so that calendar closures do not make a weekday or month look artificially weak. The historical mix is strongest on **{strongest_weekdays[0][0]}** ({strongest_weekdays[0][1]['units'] / strongest_weekdays[0][1]['days']:,.0f} units per observed day) and in calendar month **{strongest_calendar_months[0][0]}** ({strongest_calendar_months[0][1]['units'] / strongest_calendar_months[0][1]['days']:,.0f} units per observed day). Treat the partial final month (December 2011 ends on the 9th) with care.

{seasonality_table(strongest_weekdays, 'Weekday')}

{seasonality_table(strongest_calendar_months, 'Month')}

## Unusual demand spikes

`data/processed/eda_demand_outliers.csv` contains **{len(outliers):,}** daily SKU spikes. A spike is a SKU's active-day quantity above Q3 + 1.5 × IQR, evaluated only for SKUs with at least eight active sales days. Where IQR is zero, the threshold is the greater of twice the usual quantity and usual quantity + 20 units. This is a review queue, not proof of an error: validate campaigns, holidays, bulk orders, and data-entry issues before changing forecasts.

Top 20 spikes by units:

| Date | SKU | Description | Units | Typical active day | Spike threshold | Multiple of median |
| --- | --- | --- | ---: | ---: | ---: | ---: |
""" + "\n".join(
        f"| {item['date']} | {item['sku_id']} | {item['description']} | {int(item['demand_units']):,} | {item['median_active_day_units']} | {item['spike_threshold_units']} | {item['multiple_of_median']}× |"
        for item in outliers[:20]
    ) + f"""

## Reproducibility

Run from the repository root:

```powershell
python -S scripts/analyze_demand_eda.py
```

Generated outputs:

- `data/processed/eda_sku_performance.csv`
- `data/processed/eda_category_performance.csv`
- `data/processed/eda_demand_time_series.csv`
- `data/processed/eda_demand_seasonality.csv`
- `data/processed/eda_demand_outliers.csv`
""", encoding="utf-8")

    print(f"Wrote EDA outputs for {len(sku_rows):,} SKUs and {len(outliers):,} demand spikes.")


if __name__ == "__main__":
    main()
