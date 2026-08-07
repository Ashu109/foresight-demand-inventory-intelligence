# Week 1, Day 4 — Time-Series Analysis

## Scope and construction

This analysis aggregates the cleaned sales data from **2009-12-01 to 2011-12-09** into SKU-day and SKU-week demand series. Demand is positive, non-return quantity; all missing SKU-week combinations are explicitly represented as zero. The weekly calendar spans **106 weeks**; the first and final partial weeks are excluded from diagnostics, leaving **104 comparable weeks**.

## Outputs

- `data/processed/ts_sku_daily_demand.csv` — sparse SKU-day demand (only days with demand).
- `data/processed/ts_sku_weekly_demand.csv` — complete SKU-week panel including zero-demand weeks.
- `data/processed/ts_sku_diagnostics.csv` — trend, variability, intermittency, and lag-1 autocorrelation per SKU.
- `data/processed/ts_weekly_decomposition.csv` — additive decomposition of the all-SKU series and the 10 highest-volume SKUs.

## Aggregate trend and seasonality

Across the comparable weeks, total weekly demand averages **106,370 units** (standard deviation **40,814**). The portfolio's lag-1 autocorrelation is **0.528**, indicating that adjacent weeks have meaningful persistence, though promotion and bulk-order spikes remain material.

The additive decomposition uses a centered 13-week moving average for local trend. Seasonal components are calculated by ISO week after removing that trend and are normalized to average zero. It is produced for the full portfolio and the 10 highest-volume SKUs. This is exploratory—not a substitute for a forecasting model—and the boundary weeks lack a centered trend estimate.

Highest positive seasonal components:

| ISO week | Additive seasonal component (units) |
| ---: | ---: |
| 3 | 56,403 |
| 39 | 45,471 |
| 46 | 42,633 |
| 48 | 42,425 |
| 7 | 38,179 |
| 32 | 37,532 |
| 11 | 33,424 |
| 45 | 32,988 |

## SKU trend diagnostics

The growth and decline lists require at least 52 positive-demand weeks and mean weekly demand of at least 50 units. The growth list also requires at least 20 units per week in the initial window so tiny launch-period baselines do not create misleading percentage growth. Trend compares the most recent 13 full weeks with the first 13 full weeks, so it should be read alongside seasonality and business events.

### Strongest recent growth

| SKU | Description | Mean weekly units | 13-week change |
| --- | --- | ---: | ---: |
| 22065 | CHRISTMAS PUDDING TRINKET POT | 78.05 | 2166.42 |
| 22086 | PAPER CHAIN KIT 50'S CHRISTMAS | 303.48 | 950.04 |
| 21703 | BAG 125g SWIRLY MARBLES | 137.35 | 858.24 |
| 79321 | CHILLI LIGHTS | 149.94 | 673.59 |
| POST | POSTAGE | 97.97 | 537.89 |
| 22197 | POPCORN HOLDER | 806.35 | 535.33 |
| 85049A | TRADITIONAL CHRISTMAS RIBBONS | 61.43 | 439.81 |
| 22130 | PARTY CONE CHRISTMAS DECORATION | 89.79 | 414.84 |
| 21108 | FAIRY CAKE FLANNEL ASSORTED COLOUR | 121.88 | 402.53 |
| 21917 | SET 12 KIDS WHITE CHALK STICKS | 75.19 | 395.80 |

### Sharpest recent decline

| SKU | Description | Mean weekly units | 13-week change |
| --- | --- | ---: | ---: |
| 10002 | INFLATABLE POLITICAL GLOBE | 83.76 | -100.00 |
| 17096 | ASSORTED LAQUERED INCENSE HOLDERS | 59.99 | -100.00 |
| 21082 | SET/20 FRUIT SALAD PAPER NAPKINS | 68.99 | -100.00 |
| 21870 | I CAN ONLY PLEASE ONE PERSON MUG | 57.85 | -100.00 |
| 22198 | LARGE POPCORN HOLDER | 68.29 | -100.00 |
| 84520B | PACK 20 ENGLISH ROSE PAPER NAPKINS | 71.50 | -100.00 |
| 79000 | MOROCCAN TEA GLASS | 120.75 | -99.34 |
| 22084 | PAPER CHAIN KIT EMPIRE | 84.24 | -98.45 |
| 22243 | 5 HOOK HANGER RED MAGIC TOADSTOOL | 73.83 | -97.50 |
| 22432 | WATERING CAN PINK BUNNY | 73.81 | -97.41 |

## Demand variability and autocorrelation

Coefficient of variation (CV) is standard deviation divided by mean weekly demand; higher values indicate greater relative variability. Average demand interval (ADI) is total weeks divided by positive-demand weeks; it quantifies intermittency. Lag-1 autocorrelation measures similarity to the immediately preceding week.

### Most variable eligible SKUs

| SKU | Description | CV | ADI weeks | Lag-1 ACF |
| --- | --- | ---: | ---: | ---: |
| 22756 | LARGE YELLOW BABUSHKA NOTEBOOK | 8.446 | 1.79 | 0.009 |
| 22758 | LARGE PURPLE BABUSHKA NOTEBOOK | 7.371 | 1.65 | 0.008 |
| 22753 | SMALL YELLOW BABUSHKA NOTEBOOK | 7.133 | 1.62 | -0.011 |
| 22757 | LARGE RED BABUSHKA NOTEBOOK | 6.966 | 1.62 | 0.018 |
| 22752 | SET 7 BABUSHKA NESTING BOXES | 6.590 | 1.53 | -0.002 |
| 21096 | SET/6 FRUIT SALAD PAPER PLATES | 6.311 | 1.79 | -0.025 |
| 21082 | SET/20 FRUIT SALAD PAPER NAPKINS | 6.172 | 1.62 | -0.023 |
| 21088 | SET/6 FRUIT SALAD PAPER CUPS | 6.159 | 1.79 | -0.025 |
| 22755 | SMALL PURPLE BABUSHKA NOTEBOOK | 6.131 | 1.55 | -0.006 |
| 22754 | SMALL RED BABUSHKA NOTEBOOK | 6.115 | 1.58 | 0.005 |

### Strongest week-to-week persistence

| SKU | Description | CV | ADI weeks | Lag-1 ACF |
| --- | --- | ---: | ---: | ---: |
| 22577 | WOODEN HEART CHRISTMAS SCANDINAVIAN | 2.147 | 1.65 | 0.942 |
| 22086 | PAPER CHAIN KIT 50'S CHRISTMAS | 1.730 | 1.27 | 0.866 |
| 35970 | ZINC FOLKART SLEIGH BELLS | 1.773 | 1.39 | 0.804 |
| 22112 | CHOCOLATE HOT WATER BOTTLE | 1.317 | 1.02 | 0.802 |
| 22114 | HOT WATER BOTTLE TEA AND SYMPATHY | 1.478 | 1.37 | 0.746 |
| 22198 | LARGE POPCORN HOLDER | 1.445 | 1.76 | 0.724 |
| 22084 | PAPER CHAIN KIT EMPIRE | 1.694 | 1.12 | 0.721 |
| 22158 | 3 HEARTS HANGING DECORATION RUSTIC | 1.844 | 1.42 | 0.703 |
| 84029G | KNITTED UNION FLAG HOT WATER BOTTLE | 1.580 | 1.05 | 0.697 |
| 22697 | GREEN REGENCY TEACUP AND SAUCER | 0.915 | 1.53 | 0.677 |

## Interpretation for forecasting

- Use weekly models for intermittent products or aggregate low-volume SKUs before forecasting.
- Treat high-CV/long-ADI SKUs as candidates for intermittent-demand approaches rather than ordinary seasonal models.
- Include calendar/promotion features when modeling high seasonal-component weeks and review the Day 3 spike queue before training.
- The source ends on 2011-12-09; do not treat that partial period as a normal December forecast target.

## Reproducibility

Run from the repository root:

```powershell
python -S scripts/analyze_time_series.py
```
