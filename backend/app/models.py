from __future__ import annotations

from pydantic import BaseModel


class Sector(BaseModel):
    id: str
    name_ar: str
    name_en: str


class Company(BaseModel):
    ticker: str
    name_ar: str
    name_en: str
    sector: str
    description_ar: str
    is_islamic_bank: bool
    has_sukuk: bool
    # leadership & facts (synthetic demo profile data)
    ceo_ar: str
    ceo_en: str
    ceo_since: int
    ceo_experience_years: int
    founded: int
    employees: int | None = None  # None = no verified figure available
    hq_ar: str
    hq_en: str


class QuarterFinancials(BaseModel):
    quarter: str
    revenue: float
    net_income: float
    gross_margin: float
    net_margin: float
    eps: float
    total_debt: float
    sukuk_debt: float
    zakat_expense: float
    free_cash_flow: float
    share_price: float


class CompanyProfile(Company):
    """Company profile plus its latest quarterly snapshot and key ratios."""

    latest: QuarterFinancials
    market_cap: float  # SAR millions
    pe_ratio: float  # price / annualized EPS
    revenue_cagr_3y: float  # 12-quarter revenue CAGR (annualized)


class NewsItem(BaseModel):
    headline: str
    date: str
    body: str
    source: str
    url: str | None = None  # live items link to the article; seed items don't


class TapeEntry(BaseModel):
    """One cell of the market ticker tape."""

    ticker: str
    name_ar: str
    name_en: str
    price: float
    change_pct: float  # vs previous quarter close


class PeerRow(BaseModel):
    ticker: str
    name_ar: str
    name_en: str
    price: float
    fair_value: float
    upside_pct: float
    pe_ratio: float
    net_margin: float
    revenue_yoy: float
    is_self: bool
