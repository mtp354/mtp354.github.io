# Quantum Radar

In-tree automation for `/quantum-radar/` on the website. These scripts and
configs live inside the website repo and are driven by the workflows under
`.github/workflows/quantum-radar-*.yml`.

Four unattended jobs:

1. **Opportunities digests** every three days
   (`fetch_opportunities.py` → `enrich_deadlines.py` →
   `render_opportunity_tables.py`) — grants, internships, hackathons,
   summer schools, fellowships, with deadlines scraped from each program's
   page where possible.
2. **Publications & news digests** every two days
   (`fetch_publications_news.py`).
3. **Movers & Shakers** — a hand-curated list of leading quantum companies,
   influential university labs, and notable people in the field. Updated by
   editing `_quantum_radar/movers-shakers-*.md` directly.
4. **Publicly Traded Quantum** — daily refresh of stock prices for the main
   publicly listed quantum-primary companies and a couple of broad quantum
   ETFs (`fetch_stock_prices.py`).

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
