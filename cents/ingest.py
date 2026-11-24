"""CSV import: column auto-detection, amount parsing, merchant normalization, dedupe."""

from __future__ import annotations

import csv
import hashlib
import re
import sqlite3
from pathlib import Path

from .normalize import normalize_merchant

# Column-name aliases. Keys are our internal field names; values are the
# header spellings we recognize. Matching is on a normalized (lowercase,
# alphanumeric-only) form of the header, so "Transaction Date" == "transaction_date".
COLUMN_ALIASES: dict[str, list[str]] = {
    "date": ["date", "transaction date", "posted date", "posting date", "date posted", "transactiondate", "datetime"],
    "description": [
        "description", "merchant", "name", "payee", "details", "memo", "narrative",
        "transaction description", "merchant name", "payee name", "transactiondescription",
    ],
    "amount": ["amount", "transaction amount", "transactionamount"],
    "debit": ["debit", "withdrawal", "withdrawals", "money out", "amount out", "debit amount", "debitamount"],
    "credit": ["credit", "deposit", "deposits", "money in", "amount in", "credit amount", "creditamount"],
    "category": ["category", "classification", "expense category", "expensecategory"],
    "account": ["account", "account name", "card", "accountname"],
}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def detect_columns(header: list[str]) -> dict[str, int]:
    norm_cols = {_norm(c): i for i, c in enumerate(header)}
    found: dict[str, int] = {}
    for target, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            a = _norm(alias)
            if a in norm_cols:
                found[target] = norm_cols[a]
                break
            hit = next((i for c, i in norm_cols.items() if a in c), None)
            if hit is not None:
                found[target] = hit
                break
    return found


def parse_float(value) -> float | None:
    if value is None:
        return None
    s = str(value).strip().replace("$", "").replace(",", "").replace("\xa0", "")
    if not s:
        return None
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg, s = True, s[1:-1]
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


def _date(s: str) -> str:
    """Normalize a date string to ISO (YYYY-MM-DD)."""
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y", "%Y/%m/%d", "%m-%d-%Y", "%d-%m-%Y"):
        try:
            from datetime import datetime
            return datetime.strptime(s.split(" ")[0], fmt).date().isoformat()
        except ValueError:
            continue
    # Last resort: keep as-is (caller will validate).
    return s


def row_amount(row: list[str], colmap: dict[str, int]) -> float | None:
    if "debit" in colmap or "credit" in colmap:
        debit = parse_float(row[colmap["debit"]]) if "debit" in colmap else 0.0
        credit = parse_float(row[colmap["credit"]]) if "credit" in colmap else 0.0
        if debit:
            return abs(debit)             # money out -> positive
        if credit:
            return -abs(credit)           # money in  -> negative
        return None
    return parse_float(row[colmap["amount"]])


def _hash(date: str, desc: str, amount: float) -> str:
    key = f"{date}|{desc.strip().lower()}|{amount:.2f}"
    return hashlib.sha256(key.encode()).hexdigest()


def import_csv(
    conn: sqlite3.Connection,
    path: str | Path,
    account: str = "",
    source: str | None = None,
) -> dict:
    """Import a CSV file. Returns counts of added/skipped/invalid rows."""
    path = Path(path)
    source = source or path.name
    stats = {"added": 0, "duplicate": 0, "invalid": 0}

    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return stats

        colmap = detect_columns(header)
        required = {"date", "description"} & set(colmap)
        if len(required) != 2 or ("amount" not in colmap and "debit" not in colmap and "credit" not in colmap):
            raise ValueError(
                f"Could not detect required columns (date, description, amount/debit/credit) "
                f"in header: {header}"
            )

        for row in reader:
            if not row or all(not c.strip() for c in row):
                continue
            row = list(row) + [""] * (len(header) - len(row))

            date = _date(row[colmap["date"]])
            desc = row[colmap["description"]].strip()
            amount = row_amount(row, colmap)
            if not date or not desc or amount is None:
                stats["invalid"] += 1
                continue

            merchant = normalize_merchant(desc)
            h = _hash(date, desc, amount)
            category = row[colmap["category"]].strip() if "category" in colmap else None
            acct = row[colmap["account"]].strip() if "account" in colmap else account

            try:
                conn.execute(
                    """INSERT INTO transactions
                       (date, merchant, raw_description, amount, category, account, source, hash)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (date, merchant, desc, amount, category or None, acct, source, h),
                )
                stats["added"] += 1
            except sqlite3.IntegrityError:
                stats["duplicate"] += 1

    conn.commit()
    return stats
