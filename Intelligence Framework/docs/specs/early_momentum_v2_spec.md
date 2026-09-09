# Spec: EARLY_MOMENTUM_v2 (Branch 2 of the 2026-09-09 post-audit directive)

**Status:** team-directed 2026-09-09. Changes what fires (a candidate spec
change) — PROTECTED path, SPEC FREEZE rules apply.
**Branch:** `feat/early-momentum-v2` (stacked on `feat/honesty-repairs`,
which defines the invalid_spec guard this candidate exists to make
unnecessary). Merge held for team review.

## Why v1 is retired

First grading (2026-09-08, validation_log entry 2026-09-09): v1 computes the
SHORT stop from `latest_sh` (the last confirmed swing high). When price has
rallied **above** that stale swing while D1 structure still reads DOWNTREND,
the stop lands on the non-adverse side of entry. Rows 2–3 of the July episode
fired that way: guaranteed −1.0R at entry (the grader's hit test is trivially
true), while price ran 877.7 / 899.7 pips in the signal's favor —
unscoreable by construction. A candidate that can emit rows no grading can
score cannot accumulate evidence. **EARLY_MOMENTUM (v1) is RETIRED
2026-09-09.** Its ledger rows are preserved untouched; the one valid row
(Episode 1, −1.0R) remains counted evidence for v1's record.

## v2 definition — identical trigger + one guard

Everything below is byte-identical to v1 except the guard and the id:

- Instrument: GBP/JPY only.
- Trigger: `EM_ADX_LO (18.0) <= adx < EM_ADX_HI (25.0)`, D1 structure
  UPTREND → LONG / DOWNTREND → SHORT, entry = last complete H4 close.
- Stop: the last confirmed swing (LONG: `latest_sl`; SHORT: `latest_sh`);
  when no swing exists, the v1 fallback of entry ∓ 1.5×ATR (always
  adverse-side) is unchanged.
- **GUARD (the only change):** when the swing exists but sits on the
  non-adverse side of entry (SHORT: swing <= entry; LONG: swing >= entry),
  there is no valid stop — **NO FIRE**. No fallback substitution: a market
  where structure says DOWNTREND while price trades beyond the last swing
  high is exactly the ambiguous state v1 mis-scored; v2 stands aside there.
- Candidate id: `EARLY_MOMENTUM_v2`. Fresh evidence line: tallies, episodes
  and review gates (FLAG N=30 / DECISION N=60) count v2 rows only, from
  zero. v1 rows are never migrated.

Frozen as of 2026-09-09. Any further change starts EARLY_MOMENTUM_v3.

## Touched files

- `shadow_signals.py` — the candidate function (v2 id + guard), frozen-spec
  header note, `_CANDIDATES` entry. Grading, logging, tally, and the other
  two candidates untouched.
- `scripts/scheduled_outcome_check.sh` — notification tally names v2
  alongside the retired v1 (v1's graded row remains honest history).
- `test_shadow_signals.py` — v1 trigger pins carried over to v2 verbatim,
  plus guard pins (wrong-side swing = silent, both directions; no-swing
  fallback still fires).

## Gates

- **Gate 1:** pinned tests — identical-trigger values fire under the v2 id;
  wrong-side swing is silent in both directions; missing swing keeps the ATR
  fallback; the July row-2/3 geometry (entry above stale swing high,
  DOWNTREND) produces NO row.
- **Gate 2 (REALITY):** live evaluation on real OANDA H4 context for both
  pairs with the actual ctx values (adx, structure, swing vs entry) and the
  fire/no-fire decision shown; live brief run confirming the shadow section
  renders (or stays silent) coherently.
