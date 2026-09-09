# Spec: unconfirmed-trend display subtype (display-layer only)

**Status:** team-directed 2026-09-09, stage 2 of the two-stage directive —
built because stage 1 confirmed **lag, not a bug**. Same shape as the
exhaustion subtype: words change, decisions byte-identical, **the structure
rule is UNTOUCHED**.
**Branch:** `feat/unconfirmed-trend-display`. Merge held for review.

## Stage-1 finding this rests on (2026-09-09, GBP_AUD D1, read-only)

Engine and hand-replication agree: TRANSITIONAL comes from the mixed pair
`lh=True, hl=True`. Swing highs stepped down (1.91912 → 1.89716,
2026-08-19 → 08-31: lower high ✓). **The blocking pair is the swing lows:**
latest confirmed swing low 1.90733 (2026-08-04) vs prior 1.90030
(2026-07-27) — a HIGHER low, recorded before the decline. Price has since
fallen ~290 pips (closed 1.9052 → 1.8762 over 10 sessions) without ONE
confirmed lower low, because in a persistent decline every new low keeps
undercutting before the 3-bar shape completes and a close confirms above
it. Zero unconfirmed pivot-low candidates exist yet — the leg's lowest low
(1.87323, 2026-09-06) is still inside the 3-bar tail window. Designed
confirmation lag; the rule is doing exactly what Problem 2 asked of it.

## 1. Single source of truth

`_classify_ex`'s final fallthrough — reached when ADX sits in the trending
band (≥ 25, below the exhaustion overrides) and structure has not
confirmed — returns subtype **"UNCONFIRMED_TREND"** when structure is
TRANSITIONAL (and `""` otherwise). Exposed for D1 and H4 via the existing
`regime_d1_subtype` / `regime_h4_subtype` fields. Routing unchanged: the
regime stays VOLATILE.

## 2. The direction descriptor is a FACT, not a label

`get_regime` exposes `d1_change_pips_10`: the signed CLOSED-bar price
change over the last 10 sessions, in pips. A stated pip change is
description, not classification — Problem 2 retired slope-based direction
claims and this does not resurrect them. Also exposed, for the concrete
EXIT IF: `d1_pending_low` / `d1_pending_high` (the running extreme of the
current leg — the only candidate that can become the next confirmed pivot)
with `_age` in closed sessions, and the structure engine's existing
`lh`/`hl` flags as `d1_lower_highs` / `d1_higher_lows` (read from the
structure result, not recomputed).

## 3. Display (subtype + fact present; otherwise wording unchanged)

- **MARKET STATE:** "Daily chart: falling — down 290 pips over the last 10
  sessions — but the confirmation rule isn't met yet (trend strength
  25/100)" (rising mirror).
- **FULL PICTURE:** "The daily chart has been falling — down 290 pips over
  the last 10 sessions. The engine is waiting for the latest low to
  confirm before calling it a trend."
- **EXIT IF becomes concrete** — names the pending pivot and its TRUE
  condition, rendered only when the claim would be honest (falling: lower
  highs already in place AND the pending low would be a lower low; rising
  mirror):
  - candidate younger than 3 sessions: "The low near 1.8732 confirms as a
    swing low — it stays the lowest point for N more session(s) and a
    session then closes above it — with the 4-hour chart aligned, the
    downtrend is confirmed then. Revisit then."
  - shape already complete: "…confirms the moment a session closes back
    above it…"
  - Otherwise (flags don't line up, candidate stale >30 sessions, or no
    fact): the existing generic stair-step sentence stays.

**Deviations from the directive's illustrative text, flagged:** (a) today's
fact is −290 pips, not the example's −302; the number is computed, never
copied. (b) The directive's parenthetical "(three sessions closing above
it)" does not match the engine's actual rule — a pivot low needs the 3-bar
shape and then ONE close above it. The display renders the true rule;
anything else would be a new display-honesty bug.

## 4. Vocabulary

For this subtype, "choppy" and "no clear direction" are banned (test-
enforced on the D1 clauses). Transition-zone VOLATILE (ADX 18–25, subtype
"") keeps its current wording verbatim. **Open questions logged in
validation_log:** whether transition-zone VOLATILE deserves the same
factual treatment (the directive's literal "choppy is permitted ONLY for
quiet RANGING" collides with "transition-zone keeps current wording",
which is "choppy with no clear direction" — kept as directed, tension
recorded); and whether the H4 subtype (exposed but unrendered — the
directed templates are daily-only) should get a display of its own.

## 5. Gates

- **Gate 1:** classifier subtype pins (trending-band TRANSITIONAL → tagged;
  18–25 transition zone → untagged; confirmed structure → untagged;
  routing matrix unchanged); today's GBP_AUD D1 shape → falling/unconfirmed
  wording + concrete EXIT IF (both age variants + the honesty-gated
  fallback); transition-zone case → wording unchanged; H4 RANGING 17 →
  unchanged; official decision identical with/without the new fields on
  both pairs; vocabulary ban.
- **Gate 2 (REALITY):** live GBP/AUD brief showing the new daily sentence
  and the concrete EXIT IF against today's real state.
