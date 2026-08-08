"""Validation script for forecast and replenishment data quality."""
from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path(os.getenv("DATA_ROOT", ROOT / "data"))
PROCESSED = Path(os.getenv("PROCESSED_DATA_DIR", DATA_ROOT / "processed"))


def load_csv(filename: str) -> list[dict[str, Any]]:
    path = PROCESSED / filename
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def validate() -> dict[str, Any]:
    forecast_metrics = load_csv("forecast_model_comparison.csv")
    replenishment = load_csv("replenishment_recommendations.csv")

    result = {
        "forecast_rows": len(forecast_metrics),
        "replenishment_rows": len(replenishment),
        "reorder_now_count": sum(1 for row in replenishment if row.get("recommendation_status") == "reorder_now"),
        "has_forecast_data": len(forecast_metrics) > 0,
        "has_replenishment_data": len(replenishment) > 0,
    }

    if result["forecast_rows"] and result["replenishment_rows"]:
        result["status"] = "ok"
    else:
        result["status"] = "warning"
    return result


if __name__ == "__main__":
    print(validate())
