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
