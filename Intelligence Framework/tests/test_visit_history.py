"""
test_visit_history.py
─────────────────────
Pins owner rulings R1-R3 of 2026-11-18 (docs/specs/configuration_detector_spec.md
§14.1) on a level's touch and hold counts, as computed by
studies/ccd1_arrival_lastweek.history:

  R1  a touch is every continuous visit inside the 0.10 ATR band, not every
      ARRIVAL (the re-arm cooldown limits alerts, not the count)
  R2  a visit broke on a close 0.10 ATR or more beyond the level, the LEVEL
      BREAK rule, so "held" and "broke" never disagree about one close
  R3  "beyond" is judged from the side price approached from, and a visit's
      outcome never changes after it

Run: pytest tests/test_visit_history.py
"""
import os
import random
import sys
from datetime import datetime, timedelta, timezone

from _paths import ROOT

for _d in ("studies",):
    if os.path.join(ROOT, _d) not in sys.path:
        sys.path.insert(0, os.path.join(ROOT, _d))

import ccd1_arrival_calibration as A
import ccd1_arrival_lastweek as R

P, ATR = 100.0, 10.0               # band 99..101; break margin 1.0; re-arm 5.0
T0 = datetime(2026, 11, 2, tzinfo=timezone.utc)
LV = [("D1", "D1x", P)]

# (low, high, close) per hour
BARS = [
    (110, 112, 111),       # 0  far above
    (100.5, 103, 101.5),   # 1  enters the band from above: visit 1
    (99.6, 100.5, 99.71),  # 2  closes $0.29 through (0.029 ATR): sitting on it
    (102, 105, 104),       # 3  leaves (0.40 ATR away: never re-arms an ARRIVAL)
    (101.5, 103, 102),     # 4  still outside
    (100.8, 102, 101),     # 5  back in: visit 2, from above
    (98.5, 101, 99.0),     # 6  closes exactly 0.10 ATR through: broke
    (94, 98.5, 96),        # 7  outside, below
    (98.8, 100, 99.5),     # 8  back in from below: visit 3, a close under the level is not through
    (90, 92, 91),          # 9  far below
]


def _series(bars):
    return {"H1": {"t": [T0 + timedelta(hours=i) for i in range(len(bars))],
                   "L": [b[0] for b in bars], "H": [b[1] for b in bars], "C": [b[2] for b in bars]}}


def _hist(bars, t=None):
    s = _series(bars)
    return R.history(s, [(ATR, LV)] * len(bars), P, T0, len(bars) if t is None else t)


def test_counts_every_visit_not_every_arrival():
    s = _series(BARS)
    arrivals = R.fires_detail(s, [(ATR, LV)] * len(BARS), R.TOL, {"D1"})
    assert [t for t, _ in arrivals] == [1]              # the cooldown allows one alert
    assert [(v[0], v[1]) for v in _hist(BARS)] == [(1, 2), (5, 6), (8, 8)]   # three visits on the chart


def test_close_by_cents_holds_and_a_margin_close_breaks():
    vis = _hist(BARS)
    assert vis[0][3] is None                            # $0.29 through held (ruling Q1)
    assert vis[1][3] == 6                               # 0.10 ATR exactly is a break
    nudged = list(BARS)
    nudged[6] = (98.5, 101, 99.01)                      # 0.099 ATR through
    assert _hist(nudged)[1][3] is None


def test_judged_from_the_side_price_came_from():
    vis = _hist(BARS)
    assert [v[2] for v in vis] == [1, 1, -1]
    assert vis[2][3] is None                            # from below, a close under the level is not through
    flipped = list(BARS)
    flipped[8] = (98.8, 101.5, 101.2)                   # from below, 0.12 ATR above: broke
    assert _hist(flipped)[2][3] == 8


def test_an_outcome_is_never_revised():
    full = _hist(BARS)
    for t in range(1, len(BARS) + 1):
        for v in _hist(BARS, t):
            if v[1] < t - 1:                            # the visit had ended by then
                assert v in full, (t, v)
    later = BARS + [(130, 135, 133)] * 5 + [(60, 65, 62)] * 5   # price ends far on each side in turn
    assert _hist(later)[:3] == full


def test_held_and_broke_agree_with_level_break_on_a_long_series():
    rng = random.Random(20261118)
    c, bars = 120.0, []                                   # starts off the level: bar 0 has no earlier close
    for _ in range(4000):
        o, c = c, c + 0.05 * (P - c) + rng.gauss(0, 0.6)    # wanders, keeps coming back
        bars.append((min(o, c) - abs(rng.gauss(0, 0.3)), max(o, c) + abs(rng.gauss(0, 0.3)), c))
    s, sets = _series(bars), [(ATR, LV)] * len(bars)
    vis = R.history(s, sets, P, T0, len(bars))
    # every visit's first bar as an arrival, so LEVEL BREAK watches each visit
    breaks = A.level_breaks(s, sets, [(v[0], LV) for v in vis], {"D1"}, margin=A.BREAK_MARGIN)
    by_visit = {}
    for t, broke in breaks:
        for p, side, t0 in broke:
            by_visit[t0] = (t, side)
    held = broke_n = 0
    for first, last, side, b in vis:
        lb = by_visit.get(first)                        # each bar opens at the last close, so no gap
        assert (b, side if b is not None else None) == (lb or (None, None)), (first, last, b, lb)
        held += b is None
        broke_n += b is not None
    assert held >= 20 and broke_n >= 20, (held, broke_n)   # both outcomes exercised
