"""Deterministic share-price calibration (run after generate_seed.py).

The synthetic share-price random walk knows nothing about the valuation
engine, so some companies end up with prices the DCF can never reconcile
(real-world ACWA Power trades at ~90x earnings — no POC DCF reproduces
that). This step rescales each company's price series so the latest price
sits within a sane band of the model's fair value, while preserving each
company's relative character (cheap names stay cheap, rich names rich).

fair value / price is compressed toward 1.0:  target = clip(natural^0.35,
0.72, 1.35). Pure function of the seed data — fully reproducible.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "backend"))

from app import data as app_data  # noqa: E402
from app import valuation  # noqa: E402


def main() -> None:
    fins_path = HERE / "financials.json"
    fins = json.loads(fins_path.read_text(encoding="utf-8"))

    for c in app_data.companies():
        base = valuation.baseline(c)
        fv, px = base.fair_value, base.current_price
        natural = fv / px
        target = min(max(natural ** 0.35, 0.72), 1.35)
        scale = (fv / target) / px
        for row in fins[c.ticker]:
            row["share_price"] = round(row["share_price"] * scale, 2)
        print(f"{c.ticker} {c.name_en:28s} fv={fv:8.2f} "
              f"px {px:8.2f} -> {fins[c.ticker][-1]['share_price']:8.2f} "
              f"(fv/px {natural:5.2f} -> {target:4.2f})")

    fins_path.write_text(json.dumps(fins, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    print("calibrated prices written")


if __name__ == "__main__":
    main()
