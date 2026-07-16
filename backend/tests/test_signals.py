"""Synthetic-series tests for signals.py (3-dimension anomaly detection).

All tests monkeypatch marketdata.fetch_ticker/fetch_financials with
hand-built series so results are deterministic and don't hit the network.
"""

from app import marketdata, signals

TICKER = "TEST"


def _bars(returns: list[float], volumes: list[float], start_price: float = 100.0) -> list[marketdata.DailyBar]:
    """Build DailyBars from a list of daily log returns (bars[0] is the anchor
    day with no prior return, so len(bars) == len(returns) + 1)."""
    closes = [start_price]
    for r in returns:
        closes.append(closes[-1] * pow(2.718281828459045, r))
    bars = []
    for i, close in enumerate(closes):
        vol = volumes[i] if i < len(volumes) else volumes[-1]
        bars.append(marketdata.DailyBar(date=f"2026-01-{i + 1:02d}" if i < 28 else f"2026-{2 + i // 28:02d}-{i % 28 + 1:02d}", close=close, volume=vol))
    return bars


def _flat_bars(n: int, price: float = 100.0, volume: float = 1_000_000.0) -> list[marketdata.DailyBar]:
    return _bars([0.0] * (n - 1), [volume] * n, start_price=price)


def _quarters(n: int, net_margin: float, growth: float) -> list[marketdata.QuarterlyFundamental]:
    revenue = 1000.0
    out = []
    for i in range(n):
        out.append(marketdata.QuarterlyFundamental(
            quarter=f"202{3 + i // 4}-{['03', '06', '09', '12'][i % 4]}-28",
            revenue=revenue,
            net_income=revenue * net_margin,
            net_margin=net_margin,
        ))
        revenue *= (1 + growth)
    return out


def test_injected_return_spike_flags_high_severity_and_drop(monkeypatch):
    # Alternating +-1% baseline (std ~1%), then one big -6.2% day.
    returns = [0.01 if i % 2 == 0 else -0.01 for i in range(99)] + [-0.062]
    bars = _bars(returns, [1_000_000.0] * 101)
    monkeypatch.setattr(signals.marketdata, "fetch_ticker", lambda t, period="1y": bars)
    monkeypatch.setattr(signals.marketdata, "fetch_financials", lambda t: [])

    result = signals.detect_signals(TICKER)
    price_flags = [f for f in result.flags if f.dimension == "price"]
    last_flag = next((f for f in price_flags if f.date == bars[-1].date), None)

    assert last_flag is not None, f"expected a flag on the injected spike day, got {price_flags}"
    assert last_flag.direction == "drop"
    assert last_flag.severity == "high"
    assert abs(last_flag.zscore) >= 3.0


def test_calm_series_does_not_flag(monkeypatch):
    bars = _flat_bars(150)
    quarters = _quarters(9, net_margin=0.20, growth=0.02)
    monkeypatch.setattr(signals.marketdata, "fetch_ticker", lambda t, period="1y": bars)
    monkeypatch.setattr(signals.marketdata, "fetch_financials", lambda t: quarters)

    result = signals.detect_signals(TICKER)
    assert result.flags == []
    assert result.data_status == "ok"


def test_short_series_is_insufficient_data(monkeypatch):
    bars = _flat_bars(10)
    monkeypatch.setattr(signals.marketdata, "fetch_ticker", lambda t, period="1y": bars)
    monkeypatch.setattr(signals.marketdata, "fetch_financials", lambda t: [])

    result = signals.detect_signals(TICKER)
    assert result.flags == []
    assert result.data_status == "insufficient_data"


def test_volume_spike_with_flat_price_flags_volume_only(monkeypatch):
    n = 120
    volumes = [1_000_000.0 if i % 2 == 0 else 1_050_000.0 for i in range(n)]
    volumes[-1] = 20_000_000.0  # huge spike, price stays flat throughout
    bars = _bars([0.0] * (n - 1), volumes)
    monkeypatch.setattr(signals.marketdata, "fetch_ticker", lambda t, period="1y": bars)
    monkeypatch.setattr(signals.marketdata, "fetch_financials", lambda t: [])

    result = signals.detect_signals(TICKER)
    dimensions = {f.dimension for f in result.flags}
    assert "volume" in dimensions
    assert "price" not in dimensions  # zero-variance returns must never flag
    spike_flag = next(f for f in result.flags if f.dimension == "volume" and f.date == bars[-1].date)
    assert spike_flag.direction == "spike"
