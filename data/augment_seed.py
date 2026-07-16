"""Analyst Model v2 seed extension: derive the 7-metric series.

Adds to every company's 12-quarter record: equity, total_assets, roe, roa,
and (non-banks only) ebitda, ebitda_margin, current_assets,
current_liabilities, current_ratio. Banks carry null for the EBITDA and
current-ratio fields — banks have no EBITDA line and no current/non-current
split; that is accounting, not a data gap.

Every value is a PURE FUNCTION of the existing series plus per-sector
constants — no randomness — so augmenting the shipped financials.json does
not move any already-calibrated number, and regeneration stays reproducible
(the CLAUDE.md invariant: every valuation number reproducible from seed).

Derivations (per quarter i, SAR millions, ratios annualized):
  equity_0        = 4*NI_0 / roe0(sector)          (opening book value)
  equity_i        = equity_{i-1} + NI_i * (1 - payout(sector))   (retention)
  roe_i           = 4*NI_i / equity_i
  total_assets_i  = equity_i * leverage(sector)
  roa_i           = 4*NI_i / total_assets_i
  ebitda_i        = NI_i + dep(sector)*revenue_i + 0.0125*total_debt_i + zakat_i
                    (add back D&A, ~5%/yr financing cost, and zakat)
  ebitda_margin_i = ebitda_i / revenue_i
  current_assets_i      = ca(sector) * revenue_i
  current_liabilities_i = 0.55*ca(sector)*revenue_i + 0.25*total_debt_i
  current_ratio_i       = CA_i / CL_i

Usable two ways: imported by generate_seed.py after gen_financials, or run
directly to upgrade an existing financials.json in place:
    python augment_seed.py
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent

# Per-sector financial profile. payout mirrors backend/app/valuation.py's
# SECTOR_DEFAULTS (duplicated on purpose: /data must stay importable without
# the backend package).
#   roe0      opening annualized ROE anchoring the equity series
#   payout    dividend payout ratio (retention drives book-value growth)
#   leverage  total assets / equity
#   dep       D&A as a fraction of quarterly revenue (None for banks)
#   ca        current assets as a multiple of quarterly revenue (None for banks)
SECTOR_PROFILE: dict[str, dict] = {
    "banks":      {"roe0": 0.16, "payout": 0.65, "leverage": 10.5, "dep": None, "ca": None},
    "energy":     {"roe0": 0.30, "payout": 0.60, "leverage": 2.0,  "dep": 0.10, "ca": 0.8},
    "materials":  {"roe0": 0.08, "payout": 0.55, "leverage": 1.8,  "dep": 0.09, "ca": 1.4},
    "telecom":    {"roe0": 0.12, "payout": 0.70, "leverage": 2.2,  "dep": 0.16, "ca": 0.7},
    "healthcare": {"roe0": 0.18, "payout": 0.50, "leverage": 1.6,  "dep": 0.06, "ca": 1.0},
    "retail":     {"roe0": 0.25, "payout": 0.60, "leverage": 2.4,  "dep": 0.025, "ca": 0.9},
    "utilities":  {"roe0": 0.08, "payout": 0.65, "leverage": 3.2,  "dep": 0.18, "ca": 0.6},
    "food":       {"roe0": 0.10, "payout": 0.55, "leverage": 2.1,  "dep": 0.06, "ca": 1.1},
    "realestate": {"roe0": 0.07, "payout": 0.40, "leverage": 2.6,  "dep": 0.04, "ca": 2.5},
}

QUARTERLY_FINANCING_RATE = 0.0125  # ~5% annual cost on total debt
CL_REVENUE_SHARE = 0.55            # current liabilities: revenue-linked part
CL_DEBT_SHARE = 0.25               # share of total debt that is short-term

V2_FIELDS = [
    "equity", "total_assets", "roe", "roa",
    "ebitda", "ebitda_margin",
    "current_assets", "current_liabilities", "current_ratio",
]


def augment_rows(sector: str, rows: list[dict]) -> list[dict]:
    """Add the v2 metric series to one company's quarter rows, in place."""
    prof = SECTOR_PROFILE[sector]
    is_bank = sector == "banks"

    # Opening book anchored so the first quarter's ROE = sector roe0.
    ni0 = abs(rows[0]["net_income"]) or 1.0
    equity = 4.0 * ni0 / prof["roe0"]

    for row in rows:
        ni = row["net_income"]
        rev = row["revenue"]

        equity += ni * (1.0 - prof["payout"])
        equity = max(equity, 1.0)  # a demo series must never go non-positive
        assets = equity * prof["leverage"]

        row["equity"] = round(equity, 1)
        row["total_assets"] = round(assets, 1)
        row["roe"] = round(4.0 * ni / equity, 4)
        row["roa"] = round(4.0 * ni / assets, 4)

        if is_bank:
            row["ebitda"] = None
            row["ebitda_margin"] = None
            row["current_assets"] = None
            row["current_liabilities"] = None
            row["current_ratio"] = None
        else:
            ebitda = (ni + prof["dep"] * rev
                      + QUARTERLY_FINANCING_RATE * row["total_debt"]
                      + row["zakat_expense"])
            ca = prof["ca"] * rev
            cl = CL_REVENUE_SHARE * prof["ca"] * rev + CL_DEBT_SHARE * row["total_debt"]
            row["ebitda"] = round(ebitda, 1)
            row["ebitda_margin"] = round(ebitda / rev, 4) if rev else 0.0
            row["current_assets"] = round(ca, 1)
            row["current_liabilities"] = round(cl, 1)
            row["current_ratio"] = round(ca / cl, 4) if cl else 0.0
    return rows


def main() -> None:
    companies = json.loads((HERE / "companies.json").read_text(encoding="utf-8"))["companies"]
    sector_of = {c["ticker"]: c["sector"] for c in companies}
    fin_path = HERE / "financials.json"
    financials = json.loads(fin_path.read_text(encoding="utf-8"))

    for ticker, rows in financials.items():
        augment_rows(sector_of[ticker], rows)

    fin_path.write_text(json.dumps(financials, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(f"augmented {len(financials)} companies with v2 metric series "
          f"({', '.join(V2_FIELDS)})")


if __name__ == "__main__":
    main()
