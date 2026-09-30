# Spec: the regime-change message names the timeframe that changed (issue 4, 2026-09-30)

Status: committed before any build commit on `fix/regime-change-timeframe`.
The owner directed the fix on 2026-09-30 ("handle issue 2 and 4"). Protected
file touched: `session_memory.py`. Merge is HELD for owner approval.

## Defect (observed live, 2026-09-30 02:30 PDT brief, GBP/AUD)
- The session ledger rows: 01:15:59Z D1 `VOLATILE`, H4 `TRENDING_UP`, then
  09:30:07Z D1 `VOLATILE`, H4 `VOLATILE`. Only the 4-hour chart changed.
- The brief printed: `⚡ SESSION  Since 8h 14min ago: Regime changed (no
  clear direction → no clear direction). Re-evaluate.`
- Cause: `session_memory._build_summary` always prints
  `previous['regime_d1'] → current['regime_d1']`, while `regime_changed` is
  true when EITHER timeframe changed.
- The alert (`##ALERT## … the market regime changed`) was correct; only the
  message misnames the change.

## Change
- The message names each timeframe that changed, e.g.
  `Regime changed (4-hour chart: TRENDING_UP → VOLATILE). Re-evaluate.`
- Both changed: `(daily chart: A → B; 4-hour chart: C → D)`.
- Raw regime tokens stay in the summary. The brief already translates them
  to plain English (`_plain`), exactly as it did the old D1-only text.
- The `Regime changed` prefix is unchanged (the brief keys its ⚡ marker on it).
- No decision, alert or ledger change.

## Verification (evidence-validation standard, AGENTS.md rule 11)
- **BEFORE/AFTER:** the same script renders the session line from today's
  real two GBP/AUD rows, on main and on the branch.
- **Tests:** D1-only, H4-only and both; the rendered brief text for the real
  rows; the prefix is kept.
- The new tests fail on main. Mutations: each branch of the fix removed must
  fail a test.
- `/code-review`, with findings reproduced first.
- **Gate 2:** `reality_run brief` against the live ledgers (today's rows give
  a real delta).
- **Gate 3 (PENDING):** the first live brief after a single-timeframe change.
