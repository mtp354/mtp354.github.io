from __future__ import annotations

import json
import os

import requests

from common import STATE


SENDGRID_ENDPOINT = "https://api.sendgrid.com/v3/mail/send"


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def _load_digest() -> dict:
    path = STATE / "personal_radar_digest.json"
    if not path.exists():
        raise SystemExit("Missing digest file: state/personal_radar_digest.json")
    return json.loads(path.read_text(encoding="utf-8"))


def _build_text_body(digest: dict) -> str:
    lines = [
        f"Personal Radar Weekly Digest for {digest.get('candidate_name', 'Candidate')}",
        f"Generated at: {digest.get('generated_at', '')}",
        "",
    ]
    recs = digest.get("recommendations", [])
    if not recs:
        lines.append("No suitable opportunities were selected this week.")
        return "\n".join(lines)

    for idx, rec in enumerate(recs, start=1):
        reader = rec.get("likely_first_reader", {})
        lines.extend(
            [
                f"{idx}. {rec.get('name', 'Opportunity')} - {rec.get('organization', '')}",
                f"   Link: {rec.get('link', '')}",
                f"   Fit score: {rec.get('score', 0)}",
                f"   Likely first reader: {reader.get('name', 'Unknown')} ({reader.get('title', 'Unknown')})",
                "   CV suggestions:",
            ]
        )
        for item in rec.get("cv_suggestions", [])[:3]:
            lines.append(f"   - {item}")
        lines.append("   Cover letter suggestions:")
        for item in rec.get("cover_letter_suggestions", [])[:3]:
            lines.append(f"   - {item}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _build_html_body(text_body: str) -> str:
    escaped = (
        text_body.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return f"<pre style=\"font-family:Arial,sans-serif;white-space:pre-wrap\">{escaped}</pre>"


def main() -> int:
    sendgrid_api_key = _required_env("SENDGRID_API_KEY")
    to_email = _required_env("PERSONAL_REPORT_TO_EMAIL")
    from_email = _required_env("PERSONAL_REPORT_FROM_EMAIL")
    reply_to = os.getenv("PERSONAL_REPORT_REPLY_TO", "").strip()
    subject_prefix = os.getenv("PERSONAL_REPORT_SUBJECT_PREFIX", "Personal Radar")

    digest = _load_digest()
    subject = f"{subject_prefix}: top {digest.get('recommendation_count', 0)} matches"
    text_body = _build_text_body(digest)
    html_body = _build_html_body(text_body)

    payload = {
        "personalizations": [
            {
                "to": [{"email": to_email}],
                "subject": subject,
            }
        ],
        "from": {"email": from_email},
        "content": [
            {"type": "text/plain", "value": text_body},
            {"type": "text/html", "value": html_body},
        ],
    }
    if reply_to:
        payload["reply_to"] = {"email": reply_to}

    response = requests.post(
        SENDGRID_ENDPOINT,
        headers={
            "Authorization": f"Bearer {sendgrid_api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=20,
    )
    if response.status_code >= 300:
        raise SystemExit(f"SendGrid request failed ({response.status_code}): {response.text}")

    print("Personal radar email sent successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
