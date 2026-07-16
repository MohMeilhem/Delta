"""Analyst chat agent — the analyst voices worries, the agent answers with data.

POST /companies/{ticker}/chat takes the full message history plus the
analyst's current slider assumptions, grounds the conversation in the
company's real numbers (financials, baseline vs analyst valuation, anomaly
flags, news), and returns a schema-validated reply — conversational UX on
top of the project's structured-JSON contract, never free-form generation.

Reliability contract (per CLAUDE.md): pydantic-validated output with one
retry, and an offline rule-based fallback that answers the most common
worry topics (margins, growth, debt/sukuk, zakat, valuation, anomalies)
from the seed data when ANTHROPIC_API_KEY is unset or the API fails.
"""

from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, Field

from . import anomaly, data, prices, valuation
from .llm import Lang, _client
from .models import Company
from .valuation import Assumptions

# The chat analyst gets the strongest model — it must reason across history,
# peers, technicals and the valuation model, not just rephrase one number.
# Override with DELTA_CHAT_MODEL (e.g. claude-sonnet-4-6 for cheaper/faster).
CHAT_MODEL = os.environ.get("DELTA_CHAT_MODEL", "claude-opus-4-8")


# --------------------------------------------------------------------------
# Schemas (field names are stable identifiers; content follows `lang`)
# --------------------------------------------------------------------------

class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    messages: list[ChatTurn] = Field(min_length=1, max_length=40)
    assumptions: Assumptions | None = None
    lang: Lang = "ar"


class AssumptionRating(BaseModel):
    """Verdict on one model lever. Direction convention: "aggressive" means
    value-inflating vs the evidence (high growth/margin, low discount),
    "conservative" means value-suppressing."""

    parameter: Literal["revenue_growth", "net_margin", "discount_rate", "terminal_growth"]
    verdict: Literal["conservative", "balanced", "aggressive"]
    note_ar: str = Field(max_length=160,
                         description="One short justification with its anchor number, user's language")


class ChatReply(BaseModel):
    reply_ar: str = Field(description="The analyst's answer, grounded in the data room")
    key_numbers_ar: list[str] = Field(default_factory=list, max_length=6,
                                      description="The specific figures the reply relies on")
    follow_ups_ar: list[str] = Field(default_factory=list, max_length=3,
                                     description="Short next questions the analyst might ask")
    # Report card on the user's current slider values, one entry per lever.
    assumption_ratings: list[AssumptionRating] | None = None
    # Scenario proposal: set when the agent translates a what-if (oil move,
    # rate change, ...) into model inputs. fair value / upside are computed
    # server-side by the valuation engine — never by the LLM.
    proposed_assumptions: Assumptions | None = None
    proposed_label_ar: str | None = None
    proposed_fair_value: float | None = None
    proposed_upside_pct: float | None = None
    source: str = "llm"  # "llm" | "fallback"


class _LLMReply(BaseModel):
    """What the model is asked to produce. The public ChatReply adds the
    server-computed valuation of any proposal, so the LLM can never invent
    a scenario fair value."""

    reply_ar: str = Field(description="The analyst's answer, grounded in the data room")
    key_numbers_ar: list[str] = Field(default_factory=list, max_length=6,
                                      description="The specific figures the reply relies on")
    follow_ups_ar: list[str] = Field(default_factory=list, max_length=3,
                                     description="Short next questions the analyst might ask")
    assumption_ratings: list[AssumptionRating] | None = Field(
        default=None, max_length=4,
        description=("One rating per core lever (growth, margin, discount, terminal). Only when "
                     "the user asks you to rate/evaluate their assumptions, parameters or model."))
    proposed_assumptions: Assumptions | None = Field(
        default=None,
        description=("Complete assumption set implementing the discussed scenario. Only when the "
                     "user asks a what-if / macro scenario or asks to adjust the model; start "
                     "from the current analyst values and change only justified levers."))
    proposed_label_ar: str | None = Field(
        default=None, max_length=80,
        description="Short scenario name in the user's language, e.g. 'سيناريو ارتفاع النفط'")


# UI slider ranges (AssumptionPanel) — proposals are clamped so an applied
# scenario always lands on a reachable slider position. The v2 sliders are
# nullable (None = baseline / n.a. for banks) and clamp only when set.
_UI_RANGES = {
    "revenue_growth": (-0.20, 0.40),
    "net_margin": (0.01, 0.70),
    "discount_rate": (0.05, 0.20),
    "terminal_growth": (0.0, 0.06),
    "exit_pe": (2.0, 40.0),
    "ebitda_margin": (0.02, 0.80),
    "roe": (0.01, 0.50),
    "roa": (0.005, 0.30),
    "current_ratio": (0.5, 4.0),
}


def _clamp_proposal(p: Assumptions) -> Assumptions:
    values = p.model_dump()
    for key, (lo, hi) in _UI_RANGES.items():
        if values.get(key) is not None:
            values[key] = min(max(values[key], lo), hi)
    if values.get("fcf_conversion") is not None:
        values["fcf_conversion"] = min(max(values["fcf_conversion"], 0.2), 1.2)
    return Assumptions(**values)


# --------------------------------------------------------------------------
# Grounding context — everything the agent is allowed to reason from
# --------------------------------------------------------------------------

def _history_table(c: Company) -> str:
    """Full quarterly history so the agent can reason about trends itself."""
    fins = data.financials(c.ticker) or []
    rows = [
        f"| {q.quarter} | {q.revenue:,.0f} | {q.net_income:,.0f} | {q.net_margin * 100:.1f}% "
        f"| {q.free_cash_flow:,.0f} | {q.total_debt:,.0f} | {q.eps:.2f} | {q.share_price:,.2f} |"
        for q in fins
    ]
    header = ("| quarter | revenue (SARm) | net income (SARm) | net margin | FCF (SARm) "
              "| total debt (SARm) | EPS | share price |")
    return "\n".join([header] + rows)


def _peers_table(c: Company) -> str:
    """Sector peer comps: valuation and quality metrics side by side."""
    rows = []
    for peer in data.companies_by_sector(c.sector):
        fins = data.financials(peer.ticker) or []
        if not fins:
            continue
        latest = fins[-1]
        base = valuation.baseline(peer)
        annual_eps = latest.eps * 4
        pe = latest.share_price / annual_eps if annual_eps > 0 else 0.0
        yoy = (latest.revenue / fins[-5].revenue - 1) * 100 if len(fins) >= 5 else 0.0
        marker = " <-- this company" if peer.ticker == c.ticker else ""
        rows.append(
            f"| {peer.name_en} ({peer.ticker}) | {latest.share_price:,.2f} | {base.fair_value:,.2f} "
            f"| {base.upside_pct:+.1f}% | {pe:.1f}x | {latest.net_margin * 100:.1f}% | {yoy:+.1f}% |{marker}"
        )
    header = "| peer | price | baseline fair value | gap | P/E | net margin | rev YoY |"
    return "\n".join([header] + rows)


def _macro_table() -> str:
    """Saudi macro series aligned to the company quarters (best effort)."""
    try:
        m = data.macro()
    except Exception:
        return "not available"
    rows = [
        f"| {r['quarter']} | {r['brent_usd']:.1f} | {r['sama_repo_pct']:.2f}% |"
        for r in m["series"]
    ]
    header = "| quarter | Brent avg (USD/bbl) | SAMA repo rate |"
    notes = "\n".join(f"- {line}" for line in m.get("context_en", []))
    return "\n".join([header] + rows) + ("\n" + notes if notes else "")


def _technicals_block(c: Company) -> str:
    """Indicator battery + 52-week price context (best effort)."""
    try:
        t = prices.technicals(c.ticker)
        s = prices.price_series(c.ticker, "1y").stats
    except Exception:
        return "not available"
    ind = ", ".join(f"{i.name}={i.signal}" for i in t.indicators)
    changes = ", ".join(f"{ch.range}: {ch.change_pct:+.1f}%" for ch in s.changes)
    return (
        f"aggregate rating: {t.rating} (score {t.score:+.2f}) — {ind}\n"
        f"price action: last SAR {s.last:,.2f}; 52w high {s.high_52w:,.2f} ({s.high_52w_date}), "
        f"52w low {s.low_52w:,.2f} ({s.low_52w_date}); trailing moves: {changes}"
    )


def _grounding(c: Company, assumptions: Assumptions | None) -> tuple[str, dict]:
    """System-prompt data room + the raw numbers the fallback engine reuses."""
    fins = data.financials(c.ticker) or []
    latest = fins[-1]
    yoy = (latest.revenue / fins[-5].revenue - 1) * 100 if len(fins) >= 5 else 0.0
    base = valuation.baseline(c)
    a = assumptions or base.assumptions
    val = valuation.analyst_valuation(c, a)
    report = anomaly.agent_report(c.ticker)
    news_items = data.news(c.ticker) or []

    n = {
        "company": c,
        "latest": latest,
        "yoy": yoy,
        "base": base,
        "val": val,
        "assumptions": a,
        "flags": report.flags,
        "news": news_items[:3],
    }

    bd = val.breakdown
    shares = latest.net_income / latest.eps if latest.eps else 0.0
    annual_eps = latest.eps * 4
    pe = latest.share_price / annual_eps if annual_eps > 0 else 0.0

    flags_block = "\n".join(
        f"- {f.metric} z-score {f.z_score:+.1f} ({f.severity}, {f.direction}): {f.explanation_ar}"
        for f in report.flags
    ) or "none — the monitoring agent found no unusual signals over the trailing 8 quarters"
    news_block = "\n".join(
        f"- [{i.date}] {i.headline} ({i.source})" for i in news_items[:5]
    ) or "none"

    block = f"""## Company
{c.name_ar} / {c.name_en} ({c.ticker}), sector {c.sector}. {c.description_ar}
CEO: {c.ceo_en} since {c.ceo_since} ({c.ceo_experience_years}y industry experience). Founded {c.founded}, {f'~{c.employees:,} employees' if c.employees is not None else 'employee count not publicly disclosed'}.
{'Islamic bank: use financing-income terminology, never interest. Valued with a dividend-discount model.' if c.is_islamic_bank else ('Conventional (non-Islamic) bank — never describe it as an Islamic bank. Valued with a zakat-adjusted DCF.' if c.sector == 'banks' else 'Valued with a zakat-adjusted DCF.')}
{'Has sukuk outstanding (tracked separately from conventional debt).' if c.has_sukuk else ''}

## Quarterly history ({'financing income' if c.is_islamic_bank else 'revenue'} basis)
{_history_table(c)}
Latest YoY growth {yoy:+.1f}%. Trailing P/E {pe:.1f}x on annualized EPS {annual_eps:.2f}. Shares outstanding ~{shares:,.0f}m.

## Valuation model (machine baseline vs the analyst's current slider assumptions)
- baseline: growth {base.assumptions.revenue_growth * 100:.1f}%, margin {base.assumptions.net_margin * 100:.1f}%, fair value SAR {val.baseline_fair_value:,.2f}
- analyst:  growth {a.revenue_growth * 100:.1f}%, margin {a.net_margin * 100:.1f}%, discount {a.discount_rate * 100:.1f}%, terminal {a.terminal_growth * 100:.1f}% ({a.terminal_method}), horizon {a.horizon_quarters}q, fair value SAR {val.fair_value:,.2f}
- delta analyst vs baseline: {val.delta_pct:+.1f}% — gap of analyst fair value to market price SAR {val.current_price:,.2f}: {val.upside_pct:+.1f}%
- breakdown ({bd.method}): PV of forecast SAR {bd.pv_forecast:,.0f}m + PV of terminal SAR {bd.pv_terminal:,.0f}m; zakat in forecast SAR {bd.zakat_total:,.0f}m; net debt deducted SAR {bd.total_debt:,.0f}m (sukuk SAR {bd.sukuk_debt:,.0f}m)

## Sector peers (machine baseline for each)
{_peers_table(c)}

## Macro context (Saudi Arabia, same quarters as the financials)
{_macro_table()}

## Technicals & price action
{_technicals_block(c)}

## Anomaly flags (z-score over trailing 8 quarters)
{flags_block}

## Recent news
{news_block}"""
    return block, n


# --------------------------------------------------------------------------
# LLM path
# --------------------------------------------------------------------------

def _llm_reply(c: Company, req: ChatRequest) -> ChatReply | None:
    client = _client()
    if client is None:
        return None
    block, _ = _grounding(c, req.assumptions)
    lang_line = (
        "أجب بالعربية الفصحى فقط." if req.lang == "ar" else "Answer in professional English only."
    )
    system = f"""You are a senior equity research analyst covering the Saudi Exchange (Tadawul), working
alongside an analyst who is building their own valuation model for this stock. The slider
assumptions in the data room are THEIR prediction. Your job is to stress-test that prediction
against the evidence — never to make the investment decision for them. Every company-level
number must trace to the data room below; for macro reasoning you may additionally use general
economic knowledge (see Macro scenarios), but never invent company figures. {lang_line}

The one hard rule — no investment recommendations:
- Never tell the user to buy, sell, hold, enter, exit, or avoid the stock, and never assign a
  rating ("شراء", "احتفاظ", "بيع") — even when asked directly. If asked "هل أشتري؟" or similar,
  do not dodge with generic caution: lay out what the data says for and against their scenario,
  quantify it, and close by making clear the decision is theirs (e.g. "القرار قرارك — لكن هذا
  ما تقوله الأرقام...").
- You DO take positions on analytical claims: whether an assumption is aggressive or
  conservative vs history, whether a margin trend is deteriorating, whether the stock trades
  rich or cheap vs peers and vs the model's fair value. State those plainly — that is analysis,
  not advice.

How you work:
- Anchor on the user's prediction: compare each of their assumptions (growth, margin, discount
  rate, terminal growth) to the trailing history, the machine baseline, and the peers. Say which
  assumptions the data supports, which it strains, and by how much.
- Do the arithmetic yourself: compute trends across the quarterly history (acceleration or
  deceleration, margin trajectory, FCF conversion, debt build-up), compare multiples to peers,
  and quantify what their scenario implies for fair value vs the market price. Show the numbers
  inline.
- Weigh evidence that cuts both ways: if fundamentals and technicals disagree, or the user's
  assumptions diverge from the trailing trend, say so and explain the tension.
- Show both roads: what has to be true for the user's scenario to play out, and what has to be
  true for the opposite — with the slider moves and rough magnitudes that would flip the picture.
- Anomaly flags and news are context — check whether they explain a break in the trend before
  extrapolating it.

Macro scenarios ("what if oil rises?", "what if rates fall?", ...):
- The data room includes a quarterly macro table (Brent, SAMA repo) covering the SAME quarters
  as the financials. Use it quantitatively: line the company's revenue/margin path up against
  the oil and rate path quarter by quarter, note where they moved together or didn't, and base
  your sensitivity estimate on that observed co-movement. Never claim the data room lacks oil
  or rate data.
- Reason through the transmission channel for THIS company's sector explicitly. Channels in the
  Saudi market: oil price → government revenue and spending, Aramco top line, petrochemical
  feedstock economics, banking system liquidity and credit growth, consumer spending;
  SAMA repo (pegged to the Fed) → bank financing margins, DCF discount rates, highly-levered
  utilities and real estate. Say which channel dominates for this company and how strong the
  link is (direct, indirect, weak) — and what the quarter-by-quarter comparison actually shows.
- Then translate the scenario into the model: which sliders move, in which direction, and by a
  modest, defensible magnitude. Anchor magnitudes to the company's own history (e.g. the range
  its growth or margin actually traded in across the quarterly table) — not invented elasticities.
- Populate proposed_assumptions with the COMPLETE assumption set for the scenario: copy the
  analyst's current values and change only the levers the scenario justifies. Set
  proposed_label_ar to a short scenario name. In reply_ar explain each change (from → to) and
  the channel behind it.
- NEVER state the scenario's resulting fair value — the valuation engine computes it from your
  proposal and shows it to the user alongside an "apply" button. You may describe the direction
  ("سترتفع القيمة العادلة").
- Also populate proposed_assumptions when the user directly asks you to adjust the model
  ("ارفع النمو إلى 10٪"). Leave it null for ordinary questions with no scenario to implement.

Rating the user's parameters ("قيّم فرضياتي", "rate my parameters", "ما رأيك في نموذجي"):
- Populate assumption_ratings with one entry per core lever (revenue_growth, net_margin,
  discount_rate, terminal_growth). Verdict direction: "aggressive" = value-inflating vs the
  evidence (growth/margin above what history and peers support, discount below what the risk
  profile warrants); "conservative" = value-suppressing; "balanced" = defensible either way.
- Judge each lever against the quarterly history, the machine baseline, the peer table, and the
  macro context. note_ar = one short sentence naming the anchor number (e.g. "6٪ مقابل نمو
  متحقق 10.6٪ — أقل من نصف الوتيرة الفعلية").
- In reply_ar give the overall read: which levers drive the gap vs the baseline and the market
  price, and which single change would move fair value most. Do not repeat every note verbatim.

Format:
- Simple factual question → 2-3 sentences. Analytical question (valuation, thesis, risk
  assessment) → a structured answer up to ~8 sentences: your read of their prediction first,
  then the evidence, then what would change the picture.
- key_numbers_ar: the specific figures your argument rests on (max 6 short items).
- follow_ups_ar: 2-3 sharp next questions the analyst should investigate, same language.
- Internal research conversation — no legal disclaimers, no boilerplate.
- Do not assume the user's gender: in Arabic use neutral phrasing (e.g. impersonal or plural
  forms) rather than gendered صيغ التذكير/التأنيث.

# Data room
{block}"""
    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    for attempt in range(2):  # initial attempt + one retry on invalid output
        try:
            response = client.messages.parse(
                model=CHAT_MODEL,
                max_tokens=2500,
                system=system,
                messages=messages,
                output_format=_LLMReply,
            )
            if response.parsed_output is not None:
                return _finalize(c, req, response.parsed_output)
        except Exception as exc:  # log, then fall back — the demo must not break
            print(f"[chat] attempt {attempt + 1} failed: {exc}")
            continue
    return None


def _finalize(c: Company, req: ChatRequest, llm: _LLMReply) -> ChatReply:
    """Attach the engine-computed valuation to any scenario proposal, so every
    number shown to the user is reproducible from the seed data."""
    reply = ChatReply(
        reply_ar=llm.reply_ar,
        key_numbers_ar=llm.key_numbers_ar,
        follow_ups_ar=llm.follow_ups_ar,
        assumption_ratings=llm.assumption_ratings,
        source="llm",
    )
    if llm.proposed_assumptions is None:
        return reply
    try:
        proposal = _clamp_proposal(llm.proposed_assumptions)
        current = req.assumptions or valuation.baseline(c).assumptions
        if proposal.model_dump() == current.model_dump():
            return reply  # no-op proposal: nothing to apply
        v = valuation.analyst_valuation(c, proposal)
        reply.proposed_assumptions = proposal
        reply.proposed_label_ar = llm.proposed_label_ar
        reply.proposed_fair_value = round(v.fair_value, 2)
        reply.proposed_upside_pct = round(v.upside_pct, 1)
    except Exception as exc:  # drop a broken proposal, keep the text answer
        print(f"[chat] proposal valuation failed: {exc}")
    return reply


# --------------------------------------------------------------------------
# Offline fallback — keyword-routed answers built from the seed numbers
# --------------------------------------------------------------------------

_TOPIC_HINTS: dict[str, list[str]] = {
    # "rate" first: "قيّم فرضياتي" must not fall into the valuation bucket
    "rate": ["قيّم", "قيم فرض", "فرضيات", "مدخلات", "معايير", "rate my", "assumptions",
             "parameters", "نموذجي"],
    "margin": ["هامش", "ربحية", "تكاليف", "margin", "profitability", "cost"],
    "growth": ["نمو", "إيراد", "مبيعات", "growth", "revenue", "sales", "top line"],
    "debt": ["دين", "ديون", "صكوك", "رافعة", "اقتراض", "debt", "sukuk", "leverage", "borrow"],
    "zakat": ["زكاة", "زكوية", "zakat"],
    "valuation": ["تقييم", "قيمة", "قيمت", "مقيم", "مقيّم", "سعر", "غالي", "رخيص", "مبالغ",
                  "valuation", "value", "price", "expensive", "cheap", "overvalued",
                  "undervalued", "target"],
    "anomaly": ["شذوذ", "غريب", "تحذير", "إنذار", "مراقبة", "anomaly", "flag", "unusual",
                "warning", "red flag"],
}


def _topic(text: str) -> str:
    lowered = text.lower()
    for topic, hints in _TOPIC_HINTS.items():
        if any(h in lowered for h in hints):
            return topic
    return "general"


def _fallback_ratings(a: Assumptions, base, ar: bool) -> list[AssumptionRating]:
    """Rule-based report card vs the machine baseline (offline path)."""
    b = base.assumptions

    def verdict(diff: float, tol: float, higher_inflates: bool) -> str:
        if abs(diff) <= tol:
            return "balanced"
        inflating = diff > 0 if higher_inflates else diff < 0
        return "aggressive" if inflating else "conservative"

    def note(user: float, ref: float, label_ar: str, label_en: str) -> str:
        return (f"{user * 100:.1f}٪ مقابل {ref * 100:.1f}٪ {label_ar}" if ar
                else f"{user * 100:.1f}% vs {ref * 100:.1f}% {label_en}")

    base_lbl = ("للأساس الآلي", "machine baseline")
    return [
        AssumptionRating(parameter="revenue_growth",
                         verdict=verdict(a.revenue_growth - b.revenue_growth, 0.02, True),
                         note_ar=note(a.revenue_growth, b.revenue_growth, *base_lbl)),
        AssumptionRating(parameter="net_margin",
                         verdict=verdict(a.net_margin - b.net_margin, 0.02, True),
                         note_ar=note(a.net_margin, b.net_margin, *base_lbl)),
        AssumptionRating(parameter="discount_rate",
                         verdict=verdict(a.discount_rate - b.discount_rate, 0.01, False),
                         note_ar=note(a.discount_rate, b.discount_rate, *base_lbl)),
        AssumptionRating(parameter="terminal_growth",
                         verdict=verdict(a.terminal_growth - b.terminal_growth, 0.005, True),
                         note_ar=note(a.terminal_growth, b.terminal_growth, *base_lbl)),
    ]


def _fallback_reply(c: Company, req: ChatRequest) -> ChatReply:
    _, n = _grounding(c, req.assumptions)
    latest, val, base, a = n["latest"], n["val"], n["base"], n["assumptions"]
    ar = req.lang == "ar"
    name = c.name_ar if ar else c.name_en
    income = ("دخل التمويل" if c.is_islamic_bank else "الإيرادات") if ar else \
        ("financing income" if c.is_islamic_bank else "revenue")

    last_user = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
    topic = _topic(last_user)

    margin_pct = latest.net_margin * 100
    yoy = n["yoy"]
    sukuk_share = (latest.sukuk_debt / latest.total_debt * 100) if latest.total_debt else 0.0
    flags = n["flags"]

    if topic == "rate":
        ratings = _fallback_ratings(a, base, ar)
        n_off = sum(1 for r in ratings if r.verdict != "balanced")
        reply = (
            f"قارنت فرضياتك للـ{name} بالأساس الآلي: "
            f"{'جميع المدخلات ضمن نطاق متوازن.' if n_off == 0 else f'{n_off} من 4 مدخلات تنحرف عن الأساس.'} "
            f"قيمتك العادلة الناتجة {val.fair_value:,.2f} ر.س مقابل {val.baseline_fair_value:,.2f} ر.س للأساس "
            f"(دلتا {val.delta_pct:+.1f}٪) وسعر السوق {val.current_price:,.2f} ر.س. التفاصيل في البطاقة."
            if ar else
            f"I compared your {name} assumptions to the machine baseline: "
            f"{'all levers sit in a balanced range.' if n_off == 0 else f'{n_off} of 4 levers deviate from the baseline.'} "
            f"Your fair value is SAR {val.fair_value:,.2f} vs SAR {val.baseline_fair_value:,.2f} for the baseline "
            f"(delta {val.delta_pct:+.1f}%) against the SAR {val.current_price:,.2f} market price. Details in the card."
        )
        keys = ([f"قيمتك: {val.fair_value:,.2f}", f"الأساس: {val.baseline_fair_value:,.2f}"] if ar
                else [f"Yours: {val.fair_value:,.2f}", f"Baseline: {val.baseline_fair_value:,.2f}"])
        follow_ups = (
            ["ماذا لو ارتفع سعر النفط؟", "أي مدخل يحرك القيمة العادلة أكثر؟"]
            if ar else
            ["What if oil prices rise?", "Which lever moves fair value most?"]
        )
        return ChatReply(reply_ar=reply, key_numbers_ar=keys, follow_ups_ar=follow_ups,
                         assumption_ratings=ratings, source="fallback")

    if topic == "margin":
        reply = (
            f"هامش صافي الربح لدى {name} بلغ {margin_pct:.1f}٪ في آخر ربع، بينما يفترض نموذجك "
            f"{a.net_margin * 100:.1f}٪ مقابل {base.assumptions.net_margin * 100:.1f}٪ في الأساس الآلي. "
            f"إن كان القلق من ضغط الهوامش فجرّب خفض شريط الهامش وراقب أثره على القيمة العادلة "
            f"({val.fair_value:,.2f} ر.س حالياً)."
            if ar else
            f"{name}'s net margin came in at {margin_pct:.1f}% last quarter; your model assumes "
            f"{a.net_margin * 100:.1f}% vs {base.assumptions.net_margin * 100:.1f}% in the machine baseline. "
            f"If margin pressure is the worry, pull the margin slider down and watch the fair value "
            f"(currently SAR {val.fair_value:,.2f}) react."
        )
        keys = [f"هامش آخر ربع: {margin_pct:.1f}٪", f"هامش النموذج: {a.net_margin * 100:.1f}٪"] if ar else \
            [f"Latest margin: {margin_pct:.1f}%", f"Model margin: {a.net_margin * 100:.1f}%"]
    elif topic == "growth":
        reply = (
            f"نمو {income} السنوي لدى {name} بلغ {yoy:+.1f}٪، ونموذجك يفترض {a.revenue_growth * 100:.1f}٪ "
            f"سنوياً مقابل {base.assumptions.revenue_growth * 100:.1f}٪ في الأساس الآلي. "
            f"إذا كنت تشك في استدامة النمو فخفّض شريط النمو؛ الفجوة الحالية مع السعر {val.upside_pct:+.1f}٪."
            if ar else
            f"{name}'s {income} grew {yoy:+.1f}% YoY, and your model assumes {a.revenue_growth * 100:.1f}% p.a. "
            f"vs {base.assumptions.revenue_growth * 100:.1f}% in the baseline. If you doubt that growth is "
            f"sustainable, ease the growth slider down; the gap to price is currently {val.upside_pct:+.1f}%."
        )
        keys = [f"النمو السنوي: {yoy:+.1f}٪", f"نمو النموذج: {a.revenue_growth * 100:.1f}٪"] if ar else \
            [f"YoY growth: {yoy:+.1f}%", f"Model growth: {a.revenue_growth * 100:.1f}%"]
    elif topic == "debt":
        reply = (
            f"إجمالي دين {name} يبلغ {latest.total_debt:,.0f} مليون ر.س، منها صكوك بنسبة {sukuk_share:.0f}٪ "
            f"({latest.sukuk_debt:,.0f} مليون). الدين يُخصم من قيمة حقوق الملكية في النموذج، "
            f"فإن كان القلق من الرافعة راقب أثر رفع معدل الخصم على القيمة العادلة."
            if ar else
            f"{name} carries SAR {latest.total_debt:,.0f}m of total debt, {sukuk_share:.0f}% of it in sukuk "
            f"(SAR {latest.sukuk_debt:,.0f}m). Debt is netted off equity value in the model — if leverage is "
            f"the worry, test a higher discount rate and watch the fair value."
        )
        keys = [f"إجمالي الدين: {latest.total_debt:,.0f} مليون", f"الصكوك: {latest.sukuk_debt:,.0f} مليون"] if ar else \
            [f"Total debt: SAR {latest.total_debt:,.0f}m", f"Sukuk: SAR {latest.sukuk_debt:,.0f}m"]
    elif topic == "zakat":
        reply = (
            f"مصروف الزكاة لدى {name} بلغ {latest.zakat_expense:,.0f} مليون ر.س في آخر ربع، "
            f"وهو بند مستقل في نموذج التقييم (وعاء زكوي بنسبة 2.5٪) وليس ضريبة عامة، "
            f"لذا فهو محسوب بالفعل ضمن القيمة العادلة ({val.fair_value:,.2f} ر.س)."
            if ar else
            f"{name}'s zakat expense was SAR {latest.zakat_expense:,.0f}m last quarter. It sits as its own "
            f"line in the valuation (2.5% zakat base, not a generic tax), so it is already reflected in the "
            f"fair value of SAR {val.fair_value:,.2f}."
        )
        keys = [f"الزكاة: {latest.zakat_expense:,.0f} مليون ر.س"] if ar else \
            [f"Zakat: SAR {latest.zakat_expense:,.0f}m"]
    elif topic == "valuation":
        rich = val.upside_pct < 0
        reply = (
            f"القيمة العادلة وفق فرضياتك {val.fair_value:,.2f} ر.س مقابل سعر السوق {val.current_price:,.2f} ر.س "
            f"(فجوة {val.upside_pct:+.1f}٪)، والأساس الآلي يقدّرها بـ{val.baseline_fair_value:,.2f} ر.س. "
            + (f"السوق يسعّر السهم أعلى من نموذجك، فإما أن السوق يرى نمواً لا تراه أو أن السهم مكلف فعلاً."
               if rich else
               f"نموذجك يشير إلى قيمة أعلى من السعر الحالي، والدلتا مع الأساس {val.delta_pct:+.1f}٪.")
            if ar else
            f"Your assumptions imply a fair value of SAR {val.fair_value:,.2f} vs the market at "
            f"SAR {val.current_price:,.2f} ({val.upside_pct:+.1f}% gap); the machine baseline says "
            f"SAR {val.baseline_fair_value:,.2f}. "
            + ("The market prices the stock above your model — either it sees growth you don't, or the "
               "stock is genuinely rich." if rich else
               f"Your model sits above the current price, with a {val.delta_pct:+.1f}% delta to the baseline.")
        )
        keys = [f"القيمة العادلة: {val.fair_value:,.2f}", f"السعر: {val.current_price:,.2f}"] if ar else \
            [f"Fair value: SAR {val.fair_value:,.2f}", f"Price: SAR {val.current_price:,.2f}"]
    elif topic == "anomaly" or (topic == "general" and flags):
        if flags:
            f0 = flags[0]
            reply = (
                f"وكيل المراقبة رصد {len(flags)} إشارة غير اعتيادية لدى {name}؛ أبرزها في "
                f"{f0.metric_label_ar} بدرجة انحراف {f0.z_score:+.1f}. {f0.explanation_ar} "
                f"يستحق هذا فحص ما إذا كان حدثاً استثنائياً قبل تعديل الفرضيات."
                if ar else
                f"The monitoring agent flagged {len(flags)} unusual signal(s) for {name}; the sharpest is in "
                f"{f0.metric} with a z-score of {f0.z_score:+.1f}. Worth checking whether it's a one-off "
                f"before you bake it into your assumptions."
            )
            keys = [f"{f0.metric_label_ar}: z {f0.z_score:+.1f}"] if ar else [f"{f0.metric}: z {f0.z_score:+.1f}"]
        else:
            reply = (
                f"لا يرصد وكيل المراقبة أي إشارات غير اعتيادية لدى {name} — "
                f"جميع المقاييس ضمن نطاقها المعتاد عبر آخر ثمانية أرباع."
                if ar else
                f"The monitoring agent sees no unusual signals for {name} — every metric is inside its "
                f"normal range across the trailing eight quarters."
            )
            keys = []
    else:
        reply = (
            f"وضع {name} باختصار: نمو {income} {yoy:+.1f}٪ سنوياً، هامش صافي {margin_pct:.1f}٪، "
            f"وقيمة عادلة وفق فرضياتك {val.fair_value:,.2f} ر.س مقابل سعر {val.current_price:,.2f} ر.س "
            f"(فجوة {val.upside_pct:+.1f}٪). أخبرني ما الذي يقلقك تحديداً — الهوامش، النمو، الدين، أم التقييم؟"
            if ar else
            f"Quick read on {name}: {income} growing {yoy:+.1f}% YoY, net margin {margin_pct:.1f}%, and your "
            f"assumptions imply SAR {val.fair_value:,.2f} vs the market at SAR {val.current_price:,.2f} "
            f"({val.upside_pct:+.1f}% gap). Tell me what worries you specifically — margins, growth, debt, "
            f"or the valuation?"
        )
        keys = [f"النمو: {yoy:+.1f}٪", f"الهامش: {margin_pct:.1f}٪"] if ar else \
            [f"Growth: {yoy:+.1f}%", f"Margin: {margin_pct:.1f}%"]

    follow_ups = (
        ["هل التقييم الحالي مبرر؟", "ماذا عن مستوى الديون؟", "هل هناك إشارات غير اعتيادية؟"]
        if ar else
        ["Is the current valuation justified?", "What about the debt level?", "Any unusual signals?"]
    )
    return ChatReply(reply_ar=reply, key_numbers_ar=keys, follow_ups_ar=follow_ups, source="fallback")


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def respond(c: Company, req: ChatRequest) -> ChatReply:
    return _llm_reply(c, req) or _fallback_reply(c, req)
