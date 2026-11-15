#!/bin/bash
# scheduled_brief.sh
# ──────────────────
# Scheduling + notification WRAPPER only. No decision or shadow logic lives here.
# Refreshes calendar.csv when it is over 24h old, runs the brief for both pairs,
# logs it, then checks ledger freshness. A crash, an error brief, a shadow
# candidate error or a STALE ledger counts as a failed run.
# Notifies on: health failure/recovery and the live-branch guard; then one of
# ALERT (an open pair's flip you can act on, plus any decision change) >
# DECISION (an open pair's decision CHANGED: new, reversed or withdrawn); plus
# the 07:30 DIGEST when a pair is open (only the brief-ny plist passes
# "digest"; it also rewrites logs/latest_brief.log). Shadow signals never
# notify: they go to the digest (docs/specs/alert_importance_spec.md).
# Always exits 0 so launchd never enters an error state.

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

# One brief run at a time (alert_importance_spec N6). launchd runs a missed job
# and the next one together on wake (two runs at 07:41:07 on 2026-11-14); the
# second waits here, then reads the first run's alert state instead of
# repeating its notifications. A lock older than 30 minutes is stale.
BRIEF_LOCK="logs/.brief.lock"; HAVE_LOCK=""; WAITED=0
while :; do
    if mkdir "$BRIEF_LOCK" 2>/dev/null; then HAVE_LOCK=1; break; fi
    if [ -n "$(find "$BRIEF_LOCK" -maxdepth 0 -mmin +30 2>/dev/null)" ]; then
        rmdir "$BRIEF_LOCK" 2>/dev/null && echo "stale brief lock taken over" >> "$LOG"
        continue
    fi
    if [ "$WAITED" -ge "${INTEL_LOCK_WAIT_SECS:-600}" ]; then
        echo "brief lock still held after ${WAITED}s — running without it" >> "$LOG"
        break
    fi
    sleep 2; WAITED=$((WAITED + 2))
done
[ -n "$HAVE_LOCK" ] && trap 'rmdir "$BRIEF_LOCK" 2>/dev/null' EXIT

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
# The header is stamped once: the digest's freshness check below matches it.
RUN_STAMP="$(TZ="${DISPLAY_TZ:-America/Los_Angeles}" date '+%Y-%m-%d %H:%M:%S %Z')"
{ echo "===== $RUN_STAMP ====="; echo "$OUT"; echo; } >> "$LOG"
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

# Brief triggers are anchored to LABEL lines (docs/specs/us_events_context_spec.md
# §1.4, team review 2026-11-01). Labels start with 0-2 spaces; wrapped
# continuation lines start with 13 or 15, so feed text that wraps onto a new
# line (a US title, a news REASON) can never pose as a DECISION, SHADOW,
# error or pair-header line. "^ *" would not do: a wrapped word starts a
# continuation line. Same anchors in the awk programs below.
RE_DECISION='^ ? ?DECISION '
RE_SHADOW='^ ? ?SHADOW SIGNALS'
RE_ERROR='^ ? ?REASON +Framework error'

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
    HEALTH="$(python3 scripts/health_state.py record-failure brief "$CRASH" 2>>"$LOG")"
elif [ -z "$OUT" ] || printf '%s\n' "$OUT" | grep -Eq "$RE_ERROR"; then
    HREASON="$(printf '%s\n' "$OUT" | grep -E "$RE_ERROR" | grep -o 'Framework error[^"]*' | head -1)"
    [ -z "$HREASON" ] && HREASON="brief produced no output"
    HEALTH="$(python3 scripts/health_state.py record-failure brief "$HREASON" 2>>"$LOG")"
elif [ -n "$SHADOW_ERR" ]; then
    HEALTH="$(python3 scripts/health_state.py record-failure brief "$SHADOW_ERR" 2>>"$LOG")"
elif [ -n "$STALE_LINE" ]; then
    HEALTH="$(python3 scripts/health_state.py record-failure brief "$STALE_LINE" 2>>"$LOG")"
else
    HEALTH="$(python3 scripts/health_state.py record-success brief 2>>"$LOG")"
fi
if [ -n "$HEALTH" ]; then
    echo "$HEALTH" >> "$LOG"
    case "$HEALTH" in
        ALERT:*) HCAT="ALERT" ;;
        *)       HCAT="RECOVERED" ;;
    esac
    notify "$HCAT" "$(printf '%s' "$HEALTH" | sed 's/^ALERT://')" "$LOG"
fi

# Market-status gate on DECISION (docs/specs/decision_channel_measurement_spec.md,
# Phase 0): a decision issued while the market is closed cannot be acted on,
# so its line is dropped before the DECISION test and the summary. Only
# DECISION is gated; ALERT, health, SHADOW and DIGEST fire as before. The
# brief has no machine-readable market flag (decision_brief.py is protected),
# so this is the banner regime_detection._market_status puts in a closed
# instrument's header, pinned in test_wrapper_behavior.py (g1-g9) so a wording
# change fails the suite rather than silently disabling the gate. Scoped per
# instrument: each "XXX/YYY" header line starts a new block. No banner means
# open, which is the old behavior.
CLOSED_MARKER='Market closed — analysis based on last close.'
OUT_GATED="$(printf '%s\n' "$OUT" | awk -v m="$CLOSED_MARKER" '
    /^ ? ?[A-Z][A-Z][A-Z]\/[A-Z][A-Z][A-Z]( |$)/ { closed = 0 }
    index($0, m) { closed = 1 }
    closed && /^ ? ?DECISION / && !/STAND ASIDE/ { next }
    { print }')"
if printf '%s\n' "$OUT" | grep -E "$RE_DECISION" | grep -qv 'STAND ASIDE' \
   && ! printf '%s\n' "$OUT_GATED" | grep -E "$RE_DECISION" | grep -qv 'STAND ASIDE'; then
    echo "DECISION notification suppressed: market closed" >> "$LOG"
fi

# Per-pair decision state for the notification ledger
# (docs/specs/notification_ledger_spec.md), e.g.
# "GBP_AUD=LONG/closed;GBP_JPY=STAND ASIDE/closed". An error page prints
# STAND ASIDE, so its REASON line makes the state ERROR.
DSTATE="$(printf '%s\n' "$OUT" | awk -v m="$CLOSED_MARKER" '
    function emit() { if (p != "") print p "=" d "/" (c ? "closed" : "open") }
    /^ ? ?[A-Z][A-Z][A-Z]\/[A-Z][A-Z][A-Z]( |$)/ { emit(); p = $1; sub("/", "_", p); d = "?"; c = 0 }
    index($0, m) { c = 1 }
    /^ ? ?DECISION / && d != "ERROR" { d = ($0 ~ /STAND ASIDE/) ? "STAND ASIDE" : ($0 ~ /LONG/) ? "LONG" : ($0 ~ /SHORT/) ? "SHORT" : "?" }
    /^ ? ?REASON +Framework error/ { d = "ERROR" }
    END { emit() }' | paste -sd ';' -)"
PAIRS="$(printf '%s' "$DSTATE" | tr ';' '\n' | cut -d= -f1 | paste -sd ' ' -)"

# What reaches the owner (docs/specs/alert_importance_spec.md).
# N1 + N2: a pair's flip line ("GBP/AUD: ...") notifies only when that pair is
# open AND it says what the framework now allows, or that an exit-watch fired.
# A bare "the market regime changed" (5 GBP/JPY alerts in 5 days while only
# the 4-hour label flickered) stays in the day log. Lines without a pair
# prefix are system lines (exclusion registry, candidate error): always sent.
OPEN_PAIRS="$(printf '%s' "$DSTATE" | tr ';' '\n' | grep '/open$' | cut -d= -f1 | tr '_' '/' | paste -sd ' ' -)"
SEND_ALERTS=""
if [ -n "$ALERTS" ]; then
    SEND_ALERTS="$(printf '%s\n' "$ALERTS" | awk -v open=" $OPEN_PAIRS " '
        /^[A-Z][A-Z][A-Z]\/[A-Z][A-Z][A-Z][: ]/ {
            if (index(open, " " substr($0, 1, 7) " ") &&
                $0 ~ /the framework now allows a trade|the framework has stood down|exit-watch fired/) print
            next }
        { print }')"
    printf '%s\n' "$ALERTS" | while IFS= read -r a; do
        printf '%s\n' "$SEND_ALERTS" | grep -qxF -- "$a" \
            || echo "ALERT not sent (market closed or nothing to act on): $a" >> "$LOG"
    done
fi

# N5: a decision notifies when it CHANGES (new, reversed, withdrawn), never on
# every run. A failing state helper falls back to the old behavior, loudly.
DECISIONS="$(python3 scripts/alert_state.py decisions "$DSTATE" 2>>"$LOG")"
if [ $? -ne 0 ]; then
    echo "ALERT STATE FAILED — notifying every open-market decision this run" >> "$LOG"
    DECISIONS="$(printf '%s\n' "$OUT_GATED" | awk '
            /^ ? ?[A-Z][A-Z][A-Z]\/[A-Z][A-Z][A-Z]( |$)/ { pair = $1 }
            /^ ? ?DECISION +(LONG|SHORT)/ {
                d = ($0 ~ /DECISION +LONG/) ? "LONG" : "SHORT"
                print (pair != "" ? pair " " : "") d }' | paste -sd '|' - | sed 's/|/ · /g')"
fi

# N3: shadow signals never notify; they reach the owner in the next digest.
if printf '%s\n' "$OUT" | grep -Eq "$RE_SHADOW"; then
    echo "SHADOW not sent (digest only): this run's brief has shadow signals" >> "$LOG"
fi

CATEGORY=""; SUMMARY=""
if [ -n "$SEND_ALERTS" ]; then
    CATEGORY="ALERT"
    SUMMARY="$(printf '%s\n' "$SEND_ALERTS" | paste -sd '|' -)"
    [ -n "$DECISIONS" ] && SUMMARY="$SUMMARY|$DECISIONS"
elif [ -n "$DECISIONS" ]; then
    CATEGORY="DECISION"; SUMMARY="$DECISIONS"
fi
if [ -n "$CATEGORY" ]; then
    notify "$CATEGORY" "$(printf '%s' "$SUMMARY" | cut -c1-180)" "$LOG" "$PAIRS" "$DSTATE"
fi

# Daily DIGEST (docs/specs/daily_digest_spec.md): ONLY when launchd passed
# the "digest" argument (the 07:30 job's plist does; nothing else does).
# One line, both pairs' decisions + the concrete watch condition, clicking
# through to the regenerated latest-view. View/digest failure falls back
# to the day log — never breaks the run.
# N1: no digest when every rendered pair is closed. A run that rendered no
# pair (a crash) still digests, as "run failed".
if [ "${1:-}" = "digest" ] && [ -n "$DSTATE" ] && [ -z "$OPEN_PAIRS" ]; then
    python3 scripts/latest_view.py "logs" "logs/latest_brief.log" || true
    echo "DIGEST not sent: market closed" >> "$LOG"
elif [ "${1:-}" = "digest" ]; then
    python3 scripts/latest_view.py "logs" "logs/latest_brief.log" || true
    DIGEST="$(printf '%s
' "$OUT" | python3 scripts/daily_digest.py)"
    [ -z "$DIGEST" ] && DIGEST="digest unavailable — see the log"
    # latest_view.py always exits 0 and keeps the old file on failure, so the
    # view is used only when its first line is THIS run (team review
    # 2026-11-05, defect 5); otherwise the click opens the day log. Ledger
    # failures always go to the day log (notify's 6th argument).
    if [ -f "logs/latest_brief.log" ] \
       && [ "$(head -n 1 logs/latest_brief.log)" = "LATEST RUN — $RUN_STAMP" ]; then
        notify "DIGEST" "$DIGEST" "logs/latest_brief.log" "$PAIRS" "$DSTATE" "$LOG"
    else
        notify "DIGEST" "$DIGEST" "$LOG" "$PAIRS" "$DSTATE"
    fi
fi

exit 0
