"""LLM structured outputs (Anthropic API) — the generative core.

Three features, all returning schema-validated JSON in Arabic or English
(`lang` parameter; field names keep the `_ar` suffix as stable identifiers,
content follows the requested language):
  1. Company overview  (GET  /companies/{t}/overview)
  2. News summary      (GET  /companies/{t}/news-summary)
  3. Scenario cards    (POST /companies/{t}/scenarios)

Reliability contract (per CLAUDE.md):
  - pydantic validation via client.messages.parse (retry once on failure)
  - graceful fallback to /data/llm_fallbacks.json when ANTHROPIC_API_KEY is
    unset or the API fails — the demo must never break offline. Fallback
    templates are .format()-ed with the company's real numbers so even the
    offline path stays tied to the seed data.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from . import data, live_news, valuation
from .models import Company
from .valuation import AnalystValuationResponse, Assumptions

MODEL = "claude-sonnet-4-6"
FALLBACKS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "llm_fallbacks.json"

Lang = Literal["ar", "en"]


# --------------------------------------------------------------------------
# Schemas (field names are stable identifiers; content follows `lang`)
# --------------------------------------------------------------------------

class CompanyOverview(BaseModel):
    overview_ar: str = Field(description="3-sentence company overview")
    ceo_note_ar: str = Field(default="", description="1-2 sentences on the CEO and leadership")
    outlook_ar: str = Field(default="", description="2-3 sentence forward-looking analyst view")
    strengths_ar: list[str] = Field(min_length=3, max_length=3)
    risks_ar: list[str] = Field(min_length=3, max_length=3)
    source: str = "llm"  # "llm" | "fallback"


class NewsItemSentiment(BaseModel):
    headline: str
    sentiment: Literal["إيجابي", "محايد", "سلبي"]  # canonical enum; UI translates


class NewsSummary(BaseModel):
    summary_ar: str
    items: list[NewsItemSentiment]
    source: str = "llm"


class Scenario(BaseModel):
    title_ar: str
    points_ar: list[str] = Field(min_length=3, max_length=3)
    target_price: float | None = None
    probability_pct: int | None = Field(default=None, ge=0, le=100)


class ScenarioSet(BaseModel):
    bull: Scenario       # optimistic case
    bear: Scenario       # pessimistic case
    thesis_breakers: Scenario  # what would invalidate the thesis
    monitoring_ar: list[str] = Field(default_factory=list, max_length=4,
                                     description="Concrete indicators to watch each quarter")
    source: str = "llm"


# --------------------------------------------------------------------------
# Anthropic client (lazy; None when no key so the fallback path is used)
# --------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _client():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    import anthropic

    return anthropic.Anthropic()


def _parse_with_retry(prompt: str, schema: type[BaseModel]) -> BaseModel | None:
    """Call the API with pydantic-validated output; one retry, then None."""
    client = _client()
    if client is None:
        return None
    for attempt in range(2):  # initial attempt + one retry on invalid output
        try:
            response = client.messages.parse(
                model=MODEL,
                max_tokens=2500,
                temperature=0.2,  # research notes must stay factual, not creative
                messages=[{"role": "user", "content": prompt}],
                output_format=schema,
            )
            if response.parsed_output is not None:
                return response.parsed_output
        except Exception as exc:  # log, then fall back — the demo must not break
            print(f"[llm] {schema.__name__} attempt {attempt + 1} failed: {exc}")
            continue
    return None


# --------------------------------------------------------------------------
# Fallbacks
# --------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _fallbacks() -> dict:
    return json.loads(FALLBACKS_PATH.read_text(encoding="utf-8"))


def _fallback_entry(feature: str, ticker: str, lang: Lang) -> dict:
    section = _fallbacks()[feature]
    if lang == "en":
        return section["_default_en"]
    return section.get(ticker, section["_default"])


# --------------------------------------------------------------------------
# Daily summary cache: one LLM call per (ticker, lang) per news snapshot.
# Keyed by a hash of the headlines, so a new day's news invalidates it and
# unchanged news costs nothing. Disk-persisted to survive --reload restarts.
# --------------------------------------------------------------------------

SUMMARY_CACHE_PATH = FALLBACKS_PATH.parent / "summary_cache.json"
_summary_lock = threading.Lock()
_summary_cache: dict[str, dict] | None = None


def _summary_cache_load() -> dict[str, dict]:
    global _summary_cache
    if _summary_cache is None:
        try:
            _summary_cache = json.loads(
                SUMMARY_CACHE_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _summary_cache = {}
    return _summary_cache


def _summary_cache_get(key: str, news_key: str) -> dict | None:
    with _summary_lock:
        entry = _summary_cache_load().get(key)
        if entry and entry["news_key"] == news_key:
            return entry["summary"]
        return None


def _summary_cache_put(key: str, news_key: str, summary: dict) -> None:
    with _summary_lock:
        cache = _summary_cache_load()
        cache[key] = {"news_key": news_key, "summary": summary}
        try:
            SUMMARY_CACHE_PATH.write_text(
                json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
        except OSError:
            pass  # in-process cache still works


def _fmt_context(c: Company) -> dict:
    fins = data.financials(c.ticker) or []
    latest = fins[-1]
    year_ago = fins[-5] if len(fins) >= 5 else None
    yoy = (latest.revenue / year_ago.revenue - 1) * 100 if year_ago else 0.0
    ni_yoy = (
        (latest.net_income / year_ago.net_income - 1) * 100
        if year_ago and year_ago.net_income else 0.0
    )
    margin_pp = (latest.net_margin - year_ago.net_margin) * 100 if year_ago else 0.0
    return {
        "name": c.name_ar,
        "name_en": c.name_en,
        "sector_ar": next(s.name_ar for s in data.sectors() if s.id == c.sector),
        "sector_en": next(s.name_en for s in data.sectors() if s.id == c.sector),
        "quarter": latest.quarter,
        "revenue": f"{latest.revenue:,.0f}",
        "net_income": f"{latest.net_income:,.0f}",
        "net_margin": f"{latest.net_margin * 100:.1f}",
        "yoy_growth": f"{yoy:+.1f}",
        "ni_yoy_growth": f"{ni_yoy:+.1f}",
        "margin_change_pp": f"{margin_pp:+.1f}",
        "eps": f"{latest.eps:,.2f}",
        "fcf": f"{latest.free_cash_flow:,.0f}",
        "income_label": "دخل التمويل" if c.is_islamic_bank else "الإيرادات",
        "income_label_en": "financing income" if c.is_islamic_bank else "revenue",
        "ceo": c.ceo_ar,
        "ceo_en": c.ceo_en,
        "ceo_since": c.ceo_since,
        "ceo_exp": c.ceo_experience_years,
        "founded": c.founded,
        "employees": f"{c.employees:,}" if c.employees is not None else "undisclosed",
        "hq": c.hq_ar,
        "hq_en": c.hq_en,
    }


# --------------------------------------------------------------------------
# 1. Company overview (the research note)
# --------------------------------------------------------------------------

def generate_overview(ticker: str, lang: Lang = "ar") -> CompanyOverview:
    c = data.company(ticker)
    assert c is not None
    ctx = _fmt_context(c)

    lang_line = (
        "اكتب بالعربية الفصحى فقط." if lang == "ar" else "Write in professional English only."
    )
    prompt = f"""You are an equity research analyst covering the Saudi Exchange (Tadawul). {lang_line}

Company: {c.name_ar} / {c.name_en} ({c.ticker}), sector {ctx['sector_en']}
Profile: {c.description_ar}
CEO: {c.ceo_en} ({c.ceo_ar}), appointed {c.ceo_since}, {c.ceo_experience_years} years of industry experience.
Founded {c.founded}, {'~' + ctx['employees'] + ' employees' if c.employees is not None else 'employee count not publicly disclosed'}, HQ {c.hq_en}.
Latest quarter ({ctx['quarter']}):
- {ctx['income_label_en']}: SAR {ctx['revenue']}m ({ctx['yoy_growth']}% YoY)
- net income: SAR {ctx['net_income']}m ({ctx['ni_yoy_growth']}% YoY)
- net margin: {ctx['net_margin']}% ({ctx['margin_change_pp']} pp YoY)
- EPS: SAR {ctx['eps']}, free cash flow: SAR {ctx['fcf']}m
{'Islamic bank: use financing-income terminology, never interest.' if c.is_islamic_bank else ('Conventional (non-Islamic) bank: never describe it as an Islamic bank or fully Sharia-compliant.' if c.sector == 'banks' else '')}

Accuracy rules (strict):
- Cite only the facts and figures listed above, and attribute every number to
  its exact metric (revenue growth is not net income growth; employee count is
  not customer count).
- Do not add numbers, rankings, market share, or superlative claims
  (e.g. "largest in the world") that are not stated above. If the data above
  cannot support a claim, omit the claim.
- If the data above is genuinely insufficient for a whole section, write
  {'"لا تتوفر معلومات مؤكدة حول هذا البند."' if lang == 'ar' else '"No verified information is available on this item."'}
  for that section instead of inventing content.

Return: overview_ar = exactly 3 sentences on the business and its position;
ceo_note_ar = 1-2 sentences on the CEO, tenure and track record;
outlook_ar = 2-3 sentence forward-looking analyst view for the next 12 months
(growth drivers, margin direction, what would change the picture);
strengths_ar = 3 concrete strengths; risks_ar = 3 concrete risks.
Tie points to the numbers above where possible."""

    result = _parse_with_retry(prompt, CompanyOverview)
    if result is not None:
        result.source = "llm"
        return result

    entry = _fallback_entry("overview", ticker, lang)
    ceo_tpl = entry.get("ceo_note_ar") or (
        "يقود الشركة {ceo} منذ عام {ceo_since} بخبرة تتجاوز {ceo_exp} عاماً في القطاع."
        if lang == "ar"
        else "The company is led by {ceo_en}, CEO since {ceo_since}, with over {ceo_exp} years in the industry."
    )
    outlook_tpl = entry.get("outlook_ar") or (
        "نتوقع استمرار مسار النمو الحالي ({yoy_growth}٪ سنوياً) خلال الاثني عشر شهراً المقبلة "
        "مع بقاء هامش صافي الربح قرب {net_margin}٪. يبقى العامل الحاسم قدرة الإدارة على "
        "الحفاظ على الهوامش في ظل المنافسة، وأي انحراف عن هذا المسار يستدعي مراجعة الفرضيات."
        if lang == "ar"
        else "We expect the current growth path ({yoy_growth}% YoY) to persist over the next "
        "twelve months with net margin holding near {net_margin}%. The swing factor is "
        "management's ability to defend margins against competition; a break from this "
        "path would warrant revisiting the assumptions."
    )
    return CompanyOverview(
        overview_ar=entry["overview_ar"].format(**ctx),
        ceo_note_ar=ceo_tpl.format(**ctx),
        outlook_ar=outlook_tpl.format(**ctx),
        strengths_ar=[s.format(**ctx) for s in entry["strengths_ar"]],
        risks_ar=[r.format(**ctx) for r in entry["risks_ar"]],
        source="fallback",
    )


# --------------------------------------------------------------------------
# 2. News summary
# --------------------------------------------------------------------------

def summarize_news(ticker: str, lang: Lang = "ar") -> NewsSummary:
    c = data.company(ticker)
    assert c is not None
    live_items = live_news.company_news(c)
    items = live_items or data.news(ticker) or []

    # News changes once a day, so one LLM call per (ticker, lang, headlines
    # snapshot) is enough; the cache invalidates itself when headlines change.
    news_key = hashlib.md5(
        "|".join(i.headline for i in items).encode()).hexdigest()
    cached = _summary_cache_get(f"{ticker}:{lang}", news_key)
    if cached is not None:
        return NewsSummary(**cached)

    news_block = "\n".join(
        f"- [{i.date}] {i.headline}: {i.body} (المصدر: {i.source})" for i in items
    )
    lang_line = (
        "لخّص بالعربية في فقرة واحدة." if lang == "ar" else "Summarize in one English paragraph."
    )
    prompt = f"""You are an equity analyst. {lang_line}
Then classify each item's likely impact on the stock as one of exactly:
"إيجابي" (positive), "محايد" (neutral), "سلبي" (negative).
Repeat each headline verbatim in the headline field — the headline text only,
never append the source or date to it.

News for {c.name_ar} / {c.name_en}:
{news_block}"""

    result = _parse_with_retry(prompt, NewsSummary)
    if result is not None:
        result.source = "llm"
        _summary_cache_put(f"{ticker}:{lang}", news_key, result.model_dump())
        return result

    # Fallback: curated summary if available, else heuristic sentiment.
    # The curated text describes the seed stories, so it only applies when
    # live news wasn't fetched — live headlines get the generic summary line.
    section = _fallbacks()["news_summary"]
    entry = section.get(ticker) if lang == "ar" and live_items is None else None
    negative_hints = ["خسائر", "انخفاض", "ضغوط", "السالب", "تراجع"]
    positive_hints = ["نمو", "توزيع أرباح", "شراكة", "رفع السعر", "افتتح", "قفز", "مكسب", "توسع", "ذروة", "تدعم"]

    def classify(headline: str) -> str:
        if any(h in headline for h in negative_hints):
            return "سلبي"
        if any(h in headline for h in positive_hints):
            return "إيجابي"
        return "محايد"

    if entry:
        summary = entry["summary_ar"]
    elif lang == "ar":
        summary = (
            f"تتوزع آخر أخبار {c.name_ar} بين النتائج المالية الدورية وأنشطة التوسع، "
            f"مع بقاء النبرة العامة للأخبار متوازنة خلال الفترة الأخيرة."
        )
    else:
        summary = (
            f"Recent coverage of {c.name_en} spans routine earnings news and expansion "
            f"activity, with an overall balanced tone across the period. Headlines are "
            f"shown in their original Arabic as published."
        )
    return NewsSummary(
        summary_ar=summary,
        items=[NewsItemSentiment(headline=i.headline, sentiment=classify(i.headline))
               for i in items],
        source="fallback",
    )


# --------------------------------------------------------------------------
# 3. Scenario generator (bull / bear / thesis-breakers + monitoring)
# --------------------------------------------------------------------------

TITLES = {
    "ar": {"bull": "السيناريو المتفائل", "bear": "السيناريو المتشائم", "tb": "ما قد يُبطل الفرضية"},
    "en": {"bull": "Bull case", "bear": "Bear case", "tb": "What breaks the thesis"},
}


def _probabilities(delta_pct: float) -> tuple[int, int]:
    """Deterministic heuristic: the further the analyst strays from the
    machine baseline, the less probability the optimistic tail gets."""
    stretch = min(abs(delta_pct) / 10, 3)  # 0..3
    bull = round(35 - 4 * stretch)
    bear = round(25 + 3 * stretch)
    return bull, bear


def generate_scenarios(ticker: str, assumptions: Assumptions, lang: Lang = "ar") -> ScenarioSet:
    c = data.company(ticker)
    assert c is not None
    val: AnalystValuationResponse = valuation.analyst_valuation(c, assumptions)
    base = valuation.baseline(c)
    targets = valuation.scenario_targets(c, assumptions)
    bull_p, bear_p = _probabilities(val.delta_pct)

    nums = {
        "name": c.name_ar,
        "name_en": c.name_en,
        "baseline_fv": f"{val.baseline_fair_value:,.2f}",
        "analyst_fv": f"{val.fair_value:,.2f}",
        "delta_pct": f"{val.delta_pct:+.1f}",
        "price": f"{val.current_price:,.2f}",
        "upside": f"{val.upside_pct:+.1f}",
        "growth": f"{assumptions.revenue_growth * 100:.1f}",
        "base_growth": f"{base.assumptions.revenue_growth * 100:.1f}",
        "margin": f"{assumptions.net_margin * 100:.1f}",
        "base_margin": f"{base.assumptions.net_margin * 100:.1f}",
        "discount": f"{assumptions.discount_rate * 100:.1f}",
        "terminal": f"{assumptions.terminal_growth * 100:.1f}",
        "bull_target": f"{targets['bull_target']:,.2f}",
        "bear_target": f"{targets['bear_target']:,.2f}",
    }

    lang_line = "اكتب كل النصوص بالعربية." if lang == "ar" else "Write all text in English."
    t = TITLES[lang]
    prompt = f"""You are a Tadawul equity analyst. {lang_line}
Comparison between the machine baseline and the analyst's assumptions for {c.name_ar} / {c.name_en} ({c.ticker}):

- Revenue growth: baseline {nums['base_growth']}% vs analyst {nums['growth']}% p.a.
- Net margin: baseline {nums['base_margin']}% vs analyst {nums['margin']}%
- Discount rate {nums['discount']}%, terminal growth {nums['terminal']}%
- Baseline fair value SAR {nums['baseline_fv']}, analyst fair value SAR {nums['analyst_fv']}
- Delta {nums['delta_pct']}%, current price SAR {nums['price']} (gap {nums['upside']}%)
- Mechanical bull target SAR {nums['bull_target']} (growth +3pp, margin +8%)
- Mechanical bear target SAR {nums['bear_target']} (growth -3pp, margin -15%, discount +1pp)

Return three cards, each with exactly 3 concrete points tied to these numbers:
1. bull  (title_ar: "{t['bull']}", target_price {nums['bull_target']}, probability_pct {bull_p})
2. bear  (title_ar: "{t['bear']}", target_price {nums['bear_target']}, probability_pct {bear_p})
3. thesis_breakers (title_ar: "{t['tb']}", no target, no probability)
Plus monitoring_ar: 3-4 concrete quarterly indicators an analyst should track
(specific metrics with thresholds, not generic advice). No generic filler."""

    result = _parse_with_retry(prompt, ScenarioSet)
    if result is not None:
        result.source = "llm"
        result.bull.target_price = targets["bull_target"]
        result.bear.target_price = targets["bear_target"]
        if result.bull.probability_pct is None:
            result.bull.probability_pct = bull_p
        if result.bear.probability_pct is None:
            result.bear.probability_pct = bear_p
        return result

    entry = _fallback_entry("scenarios", ticker, lang)

    def fmt(s: dict, target: float | None, prob: int | None) -> Scenario:
        return Scenario(
            title_ar=s["title_ar"],
            points_ar=[p.format(**nums) for p in s["points_ar"]],
            target_price=target,
            probability_pct=prob,
        )

    return ScenarioSet(
        bull=fmt(entry["bull"], targets["bull_target"], bull_p),
        bear=fmt(entry["bear"], targets["bear_target"], bear_p),
        thesis_breakers=fmt(entry["thesis_breakers"], None, None),
        monitoring_ar=[m.format(**nums) for m in entry.get("monitoring_ar", [])],
        source="fallback",
    )
