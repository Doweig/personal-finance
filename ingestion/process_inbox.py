"""CSV-first inbox workflow: parse .eml files, upsert CSVs, archive files."""

from __future__ import annotations

import csv
import shutil
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from pathlib import Path

from ingestion.parse_eml import parse_eml_file
from ingestion.restaurants import RESTAURANT_NAME_MAP

MONTHLY_PL_FIELDS = [
    "restaurant_id",
    "month",
    "revenue",
    "revenue_n1",
    "food_cost",
    "beverage_cost",
    "total_fb_cost",
    "total_other_expenses",
    "total_monthly_exp",
    "gop_before_fee",
    "other_special_fee",
    "monthly_provision",
    "gop_net",
    "rebate",
]

DIVIDEND_FIELDS = ["restaurant_id", "date", "total_thb", "my_share_thb", "comment"]


@dataclass
class ProcessResult:
    processed_files: int = 0
    skipped_files: int = 0
    error_files: int = 0
    monthly_inserted: int = 0
    monthly_updated: int = 0
    dividend_inserted: int = 0
    dividend_updated: int = 0
    archived_files: int = 0


def _to_csv_value(value):
    if value is None:
        return ""
    return str(value)


def _normalize_row(fieldnames: list[str], row: dict) -> dict:
    return {field: _to_csv_value(row.get(field)) for field in fieldnames}


def _read_csv_table(path: Path, key_fields: tuple[str, ...], fieldnames: list[str]) -> dict:
    if not path.exists():
        return {}
    table = {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for src in reader:
            row = _normalize_row(fieldnames, src)
            key = tuple(row[field] for field in key_fields)
            table[key] = row
    return table


def _write_csv_table(path: Path, fieldnames: list[str], rows: list[dict], sort_fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sorted_rows = sorted(rows, key=lambda r: tuple(r[field] for field in sort_fields))
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted_rows)


def _upsert(table: dict, key: tuple, row: dict) -> str:
    old = table.get(key)
    if old is None:
        table[key] = row
        return "inserted"
    if old != row:
        table[key] = row
        return "updated"
    return "unchanged"


def _safe_email_date(date_header: str | None, fallback_month: str) -> str:
    if date_header:
        try:
            return parsedate_to_datetime(date_header).date().isoformat()
        except (TypeError, ValueError):
            pass
    return fallback_month


def _archive_path_for(eml_path: Path, archive_root: Path, month: str) -> Path:
    target_dir = archive_root / month[:7]
    target_dir.mkdir(parents=True, exist_ok=True)
    candidate = target_dir / eml_path.name
    if not candidate.exists():
        return candidate

    index = 1
    while True:
        candidate = target_dir / f"{eml_path.stem}-{index}{eml_path.suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def process_inbox_to_csv(
    inbox_dir: str | Path,
    data_dir: str | Path,
    archive_dir: str | Path | None = None,
    dry_run: bool = False,
    archive_processed: bool = True,
) -> ProcessResult:
    """Parse inbox .eml files and upsert monthly_pl/dividends CSVs."""
    inbox_dir = Path(inbox_dir)
    data_dir = Path(data_dir)
    archive_root = Path(archive_dir) if archive_dir else (inbox_dir / "archive")

    if not inbox_dir.is_dir():
        raise ValueError(f"Not a directory: {inbox_dir}")
    if not data_dir.is_dir():
        raise ValueError(f"Not a directory: {data_dir}")

    monthly_csv = data_dir / "monthly_pl.csv"
    dividends_csv = data_dir / "dividends.csv"

    monthly_table = _read_csv_table(monthly_csv, ("restaurant_id", "month"), MONTHLY_PL_FIELDS)
    dividend_table = _read_csv_table(dividends_csv, ("restaurant_id", "date"), DIVIDEND_FIELDS)

    result = ProcessResult()
    eml_files = sorted(inbox_dir.glob("*.eml"))

    for eml_path in eml_files:
        try:
            parsed = parse_eml_file(eml_path)
        except Exception:
            result.error_files += 1
            continue

        restaurant_name = parsed["restaurant_name"]
        restaurant_id = RESTAURANT_NAME_MAP.get(restaurant_name)
        if restaurant_id is None:
            result.skipped_files += 1
            continue

        month = parsed["month"][:7]
        pl = parsed["pl"]
        monthly_row = _normalize_row(
            MONTHLY_PL_FIELDS,
            {
                "restaurant_id": restaurant_id,
                "month": month,
                "revenue": pl.get("revenue"),
                "revenue_n1": pl.get("revenue_n1"),
                "food_cost": pl.get("food_cost"),
                "beverage_cost": pl.get("beverage_cost"),
                "total_fb_cost": pl.get("total_fb_cost"),
                "total_other_expenses": pl.get("total_other_expenses"),
                "total_monthly_exp": pl.get("total_monthly_exp"),
                "gop_before_fee": pl.get("gop_before_fee"),
                "other_special_fee": pl.get("other_special_fee"),
                "monthly_provision": pl.get("monthly_provision"),
                "gop_net": pl.get("gop_net"),
                "rebate": pl.get("rebate"),
            },
        )
        monthly_action = _upsert(monthly_table, (restaurant_id, month), monthly_row)
        if monthly_action == "inserted":
            result.monthly_inserted += 1
        elif monthly_action == "updated":
            result.monthly_updated += 1

        dividend = parsed.get("dividend")
        if dividend and dividend.get("my_share_thb") not in (None, 0):
            dividend_date = _safe_email_date(parsed.get("email_date"), parsed["month"])
            dividend_row = _normalize_row(
                DIVIDEND_FIELDS,
                {
                    "restaurant_id": restaurant_id,
                    "date": dividend_date,
                    "total_thb": dividend.get("total_thb", dividend.get("my_share_thb")),
                    "my_share_thb": dividend.get("my_share_thb"),
                    "comment": None,
                },
            )
            div_action = _upsert(dividend_table, (restaurant_id, dividend_date), dividend_row)
            if div_action == "inserted":
                result.dividend_inserted += 1
            elif div_action == "updated":
                result.dividend_updated += 1

        if archive_processed:
            result.archived_files += 1
            if not dry_run:
                archive_path = _archive_path_for(eml_path, archive_root, parsed["month"])
                shutil.move(str(eml_path), str(archive_path))

        result.processed_files += 1

    if not dry_run:
        _write_csv_table(monthly_csv, MONTHLY_PL_FIELDS, list(monthly_table.values()), ("restaurant_id", "month"))
        _write_csv_table(dividends_csv, DIVIDEND_FIELDS, list(dividend_table.values()), ("restaurant_id", "date"))

    return result

