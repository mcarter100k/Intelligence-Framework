"""Pins studies/gold_session_study.py to docs/specs/gold_session_study_spec.md:
only the named inputs are rebound, and gold's complete day is the FX day
minus exactly the 17:00 New York hour. Restores every rebinding afterwards."""
import os
import sys
from datetime import date
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "studies"))
import gold_session_study as G  # noqa: E402
import session_movement_data as D  # noqa: E402
import session_movement_study as M  # noqa: E402

NY = ZoneInfo("America/New_York")


def _saved():
    return (M.PAIRS, M.PIP, dict(M.EXPECTED_HASHES), D.STUDY_FIRST_DAY, D.STUDY_LAST_DAY, D.expected_hours)


def _restore(s):
    M.PAIRS, M.PIP, M.EXPECTED_HASHES, D.STUDY_FIRST_DAY, D.STUDY_LAST_DAY, D.expected_hours = s


def test_gold_day_drops_only_the_break_hour():
    s = _saved()
    fx = D.expected_hours
    try:
        G.configure()
        for day in (date(2024, 7, 10), date(2024, 1, 10), date(2024, 1, 8), date(2024, 7, 12)):
            f, g = fx(day), D.expected_hours(day)
            dropped = [t for t in f if t not in g]
            assert all(t.astimezone(NY).hour == 17 for t in dropped)
            assert len(dropped) == sum(1 for t in f if t.astimezone(NY).hour == 17)
            assert [t for t in f if t.astimezone(NY).hour != 17] == g
        assert len(D.expected_hours(date(2024, 7, 10))) == 23           # mid-week: 24 FX hours minus the break
    finally:
        _restore(s)


def test_only_named_inputs_are_rebound():
    s = _saved()
    other = {k: v for k, v in vars(M).items() if k not in ("PAIRS", "PIP", "EXPECTED_HASHES")}
    try:
        G.configure()
        assert M.PAIRS == ("XAU_USD",) and M.PIP == {"XAU_USD": 1.0}
        assert M.EXPECTED_HASHES == G.GOLD_HASHES
        assert (D.STUDY_FIRST_DAY, D.STUDY_LAST_DAY) == (date(2021, 4, 27), date(2026, 9, 9))
        assert {k: v for k, v in vars(M).items() if k not in ("PAIRS", "PIP", "EXPECTED_HASHES")} == other
    finally:
        _restore(s)
    assert D.expected_hours is s[5] and M.PAIRS == s[0]


def test_code_pins_still_hold():
    G.R.check_code_pins()
