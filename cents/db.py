"""SQLite storage for cents.

The database lives at ``~/.cents/cents.db`` by default (override with the
``CENTS_DB`` environment variable). It is created on first use.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT    NOT NULL,   -- ISO date, e.g. 2026-11-24
    merchant        TEXT    NOT NULL,   -- normalized merchant name
    raw_description TEXT    NOT NULL,   -- original description from the CSV
    amount          REAL    NOT NULL,   -- positive = money out, negative = money in
    category        TEXT,               -- assigned category (NULL = not yet categorized)
    account         TEXT,               -- optional account/label
    source          TEXT,               -- file the row came from
    hash            TEXT    UNIQUE NOT NULL  -- dedupe key
);
CREATE TABLE IF NOT EXISTS merchant_categories (
    merchant    TEXT PRIMARY KEY,
    category    TEXT NOT NULL,
    source      TEXT NOT NULL,          -- 'rule' | 'llm' | 'manual'
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tx_date     ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions(category);
CREATE INDEX IF NOT EXISTS idx_tx_merchant ON transactions(merchant);
"""


def default_db_path() -> Path:
    env = os.environ.get("CENTS_DB")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".cents" / "cents.db"


def connect(path: str | os.PathLike | None = None) -> sqlite3.Connection:
    db_path = Path(path) if path else default_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn
