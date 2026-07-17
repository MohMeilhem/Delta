import { useEffect, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { Buildings, CaretDown, ChartLineUp, Compass, Sparkle, UserCircle } from '@phosphor-icons/react'
import { api } from '../api'
import type {
  Assumptions,
  CompanyOverview,
  CompanyProfile,
  NewsItem,
  NewsSummary,
  QuarterFinancials,
  ScenarioSet,
} from '../api'
import { fmt, fmtDate, fmtInt, fmtMillions, fmtPct } from '../format'
import { useLang } from '../i18n'
import { EASE, ErrorNote, NumberTicker, Skeleton, spotlightHandlers } from './ui'

function SourceTag({ source }: { source: 'llm' | 'fallback' }) {
  const { t } = useLang()
  return (
    <span className="rounded-full border border-line px-2 py-0.5 text-[10px] text-ink-faint">
      {source === 'llm' ? t.generated : t.cached}
    </span>
  )
}

/* ------------------------------------------------------------------ */
/* Research report: overview + leadership + strengths/risks            */
/* ------------------------------------------------------------------ */

export function ResearchReport({
  ticker,
  profile,
  history,
}: {
  ticker: string
  profile: CompanyProfile
  history: QuarterFinancials[]
}) {
  const [data, setData] = useState<CompanyOverview | null>(null)
  const [error, setError] = useState(false)
  const [tick, retry] = useState(0)
  const { t, lang } = useLang()

  useEffect(() => {
    let live = true
    setData(null)
    setError(false)
    api
      .overview(ticker, lang)
      .then((d) => live && setData(d))
      .catch(() => live && setError(true))
    return () => {
      live = false
    }
  }, [ticker, lang, tick])

  if (error) return <ErrorNote retry={() => retry((n) => n + 1)} />
  if (!data)
    return (
      <div>
        <h2 className="mb-4 text-sm font-semibold text-ink-muted">{t.companyReport}</h2>
        <div className="space-y-2.5">
          <Skeleton className="h-3.5 w-full" />
          <Skeleton className="h-3.5 w-full" />
          <Skeleton className="h-3.5 w-3/4" />
          <Skeleton className="mt-4 h-16 w-full" />
          <div className="grid grid-cols-2 gap-4 pt-2">
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </div>
        </div>
      </div>
    )

  const ceoName = lang === 'ar' ? profile.ceo_ar : profile.ceo_en
  const hq = lang === 'ar' ? profile.hq_ar : profile.hq_en

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3, ease: EASE }}
      className="h-full"
    >
      <section className="h-full">
        <header className="mb-4 flex items-center justify-between gap-3">
          <h2 className="text-sm font-semibold text-ink-muted">{t.companyReport}</h2>
          <SourceTag source={data.source} />
        </header>
        <p className="mb-4 text-sm leading-7 text-ink">{data.overview_ar}</p>

        {lang === 'ar' && (
          <p className="mb-4 border-s-0 text-[13px] leading-6 text-ink-muted">
            <span className="me-2 text-xs font-semibold text-ink-faint">{t.aboutCompany}:</span>
            {profile.description_ar}
          </p>
        )}

        {/* financial highlights: latest quarter vs year ago */}
        <FinancialHighlights history={history} />

        {/* leadership block */}
        <div className="mb-4 rounded-md bg-surface-2/60 p-4">
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
            <span className="flex items-center gap-2.5">
              <UserCircle size={30} weight="duotone" className="text-accent" />
              <span>
                <span className="block text-[10px] text-ink-faint">{t.ceo}</span>
                <span className="display block text-sm font-semibold">{ceoName}</span>
              </span>
            </span>
            <FactPill label={t.ceoSince(profile.ceo_since)} />
            <FactPill label={t.yearsExp(profile.ceo_experience_years)} />
          </div>
          {data.ceo_note_ar && (
            <p className="mt-3 border-t border-line/60 pt-3 text-[13px] leading-6 text-ink-muted">
              {data.ceo_note_ar}
            </p>
          )}
          <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1.5 text-[11px] text-ink-faint">
            <span className="flex items-center gap-1.5">
              <Buildings size={13} />
              {t.founded} <span className="num text-ink-muted">{profile.founded}</span>
            </span>
            <span>
              {t.hq} <span className="text-ink-muted">{hq}</span>
            </span>
            <span>
              <span className="num text-ink-muted">{fmtInt(profile.employees)}</span>{' '}
              {t.employees}
            </span>
            <span className="flex items-center gap-1.5">
              <ChartLineUp size={13} />
              {t.revCagr}{' '}
              <span className="num text-ink-muted">{fmtPct(profile.revenue_cagr_3y * 100, true)}</span>
            </span>
          </div>
        </div>

        <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <PointList heading={t.strengths} points={data.strengths_ar} tone="accent" />
          <PointList heading={t.risks} points={data.risks_ar} tone="negative" />
        </div>

        {/* outlook: the forward-looking analyst view */}
        {data.outlook_ar && (
          <div className="rounded-md bg-analyst/8 p-4">
            <h3 className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-analyst">
              <Compass size={14} weight="bold" />
              {t.outlook}
            </h3>
            <p className="text-[13px] leading-6 text-ink-muted">{data.outlook_ar}</p>
          </div>
        )}
      </section>
    </motion.div>
  )
}

function FinancialHighlights({ history }: { history: QuarterFinancials[] }) {
  const { t } = useLang()
  if (history.length < 5) return null
  const now = history[history.length - 1]
  const ago = history[history.length - 5]
  const pct = (a: number, b: number) => (b ? (a / b - 1) * 100 : 0)
  const rows: { label: string; value: string; delta: number; pp?: boolean }[] = [
    { label: t.revenue, value: fmtMillions(now.revenue), delta: pct(now.revenue, ago.revenue) },
    { label: t.netIncome, value: fmtMillions(now.net_income), delta: pct(now.net_income, ago.net_income) },
    { label: t.margin, value: fmtPct(now.net_margin * 100), delta: (now.net_margin - ago.net_margin) * 100, pp: true },
    { label: t.fcf, value: fmtMillions(now.free_cash_flow), delta: pct(now.free_cash_flow, ago.free_cash_flow) },
    { label: t.eps, value: fmt(now.eps), delta: pct(now.eps, ago.eps) },
  ]
  return (
    <div className="mb-4">
      <h3 className="mb-2 text-xs font-semibold text-ink-faint">{t.highlights}</h3>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        {rows.map((r) => (
          <div key={r.label} className="rounded-md bg-surface-2/50 px-3 py-2.5">
            <div className="text-[10px] leading-tight text-ink-faint">{r.label}</div>
            <div className="num mt-1 text-[13px] font-medium text-ink">{r.value}</div>
            <div className={`num mt-0.5 text-[10px] ${r.delta >= 0 ? 'text-accent' : 'text-negative'}`}>
              {r.pp ? `${r.delta >= 0 ? '+' : ''}${fmt(r.delta)} pp` : fmtPct(r.delta, true)}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function FactPill({ label }: { label: string }) {
  return (
    <span className="rounded-full border border-line px-2.5 py-1 text-[11px] text-ink-muted">
      {label}
    </span>
  )
}

function PointList({
  heading,
  points,
  tone,
}: {
  heading: string
  points: string[]
  tone: 'accent' | 'negative'
}) {
  return (
    <div>
      <h3
        className={`mb-2 text-xs font-semibold ${tone === 'accent' ? 'text-accent' : 'text-negative'}`}
      >
        {heading}
      </h3>
      <ul className="space-y-1.5 text-[13px] leading-6 text-ink-muted">
        {points.map((p) => (
          <li key={p} className="flex gap-2">
            <span className="mt-2.5 h-1 w-1 shrink-0 rounded-full bg-current opacity-60" />
            {p}
          </li>
        ))}
      </ul>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* News digest with sentiment breakdown                                */
/* ------------------------------------------------------------------ */

const SENTIMENT_STYLE: Record<string, string> = {
  إيجابي: 'text-accent border-accent-dim',
  سلبي: 'text-negative border-negative/40',
  محايد: 'text-ink-muted border-line',
}
const SENTIMENT_BAR: Record<string, string> = {
  إيجابي: 'bg-accent',
  محايد: 'bg-line-strong',
  سلبي: 'bg-negative',
}

export function NewsSummaryCard({ ticker }: { ticker: string }) {
  const [data, setData] = useState<NewsSummary | null>(null)
  const [items, setItems] = useState<NewsItem[]>([])
  const [expanded, setExpanded] = useState<string | null>(null)
  const [error, setError] = useState(false)
  const [tick, retry] = useState(0)
  const { t, lang } = useLang()

  useEffect(() => {
    let live = true
    setData(null)
    setExpanded(null)
    setError(false)
    Promise.all([api.newsSummary(ticker, lang), api.news(ticker)])
      .then(([d, n]) => {
        if (!live) return
        setData(d)
        setItems(n)
      })
      .catch(() => live && setError(true))
    return () => {
      live = false
    }
  }, [ticker, lang, tick])

  if (error) return <ErrorNote retry={() => retry((n) => n + 1)} />
  if (!data)
    return (
      <div>
        <h2 className="mb-4 text-sm font-semibold text-ink-muted">{t.newsSummary}</h2>
        <div className="space-y-2.5">
          <Skeleton className="h-3.5 w-full" />
          <Skeleton className="h-3.5 w-5/6" />
          <Skeleton className="mt-3 h-2 w-full rounded-full" />
          <div className="space-y-2 pt-2">
            <Skeleton className="h-8" />
            <Skeleton className="h-8" />
            <Skeleton className="h-8" />
          </div>
        </div>
      </div>
    )

  const counts = { إيجابي: 0, محايد: 0, سلبي: 0 } as Record<string, number>
  data.items.forEach((i) => {
    counts[i.sentiment] += 1
  })
  const total = data.items.length || 1

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3, ease: EASE }}
      className="h-full"
    >
      <section className="h-full">
        <header className="mb-4 flex items-center justify-between gap-3">
          <h2 className="text-sm font-semibold text-ink-muted">{t.newsSummary}</h2>
          <SourceTag source={data.source} />
        </header>
        <p className="mb-4 text-sm leading-7 text-ink">{data.summary_ar}</p>

        {/* sentiment breakdown bar */}
        <div className="mb-4">
          <div className="mb-1.5 flex items-center justify-between text-[10px] text-ink-faint">
            <span>{t.sentimentBreakdown}</span>
            <span className="flex gap-3">
              {(['إيجابي', 'محايد', 'سلبي'] as const).map((s) =>
                counts[s] ? (
                  <span key={s} className="flex items-center gap-1">
                    <span className={`h-1.5 w-1.5 rounded-full ${SENTIMENT_BAR[s]}`} />
                    {t.sentiments[s]} <span className="num">{counts[s]}</span>
                  </span>
                ) : null,
              )}
            </span>
          </div>
          <div className="flex h-1.5 gap-px overflow-hidden rounded-full">
            {(['إيجابي', 'محايد', 'سلبي'] as const).map((s) =>
              counts[s] ? (
                <motion.span
                  key={s}
                  className={SENTIMENT_BAR[s]}
                  initial={{ width: 0 }}
                  animate={{ width: `${(counts[s] / total) * 100}%` }}
                  transition={{ duration: 0.6, ease: EASE, delay: 0.15 }}
                />
              ) : null,
            )}
          </div>
        </div>

        <ul className="divide-y divide-line/60">
          {data.items.map((item, i) => {
            // headline match first; index fallback keeps rows expandable when
            // the summary language differs from the news items' language
            const full = items.find((n) => n.headline === item.headline) ?? items[i]
            const open = expanded === item.headline
            return (
              <li key={item.headline} className="py-2 first:pt-0 last:pb-0">
                <button
                  onClick={() => setExpanded(open ? null : item.headline)}
                  aria-expanded={open}
                  className="flex w-full items-start justify-between gap-3 text-start text-[13px]"
                >
                  <span dir="rtl" className="flex-1 text-start leading-6 text-ink-muted">
                    {item.headline}
                  </span>
                  <span className="flex shrink-0 items-center gap-1.5">
                    <span
                      className={`rounded-full border px-2 py-0.5 text-[11px] ${SENTIMENT_STYLE[item.sentiment]}`}
                    >
                      {t.sentiments[item.sentiment]}
                    </span>
                    {full && (
                      <motion.span
                        animate={{ rotate: open ? 180 : 0 }}
                        transition={{ duration: 0.2, ease: EASE }}
                        className="text-ink-faint"
                      >
                        <CaretDown size={12} weight="bold" />
                      </motion.span>
                    )}
                  </span>
                </button>
                <AnimatePresence initial={false}>
                  {open && full && (
                    <motion.div
                      key="body"
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.25, ease: EASE }}
                      className="overflow-hidden"
                    >
                      <p dir="rtl" className="mt-2 text-[12px] leading-6 text-ink-faint">
                        {full.body}
                      </p>
                      <div className="mt-1.5 text-[10px] text-ink-faint">
                        {full.url ? (
                          <a
                            href={full.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="underline decoration-line hover:text-accent"
                          >
                            {full.source}
                          </a>
                        ) : (
                          full.source
                        )}{' '}
                        · {fmtDate(full.date)}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </li>
            )
          })}
        </ul>
      </section>
    </motion.div>
  )
}

/* ------------------------------------------------------------------ */
/* Scenarios: price ladder + cards + monitoring indicators             */
/* ------------------------------------------------------------------ */

const cardSpring = { type: 'spring' as const, duration: 0.55, bounce: 0.2 }

export function ScenarioSection({
  ticker,
  assumptions,
  currentPrice,
}: {
  ticker: string
  assumptions: Assumptions
  currentPrice: number
}) {
  const [data, setData] = useState<ScenarioSet | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)
  const reduce = useReducedMotion()
  const { t, lang } = useLang()

  // Assumptions or language changed: previous scenarios are stale.
  useEffect(() => {
    setData(null)
    setError(false)
  }, [ticker, assumptions, lang])

  const generate = async () => {
    setLoading(true)
    setError(false)
    try {
      setData(await api.scenarios(ticker, assumptions, lang))
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }

  if (!data) {
    return (
      <div className="flex flex-col items-center gap-4 border-y border-line py-10 text-center">
        <p className="max-w-md text-sm leading-6 text-ink-muted">{t.scenariosHint}</p>
        <button
          onClick={generate}
          disabled={loading}
          className="btn flex items-center gap-2 bg-accent px-5 py-2.5 text-sm font-semibold text-bg hover:opacity-90 disabled:opacity-60"
        >
          <Sparkle size={15} weight="fill" />
          {loading ? t.generating : t.generateScenarios}
        </button>
        {error && <span className="text-xs text-negative">{t.generateFailed}</span>}
      </div>
    )
  }

  const bullT = data.bull.target_price
  const bearT = data.bear.target_price

  const cards = [
    { s: data.bull, tone: 'text-accent' },
    { s: data.bear, tone: 'text-negative' },
    { s: data.thesis_breakers, tone: 'text-warning' },
  ]
  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-ink-muted">{t.scenarios}</h2>
        <div className="flex items-center gap-2">
          <SourceTag source={data.source} />
          <button
            onClick={generate}
            disabled={loading}
            className="btn border border-line px-2.5 py-1 text-xs text-ink-muted hover:bg-surface-2 hover:text-ink disabled:opacity-50"
          >
            {loading ? t.regenShort : t.regenerate}
          </button>
        </div>
      </div>

      {/* price ladder: bear .. current .. bull on one rail */}
      {bullT != null && bearT != null && (
        <PriceLadder bear={bearT} bull={bullT} current={currentPrice} />
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {cards.map(({ s, tone }, i) => (
          <motion.section
            key={s.title_ar}
            initial={reduce ? false : { opacity: 0, y: 16, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ ...cardSpring, delay: i * 0.08 }}
            className="spotlight rounded-md bg-surface-2/50 p-5"
            {...spotlightHandlers()}
          >
            <div className="mb-3 flex items-baseline justify-between gap-2">
              <h3 className={`display text-sm font-bold ${tone}`}>{s.title_ar}</h3>
              {s.probability_pct != null && (
                <span className="num rounded-full bg-surface-2 px-2 py-0.5 text-[10px] text-ink-muted">
                  {fmtPct(s.probability_pct)}
                </span>
              )}
            </div>
            {s.target_price != null && (
              <div className={`mb-3 flex items-baseline gap-1.5 ${tone}`}>
                <NumberTicker
                  value={s.target_price}
                  format={fmt}
                  className="display text-2xl font-semibold"
                />
                <span className="text-[11px] opacity-70">
                  {t.sar} · {t.targetPrice}
                </span>
              </div>
            )}
            <ul className="space-y-2.5 text-[13px] leading-6 text-ink-muted">
              {s.points_ar.map((p, j) => (
                <motion.li
                  key={p}
                  initial={reduce ? false : { opacity: 0, x: 8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.35, delay: 0.15 + i * 0.08 + j * 0.05, ease: EASE }}
                  className="flex gap-2"
                >
                  <span className="mt-2.5 h-1 w-1 shrink-0 rounded-full bg-current opacity-60" />
                  {p}
                </motion.li>
              ))}
            </ul>
          </motion.section>
        ))}
      </div>

      {/* monitoring indicators */}
      {data.monitoring_ar.length > 0 && (
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.35, ease: EASE }}
          className="mt-6 border-t border-line pt-5"
        >
          <h3 className="mb-2.5 text-xs font-semibold text-ink-muted">{t.monitoring}</h3>
          <div className="grid grid-cols-1 gap-x-8 gap-y-2 text-[13px] leading-6 text-ink-muted sm:grid-cols-2">
            {data.monitoring_ar.map((m, i) => (
              <span key={m} className="flex gap-2.5">
                <span className="num mt-px text-[11px] text-accent">{`0${i + 1}`}</span>
                {m}
              </span>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  )
}

function PriceLadder({ bear, bull, current }: { bear: number; bull: number; current: number }) {
  const { t } = useLang()
  const lo = Math.min(bear, current) * 0.94
  const hi = Math.max(bull, current) * 1.06
  const pos = (v: number) => `${((v - lo) / (hi - lo)) * 100}%`

  return (
    <div dir="ltr" className="mb-5 rounded-md bg-surface-2/40 px-6 pb-3 pt-8">
      <div className="relative h-1.5 rounded-full bg-line/60">
        {/* bear→bull span */}
        <motion.div
          className="absolute inset-y-0 rounded-full bg-gradient-to-r from-negative/60 via-line-strong to-accent/70"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          style={{ left: pos(bear), right: `calc(100% - ${pos(bull)})` }}
          transition={{ duration: 0.5 }}
        />
        <LadderPin value={bear} pos={pos(bear)} label={t.bearTarget} tone="text-negative" />
        <LadderPin value={current} pos={pos(current)} label={t.current} tone="text-ink" line />
        <LadderPin value={bull} pos={pos(bull)} label={t.bullTarget} tone="text-accent" />
      </div>
    </div>
  )
}

function LadderPin({
  value,
  pos,
  label,
  tone,
  line,
}: {
  value: number
  pos: string
  label: string
  tone: string
  line?: boolean
}) {
  return (
    <motion.div
      className="absolute -top-7 flex -translate-x-1/2 flex-col items-center"
      style={{ left: pos }}
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.23, 1, 0.32, 1], delay: 0.2 }}
    >
      <span className={`num text-xs font-semibold ${tone}`}>{fmt(value)}</span>
      <span className="whitespace-nowrap text-[9px] text-ink-faint">{label}</span>
      <span
        className={`mt-0.5 ${line ? 'h-4 w-px bg-ink/70' : `h-2 w-2 rounded-full bg-current ${tone}`}`}
      />
    </motion.div>
  )
}
