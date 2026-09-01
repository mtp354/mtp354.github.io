from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from common import REPORTS, ROOT, STATE, iso_utc, load_yaml, today_str, utc_now, write_json, write_text


def _strip_tex(text: str) -> str:
    text = re.sub(r"%.*", "", text)
    text = re.sub(r"\\href\{[^}]*\}\{([^}]*)\}", r"\\1", text)
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^{}]*\})?", " ", text)
    text = text.replace("{", " ").replace("}", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _load_profile_and_docs() -> tuple[dict[str, Any], str, str]:
    cfg = load_yaml(ROOT / "config" / "personal_profile.yaml")
    profile = cfg.get("personal_profile", {})
    if not isinstance(profile, dict):
        raise ValueError("personal_profile must be a mapping")
    sources = profile.get("applicant_sources", {}) if isinstance(profile.get("applicant_sources", {}), dict) else {}

    site_root = ROOT.parents[1]
    cv_chunks = []
    for rel in list(sources.get("cv_paths", [])):
        path = site_root / rel
        if path.exists() and path.is_file():
            cv_chunks.append(_strip_tex(path.read_text(encoding="utf-8", errors="ignore")))

    cl_chunks = []
    for rel in list(sources.get("cover_letter_paths", [])):
        path = site_root / rel
        if path.exists() and path.is_file():
            cl_chunks.append(_strip_tex(path.read_text(encoding="utf-8", errors="ignore")))

    return profile, "\n".join(cv_chunks), "\n".join(cl_chunks)


def _missing_keywords(opportunity_text: str, cv_text: str, weights: dict[str, Any]) -> list[str]:
    missing = []
    opp = opportunity_text.lower()
    cv = cv_text.lower()
    weighted = sorted(weights.items(), key=lambda kv: int(kv[1]), reverse=True)
    for keyword, _weight in weighted:
        lower = keyword.lower()
        if lower in opp and lower not in cv:
            missing.append(keyword)
    return missing[:6]


def _recommendations_for_item(item: dict[str, Any], cv_text: str, cl_text: str, weights: dict[str, Any]) -> dict[str, Any]:
    full_text = "\n".join(
        [
            item.get("name", ""),
            item.get("organization", ""),
            item.get("summary", ""),
            item.get("notes", ""),
            item.get("enrichment", {}).get("page_excerpt", ""),
        ]
    )
    missing = _missing_keywords(full_text, cv_text, weights)
    first_reader = item.get("enrichment", {}).get("likely_first_reader", {})
    reader_title = first_reader.get("title", "Hiring Team")
    org = item.get("organization") or "the organization"

    cv_suggestions = [
        f"Lead with 2-3 bullets aligned to {item.get('type', 'role')} outcomes and measurable impact.",
        f"Add explicit wording for: {', '.join(missing) if missing else 'quantum cryptography, distributed systems, and Python implementation'}.",
        f"Tailor one bullet to {org} needs using language from the posting page.",
    ]

    cl_suggestions = [
        f"Open with a one-sentence fit statement for {item.get('name', 'this role')} at {org}.",
        f"Include one paragraph that speaks directly to a likely first reader ({reader_title}).",
        "Close with a concrete contribution plan for the first 3-6 months.",
    ]

    tone_adjustments = [
        "Prefer concise, technical language over broad enthusiasm statements.",
        "Use one quantified achievement per paragraph where possible.",
    ]

    if "qiskit" in full_text.lower() and "qiskit" not in cv_text.lower():
        cv_suggestions.append("Add a Qiskit project bullet emphasizing implementation details and outcomes.")
    if "grant" in full_text.lower():
        cl_suggestions.append("Mention proposal-writing, research communication, and cross-team collaboration explicitly.")
    if cl_text and "quantum cryptography" in cl_text.lower():
        tone_adjustments.append("Keep the quantum cryptography narrative, but connect it to this role's specific deliverables.")

    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "organization": org,
        "link": item.get("link"),
        "score": item.get("score"),
        "fit_score_100": item.get("fit_score_100", 0),
        "likely_first_reader": first_reader,
        "missing_keywords": missing,
        "cv_suggestions": cv_suggestions,
        "cover_letter_suggestions": cl_suggestions,
        "tone_adjustments": tone_adjustments,
        "score_breakdown": item.get("score_breakdown", {}),
    }


def _render_markdown(
    profile: dict[str, Any],
    recommendations: list[dict[str, Any]],
    selection_mode: str,
    selection_note: str,
) -> str:
    date_str = today_str()
    lines = [
        f"# Personal Radar Weekly Digest - {date_str}",
        "",
        f"Generated for: {profile.get('candidate_name', 'Candidate')}",
        f"Generated at (UTC): {iso_utc(utc_now())}",
        f"Selection mode: {selection_mode}",
        f"Selection note: {selection_note}",
        "",
    ]

    if not recommendations:
        lines.extend(
            [
                "No suitable opportunities were selected this week.",
                "",
                "Recommendation: expand location and role-type constraints to improve match volume.",
            ]
        )
        return "\n".join(lines).rstrip() + "\n"

    for idx, rec in enumerate(recommendations, start=1):
        reader = rec.get("likely_first_reader", {})
        lines.extend(
            [
                f"## {idx}. {rec.get('name', 'Opportunity')} - {rec.get('organization', '')}",
                "",
                f"- Link: {rec.get('link', '')}",
                f"- Personal fit score: {rec.get('fit_score_100', 0)}/100",
                f"- Likely first CV reader: {reader.get('name', 'Unknown')} ({reader.get('title', 'Unknown')}), confidence {reader.get('confidence', 0):.2f}",
                f"- First-reader evidence: {reader.get('evidence', 'N/A')}",
                "",
                "### CV suggestions",
            ]
        )
        lines.extend([f"- {item}" for item in rec.get("cv_suggestions", [])])
        lines.append("")
        lines.append("### Cover-letter suggestions")
        lines.extend([f"- {item}" for item in rec.get("cover_letter_suggestions", [])])
        lines.append("")
        lines.append("### Tone and positioning")
        lines.extend([f"- {item}" for item in rec.get("tone_adjustments", [])])
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    profile, cv_text, cl_text = _load_profile_and_docs()

    selected_path = STATE / "personal_radar_selected.json"
    selected_payload = {}
    if selected_path.exists():
        selected_payload = json.loads(selected_path.read_text(encoding="utf-8"))

    enriched_path = STATE / "personal_radar_enriched.json"
    if not enriched_path.exists():
        payload = {"items": []}
    else:
        payload = json.loads(enriched_path.read_text(encoding="utf-8"))

    weights = profile.get("keyword_weights", {})
    recommendations = [
        _recommendations_for_item(item, cv_text, cl_text, weights)
        for item in payload.get("items", [])
    ]

    digest = {
        "generated_at": iso_utc(utc_now()),
        "candidate_name": profile.get("candidate_name", "Candidate"),
        "selection_mode": selected_payload.get("selection_mode", "unknown"),
        "selection_note": selected_payload.get("selection_note", ""),
        "recommendation_count": len(recommendations),
        "recommendations": recommendations,
    }
    write_json(STATE / "personal_radar_digest.json", digest)

    out_dir = REPORTS / "personal-radar" / today_str()
    out_dir.mkdir(parents=True, exist_ok=True)
    md = _render_markdown(
        profile,
        recommendations,
        digest.get("selection_mode", "unknown"),
        digest.get("selection_note", ""),
    )
    write_text(out_dir / "weekly-digest.md", md)
    write_json(out_dir / "weekly-digest.json", digest)
    print(f"Generated personal radar digest with {len(recommendations)} recommendations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
