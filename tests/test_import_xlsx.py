"""Tests for the historical Excel importer."""

from pathlib import Path

import duckdb
import pytest

from ingestion.db import create_schema
from ingestion.import_xlsx import import_xlsx

XLSX_PATH = Path(__file__).resolve().parent.parent / "hma-22-26.xlsx"


@pytest.fixture(scope="module")
def loaded_conn():
    """In-memory DuckDB with schema created and Excel data imported."""
    conn = duckdb.connect(":memory:")
    create_schema(conn)
    import_xlsx(conn, XLSX_PATH)
    yield conn
    conn.close()


def test_imports_all_restaurants(loaded_conn):
    """5 restaurant IDs should be present."""
    rows = loaded_conn.execute("SELECT id FROM restaurants ORDER BY id").fetchall()
    ids = [r[0] for r in rows]
    assert len(ids) == 5
    assert set(ids) == {"mozza-emq", "cocotte-39", "mozza-prg", "mozza-icsm", "mozza-cp"}


def test_imports_monthly_pl_data(loaded_conn):
    """mozza-emq should have >= 40 months of P&L data."""
    count = loaded_conn.execute(
        "SELECT COUNT(*) FROM monthly_pl WHERE restaurant_id = 'mozza-emq'"
    ).fetchone()[0]
    assert count >= 40, f"Expected >= 40 months for mozza-emq, got {count}"


def test_imports_dividends(loaded_conn):
    """mozza-emq should have dividend records."""
    count = loaded_conn.execute(
        "SELECT COUNT(*) FROM dividends WHERE restaurant_id = 'mozza-emq'"
    ).fetchone()[0]
    assert count > 0, "Expected dividend records for mozza-emq"


def test_imports_investments(loaded_conn):
    """mozza-emq investment should be 12,105,000 THB."""
    amount = loaded_conn.execute(
        "SELECT amount_thb FROM investments WHERE restaurant_id = 'mozza-emq'"
    ).fetchone()[0]
    assert amount == 12_105_000


def test_imports_ownership(loaded_conn):
    """mozza-emq ownership should be approximately 10.6891%."""
    pct = loaded_conn.execute(
        "SELECT ownership_pct FROM ownership WHERE restaurant_id = 'mozza-emq'"
    ).fetchone()[0]
    assert abs(pct - 10.6891) < 0.001


def test_imports_cocotte_investments(loaded_conn):
    """cocotte-39 investment should be 25,325,000 THB."""
    amount = loaded_conn.execute(
        "SELECT amount_thb FROM investments WHERE restaurant_id = 'cocotte-39'"
    ).fetchone()[0]
    assert amount == 25_325_000


def test_pl_has_revenue_and_gop(loaded_conn):
    """mozza-emq Jan 2023 should have revenue > 0 and gop_net not None."""
    row = loaded_conn.execute(
        "SELECT revenue, gop_net FROM monthly_pl "
        "WHERE restaurant_id = 'mozza-emq' AND month = '2023-01-01'"
    ).fetchone()
    assert row is not None, "No P&L record for mozza-emq Jan 2023"
    revenue, gop_net = row
    assert revenue is not None and revenue > 0, f"Revenue should be > 0, got {revenue}"
    assert gop_net is not None, "gop_net should not be None"
