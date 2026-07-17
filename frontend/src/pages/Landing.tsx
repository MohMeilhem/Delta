import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  Bank,
  Broadcast,
  Buildings,
  Check,
  ChartLine,
  SealCheck,
  CurrencyDollar,
  ForkKnife,
  GlobeHemisphereEast,
  HeartStraight,
  Lightning,
  ChartBar,
  Robot,
  Scales,
  Sparkle,
  TrendUp,
  Warning,
} from '@phosphor-icons/react'
import {
  motion,
  useReducedMotion,
  useScroll,
  useTransform,
  useMotionValue,
  animate,
} from 'motion/react'
import { api } from '../api'
import { fmt } from '../format'
import { useLang } from '../i18n'

type BillingCycle = 'monthly' | 'yearly'
type FormState = { name: string; email: string; company: string }
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
      ['12', 'أرباع للمراقبة'],
    ],
    problemTitle: 'المشكلة',
    problemCards: [
      ['40 ساعة أسبوعياً لكل محترف تقريباً', 'يقضي المحلل المحترف نحو 40 ساعة أسبوعياً في بناء النماذج المالية يدوياً.'],
      ['+100,000 ريال سنوياً', 'الأدوات العالمية تتجاوز 100,000 ريال سنوياً للمستخدم، وغالباً ما تكون موجّهة بالإنجليزية.'],
      ['لا تفهم السوق السعودية', 'أدوات السوق التقليدية لا تفهم خصوصية السعودية: الزكاة ليست ضريبة، والصكوك ليست سندات.'],
    ],
    solutionTitle: 'كيف تعمل دلتا',
    solutionSteps: [
      ['اختر شركة', 'اختر شركة من 33 شركة عبر 9 قطاعات مدرجة في المنصة.'],
      ['النموذج يُبنى آلياً', 'يبني الذكاء الاصطناعي النموذج المالي الكامل في ثوانٍ: التوقع الأساسي والقيمة العادلة.'],
      ['عدّل الفرضيات', 'يعدّل المحلل الفرضيات عبر الشرائح التفاعلية مع إعادة التقييم فوراً.'],
      ['الدلتا هي القيمة', 'الفجوة بين خط المحلل وخط الآلة هي "الدلتا" — قيمة المنتج الأساسية.'],
    ],
    differentiatorsTitle: 'ما يميز دلتا للسوق السعودي',
    differentiators: [
      ['الزكاة كبند فعلي', 'الزكاة تظهر كبند فعلي داخل محرك التقييم بنسبة 2.5% من الوعاء الزكوي.'],
      ['نموذج المصارف الإسلامية', 'نموذج مستقل للمصارف الإسلامية يعتمد على دخل التمويل، لا الفوائد.'],
      ['الصكوك منفصلة', 'الصكوك منفصلة بوضوح عن الدين التقليدي في البيانات والتقييم.'],
    ],
    aiTitle: 'طبقات الذكاء الاصطناعي',
    aiLayers: [
      ['وكيل المراقبة', 'وكيل المراقبة يستخدم Z-score عبر 8 أرباع متتالية ويظهر التنبيهات تلقائياً عند فتح الشركة.'],
      ['السيناريوهات التوليدية', 'تصدر بطاقات متفائلة ومتشددة وبطاقة "ما الذي يكسر الفرضية" بصيغة JSON مضبوطة فقط.'],
    ],
    pricingTitle: 'الاشتراك',
    pricingSubtitle: 'تسعير B2B بالريال السعودي. جرّب، ثم اختر ما يناسب فريقك.',
    monthly: 'شهري',
    yearly: 'سنوي',
    saveTwoMonths: 'خصم 20%',
    popular: 'الأكثر شيوعًا',
    tiers: [
      { name: 'محلل فردي', priceMonthly: 99, priceYearly: 950, includes: ['مقعد واحد', 'كل القطاعات', 'تصدير التقارير'] },
      { name: 'فريق بحثي', priceMonthly: 499, priceYearly: 4790, includes: ['حتى 5 مقاعد', 'تنبيهات وكيل المراقبة', 'دعم أولوية'] },
      { name: 'مؤسسي', custom: true, includes: ['مقاعد غير محدودة', 'ربط بيانات داخلي', 'إدارة صلاحيات'] },
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
    monthly_hint: 'يمكنك التحويل إلى الاشتراك السنوي للحصول على خصم 20%.',
    yearly_hint: 'الفوترة السنوية تمنحك خصم 20% عن الاشتراك الشهري.',
    perMonth: 'شهريًا',
    yearlyBadge: 'خصم 20%',
    demoBadge: 'نسخة عرض للهاكاثون',
    baseline: 'خط الأساس',
    agent: 'الوكيل',
    liveModel: 'تحديث حي للنماذج',
    anomalyWatch: 'مراقبة تلقائية للانحرافات',
    heroPanelTitle: 'لوحة تداول بحثية',
    heroPanelBody: 'خط الأساس والفرضيات والتنبيهات تظهر في شاشة واحدة مع تحديث مباشر.',
    sectors: ['بنوك', 'طاقة', 'مواد', 'اتصالات', 'صحة', 'تجزئة', 'مرافق', 'غذاء', 'عقارات'],
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
      ['12', 'quarters monitored'],
    ],
    problemTitle: 'The problem',
    problemCards: [
      ['~40 hours a week per professional', 'A professional analyst spends about 40 hours a week building financial models manually.'],
      ['SAR 100k+ per year', 'Global tools cost more than SAR 100,000 per user each year and are English-first.'],
      ["Misses Saudi context", 'Most tools do not understand the Saudi market: zakat is not tax, sukuk are not bonds.'],
    ],
    solutionTitle: 'How Delta works',
    solutionSteps: [
      ['Pick a company', 'Pick one company from 33 names across 9 sectors.'],
      ['AI builds the model', 'AI builds the full financial model in seconds: baseline forecast plus fair value.'],
      ['Adjust assumptions', 'The analyst adjusts assumptions with sliders and the valuation updates live.'],
      ['The gap is the Delta', 'The gap between the analyst line and the machine line is the Delta, the core product.'],
    ],
    differentiatorsTitle: 'Saudi-first differentiators',
    differentiators: [
      ['Zakat as a line item', 'Zakat appears as a real valuation line item at 2.5% of the zakat base.'],
      ['Islamic bank model', 'A dedicated Islamic-bank model uses financing income, not interest.'],
      ['Sukuk separated', 'Sukuk are separated from conventional debt in the data and valuation stack.'],
    ],
    aiTitle: 'AI layers',
    aiLayers: [
      ['Monitoring agent', 'The monitoring agent uses Z-score anomaly detection across trailing 8 quarters and auto-flags when a company opens.'],
      ['Generative scenarios', 'Generative scenarios ship as bull, bear, and thesis-breaker cards in schema-validated JSON only.'],
    ],
    pricingTitle: 'Subscription',
    pricingSubtitle: 'B2B pricing in SAR. Start small, then scale with your team.',
    monthly: 'Monthly',
    yearly: 'Yearly',
    saveTwoMonths: 'Save 20%',
    popular: 'Most popular',
    tiers: [
      { name: 'Individual analyst', priceMonthly: 99, priceYearly: 950, includes: ['1 seat', 'All sectors', 'Report export'] },
      { name: 'Research team', priceMonthly: 499, priceYearly: 4790, includes: ['Up to 5 seats', 'Monitoring alerts', 'Priority support'] },
      { name: 'Enterprise', custom: true, includes: ['Unlimited seats', 'Internal data integration', 'Permission management'] },
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
    monthly_hint: 'Switch to yearly billing to save 20%.',
    yearly_hint: 'Yearly billing saves you 20% versus monthly.',
    perMonth: 'per month',
    yearlyBadge: 'Save 20%',
    demoBadge: 'Hackathon demo build',
    baseline: 'Baseline',
    agent: 'Agent',
    liveModel: 'Live model refresh',
    anomalyWatch: 'Automatic anomaly monitoring',
    heroPanelTitle: 'Research desk view',
    heroPanelBody: 'Baseline, assumptions, and alerts live in one screen with real-time updates.',
    sectors: ['Banks', 'Energy', 'Materials', 'Telecom', 'Healthcare', 'Retail', 'Utilities', 'Food', 'Real Estate'],
  },
} as const

function priceLabel(lang: 'ar' | 'en', value: number) {
  return lang === 'ar' ? `${fmt(value)} ريال` : `SAR ${fmt(value)}`
}

/* ── Animated counter ──────────────────────────────────────────────── */
function Counter({ to, suffix = '' }: { to: number; suffix?: string }) {
  const ref = useRef<HTMLSpanElement>(null)
  const val = useMotionValue(0)
  const reduce = useReducedMotion()

  useEffect(() => {
    if (reduce) { if (ref.current) ref.current.textContent = `${to}${suffix}`; return }
    const controls = animate(val, to, {
      duration: 1.6,
      ease: [0.23, 1, 0.32, 1],
      onUpdate: (v) => { if (ref.current) ref.current.textContent = `${Math.round(v)}${suffix}` },
    })
    return controls.stop
  }, [to, suffix, val, reduce])

  return <span ref={ref}>0{suffix}</span>
}

/* ── Decorative floating candlestick SVG (background art) ──────────── */
function CandlestickBg() {
  return (
    <svg viewBox="0 0 420 320" className="w-full h-full opacity-100" aria-hidden>
      <defs>
        <linearGradient id="cg-green" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="oklch(0.78 0.145 163)" stopOpacity="0.9" />
          <stop offset="100%" stopColor="oklch(0.55 0.12 163)" stopOpacity="0.5" />
        </linearGradient>
        <linearGradient id="cg-red" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="oklch(0.69 0.17 25)" stopOpacity="0.9" />
          <stop offset="100%" stopColor="oklch(0.5 0.14 25)" stopOpacity="0.5" />
        </linearGradient>
        <linearGradient id="cg-amber" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="oklch(0.83 0.13 85)" stopOpacity="0.8" />
          <stop offset="100%" stopColor="oklch(0.6 0.11 85)" stopOpacity="0.4" />
        </linearGradient>
        <filter id="cg-glow">
          <feGaussianBlur stdDeviation="2.5" result="blur" />
          <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>

      {/* Grid lines */}
      {[60,120,180,240,300].map(y => (
        <line key={y} x1="20" y1={y} x2="400" y2={y} stroke="currentColor" strokeWidth="0.5" strokeOpacity="0.06" strokeDasharray="4 8"/>
      ))}

      {/* Candle 1 – green */}
      <g filter="url(#cg-glow)" className="candle-float" style={{animationDelay:'0s'}}>
        <line x1="52" y1="60" x2="52" y2="200" stroke="url(#cg-green)" strokeWidth="1.5"/>
        <rect x="44" y="90" width="16" height="90" rx="2" fill="url(#cg-green)"/>
      </g>
      {/* Candle 2 – red */}
      <g filter="url(#cg-glow)" className="candle-float" style={{animationDelay:'0.4s'}}>
        <line x1="94" y1="80" x2="94" y2="220" stroke="url(#cg-red)" strokeWidth="1.5"/>
        <rect x="86" y="110" width="16" height="80" rx="2" fill="url(#cg-red)"/>
      </g>
      {/* Candle 3 – green big */}
      <g filter="url(#cg-glow)" className="candle-float" style={{animationDelay:'0.8s'}}>
        <line x1="136" y1="55" x2="136" y2="210" stroke="url(#cg-green)" strokeWidth="1.5"/>
        <rect x="128" y="75" width="16" height="110" rx="2" fill="url(#cg-green)"/>
      </g>
      {/* Candle 4 – amber */}
      <g filter="url(#cg-glow)" className="candle-float" style={{animationDelay:'1.2s'}}>
        <line x1="178" y1="70" x2="178" y2="195" stroke="url(#cg-amber)" strokeWidth="1.5"/>
        <rect x="170" y="95" width="16" height="75" rx="2" fill="url(#cg-amber)"/>
      </g>
      {/* Candle 5 – red small */}
      <g filter="url(#cg-glow)" className="candle-float" style={{animationDelay:'1.6s'}}>
        <line x1="220" y1="100" x2="220" y2="230" stroke="url(#cg-red)" strokeWidth="1.5"/>
        <rect x="212" y="125" width="16" height="75" rx="2" fill="url(#cg-red)"/>
      </g>
      {/* Candle 6 – green */}
      <g filter="url(#cg-glow)" className="candle-float" style={{animationDelay:'2s'}}>
        <line x1="262" y1="65" x2="262" y2="185" stroke="url(#cg-green)" strokeWidth="1.5"/>
        <rect x="254" y="85" width="16" height="80" rx="2" fill="url(#cg-green)"/>
      </g>
      {/* Candle 7 – green tall */}
      <g filter="url(#cg-glow)" className="candle-float" style={{animationDelay:'2.4s'}}>
        <line x1="304" y1="45" x2="304" y2="175" stroke="url(#cg-green)" strokeWidth="1.5"/>
        <rect x="296" y="60" width="16" height="95" rx="2" fill="url(#cg-green)"/>
      </g>
      {/* Candle 8 – amber */}
      <g filter="url(#cg-glow)" className="candle-float" style={{animationDelay:'2.8s'}}>
        <line x1="346" y1="55" x2="346" y2="170" stroke="url(#cg-amber)" strokeWidth="1.5"/>
        <rect x="338" y="75" width="16" height="75" rx="2" fill="url(#cg-amber)"/>
      </g>

      {/* Trend line (baseline) */}
      <path
        d="M30 190 Q100 175 180 155 T340 100"
        fill="none"
        stroke="oklch(0.78 0.145 163)"
        strokeWidth="2"
        strokeDasharray="6 4"
        strokeOpacity="0.5"
        strokeLinecap="round"
      />
      {/* Analyst line (above) */}
      <path
        d="M30 185 Q100 165 180 140 T340 78"
        fill="none"
        stroke="oklch(0.83 0.13 85)"
        strokeWidth="2"
        strokeDasharray="4 6"
        strokeOpacity="0.4"
        strokeLinecap="round"
      />

      {/* Delta triangle mark */}
      <polygon
        points="390,30 370,65 410,65"
        fill="oklch(0.78 0.145 163)"
        fillOpacity="0.15"
        stroke="oklch(0.78 0.145 163)"
        strokeOpacity="0.4"
        strokeWidth="1"
      />
    </svg>
  )
}

/* ── Animated hero delta chart (line draws in) ─────────────────────── */
function HeroDeltaChart({ lang }: { lang: 'ar' | 'en' }) {
  const copy = COPY[lang]
  const reduce = useReducedMotion()
  return (
    <svg viewBox="0 0 360 160" className="mt-4 h-40 w-full" role="img" aria-label={copy.heroPanelTitle}>
      <defs>
        <linearGradient id="heroFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="oklch(0.78 0.145 163)" stopOpacity="0.35" />
          <stop offset="100%" stopColor="oklch(0.78 0.145 163)" stopOpacity="0.02" />
        </linearGradient>
        <linearGradient id="deltaFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="oklch(0.83 0.13 85)" stopOpacity="0.22" />
          <stop offset="100%" stopColor="oklch(0.83 0.13 85)" stopOpacity="0.02" />
        </linearGradient>
        <filter id="glow-g">
          <feGaussianBlur stdDeviation="3" result="b"/>
          <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
        <filter id="glow-a">
          <feGaussianBlur stdDeviation="3" result="b"/>
          <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
        {/* Clipping mask for line draw-in animation */}
        <clipPath id="reveal-clip">
          <motion.rect
            x="0" y="0" height="160"
            initial={{ width: 0 }}
            animate={{ width: 360 }}
            transition={{ duration: reduce ? 0 : 1.8, ease: [0.23, 1, 0.32, 1], delay: 0.3 }}
          />
        </clipPath>
      </defs>

      {/* Axis lines */}
      <line x1="18" y1="18" x2="18" y2="132" stroke="currentColor" strokeWidth="1" strokeOpacity="0.2" />
      <line x1="18" y1="132" x2="344" y2="132" stroke="currentColor" strokeWidth="1" strokeOpacity="0.2" />
      {/* Grid */}
      {[55, 90, 110].map(y => (
        <line key={y} x1="18" y1={y} x2="344" y2={y} stroke="currentColor" strokeWidth="0.6" strokeOpacity="0.1" strokeDasharray="4 6"/>
      ))}

      {/* Baseline area + line */}
      <g clipPath="url(#reveal-clip)">
        <path d="M18 108 C60 102, 90 96, 120 98 S168 86, 196 76 S244 50, 272 54 S312 64, 344 42 L344 132 L18 132 Z"
          fill="url(#heroFill)" />
        <path d="M18 108 C60 102, 90 96, 120 98 S168 86, 196 76 S244 50, 272 54 S312 64, 344 42"
          fill="none" stroke="oklch(0.78 0.145 163)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
          filter="url(#glow-g)" />
      </g>

      {/* Analyst line (dashed, above) */}
      <g clipPath="url(#reveal-clip)">
        <path d="M18 105 C60 90, 90 84, 120 88 S168 70, 196 60 S244 34, 272 38 S312 48, 344 24"
          fill="url(#deltaFill)"/>
        <path d="M18 105 C60 90, 90 84, 120 88 S168 70, 196 60 S244 34, 272 38 S312 48, 344 24"
          fill="none" stroke="oklch(0.83 0.13 85)" strokeWidth="2.2" strokeDasharray="7 5"
          strokeLinecap="round" strokeLinejoin="round" filter="url(#glow-a)"/>
      </g>

      {/* Delta gap shading */}
      <g clipPath="url(#reveal-clip)" opacity="0.45">
        <path d="M18 108 C60 102, 90 96, 120 98 S168 86, 196 76 S244 50, 272 54 S312 64, 344 42
                 L344 24 S312 48, 272 38 S244 34, 196 60 S168 70, 120 88 S90 84, 60 90 L18 105 Z"
          fill="oklch(0.83 0.13 85 / 0.12)" />
      </g>

      {/* End dots */}
      <motion.circle cx="344" cy="42" r="4" fill="oklch(0.78 0.145 163)"
        initial={{ scale: 0 }} animate={{ scale: 1 }}
        transition={{ duration: 0.4, delay: reduce ? 0 : 2.0, ease: [0.23, 1, 0.32, 1] }} />
      <motion.circle cx="344" cy="24" r="4" fill="oklch(0.83 0.13 85)"
        initial={{ scale: 0 }} animate={{ scale: 1 }}
        transition={{ duration: 0.4, delay: reduce ? 0 : 2.05, ease: [0.23, 1, 0.32, 1] }} />

      {/* Labels */}
      <motion.g initial={{ opacity: 0 }} animate={{ opacity: 1 }}
        transition={{ delay: reduce ? 0 : 2.1, duration: 0.4 }}>
        <rect x="348" y="36" width="8" height="8" rx="1" fill="oklch(0.78 0.145 163)" fillOpacity="0.9"/>
        <rect x="348" y="18" width="8" height="8" rx="1" fill="oklch(0.83 0.13 85)" fillOpacity="0.9"/>
      </motion.g>
    </svg>
  )
}

/* ── Sector orbit ring (decorative) ───────────────────────────────── */
const SECTOR_ICONS_LANDING = [Bank, Lightning, ChartBar, Broadcast, HeartStraight, Scales, CurrencyDollar, ForkKnife, Buildings]

function SectorOrbit({ lang }: { lang: 'ar' | 'en' }) {
  const sectors = COPY[lang].sectors
  const reduce = useReducedMotion()
  return (
    <div className="relative mx-auto h-56 w-56 sm:h-64 sm:w-64">
      {/* Centre delta glyph */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-accent/30 to-accent-dim/40 border border-accent/30 shadow-[0_0_32px_oklch(0.78_0.145_163/0.25)]">
          <ChartLine size={36} weight="duotone" className="text-accent" />
        </div>
      </div>
      {/* Orbit ring */}
      <motion.div
        className="absolute inset-0"
        animate={reduce ? {} : { rotate: 360 }}
        transition={{ duration: 28, ease: 'linear', repeat: Infinity }}
      >
        {SECTOR_ICONS_LANDING.map((Icon, i) => {
          const angle = (i / SECTOR_ICONS_LANDING.length) * 360
          const rad = (angle * Math.PI) / 180
          const r = 100
          const cx = 50 + r * Math.cos(rad)
          const cy = 50 + r * Math.sin(rad)
          return (
            <div
              key={i}
              className="absolute flex h-9 w-9 items-center justify-center rounded-full border border-line bg-surface shadow-sm text-accent/60"
              style={{ left: `${cx}%`, top: `${cy}%`, transform: 'translate(-50%,-50%)' }}
              title={sectors[i]}
            >
              <Icon size={16} weight="duotone" />
            </div>
          )
        })}
      </motion.div>
      {/* Connecting ring line */}
      <svg className="absolute inset-0 h-full w-full" viewBox="0 0 200 200" aria-hidden>
        <circle cx="100" cy="100" r="100" fill="none" stroke="currentColor" strokeWidth="0.5" strokeOpacity="0.12" strokeDasharray="3 6"/>
      </svg>
    </div>
  )
}

/* ── Main Landing component ──────────────────────────────────────────── */
export default function Landing() {
  const { lang, dir } = useLang()
  const copy = COPY[lang]
  const pageRef = useRef<HTMLDivElement>(null)
  const [billing, setBilling] = useState<BillingCycle>('monthly')
  const [form, setForm] = useState<FormState>({ name: '', email: '', company: '' })
  const [status, setStatus] = useState<{ kind: 'idle' | 'success' | 'error'; text: string }>({ kind: 'idle', text: '' })
  const [submitting, setSubmitting] = useState(false)
  const tiers: Tier[] = copy.tiers.map((tier, i) => ({ ...tier, highlighted: i === 1 }))
  const reduce = useReducedMotion()
  const { scrollYProgress } = useScroll({ target: pageRef, offset: ['start start', 'end end'] })

  // Parallax transforms for BG orbs
  const orb1y = useTransform(scrollYProgress, [0, 1], ['0%', '30%'])
  const orb2y = useTransform(scrollYProgress, [0, 1], ['0%', '-20%'])

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setStatus({ kind: 'idle', text: '' })
    if (!form.email.trim() || !/^\S+@\S+\.\S+$/.test(form.email.trim())) {
      setStatus({ kind: 'error', text: copy.invalidEmail })
      return
    }
    setSubmitting(true)
    try {
      const res = await api.subscribe({ name: form.name, email: form.email, company: form.company })
      // localized copy, not the backend's fixed-language message string
      setStatus({ kind: 'success', text: res.status === 'duplicate' ? copy.duplicate : copy.success })
      if (res.status === 'created') setForm({ name: '', email: '', company: '' })
    } catch {
      setStatus({ kind: 'error', text: copy.genericError })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div ref={pageRef} className="relative overflow-hidden">

      {/* ── Scroll progress bar ──────────────────────────────────────── */}
      <div className="sticky top-0 z-30 h-[3px] overflow-hidden bg-surface/50">
        <motion.div
          className="h-full origin-left"
          style={{
            scaleX: scrollYProgress,
            background: 'linear-gradient(to right, oklch(0.78 0.145 163), oklch(0.83 0.13 85), oklch(0.78 0.145 163))',
          }}
        />
      </div>

      {/* ── Animated background orbs ─────────────────────────────────── */}
      <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden" aria-hidden>
        <motion.div
          className="orb orb-green"
          style={{ y: orb1y }}
        />
        <motion.div
          className="orb orb-amber"
          style={{ y: orb2y }}
        />
        <div className="orb orb-purple" />
        {/* Candlestick watermark */}
        <div className="absolute bottom-0 end-0 w-[480px] opacity-[0.045] translate-y-12">
          <CandlestickBg />
        </div>
        <div className="absolute top-[30%] start-0 w-[320px] opacity-[0.03] -translate-x-16">
          <CandlestickBg />
        </div>
      </div>

      {/* ── Hero ────────────────────────────────────────────────────────── */}
      <section className="relative z-10 mx-auto max-w-7xl px-6 pt-16 pb-20">
        <div className="grid gap-12 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">

          {/* Left: copy */}
          <div className="space-y-7">
            <motion.h1
              initial={reduce ? false : { opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.65, delay: 0.08, ease: [0.23, 1, 0.32, 1] }}
              className="display hero-gradient-text max-w-2xl text-4xl font-bold leading-[1.3] tracking-tight md:text-6xl xl:text-7xl"
            >
              {copy.hero}
            </motion.h1>

            <motion.p
              initial={reduce ? false : { opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.16, ease: [0.23, 1, 0.32, 1] }}
              className="max-w-xl text-base leading-8 text-ink-muted md:text-lg"
            >
              {copy.subhero}
            </motion.p>

            <motion.div
              initial={reduce ? false : { opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.55, delay: 0.22, ease: [0.23, 1, 0.32, 1] }}
              className="flex flex-wrap gap-3"
            >
              <Link
                to="/app"
                className="btn group inline-flex items-center gap-2.5 rounded-full bg-gradient-to-r from-accent to-accent/80 px-6 py-3.5 text-sm font-semibold text-bg shadow-[0_0_24px_oklch(0.78_0.145_163/0.35)] hover:shadow-[0_0_36px_oklch(0.78_0.145_163/0.5)] transition-shadow"
              >
                {copy.tryPlatform}
                <ArrowRight size={16} weight="bold" className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
              </Link>
              <a
                href="#subscribe"
                className="btn inline-flex items-center gap-2 rounded-full border border-line bg-surface/60 px-6 py-3.5 text-sm font-semibold text-ink backdrop-blur-sm hover:bg-surface hover:border-accent/30 transition-colors"
              >
                {copy.subscribeNow}
              </a>
            </motion.div>

            {/* Stats row */}
            <dl className="grid max-w-lg grid-cols-3 gap-3 pt-1">
              {copy.introStats.map(([value, label], i) => (
                <motion.div
                  key={label}
                  initial={reduce ? false : { opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.55, delay: 0.3 + i * 0.08, ease: [0.23, 1, 0.32, 1] }}
                  whileHover={reduce ? undefined : { y: -5, transition: { duration: 0.2 } }}
                  className="stat-card group"
                >
                  <dt className="text-[11px] text-ink-faint">{label}</dt>
                  <dd className="display mt-2 text-2xl font-bold text-accent">
                    <Counter to={parseInt(value)} />
                  </dd>
                </motion.div>
              ))}
            </dl>
          </div>

          {/* Right: hero panel */}
          <motion.div
            initial={reduce ? false : { opacity: 0, x: dir === 'rtl' ? -32 : 32, scale: 0.97 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            transition={{ duration: 0.75, delay: 0.1, ease: [0.23, 1, 0.32, 1] }}
            className="hero-panel"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-line/60 pb-4">
              <div>
                <div className="text-[11px] text-ink-faint uppercase tracking-widest">{copy.heroPanelTitle}</div>
                <div className="display mt-1 text-xl font-semibold">
                  {lang === 'ar' ? 'لوحة المنصة' : 'Platform desk'}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="live-badge">
                  <span className="live-dot" />
                  Live
                </span>
                <span className="rounded-full border border-accent/25 bg-accent/10 px-3 py-1 text-[11px] font-medium text-accent">
                  RTL / LTR
                </span>
              </div>
            </div>

            {/* Mini stat cards */}
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {[
                { label: copy.baseline, to: 33, sub: lang === 'ar' ? 'شركة' : 'companies', color: 'accent', icon: TrendUp },
                { label: copy.agent, to: 12, sub: lang === 'ar' ? 'أرباع' : 'quarters', color: 'analyst', icon: GlobeHemisphereEast },
              ].map(({ label, to, sub, color, icon: Icon }) => (
                <div key={label} className={`mini-stat-card border-${color}/20 bg-gradient-to-br from-${color}/12 via-surface to-surface-2`}>
                  <div className="text-[11px] text-ink-faint">{label}</div>
                  <div className="mt-3 flex items-baseline gap-2">
                    <span className={`display text-3xl font-bold text-${color}`}><Counter to={to} /></span>
                    <span className="text-sm text-ink-muted">{sub}</span>
                  </div>
                  <div className={`mt-2 flex items-center gap-1.5 text-[11px] text-${color}/70`}>
                    <Icon size={13} weight="bold" />
                    {color === 'accent' ? copy.liveModel : copy.anomalyWatch}
                  </div>
                </div>
              ))}
            </div>

            {/* Animated chart */}
            <div className="mt-4 rounded-2xl border border-line/50 bg-gradient-to-br from-surface via-surface to-accent/5 p-4">
              <div className="flex items-center justify-between text-[11px] text-ink-faint">
                <span className="flex items-center gap-2">
                  <span className="h-2 w-5 rounded-full bg-accent/70"/>
                  {copy.baseline}
                  <span className="h-px w-4 border-t-2 border-dashed border-analyst/70"/>
                  {copy.agent}
                </span>
                <span className="text-accent/60">Δ delta</span>
              </div>
              <HeroDeltaChart lang={lang} />
            </div>

            {/* Feature chips */}
            <div className="mt-4 grid grid-cols-3 gap-2.5">
              {[
                { icon: TrendUp, label: copy.liveModel, color: 'text-accent', bg: 'from-accent/10' },
                { icon: Sparkle, label: copy.agent, color: 'text-analyst', bg: 'from-analyst/10' },
                { icon: Warning, label: copy.anomalyWatch, color: 'text-warning', bg: 'from-warning/10' },
              ].map(({ icon: Icon, label, color, bg }) => (
                <div key={label} className={`rounded-xl border border-line/50 bg-gradient-to-br ${bg} via-surface to-surface-2 p-3`}>
                  <Icon size={14} weight={Icon === Sparkle ? 'fill' : 'bold'} className={color} />
                  <div className="mt-2 text-[10px] leading-4 text-ink-faint">{label}</div>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* ── Problem section ─────────────────────────────────────────────── */}
      <section className="relative z-10 mx-auto max-w-7xl px-6 py-20">
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.4 }}
          transition={{ duration: 0.55, ease: [0.23, 1, 0.32, 1] }}
          className="mb-10"
        >
          <div className="section-label">{lang === 'ar' ? '01' : '01'}</div>
          <h2 className="display mt-2 text-2xl font-bold md:text-4xl">{copy.problemTitle}</h2>
        </motion.div>

        <div className="grid gap-5 md:grid-cols-3">
          {copy.problemCards.map(([headline, text], i) => (
            <motion.div
              key={headline}
              initial={reduce ? false : { opacity: 0, y: 28 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{ duration: 0.6, delay: i * 0.1, ease: [0.23, 1, 0.32, 1] }}
              whileHover={reduce ? undefined : { y: -6, transition: { duration: 0.2 } }}
              className="problem-card"
            >
              <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-negative/20 to-negative/5 border border-negative/20 text-negative">
                <Warning size={22} weight="bold" />
              </div>
              <div className="display text-lg font-bold text-ink mb-2">{headline}</div>
              <p className="text-sm leading-7 text-ink-muted">{text}</p>
              <div className="mt-5 h-px bg-gradient-to-r from-negative/30 to-transparent" />
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────────────────────── */}
      <section className="relative z-10 py-20">
        {/* Full-bleed tonal band */}
        <div className="absolute inset-0 bg-gradient-to-b from-surface/0 via-surface/60 to-surface/0 border-y border-line/30" />
        <div className="relative mx-auto max-w-7xl px-6">
          <motion.div
            initial={reduce ? false : { opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.4 }}
            transition={{ duration: 0.55, ease: [0.23, 1, 0.32, 1] }}
            className="mb-10"
          >
            <div className="section-label">02</div>
            <h2 className="display mt-2 text-2xl font-bold md:text-4xl">{copy.solutionTitle}</h2>
          </motion.div>

          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
            {copy.solutionSteps.map(([headline, text], i) => (
              <motion.div
                key={headline}
                initial={reduce ? false : { opacity: 0, y: 28 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.25 }}
                transition={{ duration: 0.6, delay: i * 0.1, ease: [0.23, 1, 0.32, 1] }}
                whileHover={reduce ? undefined : { y: -6, transition: { duration: 0.2 } }}
                className="step-card"
              >
                <div className="step-number">0{i + 1}</div>
                <div className="display mt-4 text-base font-bold text-ink">{headline}</div>
                <p className="mt-2 text-sm leading-7 text-ink-muted">{text}</p>
                {/* Connector dot (not on last) */}
                {i < 3 && <div className="connector-dot" />}
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Saudi-first + AI layers ──────────────────────────────────────── */}
      <section className="relative z-10 mx-auto max-w-7xl px-6 py-20">
        <div className="grid gap-8 lg:grid-cols-[1fr_1fr] lg:items-start">

          {/* Differentiators */}
          <motion.div
            initial={reduce ? false : { opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.25 }}
            transition={{ duration: 0.6, ease: [0.23, 1, 0.32, 1] }}
            className="feature-block from-accent/6"
          >
            <div className="section-label">03</div>
            <h2 className="display mt-2 text-xl font-bold md:text-2xl">{copy.differentiatorsTitle}</h2>
            <div className="mt-6 grid gap-3">
              {copy.differentiators.map(([headline, text], i) => (
                <motion.div
                  key={headline}
                  initial={reduce ? false : { opacity: 0, x: dir === 'rtl' ? 16 : -16 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true, amount: 0.5 }}
                  transition={{ duration: 0.45, delay: i * 0.07, ease: [0.23, 1, 0.32, 1] }}
                  whileHover={reduce ? undefined : { x: dir === 'rtl' ? -3 : 3, transition: { duration: 0.18 } }}
                  className="feature-row"
                >
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent/15 border border-accent/20">
                    <Check size={14} weight="bold" className="text-accent" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-ink">{headline}</div>
                    <div className="mt-0.5 text-xs leading-5 text-ink-muted">{text}</div>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* AI layers + orbit */}
          <motion.div
            initial={reduce ? false : { opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.25 }}
            transition={{ duration: 0.6, delay: 0.1, ease: [0.23, 1, 0.32, 1] }}
            className="feature-block from-analyst/6 relative overflow-hidden"
          >
            <div className="section-label">04</div>
            <h2 className="display mt-2 text-xl font-bold md:text-2xl">{copy.aiTitle}</h2>

            {/* Orbit ring as full-bleed background behind cards */}
            <div className="pointer-events-none absolute inset-0 flex items-center justify-center opacity-35" aria-hidden>
              <div className="scale-[2.2]">
                <SectorOrbit lang={lang} />
              </div>
            </div>

            <div className="relative z-10 mt-6 grid gap-3">
              {copy.aiLayers.map(([headline, text], i) => (
                <motion.div
                  key={headline}
                  initial={reduce ? false : { opacity: 0, y: 14 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, amount: 0.5 }}
                  transition={{ duration: 0.45, delay: i * 0.1, ease: [0.23, 1, 0.32, 1] }}
                  className="ai-layer-card"
                >
                  <Robot size={18} weight="duotone" className="shrink-0 text-analyst" />
                  <div>
                    <div className="text-sm font-semibold text-ink">{headline}</div>
                    <p className="mt-0.5 text-xs leading-5 text-ink-muted">{text}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* ── Pricing ──────────────────────────────────────────────────────── */}
      <section id="subscribe" className="relative z-10 py-20">
        <div className="absolute inset-0 bg-gradient-to-b from-surface/0 via-surface/50 to-surface/0 border-y border-line/30" />
        <div className="relative mx-auto max-w-7xl px-6">
          <motion.div
            initial={reduce ? false : { opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.4 }}
            transition={{ duration: 0.55, ease: [0.23, 1, 0.32, 1] }}
            className="mb-8"
          >
            <div className="section-label">05</div>
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <h2 className="display mt-2 text-2xl font-bold md:text-4xl">{copy.pricingTitle}</h2>
                <p className="mt-2 max-w-xl text-sm text-ink-muted">{copy.pricingSubtitle}</p>
              </div>
              {/* Billing toggle */}
              <div className="flex rounded-full border border-line bg-surface p-1 text-sm shadow-sm">
                {(['monthly', 'yearly'] as const).map((cycle) => (
                  <button
                    key={cycle}
                    onClick={() => setBilling(cycle)}
                    className={`btn inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-5 py-2 font-semibold transition-all ${
                      billing === cycle
                        ? 'bg-gradient-to-r from-accent to-accent/80 text-bg shadow-sm'
                        : 'text-ink-muted hover:text-ink'
                    }`}
                  >
                    {cycle === 'monthly' ? copy.monthly : copy.yearly}
                    {cycle === 'yearly' && (
                      <span className={`rounded-full px-1.5 py-0.5 text-[10px] leading-none ${billing === 'yearly' ? 'bg-bg/20 text-bg' : 'bg-accent/15 text-accent'}`}>
                        {copy.yearlyBadge}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          </motion.div>

          <div className="grid gap-5 xl:grid-cols-3">
            {tiers.map((tier, i) => {
              const price = billing === 'monthly' ? tier.priceMonthly : tier.priceYearly
              return (
                <motion.div
                  key={tier.name}
                  initial={reduce ? false : { opacity: 0, y: 28 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, amount: 0.25 }}
                  transition={{ duration: 0.6, delay: i * 0.1, ease: [0.23, 1, 0.32, 1] }}
                  whileHover={reduce ? undefined : { y: -8, transition: { duration: 0.2 } }}
                  className={`pricing-card ${tier.highlighted ? 'pricing-card-highlighted' : ''}`}
                >
                  {tier.highlighted && (
                    <div className="popular-badge">{copy.popular}</div>
                  )}
                  <div className="text-sm font-semibold text-ink-muted">{tier.name}</div>
                  <div className="mt-4 min-h-[72px]">
                    {tier.custom ? (
                      <div className="display text-3xl font-bold text-ink">{lang === 'ar' ? 'تواصل معنا' : 'Contact us'}</div>
                    ) : (
                      <>
                        <div className="display text-4xl font-bold">{priceLabel(lang, price ?? 0)}</div>
                        <div className="mt-1 text-xs text-ink-faint">
                          {billing === 'yearly' ? copy.yearlyBadge : copy.perMonth}
                        </div>
                      </>
                    )}
                  </div>
                  <div className="my-5 h-px bg-gradient-to-r from-transparent via-line to-transparent" />
                  <ul className="space-y-3">
                    {tier.includes.map((item) => (
                      <li key={item} className="flex items-center gap-2.5 text-sm text-ink-muted">
                        <SealCheck size={16} weight="fill" className="shrink-0 text-accent" />
                        {item}
                      </li>
                    ))}
                  </ul>
                  <div className="mt-6">
                    {tier.custom ? (
                      <a href="#subscribe" className="pricing-btn-outline">{lang === 'ar' ? 'تواصل معنا' : 'Get in touch'}</a>
                    ) : (
                      <a href="#subscribe" className={`pricing-btn ${tier.highlighted ? 'pricing-btn-primary' : 'pricing-btn-outline'}`}>
                        {lang === 'ar' ? 'ابدأ الآن' : 'Get started'}
                      </a>
                    )}
                  </div>
                  <p className="mt-3 text-center text-[11px] text-ink-faint">{copy.noGateway}</p>
                </motion.div>
              )
            })}
          </div>
        </div>
      </section>

      {/* ── Early access form ─────────────────────────────────────────────── */}
      <section className="relative z-10 mx-auto max-w-7xl px-6 py-20">
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6, ease: [0.23, 1, 0.32, 1] }}
          className="cta-block"
        >
          {/* Background glow */}
          <div className="pointer-events-none absolute inset-0 rounded-3xl overflow-hidden">
            <div className="absolute -top-16 -start-16 h-64 w-64 rounded-full bg-accent/12 blur-3xl" />
            <div className="absolute -bottom-16 -end-16 h-64 w-64 rounded-full bg-analyst/10 blur-3xl" />
          </div>

          <div className="relative grid gap-10 lg:grid-cols-2 lg:items-center">
            <div className="space-y-4">
              <div className="section-label">06</div>
              <h2 className="display text-2xl font-bold md:text-3xl">{copy.formTitle}</h2>
              <p className="text-sm leading-7 text-ink-muted">{copy.formHint}</p>
              <div className="mt-4 flex items-center gap-3 text-xs text-ink-faint">
                <SealCheck size={16} weight="fill" className="text-accent" />
                {lang === 'ar' ? 'بدون بطاقة ائتمان' : 'No credit card required'}
                <span className="opacity-40">·</span>
                <SealCheck size={16} weight="fill" className="text-accent" />
                {lang === 'ar' ? 'تواصل بالعربية' : 'Arabic-first support'}
              </div>
            </div>

            <form onSubmit={submit} className="space-y-3" noValidate>
              {[
                { key: 'name', label: copy.name, type: 'text', autoComplete: 'name' },
                { key: 'email', label: copy.email, type: 'email', autoComplete: 'email' },
                { key: 'company', label: copy.company, type: 'text', autoComplete: 'organization' },
              ].map(({ key, label, type, autoComplete }) => (
                <div key={key}>
                  <label className="mb-1 block text-xs font-medium text-ink-muted">{label}</label>
                  <input
                    type={type}
                    autoComplete={autoComplete}
                    value={form[key as keyof FormState]}
                    onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                    className="form-input"
                    required={key === 'email'}
                  />
                </div>
              ))}

              {status.text && (
                <motion.p
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`rounded-xl border px-4 py-3 text-sm ${
                    status.kind === 'success'
                      ? 'border-accent/30 bg-accent/8 text-accent'
                      : 'border-negative/30 bg-negative/8 text-negative'
                  }`}
                >
                  {status.text}
                </motion.p>
              )}

              <button
                type="submit"
                disabled={submitting}
                className="btn w-full rounded-xl bg-gradient-to-r from-accent to-accent/80 py-3.5 text-sm font-semibold text-bg shadow-[0_0_24px_oklch(0.78_0.145_163/0.3)] hover:shadow-[0_0_36px_oklch(0.78_0.145_163/0.45)] transition-shadow disabled:opacity-60"
              >
                {submitting ? copy.submitting : copy.submit}
              </button>
            </form>
          </div>
        </motion.div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <footer className="relative z-10 border-t border-line/50 bg-surface/30 backdrop-blur-sm">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-6 py-6">
          <div className="flex items-center gap-2 text-sm text-ink-faint">
            <img src="/logo.svg" alt="" className="h-4 w-4 opacity-60" />
            <span>{copy.footerNote}</span>
          </div>
          <Link
            to="/app"
            className="btn inline-flex items-center gap-2 rounded-full border border-line bg-surface px-4 py-2 text-sm font-medium text-ink-muted hover:text-ink hover:border-accent/30 transition-colors"
          >
            {copy.footerApp}
            <ArrowRight size={14} weight="bold" />
          </Link>
        </div>
      </footer>
    </div>
  )
}
