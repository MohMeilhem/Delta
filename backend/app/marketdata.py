"""yfinance access layer, shared by both computation and display fallback.

fetch_ticker / fetch_financials: historical OHLCV + quarterly financials,
used by signals.py (anomaly detection) as computation input.

last_close: a single latest close, used by live.py as tier 2 of its display
fallback chain (SAHMK -> yfinance -> static seed). This is the one place
yfinance and SAHMK legitimately sit in the same code path — both are
display-only there. The hard separation rule is about SAHMK, specifically:
a SAHMK value must never reach valuation/baseline/anomaly math (which stays
on the static seed dataset and on fetch_ticker/fetch_financials above).

Tadawul tickers trade on Yahoo as "<ticker>.SR" (e.g. 1120.SR for Al Rajhi) —
the same convention already used in live.py.
"""

from __future__ import annotations

from datetime import datetime, timezone

try:
    import yfinance as yf
except ModuleNotFoundError:
    # Serverless build (root requirements.txt) omits yfinance to stay under
    # the function size limit; every fetch below already degrades to empty.
    yf = None
from pydantic import BaseModel

FETCH_TIMEOUT_S = 8.0  # yfinance has no native timeout; enforced via requests session


class DailyBar(BaseModel):
    date: str
    close: float
    volume: float


class QuarterlyFundamental(BaseModel):
    quarter: str  # ISO date of the quarter-end, e.g. "2026-03-31"
    revenue: float
    net_income: float
    net_margin: float


def _symbol(ticker: str) -> str:
    return f"{ticker}.SR"


def fetch_ticker(ticker: str, period: str = "1y") -> list[DailyBar]:
    """Daily close + volume bars, oldest first. Empty list on any failure."""
    try:
        hist = yf.Ticker(_symbol(ticker)).history(period=period, timeout=FETCH_TIMEOUT_S)
        if hist.empty:
            return []
        bars = []
        for idx, row in hist.iterrows():
            if row["Close"] != row["Close"] or row["Volume"] != row["Volume"]:  # NaN check
                continue
            bars.append(DailyBar(
                date=idx.date().isoformat(),
                close=float(row["Close"]),
                volume=float(row["Volume"]),
            ))
        return bars
    except Exception:
        return []


def fetch_last_closes(tickers: list[str]) -> dict[str, tuple[float, float]]:
    """Batched (previous_close, last_close) per ticker, one HTTP round trip.

    Used by live.py for the ticker tape — fetching 33 symbols one by one
    would take ~30s; yf.download gets them all at once. Symbols that fail
    or lack two closes are simply absent from the result.
    """
    if yf is None or not tickers:
        return {}
    try:
        hist = yf.download(
            [_symbol(t) for t in tickers],
            period="5d",
            progress=False,
            group_by="ticker",
            threads=True,
            timeout=FETCH_TIMEOUT_S,
        )
    except Exception:
        return {}
    out: dict[str, tuple[float, float]] = {}
    for t in tickers:
        try:
            closes = hist[_symbol(t)]["Close"].dropna()
            if len(closes) >= 2:
                out[t] = (float(closes.iloc[-2]), float(closes.iloc[-1]))
        except Exception:
            continue
    return out


def fetch_financials(ticker: str) -> list[QuarterlyFundamental]:
    """Quarterly revenue/net income/net margin, oldest first. Empty on failure.

    Yahoo commonly exposes only ~4-5 quarters of quarterly financials for
    Tadawul-listed names (fewer than the 8 the fundamentals check wants) —
    that's expected, not a bug; the caller degrades to insufficient_data.
    """
    try:
        t = yf.Ticker(_symbol(ticker))
        income = t.quarterly_financials
        if income is None or income.empty:
            return []
        revenue_row = next((r for r in ("Total Revenue", "TotalRevenue") if r in income.index), None)
        income_row = next((r for r in ("Net Income", "NetIncome") if r in income.index), None)
        if revenue_row is None or income_row is None:
            return []
        out = []
        for col in sorted(income.columns):  # columns are quarter-end Timestamps, oldest first
            revenue = income.loc[revenue_row, col]
            net_income = income.loc[income_row, col]
            if revenue != revenue or net_income != net_income or revenue == 0:  # NaN/zero guard
                continue
            out.append(QuarterlyFundamental(
                quarter=col.date().isoformat(),
                revenue=float(revenue),
                net_income=float(net_income),
                net_margin=float(net_income) / float(revenue),
            ))
        return out
    except Exception:
        return []


def last_close(ticker: str) -> tuple[float, str] | None:
    """Latest available close + its date, for live.py's fallback tier. None on failure."""
    bars = fetch_ticker(ticker, period="5d")
    if not bars:
        return None
    last = bars[-1]
    return last.close, last.date
