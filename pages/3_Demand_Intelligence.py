"""Demand intelligence dashboard page."""

from __future__ import annotations

import statistics
import streamlit as st

from dashboard.data import load_csv, load_manifest, number, render_sidebar


def parse_float(value: str | None, default: float = 0.0) -> float:
    try:
        return float(value or 0)
    except ValueError:
        return default


def select_sku(sku_meta: dict[str, str]) -> tuple[str, str]:
    search = st.text_input("Search SKU or description")
    normalized = search.casefold().strip()
    sorted_items = sorted(sku_meta.items(), key=lambda item: (item[0], item[1]))
    if normalized:
        results = [item for item in sorted_items if normalized in item[0].casefold() or normalized in item[1].casefold()]
    else:
        results = sorted_items[:200]
    if not results:
        st.warning("No SKUs match that search. Clear the search box to browse the first 200 SKUs.")
        results = sorted_items[:200]

    options = [f"{sku} — {description}" for sku, description in results]
    selected = st.selectbox("Select SKU", options, index=0)
    sku_id, description = selected.split(" — ", 1)
    return sku_id, description


def series_for_sku(rows: list[dict[str, str]], sku_id: str, date_field: str, value_field: str) -> list[tuple[str, float]]:
    return sorted(
        [
            (row[date_field], parse_float(row[value_field]))
            for row in rows
            if row["sku_id"] == sku_id and row.get(date_field) and row.get(value_field) is not None
        ],
        key=lambda pair: pair[0],
    )


def first_matching_row(rows: list[dict[str, str]], sku_id: str) -> dict[str, str] | None:
    return next((row for row in rows if row["sku_id"] == sku_id), None)


st.set_page_config(page_title="Forsight | Demand Intelligence", page_icon="🧠", layout="wide")
render_sidebar()
st.title("Demand Intelligence")
st.caption("Historical demand, short-term forecasts, and forecast confidence for selected SKUs.")

manifest = load_manifest()

demand_rows = load_csv("ts_sku_daily_demand.csv")
if not demand_rows:
    st.error("Historical demand data is unavailable. Run the time-series analysis pipeline first.")
    st.stop()

recommendations = load_csv("week2_sku_recommendations.csv")
sku_accuracy = load_csv("sku_forecast_accuracy.csv")
champions = load_csv("sku_model_champions.csv")
baseline_forecasts = load_csv("baseline_holdout_forecasts.csv")
deep_forecasts = load_csv("deep_learning_validation_forecasts.csv")
ml_forecasts = load_csv("ml_validation_forecasts.csv")

sku_meta: dict[str, str] = {}
for row in demand_rows:
    sku_id = row["sku_id"]
    if sku_id not in sku_meta:
        sku_meta[sku_id] = row.get("description", "")

sku_id, description = select_sku(sku_meta)
selected_demand = [row for row in demand_rows if row["sku_id"] == sku_id]
selected_demand.sort(key=lambda row: row["date"])

st.subheader("SKU summary")
if not selected_demand:
    st.error("This SKU has no historical demand records in the processed time-series data.")
    st.stop()

latest_date = selected_demand[-1]["date"]
recent_days = selected_demand[-90:]
recent_demand = [parse_float(row["demand_units"]) for row in recent_days]
recent_dates = [row["date"] for row in recent_days]

recommendation = first_matching_row(recommendations, sku_id)
if recommendation:
    avg_daily_forecast = parse_float(recommendation.get("avg_daily_gru_forecast_units"))
    forecast_window_start = recommendation.get("forecast_window_start", "?")
    forecast_window_end = recommendation.get("forecast_window_end", "?")
    reorder_status = recommendation.get("recommendation_status", "unknown")
    daily_stddev = parse_float(recommendation.get("daily_demand_stddev_units"))
    avg_daily_demand = parse_float(recommendation.get("avg_daily_demand_units"))
    service_level = parse_float(recommendation.get("service_level"))
    safety_stock = parse_float(recommendation.get("safety_stock_units"))
else:
    avg_daily_forecast = 0.0
    forecast_window_start = "Unavailable"
    forecast_window_end = "Unavailable"
    reorder_status = "Unavailable"
    daily_stddev = 0.0
    avg_daily_demand = 0.0
    service_level = 0.0
    safety_stock = 0.0

champion_row = first_matching_row(champions, sku_id)
best_row = None
if champion_row:
    selected_model = champion_row.get("selected_model", "gru")
    best_row = first_matching_row(sku_accuracy, sku_id)
else:
    selected_model = "gru"

accuracy_rows = [row for row in sku_accuracy if row["sku_id"] == sku_id]
if accuracy_rows:
    ranked = sorted(accuracy_rows, key=lambda row: parse_float(row.get("wmape")))
    best_metrics = ranked[0]
else:
    best_metrics = None

if recommendation:
    forecast_7 = avg_daily_forecast * 7
    forecast_14 = avg_daily_forecast * 14
    forecast_28 = avg_daily_forecast * 28
else:
    forecast_7 = forecast_14 = forecast_28 = 0.0

if recommendation:
    risk_cv = daily_stddev / avg_daily_demand if avg_daily_demand > 0 else 0.0
else:
    last_28_values = [parse_float(row["demand_units"]) for row in selected_demand[-28:]]
    mean_28 = statistics.mean(last_28_values) if last_28_values else 0.0
    std_28 = statistics.pstdev(last_28_values) if len(last_28_values) > 1 else 0.0
    risk_cv = std_28 / mean_28 if mean_28 > 0 else 0.0

risk_level = "Lower"
if risk_cv > 1 or (best_metrics and parse_float(best_metrics.get("wmape")) > 1):
    risk_level = "High"
elif risk_cv > 0.5 or (best_metrics and parse_float(best_metrics.get("wmape")) > 0.5):
    risk_level = "Medium"

col1, col2, col3, col4 = st.columns(4)
col1.metric("SKU", sku_id)
col2.metric("Latest demand date", latest_date)
col3.metric("Forecast window", f"{forecast_window_start} → {forecast_window_end}")
col4.metric("Recommendation", reorder_status.replace("_", " ").title())

st.markdown("---")

st.subheader("Historical demand")
if recent_dates:
    chart_data = {
        "Actual demand": recent_demand,
    }
    st.line_chart(chart_data)
    st.write(f"Showing the most recent {len(recent_dates)} positive-demand records for this SKU.")
else:
    st.info("No recent demand values are available for this SKU.")

st.subheader("Short-term forecast horizon")
col1, col2, col3 = st.columns(3)
col1.metric("7-day forecast", number(forecast_7))
col2.metric("14-day forecast", number(forecast_14))
col3.metric("28-day forecast", number(forecast_28))
st.write("Forecast totals are estimated from the average daily GRU forecast in the recommendation handoff.")

st.subheader("Actual vs predicted")
model_series = []
champion_model = selected_model or "gru"
if champion_model in {"gru", "lstm"}:
    model_series = series_for_sku(deep_forecasts, sku_id, "date", champion_model)
elif champion_model in {"naive_lag_1", "moving_average_7", "seasonal_naive_lag_7", "weekday_seasonal_mean"}:
    model_series = series_for_sku(baseline_forecasts, sku_id, "date", champion_model)
else:
    model_series = series_for_sku(ml_forecasts, sku_id, "date", champion_model)

if model_series:
    model_dates, model_values = zip(*model_series)
    actual_for_model = [parse_float(row["actual_demand_units"]) for row in baseline_forecasts if row["sku_id"] == sku_id]
    chart_data = {
        "Actual demand": [parse_float(row["actual_demand_units"] if row.get("actual_demand_units") else "0") for row in baseline_forecasts if row["sku_id"] == sku_id],
        champion_model: [value for _, value in model_series],
    }
    st.line_chart(chart_data)
    st.write(f"Actual vs predicted values on holdout data from the {champion_model} model.")
else:
    st.info("No model forecast series is available for the selected model on this SKU.")

st.subheader("Forecast confidence and risk")
confidence_cols = st.columns(3)
confidence_cols[0].metric("Best model", champion_model.upper())
if best_metrics:
    confidence_cols[1].metric("WMAPE", f"{parse_float(best_metrics.get('wmape')):.2%}")
    confidence_cols[2].metric("MAE", f"{parse_float(best_metrics.get('mae')):.2f}")
else:
    confidence_cols[1].metric("WMAPE", "Unavailable")
    confidence_cols[2].metric("MAE", "Unavailable")

risk_cols = st.columns(3)
risk_cols[0].metric("Demand variability", f"{daily_stddev:.2f} units")
risk_cols[1].metric("Safety stock", number(safety_stock))
risk_cols[2].metric("Risk level", risk_level)

st.write(
    "Forecast risk is driven by demand variability and model error. High standard deviation or WMAPE indicates less confidence in next-period demand estimates, while safety stock is the operational buffer used to protect service levels."
)
