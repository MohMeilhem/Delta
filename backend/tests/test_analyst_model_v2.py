"""Smoke tests for Analyst Model v2 — one block per build phase:
seed extension, anomaly cause-labelling, incident exclusion, 7-metric
sliders (all offline: conftest forces the fallback paths)."""

from fastapi.testclient import TestClient

from app import anomaly, data, valuation
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Phase 1 — seed extension
# ---------------------------------------------------------------------------

def test_seed_carries_v2_series_for_every_company():
    for c in data.companies():
        fins = data.financials(c.ticker)
        assert fins and len(fins) == 12
        for f in fins:
            assert f.equity and f.equity > 0
            assert f.total_assets and f.total_assets > 0
            # identity: roe == 4*NI/equity (rounding tolerance)
            assert abs(f.roe - 4 * f.net_income / f.equity) < 2e-3
            if c.sector == "banks":
                assert f.ebitda is None and f.current_ratio is None
            else:
                assert f.ebitda_margin is not None
                assert f.current_ratio is not None and f.current_ratio > 0


# ---------------------------------------------------------------------------
# Phase 2 — cause-labelling on flags
# ---------------------------------------------------------------------------

def test_flags_carry_grounded_causes():
    report = anomaly.agent_report("7030")  # Zain: embedded margin collapse
    assert report.flags
    top = report.flags[0]
    assert top.cause_ar and top.cause_en
    assert top.cause_confidence in ("grounded", "tentative")
    assert top.suggested_exclusion == "2026Q2"
    # the seeded impairment headline sits in the ±45d window and is negative
    assert top.causal_news, "anomaly companies have aligned seed news"


def test_clean_company_has_no_flags():
    assert anomaly.agent_report("4190").flags == []


# ---------------------------------------------------------------------------
# Phase 3 — incident exclusion
# ---------------------------------------------------------------------------

def test_excluding_the_incident_quarter_clears_the_flag_and_refits():
    assert anomaly.detect_anomalies("7030")
    assert anomaly.detect_anomalies("7030", ("2026Q2",)) == []

    zain = data.company("7030")
    fv_with = valuation.baseline(zain).fair_value
    fv_without = valuation.baseline(zain, exclude=("2026Q2",)).fair_value
    assert fv_with != fv_without  # the model re-fit on normalized history

    # sector scope drops the quarter from the pooled fit too
    fv_sector = valuation.baseline(zain, exclude=("2026Q2",), scope="sector").fair_value
    assert fv_sector != fv_with


def test_exclusion_flows_through_the_api():
    r = client.get("/companies/7030/baseline?exclude=2026Q2")
    assert r.status_code == 200
    assert r.json()["assumptions"]["exclude_quarters"] == ["2026Q2"]

    r = client.get("/companies/7030/agent-report?exclude=2026Q2")
    assert r.status_code == 200
    assert r.json()["flags"] == []


# ---------------------------------------------------------------------------
# Phase 4 — the 7-metric sliders
# ---------------------------------------------------------------------------

def test_baseline_populates_the_v2_sliders():
    jarir = valuation.baseline(data.company("4190")).assumptions
    assert jarir.roe and jarir.roa and jarir.ebitda_margin and jarir.current_ratio
    bank = valuation.baseline(data.company("1120")).assumptions
    assert bank.roe and bank.roa
    assert bank.ebitda_margin is None and bank.current_ratio is None  # n.a.


def test_every_slider_moves_fair_value_in_the_right_direction():
    jarir = data.company("4190")
    base = valuation.baseline(jarir)
    a = base.assumptions

    def fv(**updates):
        return valuation.analyst_valuation(jarir, a.model_copy(update=updates)).fair_value

    # continuity: analyst == baseline at the baseline assumptions
    assert fv() == base.fair_value

    assert fv(ebitda_margin=a.ebitda_margin + 0.05) > base.fair_value
    assert fv(roe=a.roe + 0.08) > base.fair_value
    assert fv(roe=a.roe - 0.08) < base.fair_value
    assert fv(roa=a.roa - 0.05) < base.fair_value           # risk premium up
    assert fv(current_ratio=a.current_ratio - 0.8) < base.fair_value
    assert (fv(terminal_method="exit_multiple", exit_pe=a.exit_pe + 10)
            > fv(terminal_method="exit_multiple"))


def test_banks_use_the_roe_driven_book_value_path():
    rajhi = data.company("1120")
    base = valuation.baseline(rajhi)
    assert base.breakdown.method == "ddm_islamic"  # Islamic label kept
    snb = valuation.baseline(data.company("1180"))
    assert snb.breakdown.method == "ddm_bank"  # conventional bank

    a = base.assumptions
    assert valuation.analyst_valuation(rajhi, a).fair_value == base.fair_value
    up = valuation.analyst_valuation(rajhi, a.model_copy(update={"roe": a.roe + 0.05}))
    dn = valuation.analyst_valuation(rajhi, a.model_copy(update={"roe": a.roe - 0.05}))
    assert up.fair_value > base.fair_value > dn.fair_value

    # bank-n.a. sliders are accepted as null through the API
    body = a.model_dump()
    r = client.post("/companies/1120/valuation", json=body)
    assert r.status_code == 200
