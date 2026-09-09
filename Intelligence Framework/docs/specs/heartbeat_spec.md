# Spec: heartbeat — the system must be unable to die silently (Spec A, Branch 3)

**Status:** team-directed 2026-09-09 (post-audit directive), ranked above the
wealth specs. Root cause being closed: 39 days of error-runs that resolved to
STAND ASIDE, fired no notification, and exited 0 — indistinguishable from a
healthy quiet market (validation_log 2026-09-09, outage post-mortem).
**Branch:** `feat/heartbeat` (stacked on `feat/early-momentum-v2`).
Merge held for team review.

## Item 0 — credential delivery to launchd context (prerequisite, added at build)

**Added by the builder, flagged for review:** the directive's Gate 2 demands a
real healthy run staying silent — impossible while launchd starts wrappers in
a bare env and the credentials live only in the interactive shell (the outage
root cause, still live at build time: the 2026-09-08 18:15 scheduled run
failed). Fix, smallest possible: the wrappers source the project's existing
gitignored secrets file before running Python —

    set -a; . "$PROJ/.env"; set +a     # skipped when INTEL_NO_ENV_FILE=1

and `OANDA_API_KEY` / `OANDA_ACCOUNT_ID` are added to `.env` (values taken
from the working shell environment; file is gitignored, already the
designated secrets location, holding ALPHA_VANTAGE_API_KEY since May).
`oanda_feed` is untouched — it keeps reading `os.environ` only.
`INTEL_NO_ENV_FILE=1` is the documented test/ops knob that skips sourcing so
a failure can be forced deliberately (Gate 2) without touching `.env`.

## Item 1 — error-state alerting (2 consecutive errors → notify, then daily)

State lives in `logs/health_state.json` (written by the automation layer,
like every logs/ artifact): `{"consecutive_failures", "last_failure_reason",
"last_alert_date", "last_success_utc", "last_failure_utc"}`.

Logic lives in `scripts/health_state.py` (free zone, stdlib-only, testable):

- `record-failure "<reason>"` — increments the counter, and prints
  `ALERT:FRAMEWORK UNHEALTHY — <reason> — Nth consecutive failed run` when
  the counter is ≥ 2 AND no alert has fired yet today (repeat daily, not
  per-run). Never raises; exits 0.
- `record-success` — resets the counter and the alert-date; prints
  `RECOVERED after N failed runs` once when a failure streak ends (recovery
  is a notification-worthy event; silence stays reserved for steady health).
- A corrupt/missing state file is treated as zero state, never an error.

Both wrappers call it after their Python run:

- `scheduled_brief.sh` — failure signature: brief output containing
  `Framework error` (the `_error_brief` marker) or empty output.
- `scheduled_outcome_check.sh` — failure signature: output containing
  `GRADER EARLY EXIT` or `not configured` or `no data from OANDA`, or empty.
- An `ALERT:`/`RECOVERED` line from the helper is routed to `osascript`
  notification AND appended to the day's log. Exit-0 discipline unchanged.

## Item 2 — grader liveness (`run_outcome_check.py`, PROTECTED)

The not-configured early exit prints a loud, machine-detectable line —
`GRADER EARLY EXIT — OANDA not configured — nothing graded this run` —
instead of the old one-liner, and still returns cleanly. The wrapper owns
the counter ("Nth consecutive") and prints it when recording the failure;
the module stays feed-pure. The per-instrument `no data from OANDA` prints
already exist and become part of the failure signature.

## Item 3 — weekly proof-of-life (positive confirmation; silence becomes signal)

`scripts/weekly_heartbeat.sh` + `scripts/launchd/
com.quis.intelligence.heartbeat.plist` (Sunday 12:30 local, after the 12:00
calendar fetch; logs to `logs/heartbeat_<date>.log`, launchd stdio to
`logs/launchd_heartbeat.*`). Every Sunday it ALWAYS notifies, healthy or
not: health state (consecutive failures / last success), yesterday's
brief+outcomes log presence and error content, shadow rows graded per
candidate (valid rows only, via the Branch-1 guard), calendar.csv age and
newest event, storylines.md header age. A missing Sunday notification is
itself the alarm — that is the point.

## Gates

- **Gate 1:** `test_health_state.py` pins: failure #1 silent, #2 alerts with
  exact message, #3 same-day silent (daily repeat, not per-run), next-day
  repeat fires, success resets and prints RECOVERED exactly once, corrupt
  state file treated as empty, reason text carried through. Loud-exit line
  of `run_outcome_check` pinned by test.
- **Gate 2 (REALITY):** (a) forced failure — the real wrapper run twice with
  `INTEL_NO_ENV_FILE=1` and empty OANDA vars: run 1 silent, run 2 fires the
  real notification (visible on screen, line in the day's log); (b) real
  healthy wrapper run immediately after: RECOVERED fires once, counter
  resets, no UNHEALTHY alert; (c) real weekly_heartbeat.sh run producing the
  actual notification and log; (d) `launchctl list` showing the heartbeat
  job loaded.
- **Gate 3 (PENDING LIVE CONFIRMATION):** first *scheduled* healthy
  brief/outcomes runs via launchd with sourced credentials (expected the
  first scheduled slot after merge); first Sunday heartbeat notification
  fired by launchd.
