"""Optional live-market layer: real Tadawul quotes via Yahoo Finance.

Tadawul symbols trade on Yahoo as "<ticker>.SR" (e.g. 1120.SR for Al Rajhi).
This is a best-effort enrichment on top of the offline seed dataset: a short
timeout, a small in-process cache, and a graceful {available: false} response
keep the demo bulletproof with no network. The seed numbers remain the model
inputs; the live quote is display-only context for the analyst.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import httpx
from pydantic import BaseModel

YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
TIMEOUT_S = 3.0
CACHE_TTL_S = 300  # quotes are delayed anyway; 5 minutes is plenty

_cache: dict[str, tuple[float, "LiveQuote"]] = {}


class LiveQuote(BaseModel):
    available: bool
    symbol: str
    price: float | None = None
    previous_close: float | None = None
    change_pct: float | None = None
    currency: str | None = None
    market_time: str | None = None  # ISO 8601, exchange time
    source: str = "Yahoo Finance (Tadawul)"


def _fetch(symbol: str) -> LiveQuote:
    try:
        with httpx.Client(timeout=TIMEOUT_S, headers={"User-Agent": "Mozilla/5.0"}) as client:
            r = client.get(YAHOO_CHART.format(symbol=symbol),
                           params={"interval": "1d", "range": "5d"})
            r.raise_for_status()
            meta = r.json()["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice")
        prev = meta.get("chartPreviousClose") or meta.get("previousClose")
        ts = meta.get("regularMarketTime")
        if price is None:
            return LiveQuote(available=False, symbol=symbol)
        return LiveQuote(
            available=True,
            symbol=symbol,
            price=round(float(price), 2),
            previous_close=round(float(prev), 2) if prev else None,
            change_pct=round((float(price) / float(prev) - 1) * 100, 2) if prev else None,
            currency=meta.get("currency"),
            market_time=datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
            if ts else None,
        )
    except Exception:
        return LiveQuote(available=False, symbol=symbol)


def live_quote(ticker: str) -> LiveQuote:
    symbol = f"{ticker}.SR"
    now = time.monotonic()
    hit = _cache.get(symbol)
    if hit and now - hit[0] < CACHE_TTL_S:
        return hit[1]
    quote = _fetch(symbol)
    # cache failures briefly too, so an offline demo doesn't retry every render
    _cache[symbol] = (now, quote)
    return quote
