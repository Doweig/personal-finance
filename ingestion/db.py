"""DuckDB schema and data access layer for restaurant portfolio tracker."""

from pathlib import Path

import duckdb


def get_connection(db_path=None):
    """Return a DuckDB connection. Default path: data/portfolio.duckdb."""
    if db_path is None:
        db_path = Path(__file__).resolve().parent.parent / "data" / "portfolio.duckdb"
        db_path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(db_path))


def create_schema(conn):
    """Create all tables with proper types and constraints."""
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
            comment TEXT,
            PRIMARY KEY (restaurant_id, date)
        )
    """)


def insert_restaurant(conn, row):
    """Insert or update a restaurant."""
    conn.execute("""
        INSERT INTO restaurants (id, name, restaurant_code, opening_date)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            restaurant_code = EXCLUDED.restaurant_code,
            opening_date = EXCLUDED.opening_date
    """, [row["id"], row["name"], row.get("restaurant_code"), row.get("opening_date")])


def insert_ownership(conn, row):
    """Insert or update an ownership record."""
    conn.execute("""
        INSERT INTO ownership (restaurant_id, effective_date, ownership_pct)
        VALUES ($1, $2, $3)
        ON CONFLICT (restaurant_id, effective_date) DO UPDATE SET
            ownership_pct = EXCLUDED.ownership_pct
    """, [row["restaurant_id"], row["effective_date"], row["ownership_pct"]])


def insert_investment(conn, row):
    """Insert or update an investment record."""
    conn.execute("""
        INSERT INTO investments (restaurant_id, date, amount_thb)
        VALUES ($1, $2, $3)
        ON CONFLICT (restaurant_id, date) DO UPDATE SET
            amount_thb = EXCLUDED.amount_thb
    """, [row["restaurant_id"], row["date"], row["amount_thb"]])


def upsert_monthly_pl(conn, row):
    """Insert or update a monthly P&L record. Key: (restaurant_id, month)."""
    conn.execute("""
        INSERT INTO monthly_pl (
            restaurant_id, month, revenue, revenue_n1,
            food_cost, beverage_cost, total_fb_cost,
            total_other_expenses, total_monthly_exp,
            gop_before_fee, other_special_fee, monthly_provision,
            gop_net, rebate
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
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
        row["restaurant_id"], row["month"], row["revenue"], row.get("revenue_n1"),
        row.get("food_cost"), row.get("beverage_cost"), row.get("total_fb_cost"),
        row.get("total_other_expenses"), row.get("total_monthly_exp"),
        row.get("gop_before_fee"), row.get("other_special_fee", 0),
        row.get("monthly_provision", 0), row.get("gop_net"), row.get("rebate", 0),
    ])


def insert_dividend(conn, row):
    """Insert or update a dividend record."""
    conn.execute("""
        INSERT INTO dividends (restaurant_id, date, total_thb, my_share_thb, comment)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (restaurant_id, date) DO UPDATE SET
            total_thb = EXCLUDED.total_thb,
            my_share_thb = EXCLUDED.my_share_thb,
            comment = EXCLUDED.comment
    """, [
        row["restaurant_id"], row["date"], row["total_thb"],
        row["my_share_thb"], row.get("comment"),
    ])


def clear_all_data(conn):
    """Delete all table rows while preserving schema."""
    for table in ["dividends", "monthly_pl", "investments", "ownership", "restaurants"]:
        conn.execute(f"DELETE FROM {table}")
