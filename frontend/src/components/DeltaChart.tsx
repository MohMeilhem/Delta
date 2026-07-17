import { useMemo, useRef } from 'react'
import { motion, useReducedMotion } from 'motion/react'
import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { ProjectedQuarter, QuarterFinancials } from '../api'
import { fmtMillions, fmtMillionsShort, fmtQuarter } from '../format'
import { useLang } from '../i18n'
import { useChartColors } from '../theme'
import { Crosshair, NumberTicker } from './ui'

/* Plot geometry (kept in one place: the crosshair overlay depends on it). */
const PAD = 12 // .screen p-3
const M = { top: 10, right: 10, bottom: 4, left: 8 }
const Y_WIDTH = 52
const X_HEIGHT = 30

interface Point {
  quarter: string
  actual?: number
  baseline?: number
  analyst?: number
  band?: [number, number]
  pv?: number
}

export type Metric = 'net_income' | 'revenue'

export default function DeltaChart({
  history,
  baseline,
  analyst,
  metric,
  pvSeries,
  pvTerminal,
}: {
  history: QuarterFinancials[]
  baseline: ProjectedQuarter[]
  analyst: ProjectedQuarter[] | null
  metric: Metric
  pvSeries?: number[]
  pvTerminal?: number
}) {
  const { t } = useLang()
  const cc = useChartColors()
  const data = useMemo<Point[]>(() => {
    const pick = (p: { revenue: number; net_income: number }) =>
      metric === 'revenue' ? p.revenue : p.net_income

    const points: Point[] = history.map((h) => ({ quarter: h.quarter, actual: pick(h) }))
    // Bridge: projections start from the last actual so lines connect.
    const last = history[history.length - 1]
    if (last) {
      points[points.length - 1] = {
        ...points[points.length - 1],
        baseline: pick(last),
        analyst: analyst ? pick(last) : undefined,
        band: analyst ? [pick(last), pick(last)] : undefined,
      }
    }
    baseline.forEach((b, i) => {
      const a = analyst?.[i]
      points.push({
        quarter: b.quarter,
        baseline: pick(b),
        analyst: a ? pick(a) : undefined,
        band: a ? [Math.min(pick(b), pick(a)), Math.max(pick(b), pick(a))] : undefined,
        pv: metric === 'net_income' ? pvSeries?.[i] : undefined,
      })
    })
    return points
  }, [history, baseline, analyst, metric, pvSeries])

  // PV bars live in the bottom fifth of the screen on their own hidden axis.
  const pvMax = useMemo(
    () => (pvSeries?.length ? Math.max(...pvSeries) : 0),
    [pvSeries],
  )

  // Pin the Y domain so the crosshair readout inverts the exact plotted scale.
  // yMin extends below zero when a quarter reports a loss — a [0, max] pin
  // would clamp the line to the baseline and hide the loss entirely.
  const [yMin, yMax] = useMemo(() => {
    const vals = data.flatMap((p) =>
      [p.actual, p.baseline, p.analyst].filter((v): v is number => v != null),
    )
    if (!vals.length) return [0, 1]
    const max = Math.max(...vals) * 1.06
    const min = Math.min(0, Math.min(...vals) * 1.06)
    return [min, max]
  }, [data])

  const wrapRef = useRef<HTMLDivElement>(null)
  const fmtValue = fmtMillionsShort // locale-aware: Arabic-Indic digits in AR mode

  const lastActualQuarter = history[history.length - 1]?.quarter
  const reduce = useReducedMotion()

  return (
    // Financial time axis stays LTR inside the RTL page (market convention).
    // Mount reveal: the screen wipes in along the time axis.
    <motion.div
      ref={wrapRef}
      dir="ltr"
      className="screen relative h-105 w-full p-3"
      initial={reduce ? false : { clipPath: 'inset(0 100% 0 0)', opacity: 0.4 }}
      animate={{ clipPath: 'inset(0 0% 0 0)', opacity: 1 }}
      transition={{ duration: 0.8, ease: [0.23, 1, 0.32, 1] }}
    >
      {/* live terminal-value readout: this is what the terminal-growth lever moves */}
      {metric === 'net_income' && pvTerminal != null && (
        <div className="absolute left-16 top-3.5 z-10 flex items-baseline gap-1.5 rounded-md border border-line/60 bg-surface/75 px-2 py-1 text-[10px] text-ink-faint backdrop-blur-sm">
          <span>{t.pvTerminal}</span>
          <NumberTicker value={pvTerminal} format={fmtMillions} className="text-[11px] text-analyst" />
        </div>
      )}
      {/* precision crosshair: dashed guides + axis readouts under the cursor */}
      <Crosshair
        host={wrapRef}
        getBounds={(w, h) => ({
          l: PAD + M.left + Y_WIDTH,
          r: w - PAD - M.right,
          t: PAD + M.top,
          b: h - PAD - M.bottom - X_HEIGHT,
        })}
        valueAt={(y, b) => yMin + (yMax - yMin) * ((b.b - y) / (b.b - b.t))}
        xLabelAt={(x, b) => {
          if (data.length < 2) return null
          const i = Math.round((x - b.l) / ((b.r - b.l) / (data.length - 1)))
          const q = data[Math.min(Math.max(i, 0), data.length - 1)]?.quarter
          return q ? fmtQuarter(q, true) : null
        }}
        formatValue={fmtValue}
      />
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={M}>
          <defs>
            <linearGradient id="deltaBand" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={cc.analyst} stopOpacity={0.28} />
              <stop offset="100%" stopColor={cc.analyst} stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={cc.grid} strokeDasharray="2 4" vertical={false} />
          <XAxis
            dataKey="quarter"
            tickFormatter={(q: string) => fmtQuarter(q, true)}
            tick={{ fill: cc.faint, fontSize: 11, fontFamily: 'IBM Plex Mono' }}
            tickLine={false}
            axisLine={{ stroke: cc.line }}
            interval="preserveStartEnd"
            minTickGap={28}
            height={X_HEIGHT}
          />
          <YAxis
            domain={[yMin, yMax]}
            tickFormatter={fmtValue}
            tick={{ fill: cc.faint, fontSize: 11, fontFamily: 'IBM Plex Mono' }}
            tickLine={false}
            axisLine={false}
            width={Y_WIDTH}
          />
          {/* hidden axis keeps the PV bars in the bottom fifth of the plot */}
          <YAxis yAxisId="pv" hide domain={[0, pvMax * 5]} />
          {/* the crosshair overlay carries the vertical guide now */}
          <Tooltip content={<DeltaTooltip />} cursor={false} />
          {lastActualQuarter && (
            <ReferenceLine
              x={lastActualQuarter}
              stroke={cc.faint}
              strokeDasharray="4 4"
              label={{
                value: t.projections,
                fill: cc.faint,
                fontSize: 11,
                position: 'insideTopRight',
                offset: 8,
              }}
            />
          )}
          {/* Discounted value of each projected quarter: the discount-rate lever */}
          {pvMax > 0 && (
            <Bar
              dataKey="pv"
              yAxisId="pv"
              fill={cc.analyst}
              fillOpacity={0.22}
              stroke={cc.analyst}
              strokeOpacity={0.4}
              strokeWidth={1}
              radius={[2, 2, 0, 0]}
              isAnimationActive
              animationDuration={220}
              animationEasing="ease-out"
            />
          )}
          {/* The Delta: shaded gap between baseline and analyst — the hero */}
          <Area
            dataKey="band"
            fill="url(#deltaBand)"
            stroke="none"
            isAnimationActive
            animationDuration={220}
            animationEasing="ease-out"
            connectNulls
          />
          <Line
            dataKey="actual"
            stroke={cc.ink}
            strokeWidth={1.75}
            dot={false}
            isAnimationActive={false}
            connectNulls
          />
          <Line
            dataKey="baseline"
            stroke={cc.baseline}
            strokeWidth={2}
            dot={false}
            className="glow-baseline"
            isAnimationActive
            animationDuration={220}
            animationEasing="ease-out"
            connectNulls
          />
          <Line
            dataKey="analyst"
            stroke={cc.analyst}
            strokeWidth={2}
            strokeDasharray="6 4"
            dot={false}
            className="glow-analyst"
            isAnimationActive
            animationDuration={220}
            animationEasing="ease-out"
            connectNulls
          />
        </ComposedChart>
      </ResponsiveContainer>
    </motion.div>
  )
}

function DeltaTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: { dataKey?: string; value?: number | number[] }[]
  label?: string
}) {
  const { t, dir } = useLang()
  const cc = useChartColors()
  if (!active || !payload?.length || !label) return null
  const get = (key: string) => {
    const v = payload.find((p) => p.dataKey === key)?.value
    return typeof v === 'number' ? v : undefined
  }
  const actual = get('actual')
  const base = get('baseline')
  const analyst = get('analyst')
  const rows: { label: string; value: number; color: string }[] = []
  if (actual !== undefined) rows.push({ label: t.actual, value: actual, color: cc.ink })
  if (base !== undefined) rows.push({ label: t.baseline, value: base, color: cc.baseline })
  if (analyst !== undefined) rows.push({ label: t.analystProj, value: analyst, color: cc.analyst })
  if (!rows.length) return null

  return (
    <div
      dir={dir}
      className="rounded-lg border border-line bg-surface px-3.5 py-2.5 text-xs shadow-lg"
    >
      <div className="mb-1.5 font-medium text-ink-muted">{fmtQuarter(label)}</div>
      <div className="space-y-1">
        {rows.map((r) => (
          <div key={r.label} className="flex items-center justify-between gap-6">
            <span className="flex items-center gap-1.5">
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ background: r.color }}
              />
              {r.label}
            </span>
            <span className="num">{fmtMillions(r.value)}</span>
          </div>
        ))}
        {base !== undefined && analyst !== undefined && (
          <div className="mt-1 flex items-center justify-between gap-6 border-t border-line pt-1 text-ink-muted">
            <span>{t.delta}</span>
            <span className="num">{fmtMillions(analyst - base)}</span>
          </div>
        )}
        {get('pv') !== undefined && (
          <div className="flex items-center justify-between gap-6 text-ink-muted">
            <span>{t.pvDiscounted}</span>
            <span className="num">{fmtMillions(get('pv')!)}</span>
          </div>
        )}
      </div>
    </div>
  )
}
