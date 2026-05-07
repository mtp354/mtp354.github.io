from __future__ import annotations

import html
import xml.etree.ElementTree as ET
from datetime import timedelta
from typing import Any

import feedparser
import requests

from common import (
    REPORTS,
    ROOT,
    dedupe_by_key,
    google_news_rss_url,
    iso_utc,
    keyword_score,
    load_yaml,
    stable_id,
    today_str,
    utc_now,
    write_json,
    write_text,
)


def fetch_arxiv(category: str, max_results: int) -> list[dict[str, Any]]:
    url = (
        "https://export.arxiv.org/api/query"
        f"?search_query=cat:{category}&start=0&max_results={max_results}"
        "&sortBy=submittedDate&sortOrder=descending"
    )
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    items = []
    for entry in root.findall("atom:entry", ns):
        title = " ".join((entry.findtext("atom:title", default="", namespaces=ns) or "").split())
        summary = " ".join((entry.findtext("atom:summary", default="", namespaces=ns) or "").split())
        link = entry.findtext("atom:id", default="", namespaces=ns) or ""
        published = entry.findtext("atom:published", default="", namespaces=ns) or ""
        authors = [
            author.findtext("atom:name", default="", namespaces=ns) or ""
            for author in entry.findall("atom:author", ns)
        ]
        items.append({
            "source": "arXiv",
            "title": html.unescape(title),
            "summary": html.unescape(summary),
            "url": link,
            "published": published,
            "authors": authors,
        })
    return items


def fetch_news(rss_queries: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for query in rss_queries:
        feed = feedparser.parse(google_news_rss_url(query))
        for entry in feed.entries:
            published = ""
            if getattr(entry, "published_parsed", None):
                import calendar
                published = iso_utc(__import__("datetime").datetime.utcfromtimestamp(calendar.timegm(entry.published_parsed)).replace(tzinfo=__import__("datetime").timezone.utc))
            items.append({
                "source": "News",
                "query": query,
                "title": entry.get("title", "").strip(),
                "summary": entry.get("summary", "").strip(),
                "url": entry.get("link", "").strip(),
                "published": published,
            })
    return items


def main() -> int:
    cfg = load_yaml(ROOT / "config" / "publications.yaml")
    keywords = list(cfg.get("keywords", []))
    arxiv_cfg = cfg.get("arxiv", {})
    news_cfg = cfg.get("news", {})

    max_age_papers = int(arxiv_cfg.get("max_age_days", 14))
    max_age_news = int(news_cfg.get("max_age_days", 10))
    keep_papers = int(arxiv_cfg.get("keep_top_n", 12))
    keep_news = int(news_cfg.get("keep_top_n", 12))

    now = utc_now()

    arxiv_items = fetch_arxiv(
        category=arxiv_cfg.get("category", "quant-ph"),
        max_results=int(arxiv_cfg.get("max_results", 80)),
    )
    scored_papers = []
    for item in arxiv_items:
        score, matched = keyword_score(
            f"{item['title']}\n{item['summary']}",
            keywords,
        )
        try:
            pub_dt = __import__("datetime").datetime.fromisoformat(item["published"].replace("Z", "+00:00"))
        except ValueError:
            continue
        age_days = (now - pub_dt).days
        if age_days > max_age_papers:
            continue
        if score <= 0:
            continue
        item["score"] = score
        item["matched_keywords"] = matched
        item["id"] = stable_id(item["url"], item["title"])
        scored_papers.append(item)

    scored_papers.sort(key=lambda x: (-x["score"], x["published"]), reverse=False)
    scored_papers = sorted(scored_papers, key=lambda x: (x["score"], x["published"]), reverse=True)
    scored_papers = dedupe_by_key(scored_papers, "url")[:keep_papers]

    news_items = fetch_news(list(news_cfg.get("rss_queries", [])))
    scored_news = []
    for item in news_items:
        score, matched = keyword_score(
            f"{item['query']}\n{item['title']}\n{item['summary']}",
            keywords,
        )
        if score <= 0:
            continue
        published = item.get("published")
        if published:
            try:
                pub_dt = __import__("datetime").datetime.fromisoformat(published.replace("Z", "+00:00"))
                age_days = (now - pub_dt).days
                if age_days > max_age_news:
                    continue
            except ValueError:
                pass
        item["score"] = score
        item["matched_keywords"] = matched
        item["id"] = stable_id(item["url"], item["title"])
        scored_news.append(item)

    scored_news = dedupe_by_key(sorted(scored_news, key=lambda x: (x["score"], x.get("published", "")), reverse=True), "url")[:keep_news]

    lines = [
        "# Quantum publications and news digest",
        "",
        f"_Generated: {now.strftime('%Y-%m-%d %H:%M UTC')}_",
        "",
        "## Publications",
        "",
    ]
    if not scored_papers:
        lines.append("No publication matches passed the current filters.")
    else:
        for i, item in enumerate(scored_papers, start=1):
            authors = ", ".join(item["authors"][:4])
            if len(item["authors"]) > 4:
                authors += ", et al."
            lines.append(f"{i}. [{item['title']}]({item['url']})")
            lines.append(f"   - Published: {item['published'][:10]}")
            if authors:
                lines.append(f"   - Authors: {authors}")
            if item.get("matched_keywords"):
                lines.append(f"   - Matched: {', '.join(item['matched_keywords'][:6])}")
            lines.append("")

    lines.extend(["## News", ""])
    if not scored_news:
        lines.append("No news matches passed the current filters.")
    else:
        for i, item in enumerate(scored_news, start=1):
            lines.append(f"{i}. [{item['title']}]({item['url']})")
            if item.get("published"):
                lines.append(f"   - Published: {item['published'][:10]}")
            lines.append(f"   - Query bucket: {item.get('query', 'n/a')}")
            if item.get("matched_keywords"):
                lines.append(f"   - Matched: {', '.join(item['matched_keywords'][:6])}")
            lines.append("")

    text = "\n".join(lines).strip() + "\n"

    latest = REPORTS / "publications-news" / "latest.md"
    dated = REPORTS / "publications-news" / today_str() / "digest.md"
    data_path = ROOT / "state" / "publications-news.json"

    write_text(latest, text)
    write_text(dated, text)
    write_json(
        data_path,
        {
            "generated_at": iso_utc(now),
            "publications": scored_papers,
            "news": scored_news,
        },
    )
    print(f"Saved {len(scored_papers)} papers and {len(scored_news)} news items.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
