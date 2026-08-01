#!/bin/bash
# scheduled_brief.sh
# ──────────────────
# Scheduling + notification WRAPPER only. No decision or shadow logic lives here.
# Runs the daily brief, appends full output to a dated log, and fires a macOS
# notification ONLY when there is something to see (a tradeable decision, or a
# shadow signal). Always exits 0 so launchd never enters an error state.

PROJ="/Users/quis/Intelligence Framework"
cd "$PROJ" || exit 0
[ -f "venv/bin/activate" ] && source "venv/bin/activate"
mkdir -p logs

DATE="$(date +%F)"
LOG="logs/brief_${DATE}.log"

# News-calendar refresh: when calendar.csv is missing or older than 24h, run
# the AUTO-FETCHER before the brief (docs/specs/calendar_autofetch_spec.md —
# this is the mid-week retry path; the weekly primary is the Sunday launchd
# job). calendar_fetch.py keeps the existing file on any failure; the brief's
# stale-calendar note is the backstop. Manual fallback: update_calendar.py.
# Failures are logged and never fatal (exit 0 discipline).
if [ ! -f calendar.csv ] || [ -n "$(find calendar.csv -mmin +1440 2>/dev/null)" ]; then
    {
        echo "----- calendar auto-fetch $(date '+%Y-%m-%d %H:%M:%S %Z') -----"
        python3 calendar_fetch.py 2>&1 || echo "calendar fetch wrapper error (non-fatal)"
    } >> "$LOG"
fi

OUT="$(python3 decision_brief.py GBP_AUD GBP_JPY 2>&1)"
{ echo "===== $(date '+%Y-%m-%d %H:%M:%S %Z') ====="; echo "$OUT"; echo; } >> "$LOG"

# Notify if a real decision (anything other than STAND ASIDE) OR a shadow signal.
NOTIFY=0
if printf '%s\n' "$OUT" | grep 'DECISION' | grep -qv 'STAND ASIDE'; then NOTIFY=1; fi
if printf '%s\n' "$OUT" | grep -q 'SHADOW SIGNALS'; then NOTIFY=1; fi

if [ "$NOTIFY" -eq 1 ]; then
    SUMMARY="$(printf '%s\n' "$OUT" \
        | grep -E 'DECISION +(LONG|SHORT)|EARLY_MOMENTUM|THRUST_PULLBACK|MOMENTUM_JOIN' \
        | sed -E 's/^ *//; s/  +/ /g' | paste -sd '|' - | cut -c1-180)"
    [ -z "$SUMMARY" ] && SUMMARY="Signal — see $LOG"
    SAFE="$(printf '%s' "$SUMMARY" | sed 's/"/\\"/g')"
    osascript -e "display notification \"$SAFE\" with title \"Intelligence Framework — Brief\"" >/dev/null 2>&1
fi

exit 0
