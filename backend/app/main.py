from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import anomaly, chat, data, live, llm, prices, signals, valuation
from .anomaly import AgentReport
from .chat import ChatReply, ChatRequest
from .llm import CompanyOverview, Lang, NewsSummary, ScenarioSet
from .models import PeerRow, TapeEntry, SubscriptionRequest, SubscriptionResponse
from .valuation import SensitivityResponse
from .models import Company, CompanyProfile, NewsItem, QuarterFinancials, Sector
from .valuation import AnalystValuationResponse, Assumptions, BaselineResponse

app = FastAPI(title="Delta — Tadawul Equity Research API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "delta-backend"}


@app.get("/sectors", response_model=list[Sector])
def list_sectors() -> list[Sector]:
    return data.sectors()


@app.get("/sectors/{sector_id}/companies", response_model=list[Company])
def list_sector_companies(sector_id: str) -> list[Company]:
    if sector_id not in {s.id for s in data.sectors()}:
        raise HTTPException(404, f"unknown sector: {sector_id}")
    return data.companies_by_sector(sector_id)


@app.post("/subscribe", response_model=SubscriptionResponse)
def subscribe(payload: SubscriptionRequest) -> SubscriptionResponse:
    email = payload.email.lower()
    existing = next((row for row in data.subscribers() if row.get("email", "").lower() == email), None)
    if existing:
        return SubscriptionResponse(
            status="duplicate",
            message="هذا البريد مسجل بالفعل، وسنتواصل معك عبر الطلب السابق.",
        )

    data.append_subscriber(
        {
            "name": payload.name,
            "email": email,
            "company": payload.company,
        },
    )
    return SubscriptionResponse(
        status="created",
        message="تم استلام طلبك بنجاح. سنرسل لك تفاصيل الوصول المبكر قريباً.",
    )


def _company_or_404(ticker: str) -> Company:
    c = data.company(ticker)
    if c is None:
        raise HTTPException(404, f"unknown ticker: {ticker}")
    return c


@app.get("/market/tape", response_model=list[TapeEntry])
def market_tape() -> list[TapeEntry]:
    """Latest price + QoQ move for every listed company (the ticker tape)."""
    entries = []
    for c in data.companies():
        fins = data.financials(c.ticker) or []
        if len(fins) < 2:
            continue
        last, prev = fins[-1].share_price, fins[-2].share_price
        entries.append(TapeEntry(
            ticker=c.ticker,
            name_ar=c.name_ar,
            name_en=c.name_en,
            price=last,
            change_pct=round((last / prev - 1) * 100, 2) if prev else 0.0,
        ))
    return entries


@app.get("/companies/{ticker}", response_model=CompanyProfile)
def company_profile(ticker: str) -> CompanyProfile:
    c = _company_or_404(ticker)
    fins = data.financials(ticker)
    assert fins, f"no financials for {ticker}"
    latest = fins[-1]
    shares = latest.net_income / latest.eps if latest.eps else 0.0
    annual_eps = latest.eps * 4
    years = (len(fins) - 1) / 4
    cagr = (fins[-1].revenue / fins[0].revenue) ** (1 / years) - 1 if years and fins[0].revenue > 0 else 0.0
    return CompanyProfile(
        **c.model_dump(),
        latest=latest,
        market_cap=round(latest.share_price * shares, 1),
        pe_ratio=round(latest.share_price / annual_eps, 1) if annual_eps > 0 else 0.0,
        revenue_cagr_3y=round(cagr, 4),
    )


@app.get("/companies/{ticker}/financials", response_model=list[QuarterFinancials])
def company_financials(ticker: str) -> list[QuarterFinancials]:
    _company_or_404(ticker)
    return data.financials(ticker) or []


@app.get("/companies/{ticker}/news", response_model=list[NewsItem])
def company_news(ticker: str) -> list[NewsItem]:
    _company_or_404(ticker)
    return data.news(ticker) or []


@app.get("/companies/{ticker}/baseline", response_model=BaselineResponse)
def company_baseline(ticker: str, horizon: int = 8) -> BaselineResponse:
    return valuation.baseline(_company_or_404(ticker), max(4, min(12, horizon)))


@app.post("/companies/{ticker}/valuation", response_model=AnalystValuationResponse)
def company_valuation(ticker: str, assumptions: Assumptions) -> AnalystValuationResponse:
    return valuation.analyst_valuation(_company_or_404(ticker), assumptions)


@app.get("/companies/{ticker}/agent-report", response_model=AgentReport)
def company_agent_report(ticker: str) -> AgentReport:
    _company_or_404(ticker)
    return anomaly.agent_report(ticker)


@app.get("/companies/{ticker}/prices", response_model=prices.PriceSeries)
def company_prices(ticker: str, range: prices.Range = "6m") -> prices.PriceSeries:
    """Daily/weekly OHLC candles + trailing performance + support/resistance."""
    _company_or_404(ticker)
    return prices.price_series(ticker, range)


@app.get("/companies/{ticker}/live", response_model=live.LiveQuote)
def company_live_quote(ticker: str) -> live.LiveQuote:
    """Real Tadawul quote: SAHMK -> yfinance -> static seed, in that order.

    `source` on the response says which layer actually served it
    ("sahmk" | "yfinance" | "cache"); {available: false} only if all three
    fail (never happens in practice — the static seed is always present).
    """
    _company_or_404(ticker)
    return live.live_quote(ticker)


@app.get("/market/summary", response_model=live.MarketSummary)
def market_summary() -> live.MarketSummary:
    """TASI index + breadth (SAHMK only; {available: false} offline — there
    is no yfinance/static fallback for market-wide data)."""
    return live.market_summary()


@app.get("/health/data-sources")
def data_sources_health() -> dict:
    """Which layer is currently serving live quotes / market summary."""
    return live.health()


@app.get("/anomalies/{ticker}", response_model=signals.SignalsResponse)
def company_signals(ticker: str) -> signals.SignalsResponse:
    """Price/volume/fundamental Z-score flags, from yfinance only (never
    SAHMK) — see signals.py for the source-separation rationale."""
    _company_or_404(ticker)
    return signals.detect_signals(ticker)


@app.get("/anomalies/{ticker}/series", response_model=signals.SeriesResponse)
def company_signal_series(ticker: str) -> signals.SeriesResponse:
    """Rolling mean/+-2.5-sigma price band for chart shading; see
    signals.signal_series's docstring for the full frontend marker/color
    contract (amber #F4A93D medium, red #E5484D high, reserved chart colors
    #4C6FFF/#FF7A45/#FFD166 must not be reused for anomaly elements)."""
    _company_or_404(ticker)
    return signals.signal_series(ticker)


@app.get("/companies/{ticker}/technicals", response_model=prices.Technicals)
def company_technicals(ticker: str) -> prices.Technicals:
    """Indicator battery (SMA/RSI/MACD) with an aggregate buy/sell rating."""
    _company_or_404(ticker)
    return prices.technicals(ticker)


@app.post("/companies/{ticker}/sensitivity", response_model=SensitivityResponse)
def company_sensitivity(ticker: str, assumptions: Assumptions) -> SensitivityResponse:
    return valuation.sensitivity(_company_or_404(ticker), assumptions)


@app.get("/companies/{ticker}/peers", response_model=list[PeerRow])
def company_peers(ticker: str) -> list[PeerRow]:
    """Sector peer comparison: valuation and quality metrics side by side."""
    c = _company_or_404(ticker)
    rows = []
    for peer in data.companies_by_sector(c.sector):
        fins = data.financials(peer.ticker) or []
        latest = fins[-1]
        base = valuation.baseline(peer)
        annual_eps = latest.eps * 4
        yoy = (latest.revenue / fins[-5].revenue - 1) if len(fins) >= 5 else 0.0
        rows.append(PeerRow(
            ticker=peer.ticker,
            name_ar=peer.name_ar,
            name_en=peer.name_en,
            price=latest.share_price,
            fair_value=base.fair_value,
            upside_pct=base.upside_pct,
            pe_ratio=round(latest.share_price / annual_eps, 1) if annual_eps > 0 else 0.0,
            net_margin=latest.net_margin,
            revenue_yoy=round(yoy, 4),
            is_self=peer.ticker == c.ticker,
        ))
    rows.sort(key=lambda r: -r.upside_pct)
    return rows


@app.get("/companies/{ticker}/overview", response_model=CompanyOverview)
def company_overview(ticker: str, lang: Lang = "ar") -> CompanyOverview:
    _company_or_404(ticker)
    return llm.generate_overview(ticker, lang)


@app.get("/companies/{ticker}/news-summary", response_model=NewsSummary)
def company_news_summary(ticker: str, lang: Lang = "ar") -> NewsSummary:
    _company_or_404(ticker)
    return llm.summarize_news(ticker, lang)


@app.post("/companies/{ticker}/scenarios", response_model=ScenarioSet)
def company_scenarios(ticker: str, assumptions: Assumptions, lang: Lang = "ar") -> ScenarioSet:
    _company_or_404(ticker)
    return llm.generate_scenarios(ticker, assumptions, lang)


@app.post("/companies/{ticker}/chat", response_model=ChatReply)
def company_chat(ticker: str, req: ChatRequest) -> ChatReply:
    """Analyst chat agent grounded in the company's data room (LLM with
    rule-based offline fallback)."""
    return chat.respond(_company_or_404(ticker), req)
