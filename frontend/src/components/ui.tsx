import type { ComponentType, ReactNode, RefObject } from 'react'
import { useEffect, useRef, useState } from 'react'
import { animate, useReducedMotion } from 'motion/react'
import { useLang } from '../i18n'
import {
  ArrowClockwise,
  Bank,
  Broadcast,
  Buildings,
  Cube,
  ForkKnife,
  HeartStraight,
  Lightning,
  PlugCharging,
  Storefront,
  WarningCircle,
} from '@phosphor-icons/react'

/* Strong ease-out shared by every motion/react transition. */
export const EASE: [number, number, number, number] = [0.23, 1, 0.32, 1]

export function Panel({
  title,
  children,
  className = '',
  action,
  raised = false,
}: {
  title?: ReactNode
  children: ReactNode
  className?: string
  action?: ReactNode
  raised?: boolean
}) {
  return (
    <section className={`${raised ? 'panel-raised' : 'panel'} p-5 ${className}`}>
      {(title || action) && (
        <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
          {title && <h2 className="text-sm font-semibold text-ink-muted">{title}</h2>}
          {action}
        </header>
      )}
      {children}
    </section>
  )
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`skeleton ${className}`} aria-hidden />
}

export function ErrorNote({ retry }: { retry?: () => void }) {
  const { t } = useLang()
  return (
    <div className="panel flex items-center justify-between gap-3 p-5 text-sm text-ink-muted">
      <span className="flex items-center gap-2">
        <WarningCircle size={18} className="text-negative" weight="bold" />
        {t.loadFailed}
      </span>
      {retry && (
        <button
          onClick={retry}
          className="btn flex items-center gap-1.5 border border-line px-3 py-1 text-xs hover:bg-surface-2"
        >
          <ArrowClockwise size={13} weight="bold" />
          {t.retryBtn}
        </button>
      )}
    </div>
  )
}

export interface PlotBounds {
  l: number
  r: number
  t: number
  b: number
}

/**
 * Precision crosshair: dashed guides follow the pointer over a chart with a
 * live value readout pinned to the value axis (and optionally a label chip on
 * the time axis). Purely positional — no animation, nothing to reduce.
 * The host element must be position:relative; geometry comes from the caller
 * so the readout inverts the exact scale the chart renders with.
 */
export function Crosshair({
  host,
  getBounds,
  valueAt,
  xLabelAt,
  formatValue,
}: {
  host: RefObject<HTMLElement | null>
  getBounds: (w: number, h: number) => PlotBounds
  valueAt: (y: number, b: PlotBounds) => number
  xLabelAt?: (x: number, b: PlotBounds) => string | null
  formatValue: (v: number) => string
}) {
  const [pt, setPt] = useState<{ x: number; y: number } | null>(null)

  useEffect(() => {
    const el = host.current
    if (!el) return
    const move = (e: PointerEvent) => {
      const r = el.getBoundingClientRect()
      setPt({ x: e.clientX - r.left, y: e.clientY - r.top })
    }
    const leave = () => setPt(null)
    el.addEventListener('pointermove', move)
    el.addEventListener('pointerleave', leave)
    return () => {
      el.removeEventListener('pointermove', move)
      el.removeEventListener('pointerleave', leave)
    }
  }, [host])

  const el = host.current
  if (!pt || !el) return null
  const b = getBounds(el.clientWidth, el.clientHeight)
  if (pt.x < b.l || pt.x > b.r || pt.y < b.t || pt.y > b.b) return null
  const label = xLabelAt?.(pt.x, b)

  return (
    <div dir="ltr" className="pointer-events-none absolute inset-0 z-20">
      <div
        className="absolute border-t border-dashed border-line-strong"
        style={{ left: b.l, width: b.r - b.l, top: pt.y }}
      />
      <div
        className="absolute border-s border-dashed border-line-strong"
        style={{ top: b.t, height: b.b - b.t, left: pt.x }}
      />
      <div
        className="num absolute -translate-y-1/2 rounded border border-line bg-surface px-1.5 py-0.5 text-[10px] leading-none text-ink shadow-sm"
        style={{ left: 2, top: pt.y }}
      >
        {formatValue(valueAt(pt.y, b))}
      </div>
      {label && (
        <div
          className="num absolute -translate-x-1/2 rounded border border-line bg-surface px-1.5 py-0.5 text-[10px] leading-none text-ink shadow-sm"
          style={{ left: pt.x, top: b.b + 3 }}
        >
          {label}
        </div>
      )}
    </div>
  )
}

/** Attach to any .spotlight element: tracks the cursor for the border glow. */
export function spotlightHandlers() {
  return {
    onMouseMove: (e: React.MouseEvent<HTMLElement>) => {
      const r = e.currentTarget.getBoundingClientRect()
      e.currentTarget.style.setProperty('--mx', `${e.clientX - r.left}px`)
      e.currentTarget.style.setProperty('--my', `${e.clientY - r.top}px`)
    },
  }
}

/* Sector glyphs — Phosphor, one family, one weight. */
const SECTOR_ICONS: Record<string, ComponentType<{ size?: number; weight?: 'regular' | 'duotone' }>> = {
  banks: Bank,
  energy: Lightning,
  materials: Cube,
  telecom: Broadcast,
  healthcare: HeartStraight,
  retail: Storefront,
  utilities: PlugCharging,
  food: ForkKnife,
  realestate: Buildings,
}

export function SectorIcon({ id, size = 20 }: { id: string; size?: number }) {
  const Icon = SECTOR_ICONS[id] ?? Cube
  return <Icon size={size} weight="duotone" />
}

/**
 * Number ticker: the digits roll to the new value instead of snapping.
 * Falls back to an instant swap under prefers-reduced-motion.
 */
export function NumberTicker({
  value,
  format,
  className = '',
}: {
  value: number
  format: (v: number) => string
  className?: string
}) {
  const ref = useRef<HTMLSpanElement>(null)
  const previous = useRef(value)
  const reduce = useReducedMotion()

  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (reduce || previous.current === value) {
      el.textContent = format(value)
      previous.current = value
      return
    }
    const controls = animate(previous.current, value, {
      duration: 0.55,
      ease: EASE,
      onUpdate: (v) => {
        el.textContent = format(v)
      },
    })
    previous.current = value
    return () => controls.stop()
  }, [value, format, reduce])

  return (
    <span ref={ref} className={`num ${className}`}>
      {format(value)}
    </span>
  )
}
