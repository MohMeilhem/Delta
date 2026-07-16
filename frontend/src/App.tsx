import { useEffect, useState } from 'react'
import { BrowserRouter, Link, Route, Routes, useLocation } from 'react-router-dom'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { Moon, Sun, Translate } from '@phosphor-icons/react'
import Home from './pages/Home'
import CompanyPage from './pages/CompanyPage'
import { api } from './api'
import type { TapeEntry } from './api'
import { LangProvider, useLang } from './i18n'
import { ThemeProvider, useTheme } from './theme'
import { fmt, fmtPct } from './format'
import { EASE } from './components/ui'

export default function App() {
  return (
    <ThemeProvider>
      <LangProvider>
        <BrowserRouter>
          <TopBar />
          <AnimatedRoutes />
        </BrowserRouter>
      </LangProvider>
    </ThemeProvider>
  )
}

function AnimatedRoutes() {
  const location = useLocation()
  const reduce = useReducedMotion()
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={location.pathname}
        initial={reduce ? false : { opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={reduce ? undefined : { opacity: 0, y: -6 }}
        transition={{ duration: 0.25, ease: EASE }}
      >
        <Routes location={location}>
          <Route path="/" element={<Home />} />
          <Route path="/company/:ticker" element={<CompanyPage />} />
        </Routes>
      </motion.div>
    </AnimatePresence>
  )
}

function TopBar() {
  const { t, lang, setLang } = useLang()
  const { theme, setTheme } = useTheme()
  return (
    <div className="sticky top-0 z-40 border-b border-line bg-bg/85 backdrop-blur-md">
      <div className="flex h-12 items-stretch">
        <Link
          to="/"
          className="display flex shrink-0 items-center gap-2.5 border-e border-line px-5 text-lg font-bold tracking-tight"
        >
          <img src="/logo.svg" alt="" className="h-5 w-5" />
          {t.brand}
          <span className="mt-0.5 hidden text-[10px] font-medium text-ink-faint sm:block">
            {t.market}
          </span>
        </Link>
        <TickerTape />
        <button
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="btn flex shrink-0 items-center border-s border-line px-3.5 text-ink-muted hover:bg-surface hover:text-ink"
          aria-label={t.toggleTheme}
          title={t.toggleTheme}
        >
          {theme === 'dark' ? <Sun size={16} weight="bold" /> : <Moon size={16} weight="bold" />}
        </button>
        <button
          onClick={() => setLang(lang === 'ar' ? 'en' : 'ar')}
          className="btn flex shrink-0 items-center gap-2 border-s border-line px-4 text-xs font-semibold text-ink-muted hover:bg-surface hover:text-ink"
          aria-label="Switch language"
        >
          <Translate size={15} weight="bold" />
          {lang === 'ar' ? 'EN' : 'عربي'}
        </button>
      </div>
    </div>
  )
}

function TickerTape() {
  const [tape, setTape] = useState<TapeEntry[] | null>(null)
  const { name } = useLang()

  useEffect(() => {
    api.tape().then(setTape).catch(() => setTape([]))
  }, [])

  if (!tape?.length) return <div className="flex-1" />

  const cells = tape.map((e) => (
    <Link
      key={e.ticker}
      to={`/company/${e.ticker}`}
      className="group flex shrink-0 items-center gap-2 px-4 text-[11px]"
    >
      <span className="text-ink-muted transition-colors group-hover:text-ink">{name(e)}</span>
      <span className="num text-ink">{fmt(e.price)}</span>
      <span className={`num ${e.change_pct >= 0 ? 'text-accent' : 'text-negative'}`}>
        {e.change_pct >= 0 ? '▲' : '▼'} {fmtPct(Math.abs(e.change_pct))}
      </span>
    </Link>
  ))

  return (
    // The tape scrolls LTR-mechanically regardless of page direction.
    <div dir="ltr" className="relative flex-1 overflow-hidden" aria-hidden>
      <div className="tape-track h-12 items-center">
        {cells}
        {cells.map((c, i) => (
          <span key={`dup-${i}`} className="contents">
            {c}
          </span>
        ))}
      </div>
      {/* edge fades */}
      <div className="pointer-events-none absolute inset-y-0 left-0 w-10 bg-gradient-to-r from-bg to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 right-0 w-10 bg-gradient-to-l from-bg to-transparent" />
    </div>
  )
}
