/* Theme layer: dark (default, analyst desk) and light (daylight office).
 * CSS handles tokens via [data-theme]; charts read their palette from
 * useChartColors() because SVG props can't use CSS variables everywhere. */

import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

export type Theme = 'dark' | 'light'

interface ThemeCtx {
  theme: Theme
  setTheme: (t: Theme) => void
}

const Ctx = createContext<ThemeCtx | null>(null)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() => {
    // ?theme=light|dark deep-links a demo state (screenshots, shared links)
    const q = new URLSearchParams(window.location.search).get('theme')
    if (q === 'light' || q === 'dark') return q
    return (localStorage.getItem('delta-theme') as Theme) || 'dark'
  })

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    document.documentElement.style.colorScheme = theme
    localStorage.setItem('delta-theme', theme)
  }, [theme])

  const value = useMemo(() => ({ theme, setTheme }), [theme])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useTheme(): ThemeCtx {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useTheme outside ThemeProvider')
  return ctx
}

/* ---- chart palettes (SVG attribute values, per theme) ---- */

export interface ChartColors {
  ink: string
  muted: string
  faint: string
  grid: string
  line: string
  surface: string
  baseline: string
  analyst: string
  analystBandTop: string
  up: string
  down: string
  warning: string
  ratings: Record<string, string>
}

const DARK: ChartColors = {
  ink: 'oklch(0.95 0.006 170)',
  muted: 'oklch(0.75 0.015 175)',
  faint: 'oklch(0.56 0.015 175)',
  grid: 'oklch(0.23 0.015 180)',
  line: 'oklch(0.265 0.016 180)',
  surface: 'oklch(0.17 0.014 180)',
  baseline: 'oklch(0.78 0.145 163)',
  analyst: 'oklch(0.83 0.13 85)',
  analystBandTop: 'oklch(0.83 0.13 85 / 0.28)',
  up: 'oklch(0.78 0.145 163)',
  down: 'oklch(0.69 0.17 25)',
  warning: 'oklch(0.78 0.14 65)',
  ratings: {
    strong_sell: 'oklch(0.69 0.17 25)',
    sell: 'oklch(0.72 0.14 45)',
    neutral: 'oklch(0.75 0.015 175)',
    buy: 'oklch(0.78 0.1 140)',
    strong_buy: 'oklch(0.78 0.145 163)',
  },
}

const LIGHT: ChartColors = {
  ink: 'oklch(0.22 0.02 190)',
  muted: 'oklch(0.42 0.02 185)',
  faint: 'oklch(0.55 0.015 180)',
  grid: 'oklch(0.9 0.008 175)',
  line: 'oklch(0.87 0.01 175)',
  surface: 'oklch(0.99 0.002 175)',
  baseline: 'oklch(0.52 0.13 163)',
  analyst: 'oklch(0.58 0.12 80)',
  analystBandTop: 'oklch(0.58 0.12 80 / 0.25)',
  up: 'oklch(0.52 0.13 163)',
  down: 'oklch(0.55 0.19 25)',
  warning: 'oklch(0.58 0.13 65)',
  ratings: {
    strong_sell: 'oklch(0.55 0.19 25)',
    sell: 'oklch(0.6 0.15 45)',
    neutral: 'oklch(0.55 0.015 180)',
    buy: 'oklch(0.55 0.11 140)',
    strong_buy: 'oklch(0.52 0.13 163)',
  },
}

export function useChartColors(): ChartColors {
  const { theme } = useTheme()
  return theme === 'dark' ? DARK : LIGHT
}
