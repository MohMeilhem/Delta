"""LLM endpoint tests — run against the offline fallback path (no API key),
which is exactly what the judges' demo relies on."""

import os

import pytest
from fastapi.testclient import TestClient

from app import llm
from app.main import app

client = TestClient(app)

CURATED = ["1120", "2222", "7010", "4190", "7030"]  # >=5 curated fallbacks


@pytest.fixture(autouse=True)
def force_offline(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    llm._client.cache_clear()
    yield
    llm._client.cache_clear()


def _baseline_assumptions(ticker: str) -> dict:
    return client.get(f"/companies/{ticker}/baseline").json()["assumptions"]


def test_overview_schema_for_curated_and_generic():
    for ticker in CURATED + ["4002"]:  # 4002 uses the _default template
        r = client.get(f"/companies/{ticker}/overview")
        assert r.status_code == 200
        o = r.json()
        assert o["source"] == "fallback"
        assert len(o["strengths_ar"]) == 3
        assert len(o["risks_ar"]) == 3
        assert o["overview_ar"] and "{" not in o["overview_ar"], "unformatted template"


def test_overview_islamic_bank_terminology():
    o = client.get("/companies/1120/overview").json()
    text = o["overview_ar"] + " ".join(o["strengths_ar"] + o["risks_ar"])
    assert "دخل التمويل" in text or "التمويل" in text


def test_news_summary_sentiments_valid():
    for ticker in ["1120", "7030", "4190"]:
        r = client.get(f"/companies/{ticker}/news-summary")
        assert r.status_code == 200
        s = r.json()
        assert s["summary_ar"]
        assert len(s["items"]) >= 4
        assert all(i["sentiment"] in ("إيجابي", "محايد", "سلبي") for i in s["items"])


def test_news_summary_anomaly_company_has_negative_item():
    s = client.get("/companies/7030/news-summary").json()
    assert any(i["sentiment"] == "سلبي" for i in s["items"])


def test_scenarios_structure_and_numbers():
    for ticker in ["1120", "7030", "4002"]:
        assumptions = _baseline_assumptions(ticker)
        assumptions["revenue_growth"] += 0.05
        r = client.post(f"/companies/{ticker}/scenarios", json=assumptions)
        assert r.status_code == 200
        s = r.json()
        for key, title in [("bull", "السيناريو المتفائل"),
                           ("bear", "السيناريو المتشائم"),
                           ("thesis_breakers", "ما قد يُبطل الفرضية")]:
            card = s[key]
            assert card["title_ar"] == title
            assert len(card["points_ar"]) == 3
            assert all("{" not in p for p in card["points_ar"]), "unformatted template"
        # scenario text must be tied to actual numbers (fair value appears)
        joined = " ".join(p for c in (s["bull"], s["bear"], s["thesis_breakers"])
                          for p in c["points_ar"])
        assert any(ch.isdigit() for ch in joined)


def test_scenarios_invalid_assumptions_rejected():
    r = client.post("/companies/1120/scenarios",
                    json={"revenue_growth": 9, "net_margin": 0.5,
                          "discount_rate": 0.1, "terminal_growth": 0.02})
    assert r.status_code == 422


def test_fallbacks_cover_at_least_5_companies():
    import json
    from app.llm import FALLBACKS_PATH
    fb = json.loads(FALLBACKS_PATH.read_text(encoding="utf-8"))
    assert len([k for k in fb["overview"] if k != "_default"]) >= 5
