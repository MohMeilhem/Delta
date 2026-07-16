"""Daily OHLC price series, derived deterministically from the quarterly
seed closes.

The seed dataset carries one closing price per quarter. For the trading view
(candlesticks, trailing performance, 52-week high/low) we synthesize a daily
path with a geometric Brownian bridge that is pinned to every quarter-end
close — so the daily series is always consistent with financials.json and
fully reproducible (RNG seeded per ticker; no state, cached per process).
"""

from __future__ import annotations

import math
import random
from datetime import date, timedelta
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel

from . import data

Range = Literal["1m", "3m", "6m", "1y", "all"]

QUARTER_END = {"1": (3, 31), "2": (6, 30), "3": (9, 30), "4": (12, 31)}

# trading-day offsets for the trailing windows
WINDOW_DAYS = {"1m": 21, "3m": 63, "6m": 126, "1y": 252}


class Candle(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    sma20: float | None = None
    sma50: float | None = None


class RangeChange(BaseModel):
    range: str
    from_price: float
    from_date: str
    change_pct: float


class PriceStats(BaseModel):
    last: float
    last_date: str
    changes: list[RangeChange]  # 1m / 3m / 6m / 1y
    high_52w: float
    high_52w_date: str
    low_52w: float
    low_52w_date: str


class Level(BaseModel):
    """A horizontal support/resistance level from clustered swing pivots."""

    price: float
    touches: int  # how many pivots formed this level (strength)
    kind: Literal["support", "resistance"]


class PriceSeries(BaseModel):
    ticker: str
    range: Range
    candles: list[Candle]
    stats: PriceStats
    levels: list[Level]


def _quarter_end(q: str) -> date:
    year = int(q[:4])
    month, day = QUARTER_END[q[5]]
    return date(year, month, day)


def _business_days(start: date, end: date) -> list[date]:
    """Sun–Thu trading week (Tadawul convention), exclusive of start."""
    days = []
    d = start + timedelta(days=1)
    while d <= end:
        if d.weekday() not in (4, 5):  # Friday, Saturday
            days.append(d)
        d += timedelta(days=1)
    return days


@lru_cache(maxsize=64)
def _daily(ticker: str) -> list[Candle]:
    fins = data.financials(ticker)
    assert fins, f"no financials for {ticker}"
    rng = random.Random(f"prices-{ticker}")

    anchors = [(_quarter_end(f.quarter), f.share_price) for f in fins]
    candles: list[Candle] = []
    prev_close = anchors[0][1]

    for (d0, p0), (d1, p1) in zip(anchors, anchors[1:]):
        days = _business_days(d0, d1)
        n = len(days)
        if n == 0:
            continue
        # log-space Brownian bridge from p0 to p1
        sigma = 0.011 + (hash(ticker) % 7) * 0.0012  # per-ticker daily vol
        raw = [0.0]
        for _ in range(n):
            raw.append(raw[-1] + rng.gauss(0, sigma))
        target = math.log(p1 / p0)
        closes = [
            p0 * math.exp(raw[i] + (target - raw[n]) * (i / n)) for i in range(1, n + 1)
        ]
        for day, close in zip(days, closes):
            spread = abs(rng.gauss(0, sigma * 0.8))
            hi = max(prev_close, close) * (1 + spread)
            lo = min(prev_close, close) * (1 - abs(rng.gauss(0, sigma * 0.8)))
            candles.append(Candle(
                date=day.isoformat(),
                open=round(prev_close, 2),
                high=round(hi, 2),
                low=round(lo, 2),
                close=round(close, 2),
            ))
            prev_close = close

    return candles


def _with_smas(daily: list[Candle]) -> list[Candle]:
    """Attach 20- and 50-day simple moving averages to each daily candle."""
    closes = [c.close for c in daily]
    out = []
    for i, c in enumerate(daily):
        sma20 = round(sum(closes[i - 19 : i + 1]) / 20, 2) if i >= 19 else None
        sma50 = round(sum(closes[i - 49 : i + 1]) / 50, 2) if i >= 49 else None
        out.append(c.model_copy(update={"sma20": sma20, "sma50": sma50}))
    return out


def _aggregate_weekly(candles: list[Candle]) -> list[Candle]:
    weeks: dict[tuple[int, int], list[Candle]] = {}
    for c in candles:
        iso = date.fromisoformat(c.date).isocalendar()
        weeks.setdefault((iso[0], iso[1]), []).append(c)
    out = []
    for _, group in sorted(weeks.items()):
        out.append(Candle(
            date=group[-1].date,
            open=group[0].open,
            high=max(c.high for c in group),
            low=min(c.low for c in group),
            close=group[-1].close,
            sma20=group[-1].sma20,
            sma50=group[-1].sma50,
        ))
    return out


def _stats(daily: list[Candle]) -> PriceStats:
    last = daily[-1]
    changes = []
    for key, offset in WINDOW_DAYS.items():
        ref = daily[max(len(daily) - 1 - offset, 0)]
        changes.append(RangeChange(
            range=key,
            from_price=ref.close,
            from_date=ref.date,
            change_pct=round((last.close / ref.close - 1) * 100, 2),
        ))
    year = daily[-252:]
    hi = max(year, key=lambda c: c.high)
    lo = min(year, key=lambda c: c.low)
    return PriceStats(
        last=last.close,
        last_date=last.date,
        changes=changes,
        high_52w=hi.high,
        high_52w_date=hi.date,
        low_52w=lo.low,
        low_52w_date=lo.date,
    )


def _pivots(candles: list[Candle], span: int = 5) -> tuple[list[Candle], list[Candle]]:
    """Swing highs / swing lows: extremes vs `span` neighbors on each side."""
    highs, lows = [], []
    for i in range(span, len(candles) - span):
        window = candles[i - span : i + span + 1]
        c = candles[i]
        if c.high == max(w.high for w in window):
            highs.append(c)
        if c.low == min(w.low for w in window):
            lows.append(c)
    return highs, lows


def _cluster_levels(values: list[float], tolerance: float) -> list[tuple[float, int]]:
    """Group nearby pivot prices into levels; returns (mean price, touches)."""
    levels: list[list[float]] = []
    for v in sorted(values):
        if levels and abs(v - levels[-1][-1]) / v < tolerance:
            levels[-1].append(v)
        else:
            levels.append([v])
    return [(sum(g) / len(g), len(g)) for g in levels]


def detect_levels(candles: list[Candle], last_price: float, top_n: int = 3) -> list[Level]:
    """Key support (below price) and resistance (above price) levels,
    ranked by how many swing pivots touched them."""
    if len(candles) < 12:
        return []
    highs, lows = _pivots(candles)
    clustered = _cluster_levels(
        [c.high for c in highs] + [c.low for c in lows], tolerance=0.015
    )
    supports = sorted(
        (lv for lv in clustered if lv[0] < last_price),
        key=lambda lv: (-lv[1], last_price - lv[0]),
    )[:top_n]
    resistances = sorted(
        (lv for lv in clustered if lv[0] >= last_price),
        key=lambda lv: (-lv[1], lv[0] - last_price),
    )[:top_n]
    out = [Level(price=round(p, 2), touches=n, kind="support") for p, n in supports]
    out += [Level(price=round(p, 2), touches=n, kind="resistance") for p, n in resistances]
    return out


# --------------------------------------------------------------------------
# Technical analysis: indicator battery + aggregate rating (the gauge)
# --------------------------------------------------------------------------

Signal = Literal["buy", "sell", "neutral"]


class Indicator(BaseModel):
    name: str  # stable key, translated client-side
    value: float
    reference: float | None = None  # what it's compared against
    signal: Signal


class Technicals(BaseModel):
    ticker: str
    as_of: str
    score: float  # -1 .. +1
    rating: Literal["strong_sell", "sell", "neutral", "buy", "strong_buy"]
    indicators: list[Indicator]


def _rsi(closes: list[float], period: int = 14) -> float:
    gains, losses = [], []
    for prev, cur in zip(closes[-period - 1 : -1], closes[-period:]):
        change = cur - prev
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def _ema(values: list[float], period: int) -> list[float]:
    k = 2 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def technicals(ticker: str) -> Technicals:
    daily = _daily(ticker)
    closes = [c.close for c in daily]
    last = closes[-1]

    sma20 = sum(closes[-20:]) / 20
    sma50 = sum(closes[-50:]) / 50
    sma200 = sum(closes[-200:]) / 200
    rsi = _rsi(closes)
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    macd_line = [a - b for a, b in zip(ema12, ema26)]
    macd = macd_line[-1]
    macd_signal = _ema(macd_line, 9)[-1]

    def vs(value: float, ref: float) -> Signal:
        return "buy" if value > ref * 1.001 else "sell" if value < ref * 0.999 else "neutral"

    indicators = [
        Indicator(name="price_vs_sma20", value=round(last, 2), reference=round(sma20, 2),
                  signal=vs(last, sma20)),
        Indicator(name="price_vs_sma50", value=round(last, 2), reference=round(sma50, 2),
                  signal=vs(last, sma50)),
        Indicator(name="price_vs_sma200", value=round(last, 2), reference=round(sma200, 2),
                  signal=vs(last, sma200)),
        Indicator(name="sma20_vs_sma50", value=round(sma20, 2), reference=round(sma50, 2),
                  signal=vs(sma20, sma50)),
        Indicator(name="rsi14", value=round(rsi, 1), reference=None,
                  signal="sell" if rsi > 70 else "buy" if rsi < 30 else "neutral"),
        Indicator(name="macd", value=round(macd, 3), reference=round(macd_signal, 3),
                  signal=vs(macd, macd_signal)),
    ]

    score = sum(1 if i.signal == "buy" else -1 if i.signal == "sell" else 0
                for i in indicators) / len(indicators)
    if score >= 0.5:
        rating = "strong_buy"
    elif score >= 0.17:
        rating = "buy"
    elif score <= -0.5:
        rating = "strong_sell"
    elif score <= -0.17:
        rating = "sell"
    else:
        rating = "neutral"
    return Technicals(
        ticker=ticker,
        as_of=daily[-1].date,
        score=round(score, 2),
        rating=rating,
        indicators=indicators,
    )


def price_series(ticker: str, rng: Range) -> PriceSeries:
    daily = _with_smas(_daily(ticker))
    stats = _stats(daily)
    if rng in ("1m", "3m"):
        window = daily[-WINDOW_DAYS[rng] :]
    elif rng in ("6m", "1y"):
        window = _aggregate_weekly(daily[-WINDOW_DAYS[rng] :])
    else:
        window = _aggregate_weekly(daily)
    # levels come from daily pivots over the trailing year: many touch points
    # cluster into real zones (weekly windows are too sparse for pivots)
    levels = detect_levels(daily[-252:], stats.last)
    return PriceSeries(ticker=ticker, range=rng, candles=window, stats=stats, levels=levels)
