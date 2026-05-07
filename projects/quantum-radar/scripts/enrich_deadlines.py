"""Best-effort deadline enrichment for opportunities with blank deadlines.

For each entry whose `deadline` is null and `link` is present, fetch the
linked page and look for phrases like "deadline: May 6", "apply by 2026-03-01",
etc. If found, persist the discovered date back into the YAML so we don't
re-fetch on subsequent runs.

Network failures are swallowed; entries without a discoverable deadline are
left untouched and a one-line note is appended to `notes`.
"""

from __future__ import annotations

import sys
import time
from typing import Any

import requests

from opportunities_common import (
    find_deadline_in_text,
    iter_all_entries,
    load_seed,
    save_seed,
)

USER_AGENT = (
    "Mozilla/5.0 (compatible; quantum-radar/1.0; +https://github.com/mtp354/mtp354.github.io)"
)
TIMEOUT = 10
SLEEP_BETWEEN = 1.0  # be polite


def fetch(url: str) -> str:
    try:
        r = requests.get(
            url,
            timeout=TIMEOUT,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"},
            allow_redirects=True,
        )
        if r.status_code >= 400:
            return ""
        ctype = r.headers.get("content-type", "")
        if "html" not in ctype and "text" not in ctype:
            return ""
        return r.text
    except requests.RequestException:
        return ""


def strip_html(html: str) -> str:
    try:
        from bs4 import BeautifulSoup  # type: ignore

        return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    except Exception:
        # Fallback: very rough tag stripping
        import re

        return re.sub(r"<[^>]+>", " ", html)


def enrich_entry(entry: dict[str, Any]) -> bool:
    """Return True if the entry's deadline was newly populated."""
    if entry.get("deadline"):
        return False
    link = entry.get("link") or ""
    if not link.startswith("http"):
        return False

    html = fetch(link)
    if not html:
        return False
    text = strip_html(html)
    found = find_deadline_in_text(text)
    if not found:
        return False
    entry["deadline"] = found
    return True


def main() -> int:
    data = load_seed()
    updated = 0
    attempted = 0
    for _section, entry in iter_all_entries(data):
        if entry.get("deadline"):
            continue
        if not entry.get("link"):
            continue
        attempted += 1
        if enrich_entry(entry):
            updated += 1
            print(f"[enrich] {entry.get('name')!r}: {entry['deadline']}")
        time.sleep(SLEEP_BETWEEN)
    if updated:
        save_seed(data)
    print(f"[enrich] attempted={attempted}, updated={updated}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
