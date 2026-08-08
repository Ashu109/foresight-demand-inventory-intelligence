"""Alerts and reporting for inventory risk and replenishment."""

from __future__ import annotations

import csv
import io
import math

import streamlit as st

from dashboard.data import load_csv, number, render_sidebar


def parse_float(value: str | None, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


def parse_bool(value: str | None) -> bool:
    return str(value or "").strip().casefold() == "true"


def format_number(value: float) -> str:
    return number(value) if value is not None else "—"


def build_csv(rows: list[dict[str, str]], fields: list[str]) -> bytes:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def make_pdf(summary: dict[str, str], rows: list[dict[str, str]]) -> bytes | None:
    try:
        from fpdf import FPDF
    except ImportError:
        return None

    pdf = FPDF()
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Forsight Alerts & Reporting", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.ln(4)
    for key, value in summary.items():
        pdf.cell(0, 8, f"{key}: {value}", ln=True)
    pdf.ln(6)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Top alerts", ln=True)
    pdf.set_font("Arial", "", 10)
    for row in rows[:15]:
        line = (
            f"{row['SKU']} | {row['Alert type']} | {row['Category']} | "
            f"On hand: {row['On hand vs reorder']} | "
            f"Safety stock: {row['Safety stock']} | "
            f"Required reorder: {row['Required reorder']}"
        )
        pdf.multi_cell(0, 6, line)
    return pdf.output(dest="S").encode("latin-1")


st.set_page_config(page_title="Forsight | Alerts & Reporting", page_icon="🚨", layout="wide")
render_sidebar()
st.title("Alerts & Reporting")
st.caption("Low-stock, predicted stockout, and excess inventory alerting with exportable reports.")

risk_rows = load_csv("inventory_risk_assessment.csv")
replenishment_rows = load_csv("replenishment_recommendations.csv")

if not risk_rows:
    st.error("Inventory risk assessment output is unavailable. Run `scripts/analyze_inventory_risk.py` first.")
    st.stop()

if not replenishment_rows:
    st.error("Replenishment recommendations are unavailable. Run `scripts/optimize_replenishment.py` first.")
    st.stop()

risk_by_sku = {row["sku_id"]: row for row in risk_rows}
alerts: list[dict[str, object]] = []
for row in replenishment_rows:
    sku = row["sku_id"]
    risk = risk_by_sku.get(sku, {})
    inventory_position = parse_float(row.get("inventory_position_units"))
    reorder_point = parse_float(row.get("reorder_point_units"))
    days_of_supply = parse_float(risk.get("days_of_supply") or "0")
    potential_stockout = parse_bool(risk.get("potential_stockout")) or days_of_supply <= 3
    excess_inventory = parse_bool(risk.get("excess_inventory"))
    low_stock = inventory_position <= reorder_point
    alert_types: list[str] = []
    if low_stock:
        alert_types.append("Low stock")
    if potential_stockout:
        alert_types.append("Predicted stockout")
    if excess_inventory:
        alert_types.append("Excess inventory")
    if not alert_types:
        continue

    alerts.append({
        "sku_id": sku,
        "description": row.get("description", ""),
        "category": row.get("category") or str(risk.get("category") or "UNMAPPED"),
        "inventory_position": inventory_position,
        "reorder_point": reorder_point,
        "safety_stock": parse_float(row.get("safety_stock_units")),
        "days_of_supply": days_of_supply,
        "alert_types": alert_types,
        "required_reorder": max(0.0, parse_float(row.get("recommended_reorder_quantity"))),
    })

alert_type_options = ["All", "Low stock", "Predicted stockout", "Excess inventory"]
category_options = ["All"] + sorted({row["category"] for row in alerts if row.get("category")})

with st.sidebar.form("alerts_filters"):
    st.header("Alert filters")
    selected_alert = st.selectbox("Alert type", alert_type_options, index=0)
    selected_category = st.selectbox("Category", category_options, index=0)
    urgency_threshold = st.slider("Days of supply threshold", 0, 30, 7)
    submitted = st.form_submit_button("Apply filters")

filtered_alerts = alerts
if selected_alert != "All":
    filtered_alerts = [row for row in filtered_alerts if selected_alert in row["alert_types"]]
if selected_category != "All":
    filtered_alerts = [row for row in filtered_alerts if row["category"] == selected_category]
filtered_alerts = [row for row in filtered_alerts if row["days_of_supply"] <= urgency_threshold or row["required_reorder"] > 0]

low_stock_count = sum(1 for row in filtered_alerts if "Low stock" in row["alert_types"])
predicted_stockout_count = sum(1 for row in filtered_alerts if "Predicted stockout" in row["alert_types"])
excess_inventory_count = sum(1 for row in filtered_alerts if "Excess inventory" in row["alert_types"])

summary_cols = st.columns(4)
summary_cols[0].metric("Low-stock alerts", number(low_stock_count))
summary_cols[1].metric("Predicted stockouts", number(predicted_stockout_count))
summary_cols[2].metric("Excess inventory alerts", number(excess_inventory_count))
summary_cols[3].metric("Alert rows", number(len(filtered_alerts)))

st.markdown("---")

st.subheader("Alert details")
alert_columns = [
    "SKU",
    "Description",
    "Category",
    "Alert type",
    "On hand vs reorder",
    "Safety stock",
    "Days of supply",
    "Required reorder",
]
rows_for_display = [
    {
        "SKU": row["sku_id"],
        "Description": row["description"],
        "Category": row["category"],
        "Alert type": ", ".join(row["alert_types"]),
        "On hand vs reorder": f"{format_number(row['inventory_position'])} / {format_number(row['reorder_point'])}",
        "Safety stock": format_number(row["safety_stock"]),
        "Days of supply": f"{row['days_of_supply']:.1f}",
        "Required reorder": format_number(row["required_reorder"]),
    }
    for row in sorted(filtered_alerts, key=lambda item: ("Predicted stockout" in item["alert_types"], item["days_of_supply"]))
]
st.dataframe(rows_for_display, use_container_width=True, hide_index=True, height=520)

csv_data = build_csv(rows_for_display, alert_columns)
cols = st.columns(2)
cols[0].download_button(
    label="Download CSV report",
    data=csv_data,
    file_name="forsight_alerts_report.csv",
    mime="text/csv",
)

pdf_data = make_pdf(
    {
        "Low-stock alerts": str(low_stock_count),
        "Predicted stockouts": str(predicted_stockout_count),
        "Excess inventory alerts": str(excess_inventory_count),
        "Alert rows": str(len(filtered_alerts)),
    },
    rows_for_display,
)
if pdf_data is not None:
    cols[1].download_button(
        label="Download PDF report",
        data=pdf_data,
        file_name="forsight_alerts_report.pdf",
        mime="application/pdf",
    )
else:
    cols[1].warning("Install `fpdf` to enable PDF export: `pip install fpdf`.")
