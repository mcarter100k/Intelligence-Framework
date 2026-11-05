# scripts/

Paths here are fixed: the launchd plists in `launchd/` name the wrappers by
path, and the installed copies in `~/Library/LaunchAgents` must match. If a
wrapper is ever renamed, update the plists and `launchd/install.sh`, re-run
it, and add a Gate 3 PENDING entry until the next scheduled run fires.

## Scheduled jobs (run by launchd, Pacific time)

| Wrapper | When | What it does |
|---|---|---|
| `scheduled_brief.sh` | 02:30, 07:30, 18:00 daily | Runs the brief for both pairs, logs it, tracks run health, sends notifications; the 07:30 run also sends the DIGEST |
| `scheduled_outcome_check.sh` | 15:15 daily | Backs up the ledgers, then runs the nightly grader |
| `scheduled_calendar.sh` | Sunday 12:00 | Refreshes the news calendar |
| `weekly_heartbeat.sh` | Sunday 12:30 | Weekly health report, including expected vs on-time runs; always notifies |

## Sourced by the wrappers

- `notify.sh`: sends a notification (terminal-notifier, with an osascript fallback).
- `live_guard.sh`: alerts if the live checkout is not on `main`, or if any tracked code file (`*.py`, `*.sh`) in it differs from `main` (naming the files and marking Python that does not parse; incident I31).
- `crash.sh`: one definition of "the Python step crashed".

## Called by the wrappers

- `health_state.py`: consecutive-failure counter per job.
- `artifact_freshness.py`: flags an evidence ledger that has stopped being written.
- `backup_ledgers.py`: hash-checked copies of every ledger before the grader runs.
- `daily_digest.py`: the one-line DIGEST text.
- `latest_view.py`: `logs/latest_brief.log`, the page the DIGEST opens.
- `run_count.py`: expected vs on-time scheduled runs, for the heartbeat.

## Manual tools

- `reality_run.py`: runs real code on real data with every side effect neutralized (the Gate 2 tool); fails if the project changed.
- `trader_review.py`: the trader review loop: log every idea (taken or passed), score it, and write the weekly review (`foundation/trader_review.md` §0).
- `trace/`: a process and lock tracer for concurrency investigations.
- `launchd/install.sh`, `launchd/uninstall.sh`: install or remove the scheduled jobs.
