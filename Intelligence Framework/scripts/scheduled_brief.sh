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

# Credential delivery for launchd context (docs/specs/heartbeat_spec.md item 0).
# launchd starts this script in a bare env — the 39-day outage's root cause.
# .env (gitignored) is the secrets file; INTEL_NO_ENV_FILE=1 skips sourcing so
# Gate-2 can force a failure deliberately.
if [ -z "${INTEL_NO_ENV_FILE:-}" ] && [ -f "$PROJ/.env" ]; then
    set -a; . "$PROJ/.env"; set +a
fi

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

# stdout = the human brief (logged verbatim); stderr = warnings + the machine
# ##ALERT## channel (docs/specs/alert_expansion_spec.md). Both go to the log.
ERRTMP="$(mktemp)"
OUT="$(python3 decision_brief.py GBP_AUD GBP_JPY 2>"$ERRTMP")"
{ echo "===== $(date '+%Y-%m-%d %H:%M:%S %Z') ====="; echo "$OUT"; echo; } >> "$LOG"
grep '^##ALERT##' "$ERRTMP" >> "$LOG" 2>/dev/null

# Watched-condition flips (regime change / filter flip / exit-watch fired)
ALERTS="$(grep '^##ALERT## ' "$ERRTMP" | sed 's/^##ALERT## //')"
rm -f "$ERRTMP"

# Health tracking (docs/specs/heartbeat_spec.md item 1): an error brief or
# empty output is a FAILED run. Two consecutive failures notify, repeating
# daily until healthy; recovery notifies once. Never breaks the run (exit 0
# discipline lives in health_state.py too).
if [ -z "$OUT" ] || printf '%s\n' "$OUT" | grep -q 'Framework error'; then
    HREASON="$(printf '%s\n' "$OUT" | grep -o 'Framework error[^"]*' | head -1)"
    [ -z "$HREASON" ] && HREASON="brief produced no output"
    HEALTH="$(python3 scripts/health_state.py record-failure "$HREASON")"
else
    HEALTH="$(python3 scripts/health_state.py record-success)"
fi
if [ -n "$HEALTH" ]; then
    echo "$HEALTH" >> "$LOG"
    HSAFE="$(printf '%s' "$HEALTH" | sed 's/^ALERT://; s/"/\\"/g' | cut -c1-200)"
    osascript -e "display notification \"$HSAFE\" with title \"Intelligence Framework — Health\"" >/dev/null 2>&1
fi

# Notify if: a real decision (non STAND ASIDE), a shadow signal, OR a flip.
NOTIFY=0
if printf '%s\n' "$OUT" | grep 'DECISION' | grep -qv 'STAND ASIDE'; then NOTIFY=1; fi
if printf '%s\n' "$OUT" | grep -q 'SHADOW SIGNALS'; then NOTIFY=1; fi
if [ -n "$ALERTS" ]; then NOTIFY=1; fi

if [ "$NOTIFY" -eq 1 ]; then
    # Flip alerts are already one-line, plain-English, actionable — prefer them.
    if [ -n "$ALERTS" ]; then
        SUMMARY="$(printf '%s\n' "$ALERTS" | paste -sd '|' - | cut -c1-180)"
    else
        SUMMARY="$(printf '%s\n' "$OUT" \
            | grep -E 'DECISION +(LONG|SHORT)|EARLY_MOMENTUM|THRUST_PULLBACK|MOMENTUM_JOIN' \
            | sed -E 's/^ *//; s/  +/ /g' | paste -sd '|' - | cut -c1-180)"
    fi
    [ -z "$SUMMARY" ] && SUMMARY="Signal — see $LOG"
    SAFE="$(printf '%s' "$SUMMARY" | sed 's/"/\\"/g')"
    osascript -e "display notification \"$SAFE\" with title \"Intelligence Framework — Brief\"" >/dev/null 2>&1
fi

exit 0
