"""Import seed data from CSV files in the data/ directory."""

import csv
from pathlib import Path

from ingestion.db import (
    create_schema,
    insert_dividend,
    insert_investment,
    insert_ownership,
    insert_restaurant,
    upsert_monthly_pl,
)


def _read_csv(filepath):
    """Read a CSV file and return a list of dicts."""
    with open(filepath, newline="") as f:
        return list(csv.DictReader(f))


def _float_or_none(val):
    """Convert a string to float, or None if empty."""
    if val is None or val == "":
        return None
    return float(val)


def import_csv(conn, data_dir):
    """Import all seed data from CSV files.

    Args:
        conn: DuckDB connection (schema must already exist).
        data_dir: Path to directory containing CSV files.
    """
    data_dir = Path(data_dir)

    # 1. Restaurants
    for row in _read_csv(data_dir / "restaurants.csv"):
        insert_restaurant(conn, {
            "id": row["id"],
            "name": row["name"],
            "restaurant_code": row.get("restaurant_code"),
            "opening_date": None,
        })

    # 2. Investments
    for row in _read_csv(data_dir / "investments.csv"):
        insert_investment(conn, {
            "restaurant_id": row["restaurant_id"],
            "date": row["date"],
            "amount_thb": float(row["amount_thb"]),
        })

    # 3. Ownership
    for row in _read_csv(data_dir / "ownership.csv"):
        insert_ownership(conn, {
            "restaurant_id": row["restaurant_id"],
            "effective_date": row["effective_date"],
            "ownership_pct": float(row["ownership_pct"]),
        })

    # 4. Monthly P&L
    for row in _read_csv(data_dir / "monthly_pl.csv"):
        upsert_monthly_pl(conn, {
            "restaurant_id": row["restaurant_id"],
            "month": row["month"] + "-01" if len(row["month"]) == 7 else row["month"],
            "revenue": _float_or_none(row.get("revenue")),
            "revenue_n1": _float_or_none(row.get("revenue_n1")),
            "food_cost": _float_or_none(row.get("food_cost")),
            "beverage_cost": _float_or_none(row.get("beverage_cost")),
            "total_fb_cost": _float_or_none(row.get("total_fb_cost")),
            "total_other_expenses": _float_or_none(row.get("total_other_expenses")),
            "total_monthly_exp": _float_or_none(row.get("total_monthly_exp")),
            "gop_before_fee": _float_or_none(row.get("gop_before_fee")),
            "other_special_fee": _float_or_none(row.get("other_special_fee")) or 0,
            "monthly_provision": _float_or_none(row.get("monthly_provision")) or 0,
            "gop_net": _float_or_none(row.get("gop_net")),
            "rebate": _float_or_none(row.get("rebate")) or 0,
        })

    # 5. Dividends
    for row in _read_csv(data_dir / "dividends.csv"):
        insert_dividend(conn, {
            "restaurant_id": row["restaurant_id"],
            "date": row["date"],
            "total_thb": _float_or_none(row.get("total_thb")),
            "my_share_thb": _float_or_none(row.get("my_share_thb")),
            "comment": row.get("comment") or None,
        })
