from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# The 4 anomalies deliberately embedded in the seed data (see data/generate_seed.py)
EMBEDDED = {
    "7030": "net_margin",       # Zain KSA — impairment collapses margin
    "4003": "revenue_growth",   # eXtra — one-off revenue surge
    "6010": "free_cash_flow",   # NADEC — working-capital blowout
    "4300": "net_margin",       # Dar Al Arkan — one-off land sale gain
}

CLEAN = ["1120", "2222", "7010", "4190", "4013"]


def test_embedded_anomalies_are_caught():
    for ticker, metric in EMBEDDED.items():
        r = client.get(f"/companies/{ticker}/agent-report")
        assert r.status_code == 200
        report = r.json()
        flagged = {f["metric"] for f in report["flags"]}
        assert metric in flagged, f"{ticker}: expected {metric} flag, got {flagged}"
        assert all(abs(f["z_score"]) > 2 for f in report["flags"])
        assert all(f["explanation_ar"] for f in report["flags"])
        assert all(f["severity"] in ("high", "medium") for f in report["flags"])


def test_clean_companies_return_empty_flags():
    for ticker in CLEAN:
        report = client.get(f"/companies/{ticker}/agent-report").json()
        assert report["flags"] == [], f"{ticker} unexpectedly flagged: {report['flags']}"
        assert "لا توجد" in report["summary_ar"]


def test_only_embedded_anomalies_fire_across_all_33():
    flagged_tickers = set()
    for s in client.get("/sectors").json():
        for c in client.get(f"/sectors/{s['id']}/companies").json():
            report = client.get(f"/companies/{c['ticker']}/agent-report").json()
            if report["flags"]:
                flagged_tickers.add(c["ticker"])
    assert flagged_tickers == set(EMBEDDED), flagged_tickers


def test_flags_ranked_high_severity_first():
    report = client.get("/companies/7030/agent-report").json()
    severities = [f["severity"] for f in report["flags"]]
    assert severities == sorted(severities, key=lambda s: s != "high")


def test_anomaly_companies_get_news_context():
    # Each embedded anomaly has a recent news item hinting at the event.
    for ticker in EMBEDDED:
        report = client.get(f"/companies/{ticker}/agent-report").json()
        assert report["news_context"] is not None, f"{ticker} missing news context"
        assert report["news_context"]["date"] >= "2026-06-20"


def test_agent_report_404():
    assert client.get("/companies/0000/agent-report").status_code == 404
