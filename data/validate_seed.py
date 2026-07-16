"""Schema-completeness validation for the Delta seed dataset."""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent

COMPANY_FIELDS = {"ticker", "name_ar", "name_en", "sector", "description_ar",
                  "is_islamic_bank", "has_sukuk"}
FIN_FIELDS = {"quarter", "revenue", "net_income", "gross_margin", "net_margin",
              "eps", "total_debt", "sukuk_debt", "zakat_expense",
              "free_cash_flow", "share_price",
              # Analyst Model v2 series (augment_seed.py)
              "equity", "total_assets", "roe", "roa", "ebitda", "ebitda_margin",
              "current_assets", "current_liabilities", "current_ratio"}
# Structurally null for banks, required non-null elsewhere.
BANK_NULL_FIELDS = {"ebitda", "ebitda_margin", "current_assets",
                    "current_liabilities", "current_ratio"}
NEWS_FIELDS = {"headline", "date", "body", "source"}


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def main() -> None:
    data = json.loads((HERE / "companies.json").read_text(encoding="utf-8"))
    sectors = {s["id"] for s in data["sectors"]}
    companies = data["companies"]
    financials = json.loads((HERE / "financials.json").read_text(encoding="utf-8"))
    news = json.loads((HERE / "news.json").read_text(encoding="utf-8"))

    if len(sectors) != 9:
        fail(f"expected 9 sectors, got {len(sectors)}")
    if len(companies) != 33:
        fail(f"expected 33 companies, got {len(companies)}")

    tickers = set()
    for c in companies:
        missing = COMPANY_FIELDS - c.keys()
        if missing:
            fail(f"{c.get('ticker')}: missing company fields {missing}")
        if c["sector"] not in sectors:
            fail(f"{c['ticker']}: unknown sector {c['sector']}")
        if c["ticker"] in tickers:
            fail(f"duplicate ticker {c['ticker']}")
        tickers.add(c["ticker"])

        fins = financials.get(c["ticker"])
        if not fins or len(fins) != 12:
            fail(f"{c['ticker']}: expected 12 quarters, got {len(fins or [])}")
        for row in fins:
            missing = FIN_FIELDS - row.keys()
            if missing:
                fail(f"{c['ticker']} {row.get('quarter')}: missing {missing}")
            if not c["has_sukuk"] and row["sukuk_debt"] != 0:
                fail(f"{c['ticker']}: sukuk_debt nonzero without has_sukuk flag")
            if c["has_sukuk"] and row["sukuk_debt"] <= 0:
                fail(f"{c['ticker']}: has_sukuk flag but sukuk_debt is zero")
            if row["zakat_expense"] < 0:
                fail(f"{c['ticker']} {row['quarter']}: negative zakat")

            # v2 coherence: banks null the EBITDA/current fields, everyone
            # else carries them; roe/roa must reconcile with equity/assets.
            is_bank = c["sector"] == "banks"
            for f in BANK_NULL_FIELDS:
                if is_bank and row[f] is not None:
                    fail(f"{c['ticker']} {row['quarter']}: bank must have null {f}")
                if not is_bank and row[f] is None:
                    fail(f"{c['ticker']} {row['quarter']}: null {f} for non-bank")
            if row["equity"] is None or row["equity"] <= 0:
                fail(f"{c['ticker']} {row['quarter']}: missing/non-positive equity")
            implied_roe = 4 * row["net_income"] / row["equity"]
            if abs(implied_roe - row["roe"]) > 0.002:
                fail(f"{c['ticker']} {row['quarter']}: roe {row['roe']} != 4*NI/equity {implied_roe:.4f}")
            implied_roa = 4 * row["net_income"] / row["total_assets"]
            if abs(implied_roa - row["roa"]) > 0.002:
                fail(f"{c['ticker']} {row['quarter']}: roa mismatch")
            if not is_bank and row["current_liabilities"]:
                implied_cr = row["current_assets"] / row["current_liabilities"]
                if abs(implied_cr - row["current_ratio"]) > 0.01:
                    fail(f"{c['ticker']} {row['quarter']}: current_ratio mismatch")

        news_items = news.get(c["ticker"])
        if not news_items or not (4 <= len(news_items) <= 6):
            fail(f"{c['ticker']}: expected 4-6 news items, got {len(news_items or [])}")
        for item in news_items:
            missing = NEWS_FIELDS - item.keys()
            if missing:
                fail(f"{c['ticker']} news: missing {missing}")

    islamic = [c["ticker"] for c in companies if c["is_islamic_bank"]]
    if len(islamic) < 3:
        fail(f"expected >=3 islamic banks, got {islamic}")

    per_sector: dict[str, int] = {}
    for c in companies:
        per_sector[c["sector"]] = per_sector.get(c["sector"], 0) + 1

    print(f"OK: 33 companies, 9 sectors {per_sector},")
    print(f"    {sum(len(v) for v in financials.values())} financial rows, "
          f"{sum(len(v) for v in news.values())} news items, "
          f"islamic banks: {islamic}")


if __name__ == "__main__":
    main()
