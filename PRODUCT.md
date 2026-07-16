# Product

## Register

product

## Users

Equity research analysts covering the Saudi stock market (Tadawul), working at
multi-monitor research desks during trading hours — and, for the demo, hackathon
judges viewing at 1366×768 projector resolution. Arabic-first professionals fluent
in Bloomberg/TradingView-class tools. Their job: build and defend a valuation
thesis for a listed company, fast.

## Product Purpose

Delta (دلتا) compresses the hours an analyst spends assembling a financial model
into minutes: pick a company → AI baseline forecast appears → adjust assumptions →
the gap between the analyst's view and the machine's view (the "Delta") is drawn
live as the hero visual, with fair value recalculating in real time. A monitoring
agent flags anomalous financial behavior unprompted. Success = an analyst trusts
the numbers enough to argue with them.

## Brand Personality

Precise, calm, market-native. The tool of a professional who reads numbers for a
living — confident enough to be quiet. Saudi identity is structural (Arabic RTL,
zakat, sukuk, Islamic-banking vocabulary), never decorative.

## Anti-references

- Generic SaaS dashboard cream/purple-gradient aesthetics.
- Crypto-trading dashboards: neon glows, gratuitous sparklines, gamified urgency.
- Western fintech navy-and-gold "trust" clichés.
- Any UI where Arabic feels like a translation layer instead of the native tongue.

## Design Principles

1. **The delta is the product** — the baseline-vs-analyst chart with its shaded gap
   gets the visual budget; everything else supports it.
2. **Numbers first-class** — tabular numerals, consistent SAR formatting, values
   readable at projector distance.
3. **Motion conveys state** — recalculation, flag arrival, card loading; nothing
   decorative, 150–250ms, reduced-motion respected.
4. **Earned familiarity** — market-data conventions (green up / red down, dark
   analytical surface, dense-but-ordered panels) so a Tadawul analyst trusts it on
   first sight.
5. **Offline-proof** — every state (loading, LLM fallback, empty, error) is
   designed, because the demo must never break.

## Accessibility & Inclusion

Full RTL layout; body text ≥4.5:1 contrast on the dark surface; charts distinguish
series by more than hue (solid vs dashed); `prefers-reduced-motion` honored;
keyboard-operable sliders with visible focus.
