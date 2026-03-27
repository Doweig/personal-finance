"""CLI entry point for restaurant portfolio data ingestion."""

import argparse
import json
import sys
from email.utils import parsedate_to_datetime
from pathlib import Path

from ingestion.db import (
    clear_all_data,
    create_schema,
    get_connection,
    insert_dividend,
    insert_investment,
    insert_ownership,
    insert_restaurant,
    upsert_monthly_pl,
)
from ingestion.extract_llm import build_codex_prompt, extract_with_openai
from ingestion.import_csv import import_csv
from ingestion.parse_eml import parse_eml_file
from ingestion.process_inbox import process_inbox_to_csv
from ingestion.restaurants import ID_TO_CANONICAL_NAME, RESTAURANT_NAME_MAP


def _resolve_db_path(db_arg):
    if db_arg is not None:
        return Path(db_arg)
    return Path(__file__).resolve().parent.parent / "data" / "portfolio.duckdb"


def _print_table_counts(conn):
    tables = ["restaurants", "monthly_pl", "dividends", "investments", "ownership"]
    for table in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count} rows")


def _email_date_or_month(data):
    email_date = data.get("email_date")
    if email_date:
        try:
            return parsedate_to_datetime(email_date).date().isoformat()
        except (TypeError, ValueError):
            pass
    return data["month"]


def cmd_import_csv(args):
    """Import seed data from CSV files."""
    conn = get_connection(args.db)
    create_schema(conn)
    import_csv(conn, args.data_dir)
    _print_table_counts(conn)
    conn.close()


def cmd_ingest(args):
    """Legacy: process all .eml files directly into DuckDB."""
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
        canonical_name = ID_TO_CANONICAL_NAME.get(restaurant_id, restaurant_name)
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
                "date": _email_date_or_month(data),
                "total_thb": div.get("total_thb", div.get("my_share_thb")),
                "my_share_thb": div["my_share_thb"],
                "comment": None,
            })

        print(f"  OK   {fname}: {restaurant_name} ({data['month']})")
        imported += 1

    conn.close()
    print(f"\nSummary: {imported} imported, {skipped} skipped, {errors} errors")


def cmd_process_inbox(args):
    """CSV-first workflow: parse inbox into CSVs, archive files."""
    try:
        result = process_inbox_to_csv(
            inbox_dir=args.inbox_dir,
            data_dir=args.data_dir,
            archive_dir=args.archive_dir,
            dry_run=args.dry_run,
            archive_processed=(not args.no_archive),
        )
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Processed: {result.processed_files}, skipped: {result.skipped_files}, errors: {result.error_files}")
    print(f"monthly_pl.csv: +{result.monthly_inserted} inserted, ~{result.monthly_updated} updated")
    print(f"dividends.csv: +{result.dividend_inserted} inserted, ~{result.dividend_updated} updated")
    if args.no_archive:
        print("Archive: disabled (--no-archive)")
    else:
        print(f"Archived emails: {result.archived_files}{' (dry-run)' if args.dry_run else ''}")


def cmd_rebuild_db(args):
    """Rebuild DuckDB from CSV source-of-truth files."""
    db_path = _resolve_db_path(args.db)
    if db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = get_connection(str(db_path))
    create_schema(conn)
    clear_all_data(conn)
    import_csv(conn, args.data_dir)
    print(f"Rebuilt DB from CSV at {db_path}")
    _print_table_counts(conn)
    conn.close()


def cmd_extract_email(args):
    """Extract one email using either a Codex prompt or OpenAI API."""
    if args.provider == "codex":
        print(build_codex_prompt(args.eml_path))
        return

    try:
        data = extract_with_openai(args.eml_path, model=args.model)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(data, indent=2, ensure_ascii=False))


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

    # import-csv
    p_import = sub.add_parser("import-csv", help="Import seed data from CSV files")
    p_import.add_argument("data_dir", help="Directory containing CSV files (default: data/)", nargs="?", default="data")
    p_import.set_defaults(func=cmd_import_csv)

    # process-inbox (recommended monthly flow)
    p_proc = sub.add_parser("process-inbox", help="Parse inbox .eml files and upsert data/*.csv")
    p_proc.add_argument("inbox_dir", help="Directory containing .eml files")
    p_proc.add_argument("--data-dir", default="data", help="Directory containing source CSV files")
    p_proc.add_argument("--archive-dir", default=None, help="Archive directory (default: <inbox>/archive)")
    p_proc.add_argument("--dry-run", action="store_true", help="Parse and report only (no writes/moves)")
    p_proc.add_argument("--no-archive", action="store_true", help="Do not move processed .eml files")
    p_proc.set_defaults(func=cmd_process_inbox)

    # rebuild-db
    p_rebuild = sub.add_parser("rebuild-db", help="Recreate DuckDB from CSV source files")
    p_rebuild.add_argument("data_dir", help="Directory containing CSV files (default: data/)", nargs="?", default="data")
    p_rebuild.set_defaults(func=cmd_rebuild_db)

    # extract-email
    p_extract = sub.add_parser("extract-email", help="Extract one .eml with Codex prompt or OpenAI API")
    p_extract.add_argument("eml_path", help="Path to one .eml file")
    p_extract.add_argument("--provider", choices=["codex", "openai"], default="codex")
    p_extract.add_argument("--model", default="gpt-4.1-mini", help="OpenAI model (provider=openai)")
    p_extract.set_defaults(func=cmd_extract_email)

    # ingest
    p_ingest = sub.add_parser("ingest", help="Legacy: process .eml files directly into DuckDB")
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
