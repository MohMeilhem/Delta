import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion, useReducedMotion } from 'motion/react'
import { api } from '../api'
import type {
  Assumptions,
  PeerRow,
  QuarterFinancials,
  SensitivityResponse,
} from '../api'
import { fmt, fmtMillions, fmtPct, fmtQuarter } from '../format'
import { useLang } from '../i18n'
import { useChartColors } from '../theme'
import { EASE, Skeleton } from './ui'

type Tab = 'sensitivity' | 'peers' | 'quarterlies'

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
    ['peers', t.peers],
    ['quarterlies', t.quarterlies],
  ]

  const panels: Record<Tab, React.ReactNode> = {
    sensitivity: <SensitivityHeatmap ticker={ticker} assumptions={assumptions} />,
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
