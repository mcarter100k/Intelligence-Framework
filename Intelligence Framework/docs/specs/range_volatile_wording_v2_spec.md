# Spec v2: truthful wording for "range + volatile 4-hour" stand-asides

**Status:** spec for team review, written 2026-11-03, before any build. It
**supersedes `range_volatile_wording_spec.md` (v1, `bc4ceff`)**, which
review returned as CHANGES NEEDED. v1's body is left untouched, as a frozen
record (docs/specs/README.md). It touches one PROTECTED module,
`decision_brief.py`, and only rendered REASON text. **No decision, filter,
regime or ledger value changes.** It does not merge without team review.

## 0. Why v1 was wrong (review 2026-11-03, verified from the regime log)

- v1 proposed one neutral sentence: "4-hour chart is swinging hard … no
  settled direction yet".
- During the rally, every GBP/AUD row from 11-02 to 11-03 was
  `RANGING / VOLATILE` with `regime_h4_subtype = UNCONFIRMED_TREND`. The
  4-hour trend strength rose from 29.1 to 38.2, and the volatility ratio
  was only 1.09–1.11.
- So the 4-hour chart was a strong one-way move whose swing pattern had not
  confirmed. It was not swinging hard, and "no settled direction" denies
  what the trader could see.
- 4-hour VOLATILE covers five different states (`regime_detection.py:683-740`).
  One sentence cannot be true for all five.

## 1. The defect (unchanged from v1 §1)

- From 2026-11-01 18:00 to 2026-11-03 07:33 PST, every GBP/AUD brief said:
  "Range breaking down — 4-hour chart volatile inside daily chart range
  (trend strength 14.x/100). Wait for resolution before engaging."
- Over the same runs, price rose from 1.9042 to 1.9233.
- "Breaking down" read as bearish (AGENTS rule 4).

## 2. Sources (v1 §2, completed by review)

| Source | Reaches the trader in this cell? | Change |
|---|---|---|
| `decision_brief.py:535`: conflict path | **Yes** (the 2026-11-01 → 03 briefs) | **Reworded per §3** |
| `decision_brief.py:597`: STAND DOWN path, RANGING + VOLATILE | **Yes** when the conflict path is not taken | **Reworded per §3** |
| `regime_detection.py:219`: composite `note` | Through `official_decision.py:195` (`resolution_note` → `decision["reason"]`), rendered only by `_render_reason`'s fallback (~:674); and through `no_trade_filter.py:335` → `stand_rsn`, rendered at `decision_brief.py:505/515/599` | **Unchanged**, because in this cell the paths at :532/:596 return first, and the filter checks news first. **Pinned by test W7**: the note string never reaches the REASON line for this cell |
| `no_trade_filter.py:251`: `apply_filter` reason | Internal; pinned by `tests/test_exhaustion_display.py:107,113` | Unchanged |
| `regime_detection.py:1270`: manual CLI print of `stand_down_reason` | Manual tool output, not the brief | Unchanged |

No other "breaking down" exists in live code. `regime_detection.py:603/607`
("breakout higher" / "breakdown lower") are directional on purpose and true
there.

## 3. New wording: one sentence per 4-hour state

All sentences end with: **"…inside a sideways daily chart (daily trend
strength X/100). Standing aside until it confirms."** The STAND DOWN path,
which has no daily figure, drops the parenthesis.

| 4-hour state (from existing regime fields) | Opening clause |
|---|---|
| `regime_h4_subtype == "UNCONFIRMED_TREND"` **and** `_unconfirmed_fact(regime, "h4")` is available | "The 4-hour chart has been **{rising/falling}** — {up/down N pips over the last 40 hours} — but its swing pattern hasn't confirmed a trend yet," |
| `UNCONFIRMED_TREND` with no fact available | "The 4-hour chart is moving strongly but its swing pattern hasn't confirmed a direction yet," |
| `"TRANSITION_ZONE"` | "The 4-hour chart has no clear direction yet," |
| `"STRUCTURE_DISAGREES"` | "On the 4-hour chart the swing pattern and the momentum point opposite ways," |
| `""`, with `atr_ratio ≥ atr_spike_multiplier` | "The 4-hour chart is making unusually large swings," |
| `""`, with `atr_ratio < atr_compression_min` (GBP/JPY only) | "The 4-hour chart has gone unusually quiet," |
| `""`, otherwise | "The 4-hour chart is unsettled," |

**The direction word.**
- It comes only from `_unconfirmed_fact`. That helper is already approved
  (`unresolved_direction_polish_spec.md`, `unconfirmed_trend_display_spec.md`)
  and already rendered in MARKET STATE.
- It is a description of closed bars ("has been rising"), never a call.
- This answers the review's Option B question for the UNCONFIRMED case using
  data the brief already has. **Any further direction-of-travel feature
  stays out of scope.**

## 4. What must not change (each pinned by a test)

- **W1, decisions.** DECISION, CONFIDENCE, POSITION, the `apply_filter`
  result and every logged regime field are identical before and after.
  Only `reason` changes. Tested by rendering every §3 state before and after.
- **W2, plain English.** Every §3 sentence, sent through `_plain()`, passes
  the banned-token floor. The floor is not edited.
- **W3, no false direction.**
  - Every state except UNCONFIRMED-with-fact contains none of these words
    (case-insensitive, whole word or prefix as marked): down, up, rising,
    falling, higher, lower, breaking, breakout, breakdown, collapse, rally,
    drop, climb, surge, slide, sell, buy, bull*, bear*.
  - In the UNCONFIRMED-with-fact state, the only direction words are the
    helper's own, and they match the sign of `h4_change_pips_10`.
  - A fixture of the 2026-11-03 GBP/AUD row (+change) must render "rising".
- **W4, rule 12.**
  - No §3 sentence contains a wrapper, digest or latest-view trigger
    (`DECISION`, `SHADOW SIGNALS`, `Framework error`, `EXIT IF`,
    `WATCH FOR`, `STAND ASIDE`).
  - A real-wrapper run on a rendered brief in this cell sends no
    notification, against a control.
- **W5, nothing else reworded.**
  - Before the build, a golden file of the REASON rendered by `main` is
    committed. It sweeps every (D1 regime × H4 regime × H4 subtype ×
    decision) cell `_render_reason` can see.
  - After the build, every cell outside RANGING + VOLATILE is
    byte-identical to it.
- **W6, EXHAUSTION is never "sideways".** When `regime_d1_subtype` or
  `regime_h4_subtype` is EXHAUSTION, no §3 sentence renders, and the
  existing exhaustion wording wins (AGENTS: RANGING covers two states).
- **W7, internal note unreachable.** For RANGING D1 + VOLATILE H4, the
  rendered REASON never contains `regime_detection.py:219`'s note text.

## 5. Tests that change, old → new

- None expected. No test pins the old rendered sentence (`grep -rn "Range
  breaking" tests/` finds none; the lowercase filter string at
  `test_exhaustion_display.py` is internal and unchanged).
- Any found during the build are listed here before merge.

## 6. Verification

- **Gate 1:**
  - W1–W7.
  - Mutants: old sentence restored on each path; subtype dispatch removed
    (everything gets the fallback); helper direction inverted; the
    spike/compression branch swapped; `_plain()` bypassed; the EXHAUSTION
    guard removed.
- **Gate 2:** `reality_run.py brief --code <worktree>` while a pair sits in
  RANGING + VOLATILE. GBP/AUD was in this cell on 2026-11-03, but the cell
  may have changed by build time; if so, say that and show the fixture
  render instead. The real REASON is shown verbatim, with DECISION,
  CONFIDENCE and POSITION compared against a `main` run.

## 7. Out of scope

- A free-zone sweep of **all** REASON templates against the W3 word list.
  It would have found this defect before the owner did. Own commit, after
  this spec.
- Any change to when the framework stands aside. That is a strategy
  question; see R37/R38 (first-pullback study: no edge found) and the
  missed-moves report.
