"""Z-score anomaly detection + the monitoring agent (وكيل المراقبة).

For each key metric — revenue growth (QoQ), net margin, free cash flow —
the latest quarter is compared against its trailing 8-quarter mean/std.
|z| > 2 flags the metric (medium), |z| > 3 is high severity.

The monitoring agent orchestrates everything that should happen when a
company is opened: run all anomaly checks, correlate with recent news,
and return ONLY items worth an analyst's attention, ranked by severity.
Clean companies return an empty flag list.
"""

from __future__ import annotations

import statistics
from datetime import date, timedelta
from functools import lru_cache

from pydantic import BaseModel

from . import data
from .models import Company

Z_THRESHOLD = 2.0
Z_HIGH = 3.0
TRAILING = 8
# Static demo dataset — "today" is pinned to just after the latest quarter.
AS_OF = date(2026, 7, 4)
NEWS_RECENCY_DAYS = 10
# Cause correlation: news within ±N days of the flagged quarter's end date
# is a candidate explanation (Analyst Model v2, Problem 3).
CAUSE_WINDOW_DAYS = 45

METRIC_LABELS_EN = {
    "revenue_growth": "Revenue growth",
    "net_margin": "Net margin",
    "free_cash_flow": "Free cash flow",
}

METRIC_LABELS_AR = {
    "revenue_growth": "نمو الإيرادات",
    "net_margin": "هامش صافي الربح",
    "free_cash_flow": "التدفق النقدي الحر",
}


class NewsContext(BaseModel):
    headline: str
    date: str
    source: str


class AnomalyFlag(BaseModel):
    metric: str
    metric_label_ar: str
    z_score: float
    severity: str  # "high" | "medium"
    direction: str  # "up" | "down"
    latest_value: float
    trailing_mean: float
    explanation_ar: str  # the statistical read (what broke the pattern)
    # v2 cause-labelling: WHY it broke, grounded in news near the quarter.
    cause_ar: str = ""
    cause_en: str = ""
    cause_confidence: str = "tentative"  # "grounded" | "tentative"
    causal_news: list[NewsContext] = []
    # the quarter an analyst would exclude to normalize the history
    suggested_exclusion: str | None = None


class AgentReport(BaseModel):
    ticker: str
    quarter: str
    flags: list[AnomalyFlag]
    news_context: NewsContext | None
    summary_ar: str


def _z(latest: float, trailing: list[float]) -> float | None:
    if len(trailing) < 4:
        return None
    mean = statistics.mean(trailing)
    std = statistics.stdev(trailing)
    if std == 0:
        return None
    return (latest - mean) / std


def _fmt_pct(x: float) -> str:
    return f"{x * 100:.1f}٪"


def _explain(metric: str, z: float, latest: float, mean: float,
             company: Company) -> str:
    direction_ar = "ارتفاعاً" if z > 0 else "انخفاضاً"
    label = METRIC_LABELS_AR[metric]
    if metric == "revenue_growth":
        income = "دخل التمويل" if company.is_islamic_bank else "الإيرادات"
        return (f"سجل نمو {income} في آخر ربع {direction_ar} حاداً "
                f"({_fmt_pct(latest)} مقابل متوسط {_fmt_pct(mean)} "
                f"في الأرباع الثمانية السابقة) — انحراف معياري {z:+.1f}.")
    if metric == "net_margin":
        return (f"انحرف {label} بشكل غير اعتيادي {direction_ar} "
                f"({_fmt_pct(latest)} مقابل متوسط {_fmt_pct(mean)}) — "
                f"انحراف معياري {z:+.1f}، ما يكسر نمط الأرباع الثمانية الماضية.")
    return (f"شهد {label} {direction_ar} حاداً عن نمطه المعتاد "
            f"({latest:,.0f} مليون ريال مقابل متوسط {mean:,.0f}) — "
            f"انحراف معياري {z:+.1f}.")


def detect_anomalies(ticker: str, exclude: tuple[str, ...] = ()) -> list[AnomalyFlag]:
    """`exclude` drops quarters from the z-score computation entirely — an
    analyst-excluded incident quarter must leave the trailing window too, or
    it would distort the very "normal range" it was excluded from (Analyst
    Model v2, Problem 2). One exclusion set serves projection and anomaly."""
    company = data.company(ticker)
    fins = data.financials(ticker) or []
    if exclude:
        fins = [f for f in fins if f.quarter not in set(exclude)]
    if company is None or len(fins) < TRAILING + 2:
        return []

    flags: list[AnomalyFlag] = []

    # Metric series (aligned to quarters).
    growth = [fins[i].revenue / fins[i - 1].revenue - 1 for i in range(1, len(fins))]
    series = {
        "revenue_growth": growth,
        "net_margin": [f.net_margin for f in fins],
        "free_cash_flow": [f.free_cash_flow for f in fins],
    }

    for metric, values in series.items():
        latest = values[-1]
        trailing = values[-1 - TRAILING:-1]
        z = _z(latest, trailing)
        if z is None or abs(z) <= Z_THRESHOLD:
            continue
        mean = statistics.mean(trailing)
        flags.append(AnomalyFlag(
            metric=metric,
            metric_label_ar=METRIC_LABELS_AR[metric],
            z_score=round(z, 2),
            severity="high" if abs(z) > Z_HIGH else "medium",
            direction="up" if z > 0 else "down",
            latest_value=round(latest, 4),
            trailing_mean=round(mean, 4),
            explanation_ar=_explain(metric, z, latest, mean, company),
        ))

    flags.sort(key=lambda f: (f.severity != "high", -abs(f.z_score)))
    return flags


def _quarter_end(quarter: str) -> date:
    """'2026Q2' -> date(2026, 6, 30)."""
    year, qnum = int(quarter[:4]), int(quarter[-1])
    month = qnum * 3
    last_day = {3: 31, 6: 30, 9: 30, 12: 31}[month]
    return date(year, month, last_day)


def _causal_news(ticker: str, direction: str, quarter: str) -> list[NewsContext]:
    """Candidate causes: news within ±CAUSE_WINDOW_DAYS of the flagged
    quarter's end, ranked by sentiment alignment (negative news should
    explain a drop, positive a spike) then by date proximity. Top 3."""
    from . import llm  # local import: llm pulls valuation; keep startup light

    q_end = _quarter_end(quarter)
    aligned_sentiment = "سلبي" if direction == "down" else "إيجابي"
    scored = []
    for item in data.news(ticker) or []:
        item_date = date.fromisoformat(item.date)
        distance = abs((item_date - q_end).days)
        if distance > CAUSE_WINDOW_DAYS:
            continue
        sentiment = llm.classify_headline_sentiment(item.headline)
        scored.append((0 if sentiment == aligned_sentiment else 1, distance, item))
    scored.sort(key=lambda s: (s[0], s[1]))
    return [NewsContext(headline=i.headline, date=i.date, source=i.source)
            for _, _, i in scored[:3]]


@lru_cache(maxsize=256)
def _cached_explanation(ticker: str, metric: str, quarter: str, direction: str,
                        z_score: float, latest_value: float, trailing_mean: float):
    """The cause of a given (ticker, metric, quarter) flag is stable — cache
    it so opening a company doesn't re-pay LLM latency every time."""
    from . import llm

    company = data.company(ticker)
    assert company is not None
    candidates = _causal_news(ticker, direction, quarter)
    explanation = llm.explain_anomaly(
        company,
        metric_label_en=METRIC_LABELS_EN.get(metric, metric),
        z_score=z_score,
        direction=direction,
        latest_value=latest_value,
        trailing_mean=trailing_mean,
        candidate_news=[n.model_dump() for n in candidates],
    )
    return explanation, candidates


def _attach_causes(company: Company, quarter: str, flags: list[AnomalyFlag]) -> None:
    """Label every flag with a grounded cause + the exclusion suggestion."""
    for f in flags:
        explanation, candidates = _cached_explanation(
            company.ticker, f.metric, quarter, f.direction,
            f.z_score, f.latest_value, f.trailing_mean)
        f.cause_ar = explanation.cause_ar
        f.cause_en = explanation.cause_en
        f.cause_confidence = explanation.confidence
        f.causal_news = candidates
        f.suggested_exclusion = quarter


def agent_report(ticker: str, exclude: tuple[str, ...] = ()) -> AgentReport:
    """The monitoring agent: everything that runs when a company is opened."""
    company = data.company(ticker)
    assert company is not None
    fins = data.financials(ticker) or []
    if exclude:
        fins = [f for f in fins if f.quarter not in set(exclude)] or fins
    flags = detect_anomalies(ticker, exclude)
    if flags and fins:
        _attach_causes(company, fins[-1].quarter, flags)

    # News recency only matters when there is something anomalous to
    # correlate it with — clean companies stay quiet.
    news_context: NewsContext | None = None
    if flags:
        for item in data.news(ticker) or []:
            item_date = date.fromisoformat(item.date)
            if AS_OF - item_date <= timedelta(days=NEWS_RECENCY_DAYS):
                news_context = NewsContext(
                    headline=item.headline, date=item.date, source=item.source)
                break

    if not flags:
        summary = "لا توجد إشارات غير اعتيادية — السلوك المالي ضمن النطاق المعتاد للأرباع الثمانية الماضية."
    else:
        top = flags[0]
        summary = (f"رصد وكيل المراقبة {len(flags)} "
                   f"{'إشارة' if len(flags) == 1 else 'إشارات'} غير اعتيادية، "
                   f"أبرزها في {top.metric_label_ar}.")
        if news_context:
            summary += " توجد أخبار حديثة قد تفسر هذا السلوك."

    return AgentReport(
        ticker=ticker,
        quarter=fins[-1].quarter if fins else "",
        flags=flags,
        news_context=news_context,
        summary_ar=summary,
    )
