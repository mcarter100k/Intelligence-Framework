"""
test_gold_rule_costs.py — studies/gold_rule_costs.held_nights, the financing
rule for the gold specs. An exit at exactly 17:00 New York is not charged for
the night it did not hold. The older shared helper is checked alongside to show
the boundary difference it keeps for the committed studies.
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "studies"))
from gold_rule_costs import held_nights  # noqa: E402
from shadow_cost_regrade import rollover_nights  # noqa: E402

PT = ZoneInfo("America/Los_Angeles")


def pt(y, m, d, h, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=PT)


# 2026-11-17 is a Tuesday (standard time); 2026-06-16 is a Tuesday (daylight time).
CASES = [
    ("Tue 10:00 -> Wed 14:00 PT", pt(2026, 11, 17, 10), pt(2026, 11, 18, 14), 1, 4),
    ("Wed 10:00 -> Thu 14:00 PT", pt(2026, 11, 18, 10), pt(2026, 11, 19, 14), 3, 4),
    ("inside one session", pt(2026, 11, 17, 6), pt(2026, 11, 17, 13), 0, 0),
    ("Tue 10:00 -> Wed 14:00 PT, daylight time", pt(2026, 6, 16, 10), pt(2026, 6, 17, 14), 1, 4),
    ("Wed 10:00 -> Thu 14:00 PT, daylight time", pt(2026, 6, 17, 10), pt(2026, 6, 18, 14), 3, 4),
]


def test_requested_cases_and_the_old_boundary():
    for name, a, b, want, old in CASES:
        assert held_nights(a, b) == want, name
        assert rollover_nights(a, b) == old, name          # the shared helper keeps its pinned boundary


def test_exit_one_minute_after_the_roll_is_charged():
    assert held_nights(pt(2026, 11, 17, 10), pt(2026, 11, 17, 14, 1)) == 1
    assert held_nights(pt(2026, 11, 17, 10), pt(2026, 11, 17, 14)) == 0


def test_entry_at_the_roll_is_not_charged_for_it():
    assert held_nights(pt(2026, 11, 17, 14), pt(2026, 11, 17, 20)) == 0


def test_friday_to_monday_is_one_night_and_exit_at_monday_roll_adds_none():
    # Fri 06:00 PT -> Mon 13:00 PT: only Friday's roll is held.
    assert held_nights(pt(2026, 11, 20, 6), pt(2026, 11, 23, 13)) == 1
    assert held_nights(pt(2026, 11, 20, 6), pt(2026, 11, 23, 14)) == 1


def test_a_full_week():
    # Mon 06:00 -> next Mon 06:00 PT: Mon 1, Tue 1, Wed 3, Thu 1, Fri 1.
    assert held_nights(pt(2026, 11, 16, 6), pt(2026, 11, 23, 6)) == 7


def test_non_positive_holds():
    a = pt(2026, 11, 17, 10)
    assert held_nights(a, a) == 0 and held_nights(a, pt(2026, 11, 17, 9)) == 0
