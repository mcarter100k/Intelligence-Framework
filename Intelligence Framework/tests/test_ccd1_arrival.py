"""Arrival and cooldown logic of studies/ccd1_arrival_calibration.py (spec §13.3)."""
import os, sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "studies"))
import ccd1_arrival_calibration as A

T0 = datetime(2026, 1, 5, tzinfo=timezone.utc)


def series(closes, wick=0.2):
    return {"H1": {"t": [T0 + timedelta(hours=i) for i in range(len(closes))],
                   "H": [c + wick for c in closes], "L": [c - wick for c in closes], "C": list(closes)}}


def run(closes, tol=0.10, kinds=("D1",), level=100.0, atr=10.0):
    s = series(closes)
    sets = [(atr, [("D1", "D1x", level)])] * len(closes)
    return [s["H1"]["t"].index(t) for t in A.fires(s, sets, tol, set(kinds))]


def test_one_approach_fires_once_and_rearms_after_leaving():
    # far (110: armed), arrives (100.5 is within 1.0 + wick), lingers, leaves to 106, returns
    closes = [110, 108, 100.5, 100.3, 100.8, 106, 104, 100.4]
    assert run(closes) == [2, 7]


def test_never_armed_never_fires():
    # starts within 0.5 ATR (5.0) of the level and never leaves
    assert run([103, 101, 100.2, 102, 100.1]) == []


def test_outside_tolerance_does_not_fire():
    # 101.5 - wick 0.2 = 101.3 > 100 + 1.0
    assert run([110, 101.5, 110]) == []


def test_level_type_outside_the_list_is_ignored():
    assert run([110, 100.0], kinds=("H4",)) == []


def test_bar_far_on_the_other_side_does_not_fire():
    # armed from below; a bar at 90 is nowhere near 100 even though its low is under 101
    assert run([80, 85, 90]) == []


def test_arrival_from_below_fires():
    assert run([90, 95, 99.5]) == [2]


def test_session_index_treats_an_hour_past_the_last_daily_bar_as_a_new_session():
    d = [T0 + timedelta(days=k) for k in range(3)]          # three complete daily bars
    assert A.session_index(d, d[2] + timedelta(hours=5)) == 2      # inside the last bar's span
    assert A.session_index(d, d[2] + timedelta(hours=25)) == 3     # live session, not in the list
    assert A.session_index(d, d[1] + timedelta(hours=1)) == 1


# ── LEVEL BREAK (spec §17, owner rulings P1/P4) ───────────────────────────────
def _lb(closes, level_sets_per_bar, kinds=("D1", "RANGE", "PDAY", "PWEEK"), atr=10.0, tol=0.10):
    s = series(closes)
    sets = [(atr, lv) for lv in level_sets_per_bar]
    arr = A.fires_detail(s, sets, tol, set(kinds))
    brk = A.level_breaks(s, sets, arr, set(kinds))
    return [t for t, _ in arr], [t for t, _ in brk]


L100 = [("PDAY", "PDL1", 100.0)]


def test_a_close_through_an_alerted_level_breaks_even_inside_the_approach_cooldown():
    # arrives at bar 2, lingers (never 5.0 away, so no re-arm), closes through at bar 5
    arr, brk = _lb([110, 108, 100.5, 101.0, 100.4, 99.2], [L100] * 6)
    assert arr == [2] and brk == [5]


def test_a_level_that_stops_qualifying_is_no_longer_watched():
    sets = [L100] * 4 + [[], []]                      # the level drops out of the set at bar 4
    arr, brk = _lb([110, 108, 100.5, 101.0, 99.0, 98.0], sets)
    assert arr == [2] and brk == []


def test_a_change_of_qualification_at_the_same_price_keeps_the_watch():
    # prior-session low at bar 2, a range edge at the same price from bar 4 (P4)
    sets = [L100] * 4 + [[("RANGE", "RL100.00000", 100.0)]] * 2
    arr, brk = _lb([110, 108, 100.5, 101.0, 100.6, 99.0], sets)
    assert arr == [2] and brk == [5]


def test_arriving_and_closing_through_in_the_same_hour_breaks_on_that_bar():
    arr, brk = _lb([110, 108, 99.3], [L100] * 3)
    assert arr == [2] and brk == [2]


def test_a_level_breaks_once():
    arr, brk = _lb([110, 108, 100.5, 99.0, 98.0, 97.0], [L100] * 6)
    assert brk == [3]


def test_moving_away_on_the_arrival_side_is_not_a_break():
    arr, brk = _lb([110, 108, 100.5, 103.0, 104.0], [L100] * 5)
    assert arr == [2] and brk == []


def test_from_below_a_close_above_breaks():
    arr, brk = _lb([90, 92, 99.5, 99.8, 100.7], [L100] * 5)
    assert arr == [2] and brk == [4]


def test_a_level_type_outside_the_firing_list_does_not_keep_the_watch():
    sets = [L100] * 4 + [[("H4", "H4x", 100.0)]] * 2      # only a 4-hour swing remains
    arr, brk = _lb([110, 108, 100.5, 101.0, 99.0, 98.0], sets)
    assert brk == []
