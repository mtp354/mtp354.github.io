from __future__ import annotations

import json
import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any

from common import STATE

GA4_ANALYTICS_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"


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
        f"Selection mode: {digest.get('selection_mode', 'unknown')}",
        f"Selection note: {digest.get('selection_note', '')}",
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
                f"   Fit score: {rec.get('fit_score_100', 0)}/100",
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


def _analytics_days() -> int:
    raw = os.getenv("GA4_ANALYTICS_DAYS", "7").strip()
    try:
        days = int(raw)
    except ValueError:
        return 7
    return min(max(days, 1), 90)


def _format_count(value: str) -> str:
    try:
        return f"{int(float(value)):,}"
    except (TypeError, ValueError):
        return value or "0"


def _format_seconds(value: str) -> str:
    try:
        total_seconds = int(round(float(value)))
    except (TypeError, ValueError):
        return value or "0s"
    minutes, seconds = divmod(total_seconds, 60)
    if minutes == 0:
        return f"{seconds}s"
    hours, minutes = divmod(minutes, 60)
    if hours == 0:
        return f"{minutes}m {seconds:02d}s"
    return f"{hours}h {minutes:02d}m"


def _metric(row: dict[str, Any], index: int) -> str:
    values = row.get("metricValues", [])
    if index >= len(values):
        return "0"
    return values[index].get("value", "0")


def _dimension(row: dict[str, Any], index: int) -> str:
    values = row.get("dimensionValues", [])
    if index >= len(values):
        return ""
    return values[index].get("value", "")


def _ga4_session(credentials_json: str) -> tuple[Any | None, str]:
    try:
        from google.auth.transport.requests import AuthorizedSession
        from google.oauth2 import service_account
    except ImportError:
        return None, "google-auth is not installed; run `pip install -r requirements.txt`."

    try:
        service_account_info = json.loads(credentials_json)
    except json.JSONDecodeError as exc:
        return None, f"GA4_SERVICE_ACCOUNT_JSON is not valid JSON: {exc}"

    try:
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=[GA4_ANALYTICS_SCOPE],
        )
    except (KeyError, ValueError) as exc:
        return None, f"GA4 service-account credentials could not be loaded: {exc}"
    return AuthorizedSession(credentials), ""


def _ga4_property_id(raw: str) -> str:
    value = raw.strip()
    return value.removeprefix("properties/")


def _run_ga4_report(session: Any, property_id: str, body: dict[str, Any]) -> dict[str, Any]:
    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
    response = session.post(url, json=body, timeout=30)
    response.raise_for_status()
    return response.json()


def _build_analytics_section() -> str:
    property_id = _ga4_property_id(os.getenv("GA4_PROPERTY_ID", ""))
    credentials_json = os.getenv("GA4_SERVICE_ACCOUNT_JSON", "").strip()
    if not property_id or not credentials_json:
        return (
            "Website Analytics\n"
            "Not configured. Add GA4_PROPERTY_ID and GA4_SERVICE_ACCOUNT_JSON "
            "repository secrets to include Google Analytics metrics."
        )

    days = _analytics_days()
    session, error = _ga4_session(credentials_json)
    if error:
        return f"Website Analytics\nCould not fetch GA4 metrics: {error}"

    date_range = {"startDate": f"{days}daysAgo", "endDate": "yesterday"}
    try:
        totals = _run_ga4_report(
            session,
            property_id,
            {
                "dateRanges": [date_range],
                "metrics": [
                    {"name": "activeUsers"},
                    {"name": "sessions"},
                    {"name": "screenPageViews"},
                    {"name": "engagedSessions"},
                    {"name": "averageSessionDuration"},
                ],
            },
        )
        top_pages = _run_ga4_report(
            session,
            property_id,
            {
                "dateRanges": [date_range],
                "dimensions": [{"name": "pagePath"}],
                "metrics": [{"name": "screenPageViews"}],
                "orderBys": [{"metric": {"metricName": "screenPageViews"}, "desc": True}],
                "limit": 5,
            },
        )
    except Exception as exc:  # pragma: no cover - depends on the remote GA4 API.
        return f"Website Analytics\nCould not fetch GA4 metrics: {exc}"

    total_row = (totals.get("rows") or [{}])[0]
    lines = [
        f"Website Analytics (last {days} days, ending yesterday)",
        f"Active users: {_format_count(_metric(total_row, 0))}",
        f"Sessions: {_format_count(_metric(total_row, 1))}",
        f"Page views: {_format_count(_metric(total_row, 2))}",
        f"Engaged sessions: {_format_count(_metric(total_row, 3))}",
        f"Avg. session duration: {_format_seconds(_metric(total_row, 4))}",
        "",
        "Top pages by views:",
    ]

    rows = top_pages.get("rows", [])
    if not rows:
        lines.append("- No page data returned.")
    for row in rows[:5]:
        page = _dimension(row, 0) or "/"
        lines.append(f"- {page}: {_format_count(_metric(row, 0))} views")
    return "\n".join(lines)


def _append_section(body: str, section: str) -> str:
    return f"{body.rstrip()}\n\n{section.rstrip()}\n"


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
    text_body = _append_section(_build_text_body(digest), _build_analytics_section())
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
