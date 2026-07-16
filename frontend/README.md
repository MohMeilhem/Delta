# Delta — Frontend

React + Vite + TypeScript + Tailwind (RTL) + Recharts + motion/react.

## Run it

```bash
npm install
npm run dev        # http://localhost:5173
```

Production build: `npm run build` (output in `dist/`).

## What it expects from the backend

All requests go to `/api/...` and Vite proxies them to `http://localhost:8000`
(see `vite.config.ts`). Start the FastAPI backend on port 8000 and everything
works; without it the UI loads but shows error/loading states.

Key endpoints the UI calls (all JSON):

| Endpoint | Used by |
|---|---|
| `GET /sectors`, `GET /sectors/{id}/companies` | home page |
| `GET /companies/{t}`, `GET /companies/{t}/financials` | company header, tables |
| `GET /companies/{t}/baseline?horizon=` | ML baseline + default assumptions |
| `POST /companies/{t}/valuation` | live revaluation while sliders move |
| `POST /companies/{t}/sensitivity` | heatmap tab |
| `GET /companies/{t}/prices?range=`, `/technicals`, `/peers` | trading view, toolkit |
| `GET /companies/{t}/anomalies`, `/agent-report` | monitoring flags |
| `GET /companies/{t}/overview`, `/news-summary`, `POST /scenarios` (`?lang=ar\|en`) | research layer |
| `GET /companies/{t}/live` | live Tadawul quote badge |
| `GET /market/tape` | ticker tape |

Types for every payload are in `src/api.ts` — treat it as the API contract.

## Where things live

- `src/pages/` — Home (sector/company picker) and CompanyPage (the whole deck)
- `src/components/` — DeltaChart (the hero), PriceChart (candles + drawing),
  AssumptionPanel (sliders + advanced), FairValueCards, Toolkit (4 tabs),
  InsightCards (research/news/scenarios), AgentFlags, LiveQuote, ui (shared)
- `src/i18n.tsx` — every user-facing string, Arabic + English; `src/format.ts`
  — locale-aware number/date formatting (always use these, never hardcode)
- `src/theme.tsx` — dark/light tokens + `useChartColors()` (chart colors must
  be added to BOTH palettes)
- `src/index.css` — design tokens and the `.zone` / `.screen` / `.num` system

## Conventions

- User-facing text in Arabic with an English dictionary twin; code in English.
- Numbers use the `.num` class (tabular, LTR-isolated); hero numerals add `.display`.
- Respect `prefers-reduced-motion` on any new animation.
