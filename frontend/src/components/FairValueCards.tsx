import type { AnalystValuation, BaselineResponse } from '../api'
import { fmt, fmtMillions, fmtPct } from '../format'
import { useLang } from '../i18n'
import { NumberTicker } from './ui'

export default function FairValueCards({
  baseline,
  valuation,
}: {
  baseline: BaselineResponse
  valuation: AnalystValuation | null
}) {
  const { t } = useLang()
  const fv = valuation?.fair_value ?? baseline.fair_value
  const deltaPct = valuation?.delta_pct ?? 0
  const upside = valuation?.upside_pct ?? baseline.upside_pct
  const price = baseline.current_price
  const b = valuation?.breakdown ?? baseline.breakdown

  return (
    <div className="py-7">
      {/* metric row: no dividers — wide, even spacing separates the readouts */}
      <div className="grid grid-cols-2 gap-x-12 gap-y-7 lg:grid-cols-4">
        <Metric label={t.fvBaseline}>
          <NumberTicker
            value={baseline.fair_value}
            format={fmt}
            className="display text-3xl font-semibold"
          />
          <Unit>{t.sar}</Unit>
        </Metric>
        <Metric label={t.fvAnalyst} tone="analyst">
          <NumberTicker value={fv} format={fmt} className="display text-3xl font-semibold" />
          <Unit>{t.sar}</Unit>
        </Metric>
        <Metric
          label={t.delta}
          tone={deltaPct > 0.05 ? 'positive' : deltaPct < -0.05 ? 'negative' : undefined}
        >
          <NumberTicker
            value={deltaPct}
            format={(v) => fmtPct(v, true)}
            className="display text-3xl font-semibold"
          />
        </Metric>
        <Metric
          label={t.vsPrice(`${fmt(price)} ${t.sar}`)}
          tone={upside > 0 ? 'positive' : 'negative'}
        >
          <NumberTicker
            value={upside}
            format={(v) => fmtPct(v, true)}
            className="display text-3xl font-semibold"
          />
          <Unit>{upside >= 0 ? t.upside : t.downside}</Unit>
        </Metric>
      </div>

      {/* valuation breakdown: a quiet fact line under the readouts */}
      <div className="mt-7 flex flex-wrap items-baseline justify-center gap-x-8 gap-y-2 text-xs">
        <span className="font-medium text-ink-muted">
          {b.method === 'ddm_islamic' ? t.ddmIslamic : t.dcf}
        </span>
        <Fact k={t.pvForecast} v={fmtMillions(b.pv_forecast)} />
        <Fact k={t.pvTerminal} v={fmtMillions(b.pv_terminal)} />
        <Fact k={t.zakat} v={fmtMillions(b.zakat_total)} accent />
        <Fact k={t.totalDebt} v={fmtMillions(b.total_debt)} />
        {b.sukuk_debt > 0 && <Fact k={t.ofWhichSukuk} v={fmtMillions(b.sukuk_debt)} accent />}
      </div>
    </div>
  )
}

function Metric({
  label,
  tone,
  children,
}: {
  label: string
  tone?: 'analyst' | 'positive' | 'negative'
  children: React.ReactNode
}) {
  const color =
    tone === 'analyst'
      ? 'text-analyst'
      : tone === 'positive'
        ? 'text-accent'
        : tone === 'negative'
          ? 'text-negative'
          : 'text-ink'
  return (
    <div>
      <div className="text-xs leading-tight text-ink-muted">{label}</div>
      <div className={`mt-2.5 flex items-baseline gap-2 ${color}`}>{children}</div>
    </div>
  )
}

function Unit({ children }: { children: React.ReactNode }) {
  return <span className="text-[11px] text-ink-faint">{children}</span>
}

function Fact({ k, v, accent }: { k: string; v: string; accent?: boolean }) {
  return (
    <span className="flex items-baseline gap-2">
      <span className={accent ? 'text-accent' : 'text-ink-faint'}>{k}</span>
      <span className="num text-ink">{v}</span>
    </span>
  )
}
