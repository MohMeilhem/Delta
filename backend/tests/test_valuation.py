from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

ALL_TICKERS = [c["ticker"] for c in client.get("/sectors").json() and []] or None


def _tickers():
    tickers = []
    for s in client.get("/sectors").json():
        tickers += [c["ticker"] for c in client.get(f"/sectors/{s['id']}/companies").json()]
    return tickers


def test_baseline_deterministic():
    a = client.get("/companies/2222/baseline").json()
    b = client.get("/companies/2222/baseline").json()
    assert a == b
    assert len(a["projected"]) == 8
    assert a["fair_value"] > 0


def test_growth_up_raises_fair_value():
    base = client.get("/companies/7010/baseline").json()
    assumptions = base["assumptions"]

    low = client.post("/companies/7010/valuation", json=assumptions).json()
    assumptions_high = {**assumptions, "revenue_growth": assumptions["revenue_growth"] + 0.10}
    high = client.post("/companies/7010/valuation", json=assumptions_high).json()

    assert high["fair_value"] > low["fair_value"]
    assert high["delta_abs"] > 0
    assert high["delta_pct"] > 0


def test_analyst_at_baseline_assumptions_reproduces_baseline():
    base = client.get("/companies/4190/baseline").json()
    v = client.post("/companies/4190/valuation", json=base["assumptions"]).json()
    assert abs(v["fair_value"] - base["fair_value"]) < 0.05
    assert abs(v["delta_pct"]) < 0.5


def test_zakat_line_present_for_all_companies():
    for t in _tickers():
        b = client.get(f"/companies/{t}/baseline").json()
        assert b["breakdown"]["zakat_total"] > 0, f"{t} missing zakat line"


def test_islamic_bank_uses_ddm_and_financing_income_label():
    for t, islamic in [("1120", True), ("1150", True), ("1140", True),
                       ("1180", False), ("1010", False)]:
        b = client.get(f"/companies/{t}/baseline").json()
        assert b["is_islamic_bank"] is islamic
        if islamic:
            assert b["breakdown"]["method"] == "ddm_islamic"
            assert b["income_label_ar"] == "دخل التمويل"
        else:
            assert b["breakdown"]["method"] == "dcf"
            assert b["income_label_ar"] == "الإيرادات"


def test_discount_rate_up_lowers_fair_value():
    base = client.get("/companies/2010/baseline").json()
    a = base["assumptions"]
    lo = client.post("/companies/2010/valuation", json=a).json()
    hi = client.post("/companies/2010/valuation",
                     json={**a, "discount_rate": a["discount_rate"] + 0.05}).json()
    assert hi["fair_value"] < lo["fair_value"]


def test_invalid_assumptions_rejected():
    r = client.post("/companies/2222/valuation",
                    json={"revenue_growth": 5.0, "net_margin": 0.2,
                          "discount_rate": 0.1, "terminal_growth": 0.02})
    assert r.status_code == 422


def test_pv_series_reconciles_with_pv_forecast():
    base = client.get("/companies/2222/baseline").json()
    b = base["breakdown"]
    assert len(b["pv_series"]) == len(base["projected"])
    assert abs(sum(b["pv_series"]) - b["pv_forecast"]) < 1.0  # rounding only
    # discount rate up -> every quarterly PV shrinks
    a = base["assumptions"]
    hi = client.post("/companies/2222/valuation",
                     json={**a, "discount_rate": a["discount_rate"] + 0.05}).json()
    assert all(h < l for h, l in zip(hi["breakdown"]["pv_series"], b["pv_series"]))


def test_all_baselines_positive_and_sane():
    for t in _tickers():
        b = client.get(f"/companies/{t}/baseline").json()
        assert b["fair_value"] > 0, f"{t} nonpositive fair value"
        price = b["current_price"]
        # Prices are calibrated (data/calibrate_prices.py) to fv/px in [0.72, 1.35]
        assert 0.5 * price < b["fair_value"] < 2 * price, (
            f"{t} fair value {b['fair_value']} vs price {price}")
