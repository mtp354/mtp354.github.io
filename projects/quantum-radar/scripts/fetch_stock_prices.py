"""Fetch a daily Quantum Industry snapshot.

The report covers public-market quantum companies, a couple of broad quantum
ETFs, and a compact investment/workforce estimate block, then writes a
Jekyll-friendly entry to ``_quantum_radar/`` for `_pages/quantum-radar.md` to
pick up.

Companies are chosen by being *primarily* quantum (i.e., the entire
business is quantum hardware, software, or quantum-enabled products). It
deliberately excludes diversified mega-caps like Google, IBM, Microsoft,
and Amazon — they have quantum divisions, but tracking their stock price
is not a meaningful proxy for the public-market quantum sector.
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any

SITE_ROOT = Path(__file__).resolve().parents[3]
COLLECTION_DIR = SITE_ROOT / "_quantum_radar"
AWARDED_GRANTS_STATE = SITE_ROOT / "projects" / "quantum-radar" / "state" / "awarded-grants.json"

# (ticker, company name, hq, focus, kind)
TICKERS: list[tuple[str, str, str, str, str]] = [
    ("IONQ",  "IonQ",                          "College Park, MD, USA",   "Trapped-ion quantum computers",       "company"),
    ("RGTI",  "Rigetti Computing",             "Berkeley, CA, USA",       "Superconducting quantum hardware",    "company"),
    ("QBTS",  "D-Wave Quantum",                "Burnaby, BC, Canada",     "Quantum annealing",                   "company"),
    ("QUBT",  "Quantum Computing Inc. (QCI)",  "Hoboken, NJ, USA",        "Photonic / entropy quantum systems",  "company"),
    ("QNT",   "Quantinuum",                    "Broomfield, CO, USA",     "Trapped-ion full-stack systems",      "company"),
    ("INFQ",  "Infleqtion",                    "Louisville, CO, USA",     "Neutral-atom computing and sensing",  "company"),
    ("XNDU",  "Xanadu",                        "Toronto, ON, Canada",     "Photonic quantum computers",          "company"),
    ("IQMX",  "IQM Quantum Computers",         "Espoo, Finland",          "Superconducting quantum computers",   "company"),
    ("ARQQ",  "Arqit Quantum",                 "London, UK",              "Symmetric quantum-safe encryption",   "company"),
    ("QSI",   "Quantum-Si",                    "Branford, CT, USA",       "Quantum-enabled protein sequencing",  "company"),
    ("LAES",  "SEALSQ",                        "Geneva, Switzerland",     "Post-quantum secure semiconductors",  "company"),
    ("QTUM",  "Defiance Quantum ETF",          "USA",                     "Broad quantum-computing ETF",         "etf"),
]

PUBLIC_INVESTMENT_COMMITMENTS_USD = 56_700_000_000
STARTUP_INVESTMENT_2025_TOTAL_USD = 12_600_000_000
STARTUP_INVESTMENT_2025_PRIVATE_USD = 12_300_000_000
STARTUP_INVESTMENT_2025_PUBLIC_USD = 300_000_000
PRIVATE_VC_2025_QEDC_USD = 4_900_000_000

WORKFORCE_TOTAL = 16_500
WORKFORCE_TECH_PHD = 5_600
WORKFORCE_TECH_NO_PHD = 9_400
WORKFORCE_NON_TECH = WORKFORCE_TOTAL - WORKFORCE_TECH_PHD - WORKFORCE_TECH_NO_PHD

DIVERSIFIED_QUANTUM_PROGRAMS = [
    {
        "program": "IBM Quantum (IBM)",
        "workforce": (600, 1_100),
        "annual_company_spend": (2_000_000_000, 2_500_000_000),
        "public_support": (1_000_000_000, 1_000_000_000),
        "basis": "IBM disclosed more than $10B over five years for quantum; NIST announced $1B in planned IBM foundry support.",
    },
    {
        "program": "Google Quantum AI (Alphabet)",
        "workforce": (300, 700),
        "annual_company_spend": (150_000_000, 500_000_000),
        "public_support": None,
        "basis": "Hardware, theory, cloud, neutral-atom expansion, Atlantic Quantum acquisition, plus $60M+ in named external commitments.",
    },
    {
        "program": "Microsoft Quantum / Azure Quantum",
        "workforce": (300, 700),
        "annual_company_spend": (150_000_000, 500_000_000),
        "public_support": None,
        "basis": "Two-decade hardware/software program, largest quantum site in Denmark, Azure Quantum, and topological-qubit roadmap.",
    },
    {
        "program": "AWS Braket / AWS Center for Quantum Computing",
        "workforce": (150, 400),
        "annual_company_spend": (75_000_000, 250_000_000),
        "public_support": None,
        "basis": "Amazon Braket, Quantum Solutions Lab, Caltech hardware center, and partner-hardware cloud access.",
    },
    {
        "program": "Intel Quantum / Intel Labs",
        "workforce": (75, 250),
        "annual_company_spend": (50_000_000, 200_000_000),
        "public_support": None,
        "basis": "Silicon spin-qubit hardware, Tunnel Falls chips, quantum SDK, and full-stack commercial-system roadmap.",
    },
    {
        "program": "NVIDIA quantum platform / NVAQC",
        "workforce": (100, 300),
        "annual_company_spend": (75_000_000, 250_000_000),
        "public_support": None,
        "basis": "CUDA-Q, cuQuantum, NVQLink, Quantum Cloud, and NVAQC research center with dedicated Blackwell GPU infrastructure.",
    },
    {
        "program": "GlobalFoundries quantum foundry work",
        "workforce": (50, 150),
        "annual_company_spend": (50_000_000, 200_000_000),
        "public_support": (375_000_000, 375_000_000),
        "basis": "Diversified semiconductor supplier; NIST announced $375M in planned quantum-foundry support.",
    },
]


def _today() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")


def _load_yfinance() -> Any:
    try:
        import yfinance as yf  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: yfinance. Install project requirements with "
            "`pip install -r projects/quantum-radar/requirements.txt`."
        ) from exc
    return yf


def _fetch_market_cap(ticker_obj: Any) -> float | None:
    """Return latest yfinance market cap metadata when available."""
    try:
        fast_info = getattr(ticker_obj, "fast_info", None)
        if fast_info:
            market_cap = fast_info.get("market_cap")
            if market_cap:
                return float(market_cap)
    except Exception:  # noqa: BLE001
        pass

    try:
        market_cap = ticker_obj.info.get("marketCap")
        if market_cap:
            return float(market_cap)
    except Exception:  # noqa: BLE001
        pass

    return None


def _fetch_one(ticker: str) -> tuple[float | None, float | None, list[float], float | None]:
    """Return (last_price, change_pct_vs_prev_close, last_30d_closes, market_cap)."""
    yf = _load_yfinance()
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="2mo", interval="1d", auto_adjust=False)
        if hist is None or hist.empty:
            return None, None, [], _fetch_market_cap(t)
        closes = hist["Close"].dropna()
        if closes.empty:
            return None, None, [], _fetch_market_cap(t)
        last = float(closes.iloc[-1])
        if len(closes) >= 2:
            prev = float(closes.iloc[-2])
            pct = (last - prev) / prev * 100.0 if prev else None
        else:
            pct = None
        spark = [round(float(x), 4) for x in closes.tail(30).tolist()]
        return last, pct, spark, _fetch_market_cap(t)
    except Exception as e:  # noqa: BLE001
        print(f"  ! {ticker}: {e}", file=sys.stderr)
        return None, None, [], None


def _fmt_price(p: float | None) -> str:
    return f"${p:,.2f}" if p is not None else "—"


def _fmt_pct(p: float | None) -> str:
    if p is None:
        return "—"
    sign = "+" if p >= 0 else ""
    return f"{sign}{p:.2f}%"


def _fmt_money(m: float | None) -> str:
    if m is None:
        return "—"
    amount = float(m)
    abs_amount = abs(amount)
    if abs_amount >= 1_000_000_000_000:
        return f"${amount / 1_000_000_000_000:,.2f}T"
    if abs_amount >= 1_000_000_000:
        return f"${amount / 1_000_000_000:,.2f}B"
    if abs_amount >= 1_000_000:
        return f"${amount / 1_000_000:,.1f}M"
    return f"${amount:,.0f}"


def _fmt_count_range(values: tuple[int, int]) -> str:
    low, high = values
    if low == high:
        return f"~{low:,}"
    return f"~{low:,}-{high:,}"


def _fmt_money_range(values: tuple[int, int] | None, suffix: str = "") -> str:
    if values is None:
        return "—"
    low, high = values
    if low == high:
        return f"{_fmt_money(low)}{suffix}"
    return f"{_fmt_money(low)}-{_fmt_money(high)}{suffix}"


def _load_awarded_grants() -> list[dict]:
    if not AWARDED_GRANTS_STATE.exists():
        return []
    try:
        data = json.loads(AWARDED_GRANTS_STATE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return data.get("items", []) or []


def _fmt_currency(amount: int, currency: str) -> str:
    if currency == "USD":
        return _fmt_money(amount)
    symbols = {"CAD": "C$", "AUD": "A$", "GBP": "£", "EUR": "€"}
    symbol = symbols.get(currency, f"{currency} ")
    return f"{symbol}{_fmt_money(amount).lstrip('$')}"


def _awarded_grant_lines(events: list[dict]) -> list[str]:
    totals: dict[str, int] = {}
    valued_events = 0
    for event in events:
        amounts = event.get("amounts", []) or []
        if amounts:
            valued_events += 1
        for entry in amounts:
            currency = entry.get("currency", "")
            amount = int(entry.get("amount", 0) or 0)
            if currency and amount:
                totals[currency] = totals.get(currency, 0) + amount

    total_text = ", ".join(
        _fmt_currency(value, currency)
        for currency, value in sorted(totals.items())
    ) or "No explicit award values captured yet"

    rows = []
    for event in events[:15]:
        title = str(event.get("title", "")).replace("|", "\\|")
        url = event.get("url", "")
        linked_title = f"[{title}]({url})" if url else title
        published = str(event.get("published", ""))[:10] or "—"
        amounts = event.get("amounts", []) or []
        amount_text = ", ".join(
            _fmt_currency(int(a.get("amount", 0)), a.get("currency", ""))
            for a in amounts
            if a.get("amount") and a.get("currency")
        ) or "Not stated"
        rows.append(f"| {published} | {linked_title} | {amount_text} |")

    if not rows:
        rows.append("| — | No award announcements captured yet. | — |")

    return [
        "## Awarded quantum grants",
        "",
        "Grant award announcements are catalogued here rather than presented "
        "as open opportunities. Totals use only an explicit award value in the "
        "headline (or, when absent, the feed summary), are deduplicated by story, "
        "and are kept separate by currency without applying exchange rates. They "
        "are a captured-news total, not a complete funding census, and may overlap "
        "the public-program commitments above.",
        "",
        f"**Captured total:** {total_text} across {valued_events} valued announcements "
        f"({len(events)} announcements catalogued).",
        "",
        "| Announced | Award | Captured value |",
        "|---|---|---:|",
        *rows,
        "",
    ]


def _estimate_lines(total_market_cap: float | None, market_cap_count: int) -> list[str]:
    market_cap_basis = (
        f"Sum of market caps available from Yahoo Finance for {market_cap_count} "
        "tracked company rows; excludes ETFs, diversified mega-caps, private "
        "companies, and rows with missing metadata."
        if total_market_cap is not None
        else "Market-cap metadata was unavailable from Yahoo Finance for this run."
    )

    return [
        "## Investment estimates",
        "",
        "Directional estimates for the broader quantum industry. These figures "
        "are not audited totals and should be read as a dated snapshot: "
        "public funding is mostly cumulative committed program funding, while "
        "private investment is reported as recent annual startup/VC flow.",
        "",
        "### Market and investment",
        "",
        "| Scope | Government / public | Industry / private | Total / basis |",
        "|---|---:|---:|---|",
        f"| Tracked public-company market cap | — | {_fmt_money(total_market_cap)} | {market_cap_basis} |",
        f"| Public-program commitments | {_fmt_money(PUBLIC_INVESTMENT_COMMITMENTS_USD)} | — | QED-C State of the Global Quantum Industry 2026 estimate of cumulative public quantum R&I commitments through the end of 2025. |",
        f"| 2025 startup investment flow | {_fmt_money(STARTUP_INVESTMENT_2025_PUBLIC_USD)} | {_fmt_money(STARTUP_INVESTMENT_2025_PRIVATE_USD)} | {_fmt_money(STARTUP_INVESTMENT_2025_TOTAL_USD)} total; McKinsey/PitchBook estimate, with 3% public/institutional and the rest private. |",
        f"| 2025 private VC cross-check | — | {_fmt_money(PRIVATE_VC_2025_QEDC_USD)} | QED-C's narrower private venture-capital estimate for 2025; useful as a conservative lower bound against broader startup-investment totals. |",
        "",
        "### Workforce estimate",
        "",
        "Modeled from QED-C's 2025 pure-play quantum workforce estimate and "
        "the 2026 EPJ Quantum Technology job-posting study's degree/role mix. "
        "Treat this as a role-allocation estimate, not a census.",
        "",
        "| Segment | Estimated employees | Basis |",
        "|---|---:|---|",
        f"| Technical — PhD | ~{WORKFORCE_TECH_PHD:,} | Applies the study's roughly one-third PhD-heavy job mix to the pure-play workforce total. |",
        f"| Technical — no PhD | ~{WORKFORCE_TECH_NO_PHD:,} | Bachelor/master, internship, technician, engineering, IT, and part of unspecified technical roles. |",
        f"| Non-technical | ~{WORKFORCE_NON_TECH:,} | Residual commercial, operations, finance, HR, marketing, and communications roles. |",
        f"| Total pure-play workforce | ~{WORKFORCE_TOTAL:,} | QED-C State of the Global Quantum Industry 2026 estimate for the end of 2025. |",
        "",
        "Sources: [QED-C State of the Global Quantum Industry 2026](https://quantumconsortium.org/global-quantum-computing-market-to-double/), "
        "[McKinsey Quantum Technology Monitor 2026](https://www.mckinsey.com/capabilities/mckinsey-technology/our-insights/mckinsey-quantum-technology-monitor-2026-a-commercial-tipping-point), "
        "[McKinsey quantum investment chart](https://www.mckinsey.com/featured-insights/charts/quantum-investment-surge), "
        "[Goorney et al., EPJ Quantum Technology 2026](https://doi.org/10.1140/epjqt/s40507-026-00477-z).",
        "",
    ]


def _diversified_program_lines() -> list[str]:
    workforce_low = sum(program["workforce"][0] for program in DIVERSIFIED_QUANTUM_PROGRAMS)
    workforce_high = sum(program["workforce"][1] for program in DIVERSIFIED_QUANTUM_PROGRAMS)
    spend_low = sum(
        program["annual_company_spend"][0] for program in DIVERSIFIED_QUANTUM_PROGRAMS
    )
    spend_high = sum(
        program["annual_company_spend"][1] for program in DIVERSIFIED_QUANTUM_PROGRAMS
    )
    public_support_low = sum(
        (program["public_support"] or (0, 0))[0]
        for program in DIVERSIFIED_QUANTUM_PROGRAMS
    )
    public_support_high = sum(
        (program["public_support"] or (0, 0))[1]
        for program in DIVERSIFIED_QUANTUM_PROGRAMS
    )

    rows = [
        (
            f"| {program['program']} | {_fmt_count_range(program['workforce'])} | "
            f"{_fmt_money_range(program['annual_company_spend'], '/yr')} | "
            f"{_fmt_money_range(program['public_support'])} | {program['basis']} |"
        )
        for program in DIVERSIFIED_QUANTUM_PROGRAMS
    ]

    return [
        "## Diversified-company quantum estimates",
        "",
        "Directional estimate for quantum programs inside large companies whose "
        "overall business is not primarily quantum. Most of these companies do "
        "not report quantum-specific headcount or spending as a standalone line "
        "item, so ranges are modeled from disclosed commitments, visible program "
        "scope, labs/facilities, cloud-service support, and typical loaded cost "
        "for hardware-heavy research teams.",
        "",
        "| Program | Estimated dedicated workforce | Estimated company spend | Known public support | Basis |",
        "|---|---:|---:|---:|---|",
        *rows,
        f"| **Visible-program subtotal** | **{_fmt_count_range((workforce_low, workforce_high))}** | **{_fmt_money_range((spend_low, spend_high), '/yr')}** | **{_fmt_money_range((public_support_low, public_support_high))}** | Sum of listed ranges only; excludes broad PQC migration work, ordinary cloud/HPC staff, supplier labor, university collaborators, and undisclosed programs. |",
        "",
        "Interpretation: the visible non-pure-play footprint is probably on the "
        "order of a few thousand mostly technical employees and roughly "
        "$2.5B-$4.4B per year in company-funded quantum activity, dominated by "
        "IBM's newly disclosed multi-year commitment. Known public support in "
        "this table is planned incentive funding, not necessarily obligated or "
        "outlaid cash.",
        "",
        "Sources: [IBM $10B quantum commitment](https://newsroom.ibm.com/2026-06-02-ibm-commits-more-than-10-billion-to-quantum-computing,-funding-its-roadmap-from-todays-leading-systems-to-the-worlds-first-fault-tolerant-quantum-computers), "
        "[NIST CHIPS quantum LOIs](https://www.nist.gov/news-events/news/2026/05/department-commerce-announces-letters-intent-9-companies-2-billion), "
        "[Google Chicago/Tokyo partnership](https://blog.google/innovation-and-ai/products/quantum-computing-partnership-chicago-tokyo-universities/), "
        "[Google REPLIQA](https://blog.google/innovation-and-ai/models-and-research/quantum-computing/repliqa-quantum-computing-life-sciences/), "
        "[Google neutral atoms](https://blog.google/innovation-and-ai/technology/research/neutral-atom-quantum-computers/), "
        "[Google/Atlantic Quantum](https://blog.google/innovation-and-ai/technology/research/scaling-quantum-computing-even-faster-with-atlantic-quantum/), "
        "[Microsoft quantum testimony](https://blogs.microsoft.com/on-the-issues/2025/05/07/quantum-technology/), "
        "[Microsoft Denmark quantum lab](https://news.microsoft.com/source/emea/features/microsoft-opens-state-of-the-art-quantum-lab-in-lyngby-denmark-accelerating-progress-toward-scalable-quantum-computing/), "
        "[AWS Braket/CQC/QSL announcement](https://press.aboutamazon.com/2019/12/aws-announces-new-quantum-computing-service-amazon-braket-along-with-aws-center-for-quantum-computing-and-amazon-quantum-solutions-lab), "
        "[Intel Tunnel Falls](https://newsroom.intel.com/new-technologies/quantum-computing-chip-to-advance-research), "
        "[NVIDIA NVAQC](https://nvidianews.nvidia.com/news/nvidia-to-build-accelerated-quantum-computing-research-center), "
        "[NVIDIA NVAQC GPU details](https://blogs.nvidia.com/blog/nvidia-accelerated-quantum-research-center/).",
        "",
    ]


def main() -> int:
    date = _today()
    rows_co: list[str] = []
    rows_etf: list[str] = []
    spark_data: dict[str, list[float]] = {}
    movers: list[tuple[str, str, float]] = []  # (ticker, name, pct)
    market_caps: list[float] = []

    for ticker, name, hq, focus, kind in TICKERS:
        price, pct, spark, market_cap = _fetch_one(ticker)
        if spark:
            spark_data[ticker] = spark
        if pct is not None:
            movers.append((ticker, name, pct))
        if kind == "company" and market_cap is not None:
            market_caps.append(market_cap)
        spark_cell = f'<span data-spark="{ticker}"></span>' if spark else "—"
        if kind == "company":
            row = (
                f"| {ticker} | {name} | {hq} | {focus} | "
                f"{_fmt_price(price)} | {_fmt_money(market_cap)} | "
                f"{_fmt_pct(pct)} | {spark_cell} |"
            )
        else:
            row = (
                f"| {ticker} | {name} | {hq} | {focus} | "
                f"{_fmt_price(price)} | {_fmt_pct(pct)} | {spark_cell} |"
            )
        (rows_etf if kind == "etf" else rows_co).append(row)

    total_market_cap = sum(market_caps) if market_caps else None

    gainers = sorted(
        (mover for mover in movers if mover[2] > 0),
        key=lambda x: x[2],
        reverse=True,
    )[:5]
    losers = sorted(
        (mover for mover in movers if mover[2] < 0),
        key=lambda x: x[2],
    )[:5]
    gainer_items = [
        f'<li><strong>{name}</strong> ({tk}) — {_fmt_pct(p)}</li>'
        for tk, name, p in gainers
    ] or ["<li>No gainers today.</li>"]
    loser_items = [
        f'<li><strong>{name}</strong> ({tk}) — {_fmt_pct(p)}</li>'
        for tk, name, p in losers
    ] or ["<li>No decliners today.</li>"]

    leaderboard_lines = [
        "## Leaderboard (1-day move)",
        "",
        '<div class="qr-leaderboard">',
        "",
        "**Top gainers**",
        "",
        "<ol>",
        *gainer_items,
        "</ol>",
        "",
        "**Top decliners**",
        "",
        "<ol>",
        *loser_items,
        "</ol>",
        "",
        "</div>",
        "",
    ]

    awarded_grants = _load_awarded_grants()

    body_lines = [
        f"_Generated: {date} UTC. Prices and market caps are latest available "
        "Yahoo Finance data and are informational only — not investment advice._",
        "",
        "## Companies",
        "",
        "Quantum-primary and quantum-adjacent publicly traded companies "
        "(quantum hardware, software, sensing, security, or quantum-enabled "
        "products as the core business). "
        "Diversified mega-caps with quantum divisions (Google, IBM, "
        "Microsoft, Amazon, etc.) are intentionally excluded.",
        "",
        "| Ticker | Company | HQ | Focus | Last close | Market cap | Δ vs prev close | 30d |",
        "|---|---|---|---|---|---:|---|---|",
        *rows_co,
        "",
        "## ETFs",
        "",
        "Broad-basket exchange-traded funds that track quantum-computing "
        "and adjacent quantum-tech holdings.",
        "",
        "| Ticker | Fund | Listing | Focus | Last close | Δ vs prev close | 30d |",
        "|---|---|---|---|---|---|---|",
        *rows_etf,
        "",
        *_estimate_lines(total_market_cap, len(market_caps)),
        *_awarded_grant_lines(awarded_grants),
        *_diversified_program_lines(),
        *leaderboard_lines,
        '<script type="application/json" id="qr-spark-data">',
        json.dumps(spark_data, separators=(",", ":")),
        "</script>",
        "",
    ]

    front_matter = [
        "---",
        f'title: "Quantum Industry — {date}"',
        f"date: {date}",
        "report_type: quantum-industry",
        'excerpt: "Daily public-market data, quantum funding awards, and directional quantum-industry investment and workforce estimates."',
        "tags:",
        "  - quantum-industry",
        "  - quantum-radar",
        'plain_summary: "What this is. A daily Quantum Industry snapshot: public-market data, captured quantum grant awards, and directional investment/workforce estimates. Award totals are deduplicated captured-news values, not a complete funding census. Informational only — not investment advice."',
        "---",
        "",
    ]

    out = COLLECTION_DIR / f"quantum-industry-{date}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(front_matter + body_lines) + "\n", encoding="utf-8")
    print(f"[fetch_stock_prices] wrote {out.relative_to(SITE_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
