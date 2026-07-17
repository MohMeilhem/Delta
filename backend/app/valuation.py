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

try:
    from sklearn.linear_model import Ridge
except ModuleNotFoundError:
    class Ridge:
        """Closed-form ridge regression, numerically identical to sklearn's
        Ridge(alpha, fit_intercept=True) for our tiny dense inputs. Used by
        the serverless build, where sklearn is omitted to stay under the
        function size limit (see root requirements.txt)."""

        def __init__(self, alpha: float = 1.0):
            self.alpha = alpha

        def fit(self, X, y):
            X = np.asarray(X, dtype=float)
            y = np.asarray(y, dtype=float)
            # sklearn centers X and y so the intercept is not penalized
            x_mean, y_mean = X.mean(axis=0), y.mean()
            Xc, yc = X - x_mean, y - y_mean
            A = Xc.T @ Xc + self.alpha * np.eye(X.shape[1])
            self.coef_ = np.linalg.solve(A, Xc.T @ yc)
            self.intercept_ = y_mean - x_mean @ self.coef_
            return self

        def predict(self, X):
            return np.asarray(X, dtype=float) @ self.coef_ + self.intercept_

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
    # ---- Analyst Model v2 ----
    # Incident normalization (Problem 2): quarters the analyst excluded from
    # the fit. "company" drops them from this company's anchors only;
    # "sector" also drops them from the pooled sector fit. Excluded quarters
    # keep their real label — the trend index is gapped, never re-indexed.
    exclude_quarters: list[str] = Field(default_factory=list, max_length=8)
    exclude_scope: str = Field(default="company", pattern="^(company|sector)$")
    # The 7-metric sliders (Problem 1). None = machine baseline / n.a. —
    # EBITDA margin and current ratio are structurally null for banks.
    ebitda_margin: float | None = Field(default=None, gt=0.0, le=0.9)
    roe: float | None = Field(default=None, gt=0.0, le=0.6)
    roa: float | None = Field(default=None, gt=0.0, le=0.4)
    current_ratio: float | None = Field(default=None, gt=0.0, le=6.0)


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
    current_price: float  # seed model price — engine numbers stay reproducible
    upside_pct: float  # fair_value vs current_price (seed)
    assumptions: Assumptions
    breakdown: ValuationBreakdown
    # Display overlay, filled by the endpoint layer (never by the engine):
    # the live market price the rest of the screen (tape, header, peers)
    # shows, and the gap recomputed against it. Falls back to the seed values.
    market_price: float | None = None
    market_upside_pct: float | None = None
    price_source: str = "cache"  # "yfinance" | "sahmk" | "cache"


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


def _keep_indices(fins: list[QuarterFinancials], exclude: tuple[str, ...]) -> list[int]:
    """Indices of quarters that stay in the fit. Excluded quarters keep their
    positional index elsewhere (the trend axis is gapped, never re-indexed).
    If exclusion would leave < 4 quarters, it is ignored entirely."""
    ex = set(exclude)
    kept = [i for i, f in enumerate(fins) if f.quarter not in ex]
    return kept if len(kept) >= 4 else list(range(len(fins)))


@lru_cache(maxsize=128)
def _sector_models(sector_id: str, exclude_key: tuple[str, ...] = ()) -> tuple[Ridge, Ridge]:
    """Fit (relative revenue, net margin) models pooled over the sector.

    `exclude_key` is non-empty only for scope="sector" exclusions: the
    quarters are dropped from every company's rows in the pool, with the
    trend index gapped (features are built on the full quarter list first,
    then rows are removed)."""
    X_list, y_rev, y_nm = [], [], []
    for c in data.companies_by_sector(sector_id):
        fins = data.financials(c.ticker) or []
        keep = _keep_indices(fins, exclude_key)
        feats = _features([f.quarter for f in fins], 0)[keep]
        revs = np.array([fins[i].revenue for i in keep])
        rel = revs / revs.mean()  # normalize away company size
        X_list.append(feats)
        y_rev.extend(rel.tolist())
        y_nm.extend([fins[i].net_margin for i in keep])
    X = np.vstack(X_list)
    rev_model = Ridge(alpha=1.0).fit(X, np.array(y_rev))
    nm_model = Ridge(alpha=1.0).fit(X, np.array(y_nm))
    return rev_model, nm_model


# v2 metric fields that get their own pooled sector model (locked decision:
# the sliders are trained features, not decoration).
METRIC_FIELDS = ("ebitda_margin", "roe", "roa", "current_ratio")


@lru_cache(maxsize=256)
def _metric_model(sector_id: str, field: str,
                  exclude_key: tuple[str, ...] = ()) -> Ridge | None:
    """Pooled sector model for one v2 metric series (same trend+seasonality
    features as the revenue/margin models). None when the sector has no data
    for the field (banks: ebitda_margin / current_ratio)."""
    X_list, y = [], []
    for c in data.companies_by_sector(sector_id):
        fins = data.financials(c.ticker) or []
        keep = [i for i in _keep_indices(fins, exclude_key)
                if getattr(fins[i], field) is not None]
        if not keep:
            continue
        X_list.append(_features([f.quarter for f in fins], 0)[keep])
        y.extend(getattr(fins[i], field) for i in keep)
    if not X_list:
        return None
    return Ridge(alpha=1.0).fit(np.vstack(X_list), np.array(y))


def _project_metric(company: Company, field: str, horizon: int,
                    exclude: tuple[str, ...], scope: str) -> float | None:
    """Baseline slider value for a v2 metric: the sector-shaped projected
    path re-anchored to the company's own median (the exact pattern the net
    margin baseline uses). None when the metric is n.a. for the company."""
    fins = data.financials(company.ticker) or []
    model = _metric_model(company.sector, field,
                          exclude if scope == "sector" else ())
    keep = [i for i in _keep_indices(fins, exclude)
            if getattr(fins[i], field) is not None]
    if model is None or not keep:
        return None
    company_median = float(np.median([getattr(fins[i], field) for i in keep]))
    hist_feats = _features([f.quarter for f in fins], 0)[keep]
    sector_mean = float(np.mean(model.predict(hist_feats)))
    path = model.predict(_features(PROJ_QUARTERS[:horizon], N_HIST))
    anchored = path * (company_median / sector_mean) if sector_mean else path
    return float(np.mean(anchored))


def project(company: Company, horizon: int = N_PROJ,
            exclude: tuple[str, ...] = (), scope: str = "company") -> list[ProjectedQuarter]:
    """Project the next `horizon` quarters of revenue and net income."""
    fins = data.financials(company.ticker) or []
    rev_model, nm_model = _sector_models(company.sector,
                                         exclude if scope == "sector" else ())
    quarters = PROJ_QUARTERS[:horizon]
    Xf = _features(quarters, N_HIST)

    keep = _keep_indices(fins, exclude)
    revs = np.array([fins[i].revenue for i in keep])
    rel_pred = rev_model.predict(Xf)
    rev_pred = rel_pred * revs.mean()

    # Margin: sector-shaped path re-anchored to the company's own median
    # margin (median resists the embedded anomaly quarters; explicit
    # exclusions remove an incident quarter from the anchor entirely).
    nm_sector = nm_model.predict(Xf)
    company_nm = float(np.median([fins[i].net_margin for i in keep]))
    hist_feats = _features([f.quarter for f in fins], 0)[keep]
    sector_nm_mean = float(np.mean(nm_model.predict(hist_feats)))
    nm_pred = nm_sector * (company_nm / sector_nm_mean) if sector_nm_mean else nm_sector

    return [
        ProjectedQuarter(
            quarter=q,
            revenue=round(float(r), 1),
            net_income=round(float(r * m), 1),
        )
        for q, r, m in zip(quarters, rev_pred, nm_pred)
    ]


def derive_assumptions(company: Company, projected: list[ProjectedQuarter],
                       exclude: tuple[str, ...] = (),
                       scope: str = "company") -> Assumptions:
    """Express the ML projection as the assumption set analysts adjust."""
    fins = data.financials(company.ticker) or []
    keep = _keep_indices(fins, exclude)
    # Anomaly-resistant anchor: median of the last 4 kept actual revenues.
    anchor = float(np.median([fins[i].revenue for i in keep[-4:]]))
    # clamp: a downtrend extrapolation can project revenue <= 0, and a
    # negative base under a fractional power returns a complex number
    end_rev = max(projected[-1].revenue, anchor * 0.01)
    horizon = len(projected)
    annual_growth = (end_rev / anchor) ** (4 / horizon) - 1 if anchor > 0 else 0.0
    margins = [p.net_income / p.revenue for p in projected if p.revenue]
    defaults = SECTOR_DEFAULTS[company.sector]

    # Baseline exit P/E: the company's own median trailing multiple.
    pes = [fins[i].share_price / (fins[i].eps * 4)
           for i in keep if fins[i].eps > 0]
    exit_pe = float(np.clip(np.median(pes), 2.0, 40.0)) if pes else 15.0

    metric = {f: _project_metric(company, f, horizon, exclude, scope)
              for f in METRIC_FIELDS}
    return Assumptions(
        revenue_growth=round(float(np.clip(annual_growth, -0.5, 1.0)), 4),
        net_margin=round(float(np.mean(margins)), 4),
        discount_rate=defaults["discount_rate"],
        terminal_growth=defaults["terminal_growth"],
        horizon_quarters=horizon,
        exit_pe=round(exit_pe, 1),
        exclude_quarters=list(exclude),
        exclude_scope=scope,
        ebitda_margin=round(metric["ebitda_margin"], 4) if metric["ebitda_margin"] else None,
        roe=round(float(np.clip(metric["roe"], 0.005, 0.6)), 4) if metric["roe"] else None,
        roa=round(float(np.clip(metric["roa"], 0.003, 0.4)), 4) if metric["roa"] else None,
        current_ratio=round(metric["current_ratio"], 4) if metric["current_ratio"] else None,
    )


# --------------------------------------------------------------------------
# Fair value: DCF (FCFE proxy) or dividend-discount variant for Islamic banks
# --------------------------------------------------------------------------

def _shares_outstanding(fins: list[QuarterFinancials]) -> float:
    latest = fins[-1]
    return latest.net_income / latest.eps if latest.eps else 0.0


def _bank_terminal_pv(company: Company, fins: list[QuarterFinancials],
                      projected: list[ProjectedQuarter],
                      assumptions: Assumptions, defaults: dict) -> float:
    """Justified-P/B terminal for banks: P/B = (ROE - g) / (r - g) applied
    to the projected terminal book value. ROE is the analyst's slider (or
    the trailing median when unset); g is capped at the sustainable growth
    rate ROE x (1 - payout) — a bank cannot perpetually grow book faster
    than its retention funds."""
    payout = defaults["payout"]
    roe = assumptions.roe
    if roe is None:
        series = [f.roe for f in fins if f.roe is not None and f.roe > 0]
        roe = float(np.median(series)) if series else defaults["discount_rate"]

    r = assumptions.discount_rate
    g = min(assumptions.terminal_growth, max(roe * (1 - payout), 0.0))
    if r <= g:
        g = max(r - 0.005, 0.0)

    equity_latest = fins[-1].equity
    if not equity_latest or equity_latest <= 0:
        equity_latest = 4 * abs(fins[-1].net_income) / roe if roe else 0.0

    # Book compounds quarterly at the retention-funded growth rate.
    g_ret_q = (1 + max(roe * (1 - payout), 0.0)) ** 0.25 - 1
    horizon = len(projected)
    book_terminal = equity_latest * (1 + g_ret_q) ** horizon

    multiple = max((roe - g) / (r - g), 0.0) if r > g else 0.0
    r_q = (1 + r) ** 0.25 - 1
    return book_terminal * multiple / (1 + r_q) ** horizon


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

    # All banks route through the dividend/book-value path (Analyst Model
    # v2): flows are payout x earnings, and the terminal value is a
    # justified P/B on projected book — the correct model for financial
    # institutions, with ROE as the primary driver.
    is_bank = company.sector == "banks"
    method = "ddm_islamic" if company.is_islamic_bank else ("ddm_bank" if is_bank else "dcf")
    sector_conversion = defaults["payout"] if is_bank else defaults["fcf_conversion"]
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

    # Terminal value: exit P/E multiple on annualized post-zakat earnings,
    # justified P/B on projected book value (banks), or Gordon growth on the
    # last quarterly flow (the analyst's choice / the sector's right model).
    if assumptions.terminal_method == "exit_multiple":
        terminal = max(last_ni_after_zakat, 0.0) * 4 * assumptions.exit_pe
        pv_terminal = terminal / (1 + r_q) ** len(projected)
    elif is_bank:
        pv_terminal = _bank_terminal_pv(company, fins, projected, assumptions, defaults)
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

def baseline(company: Company, horizon: int = N_PROJ,
             exclude: tuple[str, ...] = (), scope: str = "company") -> BaselineResponse:
    fins = data.financials(company.ticker) or []
    projected = project(company, horizon, exclude, scope)
    assumptions = derive_assumptions(company, projected, exclude, scope)
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


def _effective(a: Assumptions, b: Assumptions, company: Company) -> Assumptions:
    """Fold the v2 risk levers into the rates fair_value discounts with.

    - ROA below its baseline raises the discount-rate risk premium (asset
      efficiency deteriorating), 15bps per ROA point, capped at ±150bps.
    - A weaker current ratio raises it too (liquidity risk), 100bps per
      1.0x of ratio, capped at ±100bps.
    - ROE feeds the sustainable growth rate g = ROE x (1 - payout): half of
      the ROE delta vs baseline passes into terminal growth (partial
      passthrough — not all retention converts to growth), so the terminal
      value responds in both directions. Banks get the full effect through
      the justified-P/B terminal instead (fair_value reads a.roe directly).

    At a == b every adjustment is zero and the baseline reproduces exactly.
    """
    premium = 0.0
    if a.roa is not None and b.roa is not None:
        premium += float(np.clip(0.15 * (b.roa - a.roa), -0.015, 0.015))
    if a.current_ratio is not None and b.current_ratio is not None:
        premium += float(np.clip(0.01 * (b.current_ratio - a.current_ratio), -0.01, 0.01))
    discount = float(np.clip(a.discount_rate + premium, 0.02, 0.5))

    terminal = a.terminal_growth
    if company.sector != "banks" and a.roe is not None and b.roe is not None:
        payout = SECTOR_DEFAULTS[company.sector]["payout"]
        terminal = a.terminal_growth + 0.5 * (a.roe - b.roe) * (1 - payout)
    terminal = float(np.clip(terminal, 0.0, min(0.10, discount - 0.005)))

    if premium == 0.0 and terminal == a.terminal_growth:
        return a
    return a.model_copy(update={"discount_rate": round(discount, 6),
                                "terminal_growth": round(terminal, 6)})


def analyst_valuation(company: Company, assumptions: Assumptions) -> AnalystValuationResponse:
    """Analyst scenario = baseline series re-shaped by the assumption deltas.

    The analyst revenue path scales the baseline path by the compounding
    ratio of analyst vs baseline growth, and margins scale proportionally.
    With assumptions == baseline assumptions the series (and fair value)
    reproduce the baseline exactly — the delta starts at zero and widens as
    the analyst moves away from it.
    """
    base = baseline(company, assumptions.horizon_quarters,
                    tuple(assumptions.exclude_quarters), assumptions.exclude_scope)
    b, a = base.assumptions, assumptions

    gb_q = (1 + b.revenue_growth) ** 0.25 - 1
    ga_q = (1 + a.revenue_growth) ** 0.25 - 1

    # EBITDA-margin lever (non-banks): an operating-margin point passes
    # through to the earnings basis one-for-one, holding D&A and financing
    # constant. Overlap with the net-margin slider is intentional — the UI
    # warns on inconsistency instead of hard-locking (DuPont overlap).
    em_delta = ((a.ebitda_margin - b.ebitda_margin)
                if a.ebitda_margin is not None and b.ebitda_margin is not None else 0.0)
    eff_margin = a.net_margin + em_delta
    margin_scale = eff_margin / b.net_margin if b.net_margin else 1.0

    projected = []
    for i, p in enumerate(base.projected, start=1):
        ratio = ((1 + ga_q) / (1 + gb_q)) ** i
        rev = p.revenue * ratio
        ni = p.net_income * ratio * margin_scale
        projected.append(ProjectedQuarter(
            quarter=p.quarter, revenue=round(rev, 1), net_income=round(ni, 1)))

    fv, breakdown = fair_value(company, projected, _effective(a, b, company))
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
