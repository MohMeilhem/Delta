"""Tests for the daily OHLC price series, trailing stats and S/R levels."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_prices_deterministic_and_pinned_to_quarterly_close():
    a = client.get("/companies/1120/prices?range=6m").json()
    b = client.get("/companies/1120/prices?range=6m").json()
    assert a == b
    latest_quarterly = client.get("/companies/1120").json()["latest"]["share_price"]
    assert abs(a["stats"]["last"] - latest_quarterly) < 0.01


def test_candles_are_valid_ohlc():
    r = client.get("/companies/7030/prices?range=3m").json()
    assert len(r["candles"]) >= 50  # ~63 trading days
    for c in r["candles"]:
        assert c["low"] <= min(c["open"], c["close"])
        assert c["high"] >= max(c["open"], c["close"])
    dates = [c["date"] for c in r["candles"]]
    assert dates == sorted(dates)


def test_stats_have_all_windows_and_52w_extremes():
    s = client.get("/companies/2222/prices?range=1y").json()["stats"]
    assert [c["range"] for c in s["changes"]] == ["1m", "3m", "6m", "1y"]
    assert all(c["from_date"] for c in s["changes"])
    assert s["low_52w"] <= s["last"] <= s["high_52w"] * 1.001
    assert s["high_52w_date"] and s["low_52w_date"]


def test_levels_split_around_last_price():
    r = client.get("/companies/7030/prices?range=6m").json()
    last = r["stats"]["last"]
    for level in r["levels"]:
        if level["kind"] == "support":
            assert level["price"] < last
        else:
            assert level["price"] >= last
        assert level["touches"] >= 1


def test_prices_404():
    assert client.get("/companies/0000/prices").status_code == 404
