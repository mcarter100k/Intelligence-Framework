# legacy_validators/ — QUARANTINED

**INVALIDATED 2026-06-29 — overlapping-window serial correlation.**

The validators in this directory (`validate_adx_threshold.py`,
`validate_atr_threshold.py`) used **overlapping** forward windows (step = 1 bar),
which inflated the effective sample size by roughly **20×** through serial
correlation. Every "VALIDATED" finding they produced was demoted to **INFORMED
PRIOR** on 2026-06-29 (see `validation_log.md`, Audit Item 2).

## Do NOT cite their output.

Their win-rate magnitudes are statistical artifacts, not evidence. They are kept
here only for **methodology history** — to document the mistake and why it was
made — not for reuse.

## Use instead:

    validate_thresholds_v2.py

which uses **non-overlapping** 20-bar forward windows, structure-based direction
(P2 pivots, not the 10-bar slope), spread-adjusted outcomes, and reports the
**honest** sample size. At honest N, no ADX band reaches the N≥15 minimum on
daily data — which is itself the finding: daily sampling is too sparse to
validate these thresholds. Real evidence now accrues via `run_outcome_check.py`
(the live outcome loop), not one-shot backtests.

**Standing rule:** every backtest reports non-overlapping N alongside nominal N,
or it does not get a VALIDATED label.
