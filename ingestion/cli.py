"""CLI entry point for restaurant portfolio data ingestion."""

import argparse
import sys
from pathlib import Path

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

# Reverse lookup: restaurant_id -> canonical name
_ID_TO_NAME = {}
for _name, _rid in RESTAURANT_NAME_MAP.items():
    if _rid not in _ID_TO_NAME:
        _ID_TO_NAME[_rid] = _name


def cmd_import_xlsx(args):
    """Import historical data from Excel file."""
    conn = get_connection(args.db)
    create_schema(conn)
    import_xlsx(conn, args.file)

    # Print row counts
    tables = ["restaurants", "monthly_pl", "dividends", "investments", "ownership"]
    for table in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count} rows")
    conn.close()


def cmd_ingest(args):
    """Process all .eml files in the inbox directory."""
    inbox = Path(args.inbox_dir)
    if not inbox.is_dir():
        print(f"ERROR: {inbox} is not a directory", file=sys.stderr)
        sys.exit(1)

    eml_files = sorted(inbox.glob("*.eml"))
    if not eml_files:
        print(f"No .eml files found in {inbox}")
        return

    conn = get_connection(args.db)
    create_schema(conn)

    imported = 0
    skipped = 0
    errors = 0

    for eml_path in eml_files:
        fname = eml_path.name
        try:
            data = parse_eml_file(eml_path)
        except Exception as e:
            print(f"  ERR  {fname}: {e}")
            errors += 1
            continue

        restaurant_name = data["restaurant_name"]
        restaurant_id = RESTAURANT_NAME_MAP.get(restaurant_name)
        if restaurant_id is None:
            print(f"  SKIP {fname}: unknown restaurant {restaurant_name!r}")
            skipped += 1
            continue

        # Ensure restaurant exists
        canonical_name = _ID_TO_NAME.get(restaurant_id, restaurant_name)
        insert_restaurant(conn, {
            "id": restaurant_id,
            "name": canonical_name,
            "restaurant_code": data.get("restaurant_code"),
        })

        # Upsert P&L
        pl = data["pl"]
        pl["restaurant_id"] = restaurant_id
        pl["month"] = data["month"]
        upsert_monthly_pl(conn, pl)

        # Insert dividend if present
        if data["dividend"] is not None:
            div = data["dividend"]
            insert_dividend(conn, {
                "restaurant_id": restaurant_id,
                "date": data["month"],
                "total_thb": div.get("total_thb", div.get("my_share_thb")),
                "my_share_thb": div["my_share_thb"],
                "comment": None,
            })

        print(f"  OK   {fname}: {restaurant_name} ({data['month']})")
        imported += 1

    conn.close()
    print(f"\nSummary: {imported} imported, {skipped} skipped, {errors} errors")


def cmd_update_ownership(args):
    """Update ownership percentage for a restaurant."""
    conn = get_connection(args.db)
    create_schema(conn)
    insert_ownership(conn, {
        "restaurant_id": args.restaurant_id,
        "effective_date": args.date,
        "ownership_pct": args.pct,
    })
    conn.close()
    print(f"Ownership updated: {args.restaurant_id} = {args.pct}% from {args.date}")


def cmd_add_investment(args):
    """Record an investment."""
    conn = get_connection(args.db)
    create_schema(conn)
    insert_investment(conn, {
        "restaurant_id": args.restaurant_id,
        "date": args.date,
        "amount_thb": args.amount,
    })
    conn.close()
    print(f"Investment recorded: {args.restaurant_id} = {args.amount:,.0f} THB on {args.date}")


def cmd_add_dividend(args):
    """Record a dividend payment."""
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
    print(f"Dividend recorded: {args.restaurant_id} = {args.my_share:,.0f} THB on {args.date}")


def main():
    parser = argparse.ArgumentParser(
        prog="ingestion",
        description="Restaurant portfolio data ingestion CLI",
    )
    parser.add_argument("--db", default=None, help="Path to DuckDB file (default: data/portfolio.duckdb)")
    sub = parser.add_subparsers(dest="command", required=True)

    # import-xlsx
    p_import = sub.add_parser("import-xlsx", help="Import historical Excel file")
    p_import.add_argument("file", help="Path to .xlsx file")
    p_import.set_defaults(func=cmd_import_xlsx)

    # ingest
    p_ingest = sub.add_parser("ingest", help="Process .eml files from inbox")
    p_ingest.add_argument("inbox_dir", help="Directory containing .eml files")
    p_ingest.set_defaults(func=cmd_ingest)

    # update-ownership
    p_own = sub.add_parser("update-ownership", help="Set ownership percentage")
    p_own.add_argument("restaurant_id")
    p_own.add_argument("--date", required=True, help="YYYY-MM-DD")
    p_own.add_argument("--pct", required=True, type=float)
    p_own.set_defaults(func=cmd_update_ownership)

    # add-investment
    p_inv = sub.add_parser("add-investment", help="Record an investment")
    p_inv.add_argument("restaurant_id")
    p_inv.add_argument("--date", required=True, help="YYYY-MM-DD")
    p_inv.add_argument("--amount", required=True, type=float, help="Amount in THB")
    p_inv.set_defaults(func=cmd_add_investment)

    # add-dividend
    p_div = sub.add_parser("add-dividend", help="Record a dividend payment")
    p_div.add_argument("restaurant_id")
    p_div.add_argument("--date", required=True, help="YYYY-MM-DD")
    p_div.add_argument("--total", required=True, type=float, help="Total THB")
    p_div.add_argument("--my-share", required=True, type=float, help="My share THB")
    p_div.add_argument("--comment", default=None, help="Optional comment")
    p_div.set_defaults(func=cmd_add_dividend)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
