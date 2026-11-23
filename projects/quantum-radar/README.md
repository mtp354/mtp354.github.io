# Quantum Radar

In-tree automation for `/quantum-radar/` on the website. These scripts and
configs live inside the website repo and are driven by the workflows under
`.github/workflows/quantum-radar-*.yml`.

Five public radar tracks:

1. **Opportunities digests** every three days
   (`fetch_opportunities.py` → `enrich_deadlines.py` →
   `render_opportunity_tables.py`) — open/application-based grants,
   internships, hackathons, summer schools, fellowships, and a collapsible jobs
   section. Deadlines are scraped from each program's page where possible.
   Award-announcement news is diverted into `state/awarded-grants.json`.
2. **Conferences** — curated official conference pages plus newly announced
   academic and industry events (`fetch_conferences.py`). Official pages are
   read for schema.org Event dates and locations when available.
3. **Publications & news digests** every two days
   (`fetch_publications_news.py`).
4. **Movers & Shakers** — a hand-curated list of leading quantum companies,
   influential university labs, and notable people in the field. Updated by
   editing `_quantum_radar/movers-shakers-*.md` directly.
5. **Quantum Industry** — daily public-market snapshot for listed quantum
   companies, broad quantum ETFs, captured grant-award totals, and directional
   investment/workforce estimates (`fetch_stock_prices.py`).

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
`_quantum_radar/`, which is what `_pages/quantum-radar.md` renders. Jobs are
stored in state and rendered inside the Opportunities entry rather than as a
standalone public track.

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
secret exists, the jobs workflow exits without changing the Opportunities
report.
LinkedIn does not provide a generally available job-search API; its Talent APIs
require partner approval, and automated page scraping is not used here. The
suggested alert queries are in `config/jobs.yaml` for use when provisioning the
feed. `fetch_jobs.py` writes `state/jobs.json`; `render_opportunity_tables.py`
publishes those listings in the collapsible Jobs section.

## Personal Radar

The weekly personal digest is intentionally separate from the public
`/quantum-radar/` pages. It reads the profile in `config/personal_profile.yaml`,
uses the CV and cover-letter sources listed there, writes ignored artifacts
under `state/personal_radar_*.json` and `reports/personal-radar/`, and emails
the result from GitHub Actions secrets.

The Monday email can append Google Analytics 4 website metrics when
`GA4_PROPERTY_ID` and `GA4_SERVICE_ACCOUNT_JSON` are set as repository secrets.
`GA4_PROPERTY_ID` can alternatively be a repository Actions variable. Use the
numeric ID from GA4 Admin > Property details, not the `G-...` measurement ID.
Enable the **Google Analytics Data API** in the service account's Google Cloud
project, then add its email address as a **Viewer** in GA4 Admin > Property access
management. Store the complete service-account key JSON only in the
`GA4_SERVICE_ACCOUNT_JSON` Actions secret; never commit it.

The site measurement ID (`G-979B8LMLWV`) controls browser collection separately
from the reporting API. In GA4 Admin > Data streams, check that the web stream
uses the domain in the site's `CNAME` and confirm visits in Realtime. Reporting
data may take 24–48 hours to appear.

By default the email summarizes the last seven days ending yesterday.
`python scripts/personal_send_email.py --analytics-only` writes
`reports/personal-radar/analytics.txt` without SMTP. The workflow collects this
before emailing and includes it in the private digest artifact. Missing
configuration or API failures produce an Actions warning and an explicit
unavailable message in the email, not misleading zero metrics.

SMTP uses STARTTLS on port 587 by default, or implicit TLS on port 465 when
`SMTP_PORT` is set to `465`. Connection interruptions during setup/login are
retried up to three times. Authentication failures are not retried; verify the
provider's SMTP credentials/app password if they occur. Sending is never retried
automatically, to avoid duplicate messages after an ambiguous delivery failure.

Before the workflow runs, `scripts/check_applicant_privacy.py` confirms that the
top-level `Applicant/` directory is excluded from Jekyll output and that no
generated public Quantum Radar entry links back to it.
