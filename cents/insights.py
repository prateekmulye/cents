"""Analytics: summarize spending over a period and compare it to the prior period."""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from datetime import date, timedelta


def week_range(today: date) -> tuple[date, date]:
    """The Monday-Sunday week containing `today`."""
    start = today - timedelta(days=today.weekday())
    return start, start + timedelta(days=6)


def prev_period(start: date, end: date) -> tuple[date, date]:
    """The immediately preceding period of equal length."""
    length = (end - start).days
    return start - timedelta(days=length + 1), start - timedelta(days=1)


def fetch(conn: sqlite3.Connection, start: date, end: date) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM transactions WHERE date BETWEEN ? AND ? ORDER BY date",
        (start.isoformat(), end.isoformat()),
    ).fetchall()


def summarize(txs: list[sqlite3.Row]) -> dict:
    by_category: dict[str, float] = defaultdict(float)
    by_merchant: dict[str, float] = defaultdict(float)
    by_day: dict[str, float] = defaultdict(float)
    income = expense = 0.0
    largest: tuple[str, float] | None = None
    subscriptions: dict[str, float] = defaultdict(float)
    uncategorized: set[str] = set()

    for tx in txs:
        amt = tx["amount"]
        if amt > 0:
            expense += amt
            cat = tx["category"] or "Other"
            by_category[cat] += amt
            by_merchant[tx["merchant"]] += amt
            by_day[tx["date"]] += amt
            if largest is None or amt > largest[1]:
                largest = (tx["merchant"], amt)
            if cat == "Subscriptions":
                subscriptions[tx["merchant"]] += amt
            if cat == "Other":
                uncategorized.add(tx["merchant"])
        else:
            income += abs(amt)

    return {
        "income": income,
        "expense": expense,
        "net": income - expense,
        "by_category": dict(sorted(by_category.items(), key=lambda kv: -kv[1])),
        "by_merchant": dict(sorted(by_merchant.items(), key=lambda kv: -kv[1])),
        "by_day": dict(sorted(by_day.items())),
        "largest": largest,
        "subscriptions": dict(sorted(subscriptions.items(), key=lambda kv: -kv[1])),
        "uncategorized": sorted(uncategorized),
        "tx_count": len(txs),
        "days": len(by_day),
    }


def build_report_data(conn: sqlite3.Connection, start: date, end: date) -> dict:
    """Summarize the period and its predecessor for a full report."""
    cur_txs = fetch(conn, start, end)
    cur = summarize(cur_txs)

    prev_start, prev_end = prev_period(start, end)
    prev = summarize(fetch(conn, prev_start, prev_end))

    def delta(cur_val: float, prev_val: float) -> float | None:
        if prev_val == 0:
            return None
        return (cur_val - prev_val) / prev_val * 100.0

    deltas = {
        cat: delta(cur["by_category"].get(cat, 0.0), prev["by_category"].get(cat, 0.0))
        for cat in set(cur["by_category"]) | set(prev["by_category"])
    }

    return {
        "start": start,
        "end": end,
        "prev_start": prev_start,
        "prev_end": prev_end,
        "current": cur,
        "previous": prev,
        "deltas": {k: v for k, v in deltas.items() if v is not None},
    }
