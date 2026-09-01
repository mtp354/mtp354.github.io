from __future__ import annotations

import json
import os
import smtplib
import ssl
from email.message import EmailMessage

from common import STATE


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


def _smtp_port() -> int:
    raw = os.getenv("SMTP_PORT", "587").strip()
    try:
        return int(raw)
    except ValueError as exc:
        raise SystemExit(f"Invalid SMTP_PORT value: {raw}") from exc


def main() -> int:
    smtp_host = _required_env("SMTP_HOST")
    smtp_port = _smtp_port()
    smtp_username = _required_env("SMTP_USERNAME")
    smtp_password = _required_env("SMTP_PASSWORD")
    to_email = _required_env("PERSONAL_REPORT_TO_EMAIL")
    from_email = _required_env("PERSONAL_REPORT_FROM_EMAIL")
    reply_to = os.getenv("PERSONAL_REPORT_REPLY_TO", "").strip()
    subject_prefix = os.getenv("PERSONAL_REPORT_SUBJECT_PREFIX", "Personal Radar")

    digest = _load_digest()
    subject = f"{subject_prefix}: top {digest.get('recommendation_count', 0)} matches"
    text_body = _build_text_body(digest)
    html_body = _build_html_body(text_body)

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_email
    message["To"] = to_email
    if reply_to:
        message["Reply-To"] = reply_to
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
        smtp.starttls(context=context)
        smtp.login(smtp_username, smtp_password)
        smtp.send_message(message)

    print("Personal radar email sent successfully via SMTP.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
