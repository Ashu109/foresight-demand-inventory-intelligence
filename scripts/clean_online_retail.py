"""Clean and validate the Online Retail II workbook without external packages.

Usage:
    python -S scripts/clean_online_retail.py

Outputs are written to data/processed/.  The raw workbook is never modified.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import zipfile
from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree as ET


NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
SOURCE_COLUMNS = [
    "Invoice", "StockCode", "Description", "Quantity",
    "InvoiceDate", "Price", "Customer ID", "Country",
]
OUTPUT_COLUMNS = [
    "invoice_id", "sku_id", "description", "category", "quantity",
    "invoice_date", "unit_price", "customer_id", "country", "is_return",
    "line_revenue", "quality_flags",
]


def text_from_shared_item(item: ET.Element) -> str:
    return "".join(node.text or "" for node in item.iter(f"{NS}t"))


def load_shared_strings(book: zipfile.ZipFile) -> list[str]:
    with book.open("xl/sharedStrings.xml") as stream:
        root = ET.parse(stream).getroot()
    return [text_from_shared_item(item) for item in root.findall(f"{NS}si")]


def cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    value = cell.findtext(f"{NS}v", default="")
    cell_type = cell.get("t")
    if cell_type == "s" and value:
        return shared_strings[int(value)]
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.iter(f"{NS}t"))
    return value


def excel_datetime(value: str) -> str:
    try:
        serial = float(value)
    except ValueError:
        return ""
    # Excel's 1900-date system includes its historical leap-year bug.
    return (datetime(1899, 12, 30) + timedelta(days=serial)).isoformat(sep=" ", timespec="seconds")


def normalized_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def decimal_value(value: str) -> Decimal | None:
    try:
        return Decimal(normalized_text(value))
    except (InvalidOperation, ValueError):
        return None


def source_rows(book: zipfile.ZipFile, shared_strings: list[str]):
    sheets = sorted(
        entry.filename for entry in book.infolist()
        if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", entry.filename)
    )
    for sheet in sheets:
        with book.open(sheet) as stream:
            for _, row in ET.iterparse(stream, events=("end",)):
                if row.tag != f"{NS}row":
                    continue
                values: dict[str, str] = {}
                for cell in row.findall(f"{NS}c"):
                    column = re.match(r"[A-Z]+", cell.get("r", ""))
                    if column:
                        values[column.group(0)] = cell_value(cell, shared_strings)
                row.clear()
                yield sheet, values


def run(source: Path, output_dir: Path, max_price: Decimal, max_abs_quantity: Decimal) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    clean_path = output_dir / "clean_sales_transactions.csv"
    reject_path = output_dir / "rejected_sales_transactions.csv"
    report_path = output_dir / "data_quality_report.json"
    counters = Counter()
    flags = Counter()
    seen: set[tuple[str, ...]] = set()

    with zipfile.ZipFile(source) as book:
        shared_strings = load_shared_strings(book)
        with clean_path.open("w", newline="", encoding="utf-8") as clean_file, \
             reject_path.open("w", newline="", encoding="utf-8") as reject_file:
            clean_writer = csv.DictWriter(clean_file, fieldnames=OUTPUT_COLUMNS)
            reject_writer = csv.DictWriter(reject_file, fieldnames=SOURCE_COLUMNS + ["rejection_reason"])
            clean_writer.writeheader()
            reject_writer.writeheader()
            header_checked: set[str] = set()

            for sheet, cells in source_rows(book, shared_strings):
                raw = {column: cells.get(chr(65 + index), "") for index, column in enumerate(SOURCE_COLUMNS)}
                if sheet not in header_checked:
                    actual = [raw[column] for column in SOURCE_COLUMNS]
                    if actual != SOURCE_COLUMNS:
                        raise ValueError(f"Unexpected header in {sheet}: {actual}")
                    header_checked.add(sheet)
                    continue

                counters["input_rows"] += 1
                invoice = normalized_text(raw["Invoice"]).upper()
                sku = normalized_text(raw["StockCode"]).upper()
                description = normalized_text(raw["Description"])
                country = normalized_text(raw["Country"]).upper()
                customer = normalized_text(raw["Customer ID"])
                quantity = decimal_value(raw["Quantity"])
                price = decimal_value(raw["Price"])
                invoice_date = excel_datetime(raw["InvoiceDate"])

                rejection_reasons = []
                if not invoice:
                    rejection_reasons.append("missing_invoice_id")
                if not sku:
                    rejection_reasons.append("missing_sku_id")
                if not invoice_date:
                    rejection_reasons.append("invalid_invoice_date")
                if quantity is None:
                    rejection_reasons.append("invalid_quantity")
                elif quantity == 0:
                    rejection_reasons.append("zero_quantity")
                if price is None or price < 0:
                    rejection_reasons.append("invalid_unit_price")
                if rejection_reasons:
                    counters["rejected_rows"] += 1
                    for reason in rejection_reasons:
                        counters[f"rejected_{reason}"] += 1
                    raw["rejection_reason"] = ";".join(rejection_reasons)
                    reject_writer.writerow(raw)
                    continue

                duplicate_key = tuple(raw[column] for column in SOURCE_COLUMNS)
                if duplicate_key in seen:
                    counters["exact_duplicates_removed"] += 1
                    continue
                seen.add(duplicate_key)

                row_flags = []
                if not description:
                    description = "UNKNOWN"
                    row_flags.append("missing_description")
                if not country:
                    country = "UNKNOWN"
                    row_flags.append("missing_country")
                if not customer:
                    row_flags.append("missing_customer_id")
                if price == 0:
                    row_flags.append("zero_unit_price")
                if price > max_price:
                    row_flags.append("high_unit_price")
                if abs(quantity) > max_abs_quantity:
                    row_flags.append("high_absolute_quantity")

                is_return = invoice.startswith("C") or quantity < 0
                if is_return:
                    row_flags.append("return_or_cancellation")
                    counters["return_rows"] += 1
                for flag in row_flags:
                    flags[flag] += 1

                clean_writer.writerow({
                    "invoice_id": invoice,
                    "sku_id": sku,
                    "description": description,
                    "category": "UNMAPPED",
                    "quantity": str(quantity),
                    "invoice_date": invoice_date,
                    "unit_price": str(price),
                    "customer_id": customer,
                    "country": country,
                    "is_return": str(is_return).lower(),
                    "line_revenue": str(quantity * price),
                    "quality_flags": ";".join(row_flags),
                })
                counters["accepted_rows"] += 1

    report = {
        "source_file": str(source),
        "rules_version": "1.0",
        "input_rows": counters["input_rows"],
        "accepted_rows": counters["accepted_rows"],
        "rejected_rows": counters["rejected_rows"],
        "exact_duplicates_removed": counters["exact_duplicates_removed"],
        "return_rows": counters["return_rows"],
        "rejection_counts": {
            key.removeprefix("rejected_"): value
            for key, value in sorted(counters.items())
            if key.startswith("rejected_") and key != "rejected_rows"
        },
        "quality_flag_counts": dict(sorted(flags.items())),
        "thresholds": {"max_unit_price": str(max_price), "max_absolute_quantity": str(max_abs_quantity)},
        "inventory_validation": "Not run: this workbook has no inventory value/on-hand fields.",
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("data/raw/online_retail_II.xlsx"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--max-unit-price", type=Decimal, default=Decimal("10000"))
    parser.add_argument("--max-absolute-quantity", type=Decimal, default=Decimal("100000"))
    args = parser.parse_args()
    report = run(args.source, args.output_dir, args.max_unit_price, args.max_absolute_quantity)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
