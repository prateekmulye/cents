"""Self-contained HTML report rendering (inline SVG charts, no external assets)."""

from __future__ import annotations

import html
import math
import sqlite3
from datetime import date, timedelta

from . import __version__
from .insights import build_report_data

PALETTE = [
    "#4ade80", "#f97316", "#38bdf8", "#a78bfa", "#f472b6", "#facc15", "#34d399",
    "#fb7185", "#60a5fa", "#c084fc", "#fbbf24", "#22d3ee", "#a3e635", "#e879f9",
    "#94a3b8", "#2dd4bf",
]


def _money(v: float) -> str:
    v = float(v)
    return f"${v:,.2f}" if v != round(v, 0) else f"${v:,.0f}"


def _esc(s) -> str:
    return html.escape(str(s))


def _assign_colors(categories: list[str]) -> dict[str, str]:
    return {cat: PALETTE[i % len(PALETTE)] for i, cat in enumerate(categories)}


def _donut(items: list[tuple[str, float, str]], total: float, size: int = 240) -> str:
    """Donut chart built from stroked circles (no arc math)."""
    cx = cy = size / 2
    thickness = 34
    r = (size - thickness) / 2
    circ = 2 * math.pi * r
    offset = 0.0
    segs = []
    for label, amt, color in items:
        frac = amt / total if total else 0
        dash = frac * circ
        segs.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r:.1f}" fill="none" stroke="{color}" '
            f'stroke-width="{thickness}" stroke-dasharray="{dash:.2f} {circ - dash:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 {cx} {cy})"><title>'
            f'{_esc(label)}: {_money(amt)}</title></circle>'
        )
        offset += dash
    center = f'<text x="{cx}" y="{cy - 4}" text-anchor="middle" fill="#e6edf3" font-size="30" font-weight="700">{_money(total)}</text>' \
             f'<text x="{cx}" y="{cy + 22}" text-anchor="middle" fill="#8b949e" font-size="12">spent</text>'
    return f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">' + "".join(segs) + center + "</svg>"


def _category_bars(items: list[tuple[str, float, str]], width: int = 640) -> str:
    bar_h = 30
    gap = 8
    label_w = 140
    bar_area = width - label_w - 90
    maxv = max((a for _, a, _ in items), default=1)
    height = len(items) * (bar_h + gap) - gap
    rows = []
    y = 0
    for label, amt, color in items:
        w = max(6, int((amt / maxv) * bar_area)) if maxv else 0
        rows.append(
            f'<text x="0" y="{y + bar_h - 9}" fill="#c9d1d9" font-size="13">{_esc(label)}</text>'
            f'<rect x="{label_w}" y="{y}" width="{w}" height="{bar_h - 10}" rx="5" fill="{color}"/>'
            f'<text x="{label_w + w + 8}" y="{y + bar_h - 9}" fill="#e6edf3" font-size="13" font-weight="600">{_money(amt)}</text>'
        )
        y += bar_h + gap
    return f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">' + "".join(rows) + "</svg>"


def _daily_bars(days: list[tuple[str, float]], width: int = 640, height: int = 200) -> str:
    pad_b = 24
    pad_t = 14
    chart_h = height - pad_b - pad_t
    maxv = max((a for _, a in days), default=1)
    n = len(days)
    slot = width / n
    bar_w = max(6, slot * 0.5)
    bars = []
    for i, (label, amt) in enumerate(days):
        h = (amt / maxv) * chart_h if maxv else 0
        x = i * slot + (slot - bar_w) / 2
        y = pad_t + (chart_h - h)
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="4" fill="#3fb950" opacity="0.9">'
            f'<title>{_esc(label)}: {_money(amt)}</title></rect>'
            f'<text x="{i * slot + slot / 2}" y="{height - 8}" text-anchor="middle" fill="#8b949e" font-size="11">{_esc(label)}</text>'
        )
    return f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">' + "".join(bars) + "</svg>"


def _delta_badge(pct: float | None) -> str:
    if pct is None:
        return '<span class="badge mute">no prior data</span>'
    down = pct <= 0
    arrow = "▼" if down else "▲"
    cls = "good" if down else "bad"
    return f'<span class="badge {cls}">{arrow} {abs(pct):.0f}% vs last week</span>'


def _insights(data: dict) -> list[str]:
    cur = data["current"]
    prev = data["previous"]
    out = []

    if cur["expense"] == 0:
        return ["No spending in this period."]

    # Overall change.
    if prev["expense"] > 0:
        d = (cur["expense"] - prev["expense"]) / prev["expense"] * 100
        out.append(
            f"Total spending was {_money(cur['expense'])}, "
            f"{'up' if d > 0 else 'down'} {abs(d):.0f}% from last week ({_money(prev['expense'])})."
        )

    # Top category.
    if cur["by_category"]:
        cat, amt = next(iter(cur["by_category"].items()))
        share = amt / cur["expense"] * 100
        out.append(f"{cat} was your biggest category at {_money(amt)} ({share:.0f}% of spending).")

    # Largest purchase.
    if cur["largest"]:
        m, a = cur["largest"]
        out.append(f"Largest single purchase: {_money(a)} at {m}.")

    # Category swings vs last week.
    swings = sorted(data["deltas"].items(), key=lambda kv: abs(kv[1]), reverse=True)
    big = [kv for kv in swings if abs(kv[1]) >= 20 and kv[0] != "Other"]
    if big:
        cat, d = big[0]
        out.append(f"{cat} {'jumped' if d > 0 else 'dropped'} {abs(d):.0f}% vs last week.")

    # Subscriptions.
    if cur["subscriptions"]:
        total = sum(cur["subscriptions"].values())
        n = len(cur["subscriptions"])
        out.append(f"{n} recurring subscription{'s' if n != 1 else ''} totaling {_money(total)}.")

    # Daily average.
    if cur["days"]:
        avg = cur["expense"] / cur["days"]
        out.append(f"Averaging {_money(avg)}/day across {cur['days']} active days.")

    return out


CSS = """
:root{color-scheme:dark}
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0b0e14;color:#e6edf3;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;padding:48px 24px;line-height:1.5}
.wrap{max-width:1080px;margin:0 auto}
h1{font-size:28px;font-weight:700;letter-spacing:-.02em}
.sub{color:#8b949e;font-size:14px;margin-top:4px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin:24px 0}
.card{background:#12161f;border:1px solid #21262d;border-radius:14px;padding:20px}
.card .k{color:#8b949e;font-size:12px;text-transform:uppercase;letter-spacing:.06em}
.card .v{font-size:26px;font-weight:700;margin-top:6px}
.card .v.good{color:#3fb950}.card .v.bad{color:#f85149}
.row{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:820px){.row{grid-template-columns:1fr}}
.badge{display:inline-block;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:600;margin-left:8px}
.badge.good{background:#12261c;color:#3fb950}.badge.bad{background:#2d1417;color:#f85149}.badge.mute{background:#21262d;color:#8b949e}
h2{font-size:16px;font-weight:600;margin-bottom:14px;color:#c9d1d9}
.chart{display:flex;align-items:center;gap:24px;flex-wrap:wrap}
.legend{list-style:none;flex:1;min-width:200px}
.legend li{display:flex;align-items:center;gap:10px;padding:5px 0;font-size:14px}
.legend .dot{width:11px;height:11px;border-radius:3px;flex:none}
.legend .amt{margin-left:auto;font-weight:600}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid #21262d}
th{color:#8b949e;font-weight:500;font-size:12px;text-transform:uppercase;letter-spacing:.05em}
td.num,th.num{text-align:right}
.insights{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media(max-width:820px){.insights{grid-template-columns:1fr}}
.insight{background:#12161f;border:1px solid #21262d;border-left:3px solid #3fb950;border-radius:10px;padding:14px 16px;font-size:14px}
.footer{color:#8b949e;font-size:12px;margin-top:40px;text-align:center}
.warn{background:#2d2a14;border:1px solid #4d4210;border-radius:10px;padding:14px 16px;font-size:14px;color:#facc15;margin-top:16px}
code{background:#1c2128;border-radius:5px;padding:1px 6px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}
"""


def build_html(data: dict) -> str:
    cur = data["current"]
    prev = data["previous"]
    start, end = data["start"], data["end"]

    def dstr(d: date) -> str:
        return d.strftime("%b %d")

    if (end - start).days <= 8:
        period_label = f"{start.strftime('%b %d')} – {end.strftime('%b %d, %Y')}"
    else:
        period_label = f"{start.strftime('%b %d')} – {end.strftime('%b %d, %Y')}"

    colors = _assign_colors(list(cur["by_category"].keys()))

    # Header stats.
    spend_delta = None
    if prev["expense"] > 0:
        spend_delta = (cur["expense"] - prev["expense"]) / prev["expense"] * 100

    stat_cards = [
        ("Spent", _money(cur["expense"]), "good" if (spend_delta or 0) <= 0 else "bad"),
        ("Income", _money(cur["income"]), "good"),
        ("Net", _money(cur["net"]), "good" if cur["net"] >= 0 else "bad"),
        ("Avg / day", _money(cur["expense"] / cur["days"]) if cur["days"] else "—", ""),
    ]

    cards_html = "".join(
        f'<div class="card"><div class="k">{k}</div><div class="v {cls}">{v}</div></div>'
        for k, v, cls in stat_cards
    )

    # Donut + legend.
    donut_items = [(c, a, colors[c]) for c, a in cur["by_category"].items()]
    donut = _donut(donut_items, cur["expense"]) if cur["expense"] else '<div style="color:#8b949e">No spending this period.</div>'
    legend_items = "".join(
        f'<li><span class="dot" style="background:{colors[c]}"></span>{_esc(c)}'
        f'<span class="amt">{_money(a)}</span></li>'
        for c, a in cur["by_category"].items()
    )

    # Category bars.
    bars = _category_bars(donut_items) if donut_items else ""

    # Daily bars.
    days = []
    d = start
    while d <= end:
        days.append((d.strftime("%a %d"), cur["by_day"].get(d.isoformat(), 0.0)))
        d += timedelta(days=1)
    daily = _daily_bars(days)

    # Top merchants.
    top_merchants = list(cur["by_merchant"].items())[:10]
    merchant_rows = "".join(
        f'<tr><td>{_esc(m)}</td><td class="num">{_money(a)}</td></tr>' for m, a in top_merchants
    )

    # Subscriptions.
    sub_rows = "".join(
        f'<tr><td>{_esc(m)}</td><td class="num">{_money(a)}</td></tr>'
        for m, a in cur["subscriptions"].items()
    )

    # Insights.
    insight_cards = "".join(f'<div class="insight">{_esc(t)}</div>' for t in _insights(data))

    # Uncategorized warning.
    uncat = ""
    if cur["uncategorized"]:
        names = ", ".join(f"<code>{_esc(m)}</code>" for m in cur["uncategorized"][:12])
        uncat = (
            f'<div class="warn"><strong>{len(cur["uncategorized"])} merchants need review:</strong> '
            f'{names}. Run <code>cents categorize --llm</code> to auto-classify them.</div>'
        )

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>cents — {_esc(period_label)}</title>
<style>{CSS}</style></head>
<body><div class="wrap">
<h1>Where your money went {_delta_badge(spend_delta)}</h1>
<div class="sub">{_esc(period_label)} · {cur['tx_count']} transactions</div>
<div class="grid">{cards_html}</div>

<div class="row">
  <div class="card">
    <h2>Spending by category</h2>
    <div class="chart">{donut}<ul class="legend">{legend_items}</ul></div>
  </div>
  <div class="card">
    <h2>Daily spending</h2>
    {daily}
  </div>
</div>

<div class="row" style="margin-top:16px">
  <div class="card">
    <h2>Top merchants</h2>
    <table>{merchant_rows}</table>
  </div>
  <div class="card">
    <h2>Recurring subscriptions</h2>
    {f'<table>{sub_rows}</table>' if sub_rows else '<div style="color:#8b949e">None detected this period.</div>'}
    <div style="margin-top:20px"><h2>Category totals</h2>{bars}</div>
  </div>
</div>

<div class="card" style="margin-top:16px">
  <h2>Insights</h2>
  <div class="insights">{insight_cards}</div>
</div>
{uncat}
<div class="footer">Generated by <strong>cents</strong> v{__version__} · {period_label}</div>
</div></body></html>"""


def render(conn: sqlite3.Connection, start: date, end: date, out_path: str) -> str:
    data = build_report_data(conn, start, end)
    html_str = build_html(data)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_str)
    return out_path
