import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { CaretDown, CaretLeft, CaretRight } from '@phosphor-icons/react'
import { api } from '../api'
import type { Company, Sector } from '../api'
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
    <main className="mx-auto max-w-5xl px-6 py-12">
      {/* masthead: asymmetric, no card */}
      <header className="mb-12 flex flex-wrap items-end justify-between gap-6 border-b border-line pb-8">
        <div className="max-w-xl">
          <h1 className="display text-5xl font-bold tracking-tight">{t.brand}</h1>
          <p className="mt-3 text-sm leading-7 text-ink-muted">{t.heroLine}</p>
        </div>
        <dl className="flex gap-8 text-start">
          {(
            [
              [33, t.listedCompanies],
              [9, t.sectors],
              [12, t.histQuarters],
            ] as [number, string][]
          ).map(([n, label]) => (
            <div key={label}>
              <dt className="text-[11px] text-ink-faint">{label}</dt>
              <dd className="num display mt-1 text-2xl font-semibold">{n}</dd>
            </div>
          ))}
        </dl>
      </header>

      {error && <ErrorNote retry={() => window.location.reload()} />}

      {!sectors && !error && (
        <div className="space-y-px">
          {Array.from({ length: 9 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      )}

      {/* sector index: hairline rows, not cards */}
      {sectors && (
        <div className="divide-y divide-line border-y border-line">
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
                  className="row-hover group flex w-full items-center gap-4 px-4 py-4 text-start"
                >
                  <span
                    className={`transition-colors duration-200 ${open ? 'text-accent' : 'text-ink-faint group-hover:text-accent'}`}
                  >
                    <SectorIcon id={s.id} size={22} />
                  </span>
                  <span className="flex-1">
                    <span className="display block font-semibold">{name(s)}</span>
                    <span className="mt-0.5 block text-[11px] text-ink-faint">{altName(s)}</span>
                  </span>
                  <motion.span
                    animate={{ rotate: open ? 180 : 0 }}
                    transition={{ duration: 0.25, ease: EASE }}
                    className="text-ink-faint"
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
                      <div className="border-t border-line/60 bg-surface/40">
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
                                className="row-hover group/row flex items-center gap-4 py-3 pe-4 ps-14"
                              >
                                <span className="num w-12 text-xs text-ink-faint">{c.ticker}</span>
                                <span className="flex-1">
                                  <span className="text-sm font-medium">{name(c)}</span>
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
                                  className={`text-ink-faint opacity-0 transition-[opacity,transform] duration-200 group-hover/row:opacity-100 ${dir === 'rtl' ? 'group-hover/row:-translate-x-0.5' : 'group-hover/row:translate-x-0.5'}`}
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
