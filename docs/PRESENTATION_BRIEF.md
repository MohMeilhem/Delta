# Delta (دلتا) — Full Project Description
*Hand-off brief for building the presentation. Everything below is implemented and demoable.*

---

## 1. One-liner

**Delta is a generative-AI equity research platform for the Saudi stock market (Tadawul).** It gives every analyst a machine-generated baseline valuation for a company, lets them adjust the assumptions with sliders, and draws their forecast **on top of** the machine's — the shaded gap between the two lines is "the Delta," the analyst's edge made visible. Fair value recalculates live as they move each slider.

## 2. The problem

Equity analysts covering Tadawul companies spend most of their time on mechanical work: pulling quarterly financials, building the spreadsheet model, writing the company overview, scanning news, and sanity-checking for unusual numbers — before they ever get to the part that's actually their job: **the judgment call**. Existing tools are either global platforms that treat Saudi specifics (zakat, Islamic banking, sukuk) as an afterthought, or raw terminals with no modeling help at all.

## 3. The core idea

Delta doesn't replace the analyst — it makes their disagreement with the machine the product:

1. Analyst picks a **sector**, then a **company** (33 seed companies across 9 sectors, 12 quarters of financials each).
2. The platform instantly shows an **AI-generated company overview** and a **summarized news digest** with per-headline sentiment.
3. A **valuation engine** (per-sector Ridge regression + DCF/DDM) produces a machine **baseline forecast** and fair value.
4. The analyst adjusts assumptions on **7 metric sliders** (revenue growth, net margin, discount rate, terminal growth, EBITDA margin, ROE, ROA, current ratio) plus advanced levers (exit P/E, horizon, a CAPM discount-rate builder).
5. Their forecast redraws **in real time over the baseline** — the shaded band between the lines is the Delta. Fair value, upside vs. market price, and a per-quarter present-value breakdown update live.
6. A **monitoring agent** automatically flags statistical anomalies (z-scores over trailing 8 quarters), explains each one in Arabic, cites the news story that likely caused it, and offers **one-click exclusion** of the distorted quarter — which refits the whole model.
7. A **"Generate scenarios"** button produces structured **bull case / bear case / what-would-break-this-thesis** cards in Arabic, with mechanical price targets computed by the valuation engine (never invented by the LLM).
8. A floating **analyst chat agent** answers questions grounded in the full data room (financials, peers, macro, technicals, news, anomaly flags), can rate the analyst's assumptions lever-by-lever, and propose a scenario — with fair value always computed server-side and applied with one click. It never gives buy/sell advice.

## 4. Saudi-specific differentiators (first-class, not decoration)

- **Full Arabic UI, RTL layout**, Arabic-Indic numeral formatting for SAR. Bilingual (ar/en) with a language toggle; financial axes and tickers stay LTR per market convention.
- **Islamic banks get their own valuation model**: financing income (never "interest") in all terminology including LLM prompts, dividend-discount valuation path, payout-ratio lever instead of cash conversion. Conventional banks get a justified price-to-book terminal value driven by ROE.
- **Zakat is an explicit line item** in the DCF — 2.5% of a zakat base deducted each projected quarter and surfaced in the valuation breakdown, not buried in a generic "tax" row.
- **Sukuk are flagged separately** from conventional debt in company financials, badges, and breakdowns (18 of 33 companies carry sukuk).
- **Live Tadawul data** through a Saudi-licensed provider (SAHMK) with graceful fallbacks.

## 5. Feature inventory

### Valuation engine
- Per-sector **scikit-learn Ridge regressions** (trend + quarterly seasonality) for revenue, net margin, and the four v2 metrics, pooled across sector peers with company-level normalization. A numerically identical **closed-form numpy Ridge fallback** runs where sklearn can't (serverless).
- **DCF over an FCFE proxy** with explicit zakat; Gordon-growth or exit-P/E terminal. Banks route through dividend/book-value models (Islamic vs. conventional variants).
- **Analyst Model v2 levers**: weaker ROA or current ratio raise the discount rate (risk/liquidity premia); ROE feeds terminal growth. At baseline assumptions the analyst line reproduces the machine line exactly — the Delta starts at zero, honestly.
- Every number is **deterministic and reproducible from the seed data** — no magic numbers, no RNG.
- Extras: two-way **sensitivity heatmap** (growth × discount rate), **peer comparison table** sorted by upside, quarterly financials table.

### Monitoring agent (anomaly detection)
- Z-scores on revenue growth, net margin, and FCF vs. an 8-quarter trailing window; |z|>2 medium, |z|>3 high severity.
- Each flag comes with an Arabic explanation, a **grounded or tentative cause** correlated with news within ±45 days, and a **suggested quarter exclusion**. Excluding a quarter removes it from both the regression fit and the z-score window, at company or whole-sector scope.
- A separate English machine-consumable signals feed (price/volume/fundamental z-scores from market data) is kept strictly out of the valuation math — hard source-separation rule.

### Generative layer (Anthropic API)
- **Claude Sonnet** generates the company research note, news digest with sentiment, scenario cards, and anomaly-cause explanations — all as **schema-validated structured JSON (Pydantic)**, with one retry on invalid output. Never free-form generation into the UI.
- **Claude Opus** powers the analyst chat agent, grounded in a full per-company data room.
- **Offline-first**: with no API key, every LLM feature falls back to templates filled with the company's real seed numbers, and the chat falls back to a keyword-routed engine answering from actual financials. Every card shows a source tag (generated vs. cached). LLM news summaries are cached and only regenerate when headlines actually change.

### Live data (all optional — the demo runs fully offline)
- **Quotes**: 3-tier chain — SAHMK (Tadawul-licensed) → yfinance → static seed — with each response tagged by which layer served it, plus a data-sources health endpoint and a market ticker-tape of all 33 companies.
- **News**: Bing News RSS in Arabic, searched by Arabic company name, relevance-filtered, 24-hour cache, degrading gracefully to seed headlines.
- **Price charts**: candlesticks with range tabs, drawing tools (trend lines, levels), SMA/RSI/MACD technicals with an aggregate rating, support/resistance levels.

### Frontend experience
- **Landing page** with an animated hero delta chart and early-access signup; **sector picker** home; and the **company workspace**: header with profile, ratios, Islamic-bank/sukuk badges, live quote, and anomaly chips; the valuation deck (chart + slider rail + fair-value cards); toolkit tabs; research and news zone; scenario section; floating chat.
- **The hero chart**: actuals + solid baseline + dashed analyst line + shaded delta band + per-quarter PV bars + crosshair, built on Recharts.
- Dark "analyst desk" theme (light mode too), OKLCH color tokens with a Tadawul-green accent and amber for the analyst's hand, IBM Plex Sans Arabic typography, motion with reduced-motion support.
- **Installable PWA** with an Arabic RTL manifest and offline caching.

## 6. Tech stack & architecture

| Layer | Choice |
|---|---|
| Frontend | React 19 + Vite + TypeScript, Tailwind CSS v4 (RTL), Recharts, motion, vite-plugin-pwa |
| Backend | Python FastAPI (~25 endpoints) |
| ML baseline | scikit-learn Ridge per sector (numpy closed-form fallback for serverless) |
| Anomaly detection | Z-score over trailing 8 quarters per metric |
| LLM | Anthropic API — Claude Sonnet (research/scenarios), Claude Opus (chat), structured JSON only |
| Data | Local seed dataset: 33 companies, 9 sectors, 12 quarters (2023Q3–2026Q2) incl. sukuk_debt, zakat_expense, and v2 metrics; Saudi macro series (Brent, SAMA repo) |
| Deployment | Vercel serverless (FastAPI mounted under /api) + local `make dev` (backend :8000, frontend :5173) |

**Sectors (9):** Banks, Energy, Materials, Telecom, Healthcare, Retail, Utilities, Food, Real Estate — e.g. Al Rajhi, SNB, Alinma, Aramco, SABIC, Maaden, stc, Mobily, Zain KSA, Dr. Sulaiman Al Habib, Mouwasat, Jarir, eXtra, Saudi Electricity, ACWA Power, Almarai, Savola, Emaar EC, Retal.

## 7. Quality & testing

- **88 backend pytest tests** across API, valuation, anomaly detection, chat grounding, LLM fallbacks, live-data layers, and Analyst Model v2.
- **Playwright E2E smoke suite** (7 tests) driving the real product end-to-end: landing → sector picker → company page → sliders → live fair-value redraw → bank-specific slider behavior → anomaly cause + one-click exclusion → scenario cards. Runs fully offline in Arabic locale.
- Deterministic everywhere: same seed data in, same valuation out.

## 8. Demo flow (definition of done — all working)

1. Landing page → enter app → **sector picker**.
2. Open a company → **overview + news summaries** appear (AI-generated, Arabic).
3. **Baseline chart** renders with fair value.
4. Drag the **assumption sliders** → analyst forecast redraws over the baseline in real time; **fair value + delta gap** update live.
5. **Anomaly flags** appear automatically with explained causes → one-click exclude a distorted quarter → model refits.
6. **"Generate scenarios"** → bull / bear / thesis-breaker cards in Arabic with mechanical price targets.
7. Ask the **chat agent** to rate your assumptions → apply its proposed scenario with one click.
8. Bonus: open an Islamic bank (e.g. Al Rajhi) to show the financing-income model, zakat line, and sukuk badge.

## 9. Suggested presentation narrative

1. **Hook**: analysts spend 80% of their time building the model and 20% on the judgment that actually matters. Delta inverts that.
2. **The Delta concept**: machine baseline vs. analyst conviction, visualized as one shaded gap. The product doesn't hide the AI's opinion or the analyst's — it shows exactly where and by how much they disagree.
3. **Saudi-first**: zakat, Islamic banking models, sukuk, Arabic RTL — built in from the data schema up, not localized after the fact.
4. **Trustworthy AI**: structured outputs only, every number computed by the deterministic engine (the LLM never invents a price target), source tags on every card, graceful offline fallbacks.
5. **Live demo** following the flow in section 8.
6. **Close**: 33 companies, 9 sectors, 88 tests, installable PWA, deployed serverless — a working platform, not a mockup.
