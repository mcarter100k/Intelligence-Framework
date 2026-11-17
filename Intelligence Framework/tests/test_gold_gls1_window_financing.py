"""GLS-1 G2 entry window and G4 financing helpers."""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "studies"))
import gold_gls1_window_financing as W  # noqa: E402

UTC = timezone.utc
T0 = datetime(2024, 3, 5, 12, 0, tzinfo=UTC)          # a Tuesday
M = timedelta(minutes=15)
TS = [T0 + i * M for i in range(-8, 40)]               # 15-minute bars; TS[8] opens at T0


def tf(cands):
    return (TS, M, {1: cands, -1: []})


def m5(low=100.0):
    ts = [T0 + i * timedelta(minutes=5) for i in range(-24, 120)]
    return (ts, [low] * len(ts), [low + 1] * len(ts))


DEAD = T0 + timedelta(hours=6)


def test_level_confirmed_before_the_setup_is_not_a_valid_entry():
    # bar 10 breaks a level confirmed at bar 2 (before T0): skipped; bar 14's level confirmed at 11: taken
    t, j = W.first_entry(T0, 1, 90.0, tf([(10, 2), (14, 11)]), m5(), DEAD)
    assert j == 14 and t == TS[14] + M


def test_entry_after_the_4_hour_stop_is_touched_is_missed():
    t, why = W.first_entry(T0, 1, 100.0, tf([(14, 11)]), m5(low=100.0), DEAD)
    assert t is None and why == "4-hour stop touched first"


def test_entry_after_the_deadline_is_missed():
    t, why = W.first_entry(T0, 1, 90.0, tf([(30, 25)]), m5(), T0 + timedelta(hours=3))
    assert t is None and why == "none within 10 sessions"


def test_session_close_skips_the_weekend():
    fri = datetime(2024, 3, 8, 15, 0, tzinfo=UTC)       # Friday 10:00 New York
    assert W.session_close(fri, 1) == datetime(2024, 3, 11, 17, 0, tzinfo=W.NY)


def test_one_session_hold_from_tuesday_pays_one_night_and_from_wednesday_three():
    tue = datetime(2024, 3, 5, 15, 0, tzinfo=UTC)
    wed = datetime(2024, 3, 6, 15, 0, tzinfo=UTC)
    assert W.held_nights(tue, W.session_close(tue, 1)) == 1
    assert W.held_nights(wed, W.session_close(wed, 1)) == 3
