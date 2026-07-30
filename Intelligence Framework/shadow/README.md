# shadow/ — QUARANTINED signal stack

**QUARANTINED 2026-07-29.**

This directory holds the legacy signal-stack (`market_brain`, `decision_engine`
and the ~16 signal/support modules only they import) plus `notify.py` — the old
alert path the automation layer replaced.

## Why it was quarantined

Its entire justification was the official-vs-shadow comparison. That comparison
was wired into `build_market_report`, and **`build_market_report` was never
scheduled** — its only production caller was `notify.py`, which the automation
layer (`scheduled_brief.sh → decision_brief.py`) replaced. Result: the
comparison logged **0 rows**. It was not accumulating slowly — it was
*structurally incapable* of accumulating, because it triggered only on official
tradeable signals via an unscheduled caller.

It was **superseded** by `shadow_signals.py` (which stays in the live tree):
that harness triggers on its own frozen conditions and is already collecting.

## REACTIVATION CONDITION

Promote a module back to the live tree **only** with a concrete evidence path:
i.e. wire `build_market_report` into a *scheduled* run FIRST and show the
comparison actually accumulates rows. **Do not cite these modules' priors
(the 36 signal weights, the regime-weight table, etc.) as evidence** — they have
none.

## Notes

- `session_guard.py` (the circuit breaker) and `risk_config.py` live here. The
  parked circuit-breaker item (2.2) therefore depends on promotion — the breaker
  currently protects nothing in the live path.
- Tests for these modules live here too; they are not part of the live green bar.
- Nothing in `shadow/` is imported by any live-core module (verified).
