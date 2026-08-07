"""Validate a daily inventory CSV once the inventory extract is available.

Required columns: date, sku_id, location_id, on_hand_quantity, inventory_value
Optional column: unit_cost (used for a value reconciliation check)
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path


REQUIRED_COLUMNS = {"date", "sku_id", "location_id", "on_hand_quantity", "inventory_value"}


def number(value: str) -> Decimal | None:
    try:
        return Decimal(value.strip())
    except (AttributeError, InvalidOperation):
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="CSV inventory snapshot to validate")
    parser.add_argument("--report", type=Path, default=Path("data/processed/inventory_quality_report.json"))
    parser.add_argument("--value-tolerance", type=Decimal, default=Decimal("0.01"))
    args = parser.parse_args()

    counts = Counter()
    bad_keys: set[tuple[str, str, str]] = set()
    with args.source.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        headers = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - headers
        if missing:
            raise ValueError(f"Missing required inventory columns: {', '.join(sorted(missing))}")
        for row in reader:
            counts["rows"] += 1
            key = (row["date"].strip(), row["sku_id"].strip().upper(), row["location_id"].strip().upper())
            try:
                date.fromisoformat(key[0])
            except ValueError:
                counts["invalid_date"] += 1
            if not all(key):
                counts["missing_key"] += 1
            if key in bad_keys:
                counts["duplicate_snapshot_key"] += 1
            bad_keys.add(key)
            on_hand, value = number(row["on_hand_quantity"]), number(row["inventory_value"])
            if on_hand is None:
                counts["invalid_on_hand_quantity"] += 1
            elif on_hand < 0:
                counts["negative_on_hand_quantity"] += 1
            if value is None:
                counts["invalid_inventory_value"] += 1
            elif value < 0:
                counts["negative_inventory_value"] += 1
            if "unit_cost" in headers:
                unit_cost = number(row["unit_cost"])
                if unit_cost is None or unit_cost < 0:
                    counts["invalid_unit_cost"] += 1
                elif on_hand is not None and value is not None and abs(value - on_hand * unit_cost) > args.value_tolerance:
                    counts["inventory_value_mismatch"] += 1

    report = {"source_file": str(args.source), "validation_counts": dict(sorted(counts.items()))}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
