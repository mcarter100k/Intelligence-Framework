# Spec: circuit-breaker promotion (Spec B of the 2026-09-09 post-audit directive)

**Status:** team-directed 2026-09-09, sequenced after Spec A.
**Branch:** `feat/circuit-breaker` (stacked on `feat/heartbeat`).
Merge held for team review.

## What moves

`git mv` (history preserved): `shadow/session_guard.py` → `session_guard.py`,
`shadow/risk_config.py` → `risk_config.py`, `shadow/test_session_guard.py` →
`test_session_guard.py` (into the live green bar). Both modules join the
PROTECTED list in AGENTS.md (16 → 18). The quarantined consumers
(`decision_engine`, `market_brain`, `notify`) keep resolving them by bare
name — `shadow/conftest.py` already puts the project root on `sys.path` —
and stay quarantined themselves.

## DECISION (from the directive): the adapter lives IN THE BREAKER

The audit proved the old guard fails closed against every live ledger (its
`{date, trade_taken, pnl_r}` schema exists nowhere). **Append-only ledgers
are never modified to fit a consumer.** `session_guard` is taught the
`trades.csv` two-row convention (docs/specs/trade_logger_repair_spec.md):

- **Trade counting:** positions whose OPEN row's `timestamp_utc` falls on
  the current **UTC day** (the ledger is UTC; the day boundary is
  documented, not guessed). An OPEN without a CLOSE still counts toward the
  session — an open position is exposure.
- **Per-day realized R** (the directive's unit), derived from CLOSE rows of
  the UTC day, price-based so it needs no balance bookkeeping:
  `R = sign · (close_price − open_price) / |open_price − stop|` (sign per
  direction). A CLOSE row with no parseable stop contributes its trade to
  the count but no R (same rule as the old guard's unreadable single value).
- **Drawdown** is the peak-to-trough of the running realized-R curve in file
  order (same shape as the old %-curve logic).
- **Limits:**
  - `MAX_TRADES_PER_SESSION = 2` (unchanged) → SESSION_CLOSED.
  - `MAX_DAILY_LOSS_R = 2.0` (NEW, R-denominated — two full-risk losses)
    → HALTED.
  - `MAX_DAILY_LOSS_PCT = 2.0` (kept): additionally enforced on the
    peak-to-trough of `return_pct` whenever today's CLOSE rows carry it —
    the stricter of the two loss checks wins. Where `return_pct` is empty
    (as in the existing PAPER rows) the R limit alone governs.
- **Fail-closed** unchanged in spirit: file exists but header lacks the
  required columns (`row_type, position_id, timestamp_utc, instrument,
  direction, open_price, stop, close_price`), or is unparseable → HALTED.
  Absent/empty file → ACTIVE (start of day). PAPER rows (rationale marked
  PAPER) still count — a paper session that would have halted a real one is
  information the trader wants.

## Standing rule (directive): shared currency leg = ONE position

Positions opened the same UTC day that share a currency leg (GBP_AUD +
GBP_JPY share GBP) count as ONE position against `MAX_TRADES_PER_SESSION` —
correlated exposure is one bet, not two. Counting is by connected
components over shared legs (A+B, B+C ⇒ one component). The helper lives in
`session_guard` (`count_leg_grouped_positions`) to avoid an import cycle;
`risk_config` documents and re-exports it as the standing rule
(`RISK_RULES["shared_leg_counts_as_one"] = True`). R/percent loss curves
still count every close individually — the grouping applies to position
COUNT, not to realized losses.

## Interface (unchanged shape)

`get_session_status(journal_path, account_balance) -> dict` with the same
keys (`status`, `reason`, `trades_today`, `realized_loss_pct`,
`remaining_capacity`) plus `realized_loss_r`; `can_trade(...) -> bool`;
`STATUS_*` constants. `DEFAULT_JOURNAL = "trades.csv"`. `reason` strings
stay plain-English (banned-token rules apply to anything a trader reads).

## Tests

- The 8 behavioral pins move with the file and are rewritten to two-row
  fixtures, preserving each behavior: absent→ACTIVE, corrupt→HALTED,
  empty→ACTIVE, small loss active, drawdown trips on peak-to-trough even
  when net is small, max trades close, wins never halt, only today counts.
- New pins: R-from-prices arithmetic, open-position counting,
  leg-grouping (shares → one; disjoint → two; chain → one),
  `return_pct` %-limit path, PAPER rows counted.
- `test_risk_config.py` (NEW — module had none): grade thresholds and
  size mapping pinned per GRADE_CONFIG, `calculate_lot_size` arithmetic
  (spread-adjusted stop, R:R floor, min-lot warning, ValueError guards),
  HARD_LIMITS↔session_guard wiring, standing-rule flag + re-export.

## Explicitly OUT of scope (team decision pending)

Wiring `can_trade` into the live decision path (brief/setup_check/
trade_logger). Promotion makes the breaker real and reviewed; where it
gates is its own protected-path change with its own spec.

## Gates

- **Gate 1:** the moved+new tests above, in the LIVE suite, green.
- **Gate 2 (REALITY):** `get_session_status("trades.csv", ...)` against the
  real ledger returns ACTIVE with correct zero counts (the only rows are
  the 2026-08-01 PAPER pair — not today); the old-schema fail-closed
  behavior demonstrated against the real `trade_log.csv` (still HALTED —
  wrong schema is still wrong); shadow suite still green post-move.
- **Gate 3:** first real session with a live CLOSE row grading the curve —
  stays open until a real trade day exercises it.
