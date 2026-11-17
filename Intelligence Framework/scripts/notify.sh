# notify.sh — shared notification helper (docs/specs/notify_click_through_spec.md)
# Sourced by the scheduled wrappers. Requires $PROJ to be set by the caller.
#
#   notify <SUBTITLE> <MESSAGE> <LOG-RELPATH> [PAIRS] [DECISION-STATE] [RECORD-LOG]
#
# SUBTITLE is the category (ALERT / RECOVERED / DECISION / DIGEST / HEARTBEAT /
# REVIEW). SHADOW was retired 2026-11-15: shadow signals go to the digest
# (docs/specs/alert_importance_spec.md).
# Every notification actually sent (the send command exited 0) is recorded
# in notification_log.csv with PAIRS and DECISION-STATE
# (docs/specs/notification_ledger_spec.md). A failed ledger write is
# appended to RECORD-LOG (default: LOG-RELPATH), never dropped. A caller whose
# click target is a regenerated view (the DIGEST) passes the day log here, so
# the failure never lands in a file the next run overwrites (team review
# 2026-11-05, defect 4).
# The message ALWAYS gets a "→ <log>" pointer appended, so the osascript
# fallback (which cannot open anything on click) still says where to look.
#
# Uses terminal-notifier (click opens the day's log) when the binary exists,
# under a bounded watchdog: macOS 13 blocks the FIRST post until the user
# authorizes notifications for terminal-notifier — a scheduled run must never
# hang on that dialog. A hung or failing post falls back to osascript, so a
# notification is never silently lost. Always returns 0 (exit-0 discipline).
# Muted while $PROJ/ALERTS_MUTED exists (docs/specs/alert_mute_spec.md).

TN_BIN="$HOME/Applications/terminal-notifier.app/Contents/MacOS/terminal-notifier"
NOTIFY_WATCHDOG_SECS="${NOTIFY_WATCHDOG_SECS:-15}"

_nt_record() {
    _nt_err="$(python3 "$PROJ/scripts/notification_ledger.py" "$PROJ" "$_nt_sub" \
               "$_nt_pairs" "$_nt_state" "$_nt_text" 2>&1 >/dev/null)" \
        || printf 'NOTIFICATION LEDGER WRITE FAILED: %s\n' "$_nt_err" >> "$PROJ/$_nt_rec"
    return 0
}

notify() {
    _nt_sub="$1"; _nt_msg="$2"; _nt_log="$3"; _nt_pairs="${4:-}"; _nt_state="${5:-}"
    _nt_rec="${6:-$3}"
    _nt_text="$(printf '%s → %s' "$_nt_msg" "$_nt_log" | cut -c1-400)"

    # Mute switch (docs/specs/alert_mute_spec.md): while $PROJ/ALERTS_MUTED
    # exists nothing is sent and no ledger row is written; the alert goes to
    # the log instead, so it is never lost.
    if [ -e "$PROJ/ALERTS_MUTED" ]; then
        printf 'MUTED (not sent; ALERTS_MUTED present) %s: %s\n' "$_nt_sub" "$_nt_text" \
            >> "$PROJ/$_nt_rec"
        return 0
    fi

    if [ -x "$TN_BIN" ]; then
        _nt_url="file://$(printf '%s/%s' "$PROJ" "$_nt_log" | sed 's/ /%20/g')"
        "$TN_BIN" -title "Intelligence Framework" -subtitle "$_nt_sub" \
                  -message "$_nt_text" -open "$_nt_url" >/dev/null 2>&1 &
        _nt_pid=$!
        _nt_i=0
        while kill -0 "$_nt_pid" 2>/dev/null && [ "$_nt_i" -lt "$NOTIFY_WATCHDOG_SECS" ]; do
            sleep 1; _nt_i=$((_nt_i + 1))
        done
        if kill -0 "$_nt_pid" 2>/dev/null; then
            kill "$_nt_pid" 2>/dev/null       # hung (unauthorized) — fall back
            _nt_ok=1
        else
            wait "$_nt_pid"; _nt_ok=$?        # finished — fall back on nonzero
        fi
        [ "$_nt_ok" -eq 0 ] && { _nt_record; return 0; }
    fi

    _nt_safe="$(printf '%s' "$_nt_text" | sed 's/"/\\"/g' | cut -c1-220)"
    _nt_subsafe="$(printf '%s' "$_nt_sub" | sed 's/"/\\"/g')"
    osascript -e "display notification \"$_nt_safe\" with title \"Intelligence Framework\" subtitle \"$_nt_subsafe\"" >/dev/null 2>&1 \
        && _nt_record
    return 0
}
