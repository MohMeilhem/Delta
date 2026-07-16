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

from pydantic import BaseModel

from . import data
from .models import Company

Z_THRESHOLD = 2.0
Z_HIGH = 3.0
TRAILING = 8
# Static demo dataset — "today" is pinned to just after the latest quarter.
AS_OF = date(2026, 7, 4)
NEWS_RECENCY_DAYS = 10

METRIC_LABELS_AR = {
    "revenue_growth": "نمو الإيرادات",
    "net_margin": "هامش صافي الربح",
    "free_cash_flow": "التدفق النقدي الحر",
}


class AnomalyFlag(BaseModel):
    metric: str
    metric_label_ar: str
    z_score: float
    severity: str  # "high" | "medium"
    direction: str  # "up" | "down"
    latest_value: float
    trailing_mean: float
    explanation_ar: str


class NewsContext(BaseModel):
    headline: str
    date: str
    source: str


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


def detect_anomalies(ticker: str) -> list[AnomalyFlag]:
    company = data.company(ticker)
    fins = data.financials(ticker) or []
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


def agent_report(ticker: str) -> AgentReport:
    """The monitoring agent: everything that runs when a company is opened."""
    company = data.company(ticker)
    assert company is not None
    fins = data.financials(ticker) or []
    flags = detect_anomalies(ticker)

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
