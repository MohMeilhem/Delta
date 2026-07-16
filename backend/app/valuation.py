"""Baseline valuation engine.

Proof-of-concept, deliberately lightweight:
- One scikit-learn Ridge regression PER SECTOR, trained on all companies in
  that sector with revenue normalized to each company's own mean level.
  Features are just trend + quarter-of-year dummies (seasonality). This is a
  POC — a production system would use richer features and proper backtesting.
- A second per-sector model projects net margin the same way.
- Fair value is a DCF over an FCFE proxy (net income x sector conversion
  ratio) with an explicit ZAKAT line: 2.5% of an approximated zakat base
  (equity proxy ~= 4x quarterly net income run-rate) — not a generic tax.
- Islamic banks (is_islamic_bank) use financing-income terminology and a
  dividend-discount-style model (payout of projected earnings) instead of
  the standard DCF.

Everything is deterministic: no RNG anywhere, models are refit from the seed
data on first use and cached.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from pydantic import BaseModel, Field
from sklearn.linear_model import Ridge

from . import data
from .models import Company, QuarterFinancials

N_HIST = 12
N_PROJ = 8

# Sector-default valuation assumptions (annual rates).
SECTOR_DEFAULTS = {
    "banks": {"discount_rate": 0.105, "terminal_growth": 0.030, "fcf_conversion": 1.00, "payout": 0.65},
    "energy": {"discount_rate": 0.085, "terminal_growth": 0.020, "fcf_conversion": 0.90, "payout": 0.60},
    "materials": {"discount_rate": 0.095, "terminal_growth": 0.020, "fcf_conversion": 0.85, "payout": 0.55},
    "telecom": {"discount_rate": 0.090, "terminal_growth": 0.025, "fcf_conversion": 0.90, "payout": 0.70},
    "healthcare": {"discount_rate": 0.095, "terminal_growth": 0.035, "fcf_conversion": 0.80, "payout": 0.50},
    "retail": {"discount_rate": 0.100, "terminal_growth": 0.030, "fcf_conversion": 0.85, "payout": 0.60},
    "utilities": {"discount_rate": 0.080, "terminal_growth": 0.025, "fcf_conversion": 0.75, "payout": 0.65},
    "food": {"discount_rate": 0.095, "terminal_growth": 0.025, "fcf_conversion": 0.80, "payout": 0.55},
    "realestate": {"discount_rate": 0.110, "terminal_growth": 0.025, "fcf_conversion": 0.70, "payout": 0.40},
}

ZAKAT_RATE = 0.025
# Zakat base approximated as an equity proxy: 4x quarterly net income run-rate
# (same approximation used to generate the seed data, so numbers reconcile).
ZAKAT_BASE_MULTIPLE = 4.0

PROJ_QUARTERS = ["2026Q3", "2026Q4", "2027Q1", "2027Q2",
                 "2027Q3", "2027Q4", "2028Q1", "2028Q2",
                 "2028Q3", "2028Q4", "2029Q1", "2029Q2"]


# --------------------------------------------------------------------------
# Pydantic schemas
# --------------------------------------------------------------------------

class Assumptions(BaseModel):
    """Annualized assumption set driving a valuation.

    The last four fields are the "advanced" levers; their defaults reproduce
    the original 4-slider model, so older clients keep working unchanged.
    """

    revenue_growth: float = Field(ge=-0.5, le=1.0)
    net_margin: float = Field(gt=-1.0, le=1.0)
    discount_rate: float = Field(gt=0.0, le=0.5)
    terminal_growth: float = Field(ge=0.0, le=0.10)
    horizon_quarters: int = Field(default=8, ge=4, le=12)
    fcf_conversion: float | None = Field(default=None, ge=0.2, le=1.2)  # None = sector default
    terminal_method: str = Field(default="gordon", pattern="^(gordon|exit_multiple)$")
    exit_pe: float = Field(default=15.0, ge=2.0, le=40.0)


class ProjectedQuarter(BaseModel):
    quarter: str
    revenue: float
    net_income: float


class ValuationBreakdown(BaseModel):
    method: str  # "dcf" | "ddm_islamic"
    pv_forecast: float
    pv_terminal: float
    zakat_total: float  # zakat deducted over the forecast horizon (SAR m)
    total_debt: float
    sukuk_debt: float
    shares: float
    # Present value of each projected quarter's flow (SAR m) — what the
    # discount-rate lever actually moves; drawn as bars under the chart.
    pv_series: list[float] = []


class BaselineResponse(BaseModel):
    ticker: str
    is_islamic_bank: bool
    income_label_ar: str  # "الإيرادات" or "دخل التمويل" for Islamic banks
    projected: list[ProjectedQuarter]
    fair_value: float
    current_price: float
    upside_pct: float
    assumptions: Assumptions
    breakdown: ValuationBreakdown


class AnalystValuationResponse(BaseModel):
    ticker: str
    projected: list[ProjectedQuarter]
    fair_value: float
    baseline_fair_value: float
    delta_abs: float
    delta_pct: float
    current_price: float
    upside_pct: float
    assumptions: Assumptions
    breakdown: ValuationBreakdown


# --------------------------------------------------------------------------
# Sector models (trend + quarter dummies -> relative revenue / net margin)
# --------------------------------------------------------------------------

def _features(quarter_labels: list[str], t_start: int) -> np.ndarray:
    rows = []
    for i, q in enumerate(quarter_labels):
        qnum = int(q[-1])
        rows.append([
            (t_start + i) / N_HIST,          # trend
            1.0 if qnum == 1 else 0.0,       # seasonality dummies (Q4 is base)
            1.0 if qnum == 2 else 0.0,
            1.0 if qnum == 3 else 0.0,
        ])
    return np.array(rows)


@lru_cache(maxsize=32)
def _sector_models(sector_id: str) -> tuple[Ridge, Ridge]:
    """Fit (relative revenue, net margin) models pooled over the sector."""
    X_list, y_rev, y_nm = [], [], []
    for c in data.companies_by_sector(sector_id):
        fins = data.financials(c.ticker) or []
        quarters = [f.quarter for f in fins]
        revs = np.array([f.revenue for f in fins])
        rel = revs / revs.mean()  # normalize away company size
        X_list.append(_features(quarters, 0))
        y_rev.extend(rel.tolist())
        y_nm.extend([f.net_margin for f in fins])
    X = np.vstack(X_list)
    rev_model = Ridge(alpha=1.0).fit(X, np.array(y_rev))
    nm_model = Ridge(alpha=1.0).fit(X, np.array(y_nm))
    return rev_model, nm_model


def project(company: Company, horizon: int = N_PROJ) -> list[ProjectedQuarter]:
    """Project the next `horizon` quarters of revenue and net income."""
    fins = data.financials(company.ticker) or []
    rev_model, nm_model = _sector_models(company.sector)
    quarters = PROJ_QUARTERS[:horizon]
    Xf = _features(quarters, N_HIST)

    revs = np.array([f.revenue for f in fins])
    rel_pred = rev_model.predict(Xf)
    rev_pred = rel_pred * revs.mean()

    # Margin: sector-shaped path re-anchored to the company's own median
    # margin (median resists the embedded anomaly quarters).
    nm_sector = nm_model.predict(Xf)
    company_nm = float(np.median([f.net_margin for f in fins]))
    sector_nm_mean = float(np.mean(nm_model.predict(_features([f.quarter for f in fins], 0))))
    nm_pred = nm_sector * (company_nm / sector_nm_mean) if sector_nm_mean else nm_sector

    return [
        ProjectedQuarter(
            quarter=q,
            revenue=round(float(r), 1),
            net_income=round(float(r * m), 1),
        )
        for q, r, m in zip(quarters, rev_pred, nm_pred)
    ]


def derive_assumptions(company: Company, projected: list[ProjectedQuarter]) -> Assumptions:
    """Express the ML projection as the assumption set analysts adjust."""
    fins = data.financials(company.ticker) or []
    # Anomaly-resistant anchor: median of last 4 actual revenues.
    anchor = float(np.median([f.revenue for f in fins[-4:]]))
    end_rev = projected[-1].revenue
    horizon = len(projected)
    annual_growth = (end_rev / anchor) ** (4 / horizon) - 1 if anchor > 0 else 0.0
    margins = [p.net_income / p.revenue for p in projected if p.revenue]
    defaults = SECTOR_DEFAULTS[company.sector]
    return Assumptions(
        revenue_growth=round(float(np.clip(annual_growth, -0.5, 1.0)), 4),
        net_margin=round(float(np.mean(margins)), 4),
        discount_rate=defaults["discount_rate"],
        terminal_growth=defaults["terminal_growth"],
        horizon_quarters=horizon,
    )


# --------------------------------------------------------------------------
# Fair value: DCF (FCFE proxy) or dividend-discount variant for Islamic banks
# --------------------------------------------------------------------------

def _shares_outstanding(fins: list[QuarterFinancials]) -> float:
    latest = fins[-1]
    return latest.net_income / latest.eps if latest.eps else 0.0


def fair_value(
    company: Company,
    projected: list[ProjectedQuarter],
    assumptions: Assumptions,
) -> tuple[float, ValuationBreakdown]:
    """Value the projected earnings stream per share.

    POC note: cash flows here are equity-level proxies (FCFE ~= net income x
    sector conversion; dividends = payout x financing income for Islamic
    banks), so no debt is subtracted from the PV. Zakat (2.5% of the
    approximated zakat base) is deducted explicitly each quarter.
    """
    fins = data.financials(company.ticker) or []
    defaults = SECTOR_DEFAULTS[company.sector]
    shares = _shares_outstanding(fins)
    r_q = (1 + assumptions.discount_rate) ** 0.25 - 1
    g_q = (1 + assumptions.terminal_growth) ** 0.25 - 1

    method = "ddm_islamic" if company.is_islamic_bank else "dcf"
    sector_conversion = defaults["payout"] if company.is_islamic_bank else defaults["fcf_conversion"]
    conversion = assumptions.fcf_conversion if assumptions.fcf_conversion is not None else sector_conversion

    pv_forecast = 0.0
    zakat_total = 0.0
    last_flow = 0.0
    last_ni_after_zakat = 0.0
    pv_series: list[float] = []
    for i, p in enumerate(projected, start=1):
        zakat = ZAKAT_RATE * ZAKAT_BASE_MULTIPLE * max(p.net_income, 0.0)
        flow = p.net_income * conversion - zakat
        zakat_total += zakat
        pv = flow / (1 + r_q) ** i
        pv_forecast += pv
        pv_series.append(round(pv, 1))
        last_flow = flow
        last_ni_after_zakat = p.net_income - zakat

    # Terminal value: Gordon growth on the last quarterly flow, or an exit
    # P/E multiple on annualized post-zakat earnings (the analyst's choice).
    if assumptions.terminal_method == "exit_multiple":
        terminal = max(last_ni_after_zakat, 0.0) * 4 * assumptions.exit_pe
        pv_terminal = terminal / (1 + r_q) ** len(projected)
    elif r_q > g_q and last_flow > 0:
        terminal = last_flow * (1 + g_q) / (r_q - g_q)
        pv_terminal = terminal / (1 + r_q) ** len(projected)
    else:
        pv_terminal = 0.0

    equity_value = max(pv_forecast + pv_terminal, 0.0)
    fv_per_share = equity_value / shares if shares else 0.0

    latest = fins[-1]
    breakdown = ValuationBreakdown(
        method=method,
        pv_forecast=round(pv_forecast, 1),
        pv_terminal=round(pv_terminal, 1),
        zakat_total=round(zakat_total, 1),
        total_debt=latest.total_debt,
        sukuk_debt=latest.sukuk_debt,
        shares=round(shares, 1),
        pv_series=pv_series,
    )
    return round(fv_per_share, 2), breakdown


# --------------------------------------------------------------------------
# Public API used by the endpoints
# --------------------------------------------------------------------------

def baseline(company: Company, horizon: int = N_PROJ) -> BaselineResponse:
    fins = data.financials(company.ticker) or []
    projected = project(company, horizon)
    assumptions = derive_assumptions(company, projected)
    fv, breakdown = fair_value(company, projected, assumptions)
    price = fins[-1].share_price
    return BaselineResponse(
        ticker=company.ticker,
        is_islamic_bank=company.is_islamic_bank,
        income_label_ar="دخل التمويل" if company.is_islamic_bank else "الإيرادات",
        projected=projected,
        fair_value=fv,
        current_price=price,
        upside_pct=round((fv / price - 1) * 100, 1) if price else 0.0,
        assumptions=assumptions,
        breakdown=breakdown,
    )


class SensitivityResponse(BaseModel):
    """Fair-value grid: rows = revenue growth, cols = discount rate."""

    ticker: str
    growth_steps: list[float]
    discount_steps: list[float]
    grid: list[list[float]]  # grid[i][j] = FV at growth_steps[i], discount_steps[j]
    current_price: float
    base_growth: float
    base_discount: float


def sensitivity(company: Company, assumptions: Assumptions) -> SensitivityResponse:
    """The classic analyst two-way table: FV under growth x discount shocks."""
    growth_steps = [round(assumptions.revenue_growth + d, 4) for d in (-0.04, -0.02, 0.0, 0.02, 0.04)]
    discount_steps = [round(assumptions.discount_rate + d, 4) for d in (-0.02, -0.01, 0.0, 0.01, 0.02)]
    base = baseline(company)
    grid: list[list[float]] = []
    for g in growth_steps:
        row = []
        for r in discount_steps:
            a = assumptions.model_copy(update={
                "revenue_growth": max(-0.5, min(1.0, g)),
                "discount_rate": max(0.01, min(0.5, r)),
                "terminal_growth": min(assumptions.terminal_growth, max(0.01, r) - 0.005),
            })
            row.append(analyst_valuation(company, a).fair_value)
        grid.append(row)
    return SensitivityResponse(
        ticker=company.ticker,
        growth_steps=growth_steps,
        discount_steps=discount_steps,
        grid=grid,
        current_price=base.current_price,
        base_growth=assumptions.revenue_growth,
        base_discount=assumptions.discount_rate,
    )


def scenario_targets(company: Company, assumptions: Assumptions) -> dict:
    """Mechanical bull/bear price targets: assumption shocks around the
    analyst's own case, so scenario prose can cite real numbers."""
    bull_a = assumptions.model_copy(update={
        "revenue_growth": min(1.0, assumptions.revenue_growth + 0.03),
        "net_margin": min(1.0, assumptions.net_margin * 1.08),
    })
    bear_a = assumptions.model_copy(update={
        "revenue_growth": max(-0.5, assumptions.revenue_growth - 0.03),
        "net_margin": max(0.005, assumptions.net_margin * 0.85),
        "discount_rate": min(0.5, assumptions.discount_rate + 0.01),
    })
    return {
        "bull_target": analyst_valuation(company, bull_a).fair_value,
        "bear_target": analyst_valuation(company, bear_a).fair_value,
        "base_target": analyst_valuation(company, assumptions).fair_value,
    }


def analyst_valuation(company: Company, assumptions: Assumptions) -> AnalystValuationResponse:
    """Analyst scenario = baseline series re-shaped by the assumption deltas.

    The analyst revenue path scales the baseline path by the compounding
    ratio of analyst vs baseline growth, and margins scale proportionally.
    With assumptions == baseline assumptions the series (and fair value)
    reproduce the baseline exactly — the delta starts at zero and widens as
    the analyst moves away from it.
    """
    base = baseline(company, assumptions.horizon_quarters)
    b, a = base.assumptions, assumptions

    gb_q = (1 + b.revenue_growth) ** 0.25 - 1
    ga_q = (1 + a.revenue_growth) ** 0.25 - 1
    margin_scale = a.net_margin / b.net_margin if b.net_margin else 1.0

    projected = []
    for i, p in enumerate(base.projected, start=1):
        ratio = ((1 + ga_q) / (1 + gb_q)) ** i
        rev = p.revenue * ratio
        ni = p.net_income * ratio * margin_scale
        projected.append(ProjectedQuarter(
            quarter=p.quarter, revenue=round(rev, 1), net_income=round(ni, 1)))

    fv, breakdown = fair_value(company, projected, assumptions)
    price = base.current_price
    delta_abs = round(fv - base.fair_value, 2)
    delta_pct = round((fv / base.fair_value - 1) * 100, 1) if base.fair_value else 0.0
    return AnalystValuationResponse(
        ticker=company.ticker,
        projected=projected,
        fair_value=fv,
        baseline_fair_value=base.fair_value,
        delta_abs=delta_abs,
        delta_pct=delta_pct,
        current_price=price,
        upside_pct=round((fv / price - 1) * 100, 1) if price else 0.0,
        assumptions=assumptions,
        breakdown=breakdown,
    )
