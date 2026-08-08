from __future__ import annotations

from scripts.validate_forecast_pipeline import validate


def test_validate_reports_status() -> None:
    result = validate()
    assert "status" in result
    assert "forecast_rows" in result
    assert "replenishment_rows" in result
