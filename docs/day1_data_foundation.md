# Week 1, Day 1 — Data Foundation and Business Understanding

## Dataset selection

Selected source: `data/raw/online_retail_II.xlsx` (Online Retail II). This is an invoice-line-level retail/e-commerce dataset with two worksheet periods and **1,067,371** data rows:

| Worksheet | Rows | Use |
| --- | ---: | --- |
| `Year 2009-2010` | 525,461 | Historical demand baseline |
| `Year 2010-2011` | 541,910 | Later-period validation and evaluation |

It is suitable for SKU-level demand analysis because every line identifies a product, transaction timestamp, quantity, price, and market. It is not sufficient on its own for operational inventory analysis: stock levels, replenishment lead times, and categories are absent.

## Source profile

The workbook has the same eight columns in both sheets:

| Source field | Meaning | Role in this project |
| --- | --- | --- |
| `Invoice` | Invoice/transaction identifier | Order grain; invoice IDs beginning with `C` should be treated as cancellations/returns during cleaning. |
| `StockCode` | Product code | **SKU** key. |
| `Description` | Product description | Product label; useful for quality checks and provisional category mapping. |
| `Quantity` | Units on the invoice line | Base demand measure; negative values represent returns/corrections. |
| `InvoiceDate` | Transaction date and time | **Date** dimension; aggregate to daily/weekly/monthly demand. |
| `Price` | Unit price | Revenue calculation: `Quantity × Price`. |
| `Customer ID` | Customer identifier | Optional customer/segment analysis; not required for the first forecast. |
| `Country` | Customer market | Geography dimension; use to separate UK and export demand where useful. |

### Canonical analytical fields

| Required field | Day 1 mapping | Status |
| --- | --- | --- |
| Date | `InvoiceDate` | Available |
| SKU | `StockCode` | Available |
| Category | SKU-category master; temporarily derive from `Description` only for exploration | Needs enrichment |
| Sales | `Quantity` (units) and `Quantity × Price` (revenue) | Available |
| Price | `Price` | Available |
| Stock | Daily SKU inventory-on-hand snapshot | Missing — obtain from ERP/WMS/POS inventory ledger |
| Lead Time | SKU/supplier replenishment lead time | Missing — obtain from PO/receiving or supplier master |

## Initial profiling and data-quality rules

- Granularity is one product per invoice line, not one row per order.
- Retain `StockCode` as text; it can contain non-numeric identifiers.
- Parse `InvoiceDate` as a timestamp and create `date`, `week`, and `month` derived fields.
- Separate cancellations/returns (`Invoice` begins with `C`) and negative `Quantity` rows. For a demand forecast, use fulfilled positive sales; retain returns for net-sales reporting.
- Check missing `Description`, `Customer ID`, and `Country` values before any segmentation. `Customer ID` should be optional, not a key required for demand aggregation.
- Identify non-merchandise/adjustment SKUs and zero-price lines before modelling; exclude or flag them by an agreed business rule.
- Deduplicate only exact accidental duplicate invoice lines after confirming they are not legitimate repeated quantities.
- Build a SKU master with `StockCode`, standard description, category, supplier, and replenishment policy before inventory recommendations are produced.

## KPI definitions

| KPI | Definition | Data required | Day 1 availability |
| --- | --- | --- | --- |
| Demand | Units sold by SKU and period; report gross fulfilled demand and optionally net demand after returns. | `InvoiceDate`, `StockCode`, `Quantity`, return flag | Ready after cleaning |
| Inventory turnover | Cost of goods sold ÷ average inventory value for the period. If cost is unavailable, use a clearly labelled sales-value proxy only. | COGS/unit cost, daily/monthly stock value | Not available |
| Stockout rate | SKU-location-periods with zero available stock while demand exists ÷ eligible SKU-location-periods. | Inventory snapshots, demand, location | Not available |
| Forecast accuracy | Use WAPE as primary: `Σ|actual − forecast| ÷ Σ actual`; report bias: `Σ(forecast − actual) ÷ Σ actual`. | Time-split actual demand and forecasts | Defined; available after a forecast is built |

## Business decisions supported

1. Which SKUs have stable, growing, declining, or intermittent demand?
2. How much demand should be expected per SKU over the replenishment horizon?
3. Once stock and lead-time extracts are joined, which SKU-location combinations are at risk of stockout or excess inventory?

## Required enrichment before inventory recommendations

Request these extracts at a shared SKU and date/location grain:

1. **Inventory snapshot:** date, SKU, location, on-hand units, reserved units, on-order units, inventory value/unit cost.
2. **Replenishment/PO history:** PO ID, SKU, supplier, order date, promised date, receipt date, received quantity.
3. **SKU master:** SKU, standard category, brand, supplier, active/discontinued flag, pack size, reorder policy.

These additions unlock stockout rate, turnover, safety stock, reorder point, and lead-time-aware demand planning.
