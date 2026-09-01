from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from common import STATE, iso_utc, utc_now, write_json


HEADERS = {
    "User-Agent": "quantum-radar-personal/1.0 (+https://www.mtprest.com)",
}

PERSON_PATTERNS = [
    re.compile(
        r"(?P<name>[A-Z][a-z]+\s+[A-Z][a-z]+)\s*(?:,|-)?\s*(?P<title>Hiring Manager|Recruiter|Talent Acquisition|People Operations|Program Manager)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<title>Hiring Manager|Recruiter|Talent Acquisition|People Operations|Program Manager)\s*(?:,|-|:)\s*(?P<name>[A-Z][a-z]+\s+[A-Z][a-z]+)",
        re.IGNORECASE,
    ),
]


def _fetch(url: str) -> tuple[int, str]:
    try:
        resp = requests.get(url, timeout=20, headers=HEADERS)
        return resp.status_code, resp.text
    except requests.RequestException:
        return 0, ""


def _text_excerpt(soup: BeautifulSoup, limit: int = 1200) -> str:
    text = " ".join(soup.get_text(" ", strip=True).split())
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _extract_social_links(base_url: str, soup: BeautifulSoup) -> dict[str, str]:
    links: dict[str, str] = {}
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if not href:
            continue
        full = urljoin(base_url, href)
        lowered = full.lower()
        if "linkedin.com/company/" in lowered and "linkedin_company" not in links:
            links["linkedin_company"] = full
        elif "linkedin.com/in/" in lowered and "linkedin_people" not in links:
            links["linkedin_people"] = full
        elif "x.com/" in lowered and "x" not in links:
            links["x"] = full
        elif "twitter.com/" in lowered and "x" not in links:
            links["x"] = full
    return links


def _infer_first_reader(item_type: str, excerpt: str, social_links: dict[str, str]) -> dict[str, Any]:
    for pattern in PERSON_PATTERNS:
        match = pattern.search(excerpt)
        if match:
            name = " ".join(match.group("name").split())
            title = " ".join(match.group("title").split())
            return {
                "name": name,
                "title": title,
                "confidence": 0.78,
                "evidence": "Named contact extracted from opportunity/company page text.",
            }

    fallback_titles = {
        "internships": "University Recruiting Lead",
        "summer_programs": "Program Coordinator",
        "hackathons": "Community Programs Manager",
        "fellowships": "Fellowship Program Manager",
        "grants": "Program Officer",
    }
    title = fallback_titles.get(item_type, "Talent Acquisition Partner")
    confidence = 0.58 if social_links else 0.42
    evidence = (
        "Role-type heuristic with public social/company signals."
        if social_links
        else "Role-type heuristic without reliable public contact details."
    )
    return {
        "name": "Unknown",
        "title": title,
        "confidence": confidence,
        "evidence": evidence,
    }


def _social_snapshots(social_links: dict[str, str]) -> list[dict[str, Any]]:
    snapshots = []
    for key, link in list(social_links.items())[:3]:
        status_code, html = _fetch(link)
        if not html:
            snapshots.append({"source": key, "url": link, "status_code": status_code, "title": "", "summary": ""})
            continue
        soup = BeautifulSoup(html, "html.parser")
        title = (soup.title.string or "").strip() if soup.title else ""
        summary = _text_excerpt(soup, limit=240)
        snapshots.append(
            {
                "source": key,
                "url": link,
                "status_code": status_code,
                "title": title,
                "summary": summary,
            }
        )
    return snapshots


def main() -> int:
    selected_path = STATE / "personal_radar_selected.json"
    selected_payload = {
        "selected": []
    }
    if selected_path.exists():
        import json

        selected_payload = json.loads(selected_path.read_text(encoding="utf-8"))

    enriched_items = []
    for item in selected_payload.get("selected", []):
        link = (item.get("link") or "").strip()
        status_code, html = _fetch(link) if link else (0, "")
        excerpt = ""
        page_title = ""
        social_links: dict[str, str] = {}
        if html:
            soup = BeautifulSoup(html, "html.parser")
            page_title = (soup.title.string or "").strip() if soup.title else ""
            excerpt = _text_excerpt(soup)
            social_links = _extract_social_links(link, soup)

        first_reader = _infer_first_reader(item.get("type", ""), excerpt, social_links)
        social = _social_snapshots(social_links)
        domain = ""
        try:
            domain = urlparse(link).netloc
        except ValueError:
            domain = ""

        enriched_items.append(
            {
                **item,
                "enrichment": {
                    "fetched_url": link,
                    "fetched_status_code": status_code,
                    "company_domain": domain,
                    "page_title": page_title,
                    "page_excerpt": excerpt,
                    "social_links": social_links,
                    "social_snapshots": social,
                    "likely_first_reader": first_reader,
                },
            }
        )

    payload = {
        "generated_at": iso_utc(utc_now()),
        "selected_count": len(enriched_items),
        "items": enriched_items,
    }
    write_json(STATE / "personal_radar_enriched.json", payload)
    print(f"Enriched {len(enriched_items)} selected opportunities.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
