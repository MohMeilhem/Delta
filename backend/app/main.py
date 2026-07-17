from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import anomaly, chat, data, live, live_news, llm, prices, signals, valuation
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
    # Also require financials: a company listed without seed quarters would
    # otherwise 500 deep inside profile/valuation/prices instead of 404 here.
    if c is None or not data.financials(ticker):
        raise HTTPException(404, f"unknown ticker: {ticker}")
    return c


@app.get("/market/tape", response_model=list[TapeEntry])
def market_tape() -> list[TapeEntry]:
    """Latest price + daily move for every listed company (the ticker tape).

    Prices come from the display-only live layer (batched yfinance, 60s
    server cache); companies without live data fall back to the seed
    dataset's quarter-over-quarter move, tagged source="cache".
    """
    companies = data.companies()
    quotes = live.tape_quotes([c.ticker for c in companies])
    entries = []
    for c in companies:
        q = quotes.get(c.ticker)
        if not q or not q.available or q.price is None:
            continue
        entries.append(TapeEntry(
            ticker=c.ticker,
            name_ar=c.name_ar,
            name_en=c.name_en,
            price=q.price,
            change_pct=q.change_pct or 0.0,
            source=q.source,
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
    """Live headlines (Bing News RSS, daily cache) with seed-news fallback."""
    c = _company_or_404(ticker)
    return live_news.company_news(c) or data.news(ticker) or []


def _parse_exclude(exclude: str) -> tuple[str, ...]:
    """Comma-separated quarter labels ('2026Q2,2025Q4') -> tuple."""
    return tuple(q.strip() for q in exclude.split(",") if q.strip())


@app.get("/companies/{ticker}/baseline", response_model=BaselineResponse)
def company_baseline(ticker: str, horizon: int = 8, exclude: str = "",
                     exclude_scope: str = "company") -> BaselineResponse:
    """`exclude` drops incident quarters from the fit (gapped trend index);
    scope "sector" also removes them from the pooled sector training set."""
    scope = exclude_scope if exclude_scope in ("company", "sector") else "company"
    return valuation.baseline(_company_or_404(ticker), max(4, min(12, horizon)),
                              _parse_exclude(exclude), scope)


@app.post("/companies/{ticker}/valuation", response_model=AnalystValuationResponse)
def company_valuation(ticker: str, assumptions: Assumptions) -> AnalystValuationResponse:
    """Engine math runs on seed data only; the display overlay adds the live
    market price so the gap shown here matches the tape/header/peers."""
    v = valuation.analyst_valuation(_company_or_404(ticker), assumptions)
    q = live.live_quote(ticker)  # 5s cache; SAHMK/yfinance/seed chain
    price = q.price if q.available and q.price else v.current_price
    v.market_price = round(price, 2)
    v.market_upside_pct = round((v.fair_value / price - 1) * 100, 1) if price else v.upside_pct
    v.price_source = q.source if q.available and q.price else "cache"
    return v


@app.get("/companies/{ticker}/agent-report", response_model=AgentReport)
def company_agent_report(ticker: str, exclude: str = "") -> AgentReport:
    """Excluded quarters leave the z-score baseline too — one exclusion set
    serves both the projection and the anomaly window."""
    _company_or_404(ticker)
    return anomaly.agent_report(ticker, _parse_exclude(exclude))


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
    """Sector peer comparison: valuation and quality metrics side by side.

    Fair value always comes from the seed-data valuation engine; the price
    column (and the gap/P-E derived from it) uses the same live display
    layer as the ticker tape, so both show identical numbers on screen.
    """
    c = _company_or_404(ticker)
    peers = data.companies_by_sector(c.sector)
    quotes = live.tape_quotes([p.ticker for p in peers])
    rows = []
    for peer in peers:
        fins = data.financials(peer.ticker) or []
        if not fins:
            continue  # never 500 the whole table over one bad seed entry
        latest = fins[-1]
        base = valuation.baseline(peer)
        q = quotes.get(peer.ticker)
        price = q.price if q and q.available and q.price else latest.share_price
        source = q.source if q and q.available and q.price else "cache"
        annual_eps = latest.eps * 4
        yoy = (latest.revenue / fins[-5].revenue - 1) if len(fins) >= 5 else 0.0
        rows.append(PeerRow(
            ticker=peer.ticker,
            name_ar=peer.name_ar,
            name_en=peer.name_en,
            price=price,
            fair_value=base.fair_value,
            upside_pct=round((base.fair_value / price - 1) * 100, 1) if price else 0.0,
            pe_ratio=round(price / annual_eps, 1) if annual_eps > 0 else 0.0,
            net_margin=latest.net_margin,
            revenue_yoy=round(yoy, 4),
            is_self=peer.ticker == c.ticker,
            source=source,
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
