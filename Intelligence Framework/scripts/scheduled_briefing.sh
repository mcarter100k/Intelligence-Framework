#!/bin/bash
# scheduled_briefing.sh
# ─────────────────────
# The gold BRIEFING, 3:45 AM PT (docs/specs/configuration_detector_spec.md
# §14, §14.2). Runs gold_briefing.py, appends its full text to the day log,
# and sends one BRIEFING notification whose click opens that log. BRIEFING
# is exempt from ALERTS_MUTED (scripts/notify.sh). A closed market is
# silent; a failed input is sent as a failed BRIEFING, never as a quiet
# morning. Always exits 0 so launchd never enters an error state.

# INTEL_PROJ exists for the behavioral tests only; launchd sets nothing,
# so production always uses the path below.
PROJ="${INTEL_PROJ:-/Users/quis/Intelligence Framework}"
cd "$PROJ" || exit 0
[ -f "venv/bin/activate" ] && source "venv/bin/activate"
mkdir -p logs

if [ -z "${INTEL_NO_ENV_FILE:-}" ] && [ -f "$PROJ/.env" ]; then
    set -a; . "$PROJ/.env"; set +a
fi

. "$PROJ/scripts/notify.sh"

LOG="logs/briefing_$(date +%F).log"
. "$PROJ/scripts/live_guard.sh"
live_guard "$LOG"

SUM="logs/.briefing_summary"
rm -f "$SUM"
OUT="$(python3 gold_briefing.py --summary-out "$SUM" 2>&1)"
RC=$?
{
    echo "===== briefing $(date '+%Y-%m-%d %H:%M:%S %Z') ====="
    printf '%s\n' "$OUT"
    echo "exit $RC"
    echo
} >> "$LOG"

if [ "$RC" -eq 0 ] && [ -s "$SUM" ]; then
    notify BRIEFING "$(head -n 1 "$SUM")" "$LOG" "XAU_USD"
elif [ "$RC" -eq 3 ]; then
    :    # gold's market is closed: the BRIEFING stays silent (§14)
else
    WHY="$(printf '%s\n' "$OUT" | grep -m1 '^BRIEFING FAILED' | sed 's/^BRIEFING FAILED: //')"
    [ -n "$WHY" ] || WHY="exit $RC: $(printf '%s\n' "$OUT" | tail -n 1)"
    notify BRIEFING "BRIEFING FAILED: $(printf '%s' "$WHY" | cut -c1-200)" "$LOG" "XAU_USD"
fi
rm -f "$SUM"
exit 0
