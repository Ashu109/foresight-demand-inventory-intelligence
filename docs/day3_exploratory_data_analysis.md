# Week 1, Day 3 — Exploratory Data Analysis

## Scope and method

This analysis uses `data/processed/clean_sales_transactions.csv` and covers **2009-12-01 through 2011-12-09**. Demand is defined as the quantity on positive, non-return sales lines; return/cancellation lines are excluded because they are not future demand. Revenue is the corresponding positive-line sales revenue. The source contains **1,033,031** cleaned lines, of which **1,010,534** are included in demand.

The dataset has no SKU-category master: all demand is assigned to the cleanup placeholder `UNMAPPED`. Category performance is therefore available as a completeness check only, not as a product-family comparison. Add a validated SKU-category master before using category-level results for planning.

## Demand distribution

- **4,813 SKUs** generated **11,455,907 units** and **20,476,260.45** in positive-line revenue.
- SKU demand is strongly long-tailed: median **652** units per SKU; 75th percentile **2,182**; 95th percentile **10,078**.
- The top 10 SKUs represent **7.4%** of all units. Prioritize these products for forecast accuracy and service-level review.

## Best-performing products

Ranked by demand units:

| SKU | Description | Demand units | Revenue | Active days |
| --- | --- | ---: | ---: | ---: |
| 84077 | WORLD WAR 2 GLIDERS ASSTD DESIGNS | 106,250 | 24,445.61 | 470 |
| 85123A | CREAM HANGING HEART T-LIGHT HOLDER | 98,724 | 261,168.73 | 603 |
| 85099B | JUMBO BAG RED RETROSPOT | 97,183 | 182,680.98 | 590 |
| 21212 | PACK OF 72 RETROSPOT CAKE CASES | 94,884 | 51,825.15 | 594 |
| 22197 | POPCORN HOLDER | 88,993 | 79,520.20 | 563 |
| 23843 | PAPER CRAFT , LITTLE BIRDIE | 80,995 | 168,469.60 | 1 |
| 84879 | ASSORTED COLOUR BIRD ORNAMENT | 80,090 | 129,324.49 | 582 |
| 23166 | MEDIUM CERAMIC TOP STORAGE JAR | 78,033 | 81,700.92 | 125 |
| 17003 | BROCADE RING PURSE | 70,379 | 14,766.42 | 302 |
| 21977 | PACK OF 60 PINK PAISLEY CAKE CASES | 56,061 | 28,081.73 | 565 |

Ranked by positive-line revenue:

| SKU | Description | Demand units | Revenue | Active days |
| --- | --- | ---: | ---: | ---: |
| M | Manual | 9,641 | 339,241.29 | 381 |
| 22423 | REGENCY CAKESTAND 3 TIER | 26,495 | 330,590.32 | 514 |
| DOT | DOTCOM POSTAGE | 2,920 | 309,854.11 | 441 |
| 85123A | CREAM HANGING HEART T-LIGHT HOLDER | 98,724 | 261,168.73 | 603 |
| 85099B | JUMBO BAG RED RETROSPOT | 97,183 | 182,680.98 | 590 |
| 23843 | PAPER CRAFT , LITTLE BIRDIE | 80,995 | 168,469.60 | 1 |
| 47566 | PARTY BUNTING | 28,248 | 148,318.28 | 542 |
| 84879 | ASSORTED COLOUR BIRD ORNAMENT | 80,090 | 129,324.49 | 582 |
| POST | POSTAGE | 10,313 | 125,682.42 | 514 |
| 22086 | PAPER CHAIN KIT 50'S CHRISTMAS | 35,113 | 117,760.29 | 307 |

## Lowest-demand established products

To avoid treating a one-off or newly introduced SKU as a poor performer, this list includes only SKUs active on at least 30 distinct demand days. These are candidates for assortment, pricing, or data-quality review—not automatic delist recommendations.

| SKU | Description | Demand units | Revenue | Active days |
| --- | --- | ---: | ---: | ---: |
| 90022 | EDWARDIAN DROP EARRINGS JET BLACK | 37 | 139.67 | 30 |
| 90018B | GOLD M.O.P ORBIT DROP EARRINGS | 39 | 164.62 | 31 |
| 90019C | SILVER BLACK ORBIT BRACELET | 40 | 213.38 | 32 |
| 47581B | FAIRY CAKE WICKER PICNIC BASKET | 46 | 753.77 | 33 |
| 90133 | TEAL/FUSCHIA COL BEAD NECKLACE | 47 | 236.46 | 33 |
| 22761 | CHEST 7 DRAWER MA CAMPAGNE | 48 | 1,182.78 | 34 |
| 22827 | RUSTIC SEVENTEEN DRAWER SIDEBOARD | 50 | 7,150.00 | 32 |
| 90073 | VINTAGE ENAMEL & CRYSTAL EARRINGS | 50 | 250.34 | 34 |
| 90081C | LILY BROOCH OLIVE COLOUR | 50 | 250.47 | 36 |
| 90174 | BUTTERFLY HAIR BAND | 50 | 126.12 | 32 |

## Daily, weekly, and monthly demand patterns

The daily, week-start (Monday), and calendar-month series are written to `data/processed/eda_demand_time_series.csv` for charting and forecasting. The highest-volume periods are below.

### Highest-demand days

| Period start | Demand units | Revenue | Sales lines |
| --- | ---: | ---: | ---: |
| 2010-09-27 | 126,137 | 118,838.47 | 2,253 |
| 2010-08-09 | 100,344 | 31,692.27 | 886 |
| 2010-02-15 | 96,823 | 42,469.53 | 876 |
| 2011-12-09 | 93,950 | 200,918.98 | 1,619 |
| 2011-01-18 | 82,964 | 95,947.73 | 1,421 |
| 2010-03-17 | 78,901 | 30,719.54 | 1,261 |
| 2010-01-21 | 72,905 | 27,359.23 | 1,147 |
| 2010-08-05 | 62,437 | 24,406.15 | 1,303 |
| 2010-11-04 | 60,297 | 89,585.63 | 3,540 |
| 2010-03-23 | 54,452 | 56,400.48 | 1,274 |

### Highest-demand weeks

| Period start | Demand units | Revenue | Sales lines |
| --- | ---: | ---: | ---: |
| 2011-12-05 | 246,397 | 503,785.75 | 17,296 |
| 2010-09-27 | 239,221 | 332,442.17 | 12,825 |
| 2011-11-14 | 186,567 | 387,064.65 | 20,461 |
| 2011-11-07 | 184,683 | 368,996.32 | 18,729 |
| 2010-08-09 | 183,357 | 179,584.70 | 7,870 |

### Highest-demand months

| Period start | Demand units | Revenue | Sales lines |
| --- | ---: | ---: | ---: |
| 2011-11 | 768,468 | 1,503,866.78 | 82,133 |
| 2010-11 | 730,417 | 1,464,293.14 | 75,167 |
| 2011-10 | 626,373 | 1,151,263.73 | 58,629 |
| 2010-10 | 622,277 | 1,161,902.22 | 57,093 |
| 2010-09 | 592,615 | 921,696.99 | 40,707 |
| 2011-09 | 574,169 | 1,056,435.19 | 48,962 |
| 2010-03 | 530,314 | 830,915.26 | 39,954 |
| 2010-08 | 521,762 | 695,251.91 | 32,275 |
| 2009-12 | 444,341 | 822,483.95 | 43,619 |
| 2011-08 | 424,264 | 757,841.38 | 34,345 |
| 2010-05 | 424,009 | 657,705.50 | 33,558 |
| 2010-06 | 413,723 | 749,537.31 | 38,539 |

### Recurring seasonality

Average demand is calculated per observed selling day, so that calendar closures do not make a weekday or month look artificially weak. The historical mix is strongest on **Thursday** (23,328 units per observed day) and in calendar month **11** (28,825 units per observed day). Treat the partial final month (December 2011 ends on the 9th) with care.

| Weekday | Observed demand days | Total units | Avg. units / observed day |
| --- | ---: | ---: | ---: |
| Thursday | 103 | 2,402,814 | 23,328 |
| Monday | 94 | 2,066,882 | 21,988 |
| Tuesday | 104 | 2,188,022 | 21,039 |
| Wednesday | 104 | 2,022,286 | 19,445 |
| Friday | 99 | 1,743,434 | 17,610 |
| Sunday | 99 | 1,027,350 | 10,377 |
| Saturday | 1 | 5,119 | 5,119 |

| Month | Observed demand days | Total units | Avg. units / observed day |
| --- | ---: | ---: | ---: |
| 11 | 52 | 1,498,885 | 28,825 |
| 10 | 52 | 1,248,650 | 24,012 |
| 12 | 49 | 1,119,852 | 22,854 |
| 09 | 52 | 1,166,784 | 22,438 |
| 08 | 52 | 946,026 | 18,193 |
| 03 | 54 | 914,337 | 16,932 |
| 05 | 49 | 822,695 | 16,790 |
| 01 | 48 | 792,264 | 16,506 |
| 04 | 44 | 697,061 | 15,842 |
| 06 | 52 | 807,356 | 15,526 |
| 07 | 52 | 764,063 | 14,694 |
| 02 | 48 | 677,934 | 14,124 |

## Unusual demand spikes

`data/processed/eda_demand_outliers.csv` contains **42,530** daily SKU spikes. A spike is a SKU's active-day quantity above Q3 + 1.5 × IQR, evaluated only for SKUs with at least eight active sales days. Where IQR is zero, the threshold is the greater of twice the usual quantity and usual quantity + 20 units. This is a review queue, not proof of an error: validate campaigns, holidays, bulk orders, and data-entry issues before changing forecasts.

Top 20 spikes by units:

| Date | SKU | Description | Units | Typical active day | Spike threshold | Multiple of median |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 2011-01-18 | 23166 | MEDIUM CERAMIC TOP STORAGE JAR | 74,215 | 14.00 | 63.50 | 5301.07× |
| 2010-02-15 | 37410 | BLACK AND WHITE PAISLEY FLOWER MUG | 19,152 | 12.00 | 71.12 | 1596.00× |
| 2010-03-17 | 21091 | SET/6 WOODLAND PAPER PLATES | 12,960 | 12.00 | 27.38 | 1080.00× |
| 2010-03-17 | 21099 | SET/6 STRAWBERRY PAPER CUPS | 12,960 | 5.00 | 27.00 | 2592.00× |
| 2010-03-17 | 21085 | SET/6 WOODLAND PAPER CUPS | 12,744 | 7.00 | 27.00 | 1820.57× |
| 2011-11-25 | 84826 | ASSTD DESIGN 3D PAPER STICKERS | 12,540 | 60.00 | 147.00 | 209.00× |
| 2010-03-17 | 21092 | SET/6 STRAWBERRY PAPER PLATES | 12,480 | 8.50 | 45.00 | 1468.24× |
| 2010-09-03 | 17003 | BROCADE RING PURSE | 11,124 | 37.00 | 221.00 | 300.65× |
| 2010-03-23 | 21984 | PACK OF 12 PINK PAISLEY TISSUES | 11,000 | 14.50 | 86.12 | 758.62× |
| 2010-03-23 | 21982 | PACK OF 12 SUKI TISSUES | 10,800 | 24.00 | 111.00 | 450.00× |
| 2010-05-10 | 84016 | FLAG OF ST GEORGE CAR FLAG | 10,201 | 21.00 | 72.00 | 485.76× |
| 2010-03-23 | 21981 | PACK OF 12 WOODLAND TISSUES | 10,048 | 24.00 | 115.50 | 418.67× |
| 2010-03-23 | 21980 | PACK OF 12 RED RETROSPOT TISSUES | 10,000 | 25.00 | 104.50 | 400.00× |
| 2010-08-05 | 22759 | check | 9,600 | 15.00 | 84.00 | 640.00× |
| 2010-11-04 | 84347 | ROTATING SILVER ANGELS T-LIGHT HLDR | 9,480 | 24.00 | 182.25 | 395.00× |
| 2010-01-21 | 20993 | JAZZ HEARTS MEMO PAD | 9,312 | 12.00 | 116.62 | 776.00× |
| 2010-08-09 | 21088 | SET/6 FRUIT SALAD PAPER CUPS | 7,128 | 10.00 | 55.50 | 712.80× |
| 2010-09-27 | 21088 | SET/6 FRUIT SALAD PAPER CUPS | 7,128 | 10.00 | 55.50 | 712.80× |
| 2010-08-09 | 21096 | SET/6 FRUIT SALAD PAPER PLATES | 7,008 | 6.00 | 35.50 | 1168.00× |
| 2010-09-27 | 21096 | SET/6 FRUIT SALAD PAPER PLATES | 7,008 | 6.00 | 35.50 | 1168.00× |

## Reproducibility

Run from the repository root:

```powershell
python -S scripts/analyze_demand_eda.py
```

Generated outputs:

- `data/processed/eda_sku_performance.csv`
- `data/processed/eda_category_performance.csv`
- `data/processed/eda_demand_time_series.csv`
- `data/processed/eda_demand_seasonality.csv`
- `data/processed/eda_demand_outliers.csv`
