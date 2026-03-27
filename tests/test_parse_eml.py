"""Tests for the email P&L parser."""

from pathlib import Path

import pytest

from ingestion.parse_eml import parse_eml_file

INBOX = Path(__file__).resolve().parent.parent / "inbox"


class TestParseParmaEastvilleFeb:
    """test_parse_parma_eastville_feb — verify key P&L values."""

    @pytest.fixture(autouse=True)
    def parse(self):
        self.result = parse_eml_file(INBOX / "P&L Parma Eastville February 2026.eml")

    def test_restaurant_name(self):
        assert self.result["restaurant_name"] == "Parma Eastville"

    def test_month(self):
        assert self.result["month"] == "2026-02-01"

    def test_restaurant_code(self):
        assert self.result["restaurant_code"] == "27-Parma Central Eastville"

    def test_revenue(self):
        assert self.result["pl"]["revenue"] == 2194431

    def test_gop_net(self):
        assert self.result["pl"]["gop_net"] == 454889

    def test_food_cost(self):
        assert self.result["pl"]["food_cost"] == 453336

    def test_beverage_cost(self):
        assert self.result["pl"]["beverage_cost"] == 81850

    def test_total_fb_cost(self):
        assert self.result["pl"]["total_fb_cost"] == 535185

    def test_rebate(self):
        assert self.result["pl"]["rebate"] == 137614


class TestParseMozzaEmqFeb:
    """test_parse_mozza_emq_feb — verify name/month/code, revenue > 0."""

    @pytest.fixture(autouse=True)
    def parse(self):
        self.result = parse_eml_file(INBOX / "P&L Mozza EmQuartier February 2026.eml")

    def test_restaurant_name(self):
        assert self.result["restaurant_name"] == "Mozza EmQuartier"

    def test_month(self):
        assert self.result["month"] == "2026-02-01"

    def test_restaurant_code(self):
        assert self.result["restaurant_code"] == "17-Mozza EMQ"

    def test_revenue_positive(self):
        assert self.result["pl"]["revenue"] > 0


class TestParseDividendPresent:
    """test_parse_extracts_dividend_when_present — Mozza EMQ should have dividend."""

    def test_mozza_emq_has_dividend(self):
        result = parse_eml_file(INBOX / "P&L Mozza EmQuartier February 2026.eml")
        assert result["dividend"] is not None
        assert result["dividend"]["my_share_thb"] > 0
        assert result["dividend"]["total_thb"] == 2_500_000.0


class TestParseDividendAbsent:
    """test_parse_no_dividend_when_absent — Parma Eastville should have dividend=None."""

    def test_parma_eastville_no_dividend(self):
        result = parse_eml_file(INBOX / "P&L Parma Eastville February 2026.eml")
        assert result["dividend"] is None


class TestParseCocotteFeb:
    """test_parse_cocotte_feb — verify name/month, revenue > 0."""

    @pytest.fixture(autouse=True)
    def parse(self):
        self.result = parse_eml_file(INBOX / "P&L Cocotte February 2026.eml")

    def test_restaurant_name(self):
        assert self.result["restaurant_name"] == "Cocotte"

    def test_month(self):
        assert self.result["month"] == "2026-02-01"

    def test_revenue_positive(self):
        assert self.result["pl"]["revenue"] > 0


class TestParseAllInboxFiles:
    """test_parse_all_inbox_files — smoke test: all .eml files parse without error."""

    def test_all_files_parse(self):
        eml_files = sorted(INBOX.glob("*.eml"))
        assert len(eml_files) >= 7, f"Expected at least 7 .eml files, found {len(eml_files)}"

        for eml_file in eml_files:
            result = parse_eml_file(eml_file)
            assert result["restaurant_name"], f"Missing restaurant_name in {eml_file.name}"
            assert result["month"], f"Missing month in {eml_file.name}"
            assert result["pl"]["revenue"] > 0, f"Revenue not > 0 in {eml_file.name}"
