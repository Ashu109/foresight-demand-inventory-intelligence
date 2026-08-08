"""Day 15 Streamlit dashboard entry point updated for production structure."""

from __future__ import annotations

import streamlit as st
from utils import get_logger
from config.settings import load_config

from dashboard.data import is_synthetic_inventory, load_csv, load_manifest, number, render_sidebar
from monitoring.metrics import MetricsCollector
from utils.errors import ApplicationError


logger = get_logger("app")
config = load_config()
metrics = MetricsCollector()


def pd_to_numeric_sum(frame, column: str) -> int:
    return int(sum(float(row.get(column) or 0) for row in frame))


def render_dashboard() -> None:
    st.set_page_config(page_title="Forsight | Decision Intelligence", page_icon="📊", layout="wide")
    render_sidebar()

    st.title("Decision Intelligence Overview")
    st.caption("Forecast accuracy and replenishment priorities in one operational view.")

    manifest = load_manifest()
    recommendations = load_csv("week2_sku_recommendations.csv")
    replenishment = load_csv("replenishment_recommendations.csv")
    champion = manifest.get("forecast_accuracy", {}).get("best_model", {})
    reorder_now = [row for row in replenishment if row.get("recommendation_status") == "reorder_now"]
    reorder_units = pd_to_numeric_sum(reorder_now, "recommended_reorder_quantity")

    if is_synthetic_inventory():
        st.warning(
            "This dashboard currently uses synthetic demonstration inventory. "
            "Forecast metrics are real project outputs, but reorder quantities "
            "are not purchase-order ready."
        )

    left, mid, right, final = st.columns(4)
    left.metric("Forecasted SKUs", number(len(recommendations)))
    mid.metric("Forecast champion", str(champion.get("model", "Unavailable")).upper())
    right.metric("Champion WMAPE", f"{float(champion.get('wmape', 0)):.2%}" if champion else "—")
    final.metric("Reorder now", number(len(reorder_now)), f"{number(reorder_units)} units")

    st.subheader("Recommended replenishment actions")
    if not replenishment:
        st.info("Run the Day 13 replenishment script to populate inventory actions.")
    else:
        status_counts = {}
        for row in replenishment:
            status = row["recommendation_status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        st.dataframe([
            {"status": status, "SKUs": count} for status, count in status_counts.items()
        ], use_container_width=True, hide_index=True)
        columns = [
            "sku_id",
            "description",
            "recommended_reorder_quantity",
            "supplier_lead_time_days",
            "reorder_point_units",
        ]
        action_table = sorted(
            reorder_now,
            key=lambda row: float(row["recommended_reorder_quantity"]),
            reverse=True,
        )[:15]
        action_table = [{column: row[column] for column in columns} for row in action_table]
        st.dataframe(action_table, use_container_width=True, hide_index=True)

    st.subheader("Data and operational status")
    engine_status = manifest.get("inventory_optimization_engine", {}).get("status", "unavailable")
    st.write(
        f"Checkpoint: **{manifest.get('status', 'unavailable')}** · Inventory engine: **{engine_status}**"
    )
    st.caption("Use the sidebar to inspect forecast validation and the full replenishment action queue.")


def main() -> None:
    try:
        logger.info("Starting dashboard (env=%s)", config.get("app", {}).get("env", "unknown"))
        metrics.record_health("ok", "dashboard started")
        metrics.record_forecast_metrics({
            "status": "available",
            "models": ["baseline", "ml", "deep_learning"],
        })
        metrics.record_data_drift({
            "status": "monitoring",
            "drift_score": 0.0,
        })
        render_dashboard()
    except ApplicationError as exc:
        logger.error("Application error: %s", exc)
        st.error("An application error occurred. Check logs for details.")
    except Exception:
        logger.exception("Unhandled exception in dashboard")
        st.error("An unexpected error occurred. See logs for details.")


if __name__ == "__main__":
    main()
