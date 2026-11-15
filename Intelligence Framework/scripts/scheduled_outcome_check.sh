#!/bin/bash
# scheduled_outcome_check.sh
# ──────────────────────────
# Scheduling + notification WRAPPER only. Backs up every ledger, then (only if
# the backup verified) runs the nightly grader and logs its output.
# Notifies on: health failure/recovery (failed backup, crash, early exit, no
# data), the live-branch guard, and SHADOW when a shadow outcome was graded.
# Always exits 0.

# INTEL_PROJ exists for the behavioral tests only; launchd sets nothing,
# so production always uses the path below.
PROJ="${INTEL_PROJ:-/Users/quis/Intelligence Framework}"
cd "$PROJ" || exit 0
[ -f "venv/bin/activate" ] && source "venv/bin/activate"
mkdir -p logs

# Credential delivery for launchd context (docs/specs/heartbeat_spec.md item 0).
if [ -z "${INTEL_NO_ENV_FILE:-}" ] && [ -f "$PROJ/.env" ]; then
    set -a; . "$PROJ/.env"; set +a
fi

# Shared notification helper (docs/specs/notify_click_through_spec.md).
. "$PROJ/scripts/notify.sh"

DATE="$(date +%F)"
LOG="logs/outcomes_${DATE}.log"
# The live checkout must be on main (scripts/live_guard.sh).
. "$PROJ/scripts/live_guard.sh"
live_guard "$LOG"
. "$PROJ/scripts/crash.sh"

# Back up every evidence file BEFORE the grader rewrites anything
# (docs/specs/safe_ledger_writes_spec.md). The grader runs ONLY after the
# backup's success line (review R2/R10): a failed or crashed backup, or a
# missing script, means no fresh copy exists, so nothing may be rewritten.
# Grading is idempotent; a skipped night catches up on the next run.
BACKUP="$(python3 scripts/backup_ledgers.py 2>&1)"
echo "$BACKUP" >> "$LOG"
BACKUP_OK="$(printf '%s\n' "$BACKUP" | grep -m1 '^backup .*all sha256 verified')"

OUT=""; ORC=0; CRASH=""
if [ -n "$BACKUP_OK" ]; then
    # stdout and stderr captured SEPARATELY: the crash reason must come
    # from stderr (scripts/crash.sh). Both go to the day log.
    ERRTMP="$(mktemp)"
    OUT="$(python3 run_outcome_check.py 2>"$ERRTMP")"
    ORC=$?
    { echo "===== $(TZ="${DISPLAY_TZ:-America/Los_Angeles}" date '+%Y-%m-%d %H:%M:%S %Z') ====="; echo "$OUT"; echo; } >> "$LOG"
    if [ -s "$ERRTMP" ]; then
        { echo "----- stderr (exit $ORC) -----"; cat "$ERRTMP"; echo; } >> "$LOG"
    fi
    CRASH="$(crash_reason grader "$ORC" "$ERRTMP")"
    rm -f "$ERRTMP"
else
    echo "GRADER SKIPPED: no verified backup this run, so nothing is rewritten" >> "$LOG"
fi

# A run FAILS on: a failed backup, a crash (nonzero exit or a traceback), the
# grader's early-exit marker, an unconfigured feed, no data, or empty output
# (docs/specs/heartbeat_spec.md item 1; visible_failures_spec.md D1).
if [ -z "$BACKUP_OK" ]; then
    BREASON="$(printf '%s\n' "$BACKUP" | grep -m1 '^BACKUP FAILED' | cut -c1-160)"
    [ -z "$BREASON" ] && BREASON="BACKUP FAILED: no success line ($(printf '%s' "$BACKUP" | tail -1 | cut -c1-120))"
    HEALTH="$(python3 scripts/health_state.py record-failure outcomes "$BREASON" 2>>"$LOG")"
elif [ -n "$CRASH" ]; then
    HEALTH="$(python3 scripts/health_state.py record-failure outcomes "$CRASH" 2>>"$LOG")"
elif [ -z "$OUT" ] || printf '%s\n' "$OUT" | grep -qE 'GRADER EARLY EXIT|not configured|no data from OANDA'; then
    HREASON="$(printf '%s\n' "$OUT" | grep -oE 'GRADER EARLY EXIT[^(]*|[A-Z_]+: no data from OANDA' | head -1)"
    [ -z "$HREASON" ] && HREASON="outcome check produced no output"
    HEALTH="$(python3 scripts/health_state.py record-failure outcomes "$HREASON" 2>>"$LOG")"
else
    HEALTH="$(python3 scripts/health_state.py record-success outcomes 2>>"$LOG")"
fi
if [ -n "$HEALTH" ]; then
    echo "$HEALTH" >> "$LOG"
    case "$HEALTH" in
        ALERT:*) HCAT="ALERT" ;;
        *)       HCAT="RECOVERED" ;;
    esac
    notify "$HCAT" "$(printf '%s' "$HEALTH" | sed 's/^ALERT://')" "$LOG"
fi

# Review gates, not nightly tallies (docs/specs/alert_importance_spec.md N4).
# The old "shadow graded" ping fired on every grading and could not be acted
# on. Now one notification when a candidate first reaches 20 (futility
# checkpoint), 30 (flag) or 60 (decision) graded episodes, only while the
# market is open; a gate reached while closed is announced at the next open
# run. Checked every run, graded or not. A failing helper is logged loudly.
if [ -n "$BACKUP_OK" ] && [ -z "$CRASH" ]; then
    GATE_OUT="$(python3 scripts/alert_state.py gates 2>>"$LOG")"
    [ $? -ne 0 ] && echo "ALERT STATE FAILED — review gates not checked this run" >> "$LOG"
    if [ -n "$GATE_OUT" ]; then
        notify "REVIEW" "$(printf '%s\n' "$GATE_OUT" | paste -sd '|' - | sed 's/|/ · /g' | cut -c1-200)" "$LOG"
    fi
fi

exit 0
