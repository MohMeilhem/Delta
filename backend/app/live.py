"""Live-market layer: hybrid SAHMK + yfinance + static-seed fallback chain.

Display-only enrichment on top of the offline seed dataset — nothing here
ever feeds valuation/baseline/anomaly math (that's marketdata.py + the
static seed via data.py). Every response is tagged with which layer served
it: "sahmk" | "yfinance" | "cache".

Fallback chain (demo-critical — conference wifi or a vendor outage must
never break the demo):
  1. SAHMK (sahmk.sa, Tadawul-licensed, free tier)   ~3s timeout
  2. yfinance latest close                            best-effort
  3. static seed dataset (data/financials.json)        always available

Each tier is independently wrapped in try/except; a failure falls through
silently to the next tier with correct source tagging, never raises.
"""

from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # keep the serverless bundle import-safe
    load_dotenv = None
from pydantic import BaseModel

from . import data, marketdata

# Same test guard as app/__init__: the suite must never pick up a live key.
if load_dotenv is not None and not os.environ.get("DELTA_NO_ENV_FILE"):
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")  # backend/.env

SAHMK_BASE = "https://app.sahmk.sa/api/v1"
SAHMK_TIMEOUT_S = 3.0
CACHE_TTL_S = 5  # short enough for the frontend's poll loop to feel live

_cache: dict[str, tuple[float, "LiveQuote"]] = {}
# One lock for all module bookkeeping (quote/tape caches, health counters):
# endpoints run on FastAPI's threadpool, and read-modify-write on shared
# dicts is not atomic. Network fetches stay OUTSIDE the lock.
_state_lock = threading.Lock()

# Health tracking: which layer most recently served each data type, and how
# many times each layer has served a request since process start. Read-only
# bookkeeping updated by live_quote()/market_summary(); no extra network
# calls are made just to answer a health check.
_source_counts: dict[str, dict[str, int]] = {
    "quote": {"sahmk": 0, "yfinance": 0, "cache": 0},
    "market_summary": {"sahmk": 0, "unavailable": 0},
}
_last_source: dict[str, str | None] = {"quote": None, "market_summary": None}


def _sahmk_key() -> str | None:
    return os.environ.get("SAHMK_API_KEY") or None


def _sahmk_headers() -> dict[str, str]:
    return {"X-API-Key": _sahmk_key() or ""}


class LiveQuote(BaseModel):
    available: bool
    symbol: str
    price: float | None = None
    previous_close: float | None = None
    change_pct: float | None = None
    currency: str | None = None
    market_time: str | None = None  # ISO 8601, exchange time
    source: str = "sahmk"  # "sahmk" | "yfinance" | "cache"


class GainerLoser(BaseModel):
    ticker: str
    name: str
    change_pct: float


class MarketSummary(BaseModel):
    available: bool
    tasi_index: float | None = None
    tasi_change_pct: float | None = None
    advancing: int | None = None
    declining: int | None = None
    unchanged: int | None = None
    market_mood: str | None = None
    # SAHMK's /market/summary/ does not return per-stock movers, only the
    # advancing/declining/unchanged breadth counts above; these stay empty
    # unless a future endpoint provides them.
    gainers: list[GainerLoser] = []
    losers: list[GainerLoser] = []
    source: str = "sahmk"
    as_of: str | None = None


def _record(kind: str, source: str) -> None:
    with _state_lock:
        _source_counts[kind][source] = _source_counts[kind].get(source, 0) + 1
        _last_source[kind] = source


# --------------------------------------------------------------------------
# Tier 1: SAHMK
# --------------------------------------------------------------------------

def _sahmk_quote(ticker: str) -> LiveQuote | None:
    if not _sahmk_key():
        return None
    try:
        with httpx.Client(timeout=SAHMK_TIMEOUT_S, headers=_sahmk_headers()) as client:
            r = client.get(f"{SAHMK_BASE}/quote/{ticker}/")
            r.raise_for_status()
            body = r.json()
        price = body.get("price") or body.get("last_price") or body.get("last")
        if price is None:
            return None
        prev = body.get("previous_close") or body.get("prev_close")
        change_pct = body.get("change_pct") or body.get("change_percent")
        if change_pct is None and prev:
            change_pct = (float(price) / float(prev) - 1) * 100
        return LiveQuote(
            available=True,
            symbol=f"{ticker}.SR",
            price=round(float(price), 2),
            previous_close=round(float(prev), 2) if prev else None,
            change_pct=round(float(change_pct), 2) if change_pct is not None else None,
            currency=body.get("currency", "SAR"),
            market_time=body.get("as_of") or body.get("timestamp"),
            source="sahmk",
        )
    except Exception:
        return None


def _sahmk_market_summary() -> MarketSummary | None:
    if not _sahmk_key():
        return None
    try:
        with httpx.Client(timeout=SAHMK_TIMEOUT_S, headers=_sahmk_headers()) as client:
            r = client.get(f"{SAHMK_BASE}/market/summary/")
            r.raise_for_status()
            body = r.json()
        index_value = body.get("index_value")
        if index_value is None:
            return None

        def _row(x: dict) -> GainerLoser:
            return GainerLoser(
                ticker=str(x.get("symbol") or x.get("ticker") or ""),
                name=str(x.get("name") or x.get("name_en") or ""),
                change_pct=float(x.get("change_pct") or x.get("change_percent") or 0.0),
            )

        return MarketSummary(
            available=True,
            tasi_index=float(index_value),
            tasi_change_pct=float(body.get("index_change_percent") or 0.0),
            advancing=body.get("advancing"),
            declining=body.get("declining"),
            unchanged=body.get("unchanged"),
            market_mood=body.get("market_mood"),
            gainers=[_row(x) for x in (body.get("gainers") or body.get("top_gainers") or [])[:5]],
            losers=[_row(x) for x in (body.get("losers") or body.get("top_losers") or [])[:5]],
            source="sahmk",
            as_of=body.get("timestamp"),
        )
    except Exception:
        return None


# --------------------------------------------------------------------------
# Tier 2 (quote only): yfinance latest close
# --------------------------------------------------------------------------

def _yfinance_quote(ticker: str) -> LiveQuote | None:
    try:
        bars = marketdata.fetch_ticker(ticker, period="5d")
        if not bars:
            return None
        last = bars[-1]
        prev = bars[-2] if len(bars) >= 2 else None
        change_pct = (last.close / prev.close - 1) * 100 if prev else None
        return LiveQuote(
            available=True,
            symbol=f"{ticker}.SR",
            price=round(last.close, 2),
            previous_close=round(prev.close, 2) if prev else None,
            change_pct=round(change_pct, 2) if change_pct is not None else None,
            currency="SAR",
            market_time=last.date,
            source="yfinance",
        )
    except Exception:
        return None


# --------------------------------------------------------------------------
# Tier 3 (quote only): static seed dataset — always available
# --------------------------------------------------------------------------

def _cached_quote(ticker: str) -> LiveQuote:
    fins = data.financials(ticker) or []
    if not fins:
        return LiveQuote(available=False, symbol=f"{ticker}.SR", source="cache")
    last = fins[-1]
    prev = fins[-2] if len(fins) >= 2 else None
    change_pct = (last.share_price / prev.share_price - 1) * 100 if prev else None
    return LiveQuote(
        available=True,
        symbol=f"{ticker}.SR",
        price=last.share_price,
        previous_close=prev.share_price if prev else None,
        change_pct=round(change_pct, 2) if change_pct is not None else None,
        currency="SAR",
        market_time=None,
        source="cache",
    )


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def live_quote(ticker: str) -> LiveQuote:
    now = time.monotonic()
    with _state_lock:
        hit = _cache.get(ticker)
    if hit and now - hit[0] < CACHE_TTL_S:
        return hit[1]

    quote = None
    try:
        quote = _sahmk_quote(ticker)
    except Exception:
        quote = None
    if quote is None:
        try:
            quote = _yfinance_quote(ticker)
        except Exception:
            quote = None
    if quote is None:
        quote = _cached_quote(ticker)

    _record("quote", quote.source)
    with _state_lock:
        _cache[ticker] = (now, quote)
    return quote


TAPE_TTL_S = 60
_tape_cache: dict[tuple[str, ...], tuple[float, dict[str, LiveQuote]]] = {}


def tape_quotes(tickers: list[str]) -> dict[str, LiveQuote]:
    """Batch quotes for the ticker tape: one yfinance download for every
    listed company, per-ticker seed fallback, 60s cache. Display-only,
    same rule as live_quote(); DELTA_OFFLINE forces the seed tier."""
    key = tuple(tickers)
    now = time.monotonic()
    with _state_lock:
        hit = _tape_cache.get(key)
    if hit and now - hit[0] < TAPE_TTL_S:
        return hit[1]

    closes: dict[str, tuple[float, float]] = {}
    if not os.environ.get("DELTA_OFFLINE"):
        try:
            closes = marketdata.fetch_last_closes(tickers)
        except Exception:
            closes = {}

    quotes: dict[str, LiveQuote] = {}
    for t in tickers:
        pair = closes.get(t)
        if pair:
            prev, last = pair
            quotes[t] = LiveQuote(
                available=True,
                symbol=f"{t}.SR",
                price=round(last, 2),
                previous_close=round(prev, 2),
                change_pct=round((last / prev - 1) * 100, 2) if prev else None,
                currency="SAR",
                source="yfinance",
            )
        else:
            quotes[t] = _cached_quote(t)

    with _state_lock:
        _tape_cache[key] = (now, quotes)
    return quotes


def market_summary() -> MarketSummary:
    summary = _sahmk_market_summary()
    if summary is None:
        # No yfinance/static fallback for market breadth (gainers/losers need
        # scanning every ticker — too heavy/fragile for a fallback tier);
        # degrade to unavailable, same pattern as an unavailable quote.
        summary = MarketSummary(available=False, source="sahmk")
        _record("market_summary", "unavailable")
    else:
        _record("market_summary", "sahmk")
    return summary


def health() -> dict:
    """Which layer is currently serving each data type, for a status widget."""
    return {
        "quote": {"last_source": _last_source["quote"], "counts": _source_counts["quote"]},
        "market_summary": {
            "last_source": _last_source["market_summary"],
            "counts": _source_counts["market_summary"],
        },
        "sahmk_key_configured": _sahmk_key() is not None,
    }
