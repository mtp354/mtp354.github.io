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

import yfinance as yf

SITE_ROOT = Path(__file__).resolve().parents[3]
COLLECTION_DIR = SITE_ROOT / "_quantum_radar"

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


def _today() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")


def _fetch_market_cap(ticker_obj: yf.Ticker) -> float | None:
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
        'excerpt: "Daily public-market quantum company data, broad quantum ETFs, and directional quantum-industry investment and workforce estimates."',
        "tags:",
        "  - quantum-industry",
        "  - quantum-radar",
        'plain_summary: "What this is. A daily Quantum Industry snapshot: closing prices and market caps for publicly listed quantum-primary and quantum-adjacent companies, a couple of broad quantum-tech ETFs, and directional investment/workforce estimates. Diversified mega-caps with quantum divisions are intentionally excluded. Informational only — not investment advice."',
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
