"""Pins the helpers of studies/session_movement_study.py to
docs/specs/session_movement_study_spec.md: block tiling, hour index, the
earliest-bar tie rule, block shares, the Q4 thresholds, the fold-bar set,
the boundary-step and evenness readings, and the ATR copy against the live
regime_detection.compute_atr_series. Synthetic data only; no files, no network."""
import os
import random
import sys
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "studies"))
import session_movement_study as M  # noqa: E402
import history_study_convert as C  # noqa: E402
from regime_detection import compute_atr_series  # noqa: E402

UTC = timezone.utc


def u(*a):
    return datetime(*a, tzinfo=UTC)


def test_blocks_tile_the_day_without_overlap():
    names = [M.block_of(u(2010, 7, 7, h)) for h in range(24)]
    assert names.count("SYDNEY") == 3 and names.count("TOKYO") == 7
    assert names.count("LONDON") == 5 and names.count("LDN_NY") == 4 and names.count("NY_PM") == 5
    assert M.block_of(u(2010, 7, 7, 21)) == "SYDNEY"
    assert M.block_of(u(2010, 7, 7, 0)) == "TOKYO"
    assert M.block_of(u(2010, 7, 7, 6)) == "TOKYO"
    assert M.block_of(u(2010, 7, 7, 7)) == "LONDON"
    assert M.block_of(u(2010, 7, 7, 12)) == "LDN_NY"
    assert M.block_of(u(2010, 7, 7, 16)) == "NY_PM"
    assert M.block_of(u(2010, 7, 7, 20)) == "NY_PM"


def test_hour_index_starts_at_21z():
    assert M.hour_index(u(2010, 7, 6, 21)) == 0
    assert M.hour_index(u(2010, 7, 7, 2)) == 5
    assert M.hour_index(u(2010, 7, 7, 3)) == 6
    assert M.hour_index(u(2010, 7, 7, 20)) == 23


def _day(highs, lows, start=u(2010, 7, 6, 21)):
    times = [start + timedelta(hours=k) for k in range(len(highs))]
    return times, {t: (0.0, h, l, 0.0) for t, h, l in zip(times, highs, lows)}


def test_day_stats_earliest_tie_and_block_ranges():
    highs = [1.0] * 24
    lows = [0.9] * 24
    highs[4] = highs[15] = 1.5          # tie: hour 4 (TOKYO, 01Z) wins over hour 15 (12Z)
    lows[10] = 0.5                      # hour 10 = 07Z, LONDON
    times, bars = _day(highs, lows)
    s = M.day_stats(times, bars, 0.1)
    assert s["hbar"] == times[4] and M.block_of(s["hbar"]) == "TOKYO"
    assert s["lbar"] == times[10] and M.block_of(s["lbar"]) == "LONDON"
    assert abs(s["R"] - 10.0) < 1e-9
    assert abs(s["blocks"]["TOKYO"] - 6.0) < 1e-9          # 1.5 - 0.9
    assert abs(s["blocks"]["LONDON"] - 5.0) < 1e-9         # 1.0 - 0.5
    assert abs(s["blocks"]["LDN_NY"] - 6.0) < 1e-9         # 1.5 - 0.9
    assert abs(s["blocks"]["SYDNEY"] - 1.0) < 1e-9


def test_q4_threshold_is_strict():
    stats = [{"hbar": u(2010, 7, 7, 2), "lbar": u(2010, 7, 7, 3)},     # idx 5 and 6
             {"hbar": u(2010, 7, 7, 8), "lbar": u(2010, 7, 7, 15)}]    # idx 11 and 18
    assert M.q4_shares(stats, "hbar") == {6: 50.0, 12: 100.0, 18: 100.0}
    assert M.q4_shares(stats, "lbar") == {6: 0.0, 12: 50.0, 18: 50.0}


def test_block_pct_and_same_block():
    stats = [{"hbar": u(2010, 7, 7, 8), "lbar": u(2010, 7, 7, 9)},
             {"hbar": u(2010, 7, 7, 1), "lbar": u(2010, 7, 7, 13)}]
    hp = M.block_pct(stats, "hbar")
    assert hp["LONDON"] == 50.0 and hp["TOKYO"] == 50.0 and sum(hp.values()) == 100.0
    assert M.same_block_pct(stats) == 50.0


def test_steps_and_even_ratio():
    means = {h: 10.0 for h in range(24)}
    means[7] = 20.0
    st = M.steps(means)
    assert st[7] == 2.0 and st[12] == 1.0 and st[0] == 1.0
    assert M.even_ratio(means) == 2.0


def test_atr_copy_matches_live_function():
    rng = random.Random(3)
    c = [1.5]
    for _ in range(199):
        c.append(c[-1] + rng.uniform(-0.01, 0.01))
    h = [x + rng.uniform(0, 0.005) for x in c]
    lo = [x - rng.uniform(0, 0.005) for x in c]
    assert M.atr_series(h, lo, c) == compute_atr_series(h, lo, c)


def test_atr_by_bar_alignment():
    ts = [u(2010, 7, 7) + timedelta(hours=k) for k in range(20)]
    bars = {t: (1.0, 1.0 + 0.001 * k, 1.0, 1.0) for k, t in enumerate(ts)}
    a = M.atr_by_bar(bars)
    assert min(a) == ts[14] and len(a) == 6


def test_fold_bars_marks_target_first_bar_only():
    # Sunday-session H1 (Sun 10:00 NY) folds into Monday's first H1 (Sun 17:00 NY).
    sun = u(2010, 7, 11, 14)                 # Sun 10:00 EDT -> session Sunday
    mon0 = u(2010, 7, 11, 21)                # Sun 17:00 EDT -> session Monday
    mon1 = u(2010, 7, 11, 22)
    h1 = {sun: (1, 2, 0.5, 1), mon0: (1, 1.1, 0.9, 1), mon1: (1, 1.2, 0.95, 1.1)}
    d1 = {u(2010, 7, 10, 21): (1, 2, 0.5, 1), mon0: (1, 1.2, 0.9, 1.1)}
    _, h1c, log = C.convert(d1, h1)
    assert M.fold_bars(h1, log) == {mon0}
    assert h1c[mon0] == (1, 2, 0.5, 1)       # folded: Sunday open/high/low, own close


def test_group_days_and_completeness():
    # Summer Wednesday 2010-07-07: 24 bars from Tue 21:00Z
    ts = [u(2010, 7, 6, 21) + timedelta(hours=k) for k in range(24)]
    bars = {t: (1, 1, 1, 1) for t in ts}
    days = M.group_days(bars)
    assert list(days) == [date(2010, 7, 7)]
    assert M.is_complete(date(2010, 7, 7), days[date(2010, 7, 7)])
    assert not M.is_complete(date(2010, 7, 7), days[date(2010, 7, 7)][1:])
