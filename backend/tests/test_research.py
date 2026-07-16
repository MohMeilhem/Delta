"""Tests for the researcher features: tape, ratios, sensitivity, peers,
bilingual LLM output, and enriched scenarios."""

import pytest
from fastapi.testclient import TestClient

from app import llm
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def force_offline(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    llm._client.cache_clear()
    yield
    llm._client.cache_clear()


def _assumptions(ticker="1120"):
    return client.get(f"/companies/{ticker}/baseline").json()["assumptions"]


def test_market_tape_covers_all_companies():
    tape = client.get("/market/tape").json()
    assert len(tape) == 33
    assert all("price" in t and "change_pct" in t for t in tape)


def test_profile_has_leadership_and_ratios():
    p = client.get("/companies/2222").json()
    assert p["ceo_en"] == "Amin Nasser"
    assert p["ceo_since"] == 2015
    assert p["ceo_experience_years"] > 0
    assert p["founded"] == 1933
    assert p["employees"] > 0
    assert p["market_cap"] > 0
    assert p["pe_ratio"] > 0
    assert -1 < p["revenue_cagr_3y"] < 2


def test_sensitivity_grid_shape_and_monotonicity():
    a = _assumptions("7010")
    r = client.post("/companies/7010/sensitivity", json=a).json()
    assert len(r["grid"]) == 5 and all(len(row) == 5 for row in r["grid"])
    # More growth -> higher FV (same discount column)
    col = 2
    fvs = [row[col] for row in r["grid"]]
    assert fvs == sorted(fvs)
    # Higher discount -> lower FV (same growth row)
    row = r["grid"][2]
    assert row == sorted(row, reverse=True)


def test_peers_include_self_and_sector_only():
    peers = client.get("/companies/1120/peers").json()
    assert len(peers) == 5  # banks
    assert sum(p["is_self"] for p in peers) == 1
    assert all(p["pe_ratio"] >= 0 for p in peers)


def test_overview_english_fallback():
    o = client.get("/companies/4002/overview?lang=en").json()
    assert o["source"] == "fallback"
    assert "Mouwasat" in o["overview_ar"]
    assert "{" not in o["overview_ar"]
    assert o["ceo_note_ar"] and "{" not in o["ceo_note_ar"]


def test_overview_arabic_has_ceo_note():
    o = client.get("/companies/1120/overview").json()
    assert o["ceo_note_ar"]
    assert "وليد المقبل" in o["ceo_note_ar"] or "2021" in o["ceo_note_ar"]


def test_scenarios_have_targets_probabilities_monitoring():
    a = _assumptions("7030")
    a["revenue_growth"] += 0.05
    s = client.post("/companies/7030/scenarios", json=a).json()
    assert s["bull"]["target_price"] > s["bear"]["target_price"]
    assert 0 < s["bull"]["probability_pct"] <= 100
    assert 0 < s["bear"]["probability_pct"] <= 100
    assert s["thesis_breakers"]["target_price"] is None
    assert 3 <= len(s["monitoring_ar"]) <= 4
    assert all("{" not in m for m in s["monitoring_ar"])


def test_scenarios_english():
    a = _assumptions("4190")
    s = client.post("/companies/4190/scenarios?lang=en", json=a).json()
    assert s["bull"]["title_ar"] == "Bull case"
    assert all("{" not in p for p in s["bull"]["points_ar"])
    assert len(s["monitoring_ar"]) >= 3


def test_technicals_rating_and_indicators():
    r = client.get("/companies/1120/technicals").json()
    assert r["rating"] in ("strong_sell", "sell", "neutral", "buy", "strong_buy")
    assert -1 <= r["score"] <= 1
    names = {i["name"] for i in r["indicators"]}
    assert {"price_vs_sma20", "price_vs_sma50", "price_vs_sma200",
            "sma20_vs_sma50", "rsi14", "macd"} == names
    rsi = next(i for i in r["indicators"] if i["name"] == "rsi14")
    assert 0 <= rsi["value"] <= 100


def test_horizon_changes_projection_length():
    for h in (4, 8, 12):
        b = client.get(f"/companies/7010/baseline?horizon={h}").json()
        assert len(b["projected"]) == h
        a = b["assumptions"]
        assert a["horizon_quarters"] == h
        v = client.post("/companies/7010/valuation", json=a).json()
        assert len(v["projected"]) == h
        assert abs(v["delta_pct"]) < 0.5  # delta still ~0 at baseline assumptions


def test_exit_multiple_and_fcf_conversion_move_fair_value():
    base = client.get("/companies/2010/baseline").json()
    a = base["assumptions"]
    gordon = client.post("/companies/2010/valuation", json=a).json()["fair_value"]
    high_pe = client.post("/companies/2010/valuation",
                          json={**a, "terminal_method": "exit_multiple", "exit_pe": 30}).json()
    low_pe = client.post("/companies/2010/valuation",
                         json={**a, "terminal_method": "exit_multiple", "exit_pe": 5}).json()
    assert high_pe["fair_value"] > low_pe["fair_value"]
    more_conv = client.post("/companies/2010/valuation",
                            json={**a, "fcf_conversion": 1.1}).json()["fair_value"]
    assert more_conv > gordon


def test_overview_has_outlook():
    o = client.get("/companies/4190/overview").json()
    assert o["outlook_ar"] and "{" not in o["outlook_ar"]
    o_en = client.get("/companies/4190/overview?lang=en").json()
    assert o_en["outlook_ar"] and "{" not in o_en["outlook_ar"]


def test_candles_carry_smas():
    r = client.get("/companies/1120/prices?range=6m").json()
    assert any(c["sma20"] is not None for c in r["candles"])
    assert any(c["sma50"] is not None for c in r["candles"])


def test_live_quote_endpoint_never_breaks():
    # Works with or without network: schema is stable, availability varies.
    r = client.get("/companies/1120/live")
    assert r.status_code == 200
    q = r.json()
    assert q["symbol"] == "1120.SR"
    assert isinstance(q["available"], bool)
    if q["available"]:
        assert q["price"] and q["price"] > 0
    assert client.get("/companies/0000/live").status_code == 404
