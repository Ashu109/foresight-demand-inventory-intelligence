"""Generate a deterministic demonstration inventory snapshot from forecast SKUs.

This is explicitly simulation data for testing the inventory workflow. It must
be replaced with an ERP/WMS export before any purchase order is issued.
"""

from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"
FORECAST = OUT / "deep_learning_validation_forecasts.csv"
DEFAULT_OUTPUT = ROOT / "data" / "raw" / "inventory_snapshot.csv"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Generated demonstration snapshot")
    parser.add_argument("--seed", type=int, default=14, help="Random seed for reproducible simulation")
    parser.add_argument("--forecast-days", type=int, default=14, help="Recent GRU forecast days used as a demand signal")
    args = parser.parse_args()

    with FORECAST.open(newline="", encoding="utf-8") as handle:
        forecasts = list(csv.DictReader(handle))
    dates = sorted({row["date"] for row in forecasts})[-args.forecast_days:]
    demand: dict[str, dict[str, object]] = defaultdict(lambda: {"values": [], "description": "UNKNOWN"})
    for row in forecasts:
        if row["date"] in dates:
            item = demand[row["sku_id"].strip().upper()]
            item["values"].append(max(0.0, float(row["gru"])))
            item["description"] = row["description"]

    randomizer = random.Random(args.seed)
    rows = []
    for sku, item in sorted(demand.items()):
        daily = sum(item["values"]) / len(item["values"])
        lead_time = randomizer.choice((3, 5, 7, 10, 14))
        # Vary coverage around the lead-time threshold so that the snapshot
        # exercises both reorder-now and no-order-required paths.
        cover_days = randomizer.uniform(0.25, 3.0) * lead_time + randomizer.uniform(0, 7)
        on_hand = round(daily * cover_days)
        on_order = round(daily * randomizer.uniform(0, lead_time)) if randomizer.random() < 0.28 else 0
        reserved = min(on_hand, round(on_hand * randomizer.uniform(0, 0.15)))
        unit_value = max(1.0, randomizer.uniform(2.0, 25.0))
        rows.append({
            "date": dates[-1], "sku_id": sku, "location_id": "SIM-DC-01",
            "on_hand_quantity": on_hand, "inventory_value": f"{on_hand * unit_value:.2f}",
            "on_order_quantity": on_order, "reserved_quantity": reserved,
            "lead_time_days": lead_time, "supplier_id": f"SIM-SUP-{randomizer.randint(1, 12):02d}",
            "category": "UNMAPPED", "data_source": "synthetic_demo",
            "description": item["description"],
        })
    fields = ["date", "sku_id", "location_id", "on_hand_quantity", "inventory_value", "on_order_quantity", "reserved_quantity", "lead_time_days", "supplier_id", "category", "data_source", "description"]
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows):,} synthetic demonstration inventory rows to {args.output}.")


if __name__ == "__main__":
    main()
