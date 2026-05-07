"""Shared helpers for working with the curated opportunity seed list."""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SEED_YAML = DATA_DIR / "seed_opportunities.yaml"

SECTION_KEYS = ["internships", "grants", "summer_programs", "hackathons", "fellowships"]
SECTION_LABELS = {
    "internships": "Internships",
    "grants": "Grants",
    "summer_programs": "Summer Programs",
    "hackathons": "Hackathons",
    "fellowships": "Fellowships",
}


def load_seed() -> dict[str, list[dict[str, Any]]]:
    if not SEED_YAML.exists():
        return {key: [] for key in SECTION_KEYS}
    with SEED_YAML.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    out: dict[str, list[dict[str, Any]]] = {}
    for key in SECTION_KEYS:
        items = data.get(key) or []
        out[key] = [dict(it) for it in items]
    return out


def save_seed(data: dict[str, list[dict[str, Any]]]) -> None:
    cleaned = {key: data.get(key, []) for key in SECTION_KEYS if data.get(key)}
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with SEED_YAML.open("w", encoding="utf-8") as f:
        yaml.safe_dump(cleaned, f, sort_keys=False, allow_unicode=True, width=100)


# Regex patterns for finding application deadlines on a page.
_MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|November|December"
    "|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec"
)
_DATE_PATTERNS = [
    re.compile(rf"({_MONTHS})\s+(\d{{1,2}})(?:,?\s*(\d{{4}}))?", re.IGNORECASE),
    re.compile(r"(\d{1,2})/(\d{1,2})/(\d{2,4})"),
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),
]

_DEADLINE_TRIGGERS = re.compile(
    r"(?:deadline|apply\s+by|application\s+(?:deadline|closes?|due)|"
    r"applications?\s+(?:close|due)|due\s+(?:date|by)|closes?\s+on)"
    r"[^\n\r<]{0,80}",
    re.IGNORECASE,
)


def _normalize_year(year_str: str | None) -> int | None:
    if not year_str:
        return None
    y = int(year_str)
    if y < 100:
        y += 2000
    return y


def _try_parse_match(match: re.Match) -> date | None:
    groups = match.groups()
    today = datetime.now(timezone.utc).date()
    try:
        # Pattern 1: "Month D[, Y]"
        if re.match(r"[A-Za-z]", groups[0]):
            month_str, day_str, year_str = groups[0], groups[1], groups[2]
            year = _normalize_year(year_str) or today.year
            dt = datetime.strptime(f"{month_str[:3]} {day_str} {year}", "%b %d %Y").date()
            # If user omitted year and the date is already past, assume next year.
            if not year_str and dt < today:
                dt = dt.replace(year=today.year + 1)
            return dt
        # Pattern 3: "YYYY-MM-DD"
        if len(groups[0]) == 4:
            return date(int(groups[0]), int(groups[1]), int(groups[2]))
        # Pattern 2: "M/D/Y"
        m, d, y = int(groups[0]), int(groups[1]), _normalize_year(groups[2])
        return date(y, m, d)
    except (ValueError, TypeError):
        return None


def find_deadline_in_text(text: str) -> str | None:
    """Return ISO date string for the first deadline-shaped phrase found in text."""
    if not text:
        return None
    for trigger in _DEADLINE_TRIGGERS.finditer(text):
        snippet = trigger.group(0)
        for pat in _DATE_PATTERNS:
            m = pat.search(snippet)
            if not m:
                continue
            parsed = _try_parse_match(m)
            if parsed:
                return parsed.isoformat()
    return None


def is_open(deadline_iso: str | None) -> bool:
    if not deadline_iso:
        return True
    try:
        d = date.fromisoformat(deadline_iso)
    except ValueError:
        return True
    return d >= datetime.now(timezone.utc).date()


def fmt_deadline(deadline_iso: str | None) -> str:
    if not deadline_iso:
        return "—"
    try:
        return date.fromisoformat(deadline_iso).strftime("%Y-%m-%d")
    except ValueError:
        return deadline_iso


def md_escape_cell(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ").strip()


def iter_all_entries(data: dict[str, list[dict[str, Any]]]) -> Iterable[tuple[str, dict[str, Any]]]:
    for key in SECTION_KEYS:
        for entry in data.get(key, []):
            yield key, entry
