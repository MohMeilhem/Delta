import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion, useReducedMotion } from 'motion/react'
import { api } from '../api'
import type {
  Assumptions,
  PeerRow,
  QuarterFinancials,
  SensitivityResponse,
  Technicals,
} from '../api'
import { fmt, fmtDate, fmtMillions, fmtPct, fmtQuarter } from '../format'
import { useLang } from '../i18n'
import { useChartColors } from '../theme'
import { EASE, Skeleton } from './ui'

type Tab = 'sensitivity' | 'technicals' | 'peers' | 'quarterlies'

export default function Toolkit({
  ticker,
  assumptions,
  history,
}: {
  ticker: string
  assumptions: Assumptions
  history: QuarterFinancials[]
}) {
  const [tab, setTab] = useState<Tab>('sensitivity')
  // panels stay mounted once opened: switching back is instant, no refetch
  const [visited, setVisited] = useState<Set<Tab>>(() => new Set(['sensitivity']))
  const { t } = useLang()
  const reduce = useReducedMotion()

  const open = (id: Tab) => {
    setVisited((v) => (v.has(id) ? v : new Set(v).add(id)))
    setTab(id)
  }

  const tabs: [Tab, string][] = [
    ['sensitivity', t.sensitivity],
    ['technicals', t.technicals],
    ['peers', t.peers],
    ['quarterlies', t.quarterlies],
  ]

  const panels: Record<Tab, React.ReactNode> = {
    sensitivity: <SensitivityHeatmap ticker={ticker} assumptions={assumptions} />,
    technicals: <TechnicalsGauge ticker={ticker} />,
    peers: <PeersTable ticker={ticker} />,
    quarterlies: <QuarterliesTable history={history} />,
  }

  return (
    <div>
      <header className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-ink-muted">{t.toolkit}</h2>
        <div className="flex rounded-lg border border-line p-0.5 text-xs" role="tablist">
          {tabs.map(([id, label]) => (
            <button
              key={id}
              role="tab"
              aria-selected={tab === id}
              onClick={() => open(id)}
              className={`btn px-3 py-1 ${tab === id ? 'bg-surface-2 text-ink' : 'text-ink-faint hover:text-ink'}`}
            >
              {label}
            </button>
          ))}
        </div>
      </header>
      {(Object.keys(panels) as Tab[]).map(
        (id) =>
          visited.has(id) && (
            <motion.div
              key={id}
              role="tabpanel"
              hidden={tab !== id}
              initial={false}
              animate={{ opacity: tab === id ? 1 : 0 }}
              transition={{ duration: reduce ? 0 : 0.18, ease: EASE }}
            >
              {panels[id]}
            </motion.div>
          ),
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Sensitivity heatmap                                                  */
/* ------------------------------------------------------------------ */

function SensitivityHeatmap({ ticker, assumptions }: { ticker: string; assumptions: Assumptions }) {
  const [data, setData] = useState<SensitivityResponse | null>(null)
  const { t } = useLang()
  const cc = useChartColors()
  const reduce = useReducedMotion()

  useEffect(() => {
    let live = true
    setData(null)
    const timer = setTimeout(() => {
      api.sensitivity(ticker, assumptions).then((d) => live && setData(d)).catch(() => {})
    }, 300)
    return () => {
      live = false
      clearTimeout(timer)
    }
  }, [ticker, assumptions])

  if (!data) return <Skeleton className="h-56 w-full" />

  const flat = data.grid.flat()
  const lo = Math.min(...flat)
  const hi = Math.max(...flat)
  const price = data.current_price
  // color: below price → red side, above → green side, scaled by distance
  const cellColor = (v: number) => {
    const rel = (v - price) / price
    const c = Math.min(Math.abs(rel) / 0.5, 1)
    const base = rel >= 0 ? cc.up : cc.down
    return base.replace(')', ` / ${(0.08 + 0.3 * c).toFixed(3)})`)
  }

  return (
    <div>
      <p className="mb-3 text-[11px] text-ink-faint">{t.sensitivityHint}</p>
      <div dir="ltr" className="overflow-x-auto">
        <table className="w-full border-separate border-spacing-0.5 text-center text-xs">
          <thead>
            <tr>
              <th className="num p-1.5 text-[10px] font-normal text-ink-faint">
                {t.growthAxis.replace('←', '↓')} / {t.discountAxis}
              </th>
              {data.discount_steps.map((d) => (
                <th
                  key={d}
                  className={`num p-1.5 text-[10px] font-normal ${Math.abs(d - data.base_discount) < 1e-9 ? 'text-analyst' : 'text-ink-faint'}`}
                >
                  {fmtPct(d * 100)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.grid.map((row, i) => (
              <tr key={i}>
                <th
                  className={`num p-1.5 text-[10px] font-normal ${Math.abs(data.growth_steps[i] - data.base_growth) < 1e-9 ? 'text-analyst' : 'text-ink-faint'}`}
                >
                  {fmtPct(data.growth_steps[i] * 100, true)}
                </th>
                {row.map((v, j) => {
                  const isBase =
                    Math.abs(data.growth_steps[i] - data.base_growth) < 1e-9 &&
                    Math.abs(data.discount_steps[j] - data.base_discount) < 1e-9
                  return (
                    <motion.td
                      key={j}
                      initial={reduce ? false : { opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ duration: 0.3, delay: (i * 5 + j) * 0.015, ease: EASE }}
                      className={`num rounded-md p-2 ${isBase ? 'ring-1 ring-analyst' : ''} ${v >= price ? 'text-accent' : 'text-negative'}`}
                      style={{ background: cellColor(v) }}
                    >
                      {fmt(v)}
                    </motion.td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div dir="ltr" className="mt-2 flex items-center justify-end gap-2 text-[10px] text-ink-faint">
        <span className="num">{fmt(lo)}</span>
        <span className="h-1.5 w-24 rounded-full bg-gradient-to-r from-negative/50 via-surface-2 to-accent/50" />
        <span className="num">{fmt(hi)}</span>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Technical analysis: gauge + indicator battery                        */
/* ------------------------------------------------------------------ */

const SIGNAL_CLS: Record<string, string> = {
  buy: 'border-accent-dim text-accent',
  sell: 'border-negative/40 text-negative',
  neutral: 'border-line text-ink-muted',
}

function TechnicalsGauge({ ticker }: { ticker: string }) {
  const [data, setData] = useState<Technicals | null>(null)
  const { t, dir } = useLang()
  const cc = useChartColors()
  const RATING_COLOR = cc.ratings
  const reduce = useReducedMotion()

  useEffect(() => {
    let live = true
    setData(null)
    api.technicals(ticker).then((d) => live && setData(d)).catch(() => {})
    return () => {
      live = false
    }
  }, [ticker])

  if (!data) return <Skeleton className="h-56 w-full" />

  const angle = data.score * 82 // -82°..82° needle sweep
  const color = RATING_COLOR[data.rating]

  return (
    <div className="grid grid-cols-1 items-center gap-6 lg:grid-cols-[280px_1fr]">
      {/* the gauge */}
      <div className="mx-auto w-64">
        <svg viewBox="0 0 200 118" className="w-full">
          {/* five rating arcs */}
          {[
            ['strong_sell', -90, -54],
            ['sell', -54, -18],
            ['neutral', -18, 18],
            ['buy', 18, 54],
            ['strong_buy', 54, 90],
          ].map(([key, a0, a1]) => (
            <path
              key={key as string}
              d={arcPath(100, 100, 78, a0 as number, a1 as number)}
              fill="none"
              stroke={RATING_COLOR[key as string]}
              strokeOpacity={data.rating === key ? 0.9 : 0.22}
              strokeWidth={11}
              strokeLinecap="butt"
            />
          ))}
          {/* needle: spring-rotates to the score */}
          <motion.g
            initial={reduce ? false : { rotate: -82 }}
            animate={{ rotate: angle }}
            transition={{ type: 'spring', duration: 1.1, bounce: 0.25 }}
            style={{ originX: '100px', originY: '100px' }}
          >
            <line x1="100" y1="100" x2="100" y2="34" stroke={color} strokeWidth="2.5" strokeLinecap="round" />
          </motion.g>
          <circle cx="100" cy="100" r="5" fill={color} />
        </svg>
        <div className="mt-1 text-center">
          <div className="display text-lg font-bold" style={{ color }}>
            {t.techRatings[data.rating]}
          </div>
          <div className="num mt-0.5 text-[10px] text-ink-faint">
            {data.score > 0 ? '+' : ''}
            {data.score} · {fmtDate(data.as_of)}
          </div>
        </div>
      </div>

      {/* indicator battery */}
      <div className="overflow-x-auto" dir={dir}>
        <table className="w-full text-xs">
          <thead>
            <tr className="text-[10px] text-ink-faint">
              <th className="pb-2 pe-4 text-start font-normal">{t.indicator}</th>
              <th className="pb-2 pe-4 text-end font-normal">{t.value}</th>
              <th className="pb-2 pe-4 text-end font-normal">{t.reference}</th>
              <th className="pb-2 text-end font-normal">{t.signal}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line/60">
            {data.indicators.map((ind, i) => (
              <motion.tr
                key={ind.name}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.25, delay: i * 0.05 }}
              >
                <td className="py-2.5 pe-4">{t.techNames[ind.name] ?? ind.name}</td>
                <td className="num py-2.5 pe-4 text-end">{fmt(ind.value)}</td>
                <td className="num py-2.5 pe-4 text-end text-ink-faint">
                  {ind.reference != null ? fmt(ind.reference) : '-'}
                </td>
                <td className="py-2.5 text-end">
                  <span className={`rounded-full border px-2 py-0.5 text-[10px] ${SIGNAL_CLS[ind.signal]}`}>
                    {t.techSignals[ind.signal]}
                  </span>
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function arcPath(cx: number, cy: number, r: number, a0: number, a1: number): string {
  const rad = (a: number) => ((a - 90) * Math.PI) / 180
  const x0 = cx + r * Math.cos(rad(a0))
  const y0 = cy + r * Math.sin(rad(a0))
  const x1 = cx + r * Math.cos(rad(a1))
  const y1 = cy + r * Math.sin(rad(a1))
  return `M ${x0} ${y0} A ${r} ${r} 0 0 1 ${x1} ${y1}`
}

/* ------------------------------------------------------------------ */
/* Peer comparison                                                      */
/* ------------------------------------------------------------------ */

function PeersTable({ ticker }: { ticker: string }) {
  const [peers, setPeers] = useState<PeerRow[] | null>(null)
  const { t, name } = useLang()

  useEffect(() => {
    let live = true
    setPeers(null)
    api.peers(ticker).then((d) => live && setPeers(d)).catch(() => {})
    return () => {
      live = false
    }
  }, [ticker])

  if (!peers) return <Skeleton className="h-56 w-full" />

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-start text-[10px] text-ink-faint">
            <th className="pb-2 pe-4 text-start font-normal">{t.peer}</th>
            <th className="pb-2 pe-4 text-end font-normal">{t.price}</th>
            <th className="pb-2 pe-4 text-end font-normal">{t.fairValue}</th>
            <th className="pb-2 pe-4 text-end font-normal">{t.upsideCol}</th>
            <th className="pb-2 pe-4 text-end font-normal">{t.peRatio}</th>
            <th className="pb-2 pe-4 text-end font-normal">{t.margin}</th>
            <th className="pb-2 text-end font-normal">{t.yoy}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line/60">
          {peers.map((p, i) => (
            <motion.tr
              key={p.ticker}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.25, delay: i * 0.04 }}
              className={p.is_self ? 'bg-analyst/6' : 'row-hover'}
            >
              <td className="py-2.5 pe-4">
                <Link to={`/company/${p.ticker}`} className="flex items-center gap-2.5 hover:text-accent">
                  <span className="num text-[10px] text-ink-faint">{p.ticker}</span>
                  <span className={p.is_self ? 'font-semibold text-analyst' : 'font-medium'}>
                    {name(p)}
                  </span>
                </Link>
              </td>
              <td className="num py-2.5 pe-4 text-end">{fmt(p.price)}</td>
              <td className="num py-2.5 pe-4 text-end">{fmt(p.fair_value)}</td>
              <td
                className={`num py-2.5 pe-4 text-end ${p.upside_pct >= 0 ? 'text-accent' : 'text-negative'}`}
              >
                {fmtPct(p.upside_pct, true)}
              </td>
              <td className="num py-2.5 pe-4 text-end">{fmt(p.pe_ratio)}x</td>
              <td className="num py-2.5 pe-4 text-end">{fmtPct(p.net_margin * 100)}</td>
              <td
                className={`num py-2.5 text-end ${p.revenue_yoy >= 0 ? 'text-accent' : 'text-negative'}`}
              >
                {fmtPct(p.revenue_yoy * 100, true)}
              </td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Quarterly financials                                                 */
/* ------------------------------------------------------------------ */

function QuarterliesTable({ history }: { history: QuarterFinancials[] }) {
  const { t } = useLang()
  const rows = [...history].reverse()

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-[10px] text-ink-faint">
            <th className="pb-2 pe-4 text-start font-normal">{t.quarter}</th>
            <th className="pb-2 pe-4 text-end font-normal">{t.revenue}</th>
            <th className="pb-2 pe-4 text-end font-normal">{t.netIncome}</th>
            <th className="pb-2 pe-4 text-end font-normal">{t.margin}</th>
            <th className="pb-2 pe-4 text-end font-normal">{t.fcf}</th>
            <th className="pb-2 pe-4 text-end font-normal">{t.zakat}</th>
            <th className="pb-2 text-end font-normal">{t.price}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line/60">
          {rows.map((q, i) => (
            <motion.tr
              key={q.quarter}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.25, delay: i * 0.025 }}
              className="row-hover"
            >
              <td className="num py-2 pe-4">{fmtQuarter(q.quarter, true)}</td>
              <td className="num py-2 pe-4 text-end">{fmtMillions(q.revenue)}</td>
              <td className="num py-2 pe-4 text-end">{fmtMillions(q.net_income)}</td>
              <td className="num py-2 pe-4 text-end">{fmtPct(q.net_margin * 100)}</td>
              <td
                className={`num py-2 pe-4 text-end ${q.free_cash_flow < 0 ? 'text-negative' : ''}`}
              >
                {fmtMillions(q.free_cash_flow)}
              </td>
              <td className="num py-2 pe-4 text-end">{fmtMillions(q.zakat_expense)}</td>
              <td className="num py-2 text-end">{fmt(q.share_price)}</td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
