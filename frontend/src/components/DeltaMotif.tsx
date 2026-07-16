import { motion, useReducedMotion } from 'motion/react'
import { useLang } from '../i18n'
import { EASE } from './ui'

/**
 * The product thesis as a drawing — Delta's signature mark: shared history
 * splits into the machine baseline (green) and the analyst's line (amber);
 * the shaded gap between them IS the delta. Drawn, not told.
 * Charts stay LTR regardless of page direction, matching the app convention.
 */
export default function DeltaMotif({ className = '' }: { className?: string }) {
  const { t } = useLang()
  const reduce = useReducedMotion()

  const draw = (delay: number, duration: number) =>
    reduce
      ? {}
      : {
          initial: { pathLength: 0 },
          animate: { pathLength: 1 },
          transition: { duration, delay, ease: EASE },
        }

  return (
    <figure className={className}>
      <div dir="ltr" className="screen p-4">
        <svg viewBox="0 0 480 210" className="w-full" role="img" aria-label={t.delta}>
          {/* faint horizontal grid */}
          {[45, 90, 135, 180].map((y) => (
            <line key={y} x1="16" x2="464" y1={y} y2={y} className="stroke-line" strokeWidth="1" opacity="0.5" />
          ))}
          {/* forecast boundary */}
          <line x1="215" x2="215" y1="24" y2="192" className="stroke-line-strong" strokeWidth="1" strokeDasharray="3 4" />

          {/* the delta gap */}
          <motion.path
            d="M 215 110 L 285 102 L 355 96 L 460 88 L 460 40 L 355 66 L 285 88 Z"
            className="fill-analyst"
            initial={reduce ? false : { opacity: 0 }}
            animate={{ opacity: 0.14 }}
            transition={{ duration: 0.6, delay: 1.3 }}
          />

          {/* shared history */}
          <motion.path
            d="M 20 132 L 85 124 L 150 130 L 215 110"
            fill="none"
            className="stroke-ink-faint"
            strokeWidth="2"
            strokeLinecap="round"
            {...draw(0.15, 0.6)}
          />
          {/* machine baseline */}
          <motion.path
            d="M 215 110 L 285 102 L 355 96 L 460 88"
            fill="none"
            className="stroke-accent glow-baseline"
            strokeWidth="2"
            strokeLinecap="round"
            {...draw(0.7, 0.7)}
          />
          {/* analyst projection */}
          <motion.path
            d="M 215 110 L 285 88 L 355 66 L 460 40"
            fill="none"
            className="stroke-analyst glow-analyst"
            strokeWidth="2"
            strokeLinecap="round"
            {...draw(0.7, 0.7)}
          />
        </svg>
      </div>
      <figcaption className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5 text-[11px] text-ink-muted">
        <span className="flex items-center gap-1.5">
          <span className="h-0.5 w-4 rounded-full bg-accent" /> {t.baseline}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-0.5 w-4 rounded-full bg-analyst" /> {t.analystProj}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-4 rounded-sm bg-analyst opacity-20" /> {t.delta}
        </span>
      </figcaption>
    </figure>
  )
}
