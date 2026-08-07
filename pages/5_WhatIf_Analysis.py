"""What-if inventory scenario analysis."""

from __future__ import annotations

import math

import streamlit as st

from dashboard.data import load_csv, number, render_sidebar


def parse_float(value: str | None, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


def scenario_metrics(row: dict[str, str], demand_factor: float, lead_time_delta: float, safety_stock_factor: float) -> dict[str, float]:
    avg_demand = parse_float(row.get("avg_daily_demand_units"))
    stddev = parse_float(row.get("daily_demand_stddev_units"))
    lead_time = max(1.0, parse_float(row.get("supplier_lead_time_days")) + lead_time_delta)
    review_days = max(0.0, parse_float(row.get("review_period_days")))
    inventory_position = parse_float(row.get("inventory_position_units"))
    demand = avg_demand * demand_factor
    safety_stock = safety_stock_factor * stddev * math.sqrt(lead_time)
    reorder_point = demand * lead_time + safety_stock
    target_stock = demand * (lead_time + review_days) + safety_stock
    required_reorder = max(0.0, target_stock - inventory_position)
    return {
        "avg_demand": demand,
        "lead_time": lead_time,
        "safety_stock": safety_stock,
        "reorder_point": reorder_point,
        "target_stock": target_stock,
        "inventory_position": inventory_position,
        "required_reorder": required_reorder,
    }


def format_days(days: float) -> str:
    return f"{days:.1f} days"


st.set_page_config(page_title="Forsight | What-If Analysis", page_icon="🔍", layout="wide")
render_sidebar()
st.title("What-If Inventory Analysis")
st.caption("Simulate demand, lead-time, and safety-stock changes to estimate inventory requirements.")

recommendations = load_csv("replenishment_recommendations.csv")
category_rows = load_csv("inventory_risk_assessment.csv")

if not recommendations:
    st.error("Replenishment recommendations are unavailable. Run `scripts/optimize_replenishment.py` first.")
    st.stop()

category_by_sku: dict[str, str] = {}
for row in category_rows:
    sku_id = str(row.get("sku_id") or "").strip()
    if sku_id:
        category_by_sku[sku_id] = str(row.get("category") or "UNMAPPED")

for row in recommendations:
    row["category"] = category_by_sku.get(row.get("sku_id"), str(row.get("category") or "UNMAPPED"))

with st.sidebar.form("whatif_controls"):
    st.header("Scenario inputs")
    demand_pct = st.slider("Demand change", -50, 100, 0, step=5, format="%d%%")
    lead_time_delta = st.slider("Lead-time adjustment", -7, 14, 0, step=1, format="%+d days")
    safety_stock_factor = st.slider("Safety-stock multiplier", 50, 250, 100, step=10, format="%d%%") / 100.0
    selected_category = st.selectbox(
        "Filter by category",
        ["All"] + sorted({row["category"] for row in recommendations if row.get("category")}),
        index=0,
    )
    selected_status = st.selectbox(
        "Recommendation status",
        ["All", "reorder_now", "no_order_required"],
        index=0,
    )
    submitted = st.form_submit_button("Apply scenario")

if not submitted:
    st.info("Use the sidebar controls to apply a what-if scenario and view the resulting inventory requirements.")

scenario_factor = 1.0 + demand_pct / 100.0

filtered = recommendations
if selected_category != "All":
    filtered = [row for row in filtered if row["category"] == selected_category]
if selected_status != "All":
    filtered = [row for row in filtered if row["recommendation_status"] == selected_status]

scenario_rows = []
for row in filtered:
    metrics = scenario_metrics(row, scenario_factor, lead_time_delta, safety_stock_factor)
    scenario_rows.append({
        **row,
        **metrics,
    })

for row in scenario_rows:
    row["required_reorder"] = float(row["required_reorder"])
    row["safety_stock"] = float(row["safety_stock"])
    row["reorder_point"] = float(row["reorder_point"])
    row["target_stock"] = float(row["target_stock"])
    row["avg_demand"] = float(row["avg_demand"])
    row["lead_time"] = float(row["lead_time"])

st.subheader("Scenario summary")
total_reorder = sum(row["required_reorder"] for row in scenario_rows)
reorder_count = sum(1 for row in scenario_rows if row["required_reorder"] > 0)
avg_lead = sum(row["lead_time"] for row in scenario_rows) / max(len(scenario_rows), 1)

summary_cols = st.columns(4)
summary_cols[0].metric("Demand change", f"{demand_pct:+d}%")
summary_cols[1].metric("Lead-time adjustment", format_days(lead_time_delta))
summary_cols[2].metric("Safety-stock factor", f"{safety_stock_factor:.2f}x")
summary_cols[3].metric("Estimated reorder units", number(total_reorder))

stats_cols = st.columns(4)
stats_cols[0].metric("SKU scope", number(len(scenario_rows)))
stats_cols[1].metric("Estimated reorder SKUs", number(reorder_count))
stats_cols[2].metric("Average lead time", format_days(avg_lead))
stats_cols[3].metric("Average safety stock", number(sum(row["safety_stock"] for row in scenario_rows) / max(len(scenario_rows), 1)))

st.markdown("---")

st.subheader("Top impacted SKUs")
priority = sorted(
    scenario_rows,
    key=lambda row: (row["required_reorder"], row["avg_demand"]),
    reverse=True,
)[:15]

st.dataframe(
    [
        {
            "SKU": row["sku_id"],
            "Description": row["description"],
            "Category": row["category"],
            "Demand": number(row["avg_demand"]),
            "Lead time": format_days(row["lead_time"]),
            "Safety stock": number(row["safety_stock"]),
            "Reorder point": number(row["reorder_point"]),
            "Inventory position": number(parse_float(row.get("inventory_position_units"))),
            "Required reorder": number(row["required_reorder"]),
            "Status": row["recommendation_status"].replace("_", " ").title(),
        }
        for row in priority
    ],
    use_container_width=True,
    hide_index=True,
    height=520,
)

st.markdown("---")

st.subheader("SKU-level what-if detail")
search = st.text_input("Search SKU or description")
selected = [row for row in scenario_rows if not search or search.casefold() in str(row["sku_id"]).casefold() or search.casefold() in str(row["description"]).casefold()]
selected = sorted(selected, key=lambda row: row["required_reorder"], reverse=True)
if selected:
    chosen = st.selectbox(
        "Select SKU for detailed estimates",
        [f"{row['sku_id']} — {row['description']}" for row in selected[:200]],
    )
    chosen_sku = chosen.split(" — ", 1)[0]
    detail = next(row for row in selected if row["sku_id"] == chosen_sku)
    detail_cols = st.columns(3)
    detail_cols[0].metric("Scenario demand", number(detail["avg_demand"]))
    detail_cols[1].metric("Scenario safety stock", number(detail["safety_stock"]))
    detail_cols[2].metric("Scenario reorder point", number(detail["reorder_point"]))

    detail_cols2 = st.columns(3)
    detail_cols2[0].metric("Inventory position", number(parse_float(detail.get("inventory_position_units"))))
    detail_cols2[1].metric("Required reorder", number(detail["required_reorder"]))
    detail_cols2[2].metric("Target stock", number(detail["target_stock"]))
else:
    st.info("No SKUs match the search term. Clear the field to browse all scenario SKUs.")

st.write(
    "This analysis recomputes safety stock, reorder point, and target stock for each SKU using the selected demand, lead time, and safety-stock assumptions. Required reorder quantity is the gap between target stock and current inventory position."
)
