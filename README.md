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

### 2. Rebuild the database from CSV source-of-truth

```bash
uv run python -m ingestion.cli rebuild-db data/
```

### 3. Process monthly emails into CSVs (recommended)

Save `.eml` files from monthly P&L emails into `inbox/`, then:

```bash
uv run python -m ingestion.cli process-inbox inbox/
uv run python -m ingestion.cli rebuild-db data/
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

### Process inbox emails into CSVs (recommended)

```bash
uv run python -m ingestion.cli process-inbox inbox/
```

Parses all `.eml` files, upserts `data/monthly_pl.csv` and `data/dividends.csv`, and archives processed files to `inbox/archive/YYYY-MM/`.

Useful options:

```bash
# Preview extraction only
uv run python -m ingestion.cli process-inbox inbox/ --dry-run

# Keep source emails in place (no archive move)
uv run python -m ingestion.cli process-inbox inbox/ --no-archive
```

### Rebuild DuckDB from CSVs

```bash
uv run python -m ingestion.cli rebuild-db data/
```

Deletes/recreates `data/portfolio.duckdb` and loads all CSVs. This keeps reruns deterministic and avoids drift.

### Legacy direct DB ingest (kept for compatibility)

```bash
uv run python -m ingestion.cli ingest inbox/
```

Writes email extraction directly into DuckDB (without touching CSVs).

### Optional LLM extraction for tricky emails

```bash
# Generate a Codex/ChatGPT prompt from one .eml
uv run python -m ingestion.cli extract-email "inbox/P&L Mozza EmQuartier February 2026.eml"

# Call OpenAI API directly (requires OPENAI_API_KEY)
uv run python -m ingestion.cli extract-email "inbox/P&L Mozza EmQuartier February 2026.eml" --provider openai
```

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
3. Run `uv run python -m ingestion.cli process-inbox inbox/`
4. Rebuild DB: `uv run python -m ingestion.cli rebuild-db data/`
5. Refresh dashboard: `cd dashboard && bun run sources && bun run dev`

## Dashboard Pages

| Page | URL | Content |
|---|---|---|
| Home | `/` | Portfolio KPIs and high-level restaurant snapshot |
| Restaurants | `/restaurants` | Per-restaurant summary + moving-average trend charts |
| Restaurant Detail | `/restaurants/{id}` | Revenue/GOP charts, margins, valuations, P&L table |
| Returns | `/returns` | Dividend history, cumulative chart, ROI, IRR per restaurant |

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
│   ├── process_inbox.py     # CSV-first inbox workflow + archiving
│   ├── extract_llm.py       # Optional LLM extraction helpers
│   └── import_csv.py        # CSV seed data import
├── tests/                   # pytest suite
├── dashboard/               # Evidence.dev project
│   ├── pages/               # Dashboard pages (Markdown + SQL)
│   ├── sources/             # DuckDB connection config
│   └── components/          # Custom Svelte components (IRR)
├── inbox/                   # Drop .eml files here
└── hma-22-26.xlsx           # Original spreadsheet (reference only)
```
