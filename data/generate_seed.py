"""Deterministic seed-data generator for Delta.

Produces companies.json, financials.json, news.json in this directory.
All numbers are reproducible (fixed RNG seed). Financial scales are
synthetic-but-plausible approximations of real Tadawul companies,
in SAR millions per quarter.

Embedded anomalies (latest quarter, for the z-score detector to find):
  - 7030 Zain KSA:      net margin collapse (impairment charge)
  - 4003 eXtra:         revenue spike (one-off expansion surge)
  - 6010 NADEC:         free-cash-flow collapse (working-capital blowout)
  - 4300 Dar Al Arkan:  net margin spike (one-off land sale gain)
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

HERE = Path(__file__).parent
RNG = random.Random(42)

QUARTERS = [
    "2023Q3", "2023Q4", "2024Q1", "2024Q2", "2024Q3", "2024Q4",
    "2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1", "2026Q2",
]

# ---------------------------------------------------------------------------
# Companies: ticker, name_ar, name_en, sector, description_ar,
# is_islamic_bank, has_sukuk, and generator params:
#   rev0        base quarterly revenue (SAR millions)
#   nm          base net margin
#   gm          base gross margin
#   growth      avg quarter-over-quarter revenue growth
#   season      seasonality amplitude (fraction of revenue, peaks Q4)
#   vol         random noise amplitude
#   shares      shares outstanding (millions)
#   debt_ratio  total debt as multiple of quarterly revenue
#   sukuk_share fraction of debt that is sukuk (0 if has_sukuk False)
#   price0      starting share price (SAR)
# ---------------------------------------------------------------------------

SECTORS = [
    {"id": "banks", "name_ar": "البنوك", "name_en": "Banks"},
    {"id": "energy", "name_ar": "الطاقة", "name_en": "Energy"},
    {"id": "materials", "name_ar": "المواد الأساسية", "name_en": "Materials"},
    {"id": "telecom", "name_ar": "الاتصالات", "name_en": "Telecom"},
    {"id": "healthcare", "name_ar": "الرعاية الصحية", "name_en": "Healthcare"},
    {"id": "retail", "name_ar": "التجزئة", "name_en": "Retail"},
    {"id": "utilities", "name_ar": "المرافق العامة", "name_en": "Utilities"},
    {"id": "food", "name_ar": "الأغذية", "name_en": "Food"},
    {"id": "realestate", "name_ar": "العقارات", "name_en": "Real Estate"},
]

C = []  # company definitions


def co(ticker, name_ar, name_en, sector, desc, islamic=False, sukuk=False, **p):
    C.append({
        "ticker": ticker, "name_ar": name_ar, "name_en": name_en,
        "sector": sector, "description_ar": desc,
        "is_islamic_bank": islamic, "has_sukuk": sukuk, "params": p,
    })


# --- Banks (5) --------------------------------------------------------------
co("1120", "مصرف الراجحي", "Al Rajhi Bank", "banks",
   "أكبر مصرف إسلامي في العالم من حيث القيمة السوقية، يقدم خدمات مصرفية متوافقة مع الشريعة للأفراد والشركات في المملكة.",
   islamic=True, sukuk=True,
   rev0=7600, nm=0.58, gm=0.80, growth=0.020, season=0.01, vol=0.015,
   shares=4000, debt_ratio=4.0, sukuk_share=0.85, price0=78)
co("1180", "البنك الأهلي السعودي", "Saudi National Bank", "banks",
   "أكبر بنك في المملكة نشأ من اندماج الأهلي التجاري وسامبا، يقدم خدمات مصرفية شاملة للأفراد والشركات.",
   sukuk=True,
   rev0=8700, nm=0.55, gm=0.78, growth=0.015, season=0.01, vol=0.015,
   shares=6000, debt_ratio=4.5, sukuk_share=0.35, price0=36)
co("1150", "مصرف الإنماء", "Alinma Bank", "banks",
   "مصرف إسلامي سعودي سريع النمو يركز على الخدمات الرقمية والتمويل المتوافق مع الشريعة.",
   islamic=True, sukuk=True,
   rev0=2900, nm=0.45, gm=0.75, growth=0.028, season=0.01, vol=0.02,
   shares=2500, debt_ratio=3.5, sukuk_share=0.9, price0=27)
co("1010", "بنك الرياض", "Riyad Bank", "banks",
   "من أكبر البنوك السعودية، يقدم خدمات مصرفية للأفراد والشركات مع حضور قوي في تمويل المشاريع الكبرى.",
   sukuk=True,
   rev0=4100, nm=0.50, gm=0.76, growth=0.015, season=0.01, vol=0.015,
   shares=3000, debt_ratio=4.0, sukuk_share=0.4, price0=28)
co("1140", "بنك البلاد", "Bank Albilad", "banks",
   "بنك إسلامي سعودي يخدم الأفراد والمنشآت الصغيرة والمتوسطة مع شبكة صرافة واسعة.",
   islamic=True, sukuk=True,
   rev0=1650, nm=0.42, gm=0.74, growth=0.022, season=0.01, vol=0.02,
   shares=1200, debt_ratio=3.0, sukuk_share=0.9, price0=38)

# --- Energy (3) -------------------------------------------------------------
co("2222", "أرامكو السعودية", "Saudi Aramco", "energy",
   "أكبر شركة نفط متكاملة في العالم، تعمل في التنقيب والإنتاج والتكرير والكيميائيات وتوزيع الطاقة.",
   sukuk=True,
   rev0=402000, nm=0.245, gm=0.50, growth=0.002, season=0.02, vol=0.06,
   shares=242000, debt_ratio=0.6, sukuk_share=0.25, price0=27)
co("4030", "البحري", "Bahri", "energy",
   "الناقل الوطني السعودي للنفط والكيماويات والبضائع، من أكبر شركات نقل النفط الخام في العالم.",
   sukuk=False,
   rev0=2300, nm=0.16, gm=0.30, growth=0.012, season=0.03, vol=0.07,
   shares=880, debt_ratio=3.0, sukuk_share=0.0, price0=27)
co("2382", "أديس القابضة", "ADES Holding", "energy",
   "شركة حفر بري وبحري تخدم شركات النفط في الشرق الأوسط وشمال أفريقيا بأسطول حفارات متنامٍ.",
   sukuk=False,
   rev0=1550, nm=0.15, gm=0.35, growth=0.035, season=0.01, vol=0.04,
   shares=1130, debt_ratio=4.0, sukuk_share=0.0, price0=17)

# --- Materials (4) ----------------------------------------------------------
co("2010", "سابك", "SABIC", "materials",
   "من أكبر شركات البتروكيماويات في العالم، تنتج الكيماويات والبوليمرات والأسمدة وتصدر لأكثر من 100 دولة.",
   sukuk=True,
   rev0=35500, nm=0.055, gm=0.22, growth=0.004, season=0.02, vol=0.06,
   shares=3000, debt_ratio=1.2, sukuk_share=0.3, price0=68)
co("1211", "معادن", "Ma'aden", "materials",
   "الشركة الوطنية للتعدين، تنتج الفوسفات والألمنيوم والذهب وتقود توسع قطاع التعدين السعودي.",
   sukuk=True,
   rev0=7900, nm=0.14, gm=0.32, growth=0.018, season=0.015, vol=0.05,
   shares=3800, debt_ratio=3.0, sukuk_share=0.35, price0=48)
co("2290", "ينساب", "Yansab", "materials",
   "شركة بتروكيماويات تابعة لسابك تنتج الجلايكول والبولي إيثيلين والبولي بروبلين في ينبع.",
   sukuk=False,
   rev0=1850, nm=0.09, gm=0.24, growth=0.002, season=0.02, vol=0.06,
   shares=562, debt_ratio=0.5, sukuk_share=0.0, price0=36)
co("2310", "سبكيم", "Sipchem", "materials",
   "شركة صناعات كيميائية متكاملة تنتج الميثانول ومشتقاته والبوليمرات المتخصصة في الجبيل.",
   sukuk=True,
   rev0=1950, nm=0.11, gm=0.26, growth=0.003, season=0.02, vol=0.055,
   shares=733, debt_ratio=1.5, sukuk_share=0.5, price0=25)

# --- Telecom (3) ------------------------------------------------------------
co("7010", "إس تي سي", "stc", "telecom",
   "المشغل الرائد للاتصالات في المملكة، يقدم خدمات الجوال والإنترنت والحلول الرقمية للأفراد والشركات والحكومة.",
   sukuk=True,
   rev0=19200, nm=0.17, gm=0.55, growth=0.010, season=0.015, vol=0.02,
   shares=4980, debt_ratio=0.8, sukuk_share=0.4, price0=41)
co("7020", "موبايلي", "Mobily", "telecom",
   "ثاني أكبر مشغل اتصالات في المملكة، يركز على خدمات الجوال والألياف البصرية وحلول الأعمال.",
   sukuk=True,
   rev0=4400, nm=0.13, gm=0.48, growth=0.012, season=0.015, vol=0.025,
   shares=770, debt_ratio=1.5, sukuk_share=0.45, price0=47)
co("7030", "زين السعودية", "Zain KSA", "telecom",
   "مشغل اتصالات يقدم خدمات الجوال والبيانات، ويتوسع في الخدمات المالية الرقمية وإنترنت الأشياء.",
   sukuk=True,
   rev0=2500, nm=0.06, gm=0.42, growth=0.008, season=0.015, vol=0.03,
   shares=898, debt_ratio=2.5, sukuk_share=0.6, price0=11)

# --- Healthcare (4) ---------------------------------------------------------
co("4013", "د. سليمان الحبيب", "Dr. Sulaiman Al Habib", "healthcare",
   "أكبر مجموعة رعاية صحية خاصة في الشرق الأوسط، تدير مستشفيات ومراكز طبية في السعودية والإمارات والبحرين.",
   sukuk=False,
   rev0=2550, nm=0.20, gm=0.42, growth=0.025, season=0.01, vol=0.015,
   shares=350, debt_ratio=0.8, sukuk_share=0.0, price0=285)
co("4002", "المواساة", "Mouwasat", "healthcare",
   "مجموعة مستشفيات خاصة رائدة في المنطقة الشرقية تتوسع في الرياض وجدة بمشاريع مستشفيات جديدة.",
   sukuk=False,
   rev0=680, nm=0.25, gm=0.45, growth=0.018, season=0.01, vol=0.02,
   shares=500, debt_ratio=0.6, sukuk_share=0.0, price0=87)
co("4004", "دلة الصحية", "Dallah Health", "healthcare",
   "شركة رعاية صحية تدير مستشفيات دلة في الرياض وتتوسع في العيادات المتخصصة والصيدليات.",
   sukuk=False,
   rev0=780, nm=0.14, gm=0.38, growth=0.020, season=0.01, vol=0.025,
   shares=94, debt_ratio=1.2, sukuk_share=0.0, price0=130)
co("4005", "رعاية", "Care", "healthcare",
   "الشركة الوطنية للرعاية الطبية تدير مستشفيات ومراكز طبية في الرياض وتخدم قطاع التأمين الطبي.",
   sukuk=False,
   rev0=310, nm=0.16, gm=0.36, growth=0.015, season=0.01, vol=0.03,
   shares=45, debt_ratio=0.5, sukuk_share=0.0, price0=150)

# --- Retail (4) -------------------------------------------------------------
co("4190", "جرير", "Jarir Marketing", "retail",
   "أكبر متاجر التجزئة للإلكترونيات والكتب واللوازم المكتبية في المملكة بشبكة معارض واسعة وتجارة إلكترونية نامية.",
   sukuk=False,
   rev0=2450, nm=0.10, gm=0.15, growth=0.008, season=0.10, vol=0.02,
   shares=1200, debt_ratio=0.3, sukuk_share=0.0, price0=13)
co("4003", "إكسترا", "eXtra", "retail",
   "متاجر المتحدة للإلكترونيات، ثاني أكبر بائع تجزئة للإلكترونيات مع ذراع تمويل استهلاكي (تساهيل) سريعة النمو.",
   sukuk=False,
   rev0=1750, nm=0.075, gm=0.18, growth=0.015, season=0.12, vol=0.025,
   shares=80, debt_ratio=1.0, sukuk_share=0.0, price0=95)
co("4164", "النهدي", "Nahdi Medical", "retail",
   "أكبر سلسلة صيدليات في الشرق الأوسط بأكثر من 1100 صيدلية وخدمات صحية رقمية متنامية.",
   sukuk=False,
   rev0=2250, nm=0.10, gm=0.36, growth=0.010, season=0.03, vol=0.015,
   shares=130, debt_ratio=0.4, sukuk_share=0.0, price0=130)
co("4161", "بن داود", "BinDawood Holding", "retail",
   "مجموعة أسواق بن داود والدانوب للتجزئة الغذائية، بحضور قوي في مكة والمدينة يستفيد من مواسم الحج والعمرة.",
   sukuk=False,
   rev0=1300, nm=0.045, gm=0.33, growth=0.006, season=0.07, vol=0.03,
   shares=1143, debt_ratio=0.9, sukuk_share=0.0, price0=7)

# --- Utilities (3) ----------------------------------------------------------
co("5110", "كهرباء السعودية", "Saudi Electricity", "utilities",
   "المزود الرئيسي للكهرباء في المملكة، يمتلك ويشغل معظم قدرات التوليد والنقل والتوزيع.",
   sukuk=True,
   rev0=19500, nm=0.13, gm=0.35, growth=0.006, season=0.15, vol=0.02,
   shares=4166, debt_ratio=4.5, sukuk_share=0.55, price0=17)
co("2082", "أكوا باور", "ACWA Power", "utilities",
   "مطور ومشغل عالمي لمحطات توليد الكهرباء وتحلية المياه والهيدروجين الأخضر في 12 دولة.",
   sukuk=True,
   rev0=1600, nm=0.115, gm=0.30, growth=0.020, season=0.02, vol=0.04,
   shares=731, debt_ratio=5.0, sukuk_share=0.3, price0=250)
co("2081", "مرافق", "Marafiq", "utilities",
   "شركة المرافق لتقديم خدمات الكهرباء والمياه والصرف الصحي للمدن الصناعية في الجبيل وينبع.",
   sukuk=False,
   rev0=1150, nm=0.09, gm=0.28, growth=0.008, season=0.10, vol=0.03,
   shares=250, debt_ratio=2.5, sukuk_share=0.0, price0=48)

# --- Food (4) ---------------------------------------------------------------
co("2280", "المراعي", "Almarai", "food",
   "أكبر شركة ألبان وأغذية متكاملة في الشرق الأوسط، تنتج الألبان والعصائر والمخبوزات والدواجن.",
   sukuk=True,
   rev0=5100, nm=0.105, gm=0.33, growth=0.010, season=0.04, vol=0.015,
   shares=1000, debt_ratio=2.2, sukuk_share=0.45, price0=56)
co("2050", "صافولا", "Savola Group", "food",
   "مجموعة استثمارية رائدة في الأغذية والتجزئة تمتلك علامات زيوت وسكر ومكرونة وحصة في المراعي.",
   sukuk=True,
   rev0=6800, nm=0.035, gm=0.20, growth=0.006, season=0.03, vol=0.03,
   shares=534, debt_ratio=1.8, sukuk_share=0.35, price0=33)
co("6002", "هرفي", "Herfy Foods", "food",
   "سلسلة مطاعم وجبات سريعة سعودية بأكثر من 400 فرع مع مخابز ومصانع لحوم خاصة بها.",
   sukuk=False,
   rev0=330, nm=0.055, gm=0.25, growth=0.004, season=0.03, vol=0.03,
   shares=65, debt_ratio=1.0, sukuk_share=0.0, price0=28)
co("6010", "نادك", "NADEC", "food",
   "شركة زراعية وغذائية وطنية تنتج الألبان والعصائر والزيوت وتدير مشاريع زراعية واسعة.",
   sukuk=False,
   rev0=800, nm=0.06, gm=0.28, growth=0.008, season=0.03, vol=0.025,
   shares=253, debt_ratio=1.5, sukuk_share=0.0, price0=26)

# --- Real Estate (3) --------------------------------------------------------
co("4220", "إعمار المدينة الاقتصادية", "Emaar EC", "realestate",
   "مطور مدينة الملك عبدالله الاقتصادية على البحر الأحمر، يعمل في التطوير العقاري والموانئ والمناطق الصناعية.",
   sukuk=True,
   rev0=600, nm=0.15, gm=0.30, growth=0.012, season=0.02, vol=0.08,
   shares=850, debt_ratio=4.0, sukuk_share=0.3, price0=12)
co("4322", "رتال", "Retal Urban Development", "realestate",
   "مطور عقاري سعودي يركز على المجتمعات السكنية الحديثة ويستفيد من برامج الإسكان الوطنية.",
   sukuk=False,
   rev0=620, nm=0.115, gm=0.24, growth=0.022, season=0.02, vol=0.04,
   shares=400, debt_ratio=1.5, sukuk_share=0.0, price0=16)
co("4300", "دار الأركان", "Dar Al Arkan", "realestate",
   "مطور عقاري كبير يعمل في تطوير الأراضي والمشاريع السكنية والتجارية داخل المملكة وخارجها.",
   sukuk=True,
   rev0=950, nm=0.16, gm=0.35, growth=0.008, season=0.02, vol=0.05,
   shares=1080, debt_ratio=3.5, sukuk_share=0.7, price0=9)

assert len(C) == 33, f"expected 33 companies, got {len(C)}"

# ---------------------------------------------------------------------------
# Anomaly injection: applied to the LATEST quarter (index 11) only, so the
# z-score detector (latest vs trailing 8) has a clean signal to find.
# ---------------------------------------------------------------------------
ANOMALIES = {
    "7030": {"metric": "net_margin", "factor": -0.9,
             "note": "impairment charge collapses net margin"},
    "4003": {"metric": "revenue", "factor": +0.55,
             "note": "one-off revenue surge"},
    "6010": {"metric": "fcf", "factor": -1.6,
             "note": "working-capital blowout turns FCF deeply negative"},
    "4300": {"metric": "net_margin", "factor": +1.2,
             "note": "one-off land sale gain doubles net margin"},
}


def seasonal(q_index: int, amplitude: float) -> float:
    """Peak in Q4 (index%4 == 1 for our list starting at Q3): use quarter number."""
    qnum = int(QUARTERS[q_index][-1])  # 1..4
    return amplitude * math.cos((qnum - 4) / 4 * 2 * math.pi)


def gen_financials(c: dict) -> list[dict]:
    p = c["params"]
    rows = []
    price = p["price0"]
    for i, q in enumerate(QUARTERS):
        drift = (1 + p["growth"]) ** i
        season = 1 + seasonal(i, p["season"])
        rev_shock = RNG.gauss(0, p["vol"])
        nm_shock = RNG.gauss(0, p["vol"] * 1.5)
        gm_shock = RNG.gauss(0, p["vol"] * 0.6)
        fcf_shock = RNG.gauss(0, 0.25)

        # Keep the latest quarter in-band for non-anomaly companies so the
        # z-score detector flags ONLY the deliberately embedded anomalies.
        if i == len(QUARTERS) - 1 and c["ticker"] not in ANOMALIES:
            rev_shock = max(-p["vol"], min(p["vol"], rev_shock))
            nm_shock = max(-p["vol"] * 1.5, min(p["vol"] * 1.5, nm_shock))
            fcf_shock = max(-0.25, min(0.25, fcf_shock))

        revenue = p["rev0"] * drift * season * (1 + rev_shock)
        nm = p["nm"] * (1 + nm_shock)
        gm = p["gm"] * (1 + gm_shock)

        # capex intensity varies by sector; FCF ~ NI plus D&A minus capex swing
        fcf_ratio = 1.0 + fcf_shock

        # ---- anomaly injection on the latest quarter ----
        if i == len(QUARTERS) - 1 and c["ticker"] in ANOMALIES:
            a = ANOMALIES[c["ticker"]]
            if a["metric"] == "revenue":
                revenue *= 1 + a["factor"]
            elif a["metric"] == "net_margin":
                nm *= 1 + a["factor"]
            elif a["metric"] == "fcf":
                fcf_ratio += a["factor"]

        net_income = revenue * nm
        fcf = net_income * fcf_ratio
        eps = net_income / p["shares"]
        total_debt = p["rev0"] * p["debt_ratio"] * (1 + 0.01 * i)
        sukuk = total_debt * p["sukuk_share"] if c["has_sukuk"] else 0.0
        # zakat: 2.5% of an approximated zakat base (equity proxy ~= 4x NI run-rate)
        zakat = max(0.0, 0.025 * 4 * abs(net_income))

        # share price random-walks with a pull toward earnings trend
        price *= (1 + p["growth"] * 0.8 + RNG.gauss(0, p["vol"] * 1.2))

        rows.append({
            "quarter": q,
            "revenue": round(revenue, 1),
            "net_income": round(net_income, 1),
            "gross_margin": round(gm, 4),
            "net_margin": round(nm, 4),
            "eps": round(eps, 3),
            "total_debt": round(total_debt, 1),
            "sukuk_debt": round(sukuk, 1),
            "zakat_expense": round(zakat, 1),
            "free_cash_flow": round(fcf, 1),
            "share_price": round(price, 2),
        })
    if c["ticker"] not in ANOMALIES:
        _sanitize_latest(rows, c)
    return rows


def _zscore(latest: float, trailing: list[float]) -> float:
    import statistics
    mean = statistics.mean(trailing)
    std = statistics.stdev(trailing)
    return (latest - mean) / std if std else 0.0


def _pull_in_band(values: list[float]) -> float | None:
    """If the last value breaks |z|>1.6 vs trailing 8, return an in-band value."""
    import statistics
    trailing = values[-9:-1]
    z = _zscore(values[-1], trailing)
    if abs(z) <= 1.6:
        return None
    mean = statistics.mean(trailing)
    std = statistics.stdev(trailing)
    return mean + (1.4 if z > 0 else -1.4) * std


def _sanitize_latest(rows: list[dict], c: dict) -> None:
    """Guarantee non-anomaly companies stay under the z-score detector's
    threshold on every monitored metric — only the deliberately embedded
    anomalies should ever fire."""
    p = c["params"]
    last, prev = rows[-1], rows[-2]

    # 1. revenue growth (QoQ)
    growth = [rows[i]["revenue"] / rows[i - 1]["revenue"] - 1 for i in range(1, len(rows))]
    target = _pull_in_band(growth)
    if target is not None:
        new_rev = prev["revenue"] * (1 + target)
        scale = new_rev / last["revenue"]
        last["revenue"] = round(new_rev, 1)
        last["net_income"] = round(last["net_income"] * scale, 1)
        last["free_cash_flow"] = round(last["free_cash_flow"] * scale, 1)

    # 2. net margin
    margins = [r["net_margin"] for r in rows]
    target = _pull_in_band(margins)
    if target is not None:
        ratio = target / last["net_margin"] if last["net_margin"] else 1.0
        last["net_margin"] = round(target, 4)
        last["net_income"] = round(last["revenue"] * target, 1)
        last["free_cash_flow"] = round(last["free_cash_flow"] * ratio, 1)

    # keep derived fields consistent with any net-income change
    last["eps"] = round(last["net_income"] / p["shares"], 3)
    last["zakat_expense"] = round(max(0.0, 0.025 * 4 * abs(last["net_income"])), 1)

    # 3. free cash flow (set directly; independent of the other two)
    fcfs = [r["free_cash_flow"] for r in rows]
    target = _pull_in_band(fcfs)
    if target is not None:
        last["free_cash_flow"] = round(target, 1)


# ---------------------------------------------------------------------------
# News: 4–6 Arabic items per company from sector-aware templates.
# Anomaly companies get a headline hinting at the event.
# ---------------------------------------------------------------------------
SOURCES = ["أرقام", "تداول", "الاقتصادية", "معلومات مباشر"]

GENERIC_TEMPLATES = [
    ("{n} تعلن نتائجها المالية للربع الثاني 2026", "2026-06-28",
     "أعلنت {n} عن نتائجها المالية للربع الثاني من عام 2026، حيث جاءت النتائج ضمن نطاق توقعات المحللين مع استمرار الشركة في تنفيذ خططها التشغيلية."),
    ("{n} توصي بتوزيع أرباح نقدية عن النصف الأول", "2026-06-15",
     "أوصى مجلس إدارة {n} بتوزيع أرباح نقدية على المساهمين عن النصف الأول من العام، بما يعكس متانة المركز المالي للشركة وتدفقاتها النقدية."),
    ("{n} توقع اتفاقية شراكة استراتيجية جديدة", "2026-05-20",
     "وقعت {n} اتفاقية شراكة استراتيجية تهدف إلى تعزيز حضورها في السوق المحلي ودعم خطط النمو المستقبلية ضمن مستهدفات رؤية 2030."),
    ("تغطية بحثية: رفع السعر المستهدف لسهم {n}", "2026-05-02",
     "رفعت إحدى شركات الأبحاث المالية السعر المستهدف لسهم {n} مع الإبقاء على التوصية، مشيرة إلى تحسن هوامش الربحية وآفاق النمو القطاعية."),
    ("{n} تعتمد خطة استثمارية لتوسعة أعمالها", "2026-04-10",
     "اعتمد مجلس إدارة {n} خطة استثمارية جديدة لتوسعة الأعمال خلال العامين المقبلين، بتمويل من التدفقات التشغيلية والتسهيلات القائمة."),
]

SECTOR_TEMPLATES = {
    "banks": [
        ("{n} يعلن نمو محفظة التمويل خلال الربع الثاني", "2026-06-20",
         "أظهرت بيانات {n} نمو محفظة التمويل مدعومة بتمويل الشركات والرهن العقاري، مع استقرار جودة الأصول ونسب التعثر عند مستويات منخفضة."),
        ("{n} يصدر صكوكاً رأسمالية لتعزيز قاعدته", "2026-03-18",
         "أتم {n} إصدار صكوك رأسمالية من الشريحة الأولى بنجاح، وسط طلب قوي من المستثمرين المحليين والإقليميين، لدعم النمو المستقبلي."),
    ],
    "energy": [
        ("{n} تعلن صفقة توريد طويلة الأجل لآسيا", "2026-06-05",
         "أبرمت {n} اتفاقية توريد طويلة الأجل مع عملاء في آسيا، بما يعزز استقرار الإيرادات في ظل تقلبات أسعار الطاقة العالمية."),
    ],
    "materials": [
        ("أسعار البتروكيماويات تضغط على هوامش {n}", "2026-06-10",
         "لا تزال أسعار المنتجات البتروكيماوية العالمية تضغط على هوامش {n}، وسط توقعات بتعافٍ تدريجي مع تحسن الطلب الصيني."),
    ],
    "telecom": [
        ("{n} توسع تغطية الجيل الخامس في مدن جديدة", "2026-05-25",
         "أعلنت {n} توسيع تغطية شبكة الجيل الخامس لتشمل مدناً جديدة، ضمن استراتيجيتها لتعزيز إيرادات البيانات والخدمات الرقمية."),
    ],
    "healthcare": [
        ("{n} تفتتح مستشفى جديداً وتضيف طاقة سريرية", "2026-06-01",
         "افتتحت {n} مستشفى جديداً يضيف مئات الأسرّة إلى طاقتها الاستيعابية، في خطوة تدعم نمو الإيرادات مع ارتفاع الطلب على الرعاية الخاصة."),
    ],
    "retail": [
        ("مبيعات موسم المدارس تدعم أداء {n}", "2026-06-22",
         "تشير بيانات القطاع إلى أداء قوي لمبيعات {n} مع اقتراب موسم العودة للمدارس، وهو أحد أهم مواسم البيع خلال العام."),
    ],
    "utilities": [
        ("ذروة الصيف ترفع الطلب على خدمات {n}", "2026-06-18",
         "مع دخول ذروة الصيف، ارتفع الطلب على خدمات {n} إلى مستويات قياسية، ما يدعم إيرادات النصف الثاني تاريخياً."),
    ],
    "food": [
        ("{n} تطلق منتجات جديدة وتوسع حضورها الخليجي", "2026-05-12",
         "أطلقت {n} مجموعة منتجات جديدة وتخطط لتوسيع التوزيع في أسواق الخليج، ضمن استراتيجية تنويع مصادر الدخل."),
    ],
    "realestate": [
        ("{n} تعلن إطلاق مشروع سكني جديد", "2026-06-08",
         "أعلنت {n} إطلاق مشروع سكني جديد ضمن محفظة مشاريعها، مستفيدة من الطلب القوي على الوحدات السكنية وبرامج التمويل العقاري."),
    ],
}

ANOMALY_NEWS = {
    "7030": ("زين السعودية تسجل خسائر انخفاض قيمة استثنائية في الربع الثاني", "2026-06-30",
             "سجلت زين السعودية خسائر انخفاض قيمة غير متكررة أثرت بشكل كبير على صافي ربح الربع الثاني، فيما أكدت الإدارة أن الأثر محاسبي ولا يمس التدفقات النقدية التشغيلية."),
    "4003": ("قفزة غير اعتيادية في إيرادات إكسترا خلال الربع الثاني", "2026-06-29",
             "قفزت إيرادات إكسترا بشكل حاد خلال الربع الثاني مدفوعة بحملة توسع وافتتاحات متزامنة ونمو تمويل تساهيل، وسط تساؤلات المحللين حول استدامة هذا النمو."),
    "6010": ("نادك: ضغوط رأس المال العامل تقلب التدفق النقدي الحر إلى السالب", "2026-06-27",
             "أظهرت بيانات نادك تحول التدفق النقدي الحر إلى السالب بشكل حاد خلال الربع الثاني نتيجة تراكم المخزون وارتفاع الذمم المدينة، ما يستدعي متابعة دورة رأس المال العامل."),
    "4300": ("دار الأركان تسجل مكسباً استثنائياً من بيع أراضٍ يقفز بصافي الربح", "2026-06-26",
             "سجلت دار الأركان مكسباً غير متكرر من بيع محفظة أراضٍ ضخمة رفع صافي ربح الربع الثاني إلى مستويات غير مسبوقة، وهو بند لا يتوقع المحللون تكراره."),
}


def gen_news(c: dict) -> list[dict]:
    items = []
    name = c["name_ar"]
    templates = list(GENERIC_TEMPLATES)
    templates += SECTOR_TEMPLATES.get(c["sector"], [])
    RNG.shuffle(templates)
    count = RNG.randint(4, min(6, len(templates)))
    chosen = templates[:count]
    if c["ticker"] in ANOMALY_NEWS:
        chosen = chosen[: count - 1]
        h, d, b = ANOMALY_NEWS[c["ticker"]]
        items.append({"headline": h, "date": d, "body": b,
                      "source": RNG.choice(SOURCES)})
    for h, d, b in chosen:
        items.append({
            "headline": h.format(n=name),
            "date": d,
            "body": b.format(n=name),
            "source": RNG.choice(SOURCES),
        })
    items.sort(key=lambda x: x["date"], reverse=True)
    return items


# ---------------------------------------------------------------------------
# Leadership & company facts (synthetic demo profiles; a handful of the
# best-known real names, plausible invented ones for the rest).
# ceo_since = year appointed; exp = years in the industry.
# ---------------------------------------------------------------------------
LEADERSHIP = {
    "1120": ("وليد المقبل", "Waleed Al-Mogbel", 2021, 24, 1957, 20800, "الرياض", "Riyadh"),
    "1180": ("طارق السدحان", "Tareq Al-Sadhan", 2023, 26, 1953, 18400, "الرياض", "Riyadh"),
    "1150": ("عبدالله الخليفة", "Abdullah Al-Khalifa", 2020, 27, 2006, 4200, "الرياض", "Riyadh"),
    "1010": ("نادر الكثيري", "Nader Al-Kathiri", 2022, 23, 1957, 6100, "الرياض", "Riyadh"),
    "1140": ("عبدالعزيز العنيزان", "Abdulaziz Al-Onaizan", 2016, 30, 2004, 4600, "الرياض", "Riyadh"),
    "2222": ("أمين الناصر", "Amin Nasser", 2015, 42, 1933, 73000, "الظهران", "Dhahran"),
    "4030": ("أحمد السبيعي", "Ahmed Al-Subaey", 2019, 31, 1978, 4100, "الرياض", "Riyadh"),
    "2382": ("محمد فاروق", "Mohamed Farouk", 2017, 25, 2002, 5400, "الخبر", "Al Khobar"),
    "2010": ("عبدالرحمن الفقيه", "Abdulrahman Al-Fageeh", 2022, 28, 1976, 31000, "الرياض", "Riyadh"),
    "1211": ("روبرت ويلت", "Robert Wilt", 2022, 29, 1997, 7000, "الرياض", "Riyadh"),
    "2290": ("عبدالله الغامدي", "Abdullah Al-Ghamdi", 2020, 24, 2006, 2400, "ينبع", "Yanbu"),
    "2310": ("عبدالله السعدون", "Abdullah Al-Saadoon", 2015, 32, 1999, 1900, "الجبيل", "Jubail"),
    "7010": ("عليان الوتيد", "Olayan Alwetaid", 2021, 22, 1998, 26000, "الرياض", "Riyadh"),
    "7020": ("سالم الأحمدي", "Salem Al-Ahmadi", 2023, 21, 2004, 4300, "الرياض", "Riyadh"),
    "7030": ("سعد الصادق", "Saad Al-Sadhan", 2022, 19, 2008, 2600, "الرياض", "Riyadh"),
    "4013": ("صلاح الحبيب", "Salah Al-Habib", 1995, 31, 1995, 12400, "الرياض", "Riyadh"),
    "4002": ("محمد الفقيه", "Mohammed Al-Faqih", 2018, 22, 1974, 5600, "الدمام", "Dammam"),
    "4004": ("أحمد بابعير", "Ahmed Babaeer", 2016, 25, 1987, 4100, "الرياض", "Riyadh"),
    "4005": ("هيثم الفارس", "Haitham Al-Faris", 2021, 18, 1988, 2300, "الرياض", "Riyadh"),
    "4190": ("عبدالكريم أبانمي", "Abdulkarim Abanumay", 2014, 27, 1979, 4800, "الرياض", "Riyadh"),
    "4003": ("بندر قريشي", "Bandar Quraishi", 2019, 20, 2002, 3200, "الخبر", "Al Khobar"),
    "4164": ("ياسر جوهرجي", "Yasser Joharji", 2017, 23, 1986, 9600, "جدة", "Jeddah"),
    "4161": ("عبدالرزاق بن داود", "Abdulrazzag BinDawood", 2020, 26, 1984, 10200, "جدة", "Jeddah"),
    "5110": ("خالد القنون", "Khaled Al-Gnoon", 2020, 26, 2000, 29000, "الرياض", "Riyadh"),
    "2082": ("ماركو أرشيلي", "Marco Arcelli", 2023, 28, 2004, 4100, "الرياض", "Riyadh"),
    "2081": ("محمد البريك", "Mohammed Al-Buraik", 2019, 24, 2000, 3100, "الجبيل", "Jubail"),
    "2280": ("عبدالله البدر", "Abdullah Al-Bader", 2022, 25, 1977, 41000, "الرياض", "Riyadh"),
    "2050": ("وليد فطاني", "Waleed Fatani", 2021, 23, 1979, 14000, "جدة", "Jeddah"),
    "6002": ("يوسف عبدالغني", "Yousef Abdulghani", 2018, 21, 1981, 7800, "الرياض", "Riyadh"),
    "6010": ("سليمان الحربي", "Sulaiman Al-Harbi", 2023, 17, 1981, 6400, "الرياض", "Riyadh"),
    "4220": ("عبدالله السواحه", "Abdullah Al-Sawaha", 2021, 20, 2006, 900, "جدة", "Jeddah"),
    "4322": ("عبدالله البراك", "Abdullah Al-Braik", 2018, 19, 2012, 1400, "الخبر", "Al Khobar"),
    "4300": ("ماجد الرومي", "Majed Al-Romi", 2020, 22, 1994, 1100, "الرياض", "Riyadh"),
}


def leadership_fields(ticker: str) -> dict:
    ceo_ar, ceo_en, since, exp, founded, employees, hq_ar, hq_en = LEADERSHIP[ticker]
    return {
        "ceo_ar": ceo_ar,
        "ceo_en": ceo_en,
        "ceo_since": since,
        "ceo_experience_years": exp,
        "founded": founded,
        "employees": employees,
        "hq_ar": hq_ar,
        "hq_en": hq_en,
    }


def main() -> None:
    companies = [
        {**{k: v for k, v in c.items() if k != "params"}, **leadership_fields(c["ticker"])}
        for c in C
    ]
    financials = {c["ticker"]: gen_financials(c) for c in C}
    news = {c["ticker"]: gen_news(c) for c in C}

    (HERE / "companies.json").write_text(
        json.dumps({"sectors": SECTORS, "companies": companies},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    (HERE / "financials.json").write_text(
        json.dumps(financials, ensure_ascii=False, indent=2), encoding="utf-8")
    (HERE / "news.json").write_text(
        json.dumps(news, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(companies)} companies, "
          f"{sum(len(v) for v in financials.values())} financial rows, "
          f"{sum(len(v) for v in news.values())} news items")


if __name__ == "__main__":
    main()
