import { useEffect, useState } from 'react'
import { motion, useReducedMotion } from 'motion/react'
import { ShieldCheck } from '@phosphor-icons/react'
import { api } from '../api'
import type { AgentReport, AnomalyFlag } from '../api'
import { fmtPct } from '../format'
import { useLang } from '../i18n'
import { Skeleton } from './ui'

const SEVERITY_CLS = {
  high: 'border-negative/50 bg-negative/10 text-negative',
  medium: 'border-warning/50 bg-warning/10 text-warning',
} as const

/* Spring pop-in: flags are alerts, they should arrive with a little urgency. */
const chipSpring = { type: 'spring' as const, duration: 0.5, bounce: 0.25 }

/** Client-side English rendering of the anomaly explanation (backend text is Arabic). */
function explainEn(f: AnomalyFlag): string {
  const dir = f.direction === 'up' ? 'above' : 'below'
  if (f.metric === 'free_cash_flow') {
    return `Free cash flow broke sharply ${dir} its 8-quarter pattern (SAR ${f.latest_value.toLocaleString('en-US', { maximumFractionDigits: 0 })}m vs a trailing mean of ${f.trailing_mean.toLocaleString('en-US', { maximumFractionDigits: 0 })}m), a ${f.z_score.toFixed(1)}-sigma deviation.`
  }
  const name = f.metric === 'net_margin' ? 'Net margin' : 'Revenue growth'
  return `${name} moved ${dir} its usual range (${fmtPct(f.latest_value * 100)} vs a trailing mean of ${fmtPct(f.trailing_mean * 100)}), a ${f.z_score.toFixed(1)}-sigma break in the 8-quarter pattern.`
}

/** The monitoring agent — runs automatically when a company opens. */
export default function AgentFlags({ ticker }: { ticker: string }) {
  const [report, setReport] = useState<AgentReport | null>(null)
  const [failed, setFailed] = useState(false)
  const reduce = useReducedMotion()
  const { t, lang } = useLang()

  useEffect(() => {
    let live = true
    setReport(null)
    setFailed(false)
    api
      .agentReport(ticker)
      .then((r) => live && setReport(r))
      .catch(() => live && setFailed(true))
    return () => {
      live = false
    }
  }, [ticker])

  if (failed) return null
  if (!report) return <Skeleton className="h-8 w-64 rounded-full" />

  if (!report.flags.length) {
    return (
      <motion.div
        initial={reduce ? false : { opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={chipSpring}
        className="flex w-fit items-center gap-2 rounded-full border border-accent-dim bg-accent/8 px-3.5 py-1.5 text-xs text-accent"
      >
        <ShieldCheck size={14} weight="bold" />
        {t.agentClean}
      </motion.div>
    )
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {report.flags.map((f, i) => (
        <motion.div
          key={f.metric}
          initial={reduce ? false : { opacity: 0, scale: 0.9, y: -6 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ ...chipSpring, delay: 0.15 + i * 0.09 }}
          className={`group relative flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-xs ${SEVERITY_CLS[f.severity]}`}
        >
          <PulseDot />
          <span className="font-semibold">
            {lang === 'ar' ? f.metric_label_ar : t.metricLabels[f.metric]}
          </span>
          <span className="num opacity-80">
            z {f.z_score > 0 ? '+' : ''}
            {f.z_score.toFixed(1)}
          </span>
          <span className="rounded-full bg-current/15 px-1.5 py-px text-[10px]">
            {f.severity === 'high' ? t.critical : t.medium}
          </span>
          {/* explanation on hover */}
          <div className="pointer-events-none absolute end-0 top-full z-20 mt-2 hidden w-72 rounded-[10px] border border-line bg-surface p-3 text-[11px] leading-5 text-ink shadow-xl group-hover:block">
            {lang === 'ar' ? f.explanation_ar : explainEn(f)}
            {report.news_context && i === 0 && (
              <div className="mt-2 border-t border-line pt-2 text-ink-muted">
                {t.relatedNews} {report.news_context.headline}{' '}
                <span className="text-ink-faint">
                  ({report.news_context.source}، {report.news_context.date})
                </span>
              </div>
            )}
          </div>
        </motion.div>
      ))}
    </div>
  )
}

function PulseDot() {
  return (
    <span className="relative flex h-1.5 w-1.5">
      <span
        className="absolute inline-flex h-full w-full animate-ping rounded-full bg-current opacity-60"
        style={{ animationDuration: '2.2s' }}
      />
      <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-current" />
    </span>
  )
}
