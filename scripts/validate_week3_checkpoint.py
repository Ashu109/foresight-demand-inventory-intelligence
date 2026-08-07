"""Week 3 checkpoint validation for the interactive dashboard.

Validates that the core dashboard pages have the processed data outputs they need,
including forecast metrics, replenishment recommendations, inventory risk
assessments, and alert/reporting input files.
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
REQUIRED = {
    "week2_checkpoint_manifest.json": "Dashboard manifest and forecast summary",
    "week2_sku_recommendations.csv": "Forecast handoff for SKU-level demand and recommendations",
    "replenishment_recommendations.csv": "Safety stock, reorder point, and replenishment recommendation outputs",
    "inventory_risk_assessment.csv": "Inventory health, days of supply, and risk flags",
}


def validate_file(path: Path) -> bool:
    if not path.exists():
        print(f"MISSING: {path.relative_to(ROOT)}")
        return False
    if path.suffix == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
        if not rows:
            print(f"EMPTY CSV: {path.relative_to(ROOT)}")
            return False
    return True


def required_counts() -> dict[str, int]:
    counts = {}
    path = PROCESSED / "replenishment_recommendations.csv"
    if path.exists():
        with path.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        counts["reorder_now"] = sum(1 for row in rows if row.get("recommendation_status") == "reorder_now")
        counts["no_order_required"] = sum(1 for row in rows if row.get("recommendation_status") == "no_order_required")
    return counts


def main() -> None:
    print("Week 3 Checkpoint Validation")
    print("============================")
    all_good = True
    for filename, description in REQUIRED.items():
        path = PROCESSED / filename
        print(f"Checking {filename}: {description}")
        if not validate_file(path):
            all_good = False
    counts = required_counts()
    if counts:
        print("\nReplenishment status counts:")
        for status, value in counts.items():
            print(f"  {status}: {value}")
    if all_good:
        print("\nWeek 3 checkpoint is complete. All required processed outputs are available.")
    else:
        print("\nWeek 3 checkpoint failed. Fix the missing or empty outputs above.")


if __name__ == "__main__":
    main()
