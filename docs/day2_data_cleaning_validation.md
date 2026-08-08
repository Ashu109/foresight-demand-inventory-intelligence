# Week 1, Day 2 — Data Cleaning and Validation

## Implemented workflow

Run the following from the repository root:

```powershell
python -S scripts/clean_online_retail.py
```

The job does not alter the raw workbook. It writes these reproducible outputs to `data/processed/`:

| File | Purpose |
| --- | --- |
| `clean_sales_transactions.csv` | Accepted, standardized transaction lines with flags. |
| `rejected_sales_transactions.csv` | Rows excluded from the analytical dataset and their reasons. |
| `data_quality_report.json` | Automated row counts, validation results, and thresholds. |

## Cleaning rules

| Area | Rule | Result |
| --- | --- | --- |
| Missing required identifiers | Reject missing invoice or SKU. | Kept in reject file with a reason. |
| Missing/invalid date | Reject blank or invalid Excel date values. | Kept in reject file. |
| Quantity | Reject missing, non-numeric, or zero quantities. Retain negative quantities as returns. | Forecasts can filter `is_return = false`. |
| Unit price | Reject missing, non-numeric, or negative prices. Retain zero prices with a `zero_unit_price` flag. | Prevents invalid revenue. |
| Duplicates | Remove only exact duplicate source lines. | Avoids silently removing valid repeated purchases. |
| SKU | Trim whitespace and convert to uppercase text. | Preserves mixed alphanumeric identifiers. |
| Dates | Convert Excel serial dates to ISO `YYYY-MM-DD HH:MM:SS`. | Consistent time grain. |
| Description/country/customer | Normalize whitespace; uppercase country; label missing description/country as `UNKNOWN`; flag missing customer IDs. | Does not discard valid sales merely because optional fields are absent. |
| Categories | Set to `UNMAPPED`. | A SKU-category master is required before categories can be standardized. |

## Automated quality checks

The pipeline verifies the expected source header on every worksheet and records:

- row-level reject reasons;
- exact duplicate count;
- return/cancellation rows (`Invoice` starts with `C` or quantity is negative);
- missing optional dimensions;
- zero and unusually high prices;
- unusually high absolute quantities.

The default review thresholds are unit price above `10,000` and absolute quantity above `100,000`. They create flags rather than deleting data; tune them after reviewing the quality report with business owners.

## First-run validation result

The initial run processed 1,067,371 source rows. It accepted 1,033,031 rows, rejected 5 rows with invalid unit prices, and removed 34,335 exact duplicates. It flagged 22,497 return/cancellation rows, 235,146 rows without a customer ID, 4,275 without a description, 6,014 zero-price rows, and 23 rows above the high-price review threshold. These are review signals, not automatic business corrections.

## Inventory validation

The selected source does not include inventory values or on-hand quantities, so inventory validation is deliberately reported as **not run**. When the inventory snapshot described in Day 1 is available as CSV, run:

```powershell
python -S scripts/validate_inventory_snapshot.py path/to/inventory_snapshot.csv
```

It requires `date`, `sku_id`, `location_id`, `on_hand_quantity`, and `inventory_value`; it also uses `unit_cost` when supplied. It checks valid/non-duplicate date-SKU-location keys, invalid or negative on-hand/inventory values, invalid cost, and mismatches between inventory value and `on_hand_quantity × unit_cost`.
