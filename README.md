# Data directory

## Selected dataset

`raw/online_retail_II.xlsx` is the UCI Online Retail II transactional dataset. It is the Day 1 source for demand analysis because it provides invoice-level retail sales across a large set of SKUs and countries.

The workbook contains two chronological sheets and 1,067,371 data rows in total:

| Sheet | Transaction rows |
| --- | ---: |
| `Year 2009-2010` | 525,461 |
| `Year 2010-2011` | 541,910 |

Keep this file immutable. Derived, cleaned, and model-ready datasets should be written to `data/interim/` and `data/processed/` (both excluded from version control when they become large).

## Important scope note

This is a sales-transactions dataset, not an inventory ledger. It contains sales quantity and unit price, but **not** on-hand stock, replenishment orders, supplier lead time, or product categories. Inventory KPIs therefore require a supplementary inventory/replenishment extract and a SKU-category master. See [`../docs/day1_data_foundation.md`](../docs/day1_data_foundation.md) for the field mapping and KPI definitions.
