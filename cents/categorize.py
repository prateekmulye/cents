"""Categorization: rules first, optional local-LLM fallback for the rest."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import urllib.request
from datetime import datetime, timezone

from .rules import CATEGORIES, RULES

COMPILED: list[tuple[str, list[re.Pattern]]] = [
    (cat, [re.compile(p, re.I) for p in pats]) for cat, pats in RULES
]


def match_rule(merchant: str) -> str | None:
    for category, patterns in COMPILED:
        for pat in patterns:
            if pat.search(merchant):
                return category
    return None


def learned_category(conn: sqlite3.Connection, merchant: str) -> str | None:
    row = conn.execute(
        "SELECT category FROM merchant_categories WHERE merchant = ?", (merchant,)
    ).fetchone()
    return row["category"] if row else None


def _store_learned(conn: sqlite3.Connection, merchant: str, category: str, source: str) -> None:
    conn.execute(
        """INSERT INTO merchant_categories (merchant, category, source, updated_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(merchant) DO UPDATE SET
             category = excluded.category,
             source = excluded.source,
             updated_at = excluded.updated_at""",
        (merchant, category, source, datetime.now(timezone.utc).isoformat()),
    )


def set_override(conn: sqlite3.Connection, merchant: str, category: str) -> None:
    """Manually assign a category to a merchant (persisted, wins over rules)."""
    if category not in CATEGORIES:
        raise ValueError(f"unknown category {category!r}; choose from {CATEGORIES}")
    _store_learned(conn, merchant, category, "manual")
    conn.execute(
        "UPDATE transactions SET category = ? WHERE merchant = ?",
        (category, merchant),
    )


def categorize(conn: sqlite3.Connection, merchant: str, amount: float) -> str:
    """Return the category for a transaction. Never returns None."""
    learned = learned_category(conn, merchant)
    if learned:
        return learned

    # Money coming in is income unless it's clearly a transfer.
    if amount < 0:
        rule = match_rule(merchant)
        if rule in (None, "Income", "Transfer"):
            return "Income" if rule != "Transfer" else "Transfer"
        return rule

    return match_rule(merchant) or "Other"


def categorize_all(conn: sqlite3.Connection, use_llm: bool = False, model: str | None = None) -> dict:
    """Categorize every transaction and persist results. Returns a summary."""
    txs = conn.execute(
        "SELECT id, merchant, amount FROM transactions ORDER BY merchant"
    ).fetchall()

    # Pass 1: rules + learned overrides.
    for tx in txs:
        cat = categorize(conn, tx["merchant"], tx["amount"])
        conn.execute("UPDATE transactions SET category = ? WHERE id = ?", (cat, tx["id"]))

    stats = {"total": len(txs), "categorized": 0, "uncategorized": 0, "llm": 0}

    # Pass 2: LLM fallback for merchants still stuck on "Other".
    if use_llm:
        others = conn.execute(
            "SELECT DISTINCT merchant FROM transactions WHERE category = 'Other'"
        ).fetchall()
        if others:
            mapping = _llm_categorize([r["merchant"] for r in others], model)
            if mapping:
                for merchant, cat in mapping.items():
                    if cat in CATEGORIES:
                        _store_learned(conn, merchant, cat, "llm")
                        conn.execute(
                            "UPDATE transactions SET category = ? WHERE merchant = ?",
                            (cat, merchant),
                        )
                        stats["llm"] += 1

    for row in conn.execute(
        "SELECT COUNT(*) AS n, CASE WHEN category='Other' THEN 0 ELSE 1 END AS ok "
        "FROM transactions GROUP BY ok"
    ).fetchall():
        if row["ok"]:
            stats["categorized"] = row["n"]
        else:
            stats["uncategorized"] = row["n"]

    conn.commit()
    return stats


# --------------------------------------------------------------------------
# Optional LLM backend. Defaults to a local Ollama instance; falls back to
# any OpenAI-compatible /v1/chat/completions endpoint via env vars.
# --------------------------------------------------------------------------

def _ollama_chat(model: str, prompt: str) -> str | None:
    url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    body = json.dumps({"model": model, "stream": False, "messages": [{"role": "user", "content": prompt}]})
    req = urllib.request.Request(
        f"{url.rstrip('/')}/api/chat", data=body.encode(), headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())["message"]["content"]
    except Exception:
        return None


def _openai_chat(model: str, prompt: str) -> str | None:
    key = os.environ.get("OPENAI_API_KEY")
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    if not key:
        return None
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0})
    req = urllib.request.Request(
        f"{base.rstrip('/')}/chat/completions",
        data=body.encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())["choices"][0]["message"]["content"]
    except Exception:
        return None


def _llm_categorize(merchants: list[str], model: str | None) -> dict[str, str]:
    model = model or os.environ.get("CENTS_LLM_MODEL", "llama3.2")
    categories = ", ".join(CATEGORIES)
    prompt = (
        f"You are categorizing financial transactions. Assign each merchant to exactly "
        f"one of these categories: {categories}.\n"
        f"Respond with ONLY a JSON object mapping merchant -> category.\n\nMerchants:\n"
        + "\n".join(f"- {m}" for m in merchants)
    )

    raw = _ollama_chat(model, prompt) or _openai_chat(model, prompt)
    if not raw:
        return {}
    # Tolerate fenced/verbose replies by extracting the first JSON object.
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return {k: v for k, v in data.items() if isinstance(v, str)}
