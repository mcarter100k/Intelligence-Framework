"""GLS-1 runner (docs/specs/gold_ltf_structure_spec.md v5): trades, selection,
structures, costs, buckets and pullback outcomes on controlled inputs."""
import os
import random
import sys
from datetime import datetime, timedelta, timezone

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "studies"))
sys.path.insert(0, ROOT)
import gold_ltf_structure_study as G  # noqa: E402
from entry_confirmation import _detect_engulfing  # noqa: E402

UTC = timezone.utc
T0 = datetime(2024, 3, 5, 15, 0, tzinfo=UTC)          # Tuesday 10:00 New York


def path(lows, highs=None, opens=None, closes=None):
    n = len(lows)
    highs = highs or [x + 1 for x in lows]
    opens = opens or [x + 0.5 for x in lows]
    closes = closes or [x + 0.5 for x in lows]
    ts = [T0 + i * timedelta(minutes=5) for i in range(n)]
    return G.Path(ts, opens, highs, lows, closes)


# ── trades ──

def test_stop_touch_exits_at_the_stop():
    p = path([100, 99, 97, 101], opens=[100.5, 99.5, 99.0, 101.5])   # bar 2 opens above the stop, trades through it
    tr = G.simulate(p, 1, T0, 100.0, 98.0, T0 + timedelta(hours=1))
    assert tr["stopped"] and abs(tr["r"] + 1) < 1e-12


def test_gap_through_the_stop_fills_at_the_open():
    p = path([100, 95], opens=[100.5, 96.0])
    tr = G.simulate(p, 1, T0, 100.0, 98.0, T0 + timedelta(hours=1))
    assert tr["stopped"] and abs(tr["r"] - (96.0 - 100.0) / 2.0) < 1e-12


def test_unstopped_trade_exits_at_the_last_close_before_the_exit_and_records_adverse_excursion():
    p = path([100, 99, 103, 104, 110])                  # the bar at +20 min opens at the exit: not held
    tr = G.simulate(p, 1, T0, 100.0, 97.0, T0 + timedelta(minutes=20))
    assert not tr["stopped"] and abs(tr["r"] - (104.5 - 100) / 3) < 1e-12 and abs(tr["mae"] - 1.0) < 1e-12


def test_short_is_the_mirror():
    p = path([100, 101, 103], highs=[101, 102, 104.5])
    tr = G.simulate(p, -1, T0, 102.0, 104.0, T0 + timedelta(hours=1))
    assert tr["stopped"] and abs(tr["r"] + 1) < 1e-12


def test_worked_needs_the_target_before_the_stop_and_a_bar_doing_both_counts_the_stop():
    p = path([100, 101, 102], highs=[101, 102, 106])
    assert G.worked(p, 1, T0, 100.0, 98.0, 105.0, T0 + timedelta(hours=1))
    p2 = path([100, 97], highs=[101, 106])
    assert not G.worked(p2, 1, T0, 100.0, 98.0, 105.0, T0 + timedelta(hours=1))


def test_missed_entry_counts_zero_per_setup():
    S = [object(), object()]
    net = {(id(S[0]), "M5", 1): {"x": 2.0}}
    assert G.per_setup(S, "M5", 1, "x", net) == [2.0, 0.0]


def test_wait_buckets_have_the_ruled_edges():
    assert [G.bucket(w) for w in (1, 2, 3, 6, 7, 12, 13, 61)] == ["1", "2", "3-6", "3-6", "7-12", "7-12", "13+", "13+"]


def test_tercile_cut_offs_are_the_spec_values():
    assert G.VOL_CUTS == (1.206, 1.480) and G.USD_CUTS == (23.89, 34.78)
    assert [G.tercile(x, G.VOL_CUTS) for x in (1.2, 1.206, 1.48)] == ["low", "mid", "high"]


# ── structures ──

def test_engulfing_matches_the_live_detector_on_random_bars():
    rnd = random.Random(7)
    O, H, L, C = [], [], [], []
    for _ in range(400):
        o = 100 + rnd.uniform(-2, 2)
        c = o + rnd.uniform(-2, 2)
        O.append(o); C.append(c); H.append(max(o, c) + rnd.uniform(0, 1)); L.append(min(o, c) - rnd.uniform(0, 1))
    occ = G._structures({"O": O, "H": H, "L": L, "C": C})
    up, down = set(occ.get(("engulfing", 1), [])), set(occ.get(("engulfing", -1), []))
    for i in range(1, 400):
        d = _detect_engulfing(H[i - 1:i + 1], L[i - 1:i + 1], O[i - 1:i + 1], C[i - 1:i + 1])
        assert (i in up) == (d["direction"] == "LONG") and (i in down) == (d["direction"] == "SHORT")


def test_pin_bar_needs_a_long_lower_wick_and_a_range_at_least_the_median():
    n = 20
    O, C = [100.0] * n, [100.2] * n
    H, L = [100.5] * n, [99.5] * n
    O[-1], C[-1], H[-1], L[-1] = 100.0, 100.1, 100.2, 97.0           # wick 3.0 of range 3.2
    occ = G._structures({"O": O, "H": H, "L": L, "C": C})
    assert n - 1 in occ.get(("pin bar", 1), [])
    assert n - 1 not in occ.get(("pin bar", -1), [])


def test_double_bottom_completes_on_the_close_above_the_neckline():
    lows = [110, 109, 108, 107, 106, 100, 106, 107, 108, 109, 108, 107, 106, 100.2, 106, 107, 108, 109, 110,
            111, 112, 113, 114, 115]
    H = [x + 1 for x in lows]
    C = [x + 0.5 for x in lows]
    mr = np.full(len(lows), 1.0)
    d = G.detect([x + 0.5 for x in lows], H, lows, C, mr)
    neck = max(H[5:14])                                  # 110
    first_above = next(j for j in range(13 + 4 + 1, len(C)) if C[j] > neck)
    assert d["double bottom / top"] == [first_above]


def test_consolidation_resolves_by_the_side_of_the_breaking_close():
    # earlier bars range 2.0, so the median range is 2.0; a 12-bar box spanning 3.0 qualifies at
    # 2.0 median ranges (limit 4.0) and would not at 1.0 (limit 2.0)
    H = [101.0, 105.0] * 15 + [102.0] * 12 + [104.0]     # zigzag first: no earlier 12 bars qualify
    L = [99.0, 103.0] * 15 + [99.0] * 12 + [101.5]
    C = [100.0] * 42 + [103.0]
    mr = G.median_range(H, L)
    assert G.consolidations(H, L, C, mr) == [(42, 1)]
    # bars ranging 2.0 that zigzag (any 12 span 6.0), then a box spanning 5.5: nothing within 4.0
    H2 = [101.0, 105.0] * 15 + [104.5] * 12 + [106.0]
    L2 = [99.0, 103.0] * 15 + [99.0] * 12 + [105.0]
    assert G.consolidations(H2, L2, [100.0] * 42 + [105.5], G.median_range(H2, L2)) == []


def test_retest_held_and_failed():
    # swing high at 5 (H 106); break at 10; retest at 11 closes above (held)
    L = [100, 101, 102, 103, 104, 105, 104, 103, 102, 103, 106.5, 105.5, 108, 109]
    H = [x + 1 for x in L]
    C = [x + 0.5 for x in L]
    C[11] = 106.5                                         # touches 106 and closes above
    d = G.detect([x + 0.5 for x in L], H, L, C, np.full(len(L), 1.0))
    assert d["retest held"] == [11] and not d["retest failed"]


# ── costs ──

def test_cfd_financing_both_pay_and_the_short_receive_side_result():
    t1 = T0 + timedelta(days=1, hours=2)                # holds Tuesday's roll: 1 night
    long_ = G.cfd_cost(1, T0, t1, 2000.0, 5.0, 0.0, 0.0)
    short_ = G.cfd_cost(-1, T0, t1, 2000.0, 5.0, 0.0, 0.0)
    recv = G.cfd_cost(-1, T0, t1, 2000.0, 5.0, 0.0, 0.0, short_receives=True)
    assert abs(long_ - 2000 * 0.075 / 365) < 1e-9
    assert abs(short_ - 2000 * 0.025 / 365) < 1e-9
    assert abs(recv + 2000 * 0.025 / 365) < 1e-9          # a credit when the rate is above the markup


def test_cfd_spread_is_half_each_way_and_the_break_hour_uses_the_reopen():
    assert abs(G.cfd_cost(1, T0, T0 + timedelta(hours=1), 2000.0, 0.0, 0.4, 0.6) - 0.5) < 1e-12
    table = {(2024, 15): 0.43}
    t = datetime(2024, 3, 5, 22, 10, tzinfo=UTC)         # 2:10 PM PT
    assert G.spread_at(table, t) == 0.43


def test_futures_carry_is_paid_by_longs_and_received_by_shorts_with_no_markup():
    t1 = T0 + timedelta(days=2)
    lc = G.futures_cost(1, T0, t1, 2000.0, 5.0)
    sc = G.futures_cost(-1, T0, t1, 2000.0, 5.0)
    fixed = G.TICK + 2 * G.COMM
    carry = 2000 * 0.05 * 2 / 365
    assert abs(lc - (fixed + carry)) < 1e-9 and abs(sc - (fixed - carry)) < 1e-9
    assert abs(G.futures_cost(1, T0, t1, 2000.0, 5.0, carry=False) - fixed) < 1e-12


def test_a_roll_is_charged_once_when_the_hold_spans_the_25th():
    a = datetime(2024, 3, 22, 15, 0, tzinfo=UTC)
    assert G.rolls_between(a, a + timedelta(days=6)) == 1
    assert G.rolls_between(a, a + timedelta(days=2)) == 0
    assert G.rolls_between(datetime(2024, 4, 1, tzinfo=UTC), datetime(2024, 4, 20, tzinfo=UTC)) == 0


# ── pullbacks ──

def test_pullback_outcome_counts_a_bar_doing_both_as_reversed():
    H = [105, 104, 111]
    L = [102, 101, 100.0]                                  # touches A exactly on the bar that also makes a new high
    assert G.pullback_outcome(H, L, 100.0, 110.0, 0) == "reversed"
    assert G.pullback_outcome([105, 111], [102, 103], 100.0, 110.0, 0) == "continued"
    assert G.pullback_outcome([105, 106], [102, 103], 100.0, 110.0, 0) == "unresolved"


def test_drift_baseline_for_down_is_the_negated_up_baseline():
    src = open(os.path.join(ROOT, "studies", "gold_ltf_structure_study.py")).read()
    assert "base_v[h][-1] = ([-x for x in up[h][0]],)" in src
