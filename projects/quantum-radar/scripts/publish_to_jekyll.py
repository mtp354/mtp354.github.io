"""Wrap the latest digest reports into Jekyll-friendly entries.

This is invoked by each GitHub Actions workflow after the corresponding
fetcher script writes a fresh digest under ``projects/quantum-radar/reports/``.
It writes a sibling Markdown file under ``_quantum_radar/`` (a Jekyll
collection at the site root) with the YAML front matter Jekyll needs.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys
from pathlib import Path

# Resolve the site root regardless of where the workflow invokes us from.
# scripts/ -> projects/quantum-radar -> projects -> <site root>
SITE_ROOT = Path(__file__).resolve().parents[3]
REPORTS_DIR = SITE_ROOT / "projects" / "quantum-radar" / "reports"
COLLECTION_DIR = SITE_ROOT / "_quantum_radar"


REPORT_TYPES = {
    "publications-news": {
        "title": "Publications & news",
        "description": "Quantum publications and news digest.",
        "filename": "digest.md",
    },
    # Note: "opportunities" is intentionally NOT listed here. The opportunities
    # report is rendered as tables by `render_opportunity_tables.py`, which
    # writes its own collection entry directly.
}


def _today() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")


def _strip_top_h1(body: str) -> str:
    """Remove the first markdown H1 (the digest's own title) so the page
    can use the Jekyll front-matter title without duplication."""
    lines = body.splitlines()
    out: list[str] = []
    skipped = False
    for line in lines:
        if not skipped and line.startswith("# "):
            skipped = True
            continue
        out.append(line)
    return "\n".join(out).lstrip("\n")


def publish(report_type: str) -> Path | None:
    cfg = REPORT_TYPES[report_type]
    date = _today()
    src = REPORTS_DIR / report_type / date / cfg["filename"]
    if not src.exists():
        # Fall back to whatever "latest.md" points to.
        latest = REPORTS_DIR / report_type / "latest.md"
        if not latest.exists():
            print(f"[publish] no report found for {report_type}", file=sys.stderr)
            return None
        src = latest

    body = src.read_text(encoding="utf-8")
    body = _strip_top_h1(body)

    title = f"{cfg['title']} — {date}"
    slug = f"{report_type}-{date}"
    out_path = COLLECTION_DIR / f"{slug}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    front_matter = (
        "---\n"
        f'title: "{title}"\n'
        f"date: {date}\n"
        f"report_type: {report_type}\n"
        f'excerpt: "{cfg["description"]}"\n'
        "tags:\n"
        f"  - {report_type}\n"
        "  - quantum-radar\n"
        "---\n\n"
    )
    out_path.write_text(front_matter + body, encoding="utf-8")
    print(f"[publish] wrote {out_path.relative_to(SITE_ROOT)}")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "report_type",
        nargs="?",
        choices=sorted(REPORT_TYPES),
        help="Which report type to publish. Omit to publish all.",
    )
    args = parser.parse_args()

    targets = [args.report_type] if args.report_type else list(REPORT_TYPES)
    any_written = False
    for rt in targets:
        if publish(rt) is not None:
            any_written = True
    return 0 if any_written else 0  # do not fail the workflow on missing data


if __name__ == "__main__":
    raise SystemExit(main())
