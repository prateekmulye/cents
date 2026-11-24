"""Generate a realistic sample CSV for demoing cents.

Produces ``sample/transactions.csv`` with ~5 weeks of spending: noisy raw bank
descriptions, recurring subscriptions, biweekly income, a weekend trip, and a
handful of deliberately-unknown merchants (to show off LLM categorization).

Usage:  python3 sample/generate_sample.py
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(7)

START = date(2026, 10, 26)  # Monday
END = date(2026, 11, 24)    # Tuesday

rows: list[tuple[str, str, float]] = []


def add(day: date, desc: str, amount: float) -> None:
    rows.append((day.isoformat(), desc, round(amount, 2)))


# --- Weekly recurring habits (day offset from Monday, description, base amount) ---
WEEKLY = [
    (0, "STARBUCKS STORE 12345", 6.45),
    (1, "SQ *CHIPOTLE 9876", 12.80),
    (1, "UBER *TRIP HELP.UBER.COM", 18.42),
    (2, "STARBUCKS STORE 12345", 6.45),
    (2, "TRADER JOE'S #123", 62.18),
    (3, "SWEETGREEN", 14.75),
    (3, "LYFT *RIDE", 22.10),
    (4, "STARBUCKS STORE 12345", 6.45),
    (4, "WHOLE FOODS MKT", 78.33),
    (5, "POS DEBIT 1234 AMZN MKTP US*AB123CD45", 34.99),
    (5, "DUNKIN #456", 5.20),
    (6, "COSTCO WHSE #0987", 118.50),
]

monday = START
for week in range(5):
    base = monday + timedelta(days=7 * week)
    for offset, desc, amt in WEEKLY:
        day = base + timedelta(days=offset)
        if day <= END:
            add(day, desc, amt * random.uniform(0.82, 1.28))

# --- Biweekly income ---
add(date(2026, 10, 30), "DIRECT DEPOSIT ACME CORP PAYROLL", -3200.00)
add(date(2026, 11, 13), "DIRECT DEPOSIT ACME CORP PAYROLL", -3200.00)

# --- Monthly fixed charges ---
add(date(2026, 11, 1), "RENT PAYMENT NORTHGATE APARTMENTS", 1850.00)
add(date(2026, 11, 1), "EQUINOX MEMBERSHIP", 210.00)
add(date(2026, 11, 2), "SPOTIFY USA", 11.99)
add(date(2026, 11, 3), "APPLE.COM/BILL", 9.99)
add(date(2026, 11, 5), "COMCAST XFINITY INTERNET", 79.99)
add(date(2026, 11, 8), "PG&E ELECTRIC", 92.41)
add(date(2026, 11, 12), "NETFLIX.COM", 15.49)
add(date(2026, 11, 15), "NOTION LABS", 12.00)
add(date(2026, 11, 18), "GITHUB COPILOT", 10.00)
add(date(2026, 11, 20), "COMCAST XFINITY INTERNET", 79.99)  # next cycle

# --- One-off purchases ---
add(date(2026, 10, 28), "BEST BUY STORE 555", 249.99)
add(date(2026, 10, 31), "CVS PHARMACY", 24.63)
add(date(2026, 11, 4), "WALGREENS", 31.85)
add(date(2026, 11, 6), "AMC THEATRES", 34.50)
add(date(2026, 11, 7), "NIKE.COM", 118.00)
add(date(2026, 11, 10), "TICKETMASTER", 95.00)
add(date(2026, 11, 11), "SHELL OIL 5544 MARKET ST", 48.20)
add(date(2026, 11, 14), "TARGET", 86.44)
add(date(2026, 11, 16), "CVS PHARMACY", 19.99)
add(date(2026, 11, 19), "SAFEWAY", 54.11)
add(date(2026, 11, 21), "BEST BUY STORE 555", 89.99)
add(date(2026, 11, 22), "WALGREENS", 15.30)

# --- A weekend trip, mid-November ---
add(date(2026, 11, 13), "DELTA AIR LINES 0062147", 268.40)
add(date(2026, 11, 14), "AIRBNB *HOLD", 342.00)
add(date(2026, 11, 15), "HERTZ RENT-A-CAR", 96.75)
add(date(2026, 11, 16), "MARRIOTT BONVOY", 189.00)

# --- Transfers ---
add(date(2026, 10, 27), "VENMO PAYMENT TO ALEX", 45.00)
add(date(2026, 11, 5), "VENMO PAYMENT TO JORDAN", 60.00)
add(date(2026, 11, 9), "ATM WITHDRAWAL", 80.00)
add(date(2026, 11, 17), "ZELLE PAYMENT TO SAM", 120.00)

# --- Deliberately unknown merchants (exercise the LLM fallback) ---
add(date(2026, 10, 29), "KITH", 74.00)
add(date(2026, 11, 2), "GLOSSIER", 32.00)
add(date(2026, 11, 6), "PETAL & STEM FLORIST", 58.00)
add(date(2026, 11, 11), "LOCAL ROASTER", 9.50)
add(date(2026, 11, 16), "BODEGAS DEL MUNDO", 42.75)
add(date(2026, 11, 20), "SIDEWALK GALLERY", 27.00)

# --- Current (partial) week, Nov 23-24 ---
add(date(2026, 11, 23), "STARBUCKS STORE 12345", 6.45)
add(date(2026, 11, 23), "UBER *TRIP HELP.UBER.COM", 14.90)
add(date(2026, 11, 24), "SQ *CHIPOTLE 9876", 12.80)

rows.sort(key=lambda r: r[0])

OUT = Path(__file__).parent / "transactions.csv"
with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Transaction Date", "Description", "Amount"])
    w.writerows(rows)

print(f"Wrote {len(rows)} rows to {OUT}")
