# Alert mute switch (owner request, 2026-11-16)

**Owner, 2026-11-16:** "i think i want to hold off on GA and GJ right now -
can we cut all alerts off for that? i want to now only focus on gold for
right now".

**Zone:** free zone (`scripts/notify.sh`, its test, docs). No protected
module is touched, and no ledger is written by hand.

## What it does

- **The switch is one file: `ALERTS_MUTED` in the project folder.** While it
  exists, `notify()` sends nothing: no terminal-notifier and no osascript.
  - Mute: `touch ALERTS_MUTED`. Unmute: `rm ALERTS_MUTED`.
  - The file is gitignored. It is local state, like the ledgers, so muting
    or unmuting never needs a commit or a branch.
- **Every alert that would have been sent is written to its log instead,**
  as `MUTED (not sent; ALERTS_MUTED present) <CATEGORY>: <text>`, in the
  same file a failed ledger write would go to (the day log). Nothing is
  hidden, only not pushed to the screen.
- **A muted alert gets no `notification_log.csv` row.** That ledger records
  notifications actually sent.
- **The scheduled jobs keep running.** The brief, the nightly grader, the
  calendar and the heartbeat still run and write their ledgers, so the
  shadow candidates keep collecting forward evidence. Forward data missed
  while a job is off can never be recovered; a muted alert can be read in
  the log at any time.

## Scope: all categories

ALERT, DECISION, DIGEST, REVIEW, HEARTBEAT and the live-checkout guard are
all muted. The owner asked for all alerts off.

**Cost, stated plainly:** while muted, a broken job or a live checkout left
off `main` reaches nobody. The evidence is still in the day logs
(`UNHEALTHY`, `ALERT`, `MUTED` lines), but no one is told. Unmute, or read
the Sunday heartbeat log, to check health.

## After unmuting

- Decision state (`alert_state.py`) keeps updating while muted, so unmuting
  does not replay old decisions; only the next change notifies.
- The first DIGEST after unmuting lists every shadow signal since the last
  digest actually sent (`daily_digest.shadow_clause` reads
  `notification_log.csv`), so nothing from the muted period is skipped.

## Tests (AGENTS.md rule 12: whether it should reach the owner)

In `tests/test_notify_helper.py`:
1. Muted, terminal-notifier present: neither notifier runs, the log gets
   the MUTED line, and no `notification_log.csv` row is written.
2. Muted, terminal-notifier missing: osascript does not run either.
3. Unmuted: the existing tests still pass (alerts are still sent).
4. Single path: no script under `scripts/` other than `notify.sh` calls
   osascript or terminal-notifier, so nothing can go around the switch.
