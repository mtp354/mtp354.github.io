"""Render the curated + scraped opportunities into Jekyll table pages.

Reads:
  - data/seed_opportunities.yaml   (manually curated)
  - state/opportunities.json       (RSS-discovered items, refreshed by
                                    fetch_opportunities.py)

Writes:
  - _quantum_radar/opportunities-<YYYY-MM-DD>.md   (Jekyll collection entry)

Each section is a markdown table with columns:
    Name | Organization | Type | Deadline | Status | Link | Notes

Status is auto-derived from the deadline (Open if no deadline or in the
future, otherwise Closed). Application status from the source spreadsheet
is intentionally never published.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opportunities_common import (
    SECTION_KEYS,
    SECTION_LABELS,
    fmt_deadline,
    is_open,
    load_seed,
    md_escape_cell,
)

ROOT = Path(__file__).resolve().parents[1]
SITE_ROOT = ROOT.parents[1]
STATE_FILE = ROOT / "state" / "opportunities.json"
COLLECTION_DIR = SITE_ROOT / "_quantum_radar"

# Map RSS-discovered "type" buckets to our section keys.
RSS_TYPE_MAP = {
    "internships": "internships",
    "grants": "grants",
    "summer_programs": "summer_programs",
    "hackathons": "hackathons",
    "fellowships": "fellowships",
}


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_rss_items() -> list[dict[str, Any]]:
    if not STATE_FILE.exists():
        return []
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data.get("items", []) or []


def _rss_to_entry(item: dict[str, Any]) -> dict[str, Any] | None:
    bucket = RSS_TYPE_MAP.get(item.get("type", ""))
    if not bucket:
        return None
    title = (item.get("title") or "").strip()
    if not title:
        return None
    # Try to peel an "— Source" suffix into organization
    organization = ""
    if " - " in title:
        head, _, tail = title.rpartition(" - ")
        if 2 <= len(tail) <= 60:
            title = head
            organization = tail
    return {
        "name": title,
        "organization": organization,
        "location": "",
        "type": bucket,
        "deadline": None,
        "link": item.get("url", ""),
        "notes": "",
    }


def _merge(seed: dict[str, list[dict[str, Any]]], rss: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    merged = {key: list(seed.get(key, [])) for key in SECTION_KEYS}
    seen = {entry.get("link", "") for entries in merged.values() for entry in entries}
    seen.discard("")
    for raw in rss:
        entry = _rss_to_entry(raw)
        if not entry:
            continue
        link = entry["link"]
        if link and link in seen:
            continue
        merged[entry["type"]].append(entry)
        if link:
            seen.add(link)
    return merged


def _render_table(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return "_No entries._\n"
    header = "| Name | Organization | Location | Type | Deadline | Status | Link | Notes |\n"
    sep = "|---|---|---|---|---|---|---|---|\n"
    rows = []
    # Open first, then Closed; within each group, soonest deadline first
    # (entries without a deadline sort to the end of the Open group).
    def sort_key(e: dict[str, Any]) -> tuple[int, str]:
        d = e.get("deadline") or ""
        return (0 if is_open(d) else 1, d or "9999-12-31")

    for e in sorted(entries, key=sort_key):
        name = md_escape_cell(e.get("name", ""))
        org = md_escape_cell(e.get("organization", ""))
        location = md_escape_cell(e.get("location", ""))
        typ = md_escape_cell(e.get("type", ""))
        deadline = fmt_deadline(e.get("deadline"))
        status = "Open" if is_open(e.get("deadline")) else "Closed"
        link = (e.get("link") or "").strip()
        link_md = f"[apply]({link})" if link else "—"
        notes = md_escape_cell(e.get("notes") or "")
        rows.append(
            f"| {name} | {org} | {location or '—'} | {typ} | {deadline} | {status} | {link_md} | {notes} |"
        )
    return header + sep + "\n".join(rows) + "\n"


def render(merged: dict[str, list[dict[str, Any]]]) -> str:
    today = _today()
    lines = [f"_Generated: {today} UTC_", ""]
    section_order = ["internships", "grants", "summer_programs", "hackathons", "fellowships"]
    for key in section_order:
        entries = merged.get(key, [])
        lines.append(f"## {SECTION_LABELS[key]}")
        lines.append("")
        lines.append(_render_table(entries).rstrip())
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_collection_entry(body: str) -> Path:
    today = _today()
    out = COLLECTION_DIR / f"opportunities-{today}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    front = (
        "---\n"
        f'title: "Opportunities — {today}"\n'
        f"date: {today}\n"
        "report_type: opportunities\n"
        'excerpt: "Grants, internships, summer schools, and fellowships."\n'
        "tags:\n"
        "  - opportunities\n"
        "  - quantum-radar\n"
        "---\n\n"
    )
    out.write_text(front + body, encoding="utf-8")
    return out


def main() -> int:
    seed = load_seed()
    rss = _load_rss_items()
    merged = _merge(seed, rss)
    body = render(merged)
    out = write_collection_entry(body)
    rel = out.relative_to(SITE_ROOT)
    total = sum(len(v) for v in merged.values())
    print(f"[render_opportunity_tables] wrote {rel} with {total} entries.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
