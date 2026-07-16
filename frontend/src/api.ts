// Typed client for the Delta backend (proxied via /api).

export interface Sector {
  id: string
  name_ar: string
  name_en: string
}

export interface Company {
  ticker: string
  name_ar: string
  name_en: string
  sector: string
  description_ar: string
  is_islamic_bank: boolean
  has_sukuk: boolean
}

export interface QuarterFinancials {
  quarter: string
  revenue: number
  net_income: number
  gross_margin: number
  net_margin: number
  eps: number
  total_debt: number
  sukuk_debt: number
  zakat_expense: number
  free_cash_flow: number
  share_price: number
  // Analyst Model v2 series; EBITDA/current fields are null for banks
  equity: number | null
  total_assets: number | null
  roe: number | null
  roa: number | null
  ebitda: number | null
  ebitda_margin: number | null
  current_assets: number | null
  current_liabilities: number | null
  current_ratio: number | null
}

export interface CompanyProfile extends Company {
  latest: QuarterFinancials
  ceo_ar: string
  ceo_en: string
  ceo_since: number
  ceo_experience_years: number
  founded: number
  employees: number
  hq_ar: string
  hq_en: string
  market_cap: number
  pe_ratio: number
  revenue_cagr_3y: number
}

export interface TapeEntry {
  ticker: string
  name_ar: string
  name_en: string
  price: number
  change_pct: number
}

export interface PeerRow {
  ticker: string
  name_ar: string
  name_en: string
  price: number
  fair_value: number
  upside_pct: number
  pe_ratio: number
  net_margin: number
  revenue_yoy: number
  is_self: boolean
}

export interface Candle {
  date: string
  open: number
  high: number
  low: number
  close: number
  sma20: number | null
  sma50: number | null
}

export interface LiveQuoteData {
  available: boolean
  symbol: string
  price: number | null
  previous_close: number | null
  change_pct: number | null
  currency: string | null
  market_time: string | null
  source: string
}

export interface Indicator {
  name: string
  value: number
  reference: number | null
  signal: 'buy' | 'sell' | 'neutral'
}

export interface Technicals {
  ticker: string
  as_of: string
  score: number
  rating: 'strong_sell' | 'sell' | 'neutral' | 'buy' | 'strong_buy'
  indicators: Indicator[]
}

export interface RangeChange {
  range: string
  from_price: number
  from_date: string
  change_pct: number
}

export interface PriceStats {
  last: number
  last_date: string
  changes: RangeChange[]
  high_52w: number
  high_52w_date: string
  low_52w: number
  low_52w_date: string
}

export interface PriceLevel {
  price: number
  touches: number
  kind: 'support' | 'resistance'
}

export type PriceRange = '1m' | '3m' | '6m' | '1y' | 'all'

export interface PriceSeries {
  ticker: string
  range: PriceRange
  candles: Candle[]
  stats: PriceStats
  levels: PriceLevel[]
}

export interface SensitivityResponse {
  ticker: string
  growth_steps: number[]
  discount_steps: number[]
  grid: number[][]
  current_price: number
  base_growth: number
  base_discount: number
}

export interface NewsItem {
  headline: string
  date: string
  body: string
  source: string
}

export interface Assumptions {
  revenue_growth: number
  net_margin: number
  discount_rate: number
  terminal_growth: number
  horizon_quarters: number
  fcf_conversion: number | null
  terminal_method: 'gordon' | 'exit_multiple'
  exit_pe: number
  // Analyst Model v2: incident exclusion + the extended metric sliders
  exclude_quarters: string[]
  exclude_scope: 'company' | 'sector'
  ebitda_margin: number | null
  roe: number | null
  roa: number | null
  current_ratio: number | null
}

export interface ProjectedQuarter {
  quarter: string
  revenue: number
  net_income: number
}

export interface ValuationBreakdown {
  method: 'dcf' | 'ddm_islamic' | 'ddm_bank'
  pv_forecast: number
  pv_terminal: number
  zakat_total: number
  total_debt: number
  sukuk_debt: number
  shares: number
  pv_series: number[]
}

export interface BaselineResponse {
  ticker: string
  is_islamic_bank: boolean
  income_label_ar: string
  projected: ProjectedQuarter[]
  fair_value: number
  current_price: number
  upside_pct: number
  assumptions: Assumptions
  breakdown: ValuationBreakdown
}

export interface AnalystValuation {
  ticker: string
  projected: ProjectedQuarter[]
  fair_value: number
  baseline_fair_value: number
  delta_abs: number
  delta_pct: number
  current_price: number
  upside_pct: number
  assumptions: Assumptions
  breakdown: ValuationBreakdown
}

export interface AnomalyFlag {
  metric: string
  metric_label_ar: string
  z_score: number
  severity: 'high' | 'medium'
  direction: 'up' | 'down'
  latest_value: number
  trailing_mean: number
  explanation_ar: string
  // v2 cause-labelling: why it broke, grounded in news near the quarter
  cause_ar: string
  cause_en: string
  cause_confidence: 'grounded' | 'tentative'
  causal_news: { headline: string; date: string; source: string }[]
  suggested_exclusion: string | null
}

export interface AgentReport {
  ticker: string
  quarter: string
  flags: AnomalyFlag[]
  news_context: { headline: string; date: string; source: string } | null
  summary_ar: string
}

export interface CompanyOverview {
  overview_ar: string
  ceo_note_ar: string
  outlook_ar: string
  strengths_ar: string[]
  risks_ar: string[]
  source: 'llm' | 'fallback'
}

export interface NewsSummary {
  summary_ar: string
  items: { headline: string; sentiment: 'إيجابي' | 'محايد' | 'سلبي' }[]
  source: 'llm' | 'fallback'
}

export interface Scenario {
  title_ar: string
  points_ar: string[]
  target_price: number | null
  probability_pct: number | null
}

export interface ScenarioSet {
  bull: Scenario
  bear: Scenario
  thesis_breakers: Scenario
  monitoring_ar: string[]
  source: 'llm' | 'fallback'
}

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
}

export interface AssumptionRating {
  parameter: 'revenue_growth' | 'net_margin' | 'discount_rate' | 'terminal_growth'
  verdict: 'conservative' | 'balanced' | 'aggressive'
  note_ar: string
}

export interface ChatReply {
  reply_ar: string
  key_numbers_ar: string[]
  follow_ups_ar: string[]
  assumption_ratings: AssumptionRating[] | null
  proposed_assumptions: Assumptions | null
  proposed_label_ar: string | null
  proposed_fair_value: number | null
  proposed_upside_pct: number | null
  source: 'llm' | 'fallback'
}

export interface SubscribeRequest {
  name: string
  email: string
  company: string
}

export interface SubscribeResponse {
  status: 'created' | 'duplicate'
  message: string
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`/api${path}`)
  if (!r.ok) throw new Error(`${r.status} on ${path}`)
  return r.json()
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`/api${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error(`${r.status} on ${path}`)
  return r.json()
}

export const api = {
  sectors: () => get<Sector[]>('/sectors'),
  sectorCompanies: (id: string) => get<Company[]>(`/sectors/${id}/companies`),
  company: (t: string) => get<CompanyProfile>(`/companies/${t}`),
  financials: (t: string) => get<QuarterFinancials[]>(`/companies/${t}/financials`),
  news: (t: string) => get<NewsItem[]>(`/companies/${t}/news`),
  baseline: (t: string, horizon = 8, exclude: string[] = [], scope = 'company') =>
    get<BaselineResponse>(
      `/companies/${t}/baseline?horizon=${horizon}&exclude=${exclude.join(',')}&exclude_scope=${scope}`,
    ),
  technicals: (t: string) => get<Technicals>(`/companies/${t}/technicals`),
  live: (t: string) => get<LiveQuoteData>(`/companies/${t}/live`),
  valuation: (t: string, a: Assumptions) => post<AnalystValuation>(`/companies/${t}/valuation`, a),
  agentReport: (t: string, exclude: string[] = []) =>
    get<AgentReport>(`/companies/${t}/agent-report?exclude=${exclude.join(',')}`),
  tape: () => get<TapeEntry[]>('/market/tape'),
  prices: (t: string, range: PriceRange) => get<PriceSeries>(`/companies/${t}/prices?range=${range}`),
  peers: (t: string) => get<PeerRow[]>(`/companies/${t}/peers`),
  sensitivity: (t: string, a: Assumptions) =>
    post<SensitivityResponse>(`/companies/${t}/sensitivity`, a),
  overview: (t: string, lang: string) =>
    get<CompanyOverview>(`/companies/${t}/overview?lang=${lang}`),
  newsSummary: (t: string, lang: string) =>
    get<NewsSummary>(`/companies/${t}/news-summary?lang=${lang}`),
  scenarios: (t: string, a: Assumptions, lang: string) =>
    post<ScenarioSet>(`/companies/${t}/scenarios?lang=${lang}`, a),
  chat: (t: string, messages: ChatTurn[], assumptions: Assumptions | null, lang: string) =>
    post<ChatReply>(`/companies/${t}/chat`, { messages, assumptions, lang }),
  subscribe: (payload: SubscribeRequest) => post<SubscribeResponse>('/subscribe', payload),
}
