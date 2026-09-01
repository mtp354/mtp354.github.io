from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from common import ROOT, STATE, iso_utc, load_yaml, read_json, stable_id, utc_now, write_json
from opportunities_common import SECTION_KEYS, is_open, load_seed


RSS_TYPE_MAP = {
    "internships": "internships",
    "grants": "grants",
    "summer_programs": "summer_programs",
    "hackathons": "hackathons",
    "fellowships": "fellowships",
}


def _emit_gha_output(name: str, value: str) -> None:
    raw_output_path = os.environ.get("GITHUB_OUTPUT")
    if not raw_output_path:
        return
    output_path = Path(raw_output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as f:
        f.write(f"{name}={value}\n")


def _load_profile() -> dict[str, Any]:
    cfg = load_yaml(ROOT / "config" / "personal_profile.yaml")
    profile = cfg.get("personal_profile", {})
    if not isinstance(profile, dict):
        raise ValueError("personal_profile must be a mapping")
    return profile


def _strip_tex(text: str) -> str:
    text = re.sub(r"%.*", "", text)
    text = re.sub(r"\\href\{[^}]*\}\{([^}]*)\}", r"\\1", text)
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^{}]*\})?", " ", text)
    text = text.replace("{", " ").replace("}", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _load_applicant_text(profile: dict[str, Any], site_root: Path) -> str:
    sources = profile.get("applicant_sources", {})
    cv_paths = list(sources.get("cv_paths", [])) if isinstance(sources, dict) else []
    cl_paths = list(sources.get("cover_letter_paths", [])) if isinstance(sources, dict) else []
    chunks: list[str] = []
    for rel in [*cv_paths, *cl_paths]:
        path = site_root / rel
        if not path.exists() or not path.is_file():
            continue
        chunks.append(_strip_tex(path.read_text(encoding="utf-8", errors="ignore")))
    return "\n".join(chunks)


def _parse_iso_day(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        return datetime.fromisoformat(text[:10]).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _load_opportunities() -> list[dict[str, Any]]:
    seed = load_seed()
    seed_items: list[dict[str, Any]] = []
    for section in SECTION_KEYS:
        for entry in seed.get(section, []):
            seed_items.append(
                {
                    "id": stable_id("seed", entry.get("link", ""), entry.get("name", "")),
                    "name": (entry.get("name") or "").strip(),
                    "organization": (entry.get("organization") or "").strip(),
                    "location": (entry.get("location") or "").strip(),
                    "type": section,
                    "deadline": entry.get("deadline"),
                    "link": (entry.get("link") or "").strip(),
                    "notes": (entry.get("notes") or "").strip(),
                    "summary": (entry.get("notes") or "").strip(),
                    "source": "seed",
                }
            )

    state_items = read_json(STATE / "opportunities.json", {"items": []}).get("items", [])
    rss_items: list[dict[str, Any]] = []
    for item in state_items:
        bucket = RSS_TYPE_MAP.get(item.get("type", ""))
        if not bucket:
            continue
        title = (item.get("title") or "").strip()
        organization = (item.get("organization") or "").strip()
        if " - " in title and not organization:
            head, _, tail = title.rpartition(" - ")
            if head and tail:
                title = head
                organization = tail
        rss_items.append(
            {
                "id": item.get("id") or stable_id(item.get("url", ""), title),
                "name": title,
                "organization": organization,
                "location": "",
                "type": bucket,
                "deadline": item.get("deadline"),
                "link": (item.get("url") or "").strip(),
                "notes": "",
                "summary": (item.get("summary") or "").strip(),
                "source": item.get("application_source") or "rss",
                "published": item.get("published", ""),
            }
        )

    merged = [*seed_items, *rss_items]
    unique: dict[str, dict[str, Any]] = {}
    for row in merged:
        key = row.get("link") or f"{row.get('name', '')}|{row.get('organization', '')}"
        if not key:
            key = row["id"]
        existing = unique.get(key)
        if existing and existing.get("source") == "seed":
            continue
        unique[key] = row
    return list(unique.values())


def _time_gate(profile: dict[str, Any], now_utc: datetime) -> bool:
    tz_name = str(profile.get("target_time_zone", "America/New_York"))
    target_weekday = int(profile.get("target_run_weekday", 0))
    target_hour = int(profile.get("target_run_hour", 8))
    local_now = now_utc.astimezone(ZoneInfo(tz_name))
    return local_now.weekday() == target_weekday and local_now.hour == target_hour


def _location_score(location_text: str, preferred_locations: list[str]) -> int:
    if not location_text:
        return 1
    lowered = location_text.lower()
    for term in preferred_locations:
        if term.lower() in lowered:
            return 4
    return 0


def _source_score(source: str) -> int:
    lowered = (source or "").lower()
    if lowered == "seed":
        return 4
    if "grants.gov" in lowered:
        return 5
    if lowered == "rss":
        return 2
    return 1


def _urgency_score(deadline_iso: str | None, now: datetime) -> tuple[int, int | None]:
    if not deadline_iso:
        return 2, None
    deadline = _parse_iso_day(deadline_iso)
    if not deadline:
        return 1, None
    days_left = (deadline.date() - now.date()).days
    if days_left < 0:
        return -50, days_left
    if days_left <= 7:
        return 10, days_left
    if days_left <= 21:
        return 7, days_left
    if days_left <= 45:
        return 4, days_left
    return 1, days_left


def _score_item(
    item: dict[str, Any],
    profile: dict[str, Any],
    applicant_text: str,
    now: datetime,
    previous_ids: set[str],
) -> dict[str, Any]:
    keyword_weights = profile.get("keyword_weights", {})
    role_weights = profile.get("preferred_role_types", {})
    preferred_locations = list(profile.get("preferred_locations", []))
    disqualify_keywords = list(profile.get("disqualify_keywords", []))

    full_text = "\n".join(
        [
            item.get("name", ""),
            item.get("organization", ""),
            item.get("location", ""),
            item.get("summary", ""),
            item.get("notes", ""),
            item.get("type", ""),
        ]
    ).lower()

    matched_keywords = []
    keyword_points = 0
    for kw, weight in keyword_weights.items():
        if kw.lower() in full_text:
            matched_keywords.append(kw)
            keyword_points += int(weight)

    role_points = int(role_weights.get(item.get("type", ""), 0))
    location_points = _location_score(item.get("location", ""), preferred_locations)
    source_points = _source_score(item.get("source", ""))
    urgency_points, days_left = _urgency_score(item.get("deadline"), now)
    novelty_points = 0 if item.get("id") in previous_ids else 2

    applicant_alignment_points = 0
    if applicant_text:
        for kw in matched_keywords:
            if kw.lower() in applicant_text.lower():
                applicant_alignment_points += 1

    disqualify_hits = [kw for kw in disqualify_keywords if kw.lower() in full_text]
    disqualify_penalty = -100 if disqualify_hits else 0

    open_flag = is_open(item.get("deadline"))
    open_penalty = 0 if open_flag else -25

    total = (
        keyword_points
        + role_points
        + location_points
        + source_points
        + urgency_points
        + novelty_points
        + applicant_alignment_points
        + disqualify_penalty
        + open_penalty
    )

    host = ""
    try:
        host = urlparse(item.get("link", "")).netloc
    except ValueError:
        host = ""

    return {
        **item,
        "score": total,
        "days_left": days_left,
        "matched_keywords": matched_keywords,
        "domain": host,
        "score_breakdown": {
            "keyword_points": keyword_points,
            "role_points": role_points,
            "location_points": location_points,
            "source_points": source_points,
            "urgency_points": urgency_points,
            "novelty_points": novelty_points,
            "applicant_alignment_points": applicant_alignment_points,
            "open_penalty": open_penalty,
            "disqualify_penalty": disqualify_penalty,
            "disqualify_hits": disqualify_hits,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--enforce-time-gate", action="store_true")
    parser.add_argument("--event-name", default="")
    args = parser.parse_args(argv)

    profile = _load_profile()
    now = utc_now()

    gate_applies = args.enforce_time_gate and args.event_name != "workflow_dispatch"
    if gate_applies and not _time_gate(profile, now):
        payload = {
            "generated_at": iso_utc(now),
            "skipped": True,
            "reason": "outside target Monday 08:00 local window",
            "selected": [],
        }
        write_json(STATE / "personal_radar_selected.json", payload)
        _emit_gha_output("run_pipeline", "false")
        _emit_gha_output("selected_count", "0")
        print("Skipping personal radar run: outside local execution window.")
        return 0

    site_root = ROOT.parents[1]
    applicant_text = _load_applicant_text(profile, site_root)
    opportunities = _load_opportunities()
    prior = read_json(STATE / "personal_radar_selected.json", {"selected": []})
    previous_ids = {row.get("id") for row in prior.get("selected", []) if row.get("id")}

    scored = [
        _score_item(item, profile, applicant_text, now, previous_ids)
        for item in opportunities
    ]
    scored = [row for row in scored if row.get("score", 0) > 0]
    scored.sort(
        key=lambda row: (
            row.get("score", 0),
            -9999 if row.get("days_left") is None else -row.get("days_left"),
            row.get("name", ""),
        ),
        reverse=True,
    )

    top_n = int(profile.get("top_n", 2))
    selected = scored[:top_n]
    payload = {
        "generated_at": iso_utc(now),
        "profile": {
            "candidate_name": profile.get("candidate_name", "Candidate"),
            "target_time_zone": profile.get("target_time_zone", "America/New_York"),
            "top_n": top_n,
        },
        "selected_count": len(selected),
        "selected": selected,
    }
    write_json(STATE / "personal_radar_selected.json", payload)

    _emit_gha_output("run_pipeline", "true")
    _emit_gha_output("selected_count", str(len(selected)))
    print(f"Selected {len(selected)} opportunities for personal radar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
