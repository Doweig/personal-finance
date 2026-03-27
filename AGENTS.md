# Repository Guidelines

## Project Structure & Module Organization
- `ingestion/`: Python package for DuckDB schema, CSV/XLSX import, and `.eml` parsing (`cli.py`, `db.py`, `parse_eml.py`).
- `tests/`: `pytest` suite (`test_db.py`, `test_parse_eml.py`, `test_import_xlsx.py`) with shared fixtures in `conftest.py`.
- `data/`: Canonical CSV seed files (`restaurants.csv`, `investments.csv`, `ownership.csv`, `monthly_pl.csv`, `dividends.csv`) plus generated `portfolio.duckdb`.
- `dashboard/`: Evidence.dev app (`pages/`, `sources/`, `components/`) for portfolio reporting.
- `inbox/`: Drop monthly source `.eml` files before ingestion.
- `docs/`: Planning/spec documents.

## Build, Test, and Development Commands
- `uv sync`: Install Python dependencies from `pyproject.toml`/`uv.lock`.
- `uv run python -m ingestion.cli import-csv data/`: Seed DuckDB from CSVs.
- `uv run python -m ingestion.cli ingest inbox/`: Parse `.eml` reports and upsert monthly data.
- `uv run pytest tests/ -v`: Run the Python test suite.
- `cd dashboard && bun install`: Install dashboard dependencies (first run).
- `cd dashboard && bun run sources`: Refresh Evidence sources from DuckDB.
- `cd dashboard && bun run dev`: Start dashboard locally at `http://localhost:3000`.

## Coding Style & Naming Conventions
- Python: PEP 8 style, 4-space indentation, `snake_case` for functions/modules, `UPPER_SNAKE_CASE` for constants.
- Prefer clear dict keys matching DB columns (for example: `restaurant_id`, `ownership_pct`).
- Tests: name files `test_*.py`; group related assertions in `Test*` classes.
- Dashboard SQL files are lowercase with underscores; restaurant IDs are kebab-case (example: `parma-eastville`).
- No dedicated formatter/linter is configured yet; keep changes small and consistent with surrounding code.

## Testing Guidelines
- Use `pytest` with in-memory DuckDB fixtures for fast, isolated tests.
- Cover schema behavior, upserts/idempotency, and parsing edge cases.
- Add or update tests in the same change when modifying ingestion logic or table schema.

## Commit & Pull Request Guidelines
- Prefer Conventional Commit prefixes seen in history: `feat:`, `fix:`, `chore:`.
- Keep commits focused (schema, ingestion logic, dashboard UI, tests).
- PRs should include: purpose, key changes, test evidence (`uv run pytest ...`), and dashboard screenshots for UI/page updates.
