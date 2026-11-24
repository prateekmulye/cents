import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cents.categorize import categorize, match_rule
from cents.db import connect
from cents.ingest import detect_columns, parse_float, row_amount
from cents.normalize import normalize_merchant


def test_parse_float():
    assert parse_float("$1,234.56") == 1234.56
    assert parse_float("(99.99)") == -99.99
    assert parse_float("") is None
    assert parse_float("abc") is None


def test_detect_columns():
    assert detect_columns(["Transaction Date", "Description", "Amount"]) == {
        "date": 0, "description": 1, "amount": 2,
    }
    cols = detect_columns(["Date", "Narrative", "Debit", "Credit"])
    assert cols["date"] == 0
    assert cols["description"] == 1
    assert cols["debit"] == 2
    assert cols["credit"] == 3


def test_row_amount_debit_credit():
    cols = {"debit": 2, "credit": 3}
    assert row_amount(["2026-11-01", "X", "45.00", ""], cols) == 45.00
    assert row_amount(["2026-11-01", "X", "", "3200.00"], cols) == -3200.00


def test_normalize_merchant():
    assert normalize_merchant("POS DEBIT 1234 AMZN MKTP US*AB123CD45") == "Amazon"
    assert normalize_merchant("UBER *TRIP HELP.UBER.COM") == "Uber"
    assert normalize_merchant("STARBUCKS STORE 12345") == "Starbucks"
    assert normalize_merchant("TRADER JOE'S #123") == "Trader Joe's"


def test_match_rule():
    assert match_rule("Netflix") == "Subscriptions"
    assert match_rule("Uber") == "Transport"
    assert match_rule("Starbucks") == "Dining"
    assert match_rule("Trader Joe's") == "Groceries"
    assert match_rule("Kith") is None


def test_categorize_income_and_override():
    conn = connect(tempfile.mktemp(suffix=".db"))
    assert categorize(conn, "DIRECT DEPOSIT ACME CORP", -3200.0) == "Income"
    assert categorize(conn, "Whole Foods", 78.33) == "Groceries"
    assert categorize(conn, "Kith", 74.0) == "Other"

    from cents.categorize import set_override
    set_override(conn, "Kith", "Shopping")
    assert categorize(conn, "Kith", 74.0) == "Shopping"
    conn.close()


def test_end_to_end():
    from cents.ingest import import_csv
    from cents.categorize import categorize_all
    from cents.insights import build_report_data, week_range

    sample = Path(__file__).resolve().parent.parent / "sample" / "transactions.csv"
    if not sample.exists():
        return  # generator not run yet

    conn = connect(tempfile.mktemp(suffix=".db"))
    stats = import_csv(conn, sample)
    assert stats["added"] > 0
    cats = categorize_all(conn)
    assert cats["categorized"] + cats["uncategorized"] == cats["total"]

    data = build_report_data(conn, date(2026, 11, 16), date(2026, 11, 22))
    assert data["current"]["expense"] > 0
    conn.close()


def test_llm_filtering_drops_hallucinated_keys(monkeypatch):
    import cents.categorize as cat

    def fake_chat(model, prompt):
        return '{"Kith": "Shopping", "Other": "Transport", "Glossier": "Subscriptions"}'

    monkeypatch.setattr(cat, "_ollama_chat", fake_chat)
    monkeypatch.setattr(cat, "_openai_chat", lambda m, p: None)

    out = cat._llm_categorize(["Kith", "Glossier"], model="test")
    assert out == {"Kith": "Shopping", "Glossier": "Subscriptions"}
    assert "Other" not in out
