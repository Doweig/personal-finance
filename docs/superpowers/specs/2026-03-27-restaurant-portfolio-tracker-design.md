# Restaurant Portfolio Tracker — Design Spec

## Overview

A local-first personal finance system for tracking restaurant investments in Thailand. Replaces a Google Sheets workflow that no longer scales as the portfolio grows.

**Stack:** Python (ingestion CLI) + DuckDB (storage) + Evidence.dev (dashboard)

**Currency:** THB only (no USD conversion).

## Data Model

### Raw Tables (source of truth)

#### `restaurants`
| Column | Type | Description |
|---|---|---|
| id | TEXT PK | Slug identifier, e.g. `mozza-emq` |
| name | TEXT | Display name, e.g. `Mozza EmQuartier` |
| restaurant_code | TEXT | Code from P&L emails, e.g. `17-Mozza EMQ` |
| opening_date | DATE | When the restaurant opened or first data available |

Known restaurants and their codes:
- `mozza-emq` → `17-Mozza EMQ`
- `cocotte-39` → `15-Cocotte`
- `mozza-prg` → `20-Mozza Paragon`
- `mozza-icsm` → `25-Mozza ICON`
- `mozza-cp` → `26-Mozza Central Park`
- `parma-eastville` → `27-Parma Central Eastville`

#### `ownership`
Tracks ownership percentage over time. Ownership changes are rare (only increases when buying more shares).

| Column | Type | Description |
|---|---|---|
| restaurant_id | TEXT FK | References `restaurants.id` |
| effective_date | DATE | When this ownership % took effect |
| ownership_pct | DECIMAL | Percentage owned, e.g. `10.6891` |

To resolve ownership at a given date: use the most recent `effective_date <= target_date` for that restaurant.

#### `investments`
Capital deployed into each restaurant.

| Column | Type | Description |
|---|---|---|
| restaurant_id | TEXT FK | References `restaurants.id` |
| date | DATE | Date of investment |
| amount_thb | DECIMAL | Amount invested in THB |

#### `monthly_pl`
Monthly profit & loss data per restaurant. Composite key: `(restaurant_id, month)`.

| Column | Type | Description |
|---|---|---|
| restaurant_id | TEXT FK | References `restaurants.id` |
| month | DATE | First of the month, e.g. `2026-02-01` |
| revenue | DECIMAL | Total revenue |
| revenue_n1 | DECIMAL | Total revenue same month prior year (nullable) |
| food_cost | DECIMAL | Food cost |
| beverage_cost | DECIMAL | Beverage cost |
| total_fb_cost | DECIMAL | Total F&B cost |
| total_other_expenses | DECIMAL | Total other operating expenses |
| total_monthly_exp | DECIMAL | Total monthly expenses |
| gop_before_fee | DECIMAL | Gross operating profit before fees |
| other_special_fee | DECIMAL | Other and special fees (nullable, default 0) |
| monthly_provision | DECIMAL | Monthly provision (nullable, default 0) |
| gop_net | DECIMAL | Net gross operating profit |
| rebate | DECIMAL | Rebate amount (nullable, default 0) |

#### `dividends`
Actual cash distributions received.

| Column | Type | Description |
|---|---|---|
| restaurant_id | TEXT FK | References `restaurants.id` |
| date | DATE | Date of dividend payment |
| total_thb | DECIMAL | Total distribution amount for the restaurant |
| my_share_thb | DECIMAL | Guillaume's share in THB |
| comment | TEXT | Notes, e.g. month the dividend covers |

### Calculated Fields (SQL views in Evidence)

All calculated metrics are computed on-the-fly in Evidence SQL queries, not stored in DuckDB. This keeps the raw data clean and calculations transparent.

**Per-restaurant monthly enrichment:**
- `earnings_yield` = `gop_net / revenue`
- `ey_12sma` = 12-month simple moving average of earnings yield (window function)
- `revenue_12sma` = 12-month SMA of revenue
- `gop_net_12sma` = 12-month SMA of net income
- `revenue_valuation` = `revenue_12sma * 12` (annualized revenue)
- `income_valuation` = `gop_net_12sma * 12 * 4` (annualized income x4 multiplier)
- `blended_valuation` = average of the two methods
- `my_share_valuation` = `blended_valuation * ownership_pct / 100`

**Dividend summary:**
- `cumulative_dividends` = running sum of `my_share_thb`
- `dividend_12mma` = 12-month moving average of dividends

**IRR calculation:**
Given investment dates/amounts, all dividends received, and current valuation as terminal value, compute the monthly rate `r` such that NPV = 0. This is solved numerically using Newton's method in Evidence's JavaScript layer (since DuckDB lacks iterative solvers). The cashflow data is queried via SQL; the IRR solver runs client-side.

## Project Structure

```
personal-finance/
├── data/
│   └── portfolio.duckdb
├── ingestion/
│   ├── __init__.py
│   ├── cli.py                    # python -m ingestion.cli <command>
│   ├── parse_eml.py              # .eml → structured P&L + dividend data
│   ├── import_xlsx.py            # one-time import from hma-22-26.xlsx
│   └── db.py                     # DuckDB schema creation + insert/upsert
├── inbox/                        # drop .eml files here for ingestion
├── dashboard/                    # Evidence.dev project
│   ├── pages/
│   │   ├── index.md              # portfolio overview
│   │   ├── [restaurant].md       # per-restaurant financial detail
│   │   └── returns.md            # personal returns & dividend tracking
│   └── sources/
│       └── portfolio/
│           └── connection.yaml   # DuckDB connection → ../../../data/portfolio.duckdb
├── docs/
│   └── superpowers/
│       └── specs/
│           └── (this file)
├── hma-22-26.xlsx                # original spreadsheet (reference only)
└── requirements.txt              # duckdb, openpyxl
```

## Ingestion Pipeline

### One-Time Historical Import

```
python -m ingestion.cli import-xlsx hma-22-26.xlsx
```

Reads the 17-sheet Excel file and populates all tables:
- **Valuation sheets** (`*val.`): restaurant metadata + monthly P&L summary (revenue, net income) → `restaurants`, `monthly_pl`
- **Dividend sheets** (`*div.`): dividend payments, investment amounts, ownership % → `dividends`, `investments`, `ownership`
- **P&L sheets** (`Cocotte 22`, `Mozza EMQ 23`, etc.): detailed monthly data → `monthly_pl` (merges with valuation data where overlapping)

Sheet-to-restaurant mapping:
- `Mozza EMQ val.` / `Mozza EMQ div.` / `Mozza EMQ 22` / `Mozza EMQ 23` / `Mozza EMQ 24` → `mozza-emq`
- `Cocotte 39 val.` / `Cocotte 39 div.` / `Cocotte 22` / `Cocotte 23` / `Cocotte 24` → `cocotte-39`
- `Mozza PRG val.` / `Mozza PRG div.` → `mozza-prg`
- `Mozza ICSM val.` / `Mozza ICSM div.` → `mozza-icsm`
- `Mozza CP val.` / `Mozza CP div.` → `mozza-cp`

Note: The valuation sheets only have revenue and net income (gop_net). The detailed P&L sheets (food cost, beverage cost, etc.) only exist for Mozza EMQ and Cocotte 39 for 2022-2024. For other restaurants and periods, only summary figures are available from the valuation sheets.

### Ongoing Email Ingestion

```
python -m ingestion.cli ingest inbox/
```

For each `.eml` file in the inbox directory:
1. Parse email subject → extract restaurant name and month (pattern: `P&L <restaurant> <month> <year>`)
2. Match restaurant name to `restaurants.restaurant_code`
3. Extract plain-text body → parse P&L fields by label matching (tab-separated values)
4. If profit-sharing table is present → find row matching "Guillaume" → extract dividend amount
5. Upsert into `monthly_pl` (key: restaurant_id + month)
6. Insert into `dividends` if dividend data found
7. Print summary: imported/skipped/errors

**Upsert behavior:** If a record for (restaurant_id, month) already exists, it is updated with the new values. This makes the command idempotent — safe to re-run on the same inbox.

**Email format notes:**
- All emails come from `david.n@hmgtasia.com` (David Nemarq, HMA)
- P&L structure is identical across all restaurants
- Key labels to parse: `TOTAL REVENUE`, `TOTAL REVENUE N-1`, `Rebate`, `- Food cost`, `- Beverage cost`, `Total F&B Cost`, `Total Other Ex`, `TOTAL MONTHLY EXP`, `GOP before fee`, `Other and Special Fee`, `Monthly Provision`, `GOP NET`
- Some fields may be blank (treated as 0 or null)
- Profit-sharing table is optional (present in ~half the emails)

### Manual CLI Commands

```
python -m ingestion.cli update-ownership <restaurant-id> --date YYYY-MM-DD --pct <number>
python -m ingestion.cli add-investment <restaurant-id> --date YYYY-MM-DD --amount <thb>
python -m ingestion.cli add-dividend <restaurant-id> --date YYYY-MM-DD --total <thb> --my-share <thb> --comment "text"
```

Fallback commands for data not in emails.

## Dashboard Pages

### 1. Portfolio Overview (`index.md`)

**KPI cards (top row):**
- Total Invested (sum of all investments)
- Portfolio Valuation — My Share (sum of blended valuations x ownership %)
- Total Dividends Received (all time, sum of my_share_thb)
- Portfolio IRR (monthly + annualized)

**Restaurant summary table:**
| Column | Description |
|---|---|
| Restaurant | Name (links to detail page) |
| Ownership | Current ownership % |
| Invested | Total THB invested |
| Valuation (My Share) | Blended valuation x ownership % |
| Total Dividends | Cumulative dividends received |
| IRR (monthly) | Internal rate of return |
| Latest Month | Most recent P&L month on file (visual freshness indicator) |

### 2. Restaurant Detail (`[restaurant].md`)

Dynamic route — one template serves all restaurants, parameterized by restaurant slug.

**Content:**
- Revenue trend (line chart, monthly, with N-1 overlay for YoY comparison)
- GOP trend (line chart) + GOP margin % over time
- Earnings yield and 12-month SMA
- F&B cost ratio over time
- Valuation: revenue method vs income method vs blended (line chart)
- Monthly P&L data table (scrollable, all months)

### 3. My Returns (`returns.md`)

**Content:**
- Dividend history table per restaurant (date, amount, running total)
- Cumulative dividends chart (line per restaurant)
- ROI: total dividends received / total invested, per restaurant and overall
- IRR breakdown per restaurant (monthly and annualized)
- Months-to-ROI estimate (invested / average monthly dividend)

## Valuation Methodology

Preserved from existing spreadsheet:

1. **Revenue method:** 12-month SMA of monthly revenue × 12 = annualized revenue valuation
2. **Income method:** 12-month SMA of monthly GOP net × 12 × 4 = annualized income valuation (4x multiplier)
3. **Blended:** Average of methods 1 and 2
4. **My share:** Blended valuation × ownership percentage

The 12-month SMA only starts producing values once 12 months of data exist. Before that, the valuation columns are null.

## IRR Calculation

The internal rate of return `r` (monthly) satisfies:

```
-Investment₁/(1+r)^n₁ - Investment₂/(1+r)^n₂ - ... + Dividend₁/(1+r)^m₁ + Dividend₂/(1+r)^m₂ + ... + Valuation/(1+r)^t = 0
```

Where:
- `n_i` = months between investment date and reference date
- `m_j` = months between dividend date and reference date
- `t` = 0 (current valuation as terminal value)

Solved numerically. Annualized IRR = `(1+r)^12 - 1`.
