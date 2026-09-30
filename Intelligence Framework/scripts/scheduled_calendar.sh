#!/bin/bash
# scheduled_calendar.sh
# ─────────────────────
# Weekly calendar auto-fetch wrapper (docs/specs/calendar_autofetch_spec.md).
# Scheduling + logging only — all fetch/validate logic lives in
# calendar_fetch.py, which keeps the existing file on ANY failure.
# Always exits 0 so launchd never enters an error state.

# INTEL_PROJ exists for the behavioral tests only; launchd sets nothing,
# so production always uses the path below.
PROJ="${INTEL_PROJ:-/Users/quis/Intelligence Framework}"
cd "$PROJ" || exit 0
[ -f "venv/bin/activate" ] && source "venv/bin/activate"
mkdir -p logs

LOG="logs/calendar_$(date +%F).log"
. "$PROJ/scripts/notify.sh"
# The live checkout must be on main (scripts/live_guard.sh).
. "$PROJ/scripts/live_guard.sh"
live_guard "$LOG"
{
    echo "===== calendar fetch $(date '+%Y-%m-%d %H:%M:%S %Z') ====="
    python3 calendar_fetch.py 2>&1
    echo
} >> "$LOG"

exit 0
