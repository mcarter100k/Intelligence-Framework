# Spec v3: truthful wording for "range + volatile 4-hour" stand-asides

**Status:** spec for team review, written 2026-11-03, before any build.
**Supersedes v2 (`range_volatile_wording_v2_spec.md`, `6d477b8`) and v1
(`bc4ceff`).** Both bodies are left untouched as frozen records. It touches
one PROTECTED module, `decision_brief.py`, and only rendered REASON text.
`regime_detection.py` is **not** in scope. No decision, filter, regime or
ledger value changes. It does not merge without team review.

Everything in v2 stands except the items below, which replace the
corresponding v2 sections. The defect (v2 §1) and the source table (v2 §2)
are unchanged.

## 0. Why v2 was changed (review 2026-11-03)

1. **v2 keyed two sentences on data the brief doesn't have.**
   - It split the 4-hour subtype `""` into "unusually large swings" and
     "unusually quiet" using `atr_ratio`.
   - The 4-hour classifier's ratio (`h4_atr_ratio`, `regime_detection.py:968`)
     is a local variable and never reaches the regime dict. The dict carries
     only the daily ratio (`atr_vs_avg`).
   - A daily RANGING label already implies the daily ratio sits between the
     compression and spike thresholds (`:685-693` run before `:711`).
   - So both sentences could never render. Verified by code reading here
     (`:960-985`).
2. **Two states cannot occur on the 4-hour chart.**
   - The 4-hour slope is forced from structure (`:971-976`: UPTREND → +1,
     DOWNTREND → −1). Together with `:725-740`, at trend strength 25+ a
     confirmed structure always trends, and TRANSITIONAL always gives
     UNCONFIRMED_TREND.
   - So 4-hour `STRUCTURE_DISAGREES` and the residual `""` are unreachable.
   - The live log agrees: 4-hour subtypes are TRANSITION_ZONE 56,
     EXHAUSTION 12, UNCONFIRMED_TREND 11, STRUCTURE_DISAGREES 0.
   - A 4-hour `""` with VOLATILE comes only from a spike, or compression on
     GBP/JPY.
3. **The shared ending was wrong.** "Until it confirms" fits only the
   unconfirmed trend.

## 3 (replaces v2 §3). Wording per 4-hour state

The format is: opening clause + " inside a sideways daily chart (daily
trend strength X/100). " + ending. The STAND DOWN path, which has no daily
figure, drops the parenthesis.

| 4-hour state | Reachable? | Opening clause | Ending |
|---|---|---|---|
| `UNCONFIRMED_TREND`, fact available and \|`h4_change_pips_10`\| ≥ 10 | **Yes** (the 2026-11-03 rally) | "The 4-hour chart has been **{rising/falling}** — {up/down N pips over the last 40 hours} — but its swing pattern hasn't confirmed a trend yet," | "Standing aside until it confirms." |
| `UNCONFIRMED_TREND`, no fact or \|change\| < 10 pips | Yes | "The 4-hour chart is moving strongly but its swing pattern hasn't confirmed a direction yet," | "Standing aside until it confirms." |
| `TRANSITION_ZONE` | Yes | "The 4-hour chart has no clear direction yet," | "Standing aside until a direction emerges." |
| `""` (VOLATILE from a spike, or GBP/JPY compression) | Yes | "The 4-hour chart's volatility is well outside its normal range," | "Standing aside until the 4-hour picture settles." |
| `STRUCTURE_DISAGREES` | **Unreachable on the 4-hour chart** (§0.2). Defensive fallback only | "On the 4-hour chart the swing pattern and the momentum point opposite ways," | "Standing aside until the 4-hour picture changes." |
| any other subtype | **Unreachable.** Defensive fallback only | "The 4-hour chart is unsettled," | "Standing aside until the 4-hour picture changes." |

- **The `""` sentence.** One sentence covers both spike and compression,
  and it is true for both: the ratio is ≥ the spike multiplier or below the
  compression minimum. This keeps `regime_detection.py` out of scope.
  Splitting the two would need `h4_atr_vs_avg` exposed as a display field.
  That would be its own spec, and only if wanted.
- **The 10-pip floor.** It is a display rule, so "up 2 pips" is never
  presented as a move. Below it, the no-fact sentence renders.
- **Rule 9 for tests.** Tests of the two unreachable rows are labelled
  "defensive fallback: unreachable on H4 per §0.2". They are not counted as
  coverage of a live state. A further test pins the unreachability: across
  the W5 grid's real `_classify_ex` outputs for the 4-hour chart, neither
  state is produced.

## 4 (amends v2 §4)

- **W3.**
  - The 2026-11-03 fixture is **synthetic**: a regime dict with
    `regime_h4_subtype = UNCONFIRMED_TREND` and `h4_change_pips_10 = +190`,
    modelled on the logged row, not read from it. It must render "rising".
  - A twin with −190 must render "falling".
  - A twin with +4 must render the no-fact sentence.
- **W5, the explicit grid.**
  - A committed generator script, `tests/golden/reason_grid.py`, builds
    every combination of:
    - `regime_d1` ∈ {TRENDING_UP, TRENDING_DOWN, RANGING, VOLATILE};
    - `regime_d1_subtype` ∈ {"", TRANSITION_ZONE, UNCONFIRMED_TREND, EXHAUSTION, STRUCTURE_DISAGREES};
    - `regime_h4` × `regime_h4_subtype`, the same two sets;
    - decision ∈ {LONG, SHORT, STAND DOWN};
    - `conflict` ∈ {True, False};
    - news gating ∈ {gating, not};
    - `filter_block` ∈ {True, False};
    - `atr_vs_avg` ∈ {0.5, 1.0, 2.0};
    - `h4_change_pips_10` ∈ {None, +4, +190, −190}.
  - Fixed values: trend strengths 14.5 (D1) and 33.0 (H4), and one fixed
    weekly context.
  - It writes `tests/golden/reason_grid_main.json`: cell key → sha256 of
    `_render_reason(...)`. It is generated from **`main` before the build**
    and committed in its own commit.
  - After the build, every cell whose (D1, H4) is not (RANGING, VOLATILE)
    must match its hash. The (RANGING, VOLATILE) cells must render the §3
    sentence for their subtype (EXHAUSTION excepted, per W6).
  - The grid includes impossible combinations on purpose. Rendering must not
    crash on any of them, and they are hashed like the rest.
- **W1, W2, W4, W6, W7:** as in v2.

## 6 (amends v2 §6). Mutants

- Old sentence restored on each path.
- Subtype dispatch removed (all fallback).
- Helper direction inverted.
- 10-pip floor removed.
- Endings swapped between states.
- `_plain()` bypassed.
- EXHAUSTION guard removed.
- A reworded non-target cell, to prove W5 sees it.
