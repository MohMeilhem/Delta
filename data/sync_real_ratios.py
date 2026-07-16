"""Calibrate the latest quarter's v2 ratios to real market values.

Best-effort, display-anchoring step (same philosophy as sync_real_prices.py):
for each company, pull the real ROE / ROA / EBITDA-margin / current-ratio
snapshot from yfinance ("<ticker>.SR") and rescale the synthetic level series
so the LATEST quarter matches reality while the whole history shifts
proportionally — dynamics (trends, seasonality, the embedded anomalies) are
preserved, and the coherence identities (roe = 4*NI/equity, cr = CA/CL)
still hold exactly.

Offline / no yfinance / any per-ticker failure -> that company is skipped
untouched (graceful no-op, per CLAUDE.md). Set DELTA_OFFLINE=1 to skip all.

Run:  python sync_real_ratios.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

HERE = Path(__file__).parent

BOUNDS = {  # sanity bounds: reject junk snapshots
    "roe": (0.005, 0.60),
    "roa": (0.002, 0.40),
    "ebitda_margin": (0.02, 0.85),
    "current_ratio": (0.3, 6.0),
}


def _real_snapshot(yf, ticker: str) -> dict:
    info = yf.Ticker(f"{ticker}.SR").info or {}
    out = {}
    for field, key in (("roe", "returnOnEquity"), ("roa", "returnOnAssets"),
                       ("ebitda_margin", "ebitdaMargins"), ("current_ratio", "currentRatio")):
        v = info.get(key)
        lo, hi = BOUNDS[field]
        if isinstance(v, (int, float)) and lo <= v <= hi:
            out[field] = float(v)
    return out


def _sane(k: float) -> bool:
    """Reject scale factors that would distort the series beyond recognition
    (an anomaly-depressed latest quarter can imply absurd rescaling)."""
    return 0.2 <= k <= 5.0


def _rescale(rows: list[dict], real: dict, is_bank: bool) -> list[str]:
    """Scale level series so the latest ratio hits the real value; return
    the list of calibrated fields."""
    last = rows[-1]
    done = []

    if "roe" in real and last["roe"] and _sane(last["roe"] / real["roe"]):
        k = last["roe"] / real["roe"]  # equity *= k  =>  roe /= k
        for r in rows:
            r["equity"] = round(r["equity"] * k, 1)
            r["roe"] = round(4 * r["net_income"] / r["equity"], 4)
        done.append("roe")

    if ("roa" in real and last["total_assets"]
            and _sane((4 * last["net_income"] / real["roa"]) / last["total_assets"])):
        # target latest assets = 4*NI/roa_real; scale the whole series to it
        k = (4 * last["net_income"] / real["roa"]) / last["total_assets"]
        for r in rows:
            r["total_assets"] = round(r["total_assets"] * k, 1)
            r["roa"] = round(4 * r["net_income"] / r["total_assets"], 4)
        done.append("roa")

    if not is_bank:
        if "ebitda_margin" in real and last["revenue"]:
            # scale the non-NI add-back so the latest margin matches
            target_ebitda = real["ebitda_margin"] * last["revenue"]
            addback_last = last["ebitda"] - last["net_income"]
            if addback_last > 0 and target_ebitda > last["net_income"]:
                m = (target_ebitda - last["net_income"]) / addback_last
                for r in rows:
                    r["ebitda"] = round(r["net_income"] + (r["ebitda"] - r["net_income"]) * m, 1)
                    r["ebitda_margin"] = round(r["ebitda"] / r["revenue"], 4) if r["revenue"] else 0.0
                done.append("ebitda_margin")

        if ("current_ratio" in real and last["current_ratio"]
                and _sane(last["current_ratio"] / real["current_ratio"])):
            k = last["current_ratio"] / real["current_ratio"]  # CL *= k
            for r in rows:
                r["current_liabilities"] = round(r["current_liabilities"] * k, 1)
                r["current_ratio"] = round(
                    r["current_assets"] / r["current_liabilities"], 4
                ) if r["current_liabilities"] else 0.0
            done.append("current_ratio")

    return done


def main() -> None:
    if os.environ.get("DELTA_OFFLINE"):
        print("DELTA_OFFLINE set — skipping ratio calibration")
        return
    try:
        import yfinance as yf
    except ModuleNotFoundError:
        print("yfinance not installed — skipping ratio calibration")
        return

    companies = json.loads((HERE / "companies.json").read_text(encoding="utf-8"))["companies"]
    fin_path = HERE / "financials.json"
    financials = json.loads(fin_path.read_text(encoding="utf-8"))

    calibrated = 0
    for c in companies:
        try:
            real = _real_snapshot(yf, c["ticker"])
        except Exception:
            continue  # offline / rate-limited / unknown symbol: keep synthetic
        if not real:
            continue
        fields = _rescale(financials[c["ticker"]], real, c["sector"] == "banks")
        if fields:
            calibrated += 1
            print(f"{c['ticker']} {c['name_en']}: calibrated {', '.join(fields)}")

    fin_path.write_text(json.dumps(financials, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(f"done — {calibrated}/{len(companies)} companies calibrated to real ratios")


if __name__ == "__main__":
    main()
