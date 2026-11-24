# cents

**Zero-dependency personal finance on your own machine.**

Drop in a bank or credit-card CSV. `cents` normalizes the messy merchant names, categorizes every transaction (built-in rules, then an optional local LLM for the unknowns), and renders a beautiful self-contained **"where my money went"** report — pure Python, no `pip install`, no cloud account, no data leaving your machine.

```
$ cents import chase.csv
$ cents categorize --llm
$ cents report --open
```

---

## Why

Every budgeting app wants your credentials or sells your data. Your bank already gives you a CSV export — that's the whole API. `cents` turns that export into something you'd actually want to look at, with zero dependencies and zero telemetry.

## Features

- **CSV import** — auto-detects columns (`Transaction Date`, `Posted Date`, `Description`/`Merchant`/`Payee`, `Amount` or `Debit`/`Credit`, category, account). Idempotent: re-importing the same file skips duplicates.
- **Merchant normalization** — `POS DEBIT 1234 AMZN MKTP US*AB123CD45` → `Amazon`. Strips terminal/reference noise and canonicalizes ~60 well-known brands.
- **Smart categorization** — ~140 built-in rules across 15 categories. Anything unmatched falls to `Other`, then a **local LLM** (Ollama by default, or any OpenAI-compatible endpoint) can classify the stragglers and *remember* the answer for next time.
- **Self-contained HTML report** — dark theme, inline SVG charts (donut, bars, daily trend), top merchants, recurring subscriptions, and plain-English insights like *"Dining jumped 42% vs last week."* One file, zero JS/CDN, open in any browser.
- **SQLite storage** — everything lands in `~/.cents/cents.db`. Inspect it, back it up, `DELETE` it — it's yours.

## Install

Requires Python 3.10+. No dependencies to install.

```bash
git clone https://github.com/prateekmulye/cents
cd cents

# run directly (no install needed)
python3 -m cents --help

# or install a `cents` command
uv tool install .     # or: pipx install .
```

## Quick start

```bash
# 1. Export your transactions as CSV from your bank, then import:
cents import ~/Downloads/chase_checking.csv --account checking
cents import ~/Downloads/amex.csv --account amex

# 2. Categorize everything (rules first):
cents categorize

# 3. Let a local LLM classify the unknowns (optional):
ollama pull llama3.2            # once
cents categorize --llm

# 4. Generate this week's report and open it:
cents report --open
cents report --week last        # the previous full week
cents report --month            # rolling 30 days
```

### LLM backends (optional)

| Backend | Setup |
|---|---|
| **Ollama** (default) | `ollama pull llama3.2`, then `cents categorize --llm` |
| **Any OpenAI-compatible** | `export OPENAI_API_KEY=...` and optionally `OPENAI_BASE_URL=...`, then `cents categorize --llm --model gpt-4o-mini` |

No LLM? No problem — rule-based categorization still covers the common cases, and the report flags anything stuck in `Other` for manual review.

## Commands

| Command | What it does |
|---|---|
| `cents import <file.csv> [--account NAME]` | Import a CSV (dedupes on re-run) |
| `cents categorize [--llm] [--model M]` | Assign categories; persist learned merchants |
| `cents categorize --set "Merchant" "Category"` | Manual override for a merchant |
| `cents report [--week last\|this] [--month] [--out F] [--open]` | Render the HTML report |
| `cents list [--category X] [--merchant Y] [--limit N]` | Print transactions |
| `cents categories` | Totals per category |

## CSV format

Any of these work; columns are matched by name, case-insensitively:

- `Date, Description, Amount` (signed: negative = money in)
- `Transaction Date, Merchant, Debit, Credit` (separate columns)
- Most Chase / Amex / Capital One / bank exports as-is.

**Amount convention:** positive = money out, negative = money in. If your bank uses a single `Amount` column with the opposite sign, import then flip with SQLite or file an issue.

## How it works

1. **`ingest`** — detects columns, parses amounts (`$1,234.56`, `(99.99)`), normalizes merchants, hashes each row for idempotent re-import.
2. **`categorize`** — learned overrides → built-in rules (first match wins) → optional LLM fallback. Income is handled by sign, not name.
3. **`report`** — summarizes the period and its predecessor, computes per-category deltas, then renders a single HTML file with inline SVG.

Everything runs locally. The only network call is the optional, opt-in LLM categorization.

## Layout

```
cents/
├── cents/            # the package
│   ├── cli.py        # argparse CLI
│   ├── db.py         # SQLite schema + connection
│   ├── ingest.py     # CSV import + dedupe
│   ├── normalize.py  # merchant-name cleanup
│   ├── rules.py      # categories + matching rules
│   ├── categorize.py # rule engine + LLM fallback
│   ├── insights.py   # period summaries + deltas
│   └── report.py     # HTML/SVG report
├── sample/           # demo CSV + generator
└── tests/            # pytest (stdlib-friendly; no deps required)
```

## Try the demo

```bash
python3 sample/generate_sample.py   # writes sample/transactions.csv
CENTS_DB=/tmp/cents-demo.db python3 -m cents import sample/transactions.csv
CENTS_DB=/tmp/cents-demo.db python3 -m cents categorize
CENTS_DB=/tmp/cents-demo.db python3 -m cents report --week last --out report.html --open
```

## Tests

```bash
python3 -m pytest tests/ -q      # or: python3 -m unittest discover
```

## License

MIT — see [LICENSE](LICENSE).
