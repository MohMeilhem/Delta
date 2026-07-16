import { useEffect, useMemo, useRef, useState } from 'react'
import { motion, useReducedMotion } from 'motion/react'
import {
  ChartLine,
  Crosshair,
  Eraser,
  Minus,
  TrendUp,
} from '@phosphor-icons/react'
import {
  Bar,
  Brush,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from '../api'
import type { Candle, PriceRange, PriceSeries } from '../api'
import { fmt, fmtDate, fmtPct } from '../format'
import { useLang } from '../i18n'
import { Crosshair as ChartCrosshair, Skeleton } from './ui'

import { useChartColors } from '../theme'

/* Plot geometry (kept in one place: the drawing overlay depends on it). */
const M = { top: 10, right: 10, bottom: 0, left: 8 }
const Y_WIDTH = 56
const X_HEIGHT = 28
const BRUSH_HEIGHT = 26

const RANGES: PriceRange[] = ['1m', '3m', '6m', '1y', 'all']

type Tool = 'cursor' | 'trend' | 'level'

interface TrendLine {
  x1: number
  y1: number
  x2: number
  y2: number
}
interface HLevel {
  y: number
  price: number
}

export default function PriceChart({ ticker }: { ticker: string }) {
  const [range, setRange] = useState<PriceRange>('6m')
  const [series, setSeries] = useState<PriceSeries | null>(null)
  const [showLevels, setShowLevels] = useState(true)
  const [showMAs, setShowMAs] = useState(false)
  const [tool, setTool] = useState<Tool>('cursor')
  const [trends, setTrends] = useState<TrendLine[]>([])
  const [hlevels, setHlevels] = useState<HLevel[]>([])
  const [draft, setDraft] = useState<TrendLine | null>(null)
  // state updates from continuous pointer events are deferred by React;
  // the ref is the source of truth during a drag, state only renders it
  const draftRef = useRef<TrendLine | null>(null)
  const wrapRef = useRef<HTMLDivElement>(null)
  const { t } = useLang()
  const cc = useChartColors()
  const GREEN = cc.up
  const RED = cc.down
  const AMBER = cc.analyst
  const reduce = useReducedMotion()

  useEffect(() => {
    let live = true
    setSeries(null)
    api
      .prices(ticker, range)
      .then((d) => live && setSeries(d))
      .catch(() => {})
    return () => {
      live = false
    }
  }, [ticker, range])

  // drawings are pinned to pixels; a new window invalidates them
  useEffect(() => {
    setTrends([])
    setHlevels([])
    setDraft(null)
  }, [ticker, range])

  const domain = useMemo<[number, number]>(() => {
    if (!series) return [0, 1]
    const lo = Math.min(...series.candles.map((c) => c.low))
    const hi = Math.max(...series.candles.map((c) => c.high))
    return [lo * 0.99, hi * 1.01]
  }, [series])

  const priceAtY = (y: number): number => {
    const el = wrapRef.current
    if (!el) return 0
    const h = el.clientHeight
    const top = M.top
    const bottom = h - X_HEIGHT - BRUSH_HEIGHT
    const [lo, hi] = domain
    return hi - ((y - top) / (bottom - top)) * (hi - lo)
  }

  /* ---- drawing overlay handlers ---- */
  const pos = (e: React.PointerEvent) => {
    const r = wrapRef.current!.getBoundingClientRect()
    return { x: e.clientX - r.left, y: e.clientY - r.top }
  }

  const onPointerDown = (e: React.PointerEvent) => {
    if (tool === 'cursor') return
    const p = pos(e)
    if (tool === 'level') {
      setHlevels((ls) => [...ls, { y: p.y, price: priceAtY(p.y) }])
      return
    }
    try {
      e.currentTarget.setPointerCapture(e.pointerId)
    } catch {
      /* pointer capture is best-effort (fails on synthetic events) */
    }
    draftRef.current = { x1: p.x, y1: p.y, x2: p.x, y2: p.y }
    setDraft(draftRef.current)
  }
  const onPointerMove = (e: React.PointerEvent) => {
    if (!draftRef.current) return
    const p = pos(e)
    draftRef.current = { ...draftRef.current, x2: p.x, y2: p.y }
    setDraft(draftRef.current)
  }
  const onPointerUp = () => {
    const d = draftRef.current
    if (d && Math.hypot(d.x2 - d.x1, d.y2 - d.y1) > 8) {
      setTrends((ls) => [...ls, d])
    }
    draftRef.current = null
    setDraft(null)
  }

  if (!series) return <Skeleton className="h-105 w-full" />

  const { stats, levels, candles } = series
  const plotLeft = M.left + Y_WIDTH

  return (
    <div>
      {/* trailing performance strip */}
      <div className="mb-3 flex flex-wrap items-center gap-x-7 gap-y-2 px-1">
        {stats.changes.map((c) => (
          <div key={c.range}>
            <div className="text-[10px] text-ink-faint">{t.ranges[c.range]}</div>
            <div
              className={`num mt-0.5 text-sm font-medium ${c.change_pct >= 0 ? 'text-accent' : 'text-negative'}`}
            >
              {fmtPct(c.change_pct, true)}
            </div>
          </div>
        ))}
        <div className="ms-auto flex gap-7">
          <div className="text-end">
            <div className="text-[10px] text-ink-faint">
              {t.w52High} · {fmtDate(stats.high_52w_date)}
            </div>
            <div className="num mt-0.5 text-sm font-medium text-accent">{fmt(stats.high_52w)}</div>
          </div>
          <div className="text-end">
            <div className="text-[10px] text-ink-faint">
              {t.w52Low} · {fmtDate(stats.low_52w_date)}
            </div>
            <div className="num mt-0.5 text-sm font-medium text-negative">{fmt(stats.low_52w)}</div>
          </div>
        </div>
      </div>

      {/* toolbar: ranges + chart tools */}
      <div className="mb-2 flex flex-wrap items-center justify-between gap-3 px-1">
        <div className="flex rounded-lg border border-line p-0.5 text-xs" role="tablist">
          {RANGES.map((r) => (
            <button
              key={r}
              role="tab"
              aria-selected={range === r}
              onClick={() => setRange(r)}
              className={`btn num px-2.5 py-1 ${range === r ? 'bg-surface-2 text-ink' : 'text-ink-faint hover:text-ink'}`}
            >
              {t.ranges[r]}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1.5">
          <ToolButton
            active={showLevels}
            onClick={() => setShowLevels((v) => !v)}
            label={t.showLevels}
          >
            <ChartLine size={14} weight="bold" />
          </ToolButton>
          <ToolButton active={showMAs} onClick={() => setShowMAs((v) => !v)} label={t.showMAs}>
            <span className="num text-[9px] font-bold">MA</span>
          </ToolButton>
          <span className="mx-1 h-4 w-px bg-line" />
          <ToolButton
            active={tool === 'cursor'}
            onClick={() => setTool('cursor')}
            label="cursor"
          >
            <Crosshair size={14} weight="bold" />
          </ToolButton>
          <ToolButton
            active={tool === 'trend'}
            onClick={() => setTool(tool === 'trend' ? 'cursor' : 'trend')}
            label={t.drawTrend}
          >
            <TrendUp size={14} weight="bold" />
          </ToolButton>
          <ToolButton
            active={tool === 'level'}
            onClick={() => setTool(tool === 'level' ? 'cursor' : 'level')}
            label={t.drawLevel}
          >
            <Minus size={14} weight="bold" />
          </ToolButton>
          <ToolButton
            active={false}
            disabled={!trends.length && !hlevels.length}
            onClick={() => {
              setTrends([])
              setHlevels([])
            }}
            label={t.clearDrawings}
          >
            <Eraser size={14} weight="bold" />
          </ToolButton>
        </div>
      </div>

      {tool !== 'cursor' && (
        <div className="mb-2 px-1 text-[10px] text-analyst">{t.drawHint}</div>
      )}
      {showMAs && (
        <div className="mb-2 flex gap-4 px-1 text-[10px] text-ink-faint">
          <span className="flex items-center gap-1.5">
            <span className="h-0 w-4 border-t" style={{ borderColor: cc.muted }} />
            SMA 20
          </span>
          <span className="flex items-center gap-1.5">
            <span
              className="h-0 w-4 border-t"
              style={{ borderColor: cc.faint, borderStyle: 'dashed' }}
            />
            SMA 50
          </span>
        </div>
      )}

      {/* the trading screen */}
      <motion.div
        ref={wrapRef}
        dir="ltr"
        className="screen relative h-96 w-full p-0"
        initial={reduce ? false : { opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
      >
        {/* precision crosshair with a live price readout on the value axis */}
        <ChartCrosshair
          host={wrapRef}
          getBounds={(w, h) => ({
            l: M.left + Y_WIDTH,
            r: w - M.right,
            t: M.top,
            b: h - X_HEIGHT - BRUSH_HEIGHT,
          })}
          valueAt={(y, b) => domain[1] - ((y - b.t) / (b.b - b.t)) * (domain[1] - domain[0])}
          formatValue={fmt}
        />
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={candles} margin={M}>
            <CartesianGrid stroke={cc.grid} strokeDasharray="2 4" vertical={false} />
            <XAxis
              dataKey="date"
              // daily ranges need the day in the tick; weekly ranges just month-year
              tickFormatter={(d: string) => fmtDate(d, range !== '1m' && range !== '3m')}
              tick={{ fill: cc.faint, fontSize: 10, fontFamily: 'IBM Plex Mono' }}
              tickLine={false}
              axisLine={{ stroke: cc.line }}
              minTickGap={42}
              height={X_HEIGHT}
            />
            <YAxis
              domain={domain}
              tickFormatter={(v: number) => fmt(v)}
              tick={{ fill: cc.faint, fontSize: 10, fontFamily: 'IBM Plex Mono' }}
              tickLine={false}
              axisLine={false}
              width={Y_WIDTH}
            />
            {/* the crosshair overlay carries the cursor guides now */}
            <Tooltip content={<CandleTooltip />} cursor={false} />

            {showLevels &&
              levels.map((l) => (
                <ReferenceLine
                  key={`${l.kind}-${l.price}`}
                  y={l.price}
                  stroke={l.kind === 'support' ? GREEN : RED}
                  strokeDasharray="5 4"
                  strokeOpacity={0.35 + Math.min(l.touches, 8) * 0.06}
                  label={{
                    value: `${l.kind === 'support' ? t.support : t.resistance} ${fmt(l.price)} ×${l.touches}`,
                    fill: l.kind === 'support' ? GREEN : RED,
                    fontSize: 10,
                    fontFamily: 'IBM Plex Mono',
                    position: 'insideBottomLeft',
                  }}
                />
              ))}

            {showMAs && (
              <>
                <Line
                  dataKey="sma20"
                  stroke={cc.muted}
                  strokeWidth={1.25}
                  dot={false}
                  isAnimationActive={false}
                  connectNulls
                />
                <Line
                  dataKey="sma50"
                  stroke={cc.faint}
                  strokeWidth={1.25}
                  strokeDasharray="5 3"
                  dot={false}
                  isAnimationActive={false}
                  connectNulls
                />
              </>
            )}
            <Bar
              dataKey={(c: Candle) => [c.low, c.high]}
              shape={<CandleShape upColor={GREEN} downColor={RED} />}
              isAnimationActive={false}
            />
            <Brush
              dataKey="date"
              height={BRUSH_HEIGHT}
              travellerWidth={8}
              stroke={cc.line}
              fill={cc.surface}
              tickFormatter={(d: string) => fmtDate(d, true)}
            />
          </ComposedChart>
        </ResponsiveContainer>

        {/* analyst drawings + capture layer */}
        <svg
          className="absolute inset-0 h-full w-full"
          style={{
            pointerEvents: tool === 'cursor' ? 'none' : 'auto',
            cursor: tool === 'cursor' ? 'default' : 'crosshair',
          }}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
        >
          {trends.map((l, i) => (
            <line
              key={i}
              x1={l.x1}
              y1={l.y1}
              x2={l.x2}
              y2={l.y2}
              stroke={AMBER}
              strokeWidth={1.5}
            />
          ))}
          {draft && (
            <line
              x1={draft.x1}
              y1={draft.y1}
              x2={draft.x2}
              y2={draft.y2}
              stroke={AMBER}
              strokeWidth={1.5}
              strokeDasharray="4 3"
            />
          )}
          {hlevels.map((l, i) => (
            <g key={i}>
              <line
                x1={plotLeft}
                y1={l.y}
                x2="100%"
                y2={l.y}
                stroke={AMBER}
                strokeWidth={1}
                strokeDasharray="6 4"
              />
              <text
                x={plotLeft + 6}
                y={l.y - 4}
                fill={AMBER}
                fontSize={10}
                fontFamily="IBM Plex Mono"
              >
                {fmt(l.price)}
              </text>
            </g>
          ))}
        </svg>
      </motion.div>
    </div>
  )
}

function ToolButton({
  active,
  onClick,
  label,
  disabled,
  children,
}: {
  active: boolean
  onClick: () => void
  label: string
  disabled?: boolean
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={label}
      aria-label={label}
      aria-pressed={active}
      className={`btn grid h-7 w-7 place-items-center border ${
        active
          ? 'border-analyst-dim bg-analyst/12 text-analyst'
          : 'border-line text-ink-faint hover:text-ink'
      } disabled:opacity-35`}
    >
      {children}
    </button>
  )
}

/* Candlestick: wick spans low→high (the bar range); body spans open→close. */
function CandleShape(props: {
  x?: number
  y?: number
  width?: number
  height?: number
  payload?: Candle
  upColor?: string
  downColor?: string
}) {
  const { x = 0, y = 0, width = 0, height = 0, payload, upColor = '', downColor = '' } = props
  if (!payload || height <= 0) return null
  const { open, close, high, low } = payload
  const up = close >= open
  const color = up ? upColor : downColor
  const span = high - low || 1
  const scale = height / span
  const bodyTop = y + (high - Math.max(open, close)) * scale
  const bodyH = Math.max(Math.abs(open - close) * scale, 1.5)
  const cx = x + width / 2
  const bodyW = Math.max(Math.min(width * 0.62, 11), 2.5)

  return (
    <g>
      <line x1={cx} y1={y} x2={cx} y2={y + height} stroke={color} strokeWidth={1} />
      <rect
        x={cx - bodyW / 2}
        y={bodyTop}
        width={bodyW}
        height={bodyH}
        fill={up ? color : color}
        rx={1}
      />
    </g>
  )
}

function CandleTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: { payload?: Candle }[]
  label?: string
}) {
  const { t, dir } = useLang()
  const c = payload?.[0]?.payload
  if (!active || !c || !label) return null
  const up = c.close >= c.open
  return (
    <div
      dir={dir}
      className="rounded-lg border border-line bg-surface px-3.5 py-2.5 text-xs shadow-lg"
    >
      <div className="mb-1.5 font-medium text-ink-muted">{fmtDate(c.date)}</div>
      <div className="grid grid-cols-2 gap-x-5 gap-y-1">
        {(
          [
            [t.ohlc.open, c.open],
            [t.ohlc.high, c.high],
            [t.ohlc.low, c.low],
            [t.ohlc.close, c.close],
          ] as [string, number][]
        ).map(([k, v]) => (
          <span key={k} className="flex items-baseline justify-between gap-3">
            <span className="text-ink-faint">{k}</span>
            <span className={`num ${k === t.ohlc.close ? (up ? 'text-accent' : 'text-negative') : 'text-ink'}`}>
              {fmt(v)}
            </span>
          </span>
        ))}
      </div>
    </div>
  )
}
