# mtp354.github.io

Personal academic website of **Matthew Prest** (PhD candidate, CUNY) — published at <https://mtp354.github.io> and <https://matthewprestnz.com>.

The site is built on the [Academic Pages](https://academicpages.github.io/) Jekyll theme (a fork of [Minimal Mistakes](https://mmistakes.github.io/minimal-mistakes/)) with a number of personal extensions: a Quantum Radar data project, a topical Resources hub, a dark-mode toggle, retro view counter, plain-language summaries on publications, BibTeX cite blocks, auto-generated OG share images, and Atom feeds for both publications and the Quantum Radar reports.

The source of truth lives in the Jekyll collections, data files, assets, and scripts tracked in this repo. Local build output (`_site/`), local virtual environments (`.venv/`), dependency folders, and cache directories are intentionally ignored and can be recreated.

---

## Repository layout

```
_config.yml                 Site-wide Jekyll configuration
Gemfile                     Ruby dependencies (bundler)
package.json                Node helper scripts for bundled site JavaScript
CNAME                       Custom domain
publications.xml            Atom feed for the publications collection
quantum-radar.xml           Atom feed for Quantum Radar reports

_data/                      Site data (authors, navigation, ui-text)
_includes/                  Liquid partials (head, masthead, footer, hero cards, ...)
_layouts/                   Page layouts (default, single, archive,
                            publication, talk, qr-report, ...)
_sass/                      SCSS sources (theme/_default.scss, theme/_dark.scss,
                            _site-extras.scss for personal overrides)
assets/css/                 Compiled CSS plus academicons
assets/js/                  dark-mode.js, theme.js, copy-bibtex.js,
                            qr-sparklines.js, qr-collapse.js, plugins, …

_pages/                     Top-level pages: about, publications, talks,
                            portfolio, resources, quantum-radar,
                            quantum-101, topics, now, 404, archives
_posts/                     Blog posts (`YYYY-MM-DD-slug.md`)
_publications/              Publication entries (one Markdown file per paper)
_talks/                     Talk entries
_resources/                 Curated learning-resource entries (Quantum 101 hub)
_quantum_radar/             Auto-generated Quantum Radar report entries
                            (opportunities with embedded jobs, conferences,
                             publications-news, quantum-industry, movers-shakers)

files/                      PDFs, BibTeX files, and class materials linked by the site
images/                     Profile image, favicons, and the web manifest
projects/quantum-radar/     Python pipeline that produces the Quantum Radar reports
projects/og-images/         Script that auto-generates Open Graph share images
Applicant/                  CV and cover-letter sources used by private automation;
                            excluded from the published Jekyll site

.github/workflows/          GitHub Actions automations
```

Generated report entries under `_quantum_radar/` and generated PNGs under
`assets/og/` are tracked because GitHub Pages serves them directly. Treat the
corresponding scripts and configs in `projects/` as the maintainable source for
future automated updates.

---

## Local development

Serving the site locally requires Ruby (with `ruby-dev`) and Bundler. Node is
only needed when rebuilding the bundled JavaScript in `assets/js/main.min.js`.

```bash
bundle install
bundle exec jekyll serve -l -H localhost
```

The site is then available at <http://localhost:4000>. See <https://academicpages.github.io/markdown/> for the upstream theme docs.

To rebuild the JavaScript bundle after editing `assets/js/_main.js` or
`assets/js/plugins/jquery.greedy-navigation.js`, install the npm dependencies
and run:

```bash
npm install
npm run build:js
```

---

## Quantum Radar data project (`projects/quantum-radar/`)

A small Python pipeline that aggregates quantum-tech opportunities,
conferences, publications/news, grant awards, stock prices, and a jobs feed
that is folded into the Opportunities report, then emits
Markdown into `_quantum_radar/` for Jekyll to render at `/quantum-radar/`. Run locally with:

```bash
cd projects/quantum-radar
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/fetch_opportunities.py
python scripts/enrich_deadlines.py
python scripts/fetch_jobs.py
python scripts/render_opportunity_tables.py
python scripts/fetch_conferences.py
python scripts/fetch_publications_news.py
python scripts/fetch_stock_prices.py
```

Configuration lives under `projects/quantum-radar/config/`. Persistent state
used for deduplication and last-seen entries is in `projects/quantum-radar/state/`.
Private personal-radar output is ignored by git.

---

## GitHub Actions

| Workflow | Trigger | Purpose |
|---|---|---|
| `quantum-radar-opportunities.yml` | every 3 days | Refresh RSS → enrich deadlines → render opportunity tables |
| `quantum-radar-jobs.yml` | daily | Refresh approved public job-feed state and fold it into the latest Opportunities report |
| `quantum-radar-conferences.yml` | every 3 days | Scrape official event metadata and aggregate conference announcements |
| `quantum-radar-publications-news.yml` | every 2 days | arXiv + Google News digest → publish to `_quantum_radar/` |
| `quantum-radar-stocks.yml` | daily, post US close | Pull yfinance closes → write publicly-traded report |
| `personal-radar-weekly.yml` | weekly / manual | Build a private opportunity digest from tracked profile inputs and append website analytics |
| `og-images.yml` | on push | Regenerate Open Graph share images |
| `scrape_talks.yml` | manual / scheduled | Scrape new talks |

GitHub Pages handles the actual site build/deploy.

---

## Authoring content

- **Blog post** — add `_posts/YYYY-MM-DD-slug.md` with the `single` layout. `difficulty` front-matter (`beginner` / `intermediate` / `advanced`) renders a colored badge.
- **Publication** — add `_publications/YYYY-MM-DD-slug.md`. Optional `plain_summary` is rendered as a callout, and a sibling `.bib` in `files/` enables the in-page BibTeX cite block.
- **Talk** — add `_talks/YYYY-MM-DD-slug.md`.
- **Resource entry** — add `_resources/<topic>.md` with the appropriate `category` front-matter; rendered through the Resources hub.
- **Navigation** — edit `_data/navigation.yml`.
- **Author/sidebar info** — edit `_data/authors.yml` and the `author:` block in `_config.yml`.
- **Generated reports** — update the relevant config or script under `projects/quantum-radar/`, then rerun the workflow or script. Hand-edit `_quantum_radar/` only for curated pages such as Movers & Shakers.

---

## Theming notes

- Light theme variables: `_sass/theme/_default.scss`
- Dark theme variables: `_sass/theme/_dark.scss`
- Personal extensions and dark-mode overrides: `_sass/_site-extras.scss`
- Toggle behaviour: `assets/js/dark-mode.js` (sets `data-theme` on `<html>`, persists to `localStorage`, respects `prefers-color-scheme`)

---

## Credits

Theme: [Academic Pages](https://github.com/academicpages/academicpages.github.io) / [Minimal Mistakes](https://github.com/mmistakes/minimal-mistakes) by Michael Rose. Licensed under the MIT License — see [LICENSE](LICENSE).
