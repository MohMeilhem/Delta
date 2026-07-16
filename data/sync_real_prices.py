"""Pin seed share prices to real Tadawul closes (via Yahoo Finance).

The seed data is synthetic, so its share prices drift from the real market and
analysts notice ("the price is not accurate"). This script fetches the real
last close for every ticker (symbol "<ticker>.SR") and rescales that company's
ENTIRE financial history by one uniform factor

    k = real_price / seed_last_price

applied to the share_price series and every monetary line item (revenue, net
income, EPS, debt, sukuk, zakat, FCF). A uniform scale preserves everything the
platform depends on:

  - margins and growth rates (ratios of scaled values) — unchanged
  - z-score anomalies (z is scale-invariant) — unchanged
  - P/E (price/eps both scale by k) — unchanged
  - fair-value / price calibration window from calibrate_prices.py — unchanged
  - the last quarterly close now equals the real Tadawul price

Run order: generate_seed.py -> calibrate_prices.py -> sync_real_prices.py ->
validate_seed.py. Offline it is a graceful no-op per ticker (seed stays valid).
A snapshot of the fetched prices is written to real_prices.json for provenance.
"""

from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path

import httpx

DATA = Path(__file__).parent
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
TIMEOUT_S = 6.0

# every monetary field in a quarter row; margins/quarter label stay untouched
MONEY_FIELDS = [
    "revenue",
    "net_income",
    "eps",
    "total_debt",
    "sukuk_debt",
    "zakat_expense",
    "free_cash_flow",
    "share_price",
]
DECIMALS = {"eps": 3, "share_price": 2}  # everything else rounds to 1


def fetch_close(client: httpx.Client, ticker: str) -> float | None:
    try:
        r = client.get(
            YAHOO_CHART.format(symbol=f"{ticker}.SR"),
            params={"interval": "1d", "range": "5d"},
        )
        r.raise_for_status()
        price = r.json()["chart"]["result"][0]["meta"].get("regularMarketPrice")
        return float(price) if price else None
    except Exception:
        return None


def main() -> None:
    fins = json.loads((DATA / "financials.json").read_text(encoding="utf-8"))
    snapshot: dict[str, float] = {}
    skipped: list[str] = []

    with httpx.Client(timeout=TIMEOUT_S, headers={"User-Agent": "Mozilla/5.0"}) as client:
        for ticker, rows in fins.items():
            real = fetch_close(client, ticker)
            if real is None:
                skipped.append(ticker)
                continue
            seed_last = rows[-1]["share_price"]
            k = real / seed_last
            for row in rows:
                for f in MONEY_FIELDS:
                    row[f] = round(row[f] * k, DECIMALS.get(f, 1))
            # exact pin: rounding above can leave the last close a cent off
            rows[-1]["share_price"] = round(real, 2)
            snapshot[ticker] = round(real, 2)
            print(f"  {ticker}: {seed_last:.2f} -> {real:.2f} SAR (x{k:.3f})")
            time.sleep(0.15)  # be polite to the quote API

    if skipped:
        print(f"  skipped (no quote): {', '.join(skipped)}")
    if not snapshot:
        print("  offline or blocked: seed prices left as-is")
        return

    (DATA / "financials.json").write_text(
        json.dumps(fins, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (DATA / "real_prices.json").write_text(
        json.dumps({"as_of": date.today().isoformat(), "prices": snapshot},
                   ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"synced {len(snapshot)}/{len(fins)} tickers to real Tadawul closes")


if __name__ == "__main__":
    main()
