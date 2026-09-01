# Quantum Radar

In-tree automation for `/quantum-radar/` on the website. These scripts and
configs live inside the website repo and are driven by the workflows under
`.github/workflows/quantum-radar-*.yml`.

Six radar tracks:

1. **Opportunities digests** every three days
   (`fetch_opportunities.py` → `enrich_deadlines.py` →
   `render_opportunity_tables.py`) — open/application-based grants, internships, hackathons,
   summer schools, fellowships, with deadlines scraped from each program's
   page where possible. Award-announcement news is diverted into
   `state/awarded-grants.json`.
2. **Publications & news digests** every two days
   (`fetch_publications_news.py`).
3. **Movers & Shakers** — a hand-curated list of leading quantum companies,
   influential university labs, and notable people in the field. Updated by
   editing `_quantum_radar/movers-shakers-*.md` directly.
4. **Quantum Industry** — daily public-market snapshot for listed quantum
   companies, broad quantum ETFs, captured grant-award totals, and directional
   investment/workforce estimates (`fetch_stock_prices.py`).
5. **Conferences** — curated official conference pages plus newly announced
   academic and industry events (`fetch_conferences.py`). Official pages are
   read for schema.org Event dates and locations when available.
6. **Quantum Jobs** — public LinkedIn job URLs ingested from an approved
   RSS/Atom feed (`fetch_jobs.py`). The workflow does not scrape LinkedIn.

## Layout

```text
projects/quantum-radar/
├── config/        # YAML configs for each job
├── data/          # Curated seed lists (e.g., seed_opportunities.yaml)
├── reports/       # Raw markdown output written by the fetchers
├── scripts/       # Python entry points called by the workflows
└── state/         # Lightweight JSON dedupe state
```

The fetchers publish Jekyll-friendly entries into the site collection at
`_quantum_radar/`, which is what `_pages/quantum-radar.md` renders.

## Updating opportunities

`data/seed_opportunities.yaml` is the curated source of truth for
opportunities. To refresh it from a spreadsheet export, drop the CSV at
`data/seed_opportunities.csv` and run:

```bash
python scripts/import_seed_csv.py
```

The workflow merges these seed entries with freshly scraped items each
time it runs.

Scraped grant opportunities come from the official Grants.gov API and must be
posted, not closed, and open to individuals, higher-education institutions, or
nonprofits. Curated grants can still be added to `data/seed_opportunities.yaml`.
Headlines about funding already awarded are catalogued separately and summed by
currency in the next Quantum Industry report. No exchange-rate conversion is
applied.

## LinkedIn jobs feed

Add a repository Actions secret named `LINKEDIN_JOBS_FEED_URL` containing the
URL of an RSS or Atom job feed that you are authorized to consume. Multiple
feed URLs can be newline- or comma-separated in the same secret. Until that
secret exists, the jobs workflow exits without publishing an empty report.
LinkedIn does not provide a generally available job-search API; its Talent APIs
require partner approval, and automated page scraping is not used here. The
suggested alert queries are in `config/jobs.yaml` for use when provisioning the
feed.
