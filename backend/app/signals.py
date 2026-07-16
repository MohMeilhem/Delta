"""Three-dimension Z-score anomaly detection (price / volume / fundamentals).

Separate from anomaly.py (the Arabic monitoring-agent card wired into
/companies/{ticker}/agent-report, already used by the frontend) — this module
is a new, English, machine-consumable signal feed meant to feed a future
recommendation system and to annotate the historical price chart. Both
modules may run side by side; neither depends on the other.

Data input: yfinance ONLY (backend/app/marketdata.py), per the hard
source-separation rule — SAHMK values never enter these calculations.

Same Z-score pattern, three dimensions:
  A) PRICE  — rolling Z-score on daily log returns, 90-day trailing window.
     |z| >= 2.5 is roughly a once-a-quarter move under normality, and it's
     self-normalized to each stock's own volatility: a 3% move flags for a
     stable bank but not for a volatile small-cap.
  B) VOLUME — rolling Z-score on daily volume, same 90-day window, one-tailed
     (z >= 2.5; a quiet day is not a signal, only a spike is).
  C) FUNDAMENTALS — latest quarterly net margin & revenue growth vs the
     trailing 8-quarter mean/std. |z| >= 2 — the flags that actually change a
     valuation-model input, so the threshold is tighter than price/volume.

Severity is a single global rule applied after any dimension flags:
2 <= |z| < 3 -> medium, |z| >= 3 -> high.
"""

from __future__ import annotations

import math
import statistics
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel

from . import marketdata

PRICE_VOLUME_WINDOW = 90
PRICE_VOLUME_THRESHOLD = 2.5
FUNDAMENTALS_WINDOW = 8
FUNDAMENTALS_THRESHOLD = 2.0
MIN_RETURN_VOLUME_POINTS = 30

Dimension = Literal["price", "volume", "fundamental"]
Direction = Literal["spike", "drop"]
Severity = Literal["medium", "high"]
DataStatus = Literal["ok", "insufficient_data", "data_unavailable"]


class SignalFlag(BaseModel):
    metric: str
    dimension: Dimension
    date: str
    value: float
    zscore: float
    severity: Severity
    direction: Direction
    window: int
    message: str


class SignalsResponse(BaseModel):
    ticker: str
    flags: list[SignalFlag]
    checked_at: str
    data_status: DataStatus


class SeriesPoint(BaseModel):
    date: str
    mu: float
    upper: float
    lower: float


class SeriesResponse(BaseModel):
    ticker: str
    dates: list[str]
    mu: list[float]
    upper: list[float]
    lower: list[float]


def _severity(abs_z: float) -> Severity:
    return "high" if abs_z >= 3.0 else "medium"


def _rolling_zscores(values: list[float], window: int) -> list[tuple[int, float]]:
    """(index, zscore) for every point with a full trailing window; skips
    zero-variance windows silently (flat series -> no false signal)."""
    out = []
    for i in range(window, len(values)):
        trailing = values[i - window:i]
        std = statistics.stdev(trailing)
        if std == 0:
            continue
        mean = statistics.mean(trailing)
        out.append((i, (values[i] - mean) / std))
    return out


def _price_volume_flags(ticker: str) -> tuple[list[SignalFlag], bool, bool]:
    """Returns (flags, had_data, had_enough_data)."""
    bars = marketdata.fetch_ticker(ticker, period="1y")
    if not bars:
        return [], False, False

    closes = [b.close for b in bars]
    volumes = [b.volume for b in bars]
    dates = [b.date for b in bars]
    returns = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
    ret_dates = dates[1:]
    ret_volumes = volumes[1:]  # align volume series to the same dates as returns

    if len(returns) < MIN_RETURN_VOLUME_POINTS:
        return [], True, False

    window = min(PRICE_VOLUME_WINDOW, len(returns) - 1)
    flags: list[SignalFlag] = []

    for i, z in _rolling_zscores(returns, window):
        if abs(z) < PRICE_VOLUME_THRESHOLD:
            continue
        value = returns[i]
        flags.append(SignalFlag(
            metric="daily_log_return",
            dimension="price",
            date=ret_dates[i],
            value=round(value, 4),
            zscore=round(z, 2),
            severity=_severity(abs(z)),
            direction="spike" if z > 0 else "drop",
            window=window,
            message=(
                f"Daily return of {value * 100:+.1f}% is {abs(z):.1f}σ "
                f"{'above' if z > 0 else 'below'} the {window}-day norm."
            ),
        ))

    for i, z in _rolling_zscores(ret_volumes, window):
        if z < PRICE_VOLUME_THRESHOLD:  # one-tailed: spikes only
            continue
        value = ret_volumes[i]
        flags.append(SignalFlag(
            metric="volume",
            dimension="volume",
            date=ret_dates[i],
            value=value,
            zscore=round(z, 2),
            severity=_severity(abs(z)),
            direction="spike",
            window=window,
            message=f"Trading volume of {value:,.0f} shares is {z:.1f}σ above the {window}-day average.",
        ))

    return flags, True, True


def _fundamental_flags(ticker: str) -> tuple[list[SignalFlag], bool, bool]:
    """Returns (flags, had_data, had_enough_data)."""
    fins = marketdata.fetch_financials(ticker)
    if not fins:
        return [], False, False
    if len(fins) < FUNDAMENTALS_WINDOW + 1:
        return [], True, False

    latest = fins[-1]
    trailing = fins[-1 - FUNDAMENTALS_WINDOW:-1]
    flags: list[SignalFlag] = []

    def _check(metric: str, latest_value: float, trailing_values: list[float]) -> None:
        std = statistics.stdev(trailing_values)
        if std == 0:
            return
        mean = statistics.mean(trailing_values)
        z = (latest_value - mean) / std
        if abs(z) < FUNDAMENTALS_THRESHOLD:
            return
        label = "Net margin" if metric == "net_margin" else "Revenue growth"
        flags.append(SignalFlag(
            metric=metric,
            dimension="fundamental",
            date=latest.quarter,
            value=round(latest_value, 4),
            zscore=round(z, 2),
            severity=_severity(abs(z)),
            direction="spike" if z > 0 else "drop",
            window=FUNDAMENTALS_WINDOW,
            message=(
                f"{label} of {latest_value * 100:+.1f}% is {abs(z):.1f}σ "
                f"{'above' if z > 0 else 'below'} its trailing {FUNDAMENTALS_WINDOW}-quarter norm."
            ),
        ))

    _check("net_margin", latest.net_margin, [f.net_margin for f in trailing])

    growth_latest = latest.revenue / fins[-2].revenue - 1
    growth_trailing = [
        fins[i].revenue / fins[i - 1].revenue - 1
        for i in range(len(fins) - FUNDAMENTALS_WINDOW - 1, len(fins) - 1)
    ]
    _check("revenue_growth", growth_latest, growth_trailing)

    return flags, True, True


def detect_signals(ticker: str) -> SignalsResponse:
    checked_at = datetime.now(timezone.utc).isoformat()
    try:
        pv_flags, pv_had_data, pv_enough = _price_volume_flags(ticker)
        fund_flags, fund_had_data, fund_enough = _fundamental_flags(ticker)
    except Exception:
        return SignalsResponse(ticker=ticker, flags=[], checked_at=checked_at, data_status="data_unavailable")

    flags = pv_flags + fund_flags

    if not pv_had_data and not fund_had_data:
        status: DataStatus = "data_unavailable"
    elif not pv_enough and not fund_enough:
        status = "insufficient_data"
    else:
        status = "ok"

    flags.sort(key=lambda f: (f.severity != "high", -abs(f.zscore)))
    return SignalsResponse(ticker=ticker, flags=flags, checked_at=checked_at, data_status=status)


def signal_series(ticker: str) -> SeriesResponse:
    """Rolling mean/±2.5σ price band for chart shading.

    Frontend contract (Task 3):
      - Marker color: amber #F4A93D for medium-severity flags, red #E5484D
        for high-severity flags. Never reuse the reserved chart palette
        (#4C6FFF / #FF7A45 / #FFD166) for anomaly markers or the band.
      - Badge on each marker shows the sigma value, e.g. "3.1σ".
      - Tooltip shows the flag's `message` verbatim.
      - Band (mu/upper/lower below) is shaded at ~8% opacity behind the
        price line, using the same color as the flag(s) that fall in it
        (amber/red) or a neutral tone where no flag exists.
      - mu/upper/lower are in price terms, not return terms: for each day,
        upper/lower = previous close * exp(rolling mean return ± 2.5 *
        rolling std return), i.e. "how far this stock could move today
        before it would count as an anomaly given its own recent volatility."
    """
    bars = marketdata.fetch_ticker(ticker, period="1y")
    if len(bars) < MIN_RETURN_VOLUME_POINTS + 1:
        return SeriesResponse(ticker=ticker, dates=[], mu=[], upper=[], lower=[])

    closes = [b.close for b in bars]
    dates = [b.date for b in bars]
    returns = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
    window = min(PRICE_VOLUME_WINDOW, len(returns) - 1)

    out_dates, out_mu, out_upper, out_lower = [], [], [], []
    for i in range(window, len(returns)):
        trailing = returns[i - window:i]
        std = statistics.stdev(trailing)
        mean = statistics.mean(trailing)
        prev_close = closes[i]  # closes[i] corresponds to returns[i]'s starting price
        out_dates.append(dates[i + 1])
        out_mu.append(round(prev_close * math.exp(mean), 4))
        out_upper.append(round(prev_close * math.exp(mean + PRICE_VOLUME_THRESHOLD * std), 4))
        out_lower.append(round(prev_close * math.exp(mean - PRICE_VOLUME_THRESHOLD * std), 4))

    return SeriesResponse(ticker=ticker, dates=out_dates, mu=out_mu, upper=out_upper, lower=out_lower)
