# مسار العرض — Demo click path

Target resolution: **1366×768** (projector). Total time: ~4 minutes.
Works identically **with or without** `ANTHROPIC_API_KEY` (fallbacks are
schema-identical and formatted with the live valuation numbers).

## Act 1 — الشركة النظيفة: مصرف الراجحي (1120)

1. Open <http://localhost:5173> → sector grid (9 sectors, Arabic).
2. Click **البنوك** → the sector expands → click **مصرف الراجحي**.
3. Point out, top to bottom:
   - Header: العلامات **مصرف إسلامي** + **صكوك قائمة**؛ وكيل المراقبة يظهر
     تلقائياً: *«لا توجد إشارات غير اعتيادية»* — a clean company stays quiet.
   - Chart: white actuals, **green solid** AI baseline, metric toggle reads
     **دخل التمويل** (financing income — Islamic-bank vocabulary, not revenue).
   - Valuation breakdown: **الزكاة** as an explicit line, **منها صكوك** under debt,
     method reads *نموذج توزيعات (مصرف إسلامي)*.
4. Drag **نمو دخل التمويل السنوي** up ~5 points →
   the **amber dashed analyst line** lifts off the baseline, the **shaded delta
   band** opens up, and the fair-value cards re-pulse live: الدلتا turns green.
5. Click **توليد السيناريوهات** → three Arabic cards appear
   (متفائل / متشائم / ما قد يُبطل الفرضية) citing the actual numbers.

## Act 2 — الشركة المضطربة: زين السعودية (7030)

1. Breadcrumb **القطاعات** → **الاتصالات** → **زين السعودية**.
2. The monitoring agent fires **on load** — two red chips animate in:
   - **هامش صافي الربح z −32.4 (حرج)** — margin collapse
   - **التدفق النقدي الحر z −3.4 (حرج)**
   Hover a chip → Arabic explanation + the correlated news headline
   (*«زين السعودية تسجل خسائر انخفاض قيمة استثنائية»*).
3. The chart shows the story: net income cliff in 2026Q2, baseline projecting
   the recovery path.
4. Slide growth up → delta widens → regenerate scenarios: the
   **ما قد يُبطل الفرضية** card references the margin-recovery bet directly.

## Fallback drill (if asked "what if the internet dies?")

Kill the network — everything except live LLM keeps working, and the LLM cards
switch to the cached corpus tagged **نسخة محفوظة** with the same schema. The
demo cannot die.

## Reset between runs

Refresh the page (F5) — assumptions reset to the AI baseline automatically.
