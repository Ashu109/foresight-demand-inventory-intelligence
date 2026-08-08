"""SKU-level replenishment actions page."""

from __future__ import annotations

import streamlit as st

from dashboard.data import is_synthetic_inventory, load_csv, number, render_sidebar


def parse_float(value: str | None, default: float = 0.0) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return default


st.set_page_config(page_title="Forsight | Replenishment", page_icon="📦", layout="wide")
render_sidebar()
st.title("Replenishment Actions")
st.caption("Safety-stock and lead-time-based SKU recommendations.")

recommendations = load_csv("replenishment_recommendations.csv")
category_rows = load_csv("inventory_risk_assessment.csv")

if not recommendations:
    st.error("No replenishment output is available. Run `scripts/optimize_replenishment.py` first.")
    st.stop()
if is_synthetic_inventory():
    st.warning("Synthetic demo inventory is active. Use this page to validate workflow behavior only, not to issue purchase orders.")

category_by_sku: dict[str, str] = {}
for row in category_rows:
    sku_id = str(row.get("sku_id") or "").strip()
    if sku_id:
        category_by_sku[sku_id] = str(row.get("category") or "UNMAPPED")

for row in recommendations:
    row["recommended_reorder_quantity"] = parse_float(row.get("recommended_reorder_quantity"))
    row["inventory_position_units"] = parse_float(row.get("inventory_position_units"))
    row["reorder_point_units"] = parse_float(row.get("reorder_point_units"))
    row["safety_stock_units"] = parse_float(row.get("safety_stock_units"))
    row["avg_daily_demand_units"] = parse_float(row.get("avg_daily_demand_units"))
    row["daily_demand_stddev_units"] = parse_float(row.get("daily_demand_stddev_units"))
    row["supplier_lead_time_days"] = parse_float(row.get("supplier_lead_time_days"))
    row["category"] = category_by_sku.get(row.get("sku_id"), str(row.get("category") or "UNMAPPED"))
    row["urgency_score"] = row["reorder_point_units"] - row["inventory_position_units"]

reorder = [row for row in recommendations if row["recommendation_status"] == "reorder_now"]
urgent = sorted(reorder, key=lambda row: (row["urgency_score"], -row["recommended_reorder_quantity"]), reverse=True)

categories = sorted({row["category"] for row in recommendations if row.get("category")})
status_options = ["All", "reorder_now", "no_order_required"]

col1, col2, col3, col4 = st.columns(4)
col1.metric("SKUs to reorder", number(len(reorder)))
col2.metric("Recommended units", number(sum(row["recommended_reorder_quantity"] for row in reorder)))
col3.metric("Average safety stock", f"{sum(row['safety_stock_units'] for row in recommendations) / max(len(recommendations), 1):,.1f} units")
col4.metric("Urgent reorder SKUs", number(sum(1 for row in reorder if row["urgency_score"] > 0)))

st.subheader("Reorder recommendation filters")
filter_col1, filter_col2, filter_col3 = st.columns([2, 3, 2])
search = filter_col1.text_input("Search SKU or description")
selected_status = filter_col2.selectbox("Recommendation status", status_options, index=0)
selected_categories = filter_col3.multiselect("Category", categories, default=categories[:5] if categories else [])

filtered = recommendations
if selected_status != "All":
    filtered = [row for row in filtered if row["recommendation_status"] == selected_status]
if selected_categories:
    filtered = [row for row in filtered if row["category"] in selected_categories]
if search:
    term = search.casefold()
    filtered = [row for row in filtered if term in str(row["sku_id"]).casefold() or term in str(row["description"]).casefold()]

st.subheader("Priority queue")
priority = sorted(
    filtered,
    key=lambda row: (
        row["recommendation_status"] != "reorder_now",
        row["urgency_score"],
        row["recommended_reorder_quantity"],
        -row["supplier_lead_time_days"],
    ),
    reverse=True,
)

highlight_columns = [
    "sku_id",
    "description",
    "category",
    "supplier_ids",
    "supplier_lead_time_days",
    "inventory_position_units",
    "reorder_point_units",
    "safety_stock_units",
    "recommended_reorder_quantity",
    "recommendation_status",
]

st.dataframe(
    [
        {
            "SKU": row["sku_id"],
            "Description": row["description"],
            "Category": row["category"],
            "Supplier lead time": f"{row['supplier_lead_time_days']:.0f} days",
            "Inventory position": number(row["inventory_position_units"]),
            "Reorder point": number(row["reorder_point_units"]),
            "Safety stock": number(row["safety_stock_units"]),
            "Recommended reorder": number(row["recommended_reorder_quantity"]),
            "Status": row["recommendation_status"].replace("_", " ").title(),
        }
        for row in priority
    ],
    use_container_width=True,
    hide_index=True,
    height=560,
)

with st.expander("Replenishment policy"):
    st.markdown(
        "Safety stock = `z × daily demand standard deviation × √lead time`. A reorder is triggered when inventory position (`on hand + on order − reserved`) is at or below the reorder point. "
        "Recommendations are prioritized by how far inventory position is below the reorder point and by requested reorder quantity."
    )
