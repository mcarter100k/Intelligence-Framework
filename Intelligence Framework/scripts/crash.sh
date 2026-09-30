# crash.sh — one definition of "the Python target crashed" for the wrappers
# (docs/specs/visible_failures_spec.md D1/D3, review findings F1/F10).
# Sourced by the scheduled wrappers.
#
#   crash_reason <label> <exit-code> <stderr-file>
#
# Prints "<label> crashed (exit N): <exception line>" when the exit code is
# nonzero OR stderr holds a Python traceback. Prints nothing otherwise.
# Reads STDERR ONLY: a crashed process's buffered stdout can be flushed
# after its traceback, so a reason taken from merged output could name a
# harmless stdout line instead of the exception.
crash_reason() {
    _cr_label="$1"; _cr_rc="$2"; _cr_err="$3"
    if [ "$_cr_rc" -ne 0 ] || grep -q 'Traceback (most recent call last)' "$_cr_err" 2>/dev/null; then
        _cr_line="$(grep -v '^[[:space:]]' "$_cr_err" 2>/dev/null | grep -v '^Traceback' | tail -1 | cut -c1-160)"
        printf '%s crashed (exit %s): %s\n' "$_cr_label" "$_cr_rc" "${_cr_line:-no error output}"
    fi
    return 0
}
