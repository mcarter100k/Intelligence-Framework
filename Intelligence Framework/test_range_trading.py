"""
test_range_trading.py

Locks Phase 6.3: RANGING regimes now issue a fade-from-edge direction instead of
always NO TRADE. Only the outer edges trade; mid-range = no edge; never fade
against a strongly established weekly trend; range fades are reduced-grade.

Run: pytest test_range_trading.py
"""
import pytest

from official_decision import get_official_decision, _RANGE_EDGE


def _ranging_regime(range_position, lt_trend="RANGING", confidence="MEDIUM"):
    return {
        "filter_allowed":   True,
        "filter_mode":      "FADE_EXTREMES",
        "execution_mode":   "FADE_EXTREMES",
        "filter_size_mult": 0.75,
        "confidence":       confidence,
        "regime_d1":        "RANGING",
        "regime_h4":        "RANGING",
        "structure":        "TRANSITIONAL",
        "range_position":   range_position,
        "lt_trend":         lt_trend,
        "resolution_note":  "Clean range on both TFs — trade from edges only",
        "override_fired":   False,
        "adx_h4":           15.0,
        "atr_vs_avg":       1.0,
    }


def test_fade_long_at_support():
    d = get_official_decision(_ranging_regime(0.10))
    assert d["direction"] == "LONG"
    assert d["size_mult"] == pytest.approx(0.75)   # reduced size
    assert "Range fade" in d["reason"]


def test_fade_short_at_resistance():
    d = get_official_decision(_ranging_regime(0.90))
    assert d["direction"] == "SHORT"
    assert "Range fade" in d["reason"]


def test_mid_range_is_no_trade():
    d = get_official_decision(_ranging_regime(0.50))
    assert d["direction"] == "NO TRADE"


@pytest.mark.parametrize("pos", [0.0, _RANGE_EDGE, 1.0 - _RANGE_EDGE, 1.0])
def test_only_outer_edges_trade(pos):
    # Just inside the edge band trades; just outside it does not.
    d = get_official_decision(_ranging_regime(pos))
    assert d["direction"] in ("LONG", "SHORT")
    mid = get_official_decision(_ranging_regime(0.5))
    assert mid["direction"] == "NO TRADE"


def test_no_falling_knife_long_in_downtrend():
    # At support but the dominant weekly trend is DOWN — do not fade long.
    d = get_official_decision(_ranging_regime(0.10, lt_trend="DOWNTREND"))
    assert d["direction"] == "NO TRADE"


def test_no_fade_short_against_uptrend():
    d = get_official_decision(_ranging_regime(0.90, lt_trend="UPTREND"))
    assert d["direction"] == "NO TRADE"


def test_range_fade_is_reduced_grade():
    # Mean-reversion fade must not outrank a trend continuation (capped low).
    d = get_official_decision(_ranging_regime(0.10, confidence="MEDIUM"))
    assert d["conviction"] <= 55
    assert d["grade"] in ("B", "B+", "C")


def test_range_trade_needs_bounds():
    # No range_position available → cannot locate an edge → NO TRADE.
    regime = _ranging_regime(0.10)
    del regime["range_position"]
    d = get_official_decision(regime)
    assert d["direction"] == "NO TRADE"
