"""Build an upcoming quantum-adjacent academic and industry conference report."""

from __future__ import annotations

import argparse
import calendar
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from common import ROOT, google_news_rss_url, iso_utc, load_yaml, read_json, stable_id, utc_now, write_json

SITE_ROOT = ROOT.parents[1]
COLLECTION_DIR = SITE_ROOT / "_quantum_radar"
STATE_FILE = ROOT / "state" / "conferences.json"
USER_AGENT = "quantum-radar/1.0 (+https://github.com/mtp354/mtp354.github.io)"

INDUSTRY_WORDS = re.compile(
    r"\b(?:industry|commercial|business|executive|investor|expo|summit|enterprise|ecosystem)\b",
    re.IGNORECASE,
)
EVENT_WORDS = re.compile(
    r"\b(?:conference|congress|symposium|summit|workshop|annual meeting|call for papers|cfp)\b",
    re.IGNORECASE,
)


def _as_iso(value: Any) -> str:
    if not value:
        return ""
    raw = str(value).strip()
    try:
        return date.fromisoformat(raw[:10]).isoformat()
    except ValueError:
        return ""


def _json_objects(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        graph = value.get("@graph")
        if graph:
            yield from _json_objects(graph)
    elif isinstance(value, list):
        for item in value:
            yield from _json_objects(item)


def _location_from_json(value: Any) -> str:
    if isinstance(value, list):
        return "; ".join(filter(None, (_location_from_json(x) for x in value)))
    if not isinstance(value, dict):
        return str(value or "")
    address = value.get("address", {})
    if isinstance(address, str):
        return address
    if isinstance(address, dict):
        parts = [
            address.get("addressLocality"),
            address.get("addressRegion"),
            address.get("addressCountry"),
        ]
        return ", ".join(str(x) for x in parts if x)
    return str(value.get("name", ""))


def scrape_event(url: str) -> dict[str, str]:
    """Read schema.org Event metadata from an official conference page."""
    import requests
    from bs4 import BeautifulSoup

    try:
        response = requests.get(url, timeout=15, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
    except requests.RequestException:
        return {}
    soup = BeautifulSoup(response.text, "html.parser")
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or script.get_text())
        except (json.JSONDecodeError, TypeError):
            continue
        for obj in _json_objects(data):
            kind = obj.get("@type", "")
            kinds = kind if isinstance(kind, list) else [kind]
            if "Event" not in kinds:
                continue
            return {
                "start_date": _as_iso(obj.get("startDate")),
                "end_date": _as_iso(obj.get("endDate")),
                "location": _location_from_json(obj.get("location")),
            }
    return {}


def _published(entry: Any) -> str:
    if getattr(entry, "published_parsed", None):
        dt = datetime.utcfromtimestamp(calendar.timegm(entry.published_parsed)).replace(tzinfo=timezone.utc)
        return iso_utc(dt)
    return ""


def discover(queries: list[str], max_age_days: int) -> list[dict[str, Any]]:
    import feedparser

    now = utc_now()
    found = []
    for query in queries:
        feed = feedparser.parse(google_news_rss_url(query))
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            summary = entry.get("summary", "").strip()
            if not EVENT_WORDS.search(f"{title} {summary}"):
                continue
            published = _published(entry)
            if published:
                parsed = datetime.fromisoformat(published.replace("Z", "+00:00"))
                if (now - parsed).days > max_age_days:
                    continue
            url = entry.get("link", "").strip()
            found.append(
                {
                    "id": stable_id(url, title),
                    "name": title,
                    "organizer": "",
                    "category": "industry" if INDUSTRY_WORDS.search(title) else "academic",
                    "url": url,
                    "start_date": "",
                    "end_date": "",
                    "location": "",
                    "notes": "Newly announced or indexed; verify dates on the linked page.",
                    "published": published,
                    "source": "discovery",
                }
            )
    unique = {item["url"]: item for item in found if item["url"]}
    return sorted(unique.values(), key=lambda x: x.get("published", ""), reverse=True)


def _active(event: dict[str, Any]) -> bool:
    ending = event.get("end_date") or event.get("start_date")
    if not ending:
        return True
    try:
        return date.fromisoformat(ending) >= datetime.now(timezone.utc).date()
    except ValueError:
        return True


def _date_text(event: dict[str, Any]) -> str:
    start = event.get("start_date", "")
    end = event.get("end_date", "")
    if start and end and start != end:
        return f"{start} to {end}"
    return start or "TBA"


def _cell(value: Any) -> str:
    return str(value or "—").replace("|", "\\|").replace("\n", " ")


def render(events: list[dict[str, Any]], generated: str) -> str:
    lines = [f"_Generated: {generated} UTC._", ""]
    for category, label in (("academic", "Academic conferences"), ("industry", "Industry conferences and summits")):
        lines.extend([f"## {label}", ""])
        rows = [event for event in events if event.get("category") == category and _active(event)]
        rows.sort(key=lambda x: (x.get("start_date") or "9999-12-31", x.get("name", "")))
        if not rows:
            lines.extend(["_No upcoming events found._", ""])
            continue
        lines.extend([
            "| Conference | Organizer | Dates | Location | Link | Notes |",
            "|---|---|---|---|---|---|",
        ])
        for event in rows:
            link = f"[details]({event['url']})" if event.get("url") else "—"
            lines.append(
                f"| {_cell(event.get('name'))} | {_cell(event.get('organizer'))} | "
                f"{_date_text(event)} | {_cell(event.get('location'))} | {link} | {_cell(event.get('notes'))} |"
            )
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--offline",
        action="store_true",
        help="render curated events and cached metadata without network requests",
    )
    args = parser.parse_args(argv)
    cfg = load_yaml(ROOT / "config" / "conferences.yaml").get("conferences", {})
    previous = read_json(STATE_FILE, {"items": []}).get("items", [])
    previous_by_id = {event.get("id"): event for event in previous if event.get("id")}
    events = []
    for configured in cfg.get("events", []):
        event = dict(configured)
        event_id = stable_id(event.get("url", ""), event.get("name", ""))
        cached = previous_by_id.get(event_id, {})
        for key in ("start_date", "end_date", "location"):
            if cached.get(key) and not event.get(key):
                event[key] = cached[key]
        should_scrape = event.get("scrape", True) and event.get("url") and not args.offline
        scraped = scrape_event(event.get("url", "")) if should_scrape else {}
        for key, value in scraped.items():
            if value:
                event[key] = value
        event["id"] = event_id
        event["source"] = "curated"
        events.append(event)

    discovered = [] if args.offline else discover(
        list(cfg.get("discovery_queries", [])),
        int(cfg.get("max_discovery_age_days", 120)),
    )[: int(cfg.get("keep_discovered_n", 20))]
    known_urls = {event.get("url") for event in events}
    events.extend(item for item in discovered if item.get("url") not in known_urls)

    now = utc_now()
    write_json(STATE_FILE, {"generated_at": iso_utc(now), "items": events})
    today = now.strftime("%Y-%m-%d")
    front = (
        "---\n"
        f'title: "Conferences — {today}"\n'
        f"date: {today}\n"
        "report_type: conferences\n"
        'excerpt: "Upcoming quantum-adjacent academic conferences, industry conferences, and summits."\n'
        "tags:\n  - conferences\n  - quantum-radar\n"
        "---\n\n"
    )
    out = COLLECTION_DIR / f"conferences-{today}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(front + render(events, today), encoding="utf-8")
    print(f"[fetch_conferences] wrote {out.relative_to(SITE_ROOT)} with {len(events)} events")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
