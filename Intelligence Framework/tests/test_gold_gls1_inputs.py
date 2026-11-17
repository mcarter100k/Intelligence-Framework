"""GLS-1 inputs: the structure-break entry and its stop (spec §3, §4.1)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "studies"))
import gold_gls1_inputs as I  # noqa: E402

L = [10, 9, 8, 7, 6, 7, 8, 9, 10, 11, 12, 13, 12, 11, 10, 9, 10, 11, 12, 13, 14, 15]
H = [x + 1 for x in L]
C = [x + 0.5 for x in L]


def test_swings_need_k_bars_each_side():
    hs, ls = I.swings(H, L)
    assert hs == [11] and ls == [4, 15]


def test_long_break_enters_at_first_close_above_confirmed_high_with_latest_low_as_stop():
    longs = [b for b in I.breaks_and_stops(H, L, C) if b[1] == 1]
    assert longs == [(20, 1, 5.5)]          # close 14.5 above swing high 14; stop at the 9 low


def test_short_side_is_the_mirror():
    shorts = [b for b in I.breaks_and_stops([-x for x in L], [-x for x in H], [-x for x in C]) if b[1] == -1]
    assert shorts == [(20, -1, 5.5)]


def test_unconfirmed_low_is_not_the_stop():
    # a new low at bar 19 is a swing only once bars 20-23 print, after the entry
    L2 = L[:19] + [8.6, 14, 15, 16, 17]
    H2 = [x + 1 for x in L2]
    C2 = [x + 0.5 for x in L2]
    longs = [b for b in I.breaks_and_stops(H2, L2, C2) if b[1] == 1]
    # bar 19's lower low (known by bar 19) stops bar 15 being a swing, so the stop is the
    # bar-4 low: 14.5 - 6 = 8.5. Using the unconfirmed bar-19 low would give 5.9.
    assert longs[0][0] == 20 and abs(longs[0][2] - 8.5) < 1e-9


def test_level_is_not_replaced_by_a_swing_high_that_is_not_yet_confirmed():
    # a higher swing high forms at bar 22 (confirmed at 26); at bar 20 the live level is still 14
    L3 = L[:20] + [14, 15, 16, 15, 14, 13, 12, 11]
    H3 = [x + 1 for x in L3]
    C3 = [x + 0.5 for x in L3]
    longs = [b for b in I.breaks_and_stops(H3, L3, C3) if b[1] == 1]
    assert longs[0][0] == 20
