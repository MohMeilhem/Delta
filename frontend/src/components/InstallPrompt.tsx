import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { DeviceMobileCamera, Export, PlusSquare, X } from '@phosphor-icons/react'
import { useLang } from '../i18n'

/* Mobile-only PWA install banner.
 * - Hidden on desktop, inside the installed app (standalone), and after dismiss.
 * - Android/Chromium: captures `beforeinstallprompt` and offers the native
 *   one-tap install dialog.
 * - iOS Safari has no install API: show the Share -> Add to Home Screen steps.
 */

const DISMISS_KEY = 'delta-install-dismissed'

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

export default function InstallPrompt() {
  const { lang } = useLang()
  const ar = lang === 'ar'
  const [visible, setVisible] = useState(false)
  const [ios, setIos] = useState(false)
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null)

  useEffect(() => {
    const standalone =
      window.matchMedia('(display-mode: standalone)').matches ||
      // iOS Safari's non-standard flag when launched from the home screen
      (navigator as unknown as { standalone?: boolean }).standalone === true
    const ua = navigator.userAgent
    const mobile = /iphone|ipad|ipod|android/i.test(ua)
    if (standalone || !mobile || localStorage.getItem(DISMISS_KEY)) return

    setIos(/iphone|ipad|ipod/i.test(ua))
    const onPrompt = (e: Event) => {
      e.preventDefault()
      setDeferred(e as BeforeInstallPromptEvent)
    }
    window.addEventListener('beforeinstallprompt', onPrompt)
    // let the page land first; a banner on load feels like an ad
    const t = setTimeout(() => setVisible(true), 2500)
    return () => {
      window.removeEventListener('beforeinstallprompt', onPrompt)
      clearTimeout(t)
    }
  }, [])

  const dismiss = () => {
    localStorage.setItem(DISMISS_KEY, '1')
    setVisible(false)
  }

  const install = async () => {
    if (!deferred) return
    await deferred.prompt()
    dismiss()
  }

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ y: 96, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 96, opacity: 0 }}
          transition={{ duration: 0.35, ease: [0.23, 1, 0.32, 1] }}
          className="fixed inset-x-3 bottom-3 z-50 rounded-2xl border border-line bg-surface/95 p-4 shadow-2xl backdrop-blur-md sm:mx-auto sm:max-w-md"
          role="dialog"
          aria-label={ar ? 'تثبيت التطبيق' : 'Install the app'}
        >
          <button
            onClick={dismiss}
            aria-label={ar ? 'إغلاق' : 'Close'}
            className="absolute end-2.5 top-2.5 rounded-full p-1.5 text-ink-faint hover:bg-surface-2 hover:text-ink"
          >
            <X size={14} weight="bold" />
          </button>

          <div className="flex items-start gap-3">
            <div className="mt-0.5 rounded-xl border border-accent-dim bg-accent/10 p-2 text-accent">
              <DeviceMobileCamera size={20} weight="duotone" />
            </div>
            <div className="min-w-0 flex-1 pe-5">
              <div className="text-sm font-semibold">
                {ar ? 'ثبّت دلتا كتطبيق على جوالك' : 'Install Delta as an app'}
              </div>

              {ios ? (
                <ol className="mt-2 space-y-1.5 text-xs leading-6 text-ink-muted">
                  <li className="flex items-center gap-2">
                    <Export size={14} className="shrink-0 text-accent" />
                    {ar ? (
                      <span>اضغط زر المشاركة في شريط سفاري السفلي</span>
                    ) : (
                      <span>Tap the Share button in Safari's bottom bar</span>
                    )}
                  </li>
                  <li className="flex items-center gap-2">
                    <PlusSquare size={14} className="shrink-0 text-accent" />
                    {ar ? (
                      <span>اختر «إضافة إلى الصفحة الرئيسية» ثم «إضافة»</span>
                    ) : (
                      <span>Choose "Add to Home Screen", then "Add"</span>
                    )}
                  </li>
                </ol>
              ) : deferred ? (
                <div className="mt-2.5">
                  <button
                    onClick={install}
                    className="btn rounded-full bg-accent px-4 py-1.5 text-xs font-semibold text-bg"
                  >
                    {ar ? 'تثبيت التطبيق' : 'Install app'}
                  </button>
                </div>
              ) : (
                <p className="mt-2 text-xs leading-6 text-ink-muted">
                  {ar
                    ? 'من قائمة المتصفح (⋮) اختر «إضافة إلى الشاشة الرئيسية».'
                    : 'From the browser menu (⋮), choose "Add to Home Screen".'}
                </p>
              )}
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
