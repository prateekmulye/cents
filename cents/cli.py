"""Command-line interface for cents."""

from __future__ import annotations

import argparse
import sys
import webbrowser
from datetime import date, timedelta

from . import __version__
from .categorize import categorize_all, set_override
from .db import connect, default_db_path
from .ingest import import_csv
from .insights import build_report_data, fetch, prev_period, week_range
from .report import render
from .rules import CATEGORIES


def cmd_import(args) -> int:
    conn = connect(args.db)
    stats = import_csv(conn, args.file, account=args.account)
    print(f"Imported {args.file}:")
    print(f"  + {stats['added']} added")
    print(f"  - {stats['duplicate']} duplicates skipped")
    print(f"  ! {stats['invalid']} invalid rows skipped")
    conn.close()
    return 0


def cmd_categorize(args) -> int:
    conn = connect(args.db)
    if args.set:
        merchant, category = args.set
        set_override(conn, merchant, category)
        print(f"Set {merchant!r} -> {category!r} (manual override)")
        conn.close()
        return 0

    stats = categorize_all(conn, use_llm=args.llm, model=args.model)
    print(f"Categorized {stats['total']} transactions:")
    print(f"  ✓ {stats['categorized']} classified")
    if stats["uncategorized"]:
        print(f"  ? {stats['uncategorized']} unknown (Other)")
    if args.llm:
        if stats["llm"]:
            print(f"  ✨ {stats['llm']} merchants classified by LLM")
        else:
            print("  ✨ LLM fallback: no model available (pull one with `ollama pull llama3.2`")
            print("    or set OPENAI_API_KEY). Rule-based results kept.")
    conn.close()
    return 0


def _resolve_period(args) -> tuple[date, date]:
    today = date.today()
    if args.month:
        end = today - timedelta(days=1)
        return end - timedelta(days=29), end
    if args.week == "last":
        this_start, _ = week_range(today)
        return prev_period(this_start, this_start + timedelta(days=6))
    return week_range(today)


def cmd_report(args) -> int:
    conn = connect(args.db)
    start, end = _resolve_period(args)
    out = args.out or f"cents-report-{end.isoformat()}.html"
    render(conn, start, end, out)
    print(f"Wrote report: {out}")
    if args.open:
        webbrowser.open(f"file://{out}")
    conn.close()
    return 0


def cmd_list(args) -> int:
    conn = connect(args.db)
    q = "SELECT date, merchant, amount, category FROM transactions WHERE 1=1"
    params: list = []
    if args.category:
        q += " AND category = ?"
        params.append(args.category)
    if args.merchant:
        q += " AND merchant LIKE ?"
        params.append(f"%{args.merchant}%")
    q += " ORDER BY date DESC LIMIT ?"
    params.append(args.limit)

    rows = conn.execute(q, params).fetchall()
    if not rows:
        print("No transactions found.")
    else:
        print(f"{'date':<12}{'amount':>10}  {'category':<14} merchant")
        for r in rows:
            amt = f"${r['amount']:,.2f}"
            print(f"{r['date']:<12}{amt:>10}  {(r['category'] or '—'):<14} {r['merchant']}")
    conn.close()
    return 0


def cmd_categories(args) -> int:
    conn = connect(args.db)
    rows = conn.execute(
        "SELECT category, COUNT(*) n, SUM(CASE WHEN amount>0 THEN amount ELSE 0 END) spent "
        "FROM transactions WHERE category IS NOT NULL GROUP BY category ORDER BY spent DESC"
    ).fetchall()
    if not rows:
        print("No categorized transactions yet. Run `cents categorize`.")
        conn.close()
        return 0
    print(f"{'category':<14}{'count':>7}{'spent':>12}")
    for r in rows:
        print(f"{r['category']:<14}{r['n']:>7}{r['spent']:>12,.0f}")
    conn.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cents",
        description="Zero-dependency personal finance: import CSVs, categorize, report.",
    )
    p.add_argument("--version", action="version", version=f"cents {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    ip = sub.add_parser("import", help="Import a bank/credit-card CSV")
    ip.add_argument("file", help="path to CSV file")
    ip.add_argument("--account", default="", help="account label for all rows")
    ip.add_argument("--db", default=None, help="database path (default ~/.cents/cents.db)")
    ip.set_defaults(func=cmd_import)

    cp = sub.add_parser("categorize", help="Assign categories (rules, then optional LLM)")
    cp.add_argument("--llm", action="store_true", help="use a local/remote LLM for unknown merchants")
    cp.add_argument("--model", default=None, help="override LLM model name")
    cp.add_argument("--set", nargs=2, metavar=("MERCHANT", "CATEGORY"), help="manual override")
    cp.add_argument("--db", default=None)
    cp.set_defaults(func=cmd_categorize)

    rp = sub.add_parser("report", help="Generate an HTML spending report")
    rp.add_argument("--week", choices=["this", "last"], default="this", help="which week to report on")
    rp.add_argument("--month", action="store_true", help="report on the last 30 days instead")
    rp.add_argument("--out", default=None, help="output HTML path")
    rp.add_argument("--open", action="store_true", help="open the report in a browser")
    rp.add_argument("--db", default=None)
    rp.set_defaults(func=cmd_report)

    lp = sub.add_parser("list", help="List transactions")
    lp.add_argument("--category", default=None)
    lp.add_argument("--merchant", default=None)
    lp.add_argument("--limit", type=int, default=50)
    lp.add_argument("--db", default=None)
    lp.set_defaults(func=cmd_list)

    gp = sub.add_parser("categories", help="Summarize spending by category")
    gp.add_argument("--db", default=None)
    gp.set_defaults(func=cmd_categories)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, FileNotFoundError) as e:
        print(f"cents: error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
