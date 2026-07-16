// Locale-aware number/SAR formatting. Arabic uses Arabic-Indic digits;
// English keeps Latin digits. Unit words and percent sign follow the language.

type Lang = 'ar' | 'en'

let LANG: Lang = 'ar'

export function setFormatLang(l: Lang) {
  LANG = l
}

const NF: Record<Lang, Intl.NumberFormat> = {
  ar: new Intl.NumberFormat('ar-SA-u-nu-arab', { maximumFractionDigits: 2 }),
  en: new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }),
}
const NF1: Record<Lang, Intl.NumberFormat> = {
  ar: new Intl.NumberFormat('ar-SA-u-nu-arab', { minimumFractionDigits: 1, maximumFractionDigits: 1 }),
  en: new Intl.NumberFormat('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 }),
}
const NF0: Record<Lang, Intl.NumberFormat> = {
  ar: new Intl.NumberFormat('ar-SA-u-nu-arab', { maximumFractionDigits: 0 }),
  en: new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }),
}

export function fmt(v: number): string {
  return NF[LANG].format(v)
}

export function fmtInt(v: number): string {
  return NF0[LANG].format(v)
}

/** Share price / per-share values in SAR. */
export function fmtSAR(v: number): string {
  return LANG === 'ar' ? `${NF[LANG].format(v)} ر.س` : `SAR ${NF[LANG].format(v)}`
}

/** Company-scale amounts stored in SAR millions → compact units. */
export function fmtMillions(v: number): string {
  const abs = Math.abs(v)
  if (LANG === 'ar') {
    if (abs >= 1000) return `${NF1.ar.format(v / 1000)} مليار ر.س`
    return `${NF1.ar.format(v)} مليون ر.س`
  }
  if (abs >= 1000) return `SAR ${NF1.en.format(v / 1000)}B`
  return `SAR ${NF1.en.format(v)}M`
}

export function fmtPct(v: number, signed = false): string {
  // round to the displayed precision FIRST so "-0.04" never renders "-0.0%"
  const rounded = Math.round(Math.abs(v) * 10) / 10
  const s = NF1[LANG].format(rounded)
  const sign = rounded === 0 ? '' : v > 0 ? (signed ? '+' : '') : '-'
  return `${sign}${s}${LANG === 'ar' ? '٪' : '%'}`
}

const DF: Record<Lang, Intl.DateTimeFormat> = {
  // force Gregorian: ar-SA defaults to the Islamic calendar
  ar: new Intl.DateTimeFormat('ar-SA-u-nu-arab-ca-gregory', { day: 'numeric', month: 'short', year: '2-digit' }),
  en: new Intl.DateTimeFormat('en-US', { day: 'numeric', month: 'short', year: '2-digit' }),
}
const DF_SHORT: Record<Lang, Intl.DateTimeFormat> = {
  ar: new Intl.DateTimeFormat('ar-SA-u-nu-arab-ca-gregory', { month: 'short', year: '2-digit' }),
  en: new Intl.DateTimeFormat('en-US', { month: 'short', year: '2-digit' }),
}

export function fmtDate(iso: string, short = false): string {
  const d = new Date(iso)
  return (short ? DF_SHORT : DF)[LANG].format(d)
}

/** "2026Q2" → localized quarter label. */
export function fmtQuarter(q: string, short = false): string {
  const year = q.slice(0, 4)
  const n = q.slice(5)
  if (short) return `Q${n} ${year.slice(2)}`
  return LANG === 'ar' ? `الربع ${n} من ${year}` : `Q${n} ${year}`
}
