"""Inventory intelligence and stock health dashboard."""

from __future__ import annotations

import csv
import statistics
from pathlib import Path

import streamlit as st

from dashboard.data import load_csv, load_manifest, number, render_sidebar

ROOT = Path(__file__).resolve().parents[1]
RAW_INVENTORY = ROOT / "data" / "raw" / "inventory_snapshot.csv"


def parse_float(value: str | None, default: float = 0.0) -> float:
    try:
        return float(value or 0)
    except ValueError:
        return default


def parse_optional_float(value: str | None) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except ValueError:
        return None


def load_raw_inventory() -> dict[str, dict[str, float]]:
    if not RAW_INVENTORY.exists():
        return {}
    inventory: dict[str, dict[str, float]] = {}
    with RAW_INVENTORY.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            sku = str(row.get("sku_id") or "").strip()
            if not sku:
                continue
            record = inventory.setdefault(sku, {"on_hand_quantity": 0.0, "inventory_value": 0.0, "on_order_quantity": 0.0, "reserved_quantity": 0.0})
            record["on_hand_quantity"] += parse_optional_float(row.get("on_hand_quantity")) or 0.0
            record["inventory_value"] += parse_optional_float(row.get("inventory_value")) or 0.0
            record["on_order_quantity"] += parse_optional_float(row.get("on_order_quantity")) or 0.0
            record["reserved_quantity"] += parse_optional_float(row.get("reserved_quantity")) or 0.0
    return inventory


def parse_bool(value: str | None) -> bool:
    return str(value or "").strip().casefold() == "true"


def money(value: float | None) -> str:
    if value is None:
        return "Unavailable"
    return f"${value:,.0f}"


st.set_page_config(page_title="Forsight | Inventory Intelligence", page_icon="🏭", layout="wide")
render_sidebar()
st.title("Inventory Intelligence")
st.caption("Current stock levels, SKU health, and risk-aware turnover metrics.")

manifest = load_manifest()
risk_rows = load_csv("inventory_risk_assessment.csv")
summary_rows = load_csv("inventory_risk_summary.csv")
replenishment = load_csv("replenishment_recommendations.csv")
sku_performance = load_csv("eda_sku_performance.csv")

if not risk_rows:
    st.error("Inventory intelligence outputs are unavailable. Run `scripts/analyze_inventory_risk.py` and ensure `data/processed/inventory_risk_assessment.csv` is populated.")
    st.stop()

performance_by_sku: dict[str, dict[str, float]] = {}
for row in sku_performance:
    performance_by_sku[row["sku_id"]] = {
        "sales_revenue": parse_float(row.get("sales_revenue")),
        "demand_units": parse_float(row.get("demand_units")),
    }

raw_inventory = load_raw_inventory()

for row in risk_rows:
    row["on_hand_quantity"] = parse_float(row.get("on_hand_quantity"))
    row["on_order_quantity"] = parse_float(row.get("on_order_quantity"))
    row["reserved_quantity"] = parse_float(row.get("reserved_quantity"))
    row["available_supply_quantity"] = parse_float(row.get("available_supply_quantity"))
    row["inventory_value"] = parse_float(row.get("inventory_value"))
    row["avg_daily_forecast_units"] = parse_float(row.get("avg_daily_forecast_units"))
    row["days_of_supply"] = parse_optional_float(row.get("days_of_supply"))
    row["lead_time_days"] = parse_optional_float(row.get("lead_time_days"))
    row["potential_stockout"] = parse_bool(row.get("potential_stockout"))
    row["excess_inventory"] = parse_bool(row.get("excess_inventory"))
    row["slow_moving"] = parse_bool(row.get("slow_moving"))
    row["risk_level"] = str(row.get("risk_level") or "").lower()
    performance = performance_by_sku.get(row["sku_id"], {})
    raw_values = raw_inventory.get(row["sku_id"], {})
    if row["inventory_value"] <= 0 and raw_values.get("inventory_value", 0) > 0:
        row["inventory_value"] = raw_values["inventory_value"]
    if row["on_hand_quantity"] <= 0 and raw_values.get("on_hand_quantity", 0) > 0:
        row["on_hand_quantity"] = raw_values["on_hand_quantity"]
    if row["available_supply_quantity"] <= 0 and raw_values.get("on_hand_quantity", 0) > 0:
        row["available_supply_quantity"] = raw_values["on_hand_quantity"]
    row["sales_revenue"] = performance.get("sales_revenue")
    row["demand_units"] = performance.get("demand_units")
    row["turnover_proxy"] = (
        row["sales_revenue"] / row["inventory_value"]
        if row["inventory_value"] > 0 and row["sales_revenue"] is not None
        else None
    )

sku_count = len(risk_rows)
stocked_skus = sum(1 for row in risk_rows if row["available_supply_quantity"] > 0)
total_on_hand = sum(row["on_hand_quantity"] for row in risk_rows)
total_available_supply = sum(row["available_supply_quantity"] for row in risk_rows)
total_inventory_value = sum(row["inventory_value"] for row in risk_rows)
stockout_skus = sum(1 for row in risk_rows if row["potential_stockout"])
overstock_skus = sum(1 for row in risk_rows if row["excess_inventory"])
slow_moving_skus = sum(1 for row in risk_rows if row["slow_moving"])
high_risk_skus = sum(1 for row in risk_rows if row["risk_level"] in {"critical", "high"})

turnover_values = [row["turnover_proxy"] for row in risk_rows if row["turnover_proxy"] is not None]
turnover_avg = statistics.mean(turnover_values) if turnover_values else None
turnover_median = statistics.median(turnover_values) if turnover_values else None

risk_counts: dict[str, int] = {}
for row in risk_rows:
    key = row["risk_level"] or "unknown"
    risk_counts[key] = risk_counts.get(key, 0) + 1

risk_chart = {level.title(): count for level, count in sorted(risk_counts.items(), key=lambda item: item[0])}

col1, col2, col3, col4 = st.columns(4)
col1.metric("Tracked SKUs", number(sku_count))
col2.metric("On-hand units", number(total_on_hand))
col3.metric("Available supply", number(total_available_supply))
col4.metric("Inventory value", money(total_inventory_value))

risk1, risk2, risk3, risk4 = st.columns(4)
risk1.metric("Stockout risk", number(stockout_skus), f"{stockout_skus / sku_count:.1%}" if sku_count else "—")
risk2.metric("Overstock risk", number(overstock_skus), f"{overstock_skus / sku_count:.1%}" if sku_count else "—")
risk3.metric("Slow-moving SKUs", number(slow_moving_skus), f"{slow_moving_skus / sku_count:.1%}" if sku_count else "—")
risk4.metric("High risk SKUs", number(high_risk_skus), f"{high_risk_skus / sku_count:.1%}" if sku_count else "—")

turnover1, turnover2, turnover3 = st.columns(3)
turnover1.metric("Average turnover", f"{turnover_avg:.2f}" if turnover_avg is not None else "Unavailable")
turnover2.metric("Median turnover", f"{turnover_median:.2f}" if turnover_median is not None else "Unavailable")
turnover3.metric("SKUs with turnover", number(len(turnover_values)))

st.markdown("---")

st.subheader("Inventory health by SKU")
if risk_chart:
    st.bar_chart(risk_chart)
else:
    st.info("No inventory risk categories are available yet.")

health_columns = [
    "sku_id",
    "description",
    "on_hand_quantity",
    "available_supply_quantity",
    "inventory_value",
    "avg_daily_forecast_units",
    "days_of_supply",
    "risk_level",
    "risk_reason",
]
health_preview = sorted(
    [row for row in risk_rows if row["risk_level"] in {"critical", "high", "excess", "slow_moving"}],
    key=lambda row: (
        0 if row["risk_level"] == "critical" else 1,
        row["days_of_supply"] if row["days_of_supply"] is not None else float("inf"),
        -row["available_supply_quantity"],
    ),
)[:20]

if health_preview:
    st.dataframe(
        [
            {
                "SKU": row["sku_id"],
                "Description": row["description"],
                "On hand": number(row["on_hand_quantity"]),
                "Available": number(row["available_supply_quantity"]),
                "Inventory value": money(row["inventory_value"]),
                "Forecast demand": number(row["avg_daily_forecast_units"]),
                "Days of supply": f"{row['days_of_supply']:.1f}" if row["days_of_supply"] is not None else "—",
                "Risk": row["risk_level"].title(),
                "Reason": row["risk_reason"],
            }
            for row in health_preview
        ],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No SKUs are currently flagged for stockout, overstock, or slow-moving risk.")

st.markdown("---")

st.subheader("Stockout and overstock alerts")
alert_columns = st.columns(2)
alert_columns[0].write("### Stockout risk SKUs")
stockout_preview = sorted(
    [row for row in risk_rows if row["potential_stockout"]],
    key=lambda row: (row["days_of_supply"] if row["days_of_supply"] is not None else float("inf"), row["avg_daily_forecast_units"]),
)[:10]
if stockout_preview:
    alert_columns[0].table(
        [
            {
                "SKU": row["sku_id"],
                "On hand": number(row["on_hand_quantity"]),
                "Forecast": number(row["avg_daily_forecast_units"]),
                "Days of supply": f"{row['days_of_supply']:.1f}" if row["days_of_supply"] is not None else "—",
            }
            for row in stockout_preview
        ]
    )
else:
    alert_columns[0].info("No current stockout risk SKUs detected.")

alert_columns[1].write("### Overstock risk SKUs")
overstock_preview = sorted(
    [row for row in risk_rows if row["excess_inventory"]],
    key=lambda row: (-row["available_supply_quantity"], row["days_of_supply"] if row["days_of_supply"] is not None else float("inf")),
)[:10]
if overstock_preview:
    alert_columns[1].table(
        [
            {
                "SKU": row["sku_id"],
                "Available": number(row["available_supply_quantity"]),
                "Days of supply": f"{row['days_of_supply']:.1f}" if row["days_of_supply"] is not None else "—",
                "Value": money(row["inventory_value"]),
            }
            for row in overstock_preview
        ]
    )
else:
    alert_columns[1].info("No current overstock risk SKUs detected.")

st.markdown("---")

st.subheader("Inventory turnover metrics")
if turnover_values:
    lowest_turnover = sorted([row for row in risk_rows if row["turnover_proxy"] is not None], key=lambda row: row["turnover_proxy"])[:8]
    highest_turnover = sorted([row for row in risk_rows if row["turnover_proxy"] is not None], key=lambda row: row["turnover_proxy"], reverse=True)[:8]
    turnover_cols = st.columns(2)
    turnover_cols[0].write("#### Lowest turnover (potential excess)")
    turnover_cols[0].table(
        [
            {
                "SKU": row["sku_id"],
                "Turnover": f"{row['turnover_proxy']:.2f}",
                "Inventory value": money(row["inventory_value"]),
                "Revenue": money(row["sales_revenue"]),
            }
            for row in lowest_turnover
        ]
    )
    turnover_cols[1].write("#### Highest turnover")
    turnover_cols[1].table(
        [
            {
                "SKU": row["sku_id"],
                "Turnover": f"{row['turnover_proxy']:.2f}",
                "Inventory value": money(row["inventory_value"]),
                "Revenue": money(row["sales_revenue"]),
            }
            for row in highest_turnover
        ]
    )
else:
    st.info("Inventory turnover cannot be calculated until SKU-level inventory value and sales revenue are both available.")

st.markdown("---")

st.subheader("SKU-level inventory health")
search = st.text_input("Search SKU or description")
options = [row for row in sorted(risk_rows, key=lambda row: row["sku_id"])]
if search:
    term = search.casefold()
    options = [row for row in options if term in row["sku_id"].casefold() or term in row["description"].casefold()]

if not options:
    st.warning("No SKUs match that search. Clear the search box to browse all inventory SKUs.")
    options = [row for row in sorted(risk_rows, key=lambda row: row["sku_id"])]

selected_label = st.selectbox(
    "Select SKU for detail", [f"{row['sku_id']} — {row['description']}" for row in options[:200]])
selected_sku = selected_label.split(" — ", 1)[0]
selected_row = next(row for row in risk_rows if row["sku_id"] == selected_sku)

detail_cols = st.columns(4)
detail_cols[0].metric("On-hand units", number(selected_row["on_hand_quantity"]))
detail_cols[1].metric("Available supply", number(selected_row["available_supply_quantity"]))
detail_cols[2].metric("Days of supply", f"{selected_row['days_of_supply']:.1f}" if selected_row["days_of_supply"] is not None else "Unavailable")
detail_cols[3].metric("Risk level", selected_row["risk_level"].title() or "Unavailable")

detail_cols2 = st.columns(4)
detail_cols2[0].metric("Inventory value", money(selected_row["inventory_value"]))
detail_cols2[1].metric("Forecast demand", number(selected_row["avg_daily_forecast_units"]))
if selected_row["turnover_proxy"] is not None:
    detail_cols2[2].metric("Turnover proxy", f"{selected_row['turnover_proxy']:.2f}")
else:
    detail_cols2[2].metric("Turnover proxy", "Unavailable")
detail_cols2[3].metric("Reorder point", number(parse_float(selected_row.get("reorder_point_units"))))

st.write(
    "Inventory health is driven by available supply, forecasted demand, and stock holding. Turnover is a proxy computed from historical sales value divided by current inventory value; compare low turnover with excess-stock flags to identify slow-moving stock."
)