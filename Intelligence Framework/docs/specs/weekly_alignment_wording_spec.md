# Spec: plain wording for the 20-week alignment block (Phase 5 review 2, item R2b; 2026-09-30)

Status: committed before any build commit on `fix/weekly-alignment-wording`.
The owner directed the fix on 2026-09-30 ("fix the 10 more problems from the
2nd code review"; R2b was the one left open). Protected file touched:
`no_trade_filter.py`. Wording only: no decision changes.

## Defect (reproduced on main f2b27a6)
- The filter's reason carries raw labels, and after the brief's `_plain`
  translation it reads awkwardly:
  - raw: `Short blocked: dominant 20-week trend is UPTREND. Counter-trend short
    requires COUNTER_TREND_BOUNCE weekly context (current: ESTABLISHED_UPTREND).`
  - shown: `… Counter-trend short requires bouncing against the main trend
    weekly context (current: strong uptrend on all timeframes).`
- The rendered text has no raw tokens (checked), so this is a readability fix.
  Ledgers keep machine labels by design.

## Change
- Second sentence becomes: `A counter-trend short is allowed only when the
  weekly context is COUNTER_TREND_BOUNCE (now: <ctx>).` The long case is the
  same with `PULLBACK_IN_UPTREND`.
- Shown: `… is allowed only when the weekly context is bouncing against the
  main trend (now: strong uptrend on all timeframes).`
- The first sentence is unchanged; it is pinned by test_data_at_source.

## Verification
- Before/after: the same script renders the shown REASON on main and on the
  branch.
- Tests pin the shown wording for both directions, with no raw tokens.
- A mutant restoring the old wording must fail.
- Full suite; `/code-review`.

## Addendum (2026-09-30): design correction from `/code-review` (supersedes "Change" above)

**The review found the gate's exceptions unreachable, so the planned rewording was wrong.**
- The first build reworded the exception ("allowed only when … bouncing
  against the main trend"). `/code-review` showed that sentence promised
  something the gate can never do.
- `_compute_weekly_context` emits COUNTER_TREND_BOUNCE only when
  lt=DOWNTREND, and PULLBACK_IN_UPTREND only when lt=UPTREND. The short
  exception (lt=UPTREND and COUNTER_TREND_BOUNCE) and the long exception
  (lt=DOWNTREND and PULLBACK_IN_UPTREND) can never fire.
- This is proven over all 9 lt × st combinations with the real classifier,
  each one realized (`test_the_former_exceptions_are_unreachable`). It has
  been true since d661d81 (2026-06-28).

**Change, as built:**
- The dead exceptions are removed.
- The reason states the real rule: `Short blocked: dominant 20-week trend is
  up — the framework does not trade against it.` (long: "down").
- The block is coded `weekly_alignment`, so the brief shows it verbatim.
- `decision_brief._render_reason` is the one REASON pipeline, and the tests
  that had hand-built copies now use it.

**No decision the classifier can produce changes:**
- Grid of 6,912 reachable cells, main vs branch: 0 differences, including
  the 864 cells the gate blocks.
- History replay, 825 days × 2 pairs: 0 decision differences.
- A hand-built dict with an impossible pairing used to be allowed and is now
  blocked. That is the stricter direction, and it is pinned by
  `test_apply_filter_has_no_counter_trend_exception`.

**Open owner decision (not made here):** whether the framework should have a
counter-trend exception at all. It has never been active.
