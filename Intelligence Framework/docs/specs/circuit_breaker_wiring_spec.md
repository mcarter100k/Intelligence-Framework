# Spec: wire the circuit breaker to the live path (PROPOSED, protected path)

**Status:** PROPOSED 2026-11-06, for team review.
- **Nothing is built.** It touches PROTECTED modules (`decision_brief.py`,
  `setup_check.py`, `session_guard.py`, `risk_config.py`) and the manual
  `trade_logger.py`.
- It is committed before any code, per AGENTS.md.
- It implements the "where it gates" change that
  `circuit_breaker_promotion_spec.md` left out of scope. That change is the
  stated prerequisite to the first real-money trade (AGENTS.md,
  circuit-breaker prerequisite).

## 1. Today

- `session_guard.get_session_status` / `can_trade` and `risk_config` have no
  caller on the live path. They are imported only by each other and by
  tests (grep 2026-11-06).
- The stated limits are therefore unenforced and must not be described as
  active:
  - 2R or 2% daily loss, peak to trough;
  - 2 positions a session, with positions sharing a currency counted as one.
- **The breaker reads `trades.csv`,** the two-row ledger written by
  `trade_logger.py`. It fails closed: an unreadable ledger or a wrong schema
  gives HALTED. It needs an account balance; zero or none gives HALTED.

## 2. What the breaker can and cannot do

- **The framework cannot stop a trade placed at the broker.** Trading is
  manual (the 2026-11-06 broker probe shows the OANDA account has never held
  a position).
- **What it can do:** make its state impossible to miss, and record that
  state wherever a trade decision is recorded. A control the trader cannot
  see is not a control. This spec makes the state visible, recorded and
  provable.

## 3. Where it runs and what happens when it fires

| Place | When ACTIVE | When HALTED or SESSION_CLOSED |
|---|---|---|
| **The brief** (`decision_brief.get_decision_brief`, every pair) | one line: "Circuit breaker: open — {n} of 2 positions today, {r} R of the 2 R daily limit used." | First line of the brief: "**Circuit breaker: NO NEW TRADES TODAY.** {reason}". The official decision is unchanged (§6). The breaker states the trader's limit, not the market. |
| **The pre-trade check** (`setup_check.build_stack`) | as above, in the stack output | The verdict begins "CIRCUIT BREAKER: no new trades today — {reason}", and the check's verdict cannot read as a go-ahead |
| **The pre-trade journal** | records the state | records the state (§5) |
| **Opening a trade in the log** (`trade_logger.log_open`) | logs as today | **Still logs the trade.** Reality is never refused a record. After the row it prints the breaker state, followed by "This trade was opened while the circuit breaker said no new trades." |
| **Notifications** (`_emit_alerts`) | nothing new | one alert when the state turns HALTED or SESSION_CLOSED, none while it stays there (§7) |

**{reason}** is `get_session_status`'s plain-English reason, checked by the
banned-token display test.

## 4. The account balance input: a decision for the team

`get_session_status` needs a balance for the % limit and returns HALTED
without one. Options:
- **(a) OANDA's account summary, read-only, at run time.** The 2026-11-06
  probe shows the field is served; its value was not printed.
- **(b) A configured value.**
- **(c) R-only operation,** with the % limit marked "not configured".

**Whatever the choice,** a missing balance must show as "Circuit breaker:
NOT CONFIGURED — no account balance set". It must never show as ACTIVE, and
never as "halted after losses" (AGENTS.md rule 9: a zero from an unverified
path is not data).

## 5. Ledger change (additive)

- **The change:** `pre_trade_journal.csv` gains `breaker_status` and
  `breaker_reason`, through `ledger_io.migrate_header`. Earlier rows stay
  blank and are never backfilled.
- **Order of work:** the unmerged `feat/decision-reasoning` branch also
  migrates this journal (A2: `price_at_check`, `planned_entry`,
  `planned_entry_source`). The team should rule on that branch first, so
  the two migrations land in a known order.
- `trades.csv` is unchanged.

## 6. Decisions stay byte-identical

The breaker never changes `official_decision`, `apply_filter` or any
classification.
- `tests/test_decision_logic.py` (36,864 cells) and the stand-down
  consistency matrix (T34–T41) must pass unchanged.
- A Gate-2 run of the brief with the breaker ACTIVE must render the same
  decision fields as the pre-change brief on the same bars.

## 7. Notification rules (AGENTS.md rule 12)

Each case below is tested for whether the alert should reach the owner:

| Case | Alert? |
|---|---|
| ACTIVE → HALTED or SESSION_CLOSED | yes, once |
| unchanged HALTED on a later run | no |
| market closed (weekend) | no |
| ledger unreadable (fail-closed HALTED) | yes, worded as a ledger problem, not a loss |
| NOT CONFIGURED | no alert; shown in every brief |

## 8. How a run proves it fired

**Gate 1, positive control first:**
- Each new test is run against the pre-change code and must FAIL there:
  the brief shows no breaker line, the journal has no `breaker_status`, and
  `trade_logger` prints no warning.
- Then the tests pass on the change.
- Mutants:
  - removing the brief line;
  - turning the HALTED wording into the ACTIVE wording;
  - dropping the journal field;
  - letting `trade_logger` refuse the row.
  Each must be caught.

**Gate 2 (`scripts/reality_run.py`):**
- The brief and `setup_check` run on real bars, with a temp `trades.csv` copy
  seeded with a −2R day. The output shows "NO NEW TRADES TODAY", the temp
  journal row carries `breaker_status=HALTED`, and the project is
  unchanged by hash.
- The same run with an empty temp ledger shows the ACTIVE line.
- No real ledger is written.

**Gate 3 (PENDING LIVE CONFIRMATION):** the first real day the breaker turns
HALTED from real `trades.csv` rows, recorded with date and evidence.

## 9. Open points for the team

1. **The balance input** (§4).
2. **The shared-currency rule:**
   - The 2026-11-05 currency-leg study found the two crosses' stress-week
     correlation at −0.10 (2005–2013) and +0.33 (2021–2026). "Count as one
     position" was not supported in either era.
   - Wiring keeps the current rule unchanged unless the team rules
     otherwise, since that is a limit change, not a wiring change.
3. **The order of this spec relative to the `feat/decision-reasoning`
   branch** (§5).

## 10. Out of scope

- Position sizing (A5 waits for this spec to land).
- Changing any limit value.
- Order placement.
- Any automation at the broker.
