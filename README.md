# Restaurant Portfolio Tracker

Personal finance system for tracking restaurant investments in Thailand. Replaces a Google Sheets workflow with a local DuckDB database and an Evidence.dev dashboard.

## Stack

- **Storage:** DuckDB (single file at `data/portfolio.duckdb`)
- **Ingestion:** Python CLI (`ingestion/`)
- **Dashboard:** Evidence.dev (`dashboard/`)

## Quick Start

### 1. Install Python dependencies

```bash
uv sync
```

### 2. Seed the database from CSV seed data

```bash
uv run python -m ingestion.cli import-csv data/
```

### 3. Ingest email reports

Save `.eml` files from monthly P&L emails into `inbox/`, then:

```bash
uv run python -m ingestion.cli ingest inbox/
```

### 4. Start the dashboard

```bash
cd dashboard
bun install      # first time only
bun run sources  # refresh data from DuckDB
bun run dev      # http://localhost:3000
```

## CLI Reference

All commands accept `--db <path>` to override the default database location.

### Import seed data from CSVs (one-time)

```bash
uv run python -m ingestion.cli import-csv data/
```

Reads `data/*.csv` files (restaurants, investments, ownership, monthly_pl, dividends) into DuckDB. Edit the CSVs directly to correct historical data.

### Ingest email reports

```bash
uv run python -m ingestion.cli ingest inbox/
```

Processes all `.eml` files in the directory. Extracts P&L data and dividend payments (looks for "Guillaume" in profit-sharing tables). Safe to re-run -- existing months are updated, not duplicated.

### Manual data entry

```bash
# Record an ownership change
uv run python -m ingestion.cli update-ownership mozza-emq --date 2026-03-01 --pct 12.5

# Record a new investment
uv run python -m ingestion.cli add-investment parma-eastville --date 2026-01-15 --amount 5000000

# Record a dividend manually
uv run python -m ingestion.cli add-dividend mozza-emq --date 2026-03-15 --total 5000000 --my-share 534455 --comment "from Feb 2026"
```

## Monthly Workflow

1. Receive P&L email from HMA
2. Save as `.eml` into `inbox/`
3. Run `uv run python -m ingestion.cli ingest inbox/`
4. Refresh dashboard: `cd dashboard && bun run sources && bun run dev`

## Dashboard Pages

| Page | URL | Content |
|---|---|---|
| Portfolio Overview | `/` | KPI cards (invested, valuation, dividends), restaurant summary table |
| Restaurant Detail | `/restaurants/{id}` | Revenue/GOP charts, margins, valuations, P&L table |
| My Returns | `/returns` | Dividend history, cumulative chart, ROI, IRR per restaurant |

## Restaurant IDs

| ID | Name | Email Code |
|---|---|---|
| `mozza-emq` | Mozza EmQuartier | 17-Mozza EMQ |
| `cocotte-39` | Cocotte 39 | 15-Cocotte |
| `mozza-prg` | Mozza Paragon | 20-Mozza Paragon |
| `mozza-icsm` | Mozza Icon Siam | 25-Mozza ICON |
| `mozza-cp` | Mozza Central Park | 26-Mozza Central Park |
| `parma-eastville` | Parma Eastville | 27-Parma Central Eastville |

## Valuation Methodology

Two methods, averaged:

1. **Revenue method:** 12-month SMA of monthly revenue x 12
2. **Income method:** 12-month SMA of monthly GOP net x 12 x 4

Valuations only appear after 12 months of data. "My share" = blended valuation x ownership %.

## Running Tests

```bash
uv run pytest tests/ -v
```

## Project Structure

```
personal-finance/
├── data/                    # Seed CSVs (checked in) + DuckDB file (gitignored)
│   ├── restaurants.csv      # Restaurant metadata
│   ├── investments.csv      # Capital deployed (date + THB amount)
│   ├── ownership.csv        # Ownership % history
│   ├── monthly_pl.csv       # Historical monthly P&L
│   ├── dividends.csv        # Historical dividend payments
│   └── portfolio.duckdb     # Generated database (gitignored)
├── ingestion/               # Python ingestion package
│   ├── cli.py               # CLI entry point
│   ├── db.py                # Schema + CRUD helpers
│   ├── parse_eml.py         # Email P&L parser
│   └── import_csv.py        # CSV seed data import
├── tests/                   # pytest suite
├── dashboard/               # Evidence.dev project
│   ├── pages/               # Dashboard pages (Markdown + SQL)
│   ├── sources/             # DuckDB connection config
│   └── components/          # Custom Svelte components (IRR)
├── inbox/                   # Drop .eml files here
└── hma-22-26.xlsx           # Original spreadsheet (reference only)
```
