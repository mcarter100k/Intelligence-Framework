# SPEC: trade_logger repair (team approved 2026-07-31, amended same day)

> Review record. Original spec + the approved amendment + the Gate-2
> requirement, per AGENTS.md: protected-path specs become repo artifacts first.

## Original spec

trade_logger.py imports trade_receiver (deleted 0e4af6e) — broken
since the first cleanup. Repair, don't retire:
- Strip all trade_receiver/MT5 remnants; pure manual CLI journal
- Keep existing trade_log.csv schema, ADD stack_id column
  (links to pre_trade_journal.csv rows from setup_check)
- Prompt flow: instrument, direction, entry, stop, target, size,
  optional stack_id (offer the most recent matching stack for
  this instrument+direction as the default), one-line rationale
- Plain-English prompts, ledger rules (append-only, gitignored
  already per hygiene pass)
- Tests: full log flow mocked, stack_id linkage, schema pinned
Spec-first, feature branch, suite green, run report.

## AMENDMENT (approved "AMENDED, PROCEED", 2026-07-31)

Premise inspection found `trade_log.csv` is an orphaned April-era
framework-snapshot log (bias/vix/fuel columns — no trade fields); adding a
column would also rewrite an evidence file, which ledger rules forbid.
Resolution:

- `trade_log.csv` stays untouched as historical evidence.
- The repaired tool writes a NEW gitignored, append-only ledger:
  **`trades.csv`**, using the **two-row convention** — an OPEN row at entry
  time and a CLOSE row at exit time, linked by position_id. Rows are only
  ever appended; closing a trade never edits its OPEN row. Open positions =
  OPEN rows with no matching CLOSE row (derived, no pending-state file).
- Schema (single header, pinned):
  row_type, position_id, timestamp_utc, instrument, direction, open_price,
  stop, target, close_price, size, pips, outcome, balance_open,
  balance_close, return_pct, stack_id, rationale
- Pip math instrument-correct (GBP/JPY 0.01 pip), via trade_management.

## Gate-2 requirement (Two-Gate Verification Standard)

Gate 2 must be REAL END-TO-END USE, not a mocked flow: after building, run
the live brief, then log a real OPEN row on a genuine current market
observation (real instrument, real live prices for entry/stop/target, size
0.0 marked PAPER in rationale), then a real CLOSE row against the actual
market price at close time. Show both rows verbatim in the run report. The
mocked-flow tests remain as Gate 1.
