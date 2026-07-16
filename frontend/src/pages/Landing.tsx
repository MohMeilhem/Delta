import { useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  Check,
  CircleNotch,
  GlobeHemisphereEast,
  Sparkle,
  TrendUp,
} from '@phosphor-icons/react'
import { motion, useReducedMotion, useScroll } from 'motion/react'
import { api } from '../api'
import { fmt } from '../format'
import { useLang } from '../i18n'

type BillingCycle = 'monthly' | 'yearly'

type FormState = {
  name: string
  email: string
  company: string
}

type Tier = {
  name: string
  priceMonthly?: number
  priceYearly?: number
  includes: string[]
  custom?: boolean
  highlighted?: boolean
}

const COPY = {
  ar: {
    kicker: 'مكتب أبحاث ذكي لسوق الأسهم السعودية',
    hero: 'مكتب أبحاث ذكي للأسهم السعودية',
    subhero:
      'دلتا يبني خط الأساس الآلي، ويترك للمحلل مساحة التعديل والتحقق. الفجوة بين خطك وخط المنصة هي قيمة العمل الحقيقية.',
    tryPlatform: 'جرّب المنصة',
    subscribeNow: 'اشترك الآن',
    introStats: [
      ['33', 'شركة مدرجة'],
      ['9', 'قطاعات سعودية'],
      ['8', 'أرباع للمراقبة'],
    ],
    problemTitle: 'المشكلة',
    problemCards: [
      'يقضي المحلل عادةً نحو 8 ساعات لكل شركة في بناء النموذج المالي يدوياً.',
      'الأدوات العالمية تتجاوز 100,000 ريال سنوياً للمستخدم، وغالباً ما تكون موجّهة بالكامل بالإنجليزية.',
      'أدوات السوق التقليدية لا تفهم خصوصية السعودية: الزكاة ليست ضريبة، والصكوك ليست سندات، والمصارف الإسلامية لا تعتمد على دخل الفوائد.',
    ],
    solutionTitle: 'كيف تعمل دلتا',
    solutionSteps: [
      'اختر شركة من 33 شركة عبر 9 قطاعات مدرجة في المنصة.',
      'يبني الذكاء الاصطناعي النموذج المالي الكامل في ثوانٍ: التوقع الأساسي والقيمة العادلة.',
      'يعدّل المحلل الفرضيات عبر الشرائح التفاعلية مع إعادة التقييم فوراً.',
      'الفجوة بين خط المحلل وخط الآلة هي “الدلتا” — قيمة المنتج الأساسية.',
    ],
    differentiatorsTitle: 'ما يميز دلتا للسوق السعودي',
    differentiators: [
      'الزكاة تظهر كبند فعلي داخل محرك التقييم بنسبة 2.5% من الوعاء الزكوي.',
      'نموذج مستقل للمصارف الإسلامية يعتمد على دخل التمويل، لا الفوائد.',
      'الصكوك منفصلة بوضوح عن الدين التقليدي في البيانات والتقييم.',
      'واجهة أصلية بالعربية RTL مع تبديل فوري إلى الإنجليزية بضغطة واحدة.',
    ],
    aiTitle: 'طبقات الذكاء الاصطناعي',
    aiLayers: [
      'وكيل المراقبة يستخدم Z-score عبر 8 أرباع متتالية ويظهر التنبيهات تلقائياً عند فتح الشركة.',
      'السيناريوهات التوليدية تصدر بطاقات متفائلة ومتشددة وبطاقة “ما الذي يكسر الفرضية” بصيغة JSON مضبوطة فقط.',
    ],
    pricingTitle: 'الاشتراك',
    pricingSubtitle: 'تسعير B2B بالريال السعودي. جرّب، ثم اختر ما يناسب فريقك.',
    monthly: 'شهري',
    yearly: 'سنوي',
    saveTwoMonths: 'وفّر شهرين',
    popular: 'الأكثر شيوعًا',
    tiers: [
      {
        name: 'محلل فردي',
        priceMonthly: 899,
        priceYearly: 8990,
        includes: ['مقعد واحد', 'كل القطاعات', 'تصدير التقارير'],
      },
      {
        name: 'فريق بحثي',
        priceMonthly: 3499,
        priceYearly: 34990,
        includes: ['حتى 5 مقاعد', 'تنبيهات وكيل المراقبة', 'دعم أولوية'],
      },
      {
        name: 'مؤسسي',
        custom: true,
        includes: ['مقاعد غير محدودة', 'ربط بيانات داخلي', 'إدارة صلاحيات'],
      },
    ] satisfies Tier[],
    formTitle: 'طلب وصول مبكر',
    formHint: 'اترك بيانات العمل وسنتواصل معك عند فتح الدفعات التجريبية.',
    name: 'الاسم الكامل',
    email: 'البريد العملي',
    company: 'الشركة',
    submit: 'طلب وصول مبكر',
    submitting: 'جارٍ الإرسال…',
    success: 'تم تسجيل طلبك بنجاح. سنرسل لك رسالة بالعربية قريباً.',
    duplicate: 'هذا البريد مسجّل بالفعل، وسنستخدم الطلب السابق للتواصل معك.',
    invalidEmail: 'يرجى إدخال بريد عمل صحيح.',
    genericError: 'تعذّر إرسال الطلب حالياً. حاول مرة أخرى.',
    footerNote: 'المنصة هنا لتجربة الهاكاثون وليست نسخة إنتاجية نهائية.',
    footerApp: 'الدخول إلى المنصة',
    noGateway: 'لا توجد بوابة دفع في هذا العرض',
    monthlyHint: 'يمكنك التحويل إلى الاشتراك السنوي لتوفير شهرين.',
    yearlyHint: 'الفوترة السنوية تعادل 10 أشهر فعلياً.',
    perMonth: 'شهريًا',
    yearlyBadge: 'وفّر شهرين',
    demoBadge: 'نسخة عرض للهاكاثون',
    baseline: 'خط الأساس',
    agent: 'الوكيل',
    liveModel: 'تحديث حي للنماذج',
    anomalyWatch: 'مراقبة تلقائية للانحرافات',
    heroPanelTitle: 'لوحة تداول بحثية',
    heroPanelBody: 'خط الأساس والفرضيات والتنبيهات تظهر في شاشة واحدة مع تحديث مباشر.',
  },
  en: {
    kicker: 'AI research desk for Saudi equities',
    hero: 'AI research desk for Saudi equities',
    subhero:
      'Delta builds the machine baseline and leaves the analyst in control. The gap between your line and the platform line is the real product value.',
    tryPlatform: 'Try the platform',
    subscribeNow: 'Subscribe now',
    introStats: [
      ['33', 'listed companies'],
      ['9', 'Saudi sectors'],
      ['8', 'quarters monitored'],
    ],
    problemTitle: 'The problem',
    problemCards: [
      'Analysts spend about 8 hours per company building models manually.',
      'Global tools cost more than SAR 100,000 per user each year and are English-first.',
      'Most tools do not understand the Saudi market: zakat is not tax, sukuk are not bonds, and Islamic banks do not rely on interest income.',
    ],
    solutionTitle: 'How Delta works',
    solutionSteps: [
      'Pick one company from 33 names across 9 sectors.',
      'AI builds the full financial model in seconds: baseline forecast plus fair value.',
      'The analyst adjusts assumptions with sliders and the valuation updates live.',
      'The gap between the analyst line and the machine line is the Delta, the core product.',
    ],
    differentiatorsTitle: 'Saudi-first differentiators',
    differentiators: [
      'Zakat appears as a real valuation line item at 2.5% of the zakat base.',
      'A dedicated Islamic-bank model uses financing income, not interest.',
      'Sukuk are separated from conventional debt in the data and valuation stack.',
      'Native Arabic RTL UI with a one-click English toggle.',
    ],
    aiTitle: 'AI layers',
    aiLayers: [
      'The monitoring agent uses Z-score anomaly detection across trailing 8 quarters and auto-flags when a company opens.',
      'Generative scenarios ship as bull, bear, and thesis-breaker cards in schema-validated JSON only.',
    ],
    pricingTitle: 'Subscription',
    pricingSubtitle: 'B2B pricing in SAR. Start small, then scale with your team.',
    monthly: 'Monthly',
    yearly: 'Yearly',
    saveTwoMonths: 'Save 2 months',
    popular: 'Most popular',
    tiers: [
      {
        name: 'Individual analyst',
        priceMonthly: 899,
        priceYearly: 8990,
        includes: ['1 seat', 'All sectors', 'Report export'],
      },
      {
        name: 'Research team',
        priceMonthly: 3499,
        priceYearly: 34990,
        includes: ['Up to 5 seats', 'Monitoring alerts', 'Priority support'],
      },
      {
        name: 'Enterprise',
        custom: true,
        includes: ['Unlimited seats', 'Internal data integration', 'Permission management'],
      },
    ] satisfies Tier[],
    formTitle: 'Request early access',
    formHint: 'Leave your work details and we will contact you when the pilot opens.',
    name: 'Full name',
    email: 'Work email',
    company: 'Company',
    submit: 'Request early access',
    submitting: 'Submitting…',
    success: 'Your request was received. We will contact you shortly.',
    duplicate: 'This email is already registered. We will use the previous request to reach out.',
    invalidEmail: 'Please enter a valid work email.',
    genericError: 'We could not submit your request right now. Please try again.',
    footerNote: 'This is a hackathon demo, not a production release.',
    footerApp: 'Open the platform',
    noGateway: 'No payment gateway in this demo',
    monthlyHint: 'Switch to yearly billing to save 2 months.',
    yearlyHint: 'Yearly billing equals 10 months of usage.',
    perMonth: 'per month',
    yearlyBadge: 'Save 2 months',
    demoBadge: 'Hackathon demo build',
    baseline: 'Baseline',
    agent: 'Agent',
    liveModel: 'Live model refresh',
    anomalyWatch: 'Automatic anomaly monitoring',
    heroPanelTitle: 'Research desk view',
    heroPanelBody: 'Baseline, assumptions, and alerts live in one screen with real-time updates.',
  },
} as const

function priceLabel(lang: 'ar' | 'en', value: number) {
  return lang === 'ar' ? `${fmt(value)} ريال` : `SAR ${fmt(value)}`
}

export default function Landing() {
  const { lang, dir } = useLang()
  const copy = COPY[lang]
  const pageRef = useRef<HTMLElement>(null)
  const [billing, setBilling] = useState<BillingCycle>('monthly')
  const [form, setForm] = useState<FormState>({ name: '', email: '', company: '' })
  const [status, setStatus] = useState<{ kind: 'idle' | 'success' | 'error'; text: string }>({
    kind: 'idle',
    text: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const tiers: Tier[] = copy.tiers.map((tier, index) => ({ ...tier, highlighted: index === 1 }))
  const reduce = useReducedMotion()
  const { scrollYProgress } = useScroll({ target: pageRef, offset: ['start start', 'end end'] })

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setStatus({ kind: 'idle', text: '' })
    if (!form.email.trim() || !/^\S+@\S+\.\S+$/.test(form.email.trim())) {
      setStatus({ kind: 'error', text: copy.invalidEmail })
      return
    }

    setSubmitting(true)
    try {
      const res = await api.subscribe({
        name: form.name,
        email: form.email,
        company: form.company,
      })
      setStatus({ kind: 'success', text: res.message })
      if (res.status === 'created') {
        setForm({ name: '', email: '', company: '' })
      }
    } catch {
      setStatus({ kind: 'error', text: copy.genericError })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main ref={pageRef} className="mx-auto max-w-7xl px-6 pb-16 pt-10">
      <div className="sticky top-0 z-20 h-1 overflow-hidden rounded-full bg-surface/70 backdrop-blur-sm">
        <motion.div className="h-full origin-left bg-accent" style={{ scaleX: scrollYProgress }} />
      </div>

      <section className="grid gap-8 pt-6 lg:grid-cols-[1.08fr_0.92fr] lg:items-end">
        <div className="space-y-6">
          <div className="inline-flex items-center gap-2 rounded-full border border-line bg-surface/80 px-3 py-1 text-xs text-ink-muted">
            <Sparkle size={14} weight="fill" className="text-accent" />
            {copy.kicker}
          </div>
          <div className="space-y-4">
            <h1 className="display max-w-3xl text-4xl font-bold leading-[1.05] tracking-tight md:text-6xl xl:text-7xl">
              {copy.hero}
            </h1>
            <p className="max-w-2xl text-base leading-8 text-ink-muted md:text-lg">{copy.subhero}</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              to="/app"
              className="btn inline-flex items-center gap-2 rounded-full bg-accent px-5 py-3 text-sm font-semibold text-bg shadow-sm hover:opacity-95"
            >
              {copy.tryPlatform}
              <ArrowRight size={16} weight="bold" />
            </Link>
            <a
              href="#subscribe"
              className="btn inline-flex items-center gap-2 rounded-full border border-line bg-surface px-5 py-3 text-sm font-semibold text-ink hover:bg-surface-2"
            >
              {copy.subscribeNow}
            </a>
          </div>
          <dl className="grid max-w-2xl grid-cols-3 gap-3 pt-2">
            {copy.introStats.map(([value, label], index) => (
              <motion.div
                key={label}
                initial={reduce ? false : { opacity: 0, y: 18 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.4 }}
                transition={{ duration: 0.55, delay: index * 0.08, ease: [0.23, 1, 0.32, 1] }}
                whileHover={reduce ? undefined : { y: -4 }}
                className="panel spotlight border-accent/15 bg-gradient-to-br from-accent/8 via-surface to-surface-2 p-4"
              >
                <dt className="text-[11px] text-ink-faint">{label}</dt>
                <dd className="display mt-2 text-2xl font-semibold">{value}</dd>
              </motion.div>
            ))}
          </dl>
        </div>
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 28, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.7, ease: [0.23, 1, 0.32, 1] }}
          className="panel-raised overflow-hidden border-line/80 p-5 lg:p-6"
        >
          <div className="flex items-center justify-between border-b border-line pb-4">
            <div>
              <div className="text-xs text-ink-faint">{copy.heroPanelTitle}</div>
              <div className="display mt-1 text-2xl font-semibold">
                {lang === 'ar' ? 'لوحة المنصة' : 'Platform desk'}
              </div>
            </div>
            <div className="rounded-full border border-accent-dim px-3 py-1 text-xs text-accent">RTL / LTR</div>
          </div>
          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <motion.div
              initial={reduce ? false : { opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.35 }}
              transition={{ duration: 0.55, delay: 0.05, ease: [0.23, 1, 0.32, 1] }}
              whileHover={reduce ? undefined : { y: -4 }}
              className="panel spotlight border-accent/20 bg-gradient-to-br from-accent/12 via-surface to-surface-2 p-4"
            >
              <div className="text-xs text-ink-faint">{copy.baseline}</div>
              <div className="mt-3 flex items-baseline gap-2">
                <span className="display text-3xl font-semibold text-accent">{lang === 'ar' ? '٣٣' : '33'}</span>
                <span className="text-sm text-ink-muted">{lang === 'ar' ? 'شركة' : 'companies'}</span>
              </div>
              <div className="mt-3 flex items-center gap-2 text-xs text-ink-faint">
                <TrendUp size={14} weight="bold" className="text-accent" />
                {copy.liveModel}
              </div>
            </motion.div>
            <motion.div
              initial={reduce ? false : { opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.35 }}
              transition={{ duration: 0.55, delay: 0.1, ease: [0.23, 1, 0.32, 1] }}
              whileHover={reduce ? undefined : { y: -4 }}
              className="panel spotlight border-analyst/20 bg-gradient-to-br from-analyst/12 via-surface to-surface-2 p-4"
            >
              <div className="text-xs text-ink-faint">{copy.agent}</div>
              <div className="mt-3 flex items-baseline gap-2">
                <span className="display text-3xl font-semibold text-analyst">{lang === 'ar' ? '٨' : '8'}</span>
                <span className="text-sm text-ink-muted">{lang === 'ar' ? 'أرباع' : 'quarters'}</span>
              </div>
              <div className="mt-3 flex items-center gap-2 text-xs text-ink-faint">
                <GlobeHemisphereEast size={14} weight="bold" className="text-analyst" />
                {copy.anomalyWatch}
              </div>
            </motion.div>
          </div>
          <div className="mt-4 rounded-2xl border border-line bg-gradient-to-br from-surface via-surface to-accent/5 p-4">
            <div className="flex items-center justify-between gap-3 text-xs text-ink-faint">
              <span>{copy.heroPanelBody}</span>
              <span className="rounded-full border border-line bg-surface px-2.5 py-1 text-[10px] text-accent">
                live
              </span>
            </div>
            <svg viewBox="0 0 360 140" className="mt-4 h-36 w-full" role="img" aria-label={copy.heroPanelTitle}>
              <defs>
                <linearGradient id="heroArea" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="currentColor" stopOpacity="0.28" />
                  <stop offset="100%" stopColor="currentColor" stopOpacity="0.02" />
                </linearGradient>
              </defs>
              <g className="text-line-strong" stroke="currentColor" strokeWidth="1" strokeOpacity="0.5">
                <line x1="16" y1="20" x2="16" y2="116" />
                <line x1="16" y1="116" x2="336" y2="116" />
                <line x1="16" y1="78" x2="336" y2="78" strokeDasharray="4 5" opacity="0.35" />
              </g>
              <path
                d="M16 98 C48 92, 72 86, 96 88 S144 78, 168 70 S216 42, 240 48 S288 58, 336 34 L336 116 L16 116 Z"
                fill="url(#heroArea)"
                className="text-accent"
              />
              <path
                d="M16 98 C48 92, 72 86, 96 88 S144 78, 168 70 S216 42, 240 48 S288 58, 336 34"
                fill="none"
                className="glow-baseline text-accent"
                stroke="currentColor"
                strokeWidth="2.4"
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              <path
                d="M16 96 C48 84, 72 78, 96 82 S144 66, 168 60 S216 30, 240 34 S288 46, 336 20"
                fill="none"
                className="glow-analyst text-analyst"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeDasharray="6 4"
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              <circle cx="336" cy="34" r="3.5" className="fill-accent" />
              <circle cx="336" cy="20" r="3.5" className="fill-analyst" />
            </svg>
            <div className="mt-3 grid grid-cols-3 gap-3 text-[11px] text-ink-faint">
              <div className="rounded-xl border border-accent/15 bg-gradient-to-br from-accent/10 via-surface to-surface-2 p-3">
                <div className="flex items-center gap-2 text-accent">
                  <TrendUp size={12} weight="bold" />
                  {copy.liveModel}
                </div>
                <div className="mt-2 text-ink-muted">{lang === 'ar' ? 'خط أساس حي' : 'Live baseline'}</div>
              </div>
              <div className="rounded-xl border border-analyst/15 bg-gradient-to-br from-analyst/10 via-surface to-surface-2 p-3">
                <div className="flex items-center gap-2 text-analyst">
                  <Sparkle size={12} weight="fill" />
                  {copy.agent}
                </div>
                <div className="mt-2 text-ink-muted">{lang === 'ar' ? 'تعديل الفرضيات' : 'Assumption edits'}</div>
              </div>
              <div className="rounded-xl border border-warning/20 bg-gradient-to-br from-warning/10 via-surface to-surface-2 p-3">
                <div className="flex items-center gap-2 text-warning">
                  <GlobeHemisphereEast size={12} weight="bold" />
                  {copy.anomalyWatch}
                </div>
                <div className="mt-2 text-ink-muted">{lang === 'ar' ? 'تنبيهات فورية' : 'Instant alerts'}</div>
              </div>
            </div>
          </div>
        </motion.div>
      </section>

      <section className="mt-16 grid gap-4">
        <motion.h2
          initial={reduce ? false : { opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1] }}
          className="display text-2xl font-semibold md:text-3xl"
        >
          {copy.problemTitle}
        </motion.h2>
        <div className="grid gap-4 md:grid-cols-3">
          {copy.problemCards.map((text, index) => (
            <motion.div
              key={text}
              initial={reduce ? false : { opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.35 }}
              transition={{ duration: 0.55, delay: index * 0.08, ease: [0.23, 1, 0.32, 1] }}
              whileHover={reduce ? undefined : { y: -5 }}
              className={`panel spotlight p-5 ${index === 1 ? 'border-accent/20 bg-gradient-to-br from-accent/10 via-surface to-surface-2' : 'bg-gradient-to-br from-surface via-surface to-surface-2'}`}
            >
              <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-full border border-line bg-surface-2 text-sm font-semibold text-accent">
                0{index + 1}
              </div>
              <p className="text-sm leading-7 text-ink-muted">{text}</p>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="mt-16 grid gap-4">
        <motion.h2
          initial={reduce ? false : { opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1] }}
          className="display text-2xl font-semibold md:text-3xl"
        >
          {copy.solutionTitle}
        </motion.h2>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {copy.solutionSteps.map((text, index) => (
            <motion.div
              key={text}
              initial={reduce ? false : { opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.35 }}
              transition={{ duration: 0.55, delay: index * 0.08, ease: [0.23, 1, 0.32, 1] }}
              whileHover={reduce ? undefined : { y: -5 }}
              className={`panel-raised spotlight p-5 ${index === 2 ? 'border-warning/20 bg-gradient-to-br from-warning/10 via-surface to-surface-2' : 'bg-gradient-to-br from-surface via-surface to-surface-2'}`}
            >
              <div className="display text-3xl font-semibold text-accent">0{index + 1}</div>
              <p className="mt-4 text-sm leading-7 text-ink-muted">{text}</p>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="mt-16 grid gap-4 lg:grid-cols-2">
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 18 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.55, ease: [0.23, 1, 0.32, 1] }}
          className="panel p-6 bg-gradient-to-br from-accent/8 via-surface to-surface-2"
        >
          <h2 className="display text-2xl font-semibold md:text-3xl">{copy.differentiatorsTitle}</h2>
          <div className="mt-5 grid gap-3">
            {copy.differentiators.map((text, index) => (
              <motion.div
                key={text}
                initial={reduce ? false : { opacity: 0, x: dir === 'rtl' ? 16 : -16 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, amount: 0.5 }}
                transition={{ duration: 0.45, delay: index * 0.06, ease: [0.23, 1, 0.32, 1] }}
                className="flex items-start gap-3 rounded-xl border border-line bg-surface/70 p-4"
              >
                <Check size={18} weight="bold" className="mt-0.5 shrink-0 text-accent" />
                <p className="text-sm leading-7 text-ink-muted">{text}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 18 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.55, ease: [0.23, 1, 0.32, 1], delay: 0.08 }}
          className="panel p-6 bg-gradient-to-br from-analyst/8 via-surface to-surface-2"
        >
          <h2 className="display text-2xl font-semibold md:text-3xl">{copy.aiTitle}</h2>
          <div className="mt-5 grid gap-3">
            {copy.aiLayers.map((text, index) => (
              <motion.div
                key={text}
                initial={reduce ? false : { opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.5 }}
                transition={{ duration: 0.45, delay: index * 0.08, ease: [0.23, 1, 0.32, 1] }}
                className="rounded-xl border border-line bg-surface/70 p-4"
              >
                <p className="text-sm leading-7 text-ink-muted">{text}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      <section id="subscribe" className="mt-16">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="display text-2xl font-semibold md:text-3xl">{copy.pricingTitle}</h2>
            <p className="mt-2 max-w-2xl text-sm leading-7 text-ink-muted">{copy.pricingSubtitle}</p>
          </div>
          <div className="flex rounded-full border border-line bg-surface p-1 text-sm">
            {(['monthly', 'yearly'] as const).map((cycle) => (
              <button
                key={cycle}
                type="button"
                onClick={() => setBilling(cycle)}
                className={`btn rounded-full px-4 py-2 font-semibold ${billing === cycle ? 'bg-accent text-bg' : 'text-ink-muted hover:text-ink'}`}
              >
                {cycle === 'monthly' ? copy.monthly : copy.yearly}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-5 grid gap-4 xl:grid-cols-3">
          {tiers.map((tier) => {
            const price = billing === 'monthly' ? tier.priceMonthly : tier.priceYearly
            return (
              <motion.div
                key={tier.name}
                initial={reduce ? false : { opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.3 }}
                transition={{ duration: 0.55, ease: [0.23, 1, 0.32, 1] }}
                whileHover={reduce ? undefined : { y: -5 }}
                className={`panel spotlight p-6 ${tier.highlighted ? 'border-accent/80 bg-gradient-to-br from-accent/12 via-surface to-surface-2 shadow-sm' : 'bg-gradient-to-br from-surface via-surface to-surface-2'}`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="text-sm font-semibold text-ink-muted">{tier.name}</div>
                    {tier.highlighted && (
                      <div className="mt-2 inline-flex rounded-full border border-accent-dim px-2.5 py-0.5 text-[11px] text-accent">
                        {copy.popular}
                      </div>
                    )}
                  </div>
                  {!tier.custom && (
                    <div className="text-end">
                      <div className="display text-3xl font-semibold">{priceLabel(lang, price ?? 0)}</div>
                      <div className="mt-1 text-xs text-ink-faint">
                        {billing === 'yearly' ? copy.yearlyBadge : copy.perMonth}
                      </div>
                    </div>
                  )}
                </div>
                <div className="mt-5 space-y-3">
                  {tier.includes.map((item) => (
                    <div key={item} className="flex items-center gap-2 text-sm text-ink-muted">
                      <Check size={14} weight="bold" className="text-accent" />
                      {item}
                    </div>
                  ))}
                </div>
                {tier.custom ? (
                  <div className="mt-6 rounded-xl border border-line bg-surface-2 p-4 text-sm text-ink-muted">
                    {lang === 'ar' ? 'تسعير مخصص — تواصل معنا' : 'Custom pricing — contact us'}
                  </div>
                ) : (
                  <div className="mt-6 rounded-xl border border-line bg-surface-2 p-4 text-sm text-ink-muted">
                    {billing === 'yearly' ? copy.yearlyHint : copy.monthlyHint}
                  </div>
                )}
              </motion.div>
            )
          })}
        </div>

        <motion.div
          initial={reduce ? false : { opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.25 }}
          transition={{ duration: 0.55, ease: [0.23, 1, 0.32, 1] }}
          className="mt-6 panel-raised p-6"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="display text-xl font-semibold">{copy.formTitle}</h3>
              <p className="mt-2 text-sm leading-7 text-ink-muted">{copy.formHint}</p>
            </div>
            <div className="text-xs text-ink-faint">{copy.noGateway}</div>
          </div>
          <form onSubmit={submit} noValidate className="mt-5 grid gap-3 lg:grid-cols-3">
            <input
              value={form.name}
              onChange={(e) => setForm((s) => ({ ...s, name: e.target.value }))}
              className="btn rounded-xl border border-line bg-bg px-4 py-3 text-sm outline-none placeholder:text-ink-faint focus:border-accent"
              placeholder={copy.name}
              aria-label={copy.name}
            />
            <input
              value={form.email}
              onChange={(e) => setForm((s) => ({ ...s, email: e.target.value }))}
              className="btn rounded-xl border border-line bg-bg px-4 py-3 text-sm outline-none placeholder:text-ink-faint focus:border-accent"
              placeholder={copy.email}
              aria-label={copy.email}
              inputMode="email"
            />
            <input
              value={form.company}
              onChange={(e) => setForm((s) => ({ ...s, company: e.target.value }))}
              className="btn rounded-xl border border-line bg-bg px-4 py-3 text-sm outline-none placeholder:text-ink-faint focus:border-accent"
              placeholder={copy.company}
              aria-label={copy.company}
            />
            <div className="flex flex-wrap items-center gap-3 pt-1 lg:col-span-3">
              <button
                type="submit"
                disabled={submitting}
                className="btn inline-flex items-center gap-2 rounded-full bg-accent px-5 py-3 text-sm font-semibold text-bg disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submitting && <CircleNotch size={16} className="animate-spin" weight="bold" />}
                {submitting ? copy.submitting : copy.submit}
              </button>
              {status.text && (
                <div
                  className={`rounded-full border px-4 py-2 text-sm ${status.kind === 'error' ? 'border-negative/40 bg-negative/10 text-negative' : 'border-accent-dim bg-gradient-to-r from-accent/15 to-analyst/10 text-accent'}`}
                >
                  {status.text}
                </div>
              )}
            </div>
          </form>
        </motion.div>
      </section>

      <footer className="mt-16 border-t border-line pt-6 text-sm text-ink-muted">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="display text-lg font-semibold">{lang === 'ar' ? 'دلتا' : 'Delta'}</div>
            <p className="mt-1 max-w-2xl leading-7">{copy.footerNote}</p>
          </div>
          <div className={`flex flex-wrap gap-3 ${dir === 'rtl' ? 'text-right' : 'text-left'}`}>
            <Link to="/app" className="text-accent hover:underline">
              {copy.footerApp}
            </Link>
            <span>{copy.demoBadge}</span>
          </div>
        </div>
      </footer>
    </main>
  )
}
