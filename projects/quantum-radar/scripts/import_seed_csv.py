"""Convert `data/seed_opportunities.csv` into `data/seed_opportunities.yaml`.

Best-effort: the source spreadsheet is loosely structured (multiple
sub-tables stacked vertically, some rows hold contact emails, etc.). This
importer keeps the existing YAML as a base and only appends entries from
the CSV that are not already present (matched by link). Application
status fields in the CSV are dropped on the way in.

Run after editing the CSV:

    python scripts/import_seed_csv.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from opportunities_common import DATA_DIR, SECTION_KEYS, load_seed, save_seed

CSV_PATH = DATA_DIR / "seed_opportunities.csv"


def main() -> int:
    if not CSV_PATH.exists():
        print(f"[import] no CSV at {CSV_PATH}", file=sys.stderr)
        return 0

    seed = load_seed()
    seen_links = {
        (e.get("link") or "").strip()
        for entries in seed.values()
        for e in entries
        if e.get("link")
    }

    section = "internships"
    added = 0
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            cells = [(c or "").strip() for c in row]
            if not any(cells):
                continue
            head = cells[0].lower() if cells else ""

            # Section markers
            if head.startswith("doe grant") or "grant" in head:
                section = "grants"
                continue
            if head == "summer school":
                section = "summer_programs"
                continue
            if head in {"company name", "quantum"}:
                continue  # header rows

            # Skip personal contact lines (emails)
            if "@" in cells[0] and "http" not in cells[0]:
                continue

            link = ""
            for c in cells:
                if c.startswith("http"):
                    link = c
                    break
            if not link or link in seen_links:
                continue

            name = cells[1] if len(cells) > 1 and cells[1] else cells[0] or "(untitled)"
            organization = cells[0] if cells[0] and not cells[0].startswith("http") else ""
            entry = {
                "name": name,
                "organization": organization,
                "type": section,
                "deadline": None,
                "link": link,
                "notes": "imported from CSV",
            }
            seed.setdefault(section, []).append(entry)
            seen_links.add(link)
            added += 1

    if added:
        # Ensure all section keys exist before saving.
        for key in SECTION_KEYS:
            seed.setdefault(key, [])
        save_seed(seed)
    print(f"[import] added {added} new entries from CSV.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
