import { useEffect, useState } from 'react'
import { motion } from 'motion/react'
import { CellSignalHigh } from '@phosphor-icons/react'
import { api } from '../api'
import type { LiveQuoteData } from '../api'
import { fmt, fmtPct } from '../format'
import { useLang } from '../i18n'

/**
 * Real Tadawul quote (Yahoo Finance) shown next to the seed price.
 * When the network is down or the symbol is unavailable, it renders a quiet
 * "demo data" tag instead — the model always runs on the seed dataset.
 */
export default function LiveQuote({ ticker }: { ticker: string }) {
  const [quote, setQuote] = useState<LiveQuoteData | null>(null)
  const { t } = useLang()

  useEffect(() => {
    let alive = true
    setQuote(null)
    api.live(ticker).then((q) => alive && setQuote(q)).catch(() => {})
    return () => {
      alive = false
    }
  }, [ticker])

  if (!quote) return null

  if (!quote.available) {
    return (
      <span className="rounded-full border border-line px-2 py-0.5 text-[10px] text-ink-faint">
        {t.seedBadge}
      </span>
    )
  }

  const up = (quote.change_pct ?? 0) >= 0
  return (
    <motion.span
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.23, 1, 0.32, 1] }}
      className="flex items-center gap-2 rounded-full border border-accent-dim bg-accent/8 px-2.5 py-1 text-[11px]"
      title={`${t.liveSource}: ${quote.source}`}
    >
      <span className="relative flex h-1.5 w-1.5">
        <span
          className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-60"
          style={{ animationDuration: '2s' }}
        />
        <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-accent" />
      </span>
      <CellSignalHigh size={12} weight="bold" className="text-accent" />
      <span className="text-accent">{t.liveBadge}</span>
      <span className="num font-medium text-ink">{fmt(quote.price ?? 0)}</span>
      <span className={`num ${up ? 'text-accent' : 'text-negative'}`}>
        {up ? '▲' : '▼'} {fmtPct(Math.abs(quote.change_pct ?? 0))}
      </span>
    </motion.span>
  )
}
