"""Fallback-chain test for live.py: SAHMK raising must fall through to
yfinance (and eventually the static seed) without ever crashing, and the
response must be tagged with whichever layer actually served it."""

import pytest

from app import live, marketdata


@pytest.fixture(autouse=True)
def _clean_live_state():
    live._cache.clear()
    live._tape_cache.clear()
    live._sahmk_attempt.clear()
    live._sahmk_last.clear()
    yield
    live._cache.clear()
    live._tape_cache.clear()
    live._sahmk_attempt.clear()
    live._sahmk_last.clear()


def test_sahmk_failure_falls_back_to_yfinance(monkeypatch):
    monkeypatch.setenv("SAHMK_API_KEY", "fake-key-for-test")

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
    monkeypatch.delenv("SAHMK_API_KEY", raising=False)
    monkeypatch.setattr(live, "_yfinance_quote", lambda t: None)

    quote = live.live_quote("1120")

    assert quote.available is True
    assert quote.source == "cache"


def test_sahmk_budget_one_attempt_per_window(monkeypatch):
    """SAHMK is asked once per ticker per budget window; the 5s-cadence polls
    in between are served by yfinance (60/day free-tier protection)."""
    monkeypatch.setenv("SAHMK_API_KEY", "fake-key-for-test")
    calls = {"n": 0}

    def fake_sahmk(ticker):
        calls["n"] += 1
        return live.LiveQuote(available=True, symbol=f"{ticker}.SR",
                              price=64.45, change_pct=0.23, source="sahmk")

    monkeypatch.setattr(live, "_sahmk_quote", fake_sahmk)
    monkeypatch.setattr(
        live, "_yfinance_quote",
        lambda t: live.LiveQuote(available=True, symbol=f"{t}.SR",
                                 price=64.40, change_pct=0.15, source="yfinance"))

    first = live.live_quote("1120")
    live._cache.clear()  # bypass the 5s poll cache, but NOT the SAHMK budget
    second = live.live_quote("1120")

    assert first.source == "sahmk"
    assert second.source == "yfinance"  # budget window still open
    assert calls["n"] == 1


def test_sahmk_stale_quote_beats_seed_when_yfinance_down(monkeypatch):
    monkeypatch.setenv("SAHMK_API_KEY", "fake-key-for-test")
    monkeypatch.setattr(
        live, "_sahmk_quote",
        lambda t: live.LiveQuote(available=True, symbol=f"{t}.SR",
                                 price=64.45, change_pct=0.23, source="sahmk"))
    monkeypatch.setattr(live, "_yfinance_quote", lambda t: None)

    live.live_quote("1120")  # fills the SAHMK cache
    live._cache.clear()
    stale = live.live_quote("1120")  # budget closed + yfinance down

    assert stale.source == "sahmk"
    assert stale.price == 64.45


def test_tape_quotes_offline_uses_seed(monkeypatch):
    monkeypatch.setenv("DELTA_OFFLINE", "1")

    quotes = live.tape_quotes(["1120"])

    assert quotes["1120"].available is True
    assert quotes["1120"].source == "cache"


def test_tape_quotes_batch_with_per_ticker_fallback(monkeypatch):
    monkeypatch.delenv("DELTA_OFFLINE", raising=False)
    monkeypatch.setattr(
        marketdata, "fetch_last_closes",
        lambda tickers: {"1120": (64.0, 65.6)},  # 1180 missing from the batch
    )

    quotes = live.tape_quotes(["1120", "1180"])

    assert quotes["1120"].source == "yfinance"
    assert quotes["1120"].price == 65.6
    assert quotes["1120"].change_pct == 2.5
    assert quotes["1180"].source == "cache"  # seed fallback for the miss
    live._tape_cache.clear()
