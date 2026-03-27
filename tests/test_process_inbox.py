"""Tests for CSV-first inbox processing workflow."""

import csv
import shutil
from pathlib import Path

from ingestion.process_inbox import DIVIDEND_FIELDS, MONTHLY_PL_FIELDS, process_inbox_to_csv

ROOT = Path(__file__).resolve().parent.parent
SOURCE_INBOX = ROOT / "inbox"


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows or []:
            writer.writerow(row)


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_process_inbox_updates_rows_and_archives(tmp_path):
    inbox_dir = tmp_path / "inbox"
    data_dir = tmp_path / "data"
    inbox_dir.mkdir()
    data_dir.mkdir()

    shutil.copy2(
        SOURCE_INBOX / "P&L Mozza EmQuartier February 2026.eml",
        inbox_dir / "P&L Mozza EmQuartier February 2026.eml",
    )

    existing_monthly = {field: "" for field in MONTHLY_PL_FIELDS}
    existing_monthly["restaurant_id"] = "mozza-emq"
    existing_monthly["month"] = "2026-02"
    existing_monthly["revenue"] = "1"
    _write_csv(data_dir / "monthly_pl.csv", MONTHLY_PL_FIELDS, [existing_monthly])

    existing_dividend = {field: "" for field in DIVIDEND_FIELDS}
    existing_dividend["restaurant_id"] = "mozza-emq"
    existing_dividend["date"] = "2026-03-25"
    existing_dividend["my_share_thb"] = "1"
    _write_csv(data_dir / "dividends.csv", DIVIDEND_FIELDS, [existing_dividend])

    result = process_inbox_to_csv(inbox_dir=inbox_dir, data_dir=data_dir)
    assert result.processed_files == 1
    assert result.monthly_updated == 1
    assert result.dividend_updated == 1
    assert result.archived_files == 1

    monthly_rows = _read_csv(data_dir / "monthly_pl.csv")
    assert len(monthly_rows) == 1
    assert monthly_rows[0]["restaurant_id"] == "mozza-emq"
    assert monthly_rows[0]["month"] == "2026-02"
    assert float(monthly_rows[0]["revenue"]) == 8_055_139.0

    dividend_rows = _read_csv(data_dir / "dividends.csv")
    assert len(dividend_rows) == 1
    assert dividend_rows[0]["restaurant_id"] == "mozza-emq"
    assert dividend_rows[0]["date"] == "2026-03-25"
    assert float(dividend_rows[0]["my_share_thb"]) > 0
    assert float(dividend_rows[0]["total_thb"]) == 2_500_000.0

    assert not (inbox_dir / "P&L Mozza EmQuartier February 2026.eml").exists()
    assert (inbox_dir / "archive" / "2026-02" / "P&L Mozza EmQuartier February 2026.eml").exists()


def test_process_inbox_dry_run_does_not_write_or_move(tmp_path):
    inbox_dir = tmp_path / "inbox"
    data_dir = tmp_path / "data"
    inbox_dir.mkdir()
    data_dir.mkdir()

    fname = "P&L Parma Eastville February 2026.eml"
    shutil.copy2(SOURCE_INBOX / fname, inbox_dir / fname)

    _write_csv(data_dir / "monthly_pl.csv", MONTHLY_PL_FIELDS, [])
    _write_csv(data_dir / "dividends.csv", DIVIDEND_FIELDS, [])

    result = process_inbox_to_csv(inbox_dir=inbox_dir, data_dir=data_dir, dry_run=True)
    assert result.processed_files == 1
    assert result.monthly_inserted == 1
    assert result.archived_files == 1

    assert _read_csv(data_dir / "monthly_pl.csv") == []
    assert _read_csv(data_dir / "dividends.csv") == []
    assert (inbox_dir / fname).exists()
    assert not (inbox_dir / "archive").exists()

