# Spec: fix the decision logic (Phase 5 of the 2026-09-29 audit plan)

Status: this spec is committed before any build commit on
`feat/phase5-decision-logic`. The owner directed Phase 5 and made four
decisions (2026-09-30, recorded below).

Merge is HELD until two things happen:
- the Phase 2/3/4 Gate-3 checks (the 02:30 brief and the 15:15 grader) pass;
- the owner approves the branch and the ledger migration.

Protected files touched: `regime_detection.py`, `no_trade_filter.py`,
`official_decision.py`, `news_gate.py`, `entry_confirmation.py`,
`regime_classifier_logger.py`, `trade_outcome_logger.py`,
`session_memory.py`. **Floor tests are changed, with the owner's
authorization** (see below).

## Owner decisions (2026-09-30)
1. **Floor tests:** changing them to pin the corrected behavior is authorized.
2. **H4 exhaustion:** STAND ASIDE, with no trade, until EXHAUSTION is a
   first-class validated regime (this matches the existing AGENTS.md
   precondition).
3. **ADX ≥ 32:** requires confirmed structure, the same rule as the 25–32
   band. There are no slope-only trend calls.
4. **Grade C:** NO TRADE. `risk_config` (0% risk) wins over the brief's
   "75% size".

The owner did not object to these stated defaults:
- the news gate judges coverage and keeps a 30-minute post-release buffer
  (`risk_config` event lockout after = 0.5h);
- missing level data means NOT READY;
- `apply_filter` is the single stand-down authority;
- a `logic_version` ledger column, with a controlled migration at merge.

## Defects

All were reproduced on `main` (6471072) with `scratchpad/p5/measure.py`,
which runs the live pipeline order: conflict → composite → `apply_filter` →
official. Controls correct: ADX ≥ 32 with confirmed structure is still a
trend, and the news gate is up 60 minutes before a release.

| # | Defect | Observed on main |
|---|---|---|
| D1 | GBP/JPY H4 exhaustion (`RANGING`/`EXHAUSTION`) is read as a pullback | filter PULLBACK_ENTRY → **LONG, conviction 70, grade A**, size 0.75 |
| D2 | ADX ≥ 32 calls a trend from slope alone | ADX 33 with TRANSITIONAL structure → TRENDING_DOWN → SHORT B+ at full size. T10/T11/T15 pinned this |
| D3 | The opposite-trend conflict hard block can never fire | The code emits `D1_BULLISH_H4_BEARISH`; the filter checks `TRENDING_UP__TRENDING_DOWN`. The stand-down floor test feeds the phantom token |
| D4 | `apply_filter` is not the single authority | RANGING/RANGING and RANGING/TRENDING_* are allowed by the filter and then vetoed by official. The ledgers record `filter_allowed=True` on a stand-aside brief |
| D5a | The news gate reports "all clear" when the calendar does not cover today | A calendar whose newest event is last week gives `active=True, gating=False, note=''` |
| D5b | The news gate drops at t=0 | 5 minutes after a release: `gating=False` |
| D6 | Missing level data loosens the entry trigger | `entry_ready=True` ("degraded trigger") on the pattern alone |
| D7 | Grade C is shown as a trade | The real 2026-09-25 GBP/JPY row reproduced: **SHORT, conviction 30, grade C, size 0.75** |

## Design

1. **One decision function, one authority.**
   - `official_decision.decide(regime)` produces direction, conviction,
     grade and reason from the filter's provisional outputs. That covers
     direction derivation, the counter-trend override, the range-trade
     candidate (disabled), the direction-NONE case, the conviction
     components and the **grade-C → NO TRADE** rule.
   - `apply_filter` runs its market-condition checks and then calls
     `decide` on its provisional result. **If `decide` would not trade, the
     filter returns `allowed=False` with that reason.**
   - `get_official_decision` returns NO TRADE when the filter blocked, and
     otherwise `decide`'s result.
   - The invariant, now testable over every cell: **`filter.allowed ⇔
     official direction ∈ {LONG, SHORT}`**. Everything that reads
     `filter_allowed` (session memory flips, the ledgers, alerts) therefore
     sees the final answer.
2. **D1:** `apply_filter` hard-blocks when `regime_h4_subtype` or
   `regime_d1_subtype` is `EXHAUSTION`, with the reason: "The market is in
   an exhaustion move — fade, don't follow. Standing aside."
3. **D2:** the ADX ≥ 32 slope-only early return is removed. ADX ≥ 32 falls
   through to the same structure-agreement rule as 25–32, so mixed
   structure gives `VOLATILE` / `UNCONFIRMED_TREND`. The GBP/JPY exhaustion
   branch is unchanged.
4. **D3:** the conflict block compares the D1 and H4 regimes directly (one
   TRENDING_UP and the other TRENDING_DOWN) instead of matching strings.
   The reason is in plain English: "Daily and 4-hour trends point in
   opposite directions — no edge."
5. **D5:**
   - **Coverage:** a ForexFactory weekly calendar covers through the
     Saturday on or after its newest event. When today is past that date,
     the gate is INACTIVE with the note "calendar does not cover today", so
     it never claims an all-clear it cannot see.
   - **Buffer:** events from −30 minutes to +120 minutes gate. After a
     release the reason reads "released N minutes ago".
6. **D6:** unavailable level data gives `m15_trigger=False`,
   `entry_ready=False`, and the basis "level data unavailable — cannot
   confirm the entry at a key level; not ready".
7. **The evidence boundary.**
   - A `logic_version` column (`p5-2026-09-30`, from
     `official_decision.LOGIC_VERSION`) is added to
     `regime_classification_log.csv`, `trade_signal_log.csv` and
     `session_context_log.csv`.
   - Rows logged under the old decision rules stay blank, so they are
     separable in Phase 6/7.
   - The live ledgers get a **controlled migration at merge, with owner
     approval**: a verified backup, then `migrate_header`, then a
     field-by-field check that must show 0 differences.

## Floor tests changed (owner-authorized), old → new
- **T10/T11/T15** (`test_regime_detection_p1.py`): "ADX ≥ 32 → TRENDING
  regardless of structure" becomes "ADX ≥ 32 → TRENDING only with agreeing
  structure; otherwise VOLATILE".
- **The stand-down matrix conflict row:** the phantom `TRENDING_UP__TRENDING_DOWN`
  input becomes the emitted conflict type, with the expected reason the
  named hard block.
- **Any matrix row whose allowed/blocked expectation changes because of the
  single-authority or grade-C rule** is listed in the addendum, with its
  old and new expectation and the rule that changed it. None is silently
  edited.

## Verification (evidence-validation standard, AGENTS.md rule 11)
- **Gate 1.**
  - `measure.py` on the branch: all 8 defects fixed, with the controls
    unchanged.
  - Invariant sweep: `filter.allowed ⇔ official trades` over the full
    regime × structure × ADX grid.
  - The banned-token floor (plain English).
  - The new tests must fail on main.
  - Mutations, with caches cleared and a re-run after each revert.
  - `/code-review`, with every finding reproduced.
- **Gate 2.**
  - `reality_run` brief and grader against the live ledgers: new rows carry
    `logic_version`, and the project is UNCHANGED.
  - The real wrappers run end to end on a copy.
  - The audit-hook probe.
- **Gate 3 (PENDING):** the first scheduled briefs under the new logic.
  Record the actual decisions and compare them with what the old logic
  would have said on the same inputs.

## Addendum (2026-09-30): what the build changed beyond the plan, and `/code-review` findings

**Beyond the plan (found while building).**
- **The live filter call got only a subset of its inputs.** `get_regime` did
  not pass `adx`, `confidence`, `instrument`, the subtypes or
  `range_position` to `apply_filter`; they reached only the official path.
  One side effect: the filter's "trending band, structure unconfirmed"
  reason could never fire live (the ADX read as 0). All of these are passed
  now. The range bounds are computed before the call.
- **D2 applies to both timeframes.** `_classify_ex` is shared, so a slope-only
  4-hour trend at ADX ≥ 32 is now also VOLATILE. That accounts for the
  override and A+→B changes in the history replay, and for the one
  newly-permitted trade (below).
- **The direction-NONE reason was split.** "Range mid-zone…" is kept for
  FADE_EXTREMES. A daily chart with no trend under a trending 4-hour chart
  reads "The daily chart gives no trend direction to follow".
- **The D5 note text.** An uncovered calendar keeps the existing pinned note
  "news calendar stale — event risk unchecked". It is accurate (the file is
  stale for today), and the brief and setup_check already render it as
  "The news calendar is out of date or missing". The spec's "calendar does
  not cover today" wording was not adopted (review V10).
- **`minutes_until` is negative after a release.** Every renderer handles it:
  `news_gate.gate_reason` for the filter and the brief fallback;
  `_build_narrative`; `setup_check._minutes_phrase`.

**Findings.** Each was reproduced on the branch before fixing
(`scratchpad/p5/repro_review.py`), then re-measured fixed with the same
script. Each fix has a regression test (`test_decision_logic.py`, `v*`)
and a mutant that the test kills.

| # | Finding | Fix |
|---|---|---|
| V1 | The brief's "Cause 2" blamed exhaustion for an ADX ≥ 32 VOLATILE daily, which since D2 means unconfirmed structure | Cause 2 removed (GBP/JPY exhaustion classifies RANGING, never VOLATILE) |
| V2 | The filter's unconfirmed-structure reason was limited to 25 ≤ ADX < 32 | ADX ≥ 25. A confirmed structure against the slope now gets its own "disagrees" reason (filter and brief) |
| V3 | The brief's opposite-trend branch still matched the phantom tokens | Compares the regimes; named blocks show the filter's reason (V5) |
| V4 | The gate reported the most negative event, so a release 29 min ago hid one due in 2 | The nearest by distance either side; control: a release 5 min ago beats an event 90 min away |
| V5 | The brief re-narrated the new blocks (grade C, exhaustion) as a daily-chart cause | `FilterResult.block` (`exhaustion` / `conflict` / `decision`) → `regime["filter_block"]`; `_build_reason` shows the filter's reason for these. Verified end to end through `get_decision_brief` |
| V6 | The frozen shadow `news_window` stamp would silently gain the 30-min buffer | The gate reports `pre_release` (exactly the old definition); the stamp uses it |
| V7 | The loggers migrate a header on the next append, so a scheduled run after the merge would migrate the live ledgers before the controlled step | **Procedure** (merge preconditions below): the controlled migration runs immediately after the merge, outside every job window. The automatic migration is lossless (tested), but it takes no verified backup |
| V8 | Post-release wording was duplicated | One builder, `news_gate.gate_reason`, for the filter and the brief fallback. The narrative and setup_check keep their own established styles |
| V9 | A stale "never a decision input" comment; the duplicated exhaustion expression | The comment and AGENTS.md updated; `adx_exhaustion_note` reuses `_adx_exhaustion` |
| V10 | Spec note text | See "The D5 note text" above |

**The one newly-permitted trade (disclosed for the owner).**
- In the history replay (825 days × 2 pairs), exactly one day that main
  stood aside now trades: GBP/JPY 2026-01-26.
- H4 ADX was 32.4 with TRANSITIONAL H4 structure. Main called H4
  TRENDING_DOWN from slope alone, which manufactured a D1/H4
  "structural disagreement". Under D2 the H4 is VOLATILE, so D1 confirmed
  up with a weekly pullback-in-uptrend gives REDUCED_MOMENTUM LONG, B, 55.
- An H4 at ADX 31.9 with the same structure would already have traded on
  main. The rule is now the same on both sides of 32.
- Outcome: +262 pips at 5 D1 bars, −48 at 20. N=1, no evidence either way.

## Merge preconditions (owner)
1. The Phase 2/3/4 Gate-3 checks (the scheduled brief and the 15:15 grader)
   pass.
2. The owner approves this branch.
3. **The controlled ledger migration, run immediately after the merge**,
   outside every job window (not within 30 min of 02:30, 07:30, 15:15 or
   18:00 PDT):
   - a verified backup (sha256 manifest) of `regime_classification_log.csv`,
     `trade_signal_log.csv` and `session_context_log.csv`;
   - then each logger's own `migrate_header` (FIELDNAMES + `logic_version`);
   - then a field-by-field comparison against the backup that must show 0
     differences, with a planted-change positive control.
4. After the migration, the full suite on the live checkout, with the count
   recorded in AGENTS.md rule 2. The `test_ledger_headers` checks that skip in
   a worktree run there and must pass.
