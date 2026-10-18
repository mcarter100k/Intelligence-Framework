"""
test_hygiene_equivalence.py — behaviour kept by the 2026-10-18 hygiene
refactors (docs/specs/code_hygiene_spec.md B6). Each test passes on the
code before and after the refactor.
"""
import levels_context as lc


def _old_current_session(hour_utc):            # the logic before B6, verbatim
    if 7 <= hour_utc < 16:
        return "London"
    if 13 <= hour_utc < 22:
        return "NY"
    return "Asian"


def test_current_session_is_unchanged_for_every_hour():
    assert [lc._current_session(h) for h in range(24)] == \
           [_old_current_session(h) for h in range(24)]
