"""Tests for ingestion.db schema and data access functions."""

from ingestion.db import (
    create_schema,
    insert_dividend,
    insert_investment,
    insert_ownership,
    insert_restaurant,
    upsert_monthly_pl,
)


EXPECTED_TABLES = {"restaurants", "ownership", "investments", "monthly_pl", "dividends"}


def _helper_insert_restaurant(conn, rid="r1"):
    """Helper to insert a restaurant so FK constraints are satisfied."""
    insert_restaurant(conn, {"id": rid, "name": f"Restaurant {rid}"})


class TestCreateSchema:
    def test_creates_all_tables(self, conn):
        tables = {r[0] for r in conn.execute("SHOW TABLES").fetchall()}
        assert tables == EXPECTED_TABLES

    def test_idempotent(self, conn):
        """Calling create_schema twice does not raise."""
        create_schema(conn)
        tables = {r[0] for r in conn.execute("SHOW TABLES").fetchall()}
        assert tables == EXPECTED_TABLES


class TestUpsertMonthlyPL:
    def test_insert_new_row(self, conn):
        _helper_insert_restaurant(conn)
        row = {
            "restaurant_id": "r1",
            "month": "2025-01-01",
            "revenue": 100_000.0,
            "revenue_n1": 90_000.0,
            "food_cost": 30_000.0,
            "beverage_cost": 10_000.0,
            "total_fb_cost": 40_000.0,
            "total_other_expenses": 20_000.0,
            "total_monthly_exp": 60_000.0,
            "gop_before_fee": 40_000.0,
            "gop_net": 38_000.0,
        }
        upsert_monthly_pl(conn, row)
        result = conn.execute(
            "SELECT revenue FROM monthly_pl WHERE restaurant_id='r1' AND month='2025-01-01'"
        ).fetchone()
        assert result[0] == 100_000.0

    def test_update_existing_row(self, conn):
        _helper_insert_restaurant(conn)
        row = {
            "restaurant_id": "r1",
            "month": "2025-01-01",
            "revenue": 100_000.0,
            "gop_net": 38_000.0,
        }
        upsert_monthly_pl(conn, row)

        # Update with new revenue
        row["revenue"] = 120_000.0
        row["gop_net"] = 45_000.0
        upsert_monthly_pl(conn, row)

        result = conn.execute(
            "SELECT revenue, gop_net FROM monthly_pl WHERE restaurant_id='r1' AND month='2025-01-01'"
        ).fetchone()
        assert result[0] == 120_000.0
        assert result[1] == 45_000.0

        # Only one row (idempotent)
        count = conn.execute("SELECT COUNT(*) FROM monthly_pl").fetchone()[0]
        assert count == 1


class TestInsertDividend:
    def test_insert(self, conn):
        _helper_insert_restaurant(conn)
        insert_dividend(conn, {
            "restaurant_id": "r1",
            "date": "2025-03-15",
            "total_thb": 50_000.0,
            "my_share_thb": 12_500.0,
            "comment": "Q1 dividend",
        })
        result = conn.execute(
            "SELECT my_share_thb, comment FROM dividends WHERE restaurant_id='r1' AND date='2025-03-15'"
        ).fetchone()
        assert result[0] == 12_500.0
        assert result[1] == "Q1 dividend"

    def test_upsert(self, conn):
        _helper_insert_restaurant(conn)
        row = {
            "restaurant_id": "r1",
            "date": "2025-03-15",
            "total_thb": 50_000.0,
            "my_share_thb": 12_500.0,
            "comment": "Q1 dividend",
        }
        insert_dividend(conn, row)
        row["my_share_thb"] = 13_000.0
        row["comment"] = "revised"
        insert_dividend(conn, row)

        count = conn.execute("SELECT COUNT(*) FROM dividends").fetchone()[0]
        result = conn.execute(
            "SELECT my_share_thb, comment FROM dividends WHERE restaurant_id='r1' AND date='2025-03-15'"
        ).fetchone()
        assert count == 1
        assert result[0] == 13_000.0
        assert result[1] == "revised"


class TestInsertInvestment:
    def test_insert(self, conn):
        _helper_insert_restaurant(conn)
        insert_investment(conn, {
            "restaurant_id": "r1",
            "date": "2024-06-01",
            "amount_thb": 500_000.0,
        })
        result = conn.execute("SELECT amount_thb FROM investments").fetchone()
        assert result[0] == 500_000.0

    def test_upsert(self, conn):
        _helper_insert_restaurant(conn)
        row = {"restaurant_id": "r1", "date": "2024-06-01", "amount_thb": 500_000.0}
        insert_investment(conn, row)
        row["amount_thb"] = 600_000.0
        insert_investment(conn, row)
        count = conn.execute("SELECT COUNT(*) FROM investments").fetchone()[0]
        assert count == 1
        val = conn.execute("SELECT amount_thb FROM investments").fetchone()[0]
        assert val == 600_000.0


class TestInsertOwnership:
    def test_insert(self, conn):
        _helper_insert_restaurant(conn)
        insert_ownership(conn, {
            "restaurant_id": "r1",
            "effective_date": "2024-01-01",
            "ownership_pct": 25.0,
        })
        result = conn.execute("SELECT ownership_pct FROM ownership").fetchone()
        assert result[0] == 25.0

    def test_upsert(self, conn):
        _helper_insert_restaurant(conn)
        row = {"restaurant_id": "r1", "effective_date": "2024-01-01", "ownership_pct": 25.0}
        insert_ownership(conn, row)
        row["ownership_pct"] = 30.0
        insert_ownership(conn, row)
        count = conn.execute("SELECT COUNT(*) FROM ownership").fetchone()[0]
        assert count == 1
        val = conn.execute("SELECT ownership_pct FROM ownership").fetchone()[0]
        assert val == 30.0
