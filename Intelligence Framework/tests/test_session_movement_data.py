"""Pins the pure helpers of studies/session_movement_data.py (Phase 1 of the
session movement study): H4 slot assignment across both DST regimes, the
H1 -> H4 aggregation, the weekly market window, the 21:00Z study day, and
gap detection. No network, no files."""
import os
import sys
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "studies"))
import session_movement_data as S  # noqa: E402

UTC = timezone.utc


def u(*a):
    return datetime(*a, tzinfo=UTC)


def test_h4_bucket_summer_and_winter():
    # Summer (EDT, UTC-4): slots open 21, 01, 05, 09, 13, 17 UTC
    assert S.h4_bucket(u(2010, 7, 6, 21)) == u(2010, 7, 6, 21)
    assert S.h4_bucket(u(2010, 7, 6, 23)) == u(2010, 7, 6, 21)
    assert S.h4_bucket(u(2010, 7, 7, 0)) == u(2010, 7, 6, 21)
    assert S.h4_bucket(u(2010, 7, 7, 1)) == u(2010, 7, 7, 1)
    assert S.h4_bucket(u(2010, 7, 7, 12)) == u(2010, 7, 7, 9)
    # Winter (EST, UTC-5): slots open 22, 02, 06, 10, 14, 18 UTC
    assert S.h4_bucket(u(2010, 1, 6, 22)) == u(2010, 1, 6, 22)
    assert S.h4_bucket(u(2010, 1, 7, 1)) == u(2010, 1, 6, 22)
    assert S.h4_bucket(u(2010, 1, 7, 2)) == u(2010, 1, 7, 2)
    assert S.h4_bucket(u(2010, 1, 7, 21)) == u(2010, 1, 7, 18)


def test_aggregate_takes_first_open_last_close_extremes():
    h1 = {u(2010, 7, 7, 1): (1.0, 1.5, 0.9, 1.2),
          u(2010, 7, 7, 2): (1.2, 1.8, 1.1, 1.3),
          u(2010, 7, 7, 3): (1.3, 1.4, 0.7, 1.35),
          u(2010, 7, 7, 4): (1.35, 1.6, 1.0, 1.4),
          u(2010, 7, 7, 5): (9.0, 9.0, 9.0, 9.0)}    # next slot
    agg = S.aggregate(h1)
    assert agg[u(2010, 7, 7, 1)] == (1.0, 1.8, 0.7, 1.4, 4)
    assert agg[u(2010, 7, 7, 5)] == (9.0, 9.0, 9.0, 9.0, 1)


def test_compare_reports_pips():
    agg = {u(2010, 7, 7, 1): (1.0, 1.0003, 0.9999, 1.0001, 4)}
    h4 = {u(2010, 7, 7, 1): (1.0, 1.0001, 0.9999, 1.0001)}
    assert S.compare(agg, h4, 0.0001)[u(2010, 7, 7, 1)] == (0.0, 2.0, 0.0, 0.0)


def test_market_window():
    assert not S.market_open(u(2010, 7, 10, 12))        # Saturday
    assert not S.market_open(u(2010, 7, 11, 20))        # Sun 16:00 NY
    assert S.market_open(u(2010, 7, 11, 21))            # Sun 17:00 NY (EDT)
    assert S.market_open(u(2010, 7, 9, 20))             # Fri 16:00 NY
    assert not S.market_open(u(2010, 7, 9, 21))         # Fri 17:00 NY
    assert not S.market_open(u(2010, 1, 10, 21))        # Sun 16:00 NY (EST)
    assert S.market_open(u(2010, 1, 10, 22))
    assert S.market_open(u(2010, 1, 8, 21))             # Fri 16:00 NY (EST)


def test_study_day_runs_21z_to_21z():
    assert S.study_day(u(2010, 7, 5, 21)) == date(2010, 7, 6)
    assert S.study_day(u(2010, 7, 6, 20)) == date(2010, 7, 6)
    assert S.study_day(u(2010, 7, 6, 0)) == date(2010, 7, 6)


def test_expected_hours_counts():
    assert len(S.expected_hours(date(2010, 7, 7))) == 24      # summer Wednesday
    assert len(S.expected_hours(date(2010, 7, 5))) == 24      # summer Monday: opens Sun 21Z
    assert len(S.expected_hours(date(2010, 1, 4))) == 23      # winter Monday: opens Sun 22Z
    assert len(S.expected_hours(date(2010, 1, 8))) == 24      # winter Friday to 21Z
    assert S.expected_hours(date(2010, 1, 9)) == [u(2010, 1, 8, 21)]   # winter Fri 21Z stub


def test_gaps_finds_runs_and_skips_weekend():
    lo, hi = u(2010, 7, 8, 0), u(2010, 7, 13, 0)
    every = [t for t in (lo + __import__("datetime").timedelta(hours=k) for k in range(120))
             if S.market_open(t)]
    assert S.gaps(every, lo, hi) == []                       # weekend closure is not a gap
    missing = {u(2010, 7, 8, 3), u(2010, 7, 8, 4), u(2010, 7, 12, 10)}
    have = [t for t in every if t not in missing]
    assert S.gaps(have, lo, hi) == [(u(2010, 7, 8, 3), 2), (u(2010, 7, 12, 10), 1)]
