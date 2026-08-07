"""Lightweight metrics helpers for app health and forecast monitoring."""
from __future__ import annotations

import os
import time
from collections import Counter
from pathlib import Path
from typing import Any


class MetricsCollector:
    def __init__(self, output_dir: str | None = None) -> None:
        self.output_dir = Path(output_dir or os.getenv("METRICS_DIR", "./monitoring/output"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._start_time = time.time()

    def record_health(self, status: str, details: str = "") -> None:
        payload = {
            "timestamp": time.time(),
            "status": status,
            "details": details,
        }
        self._write_json("health.json", payload)

    def record_forecast_metrics(self, metrics: dict[str, Any]) -> None:
        self._write_json("forecast_metrics.json", metrics)

    def record_data_drift(self, drift_metrics: dict[str, Any]) -> None:
        self._write_json("data_drift.json", drift_metrics)

    def _write_json(self, filename: str, payload: dict[str, Any]) -> None:
        path = self.output_dir / filename
        path.write_text(str(payload).replace("'", '"'), encoding="utf-8")

    def uptime_seconds(self) -> float:
        return time.time() - self._start_time
