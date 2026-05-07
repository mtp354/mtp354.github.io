"""Generate Open-Graph share images (1200x630 PNG) for every Jekyll page,
publication, post, talk, resource, and Quantum Radar entry.

Reads YAML front-matter from each markdown / HTML file, renders a simple
branded card with title + author + date using Pillow, and writes
``assets/og/<slug>.png`` where ``<slug>`` mirrors the URL path with
slashes replaced by ``-``.

No external font dependency: uses the bundled DejaVuSans, which Pillow
ships on most platforms (including the GitHub-Actions Ubuntu runner).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "og"
OUT.mkdir(parents=True, exist_ok=True)

WIDTH, HEIGHT = 1200, 630
BG = (24, 26, 31)
ACCENT = (126, 184, 255)
TEXT = (232, 236, 242)
MUTED = (170, 178, 189)

SITE_NAME = "Matthew Prest"
SITE_TAGLINE = "Quantum Information Theory · CUNY"

FRONT_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for name in (
        "DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        if font.getlength(trial) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:4]


def _slug_from_path(p: Path, fm: dict) -> str:
    permalink = fm.get("permalink")
    if permalink:
        s = permalink.strip("/").replace("/", "-").replace(".html", "")
        return s or "index"
    rel = p.relative_to(ROOT).with_suffix("")
    return str(rel).replace("/", "-").replace("\\", "-")


def _render(slug: str, title: str, subtitle: str | None) -> None:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    d = ImageDraw.Draw(img)
    # Accent bar
    d.rectangle([(0, 0), (12, HEIGHT)], fill=ACCENT)
    # Site name top-right
    name_font = _load_font(28)
    name_w = name_font.getlength(SITE_NAME)
    d.text((WIDTH - name_w - 50, 40), SITE_NAME, font=name_font, fill=TEXT)
    tag_font = _load_font(20)
    tag_w = tag_font.getlength(SITE_TAGLINE)
    d.text((WIDTH - tag_w - 50, 78), SITE_TAGLINE, font=tag_font, fill=MUTED)
    # Title
    title_font = _load_font(64)
    lines = _wrap(title, title_font, WIDTH - 100)
    y = HEIGHT // 2 - (len(lines) * 76) // 2 - 40
    for line in lines:
        d.text((50, y), line, font=title_font, fill=TEXT)
        y += 76
    if subtitle:
        sub_font = _load_font(28)
        d.text((50, HEIGHT - 90), subtitle[:120], font=sub_font, fill=ACCENT)
    out = OUT / f"{slug}.png"
    img.save(out, format="PNG", optimize=True)
    print(f"  wrote {out.relative_to(ROOT)}")


def _parse(p: Path) -> dict | None:
    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        return None
    m = FRONT_RE.match(text)
    if not m:
        return None
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None


def main() -> int:
    targets: list[Path] = []
    for d in ("_pages", "_publications", "_posts", "_talks", "_resources", "_quantum_radar"):
        dp = ROOT / d
        if dp.is_dir():
            targets.extend(dp.glob("*.md"))
            targets.extend(dp.glob("*.html"))

    for p in targets:
        fm = _parse(p)
        if not fm:
            continue
        title = str(fm.get("title") or "").strip()
        if not title:
            continue
        slug = _slug_from_path(p, fm)
        date = fm.get("date")
        venue = fm.get("venue")
        sub = None
        if venue:
            sub = str(venue)
            if date:
                sub = f"{sub} · {date}"
        elif date:
            sub = str(date)
        _render(slug, title, sub)

    # Index page
    _render("index", SITE_NAME, SITE_TAGLINE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
