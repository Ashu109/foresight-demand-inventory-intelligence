from __future__ import annotations

from monitoring.metrics import MetricsCollector


def test_metrics_collector_writes_files(tmp_path) -> None:
    collector = MetricsCollector(output_dir=str(tmp_path))
    collector.record_health("ok", "startup")
    collector.record_forecast_metrics({"status": "healthy"})
    collector.record_data_drift({"drift_score": 0.1})

    assert (tmp_path / "health.json").exists()
    assert (tmp_path / "forecast_metrics.json").exists()
    assert (tmp_path / "data_drift.json").exists()
