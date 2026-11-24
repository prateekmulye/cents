"""Merchant-name normalization.

Raw bank descriptions ("POS DEBIT 1234 AMZN MKTP US*AB123CD45") are noisy.
This module strips transaction/terminal/reference noise and canonicalizes
well-known brands so that "Amazon" is always "Amazon".
"""

from __future__ import annotations

import re

# Canonical brand names, matched case-insensitively on whole words.
# Order matters: more specific names must appear before generic ones that
# share a prefix (e.g. "APPLEBEE" before "APPLE").
BRANDS: dict[str, str] = {
    "APPLEBEE": "Applebee's",
    "APPLE": "Apple",
    "AMAZON": "Amazon",
    "AMZN": "Amazon",
    "WALMART": "Walmart",
    "TARGET": "Target",
    "COSTCO": "Costco",
    "TRADER JOE": "Trader Joe's",
    "WHOLE FOODS": "Whole Foods",
    "SAFEWAY": "Safeway",
    "STARBUCKS": "Starbucks",
    "MCDONALD": "McDonald's",
    "CHIPOTLE": "Chipotle",
    "PANERA": "Panera",
    "SWEETGREEN": "Sweetgreen",
    "DUNKIN": "Dunkin'",
    "CHICK FIL": "Chick-fil-A",
    "BURGER KING": "Burger King",
    "UBER": "Uber",
    "LYFT": "Lyft",
    "DOORDASH": "DoorDash",
    "GRUBHUB": "Grubhub",
    "NETFLIX": "Netflix",
    "SPOTIFY": "Spotify",
    "HULU": "Hulu",
    "DISNEY": "Disney+",
    "GOOGLE": "Google",
    "MICROSOFT": "Microsoft",
    "ADOBE": "Adobe",
    "NOTION": "Notion",
    "GITHUB": "GitHub",
    "OPENAI": "OpenAI",
    "COMCAST": "Comcast",
    "XFINITY": "Xfinity",
    "VERIZON": "Verizon",
    "SHELL": "Shell",
    "CHEVRON": "Chevron",
    "EXXON": "Exxon",
    "CVS": "CVS",
    "WALGREENS": "Walgreens",
    "VENMO": "Venmo",
    "PAYPAL": "PayPal",
    "ZELLE": "Zelle",
    "CHASE": "Chase",
    "BANK OF AMERICA": "Bank of America",
    "EQUINOX": "Equinox",
    "PLANET FITNESS": "Planet Fitness",
    "AIRBNB": "Airbnb",
    "MARRIOTT": "Marriott",
    "HILTON": "Hilton",
    "DELTA": "Delta",
    "UNITED": "United",
    "SOUTHWEST": "Southwest",
    "NIKE": "Nike",
    "ADIDAS": "Adidas",
    "IKEA": "IKEA",
    "HOME DEPOT": "Home Depot",
    "BEST BUY": "Best Buy",
    "EBAY": "eBay",
    "ETSY": "Etsy",
    "TICKETMASTER": "Ticketmaster",
    "STUBHUB": "StubHub",
    "HERTZ": "Hertz",
    "AVIS": "Avis",
}

_PREFIX_NOISE = [
    r"(?i)^(point\s*of\s*sale|pos)\b[:\- ]*",
    r"(?i)^(debit\s*card\s*(purchase|payment)?|checkcard)\b[:\- ]*",
    r"(?i)^(purchase|payment|recurring|auto\s*pay|direct\s*debit|ach)\b[:\- ]*",
]

_TRANSACTION_NOISE = [
    r"\b(mktp|mkp|marketplace)\b",
    r"\b(pos|purchase|debit|payment|recurring|card|check)\b",
    r"\b(us|ca|uk|au|gb|de|fr|jp)\b",
]


def _strip_noise(raw: str) -> str:
    s = re.sub(r"\s+", " ", raw.strip())
    s = s.replace("*", " ").replace("  ", " ")
    for pat in _PREFIX_NOISE:
        s = re.sub(pat, "", s)
    # drop URLs and anything after them ("HELP.UBER.COM" -> "HELP.UBER")
    s = re.sub(r"\.com\b.*$", "", s, flags=re.I)
    # drop trailing reference numbers / codes
    s = re.sub(r"\s*(ref|reference|conf|id|txn|order|inv|#)\s*[:#]?\s*[A-Za-z0-9\-]+$", "", s, flags=re.I)
    s = re.sub(r"\s+\d{4,}$", "", s)  # trailing terminal/store ids
    for word in _TRANSACTION_NOISE:
        s = re.sub(word, " ", s, flags=re.I)
    s = re.sub(r"[#&/+]+", " ", s)
    s = re.sub(r"\s{2,}", " ", s).strip(" -")
    return s


def normalize_merchant(raw: str) -> str:
    """Turn a raw bank description into a clean merchant name."""
    if not raw:
        return "Unknown"
    s = _strip_noise(raw)
    up = s.upper()
    for key, canonical in BRANDS.items():
        if re.search(rf"\b{re.escape(key)}\b", up):
            return canonical
    if not s:
        return "Unknown"
    # Title-case the remainder, preserving things like "Joe's"
    return re.sub(r"\b\w", lambda m: m.group(0).upper(), s.lower())
