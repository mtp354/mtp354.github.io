"""Fetch latest stock prices for publicly listed quantum-primary companies
and a couple of broad quantum ETFs, then write a Jekyll-friendly entry to
``_quantum_radar/`` for `_pages/quantum-radar.md` to pick up.

Companies are chosen by being *primarily* quantum (i.e., the entire
business is quantum hardware, software, or quantum-enabled products). It
deliberately excludes diversified mega-caps like Google, IBM, Microsoft,
and Amazon — they have quantum divisions, but tracking their stock price
is not a meaningful proxy for the public-market quantum sector.
"""

from __future__ import annotations

import datetime as _dt
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
    ("ARQQ",  "Arqit Quantum",                 "London, UK",              "Symmetric quantum-safe encryption",   "company"),
    ("QSI",   "Quantum-Si",                    "Branford, CT, USA",       "Quantum-enabled protein sequencing",  "company"),
    ("LAES",  "SEALSQ",                        "Geneva, Switzerland",     "Post-quantum secure semiconductors",  "company"),
    ("QTUM",  "Defiance Quantum ETF",          "USA",                     "Broad quantum-computing ETF",         "etf"),
]


def _today() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")


def _fetch_one(ticker: str) -> tuple[float | None, float | None]:
    """Return (last_price, change_pct_vs_prev_close)."""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d", interval="1d", auto_adjust=False)
        if hist is None or hist.empty:
            return None, None
        closes = hist["Close"].dropna()
        if closes.empty:
            return None, None
        last = float(closes.iloc[-1])
        if len(closes) >= 2:
            prev = float(closes.iloc[-2])
            pct = (last - prev) / prev * 100.0 if prev else None
        else:
            pct = None
        return last, pct
    except Exception as e:  # noqa: BLE001
        print(f"  ! {ticker}: {e}", file=sys.stderr)
        return None, None


def _fmt_price(p: float | None) -> str:
    return f"${p:,.2f}" if p is not None else "—"


def _fmt_pct(p: float | None) -> str:
    if p is None:
        return "—"
    sign = "+" if p >= 0 else ""
    return f"{sign}{p:.2f}%"


def main() -> int:
    date = _today()
    rows_co: list[str] = []
    rows_etf: list[str] = []
    for ticker, name, hq, focus, kind in TICKERS:
        price, pct = _fetch_one(ticker)
        row = (
            f"| {ticker} | {name} | {hq} | {focus} | "
            f"{_fmt_price(price)} | {_fmt_pct(pct)} |"
        )
        (rows_etf if kind == "etf" else rows_co).append(row)

    body_lines = [
        f"_Generated: {date} UTC. Prices are last available daily close from "
        "Yahoo Finance and are informational only — not investment advice._",
        "",
        "## Companies",
        "",
        "Quantum-primary publicly traded companies (quantum hardware, "
        "software, or quantum-enabled products as the core business). "
        "Diversified mega-caps with quantum divisions (Google, IBM, "
        "Microsoft, Amazon, etc.) are intentionally excluded.",
        "",
        "| Ticker | Company | HQ | Focus | Last close | Δ vs prev close |",
        "|---|---|---|---|---|---|",
        *rows_co,
        "",
        "## ETFs",
        "",
        "Broad-basket exchange-traded funds that track quantum-computing "
        "and adjacent quantum-tech holdings.",
        "",
        "| Ticker | Fund | Listing | Focus | Last close | Δ vs prev close |",
        "|---|---|---|---|---|---|",
        *rows_etf,
        "",
    ]

    front_matter = [
        "---",
        f'title: "Publicly Traded Quantum — {date}"',
        f"date: {date}",
        "report_type: publicly-traded",
        'excerpt: "Daily close prices for publicly listed quantum-primary companies and broad quantum ETFs."',
        "tags:",
        "  - publicly-traded",
        "  - quantum-radar",
        "---",
        "",
    ]

    out = COLLECTION_DIR / f"publicly-traded-{date}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(front_matter + body_lines) + "\n", encoding="utf-8")
    print(f"[fetch_stock_prices] wrote {out.relative_to(SITE_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
