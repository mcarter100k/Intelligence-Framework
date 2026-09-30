# live_guard.sh — the live checkout must be on main (2026-09-29 audit, Phase 0).
# Sourced by the scheduled wrappers after notify.sh. Requires $PROJ.
#
#   live_guard <LOG-RELPATH>
#
# launchd runs whatever is checked out in $PROJ. From 2026-09-16 to
# 2026-09-29 that was an unmerged, unreviewed branch, and 13 days of briefs
# and nightly grading ran on it without anyone noticing. Development happens
# in git worktrees; the project folder stays on main. When it is not on
# main, every scheduled run says so in its log and as an ALERT notification.
# The run itself continues: evidence collection is never silently stopped.
# Always returns 0 (exit-0 discipline).

live_guard() {
    _lg_log="$1"
    if ! _lg_branch="$(git -C "$PROJ" symbolic-ref --short -q HEAD 2>/dev/null)"; then
        _lg_branch="(detached HEAD or git unavailable)"
    fi
    [ "$_lg_branch" = "main" ] && return 0
    _lg_msg="Live checkout is on ${_lg_branch}, not main: scheduled runs are executing unmerged code. Fix: git checkout main in the project folder."
    echo "##ALERT## LIVE BRANCH: $_lg_msg" >> "$PROJ/$_lg_log"
    notify "ALERT" "$_lg_msg" "$_lg_log"
    return 0
}
