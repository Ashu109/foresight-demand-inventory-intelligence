"""Data access and shared Streamlit UI for the dashboard."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]


def get_data_root() -> Path:
    return Path(os.getenv("DATA_ROOT", str(ROOT / "data"))).resolve()


def get_processed_dir() -> Path:
    return Path(os.getenv("PROCESSED_DATA_DIR", str(get_data_root() / "processed"))).resolve()


def get_raw_dir() -> Path:
    return Path(os.getenv("RAW_DATA_DIR", str(get_data_root() / "raw"))).resolve()


OUT = get_processed_dir()
RAW = get_raw_dir()


@st.cache_data(show_spinner=False)
def load_csv(filename: str) -> list[dict[str, str]]:
    path = get_processed_dir() / filename
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


@st.cache_data(show_spinner=False)
def load_manifest() -> dict:
    path = get_processed_dir() / "week2_checkpoint_manifest.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


@st.cache_data(show_spinner=False)
def is_synthetic_inventory() -> bool:
    path = get_raw_dir() / "inventory_snapshot.csv"
    if not path.exists():
        return False
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return any(row.get("data_source") == "synthetic_demo" for row in csv.DictReader(handle))


def _sidebar_page_link(page: str, label: str, icon: str | None = None) -> None:
    try:
        st.sidebar.page_link(page, label=label, icon=icon)
    except KeyError:
        st.sidebar.write(label)


def render_sidebar() -> None:
    st.sidebar.title("Forsight")
    st.sidebar.caption("Demand & Inventory Intelligence")
    _sidebar_page_link("app.py", label="Executive overview", icon="🏠")
    _sidebar_page_link("pages/1_Forecast_Accuracy.py", label="Forecast accuracy", icon="📈")
    _sidebar_page_link("pages/3_Demand_Intelligence.py", label="Demand intelligence", icon="🧠")
    _sidebar_page_link("pages/2_Replenishment_Actions.py", label="Replenishment actions", icon="📦")
    _sidebar_page_link("pages/4_Inventory_Intelligence.py", label="Inventory intelligence", icon="🏭")
    _sidebar_page_link("pages/5_WhatIf_Analysis.py", label="What-If analysis", icon="🔍")
    _sidebar_page_link("pages/6_Alerts_Reporting.py", label="Alerts & reporting", icon="🚨")
    st.sidebar.divider()
    if is_synthetic_inventory():
        st.sidebar.warning("Demo inventory is active. Do not create purchase orders from these values.")
    else:
        st.sidebar.success("Inventory snapshot is marked as operational data.")
    if st.sidebar.button("Refresh data"):
        st.cache_data.clear()
        st.rerun()


def number(value: float | int) -> str:
    return f"{value:,.0f}"
