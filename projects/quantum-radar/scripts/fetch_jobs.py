"""Aggregate public LinkedIn quantum-job links without scraping LinkedIn.

An approved RSS or Atom feed is supplied in ``LINKEDIN_JOBS_FEED_URL``. This is
the integration boundary for a LinkedIn Talent Solutions/ATS partner or an
authorized alert-export feed. The script writes state for the Opportunities
renderer; it does not publish a standalone jobs page.
"""

from __future__ import annotations

import calendar
import html
import os
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from common import ROOT, iso_utc, keyword_score, load_yaml, read_json, stable_id, utc_now, write_json

STATE_FILE = ROOT / "state" / "jobs.json"
JOB_ID = re.compile(r"/jobs/view/(?:[^/?]+-)?(?P<id>\d+)")


def _published(entry: Any) -> str:
    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if not parsed:
        return ""
    dt = datetime.utcfromtimestamp(calendar.timegm(parsed)).replace(tzinfo=timezone.utc)
    return iso_utc(dt)


def _plain(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(without_tags)).strip()


def _linkedin_url(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return host.lower().endswith("linkedin.com") and "/jobs/" in urlparse(url).path


def _unwrap_link(url: str) -> str:
    """Return a direct LinkedIn job URL from common alert redirect wrappers."""
    if _linkedin_url(url):
        return url
    params = parse_qs(urlparse(url).query)
    for key in ("url", "q", "target"):
        for candidate in params.get(key, []):
            direct = unquote(candidate)
            if _linkedin_url(direct):
                return direct
    return url


def _key(url: str, title: str) -> str:
    match = JOB_ID.search(url)
    return f"linkedin:{match.group('id')}" if match else stable_id(url, title)


def _set_github_output(name: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")


def _split_title(raw: str) -> tuple[str, str]:
    title = re.sub(r"\s*[|·-]\s*LinkedIn\s*$", "", _plain(raw), flags=re.IGNORECASE)
    # Indexed titles commonly use "Role - Company". Preserve titles with
    # multiple hyphens by splitting from the right only.
    if " - " in title:
        role, company = title.rsplit(" - ", 1)
        return role.strip(), company.strip()
    return title.strip(), ""


def fetch_feed(url: str, source: str, relevance_terms: list[str]) -> list[dict[str, Any]]:
    import feedparser

    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries:
        url_value = _unwrap_link(entry.get("link", "").strip())
        title, company = _split_title(entry.get("title", ""))
        summary = _plain(entry.get("summary", ""))
        score, matched = keyword_score(f"{title}\n{summary}", relevance_terms)
        if score <= 0:
            continue
        if not _linkedin_url(url_value):
            continue
        items.append(
            {
                "id": _key(url_value, title),
                "title": title,
                "company": company,
                "location": "",
                "url": url_value,
                "published": _published(entry),
                "discovered_at": iso_utc(utc_now()),
                "source": source,
                "score": score,
                "matched_keywords": matched,
                "employment_type": "Internship" if re.search(r"\b(?:intern|internship|co-op)\b", title, re.I) else "Job",
            }
        )
    return items


def main() -> int:
    cfg = load_yaml(ROOT / "config" / "jobs.yaml").get("jobs", {})
    relevance = list(cfg.get("relevance_terms", []))
    now = utc_now()
    items = []
    approved_feeds = os.environ.get("LINKEDIN_JOBS_FEED_URL", "").strip()
    if not approved_feeds:
        _set_github_output("run_render", "false")
        print("[fetch_jobs] LINKEDIN_JOBS_FEED_URL is not configured; skipping.")
        return 0
    for approved_feed in filter(None, re.split(r"[\r\n,]+", approved_feeds)):
        items.extend(fetch_feed(approved_feed.strip(), "LinkedIn approved feed", relevance))

    previous = read_json(STATE_FILE, {"items": []}).get("items", [])
    current_by_id = {item["id"]: item for item in items}
    for old in previous:
        old_id = old.get("id")
        if not old_id:
            continue
        if old_id in current_by_id:
            current_by_id[old_id]["discovered_at"] = old.get("discovered_at") or current_by_id[old_id]["discovered_at"]
        else:
            current_by_id[old_id] = old

    max_age_days = int(cfg.get("max_age_days", 45))
    fresh = []
    for item in current_by_id.values():
        timestamp = item.get("published") or item.get("discovered_at")
        if timestamp:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if (now - parsed).days > max_age_days:
                continue
        fresh.append(item)
    unique = {item["id"]: item for item in fresh}
    ranked = sorted(
        unique.values(),
        key=lambda x: (x.get("published", ""), x.get("score", 0)),
        reverse=True,
    )[: int(cfg.get("keep_top_n", 60))]

    write_json(STATE_FILE, {"generated_at": iso_utc(now), "items": ranked})
    _set_github_output("run_render", "true")
    print(f"[fetch_jobs] wrote {STATE_FILE.relative_to(ROOT)} with {len(ranked)} listings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
