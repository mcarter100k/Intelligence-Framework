# notify.sh — shared notification helper (docs/specs/notify_click_through_spec.md)
# Sourced by the scheduled wrappers. Requires $PROJ to be set by the caller.
#
#   notify <SUBTITLE> <MESSAGE> <LOG-RELPATH>
#
# SUBTITLE is the category (ALERT / RECOVERED / SHADOW / DECISION / DIGEST / HEARTBEAT).
# The message ALWAYS gets a "→ <log>" pointer appended, so the osascript
# fallback (which cannot open anything on click) still says where to look.
#
# Uses terminal-notifier (click opens the day's log) when the binary exists,
# under a bounded watchdog: macOS 13 blocks the FIRST post until the user
# authorizes notifications for terminal-notifier — a scheduled run must never
# hang on that dialog. A hung or failing post falls back to osascript, so a
# notification is never silently lost. Always returns 0 (exit-0 discipline).

TN_BIN="$HOME/Applications/terminal-notifier.app/Contents/MacOS/terminal-notifier"
NOTIFY_WATCHDOG_SECS="${NOTIFY_WATCHDOG_SECS:-15}"

notify() {
    _nt_sub="$1"; _nt_msg="$2"; _nt_log="$3"
    _nt_text="$(printf '%s → %s' "$_nt_msg" "$_nt_log" | cut -c1-400)"

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
        [ "$_nt_ok" -eq 0 ] && return 0
    fi

    _nt_safe="$(printf '%s' "$_nt_text" | sed 's/"/\\"/g' | cut -c1-220)"
    _nt_subsafe="$(printf '%s' "$_nt_sub" | sed 's/"/\\"/g')"
    osascript -e "display notification \"$_nt_safe\" with title \"Intelligence Framework\" subtitle \"$_nt_subsafe\"" >/dev/null 2>&1
    return 0
}
