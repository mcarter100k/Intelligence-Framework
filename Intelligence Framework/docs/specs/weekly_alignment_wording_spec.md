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
