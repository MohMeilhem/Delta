# Delta (دلتا) — The Idea

**One line:** an AI research desk for the Saudi stock market that turns hours of
financial-model building into minutes — and makes the *disagreement* between the
analyst and the machine the product.

---

## The problem

Equity analysts covering Tadawul spend most of their time on mechanical work
before any actual thinking happens: pulling quarterly financials, building a
forecast spreadsheet, wiring up a DCF, formatting it — for every single company
they cover. The tools they use (Excel, Bloomberg) are generic, expensive,
English-first, and know nothing about how Saudi finance actually works: zakat
is not a tax, sukuk are not conventional bonds, and an Islamic bank does not
earn "interest income."

## The idea

Delta does the mechanical work instantly, then gets out of the way:

1. **Pick a company** (33 Tadawul companies across 9 sectors).
2. **The machine speaks first** — an ML model trained on sector financials
   draws a baseline forecast of revenue and net income, and derives a fair
   value from it (DCF with an explicit zakat line).
3. **The analyst pushes back** — sliders for revenue growth, margin, discount
   rate and terminal growth reshape the forecast in real time.
4. **The gap between the two lines is "the Delta"** — a shaded band on the
   chart showing exactly where and by how much the analyst disagrees with the
   machine. Fair value, upside and the delta % recalculate live as sliders move.

That gap is the whole point. A number alone ("fair value: 51.45") is not an
argument. *"The machine says 47, I say 55, and here is the quarter where our
views diverge"* — that is an investment thesis you can defend.

Two AI layers wrap around the model:

- **A monitoring agent** scans every company's last 8 quarters with z-score
  anomaly detection the moment you open it, and flags unusual behavior
  (a margin collapse, a debt spike) unprompted — correlated with news when
  possible.
- **An LLM (Claude)** generates the written research: company overview, news
  digest, and structured scenarios — bull case, bear case, and "what would
  break this thesis" — each with a price target and probability. Always
  structured JSON, never free-form chat, always in Arabic (or English).

## Why Saudi-first is the moat (not decoration)

These are built into the engine, not translated on top:

- **Zakat as a real line item** — 2.5% on the zakat base, deducted inside the
  DCF and shown in the valuation breakdown. Not "tax."
- **Islamic banks get their own model** — Al Rajhi, Alinma and Bank Albilad are
  valued with a dividend-discount model on *financing income* (دخل التمويل),
  because "free cash flow to interest income" is meaningless for them.
- **Sukuk flagged separately** from conventional debt in every balance sheet.
- **Arabic is the native tongue** — full RTL layout, Arabic typography
  (Alexandria + IBM Plex Sans Arabic), SAR formatting, with a one-click
  English toggle. Nothing feels like a translation layer.

## What's in the product today

**The valuation deck (the hero):** history + ML baseline + analyst projection
on one chart, the shaded Delta between them, live fair-value readouts,
discounted-PV bars and a live terminal-value readout so *every* slider visibly
moves the picture, and a precision crosshair with axis readouts.

**A real trading view:** candlestick price chart (daily/weekly), moving
averages, support/resistance levels, range brush, trendline and level drawing
tools, trailing performance (1M/3M/6M/1Y, 52-week high/low).

**Analyst toolkit:** valuation sensitivity heatmap (growth × discount rate),
technical-analysis gauge (RSI, SMAs, MACD → buy/sell rating), peer comparison
table, quarterly data table. Advanced assumptions: forecast horizon, cash
conversion, Gordon vs exit-multiple terminal value, and a CAPM builder for the
discount rate.

**Research layer:** AI company overview with leadership profile (CEO, tenure,
experience), financial highlights vs a year ago, strengths/risks, outlook,
news digest with sentiment, and the scenario cards with a bear→bull price
ladder.

**Live market layer:** real Tadawul prices (seed data is pinned to real
closes; a live quote badge shows the current price when online) and a ticker
tape of all 33 companies.

**Two themes** (dark terminal / light office), **two languages**, everywhere.

## How it works (30-second technical tour)

```
React + Vite + TS + Tailwind + Recharts        FastAPI + scikit-learn + Anthropic API
        frontend (:5173)  ── /api proxy ──►    backend (:8000)
                                               │
                                               ├─ valuation.py   Ridge regression per sector
                                               │                 (trend + seasonality) → baseline;
                                               │                 DCF/DDM with zakat; sensitivity
                                               ├─ anomaly.py     z-scores over trailing quarters
                                               ├─ prices.py      daily OHLC + S/R + technicals
                                               ├─ llm.py         Claude, schema-validated JSON,
                                               │                 cached fallbacks if no API key
                                               └─ live.py        real Tadawul quotes (best-effort)
                                               data/ 33 companies × 12 quarters, deterministic
```

Design principles that shaped it: every number is reproducible from the seed
data (no magic numbers); the analyst series is built so the delta is **exactly
zero** until the analyst touches something; and the demo is offline-proof —
every AI feature has a cached fallback, so nothing on stage can break.

## The demo path (2 minutes)

1. Open **Al Rajhi (1120)** — clean company. Overview, live price badge,
   baseline appears. Drag the growth slider: the Delta band opens, fair value
   ticks in real time. Show zakat + sukuk in the breakdown.
2. Toggle **English → Arabic** and **dark → light**. Same product, native both ways.
3. Open **Zain KSA (7030)** — the monitoring agent immediately flags the
   embedded margin collapse, correlated with a news item.
4. Hit **Generate scenarios** — bull/bear/thesis-breaker cards in Arabic with
   price targets on a ladder.

## Running it

Double-click **run.bat** (starts backend on :8000, frontend on :5173, opens
the browser), or `make dev` on machines that have make. Tests: `pytest` in
`backend/` (51 tests). No API key needed — LLM output falls back to cached
Arabic/English copies.

## Where it could go next

Real fundamentals feed (Tadawul/Argaam), portfolio-level view across covered
companies, export to a formatted research-note PDF, alerts when the monitoring
agent fires between sessions, and comparison of analyst accuracy vs the
machine baseline over time.
