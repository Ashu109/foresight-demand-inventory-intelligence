"""Small monitoring dashboard script for local use."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "monitoring" / "output"
OUT.mkdir(parents=True, exist_ok=True)


def summarize() -> dict:
    payload = {}
    for filename in ["health.json", "forecast_metrics.json", "data_drift.json"]:
        path = OUT / filename
        if path.exists():
            payload[filename] = json.loads(path.read_text(encoding="utf-8"))
    return payload


if __name__ == "__main__":
    print(json.dumps(summarize(), indent=2))
