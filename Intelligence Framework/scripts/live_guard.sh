# live_guard.sh — the live checkout must be on main, running main's code
# (2026-09-29 audit, Phase 0; code check added 2026-11-01, incident I31).
# Sourced by the scheduled wrappers after notify.sh. Requires $PROJ.
#
#   live_guard <LOG-RELPATH>
#
# launchd runs whatever is checked out in $PROJ. From 2026-09-16 to
# 2026-09-29 that was an unmerged, unreviewed branch, and 13 days of briefs
# and nightly grading ran on it without anyone noticing. Development happens
# in git worktrees; the project folder stays on main. When it is not on
# main, every scheduled run says so in its log and as an ALERT notification.
#
# On 2026-11-01 an unreviewed edit left levels_context.py unparseable on
# main itself. entry_confirmation imports it inside `try/except Exception`,
# so the brief would have run on with its key-level check quietly off. So
# the guard also alerts when any TRACKED code file (*.py, *.sh) under $PROJ
# differs from HEAD, staged or not, and names the files, marking any Python
# file that does not parse. Docs and ledgers are not code and never alert;
# neither do untracked files (nothing on the live path imports them) or
# files elsewhere in the repo (its root is $HOME).
#
# The run itself continues: evidence collection is never silently stopped.
# Always returns 0 (exit-0 discipline).

live_guard() {
    _lg_log="$1"
    if ! _lg_branch="$(git -C "$PROJ" symbolic-ref --short -q HEAD 2>/dev/null)"; then
        _lg_branch="(detached HEAD or git unavailable)"
    fi
    if [ "$_lg_branch" != "main" ]; then
        _lg_msg="Live checkout is on ${_lg_branch}, not main: scheduled runs are executing unmerged code. Fix: git checkout main in the project folder."
        echo "##ALERT## LIVE BRANCH: $_lg_msg" >> "$PROJ/$_lg_log"
        notify "ALERT" "$_lg_msg" "$_lg_log"
    fi
    _live_code_guard "$_lg_log"
    return 0
}

_live_code_guard() {
    _lc_log="$1"
    # --relative: paths relative to $PROJ, and nothing outside it.
    _lc_changed="$(git -C "$PROJ" diff --name-only --relative HEAD -- '*.py' '*.sh' 2>/dev/null)"
    [ -z "$_lc_changed" ] && return 0
    _lc_files=""
    while IFS= read -r _lc_f; do
        [ -z "$_lc_f" ] && continue
        _lc_note=""
        if [ ! -e "$PROJ/$_lc_f" ]; then
            _lc_note=" (deleted)"
        else
            case "$_lc_f" in
                *.py)
                    python3 -c 'import ast, sys; ast.parse(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1])' \
                        "$PROJ/$_lc_f" >/dev/null 2>&1 || _lc_note=" (does not parse)"
                    ;;
            esac
        fi
        _lc_files="${_lc_files:+$_lc_files, }${_lc_f}${_lc_note}"
    done <<EOF
$_lc_changed
EOF
    _lc_msg="Live code differs from main: ${_lc_files}. Scheduled runs are executing unreviewed edits. Fix: put the change through a branch and review, or restore it with git checkout -- <file> in the project folder."
    echo "##ALERT## LIVE CODE MODIFIED: $_lc_msg" >> "$PROJ/$_lc_log"
    notify "ALERT" "$_lc_msg" "$_lc_log"
    return 0
}
