"""Forecast validation and model comparison page."""

from __future__ import annotations

import streamlit as st

from dashboard.data import load_csv, load_manifest, render_sidebar


st.set_page_config(page_title="Forsight | Forecast Accuracy", page_icon="📈", layout="wide")
render_sidebar()
st.title("Forecast Accuracy")
st.caption("Shared-holdout comparison of demand forecasting models.")

manifest = load_manifest()
comparison = load_csv("forecast_model_comparison.csv")
champion = manifest.get("forecast_accuracy", {}).get("best_model", {})
overall = [row.copy() for row in comparison if row.get("scope") == "overall"]

if not overall:
    st.error("Forecast comparison output is unavailable. Run the forecasting pipeline first.")
    st.stop()

for row in overall:
    row["WMAPE (%)"] = round(float(row["wmape"]) * 100, 2)
    row["mae"] = float(row["mae"])
    row["rmse"] = float(row["rmse"])
overall.sort(key=lambda row: row["WMAPE (%)"])

a, b, c = st.columns(3)
a.metric("Selected model", str(champion.get("model", "gru")).upper())
b.metric("WMAPE", f"{float(champion.get('wmape', 0)):.2%}")
c.metric("Validation observations", f"{int(champion.get('observations', 0)):,}")

st.subheader("Model ranking")
display = [{key: row[key] for key in ("model_family", "model", "observations", "mae", "rmse", "WMAPE (%)")} for row in overall]
st.dataframe(display, use_container_width=True, hide_index=True)

st.info("WMAPE is lower-is-better. Models here are compared only within the overall shared validation scope; late-holdout scores are intentionally not mixed into this ranking.")
