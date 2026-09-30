#!/bin/bash
# scheduled_outcome_check.sh
# ──────────────────────────
# Scheduling + notification WRAPPER only. Runs the daily outcome grader, appends
# full output to a dated log, and fires a macOS notification ONLY when a SHADOW
# outcome was graded this run (including the updated tally). Always exits 0.

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
# (docs/specs/safe_ledger_writes_spec.md): a bad grader write is always
# recoverable from today's hash-verified copy in backups/<date>/.
BACKUP="$(python3 scripts/backup_ledgers.py 2>&1)"
echo "$BACKUP" >> "$LOG"

# stdout and stderr captured SEPARATELY: the crash reason must come from
# stderr (scripts/crash.sh). Both go to the day log.
ERRTMP="$(mktemp)"
OUT="$(python3 run_outcome_check.py 2>"$ERRTMP")"
ORC=$?
{ echo "===== $(TZ="${DISPLAY_TZ:-America/Los_Angeles}" date '+%Y-%m-%d %H:%M:%S %Z') ====="; echo "$OUT"; echo; } >> "$LOG"
if [ -s "$ERRTMP" ]; then
    { echo "----- stderr (exit $ORC) -----"; cat "$ERRTMP"; echo; } >> "$LOG"
fi
CRASH="$(crash_reason grader "$ORC" "$ERRTMP")"
rm -f "$ERRTMP"

# Health tracking (docs/specs/heartbeat_spec.md item 1). Failure signature:
# a crash (nonzero exit or a Python traceback; visible_failures_spec D1 —
# before, a traceback matched none of the patterns and counted as SUCCESS),
# grader early-exit marker, unconfigured feed, no data, or empty output.
if [ -n "$CRASH" ]; then
    HEALTH="$(python3 scripts/health_state.py record-failure outcomes "$CRASH")"
elif printf '%s\n' "$BACKUP" | grep -q '^BACKUP FAILED'; then
    HEALTH="$(python3 scripts/health_state.py record-failure outcomes "$(printf '%s\n' "$BACKUP" | grep -m1 '^BACKUP FAILED' | cut -c1-160)")"
elif [ -z "$OUT" ] || printf '%s\n' "$OUT" | grep -qE 'GRADER EARLY EXIT|not configured|no data from OANDA'; then
    HREASON="$(printf '%s\n' "$OUT" | grep -oE 'GRADER EARLY EXIT[^(]*|[A-Z_]+: no data from OANDA' | head -1)"
    [ -z "$HREASON" ] && HREASON="outcome check produced no output"
    HEALTH="$(python3 scripts/health_state.py record-failure outcomes "$HREASON")"
else
    HEALTH="$(python3 scripts/health_state.py record-success outcomes)"
fi
if [ -n "$HEALTH" ]; then
    echo "$HEALTH" >> "$LOG"
    case "$HEALTH" in
        ALERT:*) HCAT="ALERT" ;;
        *)       HCAT="RECOVERED" ;;
    esac
    notify "$HCAT" "$(printf '%s' "$HEALTH" | sed 's/^ALERT://')" "$LOG"
fi

# Notify only if a shadow-signal outcome was graded this run.
if printf '%s\n' "$OUT" | grep -q 'shadow-signal outcomes filled'; then
    TALLY="$(python3 - <<'PY'
from shadow_signals import get_shadow_tally, episode_count
parts = []
for c in ("EARLY_MOMENTUM", "EARLY_MOMENTUM_v2", "THRUST_PULLBACK", "MOMENTUM_JOIN"):
    t = get_shadow_tally(c)
    if t["graded"] > 0:
        parts.append(f"{c}: {t['graded']}/{episode_count(c)}ep {t['wins']}W {t['avg_net']:+.0f}p")
print(" | ".join(parts) if parts else "shadow outcomes graded")
PY
)"
    notify "SHADOW" "$(printf '%s' "$TALLY" | cut -c1-200)" "$LOG"
fi

exit 0
