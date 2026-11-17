"""GLS-1 H3 tercile helpers."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "studies"))
import gold_gls1_volatility as V  # noqa: E402


def test_tercile_cuts_split_nine_values_three_ways():
    cuts = V.terciles([9, 1, 5, 3, 7, 2, 8, 4, 6])
    assert cuts == (4, 7)
    assert [V.tercile(x, cuts) for x in (1, 3, 4, 6, 7, 9)] == ["low", "low", "mid", "mid", "high", "high"]
