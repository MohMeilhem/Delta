import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { CaretDown, CaretLeft, CaretRight } from '@phosphor-icons/react'
import { api } from '../api'
import type { Company, Sector } from '../api'
import DeltaMotif from '../components/DeltaMotif'
import { EASE, ErrorNote, SectorIcon, Skeleton } from '../components/ui'
import { useLang } from '../i18n'

export default function Home() {
  const [sectors, setSectors] = useState<Sector[] | null>(null)
  const [companies, setCompanies] = useState<Record<string, Company[]>>({})
  const [active, setActive] = useState<string | null>(null)
  const [error, setError] = useState(false)
  const reduce = useReducedMotion()
  const { t, dir, name, altName } = useLang()
  const Caret = dir === 'rtl' ? CaretLeft : CaretRight

  useEffect(() => {
    api
      .sectors()
      .then(setSectors)
      .catch(() => setError(true))
  }, [])

  const openSector = async (id: string) => {
    setActive((cur) => (cur === id ? null : id))
    if (!companies[id]) {
      const list = await api.sectorCompanies(id)
      setCompanies((c) => ({ ...c, [id]: list }))
    }
  }

  return (
    <main className="relative mx-auto max-w-5xl px-6 py-12 overflow-hidden">
      {/* Ambient orbs */}
      <div className="pointer-events-none absolute inset-0 z-0 overflow-hidden" aria-hidden>
        <div className="orb orb-green" style={{ opacity: 0.6 }} />
        <div className="orb orb-amber" style={{ opacity: 0.5 }} />
      </div>

      {/* masthead: the thesis, drawn — history splits into the machine line
          and the analyst's line; the shaded gap is the product */}
      <header className="relative z-10 mb-12 grid items-end gap-x-12 gap-y-8 border-b border-line pb-8 lg:grid-cols-[1fr_minmax(300px,42%)]">
        <div className="max-w-xl">
          <h1 className="display hero-gradient-text text-5xl font-bold tracking-tight leading-[1.3]">
            {t.brand}
          </h1>
          <p className="mt-3 text-sm leading-7 text-ink-muted">{t.heroLine}</p>
          <p className="mt-5 text-[11px] tracking-wide text-ink-faint">
            <span className="num">33</span> {t.listedCompanies} · <span className="num">9</span>{' '}
            {t.sectors} · <span className="num">12</span> {t.histQuarters}
          </p>
        </div>
        <DeltaMotif className="max-lg:hidden" />
      </header>

      {error && <ErrorNote retry={() => window.location.reload()} />}

      {!sectors && !error && (
        <div className="relative z-10 space-y-px">
          {Array.from({ length: 9 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      )}

      {/* sector index */}
      {sectors && (
        <div className="relative z-10 divide-y divide-line/60 rounded-2xl border border-line/60 bg-surface/30 backdrop-blur-sm overflow-hidden shadow-[0_0_60px_oklch(0.55_0.13_163/0.06)]">
          {sectors.map((s, i) => {
            const open = active === s.id
            return (
              <motion.div
                key={s.id}
                initial={reduce ? false : { opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.45, delay: i * 0.045, ease: EASE }}
              >
                <button
                  onClick={() => openSector(s.id)}
                  aria-expanded={open}
                  className={`group flex w-full items-center gap-4 px-5 py-4 text-start transition-colors duration-200 ${open ? 'bg-accent/5' : 'hover:bg-surface/60'}`}
                >
                  <span
                    className={`transition-colors duration-200 ${open ? 'text-accent' : 'text-ink-faint group-hover:text-accent'}`}
                  >
                    <SectorIcon id={s.id} size={22} />
                  </span>
                  <span className="flex-1">
                    <span className={`display block font-semibold transition-colors duration-200 ${open ? 'text-accent' : 'text-ink group-hover:text-accent'}`}>{name(s)}</span>
                    <span className="mt-0.5 block text-[11px] text-ink-faint">{altName(s)}</span>
                  </span>
                  <motion.span
                    animate={{ rotate: open ? 180 : 0 }}
                    transition={{ duration: 0.25, ease: EASE }}
                    className={`transition-colors duration-200 ${open ? 'text-accent' : 'text-ink-faint'}`}
                  >
                    <CaretDown size={14} weight="bold" />
                  </motion.span>
                </button>

                <AnimatePresence initial={false}>
                  {open && (
                    <motion.div
                      key="companies"
                      initial={reduce ? false : { height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={reduce ? undefined : { height: 0, opacity: 0 }}
                      transition={{ duration: 0.32, ease: EASE }}
                      className="overflow-hidden"
                    >
                      <div className="border-t border-accent/15 bg-accent/3">
                        {!companies[s.id] ? (
                          <div className="space-y-px p-3">
                            <Skeleton className="h-11 w-full" />
                            <Skeleton className="h-11 w-full" />
                          </div>
                        ) : (
                          companies[s.id].map((c, j) => (
                            <motion.div
                              key={c.ticker}
                              initial={reduce ? false : { opacity: 0, x: dir === 'rtl' ? 10 : -10 }}
                              animate={{ opacity: 1, x: 0 }}
                              transition={{ duration: 0.3, delay: j * 0.035, ease: EASE }}
                            >
                              <Link
                                to={`/company/${c.ticker}`}
                                className="group/row flex items-center gap-4 py-3 pe-5 ps-14 transition-colors duration-150 hover:bg-accent/8"
                              >
                                <span className="num w-12 text-xs text-ink-faint">{c.ticker}</span>
                                <span className="flex-1">
                                  <span className="text-sm font-medium transition-colors group-hover/row:text-accent">{name(c)}</span>
                                  <span className="ms-3 text-[11px] text-ink-faint">
                                    {altName(c)}
                                  </span>
                                </span>
                                {c.is_islamic_bank && (
                                  <span className="rounded-full border border-accent-dim px-2 py-0.5 text-[10px] text-accent">
                                    {t.islamicBank}
                                  </span>
                                )}
                                <Caret
                                  size={13}
                                  weight="bold"
                                  className={`text-accent opacity-0 transition-[opacity,transform] duration-200 group-hover/row:opacity-100 ${dir === 'rtl' ? 'group-hover/row:-translate-x-0.5' : 'group-hover/row:translate-x-0.5'}`}
                                />
                              </Link>
                            </motion.div>
                          ))
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            )
          })}
        </div>
      )}
    </main>
  )
}
