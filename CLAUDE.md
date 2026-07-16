# Delta (دلتا) — Generative AI Equity Research Platform for Tadawul

## What this project is
A web platform that helps equity analysts in the Saudi stock market (Tadawul) build
financial models faster. Core flow:
1. Analyst picks a sector, then a company (33 seed companies across 9 sectors).
2. Platform shows an auto-generated company overview + summarized latest news.
3. A valuation engine generates an AI **baseline forecast** from historical data.
4. Analyst adjusts assumptions (revenue growth, margins, discount rate, terminal growth).
5. The analyst's forecast is drawn **on top of** the baseline — the gap between them
   (the "Delta") is the core product value. Fair value recalculates live.
6. Z-score anomaly detection + an AI monitoring agent flag unusual financial behavior
   automatically when a company is opened.
7. An LLM generates structured outputs: bull case, bear case, and "what would break
   this thesis" — never free-form chat.

## Saudi-specific differentiators (must be first-class, not decoration)
- Full Arabic UI, RTL layout, Arabic numerals formatting for SAR.
- Islamic banking sector handled with its own model inputs (financing income, not interest).
- Zakat (2.5% zakat base) shown as a line item in valuation, not generic "tax".
- Sukuk flagged separately from conventional debt in company financials.

## Tech stack
- Frontend: React + Vite + TypeScript, Tailwind CSS (RTL), Recharts for charts.
- Backend: Python FastAPI.
- ML baseline: scikit-learn (regression on historical financials per sector).
- Anomaly detection: Z-score over trailing 8 quarters per metric.
- LLM: Anthropic API (structured JSON outputs only). API key from env var `ANTHROPIC_API_KEY`.
- Data: local seed dataset (JSON/CSV) for 33 Tadawul companies, 9 sectors, 8+ quarters
  of financials each. No live API dependency for the demo — everything must run offline
  except the LLM calls, and LLM calls must gracefully fall back to cached sample outputs
  if no API key is set.

## Sectors (9) and example companies
Banks (Al Rajhi, SNB, Alinma), Energy (Aramco), Materials (SABIC, Maaden),
Telecom (stc, Mobily, Zain KSA), Healthcare (Dr. Sulaiman Al Habib, Mouwasat),
Retail (Jarir, eXtra), Utilities (Saudi Electricity, ACWA Power),
Food (Almarai, Savola), Real Estate (Emaar EC, Retal). Fill remaining companies
with realistic Tadawul-listed names to reach 33.

## Conventions
- All user-facing text in Arabic. Code, comments, and identifiers in English.
- Every valuation number must be reproducible from the seed data (no magic numbers).
- LLM outputs must be schema-validated JSON (pydantic). Reject and retry once on invalid.
- Keep the demo runnable with: `make dev` (starts backend on :8000, frontend on :5173).
- Write a smoke test per phase; run tests before declaring a phase done.

## Environment notes (this machine)
- Windows 10, Node at `C:\Program Files\nodejs` (not on default PATH — prefix
  `export PATH="/c/Program Files/nodejs:$PATH"` in bash), Python 3.14 via `python`.
- Backend venv lives at `backend/.venv`.

## Definition of done for the hackathon demo
Sector picker → company page → overview + news summaries → baseline chart →
assumption sliders redraw analyst forecast over baseline in real time →
fair value + delta gap update → anomaly flags appear via the monitoring agent →
"Generate scenarios" button produces bull/bear/thesis-breaker cards in Arabic.
