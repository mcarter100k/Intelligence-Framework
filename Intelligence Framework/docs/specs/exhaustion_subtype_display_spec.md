# Spec: exhaustion subtype display (display-honesty class, 2026-09-09)

**Status:** team-directed 2026-09-09 after the read-only diagnostic: GBP/JPY
brief rendered "4-hour chart: moving sideways (trend strength 64/100)" —
the deliberate JPY exhaustion routing (`_classify`, GBP_JPY & ADX ≥ 35 →
RANGING, regime_detection.py:681-683) flattened by a display layer with one
phrase for two meanings of RANGING. **This spec changes words, not routing:
decisions are byte-identical before/after.**
**Branch:** `feat/exhaustion-subtype-display` (off merged main). Merge held
for team review.

## 1. Single source of truth

The classifier body moves into `_classify_ex(...) -> (regime, subtype)`;
the existing `_classify(...)` becomes a thin wrapper returning the regime
(public surface unchanged — every current call site and test untouched).
The GBP_JPY exhaustion branch — the ONE place that knows the threshold —
returns `("RANGING", "EXHAUSTION")`; every other branch returns
`(regime, "")`. `get_regime` calls `_classify_ex` on BOTH timeframes (the
D1 site is the same instrument-parametric function, so the D1 equivalent
exists) and exposes:

- `regime_d1_subtype`, `regime_h4_subtype` — `"EXHAUSTION"` or `""`
- `structure_h4` — the confirmed H4 structure (previously computed but not
  exposed; the display needs direction WITHOUT re-deriving anything)

The filter-input dict passed to `apply_filter` is untouched. The display
layer contains no thresholds.

## 2. Display

One phrase builder in `decision_brief.py`, used everywhere the subtype
renders — direction from the confirmed structure field:

- UPTREND → "strong uptrend, flagged as overextended — the framework does
  not chase this (trend strength N/100)"
- DOWNTREND → "strong downtrend, …" (same template)
- unconfirmed structure → "strong extended move, …" (same template)

Render sites:
- **MARKET STATE** — the Daily / 4-hour segments use the phrase when their
  timeframe's subtype is EXHAUSTION.
- **THE FULL PICTURE** (`_build_narrative`) — the daily/4-hour sentences
  likewise.
- **REASON** — filter reasons carry technical regime tokens (e.g. "RANGING
  D1 + VOLATILE H4"); a subtype-aware pre-pass replaces the timeframe's
  RANGING token with the overextension wording before `_plain()`, so a
  reason can never call an exhaustion state "moving sideways".

Quiet-market RANGING (subtype `""`) keeps "moving sideways" everywhere.
Banned-token rules apply; "trend strength N/100" is the house rendering.

## 3. Behavior freeze

Routing, filter decisions, official decisions, composite resolution,
conflict detection: byte-identical. Only words change.

## 4. Gate 1 pins

- GBP_JPY, ADX 64, DOWNTREND structure → exhaustion words in MARKET STATE
  and FULL PICTURE; "moving sideways" absent for that timeframe.
- ADX 15 quiet RANGING (subtype "") → "moving sideways" retained.
- GBP_AUD with identical high-ADX inputs → no subtype, wording unchanged.
- `_classify` regime routing pinned unchanged across the branch matrix;
  official decision unchanged on both pairs given identical regime inputs
  with/without the new fields.
- REASON pre-pass: "RANGING D1" with D1 subtype EXHAUSTION renders the
  overextension wording, never "moving sideways".

## 5. Recorded (validation_log AND AGENTS.md — not built now)

"RANGING is overloaded (quiet vs JPY exhaustion). PRECONDITION: promoting
EXHAUSTION to a first-class regime — classifier, composite table, conflict
logic, tests — is REQUIRED before RANGE_TRADING_ENABLED may ever be set
True."

## Gate 2 (REALITY)

Live GBP/JPY brief showing the corrected sentence with today's real
64/100 exhaustion state; live GBP/AUD brief unchanged in wording class;
decision fields identical to a pre-change render of the same state.
