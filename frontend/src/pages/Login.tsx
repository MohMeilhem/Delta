import { useState } from 'react'
import type { FormEvent } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { AnimatePresence, motion, useIsPresent } from 'motion/react'
import { CircleNotch, Eye, EyeSlash, Moon, Sun, Translate, WarningCircle } from '@phosphor-icons/react'
import { useAuth } from '../auth'
import { useLang } from '../i18n'
import { useTheme } from '../theme'
import { EASE } from '../components/ui'
import DeltaMotif from '../components/DeltaMotif'

const DEMO_EMAIL = 'analyst@delta.sa'

export default function Login() {
  const { user, login } = useAuth()
  const { t } = useLang()
  const location = useLocation()
  const isPresent = useIsPresent()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState(false)
  const [busy, setBusy] = useState(false)

  const from = (location.state as { from?: string } | null)?.from ?? '/'

  // Redirect only from the live copy — the exiting AnimatePresence snapshot
  // keeps rendering with a stale location and must not navigate again.
  if (user && isPresent) return <Navigate to={from} replace />

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (!email.trim() || !password) {
      setError(true)
      return
    }
    setError(false)
    setBusy(true)
    // Demo build: no auth backend — a short beat so the sign-in feels real.
    // Setting the user flips the <Navigate> above, which sends us to `from`.
    setTimeout(() => login(email.trim()), 450)
  }

  const fillDemo = () => {
    setEmail(DEMO_EMAIL)
    setPassword('delta-demo')
    setError(false)
  }

  return (
    <main className="relative grid min-h-dvh lg:grid-cols-[1.1fr_1fr]">
      <CornerControls />

      {/* brand side: the product thesis, drawn */}
      <section className="hidden flex-col justify-between border-e border-line px-12 py-12 lg:flex">
        <div className="display flex items-center gap-2.5 text-lg font-bold tracking-tight">
          <img src="/logo.svg" alt="" className="h-5 w-5" />
          {t.brand}
          <span className="mt-0.5 text-[10px] font-medium text-ink-faint">{t.market}</span>
        </div>

        <div className="max-w-xl">
          <h1 className="display text-3xl font-bold leading-snug tracking-tight xl:text-4xl">
            {t.loginThesis}
          </h1>
          <p className="mt-3 max-w-md text-sm leading-7 text-ink-muted">{t.heroLine}</p>
          <DeltaMotif />
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
      </section>

      {/* form side */}
      <section className="flex items-center justify-center px-6 py-16">
        <div className="w-full max-w-sm">
          {/* compact brand header for small screens */}
          <div className="display mb-8 flex items-center justify-center gap-2.5 text-xl font-bold tracking-tight lg:hidden">
            <img src="/logo.svg" alt="" className="h-6 w-6" />
            {t.brand}
            <span className="mt-1 text-[10px] font-medium text-ink-faint">{t.market}</span>
          </div>

          <div className="panel-raised p-8">
            <h2 className="display text-2xl font-bold tracking-tight">{t.loginTitle}</h2>
            <p className="mt-1.5 text-sm text-ink-muted">{t.loginHint}</p>

            <form onSubmit={submit} className="mt-7 space-y-5" noValidate>
              <Field label={t.emailLabel}>
                <input
                  type="email"
                  dir="ltr"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={DEMO_EMAIL}
                  className="w-full rounded-lg border border-line bg-screen px-3.5 py-2.5 text-sm text-ink outline-none transition-colors placeholder:text-ink-faint focus:border-accent"
                />
              </Field>

              <Field label={t.passwordLabel}>
                <div dir="ltr" className="relative">
                  <input
                    type={showPw ? 'text' : 'password'}
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full rounded-lg border border-line bg-screen py-2.5 pl-3.5 pr-11 text-sm text-ink outline-none transition-colors placeholder:text-ink-faint focus:border-accent"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPw((s) => !s)}
                    aria-label={showPw ? t.hidePassword : t.showPassword}
                    title={showPw ? t.hidePassword : t.showPassword}
                    className="btn absolute inset-y-0 right-0 flex items-center px-3.5 text-ink-faint hover:text-ink"
                  >
                    {showPw ? <EyeSlash size={16} weight="bold" /> : <Eye size={16} weight="bold" />}
                  </button>
                </div>
              </Field>

              <AnimatePresence initial={false}>
                {error && (
                  <motion.p
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2, ease: EASE }}
                    className="flex items-center gap-1.5 overflow-hidden text-xs text-negative"
                  >
                    <WarningCircle size={14} weight="bold" />
                    {t.loginError}
                  </motion.p>
                )}
              </AnimatePresence>

              <button
                type="submit"
                disabled={busy}
                className="btn flex w-full items-center justify-center gap-2 bg-accent py-2.5 text-sm font-semibold text-bg hover:opacity-90 disabled:opacity-60"
              >
                {busy && <CircleNotch size={15} weight="bold" className="animate-spin" />}
                {busy ? t.loggingIn : t.loginBtn}
              </button>
            </form>

            <div className="mt-6 border-t border-line pt-4 text-center text-[11px] leading-5 text-ink-faint">
              {t.demoNote}
              <button onClick={fillDemo} className="btn ms-2 font-semibold text-accent hover:opacity-80">
                {t.demoFill}
              </button>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-semibold text-ink-muted">{label}</span>
      {children}
    </label>
  )
}

/** Theme + language switches, since the top bar is hidden on this page. */
function CornerControls() {
  const { t, lang, setLang } = useLang()
  const { theme, setTheme } = useTheme()
  return (
    <div className="absolute end-4 top-4 z-10 flex gap-1">
      <button
        onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        className="btn flex h-9 w-9 items-center justify-center text-ink-muted hover:bg-surface hover:text-ink"
        aria-label={t.toggleTheme}
        title={t.toggleTheme}
      >
        {theme === 'dark' ? <Sun size={16} weight="bold" /> : <Moon size={16} weight="bold" />}
      </button>
      <button
        onClick={() => setLang(lang === 'ar' ? 'en' : 'ar')}
        className="btn flex h-9 items-center gap-2 px-3 text-xs font-semibold text-ink-muted hover:bg-surface hover:text-ink"
        aria-label="Switch language"
      >
        <Translate size={15} weight="bold" />
        {lang === 'ar' ? 'EN' : 'عربي'}
      </button>
    </div>
  )
}
