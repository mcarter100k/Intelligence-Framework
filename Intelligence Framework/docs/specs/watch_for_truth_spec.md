# Spec: WATCH FOR names only conditions a trade actually needs

**Status:** PROPOSED 2026-11-05, awaiting team review. Not built.
**Protected:** `decision_brief.py` (`_build_invalidation`, and the matching
exit-watch flags in `_machine_flags`).
**Supersedes:** §2 and the §6 truth sweep of `brief_summary_block_spec.md`
(that file is unchanged; its §2 was partly false, validation_log 2026-11-05
TEAM REVIEW). The label stays "WATCH FOR"; renaming it "Changes if" reversed
its meaning in some branches (review 2.4).

## 1. Why

On a stand-aside run, WATCH FOR tells the owner what to wait for, and the 07:30
digest quotes it. Several branches name conditions that cannot produce a trade:

| Branch (stand-aside) | Says today | Problem |
|---|---|---|
| D1 RANGING (quiet) | "trend strength drops below 18 or 4-hour resolves to clean trend" | Below 18 *is* this state. A 4-hour trend alone is insufficient |
| D1 RANGING (GBP/JPY EXHAUSTION, 35+) | Same sentence | "Below 18" is meaningless at 35+ |
| D1 VOLATILE, strength under 25 | "crosses 25 with confirmed 4-hour structure holding" | The override trades at 18–25 without crossing 25 |
| D1 VOLATILE, STRUCTURE_DISAGREES | "direction turns to agree with its structure, or the structure breaks" | The override trades with the slope still disagreeing; a broken structure cannot trade |
| D1 VOLATILE, UNCONFIRMED_TREND (fallback text) | "…with the 4-hour chart aligned" | A trending daily trades with a VOLATILE 4-hour |
| D1 TRENDING, stood aside | "structure breaks — price closes below the swing low" | That is the trend ending, not the stand-aside lifting |
| Fallback | "resolves to clean trending or ranging state" | Ranging never trades |

Each "problem" entry is from the sweep in §2 or from reading the code. Displayed
strength is rounded (`:.0f`): 17.6 shows as "18" beside "drops below 18"
(review 2.2).

## 2. What every trade needs (VERIFIED)

Sweep, 2026-11-05. The real `_classify_ex` (daily and 4-hour),
`get_composite_regime`, `_detect_conflict`, `apply_filter` and
`get_official_decision` over strength, volatility ratio, structure, slope,
4-hour state, weekly context and instrument. Inputs were built as in the code
reviewer's harness. 3,175,200 cells, 56,028 trading. Run from a temp directory
with the network blocked: `/private/tmp/claude-501/specs-round/wf_sweep.py`
and `wf_sweep2.py`. In every trading cell (0 counter-cells each):

- **N1** The daily is not RANGING. Its strength is 18 or more, or its
  volatility jumped (GBP/AUD 1.2×, GBP/JPY 1.5×).
- **N2** The daily swing pattern is confirmed in the trade's direction.
- **N3** Either the daily is trending in the trade's direction, **or** (the
  override) the 4-hour trends in that direction at strength 25+, the daily is
  under 32, and the weekly picture agrees.
- **N4** The weekly picture is not against the trade.
- **N5** The 4-hour is not trending against the trade, and not exhausted.
- **N6** Daily volatility is under 2× normal.
- **N7** GBP/JPY daily strength is under 35.

**Not necessary** (counter-cells found):
- "daily strength reaches 25" (10,800);
- "the daily trends" (16,884);
- "daily slope agrees with structure" (12,168).

**INFERRED, to be swept:** GBP/JPY volatility above the 0.8× compression floor.
The harness did not isolate it.

These are **necessary, not sufficient.** Grade and conviction can still stand a
cell aside. WATCH FOR therefore always ends "revisit then", never "trade then".

## 3. Change

WATCH FOR on a stand-aside run names **the clauses of N1–N7 the current state
fails**, in plain words, most restrictive first. Proposed sentences:

- **D1 quiet range:** "The daily chart leaves its quiet range with its swing
  pattern confirmed in one direction, and either the daily trends that way or
  the 4-hour trends strongly that way with the weekly agreeing. Revisit then."
- **D1 EXHAUSTION:** "Daily trend strength falls back below 35. The framework
  neither fades nor chases an exhausted move. Revisit then."
- **D1 VOLATILE (any subtype):** name the failing clauses. For
  STRUCTURE_DISAGREES, the slope turning is not required: say "the daily trends
  with its structure, or the 4-hour trends strongly that way with the weekly
  agreeing".
- **D1 UNCONFIRMED_TREND:** keep the concrete pending-swing sentence (N2).
  Replace "with the 4-hour aligned" by "with the 4-hour not trending against
  it".
- **D1 TRENDING, stood aside:** name what blocks it (N4, N5, N6 or N7), for
  example "the 4-hour stops trending against the daily" or "the weekly picture
  stops pointing the other way". Not the trend's end.
- **Numbers:** a threshold is shown next to the unrounded value ("17.6"), or no
  value is shown.

The exit-watch flags in `_machine_flags` class (b) are aligned with the same
clauses. They must never fire on a clause outside N1–N7.

## 4. Out of scope

- Decision, filter and regime logic (unchanged; this is the text that describes
  them).
- The summary block.
- Range trading (`RANGE_TRADING_ENABLED` stays False).
- The EXHAUSTION first-class-regime precondition (AGENTS.md).

## 5. Gates

**Gate 1, the truth sweep (in the suite):**
- Two stages: (strength, slope, structure, volatility ratio, instrument, 4-hour
  state, weekly) → `_classify_ex` → composite, conflict, `apply_filter`,
  official decision.
- Built from the same input-building code `get_regime` uses (a pure helper, if
  extracting one is needed, under this spec), not a copy.
- For **every** stand-aside WATCH FOR branch:
  - **necessity:** every trading cell satisfies the branch's named condition;
  - **non-vacuity:** at least one cell satisfying it trades;
  - **old text:** the replaced sentence's condition is shown non-necessary or
    vacuous (positive control: the sweep catches today's text).

**Also in Gate 1:**
- DECISION and the filter result are identical to `main` across
  `test_decision_logic.py`.
- Stand-down matrix T34–T41 and the banned-token test pass unweakened.
- Digest: the watch clause carries the new sentence; nothing else in the line
  changes.

**Mutation:**
- Restore each old sentence (one mutant per branch).
- Show the rounded value next to a threshold.
- Make an exit-watch flag fire on "strength crosses 25" alone.

Each must be caught.

**Gate 2:** a real brief under `scripts/reality_run.py` with the WATCH FOR
lines shown before and after; project unchanged by hash.

**Gate 3, PENDING LIVE CONFIRMATION:** the owner reads a real digest watch
clause and it names something that can happen.

## 6. Questions for the team

1. N3's override route is grade B at 0.35× and was the 2026-05-15 losing
   precedent (R13). Should WATCH FOR mention it at all, or only the trending
   route? Recommended: mention it, because omitting a live route is the same
   kind of untruth this spec fixes.
2. Sentence length: the quiet-range sentence is long. Accept it, or split into
   "Watch for" plus "Also needs"?
