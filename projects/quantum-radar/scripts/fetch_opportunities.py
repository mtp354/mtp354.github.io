from __future__ import annotations

import argparse
import calendar
from datetime import datetime, timezone
from typing import Any

from common import (
    ROOT,
    dedupe_by_key,
    google_news_rss_url,
    iso_utc,
    keyword_score,
    load_yaml,
    read_json,
    stable_id,
    utc_now,
    write_json,
)
from funding_common import funding_event_from_item, grant_disposition


def classify(text: str, buckets: dict[str, list[str]]) -> str:
    lowered = text.lower()
    for bucket, kws in buckets.items():
        if any(kw.lower() in lowered for kw in kws):
            return bucket
    return "other"


def fetch_items(rss_queries: list[str]) -> list[dict[str, Any]]:
    import feedparser

    out = []
    for query in rss_queries:
        feed = feedparser.parse(google_news_rss_url(query))
        for entry in feed.entries:
            published = ""
            if getattr(entry, "published_parsed", None):
                dt = datetime.utcfromtimestamp(calendar.timegm(entry.published_parsed)).replace(tzinfo=timezone.utc)
                published = iso_utc(dt)
            out.append(
                {
                    "query": query,
                    "title": entry.get("title", "").strip(),
                    "summary": entry.get("summary", "").strip(),
                    "url": entry.get("link", "").strip(),
                    "published": published,
                }
            )
    return out


def _grants_gov_date(value: str) -> str | None:
    if not value:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _grant_details(opportunity_id: str) -> dict[str, Any]:
    import requests

    try:
        response = requests.post(
            "https://api.grants.gov/v1/api/fetchOpportunity",
            json={"opportunityId": int(opportunity_id)},
            timeout=20,
        )
        response.raise_for_status()
        return response.json().get("data", {}) or {}
    except (requests.RequestException, ValueError, TypeError):
        return {}


def fetch_grants_gov(search_terms: list[str], eligible_terms: list[str]) -> list[dict[str, Any]]:
    """Fetch posted Grants.gov opportunities suitable for an academic applicant."""
    import requests

    allowed = [term.lower() for term in eligible_terms]
    results = []
    seen_ids: set[str] = set()
    for term in search_terms:
        try:
            response = requests.post(
                "https://api.grants.gov/v1/api/search2",
                json={
                    "rows": 10,
                    "keyword": term,
                    "oppStatuses": "posted",
                    "fundingInstruments": "G|CA",
                },
                timeout=20,
            )
            response.raise_for_status()
            hits = response.json().get("data", {}).get("oppHits", []) or []
        except (requests.RequestException, ValueError, TypeError):
            continue

        for hit in hits:
            opportunity_id = str(hit.get("id", ""))
            if not opportunity_id or opportunity_id in seen_ids:
                continue
            seen_ids.add(opportunity_id)
            deadline = _grants_gov_date(hit.get("closeDate", ""))
            if deadline and datetime.fromisoformat(deadline).date() < utc_now().date():
                continue

            details = _grant_details(opportunity_id)
            synopsis = details.get("synopsis", {}) or {}
            applicant_types = [
                str(item.get("description", ""))
                for item in synopsis.get("applicantTypes", []) or []
            ]
            if not applicant_types or not any(
                term in applicant.lower()
                for applicant in applicant_types
                for term in allowed
            ):
                continue

            title = str(hit.get("title") or "").strip()
            organization = str(hit.get("agencyName") or hit.get("agency") or "").strip()
            url = f"https://www.grants.gov/search-results-detail/{opportunity_id}"
            results.append(
                {
                    "id": stable_id("grants.gov", opportunity_id),
                    "query": term,
                    "title": title,
                    "summary": synopsis.get("synopsisDesc", "") or "",
                    "url": url,
                    "published": "",
                    "type": "grants",
                    "score": 100,
                    "matched_keywords": [term],
                    "grant_disposition": "actionable",
                    "application_source": "Grants.gov",
                    "organization": organization,
                    "deadline": deadline,
                    "eligibility": applicant_types,
                    "opportunity_number": hit.get("number", ""),
                }
            )
    return results


def _store_funding_events(previous_state: dict[str, Any], new_events: list[dict[str, Any]], now: datetime) -> int:
    funding_path = ROOT / "state" / "awarded-grants.json"
    funding_events = list(new_events)
    for old_item in previous_state.get("items", []):
        if old_item.get("type") != "grants":
            continue
        old_text = f"{old_item.get('title', '')}\n{old_item.get('summary', '')}"
        if grant_disposition(old_text) == "awarded":
            funding_events.append(funding_event_from_item(old_item))

    previous_funding = read_json(funding_path, {"items": []}).get("items", [])
    combined_funding = dedupe_by_key(
        sorted(
            [*funding_events, *previous_funding],
            key=lambda x: x.get("published", ""),
            reverse=True,
        ),
        "id",
    )
    write_json(funding_path, {"generated_at": iso_utc(now), "items": combined_funding})
    return len(combined_funding)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--migrate-only",
        action="store_true",
        help="move award announcements already in opportunity state without fetching feeds",
    )
    args = parser.parse_args(argv)
    cfg = load_yaml(ROOT / "config" / "opportunities.yaml")
    section = cfg.get("opportunities", {})
    queries = list(section.get("rss_queries", []))
    grant_terms = list(section.get("grants_gov_terms", []))
    eligible_terms = list(section.get("eligible_applicant_terms", []))
    award_queries = list(section.get("award_news_queries", []))
    buckets = dict(section.get("type_keywords", {}))
    keep_top_n = int(section.get("keep_top_n", 20))
    max_age_days = int(section.get("max_age_days", 45))
    now = utc_now()

    keywords = []
    for words in buckets.values():
        keywords.extend(words)
    keywords.extend(["quantum", "quantum computing", "quantum technology"])

    state_path = ROOT / "state" / "opportunities.json"
    previous_state = read_json(state_path, {"items": []})
    if args.migrate_only:
        count = _store_funding_events(previous_state, [], now)
        print(f"Catalogued {count} awarded-grant announcements for the industry report.")
        return 0

    items = [*fetch_items(queries), *fetch_grants_gov(grant_terms, eligible_terms)]
    scored = []
    funding_events = []

    for award_item in fetch_items(award_queries):
        award_text = f"{award_item.get('title', '')}\n{award_item.get('summary', '')}"
        if grant_disposition(award_text) != "awarded":
            continue
        award_item["id"] = stable_id(award_item["url"], award_item["title"])
        funding_events.append(funding_event_from_item(award_item))

    for item in items:
        score, matched = keyword_score(
            f"{item['query']}\n{item['title']}\n{item['summary']}",
            keywords,
        )
        if score <= 0:
            continue

        published = item.get("published")
        if published:
            try:
                pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                if (now - pub_dt).days > max_age_days:
                    continue
            except ValueError:
                pass

        text = f"{item['title']}\n{item['summary']}\n{item['query']}"
        item["type"] = item.get("type") or classify(
            f"{item['title']}\n{item['summary']}", buckets
        )
        item["score"] = score
        item["matched_keywords"] = matched
        item["id"] = item.get("id") or stable_id(item["url"], item["title"])

        if item["type"] == "grants":
            if item.get("application_source") != "Grants.gov":
                continue
            disposition = item.get("grant_disposition") or grant_disposition(text)
            item["grant_disposition"] = disposition
            if disposition == "awarded":
                funding_events.append(funding_event_from_item(item))
                continue
            if disposition != "actionable":
                # A generic story containing the word "grant" is not enough to
                # claim that a reader can apply for it.
                continue
        scored.append(item)

    scored = dedupe_by_key(sorted(scored, key=lambda x: (x["score"], x.get("published", "")), reverse=True), "url")[:keep_top_n]

    write_json(
        state_path,
        {
            "generated_at": iso_utc(now),
            "items": scored,
        },
    )
    funding_count = _store_funding_events(previous_state, funding_events, now)
    print(f"Saved {len(scored)} opportunity items to state. Rendering is handled by render_opportunity_tables.py.")
    print(f"Catalogued {funding_count} awarded-grant announcements for the industry report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
