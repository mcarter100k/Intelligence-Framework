# Spec: honest shadow tally (episode count on the bar index, R first) and a market-aware digest (2026-10-19)

**Status:** team review given 2026-10-19. Committed before the build.
`shadow_signals.py` is protected.

## Why: a display caused an analytic error

The brief printed "17 rows / 4 episodes, 16 graded, 5 wins, −79 avg pips"
for EARLY_MOMENTUM_v2. A reviewer turned −79 average pips into R using the
stop of the currently pending signal (83 pips), got −0.95R, and that figure
commissioned a doctrine change (the futility rule). The ledger's truth is 3
graded independent episodes at −0.55R, −0.39R and +0.34R: mean −0.20R. Two
display defects made the error possible:

- the episode count is inflated (4, not 3);
- the tally leads with net pips (a diagnostic) and omits R (the measure).

## 1. Episodes on the bar index (M34)

`episode_count` collapses fires using 120 clock hours. 30 H4 bars span
about 168 hours over a weekend, so it overcounts. It also counts ungraded
rows. AUDIT §2 #3 ruled both wrong.

New rule, the same as `foundation/tools/episodes.py` and the futility spec:
- **Rows that count:** graded, valid (not `is_invalid_spec`) and not
  excluded rows only.
- **Grouping:** per instrument, in time order.
- **When an episode starts:** a fire starts a new episode when it is 30 or
  more H4 bars after the current episode's first fire.
- **How bars are counted:** on the instrument's H4 bar index, built from
  the trading calendar. That is six bars per trading day from 17:00
  New York (`regime_detection.is_trading_day`). No network call.
- **Calendar validated against OANDA:** 0 differences over 5,239 GBP/AUD
  and 4,735 GBP/JPY real H4 bars (2023-04-30 → 2026-09-10, every DST
  change included), and 901/901 bars per pair for 2026-03-20 → 2026-10-16.
- **An episode's R** is the R of its first fire.

## 2. The tally reports R, not pips

Per candidate and pair, as the brief renders it:

```
      tally: 3 independent episodes from 16 graded rows (1 still open)
             per episode: avg -0.20R, median -0.39R, without the best one -0.47R
             diagnostic only: avg -79 pips at bar 30 over the graded rows
             (futility check at 20 episodes, flag at 30, review at 60)
```

- Average and median R are both shown (M8); "without the best one" follows
  M9 and appears from 2 episodes.
- Net pips stays, labelled as a diagnostic (M14).
- **The win count is dropped.** A win count means nothing without the
  breakeven rate, and these candidates exit at bar 30, not at a fixed
  target, so there is no single breakeven figure to show beside it.
  Expectancy (avg R) is the success measure.
- The heartbeat and the nightly grader's shadow summaries show the same
  episode count and average R.

## 3. The 7:30 digest says when the market is closed

Phase 0 gated the DECISION notification, not the DIGEST. On Sunday at 07:30
with the market closed it sent "GBP/AUD LONG". New behavior:
- When every pair's block carries the closed-market banner, the digest
  leads with "MARKET CLOSED until <next open> — no live calls", and lists
  each pair as "last read" rather than as a call.
- A closed pair never renders as a bare direction.
- An open market renders exactly as before.

`scripts/daily_digest.py` is free zone.

## Not changed

- Decisions, grading, the ledgers.
- The frozen candidate parameters (FLAG_N, REVIEW_N, HORIZON).
- `get_shadow_tally`'s existing keys, so its callers keep working.

## Verification

- **Gate 1:** each fix has tests that fail on the old code.
- **Two independent implementations:** the episode count is cross-checked
  against `foundation/tools/episodes.py` on the real ledger.
- **Gate 2 parity:** the real brief through `reality_run` on main's code and
  on the branch, back to back. Decision lines and ledger decision fields
  must be identical.
