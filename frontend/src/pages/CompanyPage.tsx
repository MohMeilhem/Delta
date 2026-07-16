import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { CaretLeft, CaretRight } from '@phosphor-icons/react'
import { api } from '../api'
import type {
  AnalystValuation,
  Assumptions,
  BaselineResponse,
  CompanyProfile,
  QuarterFinancials,
} from '../api'
import AgentFlags from '../components/AgentFlags'
import AnalystChat from '../components/AnalystChat'
import AssumptionPanel from '../components/AssumptionPanel'
import DeltaChart, { type Metric } from '../components/DeltaChart'
import FairValueCards from '../components/FairValueCards'
import PriceChart from '../components/PriceChart'
import { NewsSummaryCard, ResearchReport, ScenarioSection } from '../components/InsightCards'
import LiveQuote from '../components/LiveQuote'
import Toolkit from '../components/Toolkit'
import { ErrorNote, NumberTicker, Skeleton } from '../components/ui'
import { fmt, fmtInt, fmtMillions, fmtPct } from '../format'
import { useLang } from '../i18n'
import { useChartColors } from '../theme'

export default function CompanyPage() {
  const { ticker = '' } = useParams()
  const { t, dir, lang, name } = useLang()
  const cc = useChartColors()
  const Caret = dir === 'rtl' ? CaretLeft : CaretRight

  const [profile, setProfile] = useState<CompanyProfile | null>(null)
  const [history, setHistory] = useState<QuarterFinancials[] | null>(null)
  const [baseline, setBaseline] = useState<BaselineResponse | null>(null)
  const [assumptions, setAssumptions] = useState<Assumptions | null>(null)
  const [valuation, setValuation] = useState<AnalystValuation | null>(null)
  const [metric, setMetric] = useState<Metric | 'price'>(() => {
    // ?tab=price|revenue deep-links a chart tab (demos, screenshots)
    const q = new URLSearchParams(window.location.search).get('tab')
    return q === 'price' || q === 'revenue' ? q : 'net_income'
  })
  const [loadError, setLoadError] = useState(false)

  // ---- initial load ----
  useEffect(() => {
    let live = true
    setProfile(null)
    setHistory(null)
    setBaseline(null)
    setAssumptions(null)
    setValuation(null)
    setLoadError(false)
    Promise.all([api.company(ticker), api.financials(ticker), api.baseline(ticker)])
      .then(([p, h, b]) => {
        if (!live) return
        setProfile(p)
        setHistory(h)
        setBaseline(b)
        setAssumptions(b.assumptions)
      })
      .catch(() => live && setLoadError(true))
    return () => {
      live = false
    }
  }, [ticker])

  // ---- horizon or exclusion changed: the baseline must be re-projected
  // (excluded quarters leave the fit; the ML re-fits on normalized history) ----
  useEffect(() => {
    if (!assumptions || !baseline) return
    const b = baseline.assumptions
    if (
      assumptions.horizon_quarters === b.horizon_quarters &&
      assumptions.exclude_quarters.join(',') === b.exclude_quarters.join(',') &&
      assumptions.exclude_scope === b.exclude_scope
    )
      return
    let live = true
    api
      .baseline(ticker, assumptions.horizon_quarters, assumptions.exclude_quarters, assumptions.exclude_scope)
      .then((nb) => {
        if (live) setBaseline(nb)
      })
    return () => {
      live = false
    }
  }, [assumptions, baseline, ticker])

  const excludeQuarter = useCallback((quarter: string) => {
    setAssumptions((a) =>
      a && !a.exclude_quarters.includes(quarter)
        ? { ...a, exclude_quarters: [...a.exclude_quarters, quarter] }
        : a,
    )
  }, [])

  // ---- debounced live revaluation while sliders move ----
  const requestSeq = useRef(0)
  useEffect(() => {
    if (!assumptions || !baseline) return
    const seq = ++requestSeq.current
    const timer = setTimeout(async () => {
      try {
        const v = await api.valuation(ticker, assumptions)
        if (seq === requestSeq.current) setValuation(v)
      } catch {
        /* keep last good valuation */
      }
    }, 200)
    return () => clearTimeout(timer)
  }, [assumptions, baseline, ticker])

  const dirty = useMemo(() => {
    if (!assumptions || !baseline) return false
    const b = baseline.assumptions
    return (Object.keys(assumptions) as (keyof Assumptions)[]).some((k) => {
      const av = assumptions[k]
      const bv = b[k]
      if (typeof av === 'number' && typeof bv === 'number') return Math.abs(av - bv) > 1e-9
      if (Array.isArray(av) && Array.isArray(bv)) return av.join(',') !== bv.join(',')
      return av !== bv
    })
  }, [assumptions, baseline])

  const reset = useCallback(() => {
    if (baseline) setAssumptions(baseline.assumptions)
  }, [baseline])

  const incomeLabel = baseline
    ? lang === 'ar'
      ? baseline.income_label_ar
      : baseline.is_islamic_bank
        ? 'Financing income'
        : 'Revenue'
    : ''

  if (loadError) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-16">
        <ErrorNote retry={() => window.location.reload()} />
        <Link
          to="/app"
          className="mt-4 inline-flex items-center gap-1 text-sm text-accent hover:underline"
        >
          {t.backToApp}
          <Caret size={13} weight="bold" />
        </Link>
      </main>
    )
  }

  return (
    <main className="relative pb-12 pt-8 overflow-hidden">
      {/* Ambient orbs */}
      <div className="pointer-events-none absolute inset-0 z-0 overflow-hidden" aria-hidden>
        <div className="orb orb-green" style={{ opacity: 0.5 }} />
        <div className="orb orb-amber" style={{ opacity: 0.4 }} />
        <div className="orb orb-purple" style={{ opacity: 0.3 }} />
      </div>

      {/* ---- header: open ground above the deck ---- */}
      <header className="relative z-10 mx-auto max-w-7xl px-6 pb-7">
        <nav className="mb-4 flex items-center gap-2 text-xs text-ink-faint">
          <Link to="/app" className="transition-colors hover:text-ink">
            {t.appLink}
          </Link>
          <Caret size={10} weight="bold" />
          <span className="text-ink-muted">{profile ? name(profile) : ticker}</span>
        </nav>

        {!profile ? (
          <div className="space-y-3">
            <Skeleton className="h-9 w-72" />
            <Skeleton className="h-8 w-64 rounded-full" />
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="flex flex-wrap items-baseline gap-3">
                  <h1 className="display hero-gradient-text text-3xl font-bold tracking-tight leading-[1.3]">{name(profile)}</h1>
                  <span className="num rounded-lg bg-surface-2 px-2 py-0.5 text-sm text-ink-muted">
                    {profile.ticker}
                  </span>
                  {profile.is_islamic_bank && (
                    <span className="rounded-full border border-accent-dim px-2.5 py-0.5 text-xs text-accent">
                      {t.islamicBank}
                    </span>
                  )}
                  {profile.has_sukuk && (
                    <span className="rounded-full border border-line px-2.5 py-0.5 text-xs text-ink-muted">
                      {t.sukuk}
                    </span>
                  )}
                </div>
                <div className="mt-3">
                  <AgentFlags
                    ticker={ticker}
                    exclude={assumptions?.exclude_quarters ?? []}
                    onExclude={excludeQuarter}
                  />
                </div>
              </div>
              <div className="text-end">
                <div className="text-[11px] text-ink-faint">
                  {t.lastPrice} ({profile.latest.quarter})
                </div>
                <div className="mt-0.5 flex items-baseline justify-end gap-1.5">
                  <NumberTicker
                    value={profile.latest.share_price}
                    format={fmt}
                    className="display text-3xl font-semibold"
                  />
                  <span className="text-xs text-ink-faint">{t.sar}</span>
                </div>
                <div className="mt-1.5 flex justify-end">
                  <LiveQuote ticker={ticker} />
                </div>
              </div>
            </div>

            {/* key ratios strip */}
            <div className="mt-5 flex flex-wrap gap-x-10 gap-y-2">
              <Ratio label={t.marketCap} value={fmtMillions(profile.market_cap)} />
              <Ratio label={t.peRatio} value={`${fmt(profile.pe_ratio)}x`} />
              <Ratio label={t.revCagr} value={fmtPct(profile.revenue_cagr_3y * 100, true)} />
              <Ratio label={t.employees} value={fmtInt(profile.employees)} />
              <Ratio label={t.founded} value={String(profile.founded)} />
            </div>
          </>
        )}
      </header>

      {/* ---- valuation deck: one tonal band holding chart, rail and readout ---- */}
      <section className="zone relative z-10">
        <div className="mx-auto grid max-w-7xl grid-cols-1 gap-8 px-6 py-7 xl:grid-cols-[1fr_320px]">
          <div>
          <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-sm font-semibold text-ink-muted">
              {baseline
                ? metric === 'price'
                  ? `${t.priceTab} (${t.sar})`
                  : `${metric === 'net_income' ? t.netIncome : incomeLabel}: ${t.chartTitle}`
                : t.valuation}
            </h2>
            {baseline && history && (
              <div className="flex flex-wrap items-center gap-4">
                <div className="flex rounded-lg border border-line p-0.5 text-xs" role="tablist">
                  {(
                    [
                      ['net_income', t.netIncome],
                      ['revenue', incomeLabel],
                      ['price', t.priceTab],
                    ] as [Metric | 'price', string][]
                  ).map(([m, label]) => (
                    <button
                      key={m}
                      role="tab"
                      aria-selected={metric === m}
                      onClick={() => setMetric(m)}
                      className={`btn px-2.5 py-1 ${
                        metric === m ? 'bg-surface-2 text-ink' : 'text-ink-faint hover:text-ink'
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                {metric !== 'price' && (
                  <div className="hidden items-center gap-4 text-[11px] text-ink-muted lg:flex">
                    <LegendItem swatch="line" color={cc.ink} label={t.actual} />
                    <LegendItem swatch="line" color={cc.baseline} label={t.baseline} />
                    <LegendItem swatch="dash" color={cc.analyst} label={t.analystProj} />
                    <LegendItem swatch="band" color={cc.analystBandTop} label={t.delta} />
                    {metric === 'net_income' && (
                      <LegendItem swatch="bar" color={cc.analyst} label={t.pvDiscounted} />
                    )}
                  </div>
                )}
              </div>
            )}
          </header>
          {!history || !baseline ? (
            <Skeleton className="h-105 w-full" />
          ) : metric === 'price' ? (
            <PriceChart ticker={ticker} />
          ) : (
            <DeltaChart
              history={history}
              baseline={baseline.projected}
              analyst={valuation?.projected ?? null}
              metric={metric}
              pvSeries={(valuation ?? baseline).breakdown.pv_series}
              pvTerminal={(valuation ?? baseline).breakdown.pv_terminal}
            />
          )}
        </div>

        <aside className="border-line max-xl:border-t max-xl:pt-6 xl:border-s xl:ps-8">
          {!baseline || !assumptions ? (
            <div className="space-y-5">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i}>
                  <Skeleton className="mb-2 h-3.5 w-32" />
                  <Skeleton className="h-1.5 w-full rounded-full" />
                </div>
              ))}
            </div>
          ) : (
            <AssumptionPanel
              value={assumptions}
              baseline={baseline.assumptions}
              incomeLabel={incomeLabel}
              isIslamic={baseline.is_islamic_bank}
              latest={history?.at(-1) ?? null}
              onChange={setAssumptions}
              onReset={reset}
              dirty={dirty}
            />
          )}
        </aside>
        </div>

        {/* fair value readout: the deck's bottom instrument row */}
        <div className="border-t border-line">
          <div className="mx-auto max-w-7xl px-6">
            {!baseline ? (
              <div className="py-4">
                <Skeleton className="h-24 w-full" />
              </div>
            ) : (
              <FairValueCards baseline={baseline} valuation={valuation} />
            )}
          </div>
        </div>
      </section>

      {/* ---- analyst toolkit: open ground between the two zones ---- */}
      {assumptions && history && (
        <section className="relative z-10 mx-auto max-w-7xl px-6 py-9">
          <Toolkit ticker={ticker} assumptions={assumptions} history={history} />
        </section>
      )}

      {/* ---- research zone: report + news on one tonal band ---- */}
      <section className="zone relative z-10">
        <div className="mx-auto grid max-w-7xl grid-cols-1 gap-8 px-6 py-9 xl:grid-cols-[3fr_2fr]">
          {profile && history ? (
            <ResearchReport ticker={ticker} profile={profile} history={history} />
          ) : (
            <Skeleton className="h-72 w-full" />
          )}
          <div className="border-line max-xl:border-t max-xl:pt-6 xl:border-s xl:ps-8">
            <NewsSummaryCard ticker={ticker} />
          </div>
        </div>
      </section>

      {assumptions && baseline && (
        <section className="mx-auto max-w-7xl px-6 py-9">
          <ScenarioSection
            ticker={ticker}
            assumptions={assumptions}
            currentPrice={baseline.current_price}
          />
        </section>
      )}

      <AnalystChat ticker={ticker} assumptions={assumptions} onApply={setAssumptions} />
    </main>
  )
}

function Ratio({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] text-ink-faint">{label}</div>
      <div className="num mt-0.5 text-sm font-medium text-ink">{value}</div>
    </div>
  )
}

function LegendItem({
  swatch,
  color,
  label,
}: {
  swatch: 'line' | 'dash' | 'band' | 'bar'
  color: string
  label: string
}) {
  return (
    <span className="flex items-center gap-1.5">
      {swatch === 'bar' ? (
        <span className="flex items-end gap-px">
          <span className="h-1.5 w-1 rounded-[1px]" style={{ background: color, opacity: 0.35 }} />
          <span className="h-2.5 w-1 rounded-[1px]" style={{ background: color, opacity: 0.35 }} />
          <span className="h-2 w-1 rounded-[1px]" style={{ background: color, opacity: 0.35 }} />
        </span>
      ) : swatch === 'band' ? (
        <span className="h-2.5 w-4 rounded-sm" style={{ background: color }} />
      ) : (
        <span
          className="h-0 w-4 border-t-2"
          style={{ borderColor: color, borderStyle: swatch === 'dash' ? 'dashed' : 'solid' }}
        />
      )}
      {label}
    </span>
  )
}
