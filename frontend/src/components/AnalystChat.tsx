import { useEffect, useRef, useState } from 'react'
import {
  ArrowCounterClockwise,
  ChatCircleDots,
  CheckCircle,
  PaperPlaneRight,
  Sliders,
  X,
} from '@phosphor-icons/react'
import { api } from '../api'
import type { AssumptionRating, Assumptions, ChatReply, ChatTurn } from '../api'
import { fmt, fmtPct } from '../format'
import { useLang } from '../i18n'

interface Proposal {
  assumptions: Assumptions
  label: string | null
  fairValue: number
  upsidePct: number
  /** the analyst's model at the moment the proposal arrived, for the diff */
  before: Assumptions | null
}

interface Message extends ChatTurn {
  meta?: Pick<ChatReply, 'key_numbers_ar' | 'follow_ups_ar' | 'source'> & {
    proposal?: Proposal
    ratings?: AssumptionRating[]
  }
}

/** Floating chat agent: the analyst voices worries about the open company,
 *  the agent answers grounded in that company's real numbers. */
export default function AnalystChat({
  ticker,
  assumptions,
  onApply,
}: {
  ticker: string
  assumptions: Assumptions | null
  onApply?: (a: Assumptions) => void
}) {
  const { t, dir, lang } = useLang()

  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState(false)
  const [appliedIdx, setAppliedIdx] = useState<Set<number>>(new Set())
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // a different company is a different conversation
  useEffect(() => {
    setMessages([])
    setDraft('')
    setFailed(false)
    setAppliedIdx(new Set())
  }, [ticker])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, busy])

  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  const send = async (text: string) => {
    const content = text.trim()
    if (!content || busy) return
    const history: Message[] = [...messages, { role: 'user', content }]
    setMessages(history)
    setDraft('')
    setFailed(false)
    setBusy(true)
    try {
      // full history (recent turns only) so the agent keeps the thread
      const reply = await api.chat(
        ticker,
        history.slice(-12).map(({ role, content }) => ({ role, content })),
        assumptions,
        lang,
      )
      setMessages([
        ...history,
        {
          role: 'assistant',
          content: reply.reply_ar,
          meta: {
            key_numbers_ar: reply.key_numbers_ar,
            follow_ups_ar: reply.follow_ups_ar,
            source: reply.source,
            ratings: reply.assumption_ratings ?? undefined,
            proposal:
              reply.proposed_assumptions && reply.proposed_fair_value !== null
                ? {
                    assumptions: reply.proposed_assumptions,
                    label: reply.proposed_label_ar,
                    fairValue: reply.proposed_fair_value,
                    upsidePct: reply.proposed_upside_pct ?? 0,
                    before: assumptions,
                  }
                : undefined,
          },
        },
      ])
    } catch {
      setMessages(messages) // roll back the optimistic user bubble
      setDraft(content)
      setFailed(true)
    } finally {
      setBusy(false)
    }
  }

  const lastMeta = messages.at(-1)?.role === 'assistant' ? messages.at(-1)?.meta : undefined

  return (
    <>
      {/* launcher */}
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label={t.chatOpen}
        aria-expanded={open}
        className="btn fixed bottom-5 end-5 z-50 flex items-center gap-2 rounded-full border border-line bg-surface-2 px-4 py-3 text-sm font-medium text-ink shadow-lg transition-colors hover:border-accent-dim"
      >
        {open ? <X size={18} weight="bold" /> : <ChatCircleDots size={18} weight="bold" />}
        <span className="max-sm:hidden">{t.chatTitle}</span>
      </button>

      {open && (
        <div
          role="dialog"
          aria-label={t.chatTitle}
          className="fixed bottom-20 end-5 z-50 flex h-[min(560px,calc(100vh-7rem))] w-[min(24rem,calc(100vw-2.5rem))] flex-col overflow-hidden rounded-2xl border border-line bg-surface shadow-2xl"
        >
          {/* header */}
          <header className="flex items-center justify-between border-b border-line px-4 py-3">
            <div>
              <div className="text-sm font-semibold text-ink">{t.chatTitle}</div>
              <div className="text-[11px] text-ink-faint">{ticker}</div>
            </div>
            {messages.length > 0 && (
              <button
                onClick={() => setMessages([])}
                className="btn flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] text-ink-faint hover:text-ink"
              >
                <ArrowCounterClockwise size={12} weight="bold" />
                {t.chatClear}
              </button>
            )}
          </header>

          {/* transcript */}
          <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
            {messages.length === 0 && (
              <div className="space-y-3 pt-2">
                <p className="text-xs leading-relaxed text-ink-muted">{t.chatIntro}</p>
                <div className="flex flex-wrap gap-1.5">
                  {t.chatChips.map((chip) => (
                    <Chip key={chip} label={chip} onClick={() => send(chip)} />
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <div key={i} className={m.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
                <div
                  className={`max-w-[85%] rounded-2xl px-3 py-2 text-[13px] leading-relaxed ${
                    m.role === 'user'
                      ? 'rounded-ee-md bg-accent text-surface'
                      : 'rounded-es-md bg-surface-2 text-ink'
                  }`}
                >
                  {m.content}
                  {m.meta && m.meta.key_numbers_ar.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {m.meta.key_numbers_ar.map((k) => (
                        <span
                          key={k}
                          className="num rounded-md border border-line px-1.5 py-0.5 text-[10px] text-ink-muted"
                        >
                          {k}
                        </span>
                      ))}
                    </div>
                  )}
                  {m.meta?.ratings && m.meta.ratings.length > 0 && (
                    <RatingsCard ratings={m.meta.ratings} />
                  )}
                  {m.meta?.proposal && (
                    <ProposalCard
                      proposal={m.meta.proposal}
                      applied={appliedIdx.has(i)}
                      onApply={
                        onApply
                          ? () => {
                              onApply(m.meta!.proposal!.assumptions)
                              setAppliedIdx((s) => new Set(s).add(i))
                            }
                          : undefined
                      }
                    />
                  )}
                  {m.meta && (
                    <div className="mt-1.5 text-[9px] text-ink-faint">
                      {m.meta.source === 'llm' ? t.generated : t.cached}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {busy && (
              <div className="flex items-center gap-2 text-xs text-ink-faint">
                <span className="flex gap-1">
                  {[0, 1, 2].map((d) => (
                    <span
                      key={d}
                      className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent"
                      style={{ animationDelay: `${d * 200}ms` }}
                    />
                  ))}
                </span>
                {t.chatThinking}
              </div>
            )}

            {!busy && lastMeta && lastMeta.follow_ups_ar.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {lastMeta.follow_ups_ar.map((q) => (
                  <Chip key={q} label={q} onClick={() => send(q)} />
                ))}
              </div>
            )}

            {failed && <p className="text-xs text-red-400">{t.chatFailed}</p>}
          </div>

          {/* composer */}
          <form
            onSubmit={(e) => {
              e.preventDefault()
              send(draft)
            }}
            className="flex items-center gap-2 border-t border-line px-3 py-2.5"
          >
            <input
              ref={inputRef}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={t.chatPlaceholder}
              className="min-w-0 flex-1 rounded-xl border border-line bg-surface-2 px-3 py-2 text-[13px] text-ink placeholder:text-ink-faint focus:border-accent-dim focus:outline-none"
            />
            <button
              type="submit"
              disabled={!draft.trim() || busy}
              aria-label={t.chatSend}
              className="btn rounded-xl bg-accent p-2 text-surface disabled:opacity-40"
            >
              <PaperPlaneRight size={16} weight="bold" className={dir === 'rtl' ? '-scale-x-100' : ''} />
            </button>
          </form>
        </div>
      )}
    </>
  )
}

function Chip({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="btn rounded-full border border-line px-2.5 py-1 text-[11px] text-ink-muted transition-colors hover:border-accent-dim hover:text-ink"
    >
      {label}
    </button>
  )
}

const VERDICT_STYLE: Record<AssumptionRating['verdict'], string> = {
  conservative: 'border-sky-500/40 text-sky-500',
  balanced: 'border-accent-dim text-accent',
  aggressive: 'border-amber-500/50 text-amber-500',
}

/** Report card: one verdict badge per model lever, with the agent's anchor. */
function RatingsCard({ ratings }: { ratings: AssumptionRating[] }) {
  const { t } = useLang()
  const labels: Record<AssumptionRating['parameter'], string> = {
    revenue_growth: t.revGrowth,
    net_margin: t.netMargin,
    discount_rate: t.discountRate,
    terminal_growth: t.terminalGrowth,
  }
  return (
    <div className="mt-2 rounded-xl border border-line bg-surface p-2.5">
      <div className="text-[11px] font-semibold text-ink">{t.chatRatings}</div>
      <div className="mt-1.5 space-y-1.5">
        {ratings.map((r) => (
          <div key={r.parameter}>
            <div className="flex items-center justify-between gap-3 text-[11px]">
              <span className="text-ink-muted">{labels[r.parameter]}</span>
              <span
                className={`rounded-full border px-2 py-px text-[10px] font-medium ${VERDICT_STYLE[r.verdict]}`}
              >
                {t.ratingVerdicts[r.verdict]}
              </span>
            </div>
            <div className="num mt-0.5 text-[10px] leading-snug text-ink-faint">{r.note_ar}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

/** Scenario card: the agent's proposed slider values + engine-computed fair
 *  value, with one click to apply them to the live model. */
function ProposalCard({
  proposal,
  applied,
  onApply,
}: {
  proposal: Proposal
  applied: boolean
  onApply?: () => void
}) {
  const { t } = useLang()
  const p = proposal.assumptions
  const b = proposal.before

  const levers: [string, number, number | null][] = [
    [t.revGrowth, p.revenue_growth, b?.revenue_growth ?? null],
    [t.netMargin, p.net_margin, b?.net_margin ?? null],
    [t.discountRate, p.discount_rate, b?.discount_rate ?? null],
    [t.terminalGrowth, p.terminal_growth, b?.terminal_growth ?? null],
  ]
  const changed = levers.filter(([, v, prev]) => prev === null || Math.abs(v - prev) > 1e-9)

  return (
    <div className="mt-2 rounded-xl border border-accent-dim bg-surface p-2.5">
      <div className="flex items-center gap-1.5 text-[11px] font-semibold text-accent">
        <Sliders size={13} weight="bold" />
        {proposal.label || t.chatScenario}
      </div>
      <div className="mt-1.5 space-y-1">
        {changed.map(([label, v, prev]) => (
          <div key={label} className="flex items-center justify-between gap-3 text-[11px]">
            <span className="text-ink-muted">{label}</span>
            <span className="num text-ink">
              {prev !== null && (
                <>
                  <span className="text-ink-faint line-through">{fmtPct(prev * 100)}</span>{' '}
                </>
              )}
              {fmtPct(v * 100)}
            </span>
          </div>
        ))}
        <div className="flex items-center justify-between gap-3 border-t border-line pt-1 text-[11px]">
          <span className="text-ink-muted">{t.fairValue}</span>
          <span className="num font-semibold text-ink">
            {fmt(proposal.fairValue)} {t.sar}
            <span className={proposal.upsidePct >= 0 ? 'text-accent' : 'text-red-400'}>
              {' '}
              ({fmtPct(proposal.upsidePct, true)})
            </span>
          </span>
        </div>
      </div>
      {onApply &&
        (applied ? (
          <div className="mt-2 flex items-center gap-1 text-[11px] font-medium text-accent">
            <CheckCircle size={14} weight="bold" />
            {t.chatApplied}
          </div>
        ) : (
          <button
            onClick={onApply}
            className="btn mt-2 w-full rounded-lg bg-accent px-2 py-1.5 text-[11px] font-semibold text-surface"
          >
            {t.chatApply}
          </button>
        ))}
    </div>
  )
}
