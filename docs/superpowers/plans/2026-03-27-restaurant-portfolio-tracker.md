# Restaurant Portfolio Tracker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first restaurant investment tracker with Python ingestion CLI and Evidence.dev dashboard, replacing a Google Sheets workflow.

**Architecture:** DuckDB stores raw financial data (P&L, dividends, ownership, investments). A Python CLI ingests data from .eml emails and a historical .xlsx file. Evidence.dev serves a 3-page dashboard with SQL-computed metrics (valuations, SMA, IRR).

**Tech Stack:** Python 3, DuckDB, openpyxl, Evidence.dev, Node.js/npm

---

## File Structure

```
personal-finance/
├── data/
│   └── portfolio.duckdb                     # DuckDB database (gitignored)
├── ingestion/
│   ├── __init__.py                          # Package marker
│   ├── cli.py                               # CLI entry point (argparse)
│   ├── db.py                                # Schema creation + insert/upsert helpers
│   ├── parse_eml.py                         # .eml → structured P&L + dividend dicts
│   └── import_xlsx.py                       # One-time historical import from Excel
├── tests/
│   ├── __init__.py
│   ├── conftest.py                          # Shared fixtures (in-memory DuckDB, sample data)
│   ├── test_db.py                           # Schema + upsert tests
│   ├── test_parse_eml.py                    # Email parser tests
│   └── test_import_xlsx.py                  # Excel import tests
├── inbox/                                   # Drop .eml files here
├── dashboard/                               # Evidence.dev project (created via degit)
│   ├── pages/
│   │   ├── index.md                         # Portfolio overview
│   │   ├── restaurants/
│   │   │   └── [restaurant].md              # Per-restaurant detail
│   │   └── returns.md                       # Personal returns & dividends
│   ├── sources/
│   │   └── portfolio/
│   │       └── connection.yaml              # DuckDB connection
│   └── components/
│       └── IRRCalculator.svelte             # Client-side IRR solver
├── requirements.txt                         # Python deps
├── hma-22-26.xlsx                           # Original spreadsheet (reference)
└── .gitignore
```

---

### Task 1: Python Environment & DuckDB Schema

**Files:**
- Create: `requirements.txt`
- Create: `ingestion/__init__.py`
- Create: `ingestion/db.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Create requirements.txt**

```
duckdb>=1.1.0
openpyxl>=3.1.0
pytest>=8.0.0
```

- [ ] **Step 2: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: All packages install successfully.

- [ ] **Step 3: Write test for schema creation**

Create `tests/__init__.py` (empty file).

Create `tests/conftest.py`:

```python
import duckdb
import pytest


@pytest.fixture
def db():
    conn = duckdb.connect(":memory:")
    yield conn
    conn.close()
```

Create `tests/test_db.py`:

```python
from ingestion.db import create_schema, upsert_monthly_pl, insert_dividend, insert_investment, insert_ownership


def test_create_schema_creates_all_tables(db):
    create_schema(db)
    tables = db.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main' ORDER BY table_name").fetchall()
    table_names = [t[0] for t in tables]
    assert "restaurants" in table_names
    assert "ownership" in table_names
    assert "investments" in table_names
    assert "monthly_pl" in table_names
    assert "dividends" in table_names


def test_upsert_monthly_pl_inserts_new_row(db):
    create_schema(db)
    db.execute("INSERT INTO restaurants VALUES ('mozza-emq', 'Mozza EmQuartier', '17-Mozza EMQ', '2022-09-01')")
    row = {
        "restaurant_id": "mozza-emq",
        "month": "2026-02-01",
        "revenue": 15000000,
        "revenue_n1": 14000000,
        "food_cost": 3000000,
        "beverage_cost": 800000,
        "total_fb_cost": 3800000,
        "total_other_expenses": 6000000,
        "total_monthly_exp": 9800000,
        "gop_before_fee": 5200000,
        "other_special_fee": 0,
        "monthly_provision": 0,
        "gop_net": 5200000,
        "rebate": 0,
    }
    upsert_monthly_pl(db, row)
    result = db.execute("SELECT revenue, gop_net FROM monthly_pl WHERE restaurant_id = 'mozza-emq' AND month = '2026-02-01'").fetchone()
    assert result == (15000000, 5200000)


def test_upsert_monthly_pl_updates_existing_row(db):
    create_schema(db)
    db.execute("INSERT INTO restaurants VALUES ('mozza-emq', 'Mozza EmQuartier', '17-Mozza EMQ', '2022-09-01')")
    row = {
        "restaurant_id": "mozza-emq",
        "month": "2026-02-01",
        "revenue": 15000000,
        "revenue_n1": 14000000,
        "food_cost": 3000000,
        "beverage_cost": 800000,
        "total_fb_cost": 3800000,
        "total_other_expenses": 6000000,
        "total_monthly_exp": 9800000,
        "gop_before_fee": 5200000,
        "other_special_fee": 0,
        "monthly_provision": 0,
        "gop_net": 5200000,
        "rebate": 0,
    }
    upsert_monthly_pl(db, row)
    row["revenue"] = 16000000
    row["gop_net"] = 6200000
    upsert_monthly_pl(db, row)
    count = db.execute("SELECT count(*) FROM monthly_pl WHERE restaurant_id = 'mozza-emq' AND month = '2026-02-01'").fetchone()[0]
    assert count == 1
    result = db.execute("SELECT revenue, gop_net FROM monthly_pl WHERE restaurant_id = 'mozza-emq' AND month = '2026-02-01'").fetchone()
    assert result == (16000000, 6200000)


def test_insert_dividend(db):
    create_schema(db)
    db.execute("INSERT INTO restaurants VALUES ('mozza-emq', 'Mozza EmQuartier', '17-Mozza EMQ', '2022-09-01')")
    insert_dividend(db, {
        "restaurant_id": "mozza-emq",
        "date": "2026-02-15",
        "total_thb": 5000000,
        "my_share_thb": 534455,
        "comment": "from Jan 2026",
    })
    result = db.execute("SELECT my_share_thb FROM dividends WHERE restaurant_id = 'mozza-emq'").fetchone()
    assert result[0] == 534455


def test_insert_investment(db):
    create_schema(db)
    db.execute("INSERT INTO restaurants VALUES ('mozza-emq', 'Mozza EmQuartier', '17-Mozza EMQ', '2022-09-01')")
    insert_investment(db, {
        "restaurant_id": "mozza-emq",
        "date": "2022-09-01",
        "amount_thb": 12105000,
    })
    result = db.execute("SELECT amount_thb FROM investments WHERE restaurant_id = 'mozza-emq'").fetchone()
    assert result[0] == 12105000


def test_insert_ownership(db):
    create_schema(db)
    db.execute("INSERT INTO restaurants VALUES ('mozza-emq', 'Mozza EmQuartier', '17-Mozza EMQ', '2022-09-01')")
    insert_ownership(db, {
        "restaurant_id": "mozza-emq",
        "effective_date": "2022-09-01",
        "ownership_pct": 10.6891,
    })
    result = db.execute("SELECT ownership_pct FROM ownership WHERE restaurant_id = 'mozza-emq'").fetchone()
    assert abs(result[0] - 10.6891) < 0.0001
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `python -m pytest tests/test_db.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingestion'`

- [ ] **Step 5: Implement db.py**

Create `ingestion/__init__.py` (empty file).

Create `ingestion/db.py`:

```python
import os

import duckdb

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "portfolio.duckdb")


def get_connection(db_path=None):
    path = db_path or DEFAULT_DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return duckdb.connect(path)


def create_schema(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS restaurants (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            restaurant_code TEXT,
            opening_date DATE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ownership (
            restaurant_id TEXT REFERENCES restaurants(id),
            effective_date DATE NOT NULL,
            ownership_pct DOUBLE NOT NULL,
            PRIMARY KEY (restaurant_id, effective_date)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS investments (
            restaurant_id TEXT REFERENCES restaurants(id),
            date DATE NOT NULL,
            amount_thb DOUBLE NOT NULL,
            PRIMARY KEY (restaurant_id, date)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS monthly_pl (
            restaurant_id TEXT REFERENCES restaurants(id),
            month DATE NOT NULL,
            revenue DOUBLE,
            revenue_n1 DOUBLE,
            food_cost DOUBLE,
            beverage_cost DOUBLE,
            total_fb_cost DOUBLE,
            total_other_expenses DOUBLE,
            total_monthly_exp DOUBLE,
            gop_before_fee DOUBLE,
            other_special_fee DOUBLE DEFAULT 0,
            monthly_provision DOUBLE DEFAULT 0,
            gop_net DOUBLE,
            rebate DOUBLE DEFAULT 0,
            PRIMARY KEY (restaurant_id, month)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS dividends (
            restaurant_id TEXT REFERENCES restaurants(id),
            date DATE NOT NULL,
            total_thb DOUBLE,
            my_share_thb DOUBLE,
            comment TEXT
        )
    """)


def upsert_monthly_pl(conn, row):
    conn.execute("""
        INSERT INTO monthly_pl (restaurant_id, month, revenue, revenue_n1, food_cost, beverage_cost,
            total_fb_cost, total_other_expenses, total_monthly_exp, gop_before_fee,
            other_special_fee, monthly_provision, gop_net, rebate)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        ON CONFLICT (restaurant_id, month) DO UPDATE SET
            revenue = EXCLUDED.revenue,
            revenue_n1 = EXCLUDED.revenue_n1,
            food_cost = EXCLUDED.food_cost,
            beverage_cost = EXCLUDED.beverage_cost,
            total_fb_cost = EXCLUDED.total_fb_cost,
            total_other_expenses = EXCLUDED.total_other_expenses,
            total_monthly_exp = EXCLUDED.total_monthly_exp,
            gop_before_fee = EXCLUDED.gop_before_fee,
            other_special_fee = EXCLUDED.other_special_fee,
            monthly_provision = EXCLUDED.monthly_provision,
            gop_net = EXCLUDED.gop_net,
            rebate = EXCLUDED.rebate
    """, [
        row["restaurant_id"], row["month"], row["revenue"], row["revenue_n1"],
        row["food_cost"], row["beverage_cost"], row["total_fb_cost"],
        row["total_other_expenses"], row["total_monthly_exp"], row["gop_before_fee"],
        row.get("other_special_fee", 0), row.get("monthly_provision", 0),
        row["gop_net"], row.get("rebate", 0),
    ])


def insert_dividend(conn, row):
    conn.execute("""
        INSERT INTO dividends (restaurant_id, date, total_thb, my_share_thb, comment)
        VALUES ($1, $2, $3, $4, $5)
    """, [row["restaurant_id"], row["date"], row.get("total_thb"), row["my_share_thb"], row.get("comment")])


def insert_investment(conn, row):
    conn.execute("""
        INSERT INTO investments (restaurant_id, date, amount_thb)
        VALUES ($1, $2, $3)
        ON CONFLICT (restaurant_id, date) DO UPDATE SET amount_thb = EXCLUDED.amount_thb
    """, [row["restaurant_id"], row["date"], row["amount_thb"]])


def insert_ownership(conn, row):
    conn.execute("""
        INSERT INTO ownership (restaurant_id, effective_date, ownership_pct)
        VALUES ($1, $2, $3)
        ON CONFLICT (restaurant_id, effective_date) DO UPDATE SET ownership_pct = EXCLUDED.ownership_pct
    """, [row["restaurant_id"], row["effective_date"], row["ownership_pct"]])


def insert_restaurant(conn, row):
    conn.execute("""
        INSERT INTO restaurants (id, name, restaurant_code, opening_date)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            restaurant_code = EXCLUDED.restaurant_code,
            opening_date = EXCLUDED.opening_date
    """, [row["id"], row["name"], row.get("restaurant_code"), row.get("opening_date")])
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_db.py -v`
Expected: All 6 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt ingestion/ tests/
git commit -m "feat: add DuckDB schema and data access layer"
```

---

### Task 2: Email Parser

**Files:**
- Create: `ingestion/parse_eml.py`
- Create: `tests/test_parse_eml.py`

- [ ] **Step 1: Write tests for email parser**

Create `tests/test_parse_eml.py`:

```python
import os

from ingestion.parse_eml import parse_eml_file

INBOX_DIR = os.path.join(os.path.dirname(__file__), "..", "inbox")


def test_parse_parma_eastville_feb():
    path = os.path.join(INBOX_DIR, "P&L Parma Eastville February 2026.eml")
    result = parse_eml_file(path)
    assert result["restaurant_name"] == "Parma Eastville"
    assert result["month"] == "2026-02-01"
    assert result["restaurant_code"] == "27-Parma Central Eastville"
    pl = result["pl"]
    assert pl["revenue"] == 2194431
    assert pl["gop_net"] == 454889
    assert pl["food_cost"] == 453336
    assert pl["beverage_cost"] == 81850
    assert pl["total_fb_cost"] == 535185
    assert pl["rebate"] == 137614


def test_parse_mozza_emq_feb():
    path = os.path.join(INBOX_DIR, "P&L Mozza EmQuartier February 2026.eml")
    result = parse_eml_file(path)
    assert result["restaurant_name"] == "Mozza EmQuartier"
    assert result["month"] == "2026-02-01"
    assert result["restaurant_code"] == "17-Mozza EMQ"
    pl = result["pl"]
    assert pl["revenue"] > 0
    assert pl["gop_net"] is not None


def test_parse_extracts_dividend_when_present():
    """Emails with profit-sharing table should yield dividend data."""
    path = os.path.join(INBOX_DIR, "P&L Mozza EmQuartier February 2026.eml")
    result = parse_eml_file(path)
    # Mozza EMQ has a profit-sharing table with Guillaume's share
    if result.get("dividend"):
        assert result["dividend"]["my_share_thb"] > 0


def test_parse_no_dividend_when_absent():
    """Emails without profit-sharing table should have no dividend data."""
    path = os.path.join(INBOX_DIR, "P&L Parma Eastville February 2026.eml")
    result = parse_eml_file(path)
    # Parma Eastville has no profit-sharing table
    assert result.get("dividend") is None


def test_parse_cocotte_feb():
    path = os.path.join(INBOX_DIR, "P&L Cocotte February 2026.eml")
    result = parse_eml_file(path)
    assert result["restaurant_name"] == "Cocotte"
    assert result["month"] == "2026-02-01"
    pl = result["pl"]
    assert pl["revenue"] > 0


def test_parse_all_inbox_files():
    """Smoke test: all .eml files in inbox should parse without error."""
    eml_files = [f for f in os.listdir(INBOX_DIR) if f.endswith(".eml")]
    assert len(eml_files) >= 6
    for f in eml_files:
        result = parse_eml_file(os.path.join(INBOX_DIR, f))
        assert result["restaurant_name"]
        assert result["month"]
        assert result["pl"]["revenue"] > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_parse_eml.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingestion.parse_eml'`

- [ ] **Step 3: Implement parse_eml.py**

Create `ingestion/parse_eml.py`:

```python
import email
import re
from datetime import date
from email import policy


MONTH_NAMES = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

# Restaurant code pattern: digits-Name at start of a line
RESTAURANT_CODE_RE = re.compile(r"^(\d+-[A-Za-z][A-Za-z &]+?)(?:\t|\n|$)", re.MULTILINE)

# Subject pattern: P&L <restaurant> <month> <year>
SUBJECT_RE = re.compile(r"P&L\s+(.+?)\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})", re.IGNORECASE)

# Label-to-field mapping. Labels appear on their own line, value on next non-empty line.
PL_FIELD_MAP = {
    "TOTAL REVENUE": "revenue",
    "TOTAL REVENUE N-1": "revenue_n1",
    "Rebate": "rebate",
    "- Food cost": "food_cost",
    "- Beverage cost": "beverage_cost",
    "Total F&B Cost": "total_fb_cost",
    "Total Other Ex": "total_other_expenses",
    "TOTAL MONTHLY EXP": "total_monthly_exp",
    "GOP before fee": "gop_before_fee",
    "Other and Special Fee": "other_special_fee",
    "Monthly Provision": "monthly_provision",
    "GOP NET": "gop_net",
}


def _parse_number(s):
    """Parse a number string like '2,194,431' or '0.00%' into a numeric value."""
    if not s or not s.strip():
        return None
    s = s.strip().replace(",", "").replace("\xa0", "")
    if s.endswith("%"):
        return None  # Skip percentage values
    try:
        return float(s) if "." in s else int(s)
    except ValueError:
        return None


def _get_plain_text(msg):
    """Extract the plain text body from an email message."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_content()
    else:
        if msg.get_content_type() == "text/plain":
            return msg.get_content()
    return ""


def _parse_pl_fields(body):
    """Extract P&L fields from plain text email body."""
    lines = body.split("\n")
    pl = {}
    for i, line in enumerate(lines):
        stripped = line.strip()
        for label, field in PL_FIELD_MAP.items():
            if stripped == label:
                # Look at the next non-empty lines for a numeric value
                for j in range(i + 1, min(i + 4, len(lines))):
                    next_line = lines[j].strip()
                    if not next_line:
                        continue
                    # The value might be tab-separated on the same line or on the next line
                    # Try to parse the first token
                    tokens = next_line.split("\t")
                    val = _parse_number(tokens[0])
                    if val is not None:
                        pl[field] = val
                        break
                    # If the next non-empty line is another label, value is missing
                    if any(next_line == lab for lab in PL_FIELD_MAP):
                        break
                break
    # Also check for tab-separated label\tvalue on same line
    for line in lines:
        parts = line.split("\t")
        if len(parts) >= 2:
            label_part = parts[0].strip()
            for label, field in PL_FIELD_MAP.items():
                if label_part == label and field not in pl:
                    val = _parse_number(parts[1])
                    if val is not None:
                        pl[field] = val
    return pl


def _parse_restaurant_code(body):
    """Extract restaurant code like '17-Mozza EMQ' from the body."""
    match = RESTAURANT_CODE_RE.search(body)
    if match:
        return match.group(1).strip()
    return None


def _parse_dividend(body):
    """Extract Guillaume's dividend share from the profit-sharing table, if present."""
    lines = body.split("\n")
    for i, line in enumerate(lines):
        if "guillaume" in line.lower():
            # Look for a numeric value on this line (tab-separated)
            parts = line.split("\t")
            for part in parts:
                val = _parse_number(part)
                if val is not None and val > 0:
                    return val
    return None


def parse_eml_file(filepath):
    """Parse an .eml file and return structured P&L + optional dividend data.

    Returns:
        dict with keys:
            - restaurant_name: str (from subject)
            - month: str (YYYY-MM-01 format)
            - restaurant_code: str (from body, e.g. '17-Mozza EMQ')
            - pl: dict of P&L fields
            - dividend: dict or None
            - email_date: str (email Date header)
    """
    with open(filepath, "rb") as f:
        msg = email.message_from_binary_file(f, policy=policy.default)

    subject = msg.get("Subject", "")
    subject_match = SUBJECT_RE.search(subject)
    if not subject_match:
        raise ValueError(f"Cannot parse subject: {subject}")

    restaurant_name = subject_match.group(1).strip()
    month_num = MONTH_NAMES[subject_match.group(2).lower()]
    year = int(subject_match.group(3))
    month_str = f"{year}-{month_num:02d}-01"

    body = _get_plain_text(msg)
    restaurant_code = _parse_restaurant_code(body)
    pl = _parse_pl_fields(body)

    # Fill defaults for missing nullable fields
    for field in ["other_special_fee", "monthly_provision", "rebate", "revenue_n1"]:
        if field not in pl:
            pl[field] = 0

    result = {
        "restaurant_name": restaurant_name,
        "month": month_str,
        "restaurant_code": restaurant_code,
        "pl": pl,
        "dividend": None,
        "email_date": msg.get("Date", ""),
    }

    dividend_amount = _parse_dividend(body)
    if dividend_amount:
        result["dividend"] = {
            "my_share_thb": dividend_amount,
        }

    return result
```

- [ ] **Step 4: Run tests and iterate**

Run: `python -m pytest tests/test_parse_eml.py -v`

The parser may need adjustments based on actual email formatting. Iterate on the regex patterns and field extraction logic until all tests pass. Common adjustments:
- Tab vs space separation
- Multi-line value blocks
- Different label variants (e.g., `Total Other Ex` vs `Total Other Expenses`)

Expected: All 6 tests PASS after iteration.

- [ ] **Step 5: Commit**

```bash
git add ingestion/parse_eml.py tests/test_parse_eml.py
git commit -m "feat: add email P&L parser with dividend extraction"
```

---

### Task 3: Historical Excel Import

**Files:**
- Create: `ingestion/import_xlsx.py`
- Create: `tests/test_import_xlsx.py`

- [ ] **Step 1: Write tests for Excel import**

Create `tests/test_import_xlsx.py`:

```python
import os

import duckdb

from ingestion.db import create_schema
from ingestion.import_xlsx import import_xlsx

XLSX_PATH = os.path.join(os.path.dirname(__file__), "..", "hma-22-26.xlsx")


@pytest.fixture
def populated_db():
    conn = duckdb.connect(":memory:")
    create_schema(conn)
    import_xlsx(conn, XLSX_PATH)
    yield conn
    conn.close()


import pytest


def test_imports_all_restaurants(populated_db):
    rows = populated_db.execute("SELECT id FROM restaurants ORDER BY id").fetchall()
    ids = [r[0] for r in rows]
    assert "mozza-emq" in ids
    assert "cocotte-39" in ids
    assert "mozza-prg" in ids
    assert "mozza-icsm" in ids
    assert "mozza-cp" in ids


def test_imports_monthly_pl_data(populated_db):
    count = populated_db.execute("SELECT count(*) FROM monthly_pl WHERE restaurant_id = 'mozza-emq'").fetchone()[0]
    # Mozza EMQ has data from Sep 2022 to Feb 2026 (~42 months)
    assert count >= 40


def test_imports_dividends(populated_db):
    count = populated_db.execute("SELECT count(*) FROM dividends WHERE restaurant_id = 'mozza-emq'").fetchone()[0]
    assert count > 0


def test_imports_investments(populated_db):
    result = populated_db.execute("SELECT amount_thb FROM investments WHERE restaurant_id = 'mozza-emq'").fetchone()
    assert result is not None
    assert result[0] == 12105000


def test_imports_ownership(populated_db):
    result = populated_db.execute("SELECT ownership_pct FROM ownership WHERE restaurant_id = 'mozza-emq' ORDER BY effective_date LIMIT 1").fetchone()
    assert result is not None
    assert abs(result[0] - 10.6891) < 0.001


def test_imports_cocotte_investments(populated_db):
    result = populated_db.execute("SELECT amount_thb FROM investments WHERE restaurant_id = 'cocotte-39'").fetchone()
    assert result is not None
    assert result[0] == 25325000


def test_pl_has_revenue_and_gop(populated_db):
    row = populated_db.execute("""
        SELECT revenue, gop_net FROM monthly_pl
        WHERE restaurant_id = 'mozza-emq' AND month = '2023-01-01'
    """).fetchone()
    assert row is not None
    assert row[0] > 0  # revenue
    assert row[1] is not None  # gop_net
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_import_xlsx.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingestion.import_xlsx'`

- [ ] **Step 3: Implement import_xlsx.py**

Create `ingestion/import_xlsx.py`:

```python
import re
from datetime import date

import openpyxl

from ingestion.db import (
    insert_dividend,
    insert_investment,
    insert_ownership,
    insert_restaurant,
    upsert_monthly_pl,
)

# Sheet name prefix → restaurant id mapping
RESTAURANT_MAP = {
    "Mozza EMQ": {"id": "mozza-emq", "name": "Mozza EmQuartier", "code": "17-Mozza EMQ"},
    "Cocotte 39": {"id": "cocotte-39", "name": "Cocotte 39", "code": "15-Cocotte"},
    "Cocotte": {"id": "cocotte-39", "name": "Cocotte 39", "code": "15-Cocotte"},
    "Mozza PRG": {"id": "mozza-prg", "name": "Mozza Paragon", "code": "20-Mozza Paragon"},
    "Mozza ICSM": {"id": "mozza-icsm", "name": "Mozza Icon Siam", "code": "25-Mozza ICON"},
    "Mozza CP": {"id": "mozza-cp", "name": "Mozza Central Park", "code": "26-Mozza Central Park"},
}


def _match_restaurant(sheet_name):
    """Match a sheet name to a restaurant config."""
    for prefix, config in RESTAURANT_MAP.items():
        if sheet_name.startswith(prefix):
            return config
    return None


def _parse_date_cell(value):
    """Convert a cell value to a date string YYYY-MM-01."""
    if isinstance(value, date):
        return f"{value.year}-{value.month:02d}-01"
    if isinstance(value, str):
        # Try common formats
        for fmt in ["%b-%y", "%B %Y", "%Y-%m-%d"]:
            try:
                from datetime import datetime
                dt = datetime.strptime(value.strip(), fmt)
                return f"{dt.year}-{dt.month:02d}-01"
            except ValueError:
                continue
    return None


def _safe_float(value):
    """Convert a cell value to float, returning None if not numeric."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _import_valuation_sheet(conn, ws, restaurant):
    """Import a valuation sheet (revenue + net income per month)."""
    insert_restaurant(conn, {
        "id": restaurant["id"],
        "name": restaurant["name"],
        "restaurant_code": restaurant["code"],
        "opening_date": None,
    })

    for row in ws.iter_rows(min_row=2, values_only=False):
        date_val = row[0].value
        revenue = _safe_float(row[1].value)
        net_income = _safe_float(row[2].value)

        if date_val is None or revenue is None:
            continue

        month_str = _parse_date_cell(date_val)
        if month_str is None:
            continue

        upsert_monthly_pl(conn, {
            "restaurant_id": restaurant["id"],
            "month": month_str,
            "revenue": revenue,
            "revenue_n1": None,
            "food_cost": None,
            "beverage_cost": None,
            "total_fb_cost": None,
            "total_other_expenses": None,
            "total_monthly_exp": None,
            "gop_before_fee": net_income,
            "other_special_fee": 0,
            "monthly_provision": 0,
            "gop_net": net_income,
            "rebate": 0,
        })


def _import_dividend_sheet(conn, ws, restaurant):
    """Import a dividend sheet (payments + investment metadata)."""
    # First row might be the initial investment (negative value)
    for row in ws.iter_rows(min_row=2, values_only=False):
        date_val = row[0].value
        total_thb = _safe_float(row[1].value)

        if date_val is None or total_thb is None:
            continue

        date_str = _parse_date_cell(date_val)
        if date_str is None:
            # Try as a full date
            if isinstance(date_val, date):
                date_str = date_val.isoformat()
            else:
                continue

        if total_thb < 0:
            # This is the initial investment
            insert_investment(conn, {
                "restaurant_id": restaurant["id"],
                "date": date_str,
                "amount_thb": abs(total_thb),
            })
            continue

        # Get ownership % from column E if available
        ownership = _safe_float(row[4].value) if len(row) > 4 else None

        comment = row[5].value if len(row) > 5 else None

        my_share = total_thb  # In div sheets, total_thb is already the investor's share
        insert_dividend(conn, {
            "restaurant_id": restaurant["id"],
            "date": date_str,
            "total_thb": total_thb,
            "my_share_thb": my_share,
            "comment": str(comment) if comment else None,
        })

    # Look for ownership and investment summary in the bottom rows
    _import_summary_block(conn, ws, restaurant)


def _import_summary_block(conn, ws, restaurant):
    """Extract ownership % and investment amount from the summary block at bottom of div sheets."""
    for row in ws.iter_rows(values_only=False):
        cell_a = row[0].value
        if cell_a is None:
            continue
        cell_str = str(cell_a).strip().lower()

        if "my shares" in cell_str or "% of shares" in cell_str:
            # Next cell or cell B might have the percentage
            pct = _safe_float(row[1].value) if len(row) > 1 else None
            if pct is not None:
                # Convert from decimal to percentage if needed
                if pct < 1:
                    pct = pct * 100
                insert_ownership(conn, {
                    "restaurant_id": restaurant["id"],
                    "effective_date": "2022-01-01",  # Default; will be refined
                    "ownership_pct": pct,
                })


def _import_pl_detail_sheet(conn, ws, restaurant, year):
    """Import a detailed P&L sheet (Cocotte 22, Mozza EMQ 23, etc.)."""
    # These sheets have months as columns, 4 columns per month (label, value, ratio, spacer)
    # Row 4: TOTAL REVENUE, Row 8: Food cost, Row 9: Bev cost, Row 10: Total F&B,
    # Row 12: Total Other Ex, Row 14: TOTAL MONTHLY EXP, Row 15: GOP before fee

    # Find month columns by reading row 1 (month names)
    month_cols = []
    for col_idx, cell in enumerate(ws[1]):
        if cell.value and isinstance(cell.value, str):
            # Check if it looks like a month name
            val = cell.value.strip().lower()
            for month_name, month_num in [
                ("january", 1), ("february", 2), ("march", 3), ("april", 4),
                ("may", 5), ("june", 6), ("july", 7), ("august", 8),
                ("september", 9), ("october", 10), ("november", 11), ("december", 12),
                ("jan", 1), ("feb", 2), ("mar", 3), ("apr", 4),
                ("jun", 6), ("jul", 7), ("aug", 8), ("sep", 9),
                ("oct", 10), ("nov", 11), ("dec", 12),
            ]:
                if val.startswith(month_name):
                    month_cols.append((col_idx, month_num))
                    break

    # Field rows (0-indexed)
    field_rows = {
        3: "revenue",       # Row 4
        4: "revenue_n1",    # Row 5
        6: "rebate",        # Row 7
        7: "food_cost",     # Row 8
        8: "beverage_cost", # Row 9
        9: "total_fb_cost", # Row 10
        11: "total_other_expenses",  # Row 12
        13: "total_monthly_exp",     # Row 14
        14: "gop_before_fee",        # Row 15
    }

    for col_idx, month_num in month_cols:
        month_str = f"{year}-{month_num:02d}-01"
        pl = {"restaurant_id": restaurant["id"], "month": month_str}

        for row_idx, field in field_rows.items():
            cell = ws.cell(row=row_idx + 1, column=col_idx + 2)  # Value is in col+1 (0-indexed → 1-indexed +1)
            pl[field] = _safe_float(cell.value)

        # Derive gop_net = gop_before_fee (unless we find it explicitly)
        pl["gop_net"] = pl.get("gop_before_fee")
        pl["other_special_fee"] = 0
        pl["monthly_provision"] = 0

        if pl.get("revenue") and pl["revenue"] > 0:
            upsert_monthly_pl(conn, pl)


def import_xlsx(conn, filepath):
    """Import all data from the historical Excel file."""
    wb = openpyxl.load_workbook(filepath, data_only=True)

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        restaurant = _match_restaurant(sheet_name)
        if restaurant is None:
            continue

        if "val." in sheet_name:
            _import_valuation_sheet(conn, ws, restaurant)
        elif "div." in sheet_name:
            _import_dividend_sheet(conn, ws, restaurant)
        else:
            # P&L detail sheet like "Cocotte 23", "Mozza EMQ 24"
            year_match = re.search(r"(\d{2,4})$", sheet_name.strip())
            if year_match:
                year = int(year_match.group(1))
                if year < 100:
                    year += 2000
                _import_pl_detail_sheet(conn, ws, restaurant, year)
```

- [ ] **Step 4: Run tests and iterate**

Run: `python -m pytest tests/test_import_xlsx.py -v`

The import logic will likely need iteration based on actual cell positions and formatting in the spreadsheet. Debug by printing cell values:

```python
# Temporary debug: print first few rows of a sheet
ws = wb["Mozza EMQ val."]
for row in ws.iter_rows(min_row=1, max_row=5, values_only=True):
    print(row)
```

Expected: All 7 tests PASS after iteration.

- [ ] **Step 5: Commit**

```bash
git add ingestion/import_xlsx.py tests/test_import_xlsx.py
git commit -m "feat: add historical Excel import for all restaurant data"
```

---

### Task 4: CLI Entry Point

**Files:**
- Create: `ingestion/cli.py`

- [ ] **Step 1: Implement cli.py**

Create `ingestion/cli.py`:

```python
import argparse
import glob
import os
import sys

from ingestion.db import (
    create_schema,
    get_connection,
    insert_dividend,
    insert_investment,
    insert_ownership,
    insert_restaurant,
    upsert_monthly_pl,
)
from ingestion.import_xlsx import import_xlsx
from ingestion.parse_eml import parse_eml_file

# Known restaurant name → id mapping for email subject matching
RESTAURANT_NAME_MAP = {
    "Mozza EmQuartier": "mozza-emq",
    "Mozza Emquartier": "mozza-emq",
    "Cocotte": "cocotte-39",
    "Mozza Paragon": "mozza-prg",
    "Mozza Icon Siam": "mozza-icsm",
    "Mozza IconSiam": "mozza-icsm",
    "Mozza Central Park": "mozza-cp",
    "Parma Eastville": "parma-eastville",
    "Parma Central Eastville": "parma-eastville",
}


def _resolve_restaurant_id(parsed):
    """Resolve restaurant id from parsed email data."""
    # Try by subject restaurant name
    name = parsed["restaurant_name"]
    if name in RESTAURANT_NAME_MAP:
        return RESTAURANT_NAME_MAP[name]
    # Try case-insensitive
    for key, rid in RESTAURANT_NAME_MAP.items():
        if key.lower() == name.lower():
            return rid
    return None


def cmd_import_xlsx(args):
    conn = get_connection(args.db)
    create_schema(conn)
    import_xlsx(conn, args.file)
    conn.close()

    # Print summary
    conn = get_connection(args.db)
    for table in ["restaurants", "monthly_pl", "dividends", "investments", "ownership"]:
        count = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count} rows")
    conn.close()
    print("Import complete.")


def cmd_ingest(args):
    conn = get_connection(args.db)
    create_schema(conn)

    eml_files = sorted(glob.glob(os.path.join(args.inbox, "*.eml")))
    if not eml_files:
        print(f"No .eml files found in {args.inbox}")
        return

    imported = 0
    skipped = 0
    errors = 0

    for filepath in eml_files:
        filename = os.path.basename(filepath)
        try:
            parsed = parse_eml_file(filepath)
            restaurant_id = _resolve_restaurant_id(parsed)
            if not restaurant_id:
                print(f"  SKIP {filename}: unknown restaurant '{parsed['restaurant_name']}'")
                skipped += 1
                continue

            # Ensure restaurant exists
            insert_restaurant(conn, {
                "id": restaurant_id,
                "name": parsed["restaurant_name"],
                "restaurant_code": parsed.get("restaurant_code"),
                "opening_date": None,
            })

            pl = parsed["pl"]
            pl["restaurant_id"] = restaurant_id
            pl["month"] = parsed["month"]
            upsert_monthly_pl(conn, pl)

            if parsed.get("dividend"):
                insert_dividend(conn, {
                    "restaurant_id": restaurant_id,
                    "date": parsed["month"],  # Use report month as dividend date
                    "total_thb": None,
                    "my_share_thb": parsed["dividend"]["my_share_thb"],
                    "comment": f"from {filename}",
                })
                print(f"  OK {filename} (+ dividend: ฿{parsed['dividend']['my_share_thb']:,.0f})")
            else:
                print(f"  OK {filename}")
            imported += 1

        except Exception as e:
            print(f"  ERR {filename}: {e}")
            errors += 1

    conn.close()
    print(f"\nDone: {imported} imported, {skipped} skipped, {errors} errors")


def cmd_update_ownership(args):
    conn = get_connection(args.db)
    create_schema(conn)
    insert_ownership(conn, {
        "restaurant_id": args.restaurant_id,
        "effective_date": args.date,
        "ownership_pct": args.pct,
    })
    conn.close()
    print(f"Updated ownership: {args.restaurant_id} = {args.pct}% from {args.date}")


def cmd_add_investment(args):
    conn = get_connection(args.db)
    create_schema(conn)
    insert_investment(conn, {
        "restaurant_id": args.restaurant_id,
        "date": args.date,
        "amount_thb": args.amount,
    })
    conn.close()
    print(f"Added investment: {args.restaurant_id} ฿{args.amount:,.0f} on {args.date}")


def cmd_add_dividend(args):
    conn = get_connection(args.db)
    create_schema(conn)
    insert_dividend(conn, {
        "restaurant_id": args.restaurant_id,
        "date": args.date,
        "total_thb": args.total,
        "my_share_thb": args.my_share,
        "comment": args.comment,
    })
    conn.close()
    print(f"Added dividend: {args.restaurant_id} ฿{args.my_share:,.0f} on {args.date}")


def main():
    parser = argparse.ArgumentParser(prog="ingestion", description="Restaurant portfolio data ingestion")
    parser.add_argument("--db", default=None, help="Path to DuckDB file (default: data/portfolio.duckdb)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # import-xlsx
    p_import = subparsers.add_parser("import-xlsx", help="One-time import from Excel spreadsheet")
    p_import.add_argument("file", help="Path to .xlsx file")
    p_import.set_defaults(func=cmd_import_xlsx)

    # ingest
    p_ingest = subparsers.add_parser("ingest", help="Ingest .eml files from inbox")
    p_ingest.add_argument("inbox", help="Path to inbox directory")
    p_ingest.set_defaults(func=cmd_ingest)

    # update-ownership
    p_own = subparsers.add_parser("update-ownership", help="Update ownership percentage")
    p_own.add_argument("restaurant_id", help="Restaurant slug (e.g. mozza-emq)")
    p_own.add_argument("--date", required=True, help="Effective date (YYYY-MM-DD)")
    p_own.add_argument("--pct", required=True, type=float, help="Ownership percentage")
    p_own.set_defaults(func=cmd_update_ownership)

    # add-investment
    p_inv = subparsers.add_parser("add-investment", help="Record an investment")
    p_inv.add_argument("restaurant_id", help="Restaurant slug")
    p_inv.add_argument("--date", required=True, help="Date (YYYY-MM-DD)")
    p_inv.add_argument("--amount", required=True, type=float, help="Amount in THB")
    p_inv.set_defaults(func=cmd_add_investment)

    # add-dividend
    p_div = subparsers.add_parser("add-dividend", help="Record a dividend manually")
    p_div.add_argument("restaurant_id", help="Restaurant slug")
    p_div.add_argument("--date", required=True, help="Date (YYYY-MM-DD)")
    p_div.add_argument("--total", type=float, default=None, help="Total distribution THB")
    p_div.add_argument("--my-share", required=True, type=float, help="Your share in THB")
    p_div.add_argument("--comment", default=None, help="Comment")
    p_div.set_defaults(func=cmd_add_dividend)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test CLI manually**

Run: `python -m ingestion.cli import-xlsx hma-22-26.xlsx`
Expected: Prints row counts for each table. No errors.

Run: `python -m ingestion.cli ingest inbox/`
Expected: Processes all 7 .eml files, prints OK for each.

- [ ] **Step 3: Verify data in DuckDB**

Run: `python -c "import duckdb; conn = duckdb.connect('data/portfolio.duckdb'); print(conn.execute('SELECT restaurant_id, count(*) FROM monthly_pl GROUP BY 1 ORDER BY 1').fetchall())"`
Expected: Shows row counts per restaurant.

- [ ] **Step 4: Commit**

```bash
git add ingestion/cli.py
git commit -m "feat: add CLI for data ingestion (import-xlsx, ingest, manual commands)"
```

---

### Task 5: Evidence Dashboard Setup & Portfolio Overview

**Files:**
- Create: `dashboard/` (Evidence project via degit)
- Create: `dashboard/sources/portfolio/connection.yaml`
- Create: `dashboard/pages/index.md`

- [ ] **Step 1: Create Evidence project**

Run:
```bash
cd /Users/doweig/dev/personal-finance
npx degit evidence-dev/template dashboard
cd dashboard
npm install
```

Expected: Evidence project scaffolded in `dashboard/`.

- [ ] **Step 2: Configure DuckDB source**

Run: `mkdir -p dashboard/sources/portfolio`

Create `dashboard/sources/portfolio/connection.yaml`:

```yaml
name: portfolio
type: duckdb
options:
  filename: ../../../data/portfolio.duckdb
```

- [ ] **Step 3: Run sources to verify connection**

Run:
```bash
cd /Users/doweig/dev/personal-finance/dashboard
npm run sources
```

Expected: Extracts data from DuckDB without errors.

- [ ] **Step 4: Write portfolio overview page**

Replace `dashboard/pages/index.md` with:

````markdown
---
title: Portfolio Overview
---

```sql kpi_invested
select coalesce(sum(amount_thb), 0) as total_invested
from portfolio.investments
```

```sql kpi_dividends
select coalesce(sum(my_share_thb), 0) as total_dividends
from portfolio.dividends
```

```sql latest_valuations
with monthly_enriched as (
    select
        pl.restaurant_id,
        pl.month,
        pl.revenue,
        pl.gop_net,
        avg(pl.revenue) over (
            partition by pl.restaurant_id
            order by pl.month
            rows between 11 preceding and current row
        ) as revenue_12sma,
        avg(pl.gop_net) over (
            partition by pl.restaurant_id
            order by pl.month
            rows between 11 preceding and current row
        ) as gop_net_12sma,
        count(*) over (
            partition by pl.restaurant_id
            order by pl.month
            rows between 11 preceding and current row
        ) as window_size
    from portfolio.monthly_pl pl
),
valuations as (
    select
        restaurant_id,
        month,
        case when window_size >= 12 then revenue_12sma * 12 end as revenue_valuation,
        case when window_size >= 12 then gop_net_12sma * 12 * 4 end as income_valuation,
        case when window_size >= 12 then (revenue_12sma * 12 + gop_net_12sma * 12 * 4) / 2 end as blended_valuation,
        row_number() over (partition by restaurant_id order by month desc) as rn
    from monthly_enriched
)
select restaurant_id, blended_valuation
from valuations
where rn = 1 and blended_valuation is not null
```

```sql kpi_valuation
select
    coalesce(sum(v.blended_valuation * o.ownership_pct / 100), 0) as portfolio_valuation
from ${latest_valuations} v
join (
    select restaurant_id, ownership_pct,
        row_number() over (partition by restaurant_id order by effective_date desc) as rn
    from portfolio.ownership
) o on v.restaurant_id = o.restaurant_id and o.rn = 1
```

```sql restaurant_summary
with latest_pl as (
    select restaurant_id, month,
        row_number() over (partition by restaurant_id order by month desc) as rn
    from portfolio.monthly_pl
),
latest_ownership as (
    select restaurant_id, ownership_pct,
        row_number() over (partition by restaurant_id order by effective_date desc) as rn
    from portfolio.ownership
),
total_invested as (
    select restaurant_id, sum(amount_thb) as invested
    from portfolio.investments
    group by restaurant_id
),
total_divs as (
    select restaurant_id, sum(my_share_thb) as total_dividends
    from portfolio.dividends
    group by restaurant_id
)
select
    r.id,
    r.name,
    '/restaurants/' || r.id as link,
    o.ownership_pct,
    i.invested,
    v.blended_valuation * o.ownership_pct / 100 as my_valuation,
    d.total_dividends,
    lp.month as latest_month
from portfolio.restaurants r
left join latest_ownership o on r.id = o.restaurant_id and o.rn = 1
left join total_invested i on r.id = i.restaurant_id
left join total_divs d on r.id = d.restaurant_id
left join latest_pl lp on r.id = lp.restaurant_id and lp.rn = 1
left join ${latest_valuations} v on r.id = v.restaurant_id
order by i.invested desc nulls last
```

<BigValue
    data={kpi_invested}
    value=total_invested
    title="Total Invested"
    fmt='#,##0 "THB"'
/>

<BigValue
    data={kpi_valuation}
    value=portfolio_valuation
    title="Portfolio Valuation (My Share)"
    fmt='#,##0 "THB"'
/>

<BigValue
    data={kpi_dividends}
    value=total_dividends
    title="Total Dividends Received"
    fmt='#,##0 "THB"'
/>

## My Restaurants

<DataTable data={restaurant_summary} link=link>
    <Column id=name title="Restaurant" />
    <Column id=ownership_pct title="Ownership %" fmt='0.00"%"' />
    <Column id=invested title="Invested" fmt='#,##0' />
    <Column id=my_valuation title="Valuation (My Share)" fmt='#,##0' />
    <Column id=total_dividends title="Total Dividends" fmt='#,##0' />
    <Column id=latest_month title="Latest Month" />
</DataTable>
````

- [ ] **Step 5: Test the dashboard**

Run:
```bash
cd /Users/doweig/dev/personal-finance/dashboard
npm run sources
npm run dev
```

Open http://localhost:3000. Verify:
- KPI cards show values
- Restaurant table renders with data
- Clicking a restaurant name navigates (will 404 until Task 6)

- [ ] **Step 6: Commit**

```bash
git add dashboard/sources/ dashboard/pages/index.md dashboard/package.json dashboard/package-lock.json dashboard/evidence.config.yaml dashboard/.gitignore
git commit -m "feat: add Evidence dashboard with portfolio overview page"
```

---

### Task 6: Restaurant Detail Page

**Files:**
- Create: `dashboard/pages/restaurants/[restaurant].md`

- [ ] **Step 1: Create restaurant detail page**

Run: `mkdir -p dashboard/pages/restaurants`

Create `dashboard/pages/restaurants/[restaurant].md`:

````markdown
---
title: "{params.restaurant}"
---

```sql restaurant_info
select name, restaurant_code
from portfolio.restaurants
where id = '${params.restaurant}'
```

# {restaurant_info[0].name}

```sql monthly_data
select
    pl.month,
    pl.revenue,
    pl.revenue_n1,
    pl.food_cost,
    pl.beverage_cost,
    pl.total_fb_cost,
    pl.total_other_expenses,
    pl.total_monthly_exp,
    pl.gop_before_fee,
    pl.gop_net,
    pl.rebate,
    case when pl.revenue > 0 then pl.gop_net / pl.revenue * 100 end as gop_margin_pct,
    case when pl.revenue > 0 then pl.total_fb_cost / pl.revenue * 100 end as fb_cost_pct,
    case when pl.revenue > 0 then pl.gop_net / pl.revenue end as earnings_yield,
    avg(pl.revenue) over (order by pl.month rows between 11 preceding and current row) as revenue_12sma,
    avg(pl.gop_net) over (order by pl.month rows between 11 preceding and current row) as gop_net_12sma,
    avg(case when pl.revenue > 0 then pl.gop_net / pl.revenue end) over (order by pl.month rows between 11 preceding and current row) as ey_12sma,
    count(*) over (order by pl.month rows between 11 preceding and current row) as window_size
from portfolio.monthly_pl pl
where pl.restaurant_id = '${params.restaurant}'
order by pl.month
```

```sql valuations
select
    month,
    case when window_size >= 12 then revenue_12sma * 12 end as revenue_valuation,
    case when window_size >= 12 then gop_net_12sma * 12 * 4 end as income_valuation,
    case when window_size >= 12 then (revenue_12sma * 12 + gop_net_12sma * 12 * 4) / 2 end as blended_valuation
from ${monthly_data}
where window_size >= 12
```

## Revenue

<LineChart
    data={monthly_data}
    x=month
    y={["revenue", "revenue_n1"]}
    yAxisTitle="THB"
    title="Monthly Revenue vs Prior Year"
    yFmt='#,##0'
/>

## GOP & Margins

<LineChart
    data={monthly_data}
    x=month
    y=gop_net
    yAxisTitle="THB"
    title="GOP Net"
    yFmt='#,##0'
/>

<LineChart
    data={monthly_data}
    x=month
    y={["gop_margin_pct", "fb_cost_pct"]}
    yAxisTitle="%"
    title="GOP Margin & F&B Cost %"
    yFmt='0.0'
/>

## Earnings Yield

<LineChart
    data={monthly_data}
    x=month
    y={["earnings_yield", "ey_12sma"]}
    title="Earnings Yield (Monthly & 12m SMA)"
    yFmt='0.00'
/>

## Valuation

<LineChart
    data={valuations}
    x=month
    y={["revenue_valuation", "income_valuation", "blended_valuation"]}
    yAxisTitle="THB"
    title="Valuation Methods"
    yFmt='#,##0'
/>

## Monthly P&L

<DataTable data={monthly_data} rows=all>
    <Column id=month title="Month" />
    <Column id=revenue title="Revenue" fmt='#,##0' />
    <Column id=total_fb_cost title="F&B Cost" fmt='#,##0' />
    <Column id=total_other_expenses title="Other Exp" fmt='#,##0' />
    <Column id=gop_net title="GOP Net" fmt='#,##0' />
    <Column id=gop_margin_pct title="GOP %" fmt='0.0"%"' />
</DataTable>
````

- [ ] **Step 2: Test the page**

Run:
```bash
cd /Users/doweig/dev/personal-finance/dashboard
npm run sources
npm run dev
```

Open http://localhost:3000/restaurants/mozza-emq. Verify:
- Revenue chart shows data
- GOP chart renders
- Valuation chart appears (may be empty for restaurants with < 12 months data)
- P&L table shows all months

- [ ] **Step 3: Commit**

```bash
git add dashboard/pages/restaurants/
git commit -m "feat: add per-restaurant financial detail page"
```

---

### Task 7: My Returns Page

**Files:**
- Create: `dashboard/pages/returns.md`
- Create: `dashboard/components/IRRCalculator.svelte`

- [ ] **Step 1: Create IRR calculator component**

Run: `mkdir -p dashboard/components`

Create `dashboard/components/IRRCalculator.svelte`:

```svelte
<script>
    export let cashflows = [];  // array of {months_ago: number, amount: number}

    function solveIRR(cfs, guess = 0.01, maxIter = 200, tol = 1e-8) {
        let r = guess;
        for (let i = 0; i < maxIter; i++) {
            let npv = 0;
            let dnpv = 0;
            for (const cf of cfs) {
                const t = cf.months_ago;
                const pv = cf.amount / Math.pow(1 + r, t);
                npv += pv;
                dnpv -= t * cf.amount / Math.pow(1 + r, t + 1);
            }
            if (Math.abs(npv) < tol) break;
            if (Math.abs(dnpv) < tol) break;
            r = r - npv / dnpv;
            if (r < -0.99) r = -0.5;
            if (r > 10) r = 1;
        }
        return r;
    }

    $: monthlyIRR = cashflows.length > 0 ? solveIRR(cashflows) : null;
    $: annualIRR = monthlyIRR !== null ? Math.pow(1 + monthlyIRR, 12) - 1 : null;
</script>

{#if monthlyIRR !== null}
    <div style="display: flex; gap: 1rem;">
        <div>
            <div style="font-size: 0.75rem; color: var(--grey-600); text-transform: uppercase;">Monthly IRR</div>
            <div style="font-size: 1.5rem; font-weight: 700;">{(monthlyIRR * 100).toFixed(2)}%</div>
        </div>
        <div>
            <div style="font-size: 0.75rem; color: var(--grey-600); text-transform: uppercase;">Annualized</div>
            <div style="font-size: 1.5rem; font-weight: 700;">{(annualIRR * 100).toFixed(1)}%</div>
        </div>
    </div>
{:else}
    <div style="color: var(--grey-500);">Insufficient data for IRR calculation</div>
{/if}
```

- [ ] **Step 2: Create returns page**

Create `dashboard/pages/returns.md`:

````markdown
---
title: My Returns
---

```sql dividend_history
select
    d.restaurant_id,
    r.name as restaurant_name,
    d.date,
    d.my_share_thb,
    d.comment,
    sum(d.my_share_thb) over (partition by d.restaurant_id order by d.date) as cumulative
from portfolio.dividends d
join portfolio.restaurants r on d.restaurant_id = r.id
where d.my_share_thb > 0
order by d.date
```

```sql cumulative_by_restaurant
select
    date,
    restaurant_name,
    sum(my_share_thb) over (partition by restaurant_name order by date) as cumulative_dividends
from ${dividend_history}
```

```sql roi_summary
with invested as (
    select restaurant_id, sum(amount_thb) as total_invested
    from portfolio.investments
    group by restaurant_id
),
divs as (
    select restaurant_id, sum(my_share_thb) as total_dividends
    from portfolio.dividends
    where my_share_thb > 0
    group by restaurant_id
),
first_investment as (
    select restaurant_id, min(date) as first_date
    from portfolio.investments
    group by restaurant_id
),
avg_monthly_div as (
    select
        restaurant_id,
        avg(my_share_thb) as avg_monthly
    from portfolio.dividends
    where my_share_thb > 0
    group by restaurant_id
)
select
    r.name,
    i.total_invested,
    coalesce(d.total_dividends, 0) as total_dividends,
    case when i.total_invested > 0 then coalesce(d.total_dividends, 0) / i.total_invested * 100 end as roi_pct,
    fi.first_date as invested_since,
    case when m.avg_monthly > 0 then i.total_invested / m.avg_monthly end as months_to_roi
from portfolio.restaurants r
join invested i on r.id = i.restaurant_id
left join divs d on r.id = d.restaurant_id
left join first_investment fi on r.id = fi.restaurant_id
left join avg_monthly_div m on r.id = m.restaurant_id
order by roi_pct desc nulls last
```

```sql cashflows_for_irr
select
    restaurant_id,
    r.name as restaurant_name,
    'investment' as type,
    i.date,
    -i.amount_thb as amount
from portfolio.investments i
join portfolio.restaurants r on i.restaurant_id = r.id
union all
select
    restaurant_id,
    r.name as restaurant_name,
    'dividend' as type,
    d.date,
    d.my_share_thb as amount
from portfolio.dividends d
join portfolio.restaurants r on d.restaurant_id = r.id
where d.my_share_thb > 0
order by date
```

# My Returns

## ROI Summary

<DataTable data={roi_summary}>
    <Column id=name title="Restaurant" />
    <Column id=total_invested title="Total Invested" fmt='#,##0' />
    <Column id=total_dividends title="Total Dividends" fmt='#,##0' />
    <Column id=roi_pct title="ROI %" fmt='0.0"%"' />
    <Column id=invested_since title="Since" />
    <Column id=months_to_roi title="Months to ROI" fmt='0.0' />
</DataTable>

## Cumulative Dividends

<LineChart
    data={cumulative_by_restaurant}
    x=date
    y=cumulative_dividends
    series=restaurant_name
    yAxisTitle="THB"
    title="Cumulative Dividends by Restaurant"
    yFmt='#,##0'
/>

## IRR

<script>
    function monthsDiff(d1, d2) {
        const a = new Date(d1);
        const b = new Date(d2);
        return (b.getFullYear() - a.getFullYear()) * 12 + (b.getMonth() - a.getMonth());
    }

    const now = new Date();
    const refDate = now.toISOString().slice(0, 10);

    $: cashflowsByRestaurant = {};
    $: {
        const grouped = {};
        if (cashflows_for_irr) {
            for (const row of cashflows_for_irr) {
                const rid = row.restaurant_name;
                if (!grouped[rid]) grouped[rid] = [];
                grouped[rid].push({
                    months_ago: monthsDiff(row.date, refDate),
                    amount: row.amount,
                });
            }
        }
        cashflowsByRestaurant = grouped;
    }
</script>

{#each Object.entries(cashflowsByRestaurant) as [name, cfs]}

### {name}

<IRRCalculator cashflows={cfs} />

{/each}

## Dividend History

<DataTable data={dividend_history} rows=all>
    <Column id=restaurant_name title="Restaurant" />
    <Column id=date title="Date" />
    <Column id=my_share_thb title="My Share (THB)" fmt='#,##0' />
    <Column id=cumulative title="Cumulative" fmt='#,##0' />
    <Column id=comment title="Comment" />
</DataTable>
````

- [ ] **Step 3: Test the returns page**

Run:
```bash
cd /Users/doweig/dev/personal-finance/dashboard
npm run sources
npm run dev
```

Open http://localhost:3000/returns. Verify:
- ROI summary table shows all restaurants with investments
- Cumulative dividends chart renders with one line per restaurant
- IRR section shows calculated values per restaurant
- Dividend history table shows all dividend records

- [ ] **Step 4: Commit**

```bash
git add dashboard/components/IRRCalculator.svelte dashboard/pages/returns.md
git commit -m "feat: add returns page with dividend tracking and IRR calculator"
```

---

### Task 8: End-to-End Verification

- [ ] **Step 1: Clean rebuild — delete DB and reimport everything**

Run:
```bash
rm -f data/portfolio.duckdb
python -m ingestion.cli import-xlsx hma-22-26.xlsx
python -m ingestion.cli ingest inbox/
```

Expected: Both commands succeed. Import shows row counts, ingest shows OK for all .eml files.

- [ ] **Step 2: Verify data completeness**

Run:
```python
python -c "
import duckdb
conn = duckdb.connect('data/portfolio.duckdb')
print('=== Restaurants ===')
for r in conn.execute('SELECT * FROM restaurants ORDER BY id').fetchall():
    print(f'  {r}')
print()
print('=== Monthly P&L counts ===')
for r in conn.execute('SELECT restaurant_id, count(*), min(month), max(month) FROM monthly_pl GROUP BY 1 ORDER BY 1').fetchall():
    print(f'  {r}')
print()
print('=== Dividends ===')
for r in conn.execute('SELECT restaurant_id, count(*), sum(my_share_thb) FROM dividends WHERE my_share_thb > 0 GROUP BY 1 ORDER BY 1').fetchall():
    print(f'  {r}')
print()
print('=== Investments ===')
for r in conn.execute('SELECT * FROM investments ORDER BY restaurant_id').fetchall():
    print(f'  {r}')
print()
print('=== Ownership ===')
for r in conn.execute('SELECT * FROM ownership ORDER BY restaurant_id').fetchall():
    print(f'  {r}')
conn.close()
"
```

Expected: 6 restaurants, P&L data spanning 2022-2026, dividends and investments for all 5 original restaurants.

- [ ] **Step 3: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS.

- [ ] **Step 4: Launch dashboard and check all pages**

Run:
```bash
cd /Users/doweig/dev/personal-finance/dashboard
npm run sources
npm run dev
```

Verify:
- http://localhost:3000 — Portfolio overview with KPI cards and table
- http://localhost:3000/restaurants/mozza-emq — Charts and P&L table
- http://localhost:3000/restaurants/cocotte-39 — Same
- http://localhost:3000/returns — ROI table, cumulative chart, IRR values

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete restaurant portfolio tracker — ingestion + dashboard"
```
