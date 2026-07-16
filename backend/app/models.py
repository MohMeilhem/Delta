from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


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
    employees: int
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


class SubscriptionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    company: str = Field(min_length=1, max_length=160)

    @field_validator("name", "company")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("invalid email")
        local, domain = value.split("@", 1)
        if not local or not domain or "." not in domain or domain.startswith(".") or domain.endswith("."):
            raise ValueError("invalid email")
        return value


class SubscriptionResponse(BaseModel):
    status: Literal["created", "duplicate"]
    message: str
