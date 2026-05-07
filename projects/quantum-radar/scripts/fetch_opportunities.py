from __future__ import annotations

import calendar
from datetime import datetime, timezone
from typing import Any

import feedparser

from common import (
    ROOT,
    dedupe_by_key,
    google_news_rss_url,
    iso_utc,
    keyword_score,
    load_yaml,
    stable_id,
    utc_now,
    write_json,
)


def classify(text: str, buckets: dict[str, list[str]]) -> str:
    lowered = text.lower()
    for bucket, kws in buckets.items():
        if any(kw.lower() in lowered for kw in kws):
            return bucket
    return "other"


def fetch_items(rss_queries: list[str]) -> list[dict[str, Any]]:
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


def main() -> int:
    cfg = load_yaml(ROOT / "config" / "opportunities.yaml")
    section = cfg.get("opportunities", {})
    queries = list(section.get("rss_queries", []))
    buckets = dict(section.get("type_keywords", {}))
    keep_top_n = int(section.get("keep_top_n", 20))
    max_age_days = int(section.get("max_age_days", 45))
    now = utc_now()

    keywords = []
    for words in buckets.values():
        keywords.extend(words)
    keywords.extend(["quantum", "quantum computing", "quantum technology"])

    items = fetch_items(queries)
    scored = []
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
        item["type"] = classify(text, buckets)
        item["score"] = score
        item["matched_keywords"] = matched
        item["id"] = stable_id(item["url"], item["title"])
        scored.append(item)

    scored = dedupe_by_key(sorted(scored, key=lambda x: (x["score"], x.get("published", "")), reverse=True), "url")[:keep_top_n]

    state_path = ROOT / "state" / "opportunities.json"
    write_json(
        state_path,
        {
            "generated_at": iso_utc(now),
            "items": scored,
        },
    )
    print(f"Saved {len(scored)} opportunity items to state. Rendering is handled by render_opportunity_tables.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
