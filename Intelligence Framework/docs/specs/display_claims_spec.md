# Spec: display lines that make claims the code or the research doesn't support (inventory items 3–7), and a standing render-sweep test

**Status:** PROPOSED 2026-11-05. **Protected:** `decision_brief.py`,
`no_trade_filter.py`, `session_memory.py`, `regime_detection.py`. The wording
fixes need team review before they are built. The standing test
(`tests/test_display_claims.py`, free zone) ships **with** this spec, in the
same merge. Each claim that is false today is recorded in it as a known
failure until its fix lands.

**Owner (2026-11-05):** "Display claims (3–8) — actively misinforming you every
morning. Item 7 is worst: refuted research stated as fact. 'No statistical
edge' reads as a finding and isn't one. Ship the render-sweep test with this,
not after — it's what stops the list regrowing."

**Item 8** (the shadow block) waits on the retirement decision
(`fcs1_retirement_decision_v2_spec.md`). It is not in this spec.

## 1. Where the inventory came from

The code reviewer's round-2 render sweep (validation_log 2026-11-05, "TEAM
REVIEW round 2"):
- 653,184 cells, rendered through the real `_render_reason`,
  `_build_market_state`, `_build_invalidation` and `_build_narrative`;
- on states assembled around the real classifier, conflict, composite, weekly,
  `apply_filter` and `get_official_decision` functions.

I re-ran that grid while writing this spec, collecting every rendered phrase
that asserts an edge, a historical result or reliability. The results are in
§2.

**The full grid reproduces the reviewer's counts exactly:** the override
"transition" sentence is false in 2,304 of 3,672 cells, and "on all
timeframes" in 216,300 of 217,728. This was done through the test built with
this spec (§4), `-m display_sweep`, on `main` 4828ab2.

## 2. The claims, and what replaces them

Wording follows AGENTS.md rule 4 (plain English, no banned tokens). Every new
sentence must be true in every cell where it renders. §4 is the check.

### Item 7 (worst): research stated as fact

A rule the framework applies is not a finding. Where a study exists, its
result is the opposite of the claim, or it was never tested at honest N.

| # | Today (rendered) | Where | What the record actually says | New wording |
|---|---|---|---|---|
| 7a | "daily chart in transition zone (trend strength x/100) — **no statistical edge**" | REASON: `decision_brief.py:726-730`, `no_trade_filter.py:286-288` | R1 demoted to INFORMED PRIOR (overlapping windows). R4: no ADX band reached N ≥ 15. R12 inconclusive. Untested, not "no edge" | "Daily chart trend strength is x/100, in the middle band (18 to 25). The framework stands aside here by rule; the rule has not been tested." |
| 7b | "pre-intervention coil, **both signals historically fail here**" | REASON `decision_brief.py:657-659`; the same claim in `regime_detection.py:1046` (`atr_compression_note`) | R3: descriptive, 11 events. R6: "compression precedes large moves" REFUTED | "GBP/JPY volatility is unusually low (x times its normal level, under 0.8). The framework stands aside here by rule; the rule has not been tested." |
| 7c | "Volatility is compressed below its normal level, which **historically precedes a fake move**, so the framework waits." | FULL PICTURE `decision_brief.py:1214-1216` | R7: "fakeout-then-go" REFUTED, backwards on both pairs | "Volatility is unusually low, and the framework stands aside on that by rule. The idea that quiet markets come before fake or big moves was tested and not supported." |
| 7d | "volatility too high **for reliable signals**" (≥ 2×) | REASON `decision_brief.py:661-663` | No study of reliability above 2×. It is a hard stand-aside rule (N6) | "Volatility is over twice its 20-day average. The framework never trades above that level (a rule, not a measured result)." |
| 7e | "too high **for a reliable read**" | FULL PICTURE `decision_brief.py:1217-1219` | Same as 7d | "Volatility is over twice its normal level, and the framework never trades above that." |
| 7f | "structural disagreement, **no edge**" / "point in opposite directions. **No edge**; standing aside." | REASON `decision_brief.py:671-672`, `no_trade_filter.py:230` | A design rule (decision_logic_spec D3), never measured | "The daily and 4-hour charts are trending in opposite directions, and the framework stands aside when they disagree." |
| 7g | "**no clean directional edge**" | REASON `decision_brief.py:675-676` | Same | "The timeframes disagree (…), and the framework stands aside when they do." |
| 7h | "Both timeframes VOLATILE — **no edge** on either TF" | `no_trade_filter.py:261` | Same | "Both the daily and 4-hour charts are unsettled, and the framework stands aside." |
| 7i | SESSION "stable in transition zone — **no edge yet**" | `session_memory.py:226-227` | Same as 7a | "Daily strength steady at x, in the middle band where the framework stands aside" |
| 7j | SESSION "approaching **pre-intervention coil** zone" / "**BoJ risk elevated**" | `session_memory.py:280-285` | R3 descriptive only. No study links low volatility to Bank of Japan risk | See item 5 |
| 7k | "The market is in an exhaustion move — **fade**, don't follow." | REASON `no_trade_filter.py:217` | Advises a trade the framework never takes (`RANGE_TRADING_ENABLED` is False). Flagged in `watch_for_truth_v2_spec.md` §2.2 | "The market is in an exhaustion move: a violent one-way run. The framework doesn't follow it, and doesn't trade against it either. Standing aside." |

Code comments and module docstrings that say "no edge" (for example
`regime_detection.py:9, 707`) are not rendered and are out of scope.

### Item 3: the override REASON says "transition" when the daily chart is spiking

- **Today** (`decision_brief.py:748-751`): "Counter-trend override: D1
  transition but H4 {h4} (ADX n) aligns with {weekly}. Reduced size —
  unvalidated condition."
- **Problem.** The override fires on any VOLATILE daily: the 18–25 band, or a
  volatility spike under 32. The inventory found "transition" false in 2,304
  of 3,672 override cells (63%).
- **New:** "Counter-trend override: the daily chart has no confirmed trend
  ({cause}), but the 4-hour chart is trending {up/down} and agrees with the
  weekly trend. Reduced size (0.35x). Unvalidated: {`_OVERRIDE_RECORD`}."
  - `{cause}` is "trend strength x/100, in the middle band" for
    `TRANSITION_ZONE`, and "volatility x times its normal level" for a spike.
  - `_OVERRIDE_RECORD` is the single cited constant from
    `watch_for_truth_v2_spec.md` §2.4: "one recorded use, May 2026, before this
    framework's records and under earlier rules: lost". Whichever spec merges
    first defines it, and its tripwire test covers both uses.

### Item 4: "strong uptrend on all timeframes" is a weekly label

- **Today.** `_plain` maps `ESTABLISHED_UPTREND` to "strong uptrend on all
  timeframes" (`decision_brief.py:227-228`). It renders in MARKET STATE
  ("Weekly: …") and FULL PICTURE ("The weekly chart shows …").
- **Problem.** The label comes from the weekly chart only
  (`regime_detection._compute_weekly_context`):
  - `ESTABLISHED_UPTREND` = 20-week up and 4-week up;
  - `ESTABLISHED_DOWNTREND` = 20-week down and 4-week down **or flat**.
  - The inventory found it false in 216,300 of 217,728 cells. My subset
    rendered "Weekly: strong downtrend on all timeframes | Daily chart: in a
    strong uptrend".
- **New mapping:**
  - `ESTABLISHED_UPTREND` → "an uptrend (20-week and 4-week both up)";
  - `ESTABLISHED_DOWNTREND` → "a downtrend (20-week down, 4-week down or flat)".
  - Both surfaces must read grammatically: "Weekly: an uptrend (…)", "The
    weekly chart shows an uptrend (…)".
- **Out of scope, raised for the team.** The classification is asymmetric:
  20-week up with a flat 4-week is `PULLBACK_IN_UPTREND`, but 20-week down
  with a flat 4-week is `ESTABLISHED_DOWNTREND`. That is a decision input
  (`no_trade_filter.py:400-405` alignment sets), not display.

### Item 5: SESSION notes (`session_memory.py`)

| # | Today | Problem | New |
|---|---|---|---|
| 5a | "Daily strength stable and trending (x)" | `_adx_note` sees only the number. Trend strength ≥ 25 is not a trend on exhaustion or unconfirmed days | "Daily strength steady at x, in the trending band" |
| 5b | "just crossed the trend threshold (25 → 25)" | Whole-number rounding: 24.6 → 25.2 prints "25 → 25" | One decimal, rounded down (the numbers rule of `watch_for_truth_v2_spec.md` §2.6): "(24.6 → 25.2)" |
| 5c | "Volatility entered compression zone … BoJ risk elevated" | Unreachable: the preceding "compressing" branch catches every downward crossing first. The BoJ claim is unsupported (7j) | Check the crossing first: "Volatility dropped below GBP/JPY's quiet-market level (0.82x → 0.78x), where the framework stands aside" |
| 5d | "Volatility compressing … approaching pre-intervention coil zone" | Renders only when already **below** the level, so "approaching" is false | "Volatility still contracting (a → b), below the quiet-market level" |

"Conditions unchanged" ignores price. That belongs to `session_compare_v2_spec.md`
§2.4 and is not changed here.

### Item 6: the spike REASON says trend strength cannot rescue it, but the override trades spikes

- **Today** (`decision_brief.py:685-690`): "ATR spike (x the 20-day average,
  threshold m) — volatility too high for reliable signals regardless of trend
  strength."
- **New:** "Daily volatility has spiked (x times its 20-day average, above the
  m level). On a spiking daily chart the framework trades only through the
  reduced-size counter-trend override, and its conditions aren't all met here."
- **The test pins** that the override does not fire in any cell where this
  sentence renders. If another block applies (news, grade, data), an earlier
  branch renders instead (`decision_brief.py:650-654`), and the test checks
  that too.

## 3. Out of scope

- Decision, filter and classifier logic. Every allow, stand-aside, size and
  grade must stay byte-identical. The sweep checks this cell by cell against
  `main`.
- WATCH FOR and FULL PICTURE's "This changes when", which belong to
  `watch_for_truth_v2_spec.md`.
- Item 8, the shadow block.
- "Conditions unchanged", which belongs to `session_compare_v2_spec.md`.
- Entry/target text, the US DATA line, the news note, `entry_confirmation`
  wording and the pre-trade check. These were not inventoried, and none was
  added to the test's registry yet (§4.6).

## 4. The standing render-sweep test (`tests/test_display_claims.py`)

### 4.1 States

- **The builder.** States are assembled around the real classifier
  (`_classify_ex`), `_detect_conflict`, `get_composite_regime`,
  `_compute_weekly_context`, `apply_filter` and `get_official_decision`. This
  is the reviewers' builder.
- **Parity pin.** It mirrors `get_regime`'s input assembly, so a parity test
  drives the real `get_regime` on synthetic bar walks. Its feeds are patched,
  and `_classify_ex` is recorded to capture each run's inputs. The test then
  asserts the builder reproduces `get_regime`'s output fields that the
  renderers read:
  - `regime_d1/h4` and their subtypes;
  - conflict and conflict type;
  - execution mode and size;
  - `stand_down` and its reason;
  - `atr_compression` and `adx_exhaustion`.
- **When the builder is extracted.** When `watch_for_truth_v2_spec.md` §5
  extracts the real input builder from `get_regime`, the test switches to it
  and the parity pin retires.

### 4.2 Surfaces

- **Per cell:** REASON, MARKET STATE, EXIT IF / WATCH FOR and THE FULL PICTURE.
- **SESSION notes:** `_adx_note` and `_atr_note` are pure functions. They get
  their own grid of (now, prior, trend) values around every threshold.

### 4.3 The claim registry

Each display claim is one entry:
- **id** and source (the inventory item or this spec);
- **trigger:** the rendered phrase or pattern;
- **truth predicate:** a function of the state, plus the whole grid where the
  claim is about other cells, as in 6;
- **baseline:** its false-cell count on today's code.

| Claim | Trigger | True when |
|---|---|---|
| 3 | override REASON says "transition" | daily subtype is `TRANSITION_ZONE` |
| 4 | "on all timeframes" anywhere | weekly, daily and 4-hour all trend that way |
| 5a | SESSION "stable and trending" | never: `_adx_note` cannot see the regime, and the grid has cells with strength ≥ 25 and no daily trend |
| 5b | crossing note | its two printed numbers differ and sit on opposite sides of the threshold |
| 5c | a downward crossing of 0.8 | renders "dropped below" or "entered" |
| 5d | SESSION "approaching" | the value is still above the level |
| 6 | spike REASON "regardless of trend strength" | no spike cell in the grid trades through the override. It is a universal claim, so every rendering is false while any does. The new wording (§2 item 6) is local, and its fix registers a per-cell predicate: the override did not fire in this cell |
| P9, P10 (inventory 9, true today) | FULL PICTURE "All three timeframes line up" / "pieces don't line up" | the alignment they assert |

### 4.4 The claim-word class (item 7's guard against regrowth)

- **The check.** A pattern of claim words runs over every rendered surface and
  every SESSION note:
  - "historically";
  - "statistical";
  - `\bno (clean |directional |clean directional )?edge\b`;
  - "reliable";
  - "BoJ";
  - "coil";
  - "typically";
  - "strongest";
  - "fade".
- **Every match must be registered** with a citation to a finding whose status
  supports it. An unregistered match fails the suite, naming the phrase and
  the cell.
- **Today's matches** (7a–7k) are registered as known false, with their
  findings (R1, R3, R4, R6, R7, R12).
- **Out of scope by construction:** "edge" in "range edges" (fade-from-edge
  wording), because of the word boundary on "no … edge".

### 4.5 How known-false claims behave

For each claim with a baseline above zero:
- **A strict xfail test,** `xfail(strict=True, raises=AssertionError)`,
  asserts zero false cells. It shows as an expected failure on every run.
- **When the fix lands,** the test passes and strict xfail turns that into a
  failure. The fix's build must then remove the marker and set the baseline to
  0.
- **A separate non-xfail test** asserts each false count is **≤ its baseline**:
  a known-false claim cannot spread.
- **Every claim's trigger must fire at least once in the grid** (non-xfail).
  Otherwise the claim is vacuous: a reworded trigger that no longer matches
  fails here instead of passing silently.

### 4.6 Tiers, and making re-runs a habit (owner method note)

| Tier | What | Runtime |
|---|---|---|
| Default (every suite run) | A fixed-seed sample of 20,000 cells drawn from the full grid (seed 20261105), plus the SESSION grid. The grid's axis values are themselves the threshold edges | 4.0 s measured |
| Full (`-m display_sweep`, deselected like `integration`) | The whole grid: 653,184 cells | 1 min 53 s measured |

**Re-runs on display changes (proposed; not built: team question 2).**
`tests/display_sweep_stamp.json` would record the
sha256 of every display-bearing file at the last full sweep:
- `decision_brief.py`, `no_trade_filter.py`, `session_memory.py`,
  `regime_detection.py`;
- the claim registry.

The default suite fails when they differ, with the message "display code
changed since the last full sweep: run `scripts/display_sweep.py`".

- **The script** runs the full tier and, only if it passes, rewrites the stamp.
  It is the one writer. Tests never write project files: the `conftest`
  guard.
- **Each run's counts go in the change's validation_log entry.**
- **Team choice.** This stamp makes the re-run mandatory. The alternative is a
  standing rule, which the framework's own history says decays.

**New display claims.** Any new display branch adds its claims to the
registry in the same change. The claim-word check catches the commonest
regrowth (research stated as fact) even when nobody remembers to.

### 4.7 Mutation tests for the test itself (run 2026-11-05, 7 of 7 caught)

Each mutant was applied in the worktree with `PYTHONDONTWRITEBYTECODE=1`.
Each was confirmed applied (`git diff --numstat`), then reverted and confirmed
byte-identical. After the last revert, with caches cleared, the result was 15
passed and 16 xfailed.

| Mutant | Caught by |
|---|---|
| M1: the spike REASON says "historically unreliable" | `test_no_unregistered_claim_word` |
| M2: the override sentence removed | the claim-3 non-vacuity test, plus strict XPASS |
| M2b: "pulling back inside an uptrend" mapped to "strong uptrend on all timeframes" | `test_known_false_claims_do_not_spread` |
| M3: builder drops the filter fields | 7 failures, including the parity pin's official-decision check |
| M3b: builder drops the compression input | 3 failures |
| M4: "regardless of trend strength" reworded | claim-6 non-vacuity, plus strict XPASS |
| M5: 5d fixed in place | strict XPASS, plus non-vacuity |

**M3 is not hypothetical.** My first draft of the builder omitted the filter
fields, so no cell ever traded. The non-vacuity tests (claims 3 and P10 fired
0 times) exposed it before the parity pin was written.

## 5. Build of the fixes (after review)

**Order** (agreed with `watch_for_truth_v2_spec.md` §3):
1. WATCH FOR v2;
2. `session_compare_v2`;
3. this spec.

This spec rebases on WATCH FOR v2's numbers rule and `_OVERRIDE_RECORD`.

**Gates:**
- **Gate 1:** the registry's xfails flip to passes and their baselines go to 0.
  The banned-token floor and the stand-down matrix are untouched. Decisions
  are byte-identical over the full sweep against `main`.
- **Gate 2:** a real brief through `scripts/reality_run.py --code <worktree> brief`,
  showing the new sentences where the market state produces them.
- **Rule 12:** no notification text changes, except where a notification
  quotes a REASON. `scheduled_brief.sh` builds DECISION summaries from REASON
  lines. The build's replay of real day-log runs (main vs branch, stub
  notifiers) must show only the reworded REASON text changing, never whether
  a notification fires.

## 6. Questions for the team

1. Approve the wording in §2 cell by cell, or amend it.
2. Make the sweep stamp (§4.6) mandatory, or keep it a standing rule?
3. The weekly classification asymmetry (item 4): open a decision-logic spec?
4. 7k drops "fade". Confirm the framework should say it doesn't trade against
   exhaustion moves, which is true while `RANGE_TRADING_ENABLED` is False and
   EXHAUSTION is not a first-class regime.
