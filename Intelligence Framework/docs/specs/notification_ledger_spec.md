# Notification ledger (2026-10-18) — team review given 2026-10-19; merged 42e15b8

**Why.** The owner's weekly review (foundation/trader_review.md §4, step 6)
counts MATERIAL vs TOTAL notifications. Nothing records what was sent. The
week-of-10/11 recap was rebuilt from day logs, and delivery was INFERRED
from the wrapper code. A standing review with no record is a review of a
guess.

**What.** `notification_log.csv` at the project root. It is an
append-only evidence ledger: gitignored, and added to
`scripts/backup_ledgers.py` EVIDENCE.

| column | content |
|---|---|
| `timestamp_utc` | when the send command returned success, `YYYY-MM-DDTHH:MM:SSZ` |
| `category` | DECISION / SHADOW / ALERT / RECOVERED / DIGEST / HEARTBEAT |
| `pairs` | the pairs covered by the brief behind it, space-separated; empty for notifications not built from a brief (health ALERT/RECOVERED, HEARTBEAT, grader SHADOW) |
| `decision_state` | per pair, `PAIR=STATE/market`: STATE is LONG, SHORT, STAND ASIDE or ERROR (an error page, never STAND ASIDE) and market is open or closed, e.g. `GBP_AUD=LONG/closed;GBP_JPY=STAND ASIDE/closed` |
| `summary` | the text sent (message plus the `→ <log>` pointer, at most 400 characters) |

**Writer.** `scripts/notification_ledger.py`, called by `notify()` in
`scripts/notify.sh`, through `ledger_io.append_row` (the locked, fsynced
append).

- **One row per notification actually sent.** A row is written only when
  the send command exited 0: terminal-notifier, or the osascript fallback.
  A failed send writes no row.
- **Rule 8 is satisfied by construction.** The live writer is the
  notification path itself.
- **A write failure is never silent.** The writer's error is appended to
  the day log the notification points to, as
  `NOTIFICATION LEDGER WRITE FAILED: …`, and the notification still goes
  out.

**Callers.**
- `scheduled_brief.sh` passes the pairs and the decision state for the
  DECISION, SHADOW, ALERT (flip) and DIGEST notifications built from its
  brief.
- Health notifications and the other wrappers pass none.

**Not in scope.** This is a record of what was sent, not an analytics
system: no materiality column, no read-side consumer and no freshness
cadence. Notifications are event-driven, so a cadence would alarm on a
quiet week (rule 8). The MATERIAL judgement is the owner's, made at review
time.

**Tests.**
- `test_ledger_headers.py` (M30): the on-disk header equals
  `notification_ledger.FIELDS`.
- `test_wrapper_behavior.py` d3_*: a sent notification writes exactly one
  row.
  - A suppressed DECISION, a failed send and a closed-market brief's
    DECISION write none.
  - An error page records ERROR.
  - A failed write lands in the day log.

**Known gap, not fixed here.** The DECISION summary line does not name the
pair: `DECISION LONG ▲ — look for buy entries`. The ledger's `pairs` and
`decision_state` columns carry it; the notification text does not.
