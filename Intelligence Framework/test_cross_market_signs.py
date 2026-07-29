"""
test_cross_market_signs.py

Locks Phase 4 cross-market fixes:
  * DXY bias is internally consistent — strong USD → BULLISH GBP/AUD, weak USD
    → BEARISH (was label-vs-note contradictory).
  * the fabricated 'BHP/iron ore' proxy (really AUD/USD reused) contributes
    NEUTRAL, no longer double-counting AUD.

Run: pytest test_cross_market_signs.py
"""
import pytest

from cross_market import _analyse_dxy, _analyse_bhp


@pytest.mark.parametrize("chg,expected", [
    (0.5, "BULLISH"), (0.2, "BULLISH"),
    (-0.5, "BEARISH"), (-0.2, "BEARISH"),
    (0.0, "NEUTRAL"), (None, "NEUTRAL"),
])
def test_dxy_sign_consistent(chg, expected):
    bias, note = _analyse_dxy(chg)
    assert bias == expected
    # the note must not contradict the label
    if bias == "BULLISH":
        assert "bearish" not in note.lower()
    if bias == "BEARISH":
        assert "bullish" not in note.lower()


@pytest.mark.parametrize("chg", [2.0, 0.5, 0.0, -0.5, -2.0, None])
def test_bhp_always_neutral(chg):
    bias, _ = _analyse_bhp(chg)
    assert bias == "NEUTRAL"
