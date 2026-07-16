"""Fallback-chain test for live.py: SAHMK raising must fall through to
yfinance (and eventually the static seed) without ever crashing, and the
response must be tagged with whichever layer actually served it."""

from app import live, marketdata


def test_sahmk_failure_falls_back_to_yfinance(monkeypatch):
    monkeypatch.setenv("SAHMK_API_KEY", "fake-key-for-test")
    live._cache.clear()

    def _raise(ticker: str):
        raise RuntimeError("SAHMK client raised (simulated outage)")

    monkeypatch.setattr(live, "_sahmk_quote", _raise)
    monkeypatch.setattr(
        marketdata, "fetch_ticker",
        lambda t, period="5d": [
            marketdata.DailyBar(date="2026-07-15", close=64.30, volume=1_000_000.0),
            marketdata.DailyBar(date="2026-07-16", close=64.45, volume=1_100_000.0),
        ],
    )

    quote = live.live_quote("1120")

    assert quote.available is True
    assert quote.source == "yfinance"
    assert quote.price == 64.45


def test_all_sources_failing_falls_back_to_static_seed(monkeypatch):
    live._cache.clear()
    monkeypatch.delenv("SAHMK_API_KEY", raising=False)
    monkeypatch.setattr(live, "_yfinance_quote", lambda t: None)

    quote = live.live_quote("1120")

    assert quote.available is True
    assert quote.source == "cache"
