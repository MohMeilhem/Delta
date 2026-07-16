"""Smoke tests for the analyst chat agent (offline fallback path —
conftest forces DELTA_OFFLINE and no ANTHROPIC_API_KEY is set)."""

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


def _chat(ticker: str, text: str, lang: str = "ar", assumptions: dict | None = None) -> dict:
    r = client.post(
        f"/companies/{ticker}/chat",
        json={"messages": [{"role": "user", "content": text}], "assumptions": assumptions, "lang": lang},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_margin_worry_cites_real_margin():
    fins = client.get("/companies/1120/financials").json()
    margin_pct = f"{fins[-1]['net_margin'] * 100:.1f}"
    reply = _chat("1120", "يقلقني هامش الربح")
    assert reply["source"] == "fallback"  # no API key in tests
    assert margin_pct in reply["reply_ar"]
    assert reply["key_numbers_ar"]
    assert reply["follow_ups_ar"]


def test_valuation_worry_cites_fair_value():
    base = client.get("/companies/2222/baseline").json()
    reply = _chat("2222", "هل السهم مقيّم بأعلى من قيمته؟")
    assert f"{base['fair_value']:,.2f}" in reply["reply_ar"]


def test_debt_worry_mentions_sukuk_for_sukuk_issuer():
    reply = _chat("7010", "مستوى الديون مرتفع")  # stc has sukuk in the seed
    assert "صكوك" in reply["reply_ar"]


def test_anomaly_worry_surfaces_embedded_flag():
    # Zain KSA (7030) carries an embedded net-margin anomaly in the seed data
    reply = _chat("7030", "هل هناك إشارات غير اعتيادية؟")
    assert "z" in reply["reply_ar"].lower() or "انحراف" in reply["reply_ar"]


def test_general_worry_returns_summary_and_follow_ups():
    reply = _chat("4190", "ما رأيك في هذا السهم؟")  # Jarir: clean company
    assert reply["reply_ar"]
    assert len(reply["follow_ups_ar"]) >= 2


def test_english_lang_replies_in_english():
    reply = _chat("1120", "Is the growth sustainable?", lang="en")
    assert "growth" in reply["reply_ar"].lower()


def test_analyst_assumptions_change_the_answer():
    base = client.get("/companies/1120/baseline").json()
    bearish = {**base["assumptions"], "revenue_growth": 0.01}
    with_base = _chat("1120", "هل التقييم مبرر؟", assumptions=base["assumptions"])
    with_bear = _chat("1120", "هل التقييم مبرر؟", assumptions=bearish)
    assert with_base["reply_ar"] != with_bear["reply_ar"]


def test_unknown_ticker_404():
    r = client.post(
        "/companies/9999x/chat",
        json={"messages": [{"role": "user", "content": "hi"}], "lang": "ar"},
    )
    assert r.status_code == 404


def test_empty_messages_rejected():
    r = client.post("/companies/1120/chat", json={"messages": [], "lang": "ar"})
    assert r.status_code == 422


def test_fallback_never_carries_a_proposal():
    reply = _chat("1120", "ماذا لو ارتفع سعر النفط؟")
    assert reply["proposed_assumptions"] is None
    assert reply["proposed_fair_value"] is None


def test_rate_assumptions_fallback_returns_report_card():
    base = client.get("/companies/1120/baseline").json()["assumptions"]
    aggressive = {**base, "revenue_growth": base["revenue_growth"] + 0.06,
                  "discount_rate": max(0.05, base["discount_rate"] - 0.02)}
    reply = _chat("1120", "قيّم فرضياتي", assumptions=aggressive)
    ratings = {r["parameter"]: r["verdict"] for r in reply["assumption_ratings"]}
    assert len(ratings) == 4
    assert ratings["revenue_growth"] == "aggressive"   # +6pp above baseline
    assert ratings["discount_rate"] == "aggressive"    # low discount inflates value
    assert ratings["net_margin"] == "balanced"

    baseline_reply = _chat("1120", "rate my parameters", assumptions=base)
    assert all(r["verdict"] == "balanced" for r in baseline_reply["assumption_ratings"])


def test_macro_series_aligned_with_financials():
    from app import data
    from app.chat import _macro_table

    macro_quarters = [r["quarter"] for r in data.macro()["series"]]
    fin_quarters = [q.quarter for q in data.financials("1120")]
    assert macro_quarters == fin_quarters, "macro.json must cover the seed quarters"
    table = _macro_table()
    assert "Brent" in table and "SAMA repo" in table


def test_proposals_clamped_to_slider_ranges():
    from app.chat import _clamp_proposal
    from app.valuation import Assumptions

    wild = Assumptions(revenue_growth=0.9, net_margin=0.9,
                       discount_rate=0.45, terminal_growth=0.09)
    p = _clamp_proposal(wild)
    assert p.revenue_growth == 0.40   # UI slider max
    assert p.net_margin == 0.70
    assert p.discount_rate == 0.20
    assert p.terminal_growth == 0.06
