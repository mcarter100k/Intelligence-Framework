#!/bin/bash
# scheduled_brief.sh
# ──────────────────
# Scheduling + notification WRAPPER only. No decision or shadow logic lives here.
# Runs the daily brief, appends full output to a dated log, and fires a macOS
# notification ONLY when there is something to see (a tradeable decision, or a
# shadow signal). Always exits 0 so launchd never enters an error state.

# INTEL_PROJ exists for the behavioral tests only; launchd sets nothing,
# so production always uses the path below.
PROJ="${INTEL_PROJ:-/Users/quis/Intelligence Framework}"
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

# Shared notification helper (docs/specs/notify_click_through_spec.md):
# click-to-open via terminal-notifier when installed, osascript fallback.
. "$PROJ/scripts/notify.sh"

DATE="$(date +%F)"
LOG="logs/brief_${DATE}.log"
# The live checkout must be on main (scripts/live_guard.sh).
. "$PROJ/scripts/live_guard.sh"
live_guard "$LOG"
. "$PROJ/scripts/crash.sh"

# News-calendar refresh: when calendar.csv is missing or older than 24h, run
# the AUTO-FETCHER before the brief (docs/specs/calendar_autofetch_spec.md —
# this is the mid-week retry path; the weekly primary is the Sunday launchd
# job). calendar_fetch.py keeps the existing file on any failure; the brief's
# stale-calendar note is the backstop.
# Failures are logged and never fatal (exit 0 discipline).
if [ ! -f calendar.csv ] || [ -n "$(find calendar.csv -mmin +1440 2>/dev/null)" ]; then
    {
        echo "----- calendar auto-fetch $(TZ="${DISPLAY_TZ:-America/Los_Angeles}" date '+%Y-%m-%d %H:%M:%S %Z') -----"
        python3 calendar_fetch.py 2>&1 || echo "calendar fetch wrapper error (non-fatal)"
    } >> "$LOG"
fi

# stdout = the human brief (logged verbatim); stderr = warnings + the machine
# ##ALERT## channel (docs/specs/alert_expansion_spec.md). ALL of stderr goes
# to the log (visible_failures_spec D2/D3): the old version kept only the
# ##ALERT## lines, so a logger failure or a crash's traceback was discarded.
ERRTMP="$(mktemp)"
OUT="$(python3 decision_brief.py GBP_AUD GBP_JPY 2>"$ERRTMP")"
BRC=$?
{ echo "===== $(TZ="${DISPLAY_TZ:-America/Los_Angeles}" date '+%Y-%m-%d %H:%M:%S %Z') ====="; echo "$OUT"; echo; } >> "$LOG"
if [ -s "$ERRTMP" ]; then
    { echo "----- stderr (exit $BRC) -----"; cat "$ERRTMP"; echo; } >> "$LOG"
fi

# Watched-condition flips (regime change / filter flip / exit-watch fired)
ALERTS="$(grep '^##ALERT## ' "$ERRTMP" | sed 's/^##ALERT## //')"
# Shadow candidate errors (thrust_pullback_alignment spec): a candidate that
# raises must ride the UNHEALTHY plumbing, never render as a quiet no-setup.
SHADOW_ERR="$(grep -m1 'SHADOW CANDIDATE ERROR' "$ERRTMP" | sed 's/^##ALERT## //')"
# A crash is a FAILED run whatever else happened (D3): nonzero exit or a
# Python traceback. Reason = the exception line, so the alert says what broke.
CRASH="$(crash_reason brief "$BRC" "$ERRTMP")"
rm -f "$ERRTMP"

# Health tracking (docs/specs/heartbeat_spec.md item 1): an error brief or
# empty output is a FAILED run. Two consecutive failures notify, repeating
# daily until healthy; recovery notifies once. Never breaks the run (exit 0
# discipline lives in health_state.py too).
# Artifact freshness (regime_log_restore spec item 4a): a run that succeeds
# while an evidence artifact is past its expected cadence is ALSO a failed
# run — a silent ledger must ride the same UNHEALTHY plumbing. Stale lines
# go to the day log; the check runs after the brief so this run's own
# writes count.
FRESH="$(python3 scripts/artifact_freshness.py check 2>/dev/null)"
STALE_LINE="$(printf '%s\n' "$FRESH" | grep -m1 '^STALE:')"
[ -n "$STALE_LINE" ] && printf '%s\n' "$FRESH" | grep '^STALE:' >> "$LOG"
# DUE: lines (human-written files past their cadence) are reminders only:
# logged, never a failure (visible_failures_spec D5).
printf '%s\n' "$FRESH" | grep '^DUE:' >> "$LOG"
if [ -n "$CRASH" ]; then
    HEALTH="$(python3 scripts/health_state.py record-failure brief "$CRASH")"
elif [ -z "$OUT" ] || printf '%s\n' "$OUT" | grep -q 'Framework error'; then
    HREASON="$(printf '%s\n' "$OUT" | grep -o 'Framework error[^"]*' | head -1)"
    [ -z "$HREASON" ] && HREASON="brief produced no output"
    HEALTH="$(python3 scripts/health_state.py record-failure brief "$HREASON")"
elif [ -n "$SHADOW_ERR" ]; then
    HEALTH="$(python3 scripts/health_state.py record-failure brief "$SHADOW_ERR")"
elif [ -n "$STALE_LINE" ]; then
    HEALTH="$(python3 scripts/health_state.py record-failure brief "$STALE_LINE")"
else
    HEALTH="$(python3 scripts/health_state.py record-success brief)"
fi
if [ -n "$HEALTH" ]; then
    echo "$HEALTH" >> "$LOG"
    case "$HEALTH" in
        ALERT:*) HCAT="ALERT" ;;
        *)       HCAT="RECOVERED" ;;
    esac
    notify "$HCAT" "$(printf '%s' "$HEALTH" | sed 's/^ALERT://')" "$LOG"
fi

# Notify if: a real decision (non STAND ASIDE), a shadow signal, OR a flip.
# Category priority mirrors the old summary preference: flips first, then the
# decision, then shadow (docs/specs/notify_click_through_spec.md).
CATEGORY=""
if printf '%s\n' "$OUT" | grep -q 'SHADOW SIGNALS'; then CATEGORY="SHADOW"; fi
if printf '%s\n' "$OUT" | grep 'DECISION' | grep -qv 'STAND ASIDE'; then CATEGORY="DECISION"; fi
if [ -n "$ALERTS" ]; then CATEGORY="ALERT"; fi

if [ -n "$CATEGORY" ]; then
    # Flip alerts are already one-line, plain-English, actionable — prefer them.
    if [ -n "$ALERTS" ]; then
        SUMMARY="$(printf '%s\n' "$ALERTS" | paste -sd '|' - | cut -c1-180)"
    else
        SUMMARY="$(printf '%s\n' "$OUT" \
            | grep -E 'DECISION +(LONG|SHORT)|EARLY_MOMENTUM|THRUST_PULLBACK|MOMENTUM_JOIN' \
            | sed -E 's/^ *//; s/  +/ /g' | paste -sd '|' - | cut -c1-180)"
    fi
    [ -z "$SUMMARY" ] && SUMMARY="Signal — see $LOG"
    notify "$CATEGORY" "$SUMMARY" "$LOG"
fi

# Daily DIGEST (docs/specs/daily_digest_spec.md): ONLY when launchd passed
# the "digest" argument (the 07:30 job's plist does; nothing else does).
# One line, both pairs' decisions + the concrete watch condition, clicking
# through to the regenerated latest-view. View/digest failure falls back
# to the day log — never breaks the run.
if [ "${1:-}" = "digest" ]; then
    python3 scripts/latest_view.py "logs" "logs/latest_brief.log" || true
    DIGEST="$(printf '%s
' "$OUT" | python3 scripts/daily_digest.py)"
    [ -z "$DIGEST" ] && DIGEST="digest unavailable — see the log"
    if [ -f "logs/latest_brief.log" ]; then
        notify "DIGEST" "$DIGEST" "logs/latest_brief.log"
    else
        notify "DIGEST" "$DIGEST" "$LOG"
    fi
fi

exit 0
