"""Classify grant search results and extract announced award values."""

from __future__ import annotations

import re
from typing import Any


_ACTIONABLE = re.compile(
    r"\b(?:call(?:s)? for (?:proposals?|applications?)|request for proposals?|rfp|"
    r"funding opportunity|solicitation|applications? (?:are )?(?:open|invited)|"
    r"apply (?:now|by)|submit (?:an? )?(?:application|proposal)|proposal deadline|"
    r"application deadline|accepting (?:applications|proposals))\b",
    re.IGNORECASE,
)

_AWARDED = re.compile(
    r"\b(?:awarded?|receives?|received|secures?|secured|wins?|won|selected for|"
    r"funded by|grant (?:will )?(?:fund|supports?|advances?)|announces? .*?grant|"
    r"grant funding (?:for|to)|investment in)\b",
    re.IGNORECASE,
)

_MONEY = re.compile(
    r"(?P<prefix>US\$|USD\s*|C\$|CAD\s*|A\$|AUD\s*|£|GBP\s*|€|EUR\s*|\$)"
    r"\s*(?P<number>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*"
    r"(?P<scale>trillion|billion|million|bn|mn|[TBMK])?\b",
    re.IGNORECASE,
)

_SCALE = {
    "": 1,
    "k": 1_000,
    "m": 1_000_000,
    "mn": 1_000_000,
    "million": 1_000_000,
    "b": 1_000_000_000,
    "bn": 1_000_000_000,
    "billion": 1_000_000_000,
    "t": 1_000_000_000_000,
    "trillion": 1_000_000_000_000,
}


def grant_disposition(text: str) -> str:
    """Return ``actionable``, ``awarded``, or ``unknown`` for grant text.

    Explicit application language wins because a call announcement can mention
    awards while still being something a reader can apply for.
    """
    if _ACTIONABLE.search(text or ""):
        return "actionable"
    if _AWARDED.search(text or ""):
        return "awarded"
    return "unknown"


def _currency(prefix: str) -> str:
    value = prefix.upper().replace(" ", "")
    if value in {"US$", "USD", "$"}:
        return "USD"
    if value in {"C$", "CAD"}:
        return "CAD"
    if value in {"A$", "AUD"}:
        return "AUD"
    if value in {"£", "GBP"}:
        return "GBP"
    if value in {"€", "EUR"}:
        return "EUR"
    return value


def extract_money(text: str) -> list[dict[str, Any]]:
    """Extract unique explicitly-currency-marked amounts without FX conversion."""
    amounts: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for match in _MONEY.finditer(text or ""):
        scale = (match.group("scale") or "").lower()
        amount = int(round(float(match.group("number").replace(",", "")) * _SCALE[scale]))
        currency = _currency(match.group("prefix"))
        key = (currency, amount)
        if key in seen:
            continue
        seen.add(key)
        amounts.append(
            {
                "currency": currency,
                "amount": amount,
                "display": match.group(0).strip(),
            }
        )
    return amounts


def funding_event_from_item(item: dict[str, Any]) -> dict[str, Any]:
    """Convert an RSS item into the stable funding-event state schema."""
    title = item.get("title", "")
    # Prefer the headline's amount. Summaries can mention larger program totals
    # that are context rather than the value of this particular award.
    amounts = extract_money(title) or extract_money(item.get("summary", ""))
    return {
        "id": item.get("id", ""),
        "title": item.get("title", ""),
        "url": item.get("url", ""),
        "published": item.get("published", ""),
        "amounts": amounts,
    }
