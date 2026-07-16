import { useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { ArrowCounterClockwise, CaretDown, Function } from '@phosphor-icons/react'
import type { Assumptions } from '../api'
import { fmt, fmtPct } from '../format'
import { useLang } from '../i18n'
import { EASE, NumberTicker } from './ui'

interface SliderSpec {
  key: 'revenue_growth' | 'net_margin' | 'discount_rate' | 'terminal_growth'
  min: number
  max: number
  step: number
  signed?: boolean
}

const SLIDERS: SliderSpec[] = [
  { key: 'revenue_growth', min: -0.2, max: 0.4, step: 0.005, signed: true },
  { key: 'net_margin', min: 0.01, max: 0.7, step: 0.005 },
  { key: 'discount_rate', min: 0.05, max: 0.2, step: 0.0025 },
  { key: 'terminal_growth', min: 0, max: 0.06, step: 0.0025 },
]

export default function AssumptionPanel({
  value,
  baseline,
  incomeLabel,
  isIslamic,
  onChange,
  onReset,
  dirty,
}: {
  value: Assumptions
  baseline: Assumptions
  incomeLabel: string
  isIslamic: boolean
  onChange: (a: Assumptions) => void
  onReset: () => void
  dirty: boolean
}) {
  const { t } = useLang()
  const [advanced, setAdvanced] = useState(false)
  const reduce = useReducedMotion()
  const labels: Record<SliderSpec['key'], string> = {
    revenue_growth: t.growthOf(incomeLabel),
    net_margin: t.netMargin,
    discount_rate: t.discountRate,
    terminal_growth: t.terminalGrowth,
  }
  const gordonMode = value.terminal_method === 'gordon'

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-ink-muted">{t.analystAssumptions}</h2>
        <button
          onClick={onReset}
          disabled={!dirty}
          className="btn flex items-center gap-1.5 border border-line px-2.5 py-1 text-xs text-ink-muted enabled:hover:bg-surface-2 enabled:hover:text-ink disabled:opacity-40"
        >
          <ArrowCounterClockwise size={12} weight="bold" />
          {t.resetToBase}
        </button>
      </div>

      {SLIDERS.map((s) => {
        // in exit-multiple mode the terminal-growth slider is inert
        const disabled = s.key === 'terminal_growth' && !gordonMode
        const current = value[s.key]
        const base = baseline[s.key]
        const changed = Math.abs(current - base) > 1e-9
        return (
          <div key={s.key} className={disabled ? 'opacity-40' : ''}>
            <div className="mb-1.5 flex items-baseline justify-between text-sm">
              <label htmlFor={s.key} className="text-ink-muted">
                {labels[s.key]}
              </label>
              <NumberTicker
                value={current * 100}
                format={(v) => fmtPct(v, s.signed)}
                className={`text-sm font-medium transition-colors duration-200 ${changed ? 'text-analyst' : 'text-ink'}`}
              />
            </div>
            <input
              id={s.key}
              type="range"
              dir="ltr"
              min={s.min}
              max={s.max}
              step={s.step}
              value={current}
              disabled={disabled}
              aria-label={labels[s.key]}
              onChange={(e) => onChange({ ...value, [s.key]: Number(e.target.value) })}
            />
            <div dir="ltr" className="mt-1 flex justify-between text-[10px] text-ink-faint">
              <span className="num">{fmtPct(s.min * 100)}</span>
              {changed && (
                <span className="num">
                  {t.baseLabel}: {fmtPct(base * 100)}
                </span>
              )}
              <span className="num">{fmtPct(s.max * 100)}</span>
            </div>
          </div>
        )
      })}

      {/* ---- advanced levers ---- */}
      <button
        onClick={() => setAdvanced((v) => !v)}
        aria-expanded={advanced}
        className="btn flex w-full items-center justify-between border-t border-line pt-3 text-xs font-semibold text-ink-muted hover:text-ink"
      >
        {t.advanced}
        <motion.span
          animate={{ rotate: advanced ? 180 : 0 }}
          transition={{ duration: 0.2, ease: EASE }}
        >
          <CaretDown size={13} weight="bold" />
        </motion.span>
      </button>

      <AnimatePresence initial={false}>
        {advanced && (
          <motion.div
            key="adv"
            initial={reduce ? false : { height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={reduce ? undefined : { height: 0, opacity: 0 }}
            transition={{ duration: 0.28, ease: EASE }}
            className="!mt-0 space-y-5 overflow-hidden"
          >
            <div className="space-y-5 pt-1">
              {/* forecast horizon */}
              <div>
                <div className="mb-1.5 text-sm text-ink-muted">{t.horizon}</div>
                <div className="flex rounded-lg border border-line p-0.5 text-xs" role="tablist">
                  {[4, 8, 12].map((h) => (
                    <button
                      key={h}
                      role="tab"
                      aria-selected={value.horizon_quarters === h}
                      onClick={() => onChange({ ...value, horizon_quarters: h })}
                      className={`btn num flex-1 px-2 py-1 ${
                        value.horizon_quarters === h
                          ? 'bg-surface-2 text-ink'
                          : 'text-ink-faint hover:text-ink'
                      }`}
                    >
                      {h} {t.quartersUnit}
                    </button>
                  ))}
                </div>
              </div>

              {/* cash conversion / payout */}
              <div>
                <div className="mb-1.5 flex items-baseline justify-between text-sm">
                  <span className="text-ink-muted">
                    {isIslamic ? t.payoutRatio : t.cashConversion}
                  </span>
                  <span className={`num text-sm font-medium ${value.fcf_conversion != null ? 'text-analyst' : 'text-ink-faint'}`}>
                    {value.fcf_conversion != null
                      ? fmtPct(value.fcf_conversion * 100)
                      : t.sectorDefault}
                  </span>
                </div>
                <input
                  type="range"
                  dir="ltr"
                  min={0.2}
                  max={1.2}
                  step={0.01}
                  value={value.fcf_conversion ?? 0.85}
                  aria-label={isIslamic ? t.payoutRatio : t.cashConversion}
                  onChange={(e) => onChange({ ...value, fcf_conversion: Number(e.target.value) })}
                />
                {value.fcf_conversion != null && (
                  <button
                    onClick={() => onChange({ ...value, fcf_conversion: null })}
                    className="mt-1 text-[10px] text-ink-faint hover:text-ink"
                  >
                    {t.sectorDefault} ↺
                  </button>
                )}
              </div>

              {/* terminal value method */}
              <div>
                <div className="mb-1.5 text-sm text-ink-muted">{t.terminalValue}</div>
                <div className="flex rounded-lg border border-line p-0.5 text-xs" role="tablist">
                  {(
                    [
                      ['gordon', t.gordon],
                      ['exit_multiple', t.exitMultiple],
                    ] as const
                  ).map(([m, label]) => (
                    <button
                      key={m}
                      role="tab"
                      aria-selected={value.terminal_method === m}
                      onClick={() => onChange({ ...value, terminal_method: m })}
                      className={`btn flex-1 px-2 py-1 ${
                        value.terminal_method === m
                          ? 'bg-surface-2 text-ink'
                          : 'text-ink-faint hover:text-ink'
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                {!gordonMode && (
                  <div className="mt-3">
                    <div className="mb-1.5 flex items-baseline justify-between text-sm">
                      <span className="text-ink-muted">{t.exitPE}</span>
                      <NumberTicker
                        value={value.exit_pe}
                        format={(v) => `${fmt(v)}x`}
                        className="text-sm font-medium text-analyst"
                      />
                    </div>
                    <input
                      type="range"
                      dir="ltr"
                      min={2}
                      max={40}
                      step={0.5}
                      value={value.exit_pe}
                      aria-label={t.exitPE}
                      onChange={(e) => onChange({ ...value, exit_pe: Number(e.target.value) })}
                    />
                  </div>
                )}
              </div>

              <CapmBuilder onApply={(r) => onChange({ ...value, discount_rate: r })} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

/* CAPM: discount rate = risk-free + beta x equity risk premium */
function CapmBuilder({ onApply }: { onApply: (rate: number) => void }) {
  const { t } = useLang()
  const [rf, setRf] = useState(4.5)
  const [beta, setBeta] = useState(1.0)
  const [erp, setErp] = useState(5.5)
  const rate = rf / 100 + (beta * erp) / 100
  const clamped = Math.min(Math.max(rate, 0.05), 0.2)

  return (
    <div className="rounded-md bg-surface-2/50 p-3.5">
      <div className="mb-3 flex items-center gap-2 text-xs font-semibold text-ink-muted">
        <Function size={14} weight="bold" />
        {t.capmTitle}
      </div>
      <div className="grid grid-cols-3 gap-3">
        {(
          [
            [t.riskFree, rf, setRf, 0, 10, 0.1, '٪'],
            [t.beta, beta, setBeta, 0.2, 2.5, 0.05, ''],
            [t.erp, erp, setErp, 2, 10, 0.1, '٪'],
          ] as [string, number, (v: number) => void, number, number, number, string][]
        ).map(([label, v, set, min, max, step]) => (
          <label key={label} className="block">
            <span className="mb-1 block text-[10px] leading-tight text-ink-faint">{label}</span>
            <input
              type="number"
              dir="ltr"
              value={v}
              min={min}
              max={max}
              step={step}
              onChange={(e) => set(Number(e.target.value))}
              className="num w-full rounded-lg border border-line bg-bg px-2 py-1.5 text-xs text-ink outline-none focus:border-analyst-dim"
            />
          </label>
        ))}
      </div>
      <div className="mt-3 flex items-center justify-between">
        <span className="text-[11px] text-ink-faint">
          {t.capmResult}: <span className="num text-analyst">{fmtPct(clamped * 100)}</span>
        </span>
        <button
          onClick={() => onApply(Number(clamped.toFixed(4)))}
          className="btn border border-analyst-dim bg-analyst/10 px-3 py-1 text-xs font-semibold text-analyst hover:bg-analyst/20"
        >
          {t.applyCapm}
        </button>
      </div>
    </div>
  )
}
