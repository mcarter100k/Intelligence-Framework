"""
test_range_trading.py

Range trading is GATED OFF (RANGE_TRADING_ENABLED=False) pending team review +
validation. These tests lock two things:
  * With the gate OFF (default/production), a detected range candidate returns
    NO TRADE with the "disabled pending review" reason.
  * With the gate patched ON, the underlying fade-from-edge logic still behaves
    (outer edges only, mid-range = no edge, no fading against the weekly trend,
    reduced grade) — so the logic is preserved for when it passes review.

Run: pytest test_range_trading.py
"""
import pytest

import official_decision as od
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


# ── Gate OFF (default / production) ────────────────────────────────────────────

def test_gate_is_off_by_default():
    assert od.RANGE_TRADING_ENABLED is False


@pytest.mark.parametrize("pos", [0.10, 0.90])
def test_range_candidate_is_disabled_no_trade(pos):
    d = get_official_decision(_ranging_regime(pos))
    assert d["direction"] == "NO TRADE"
    assert "disabled pending" in d["reason"].lower()


# ── Gate ON (logic preserved for post-review) ──────────────────────────────────

@pytest.fixture
def gate_on(monkeypatch):
    monkeypatch.setattr(od, "RANGE_TRADING_ENABLED", True)


def test_fade_long_at_support(gate_on):
    d = get_official_decision(_ranging_regime(0.10))
    assert d["direction"] == "LONG"
    assert d["size_mult"] == pytest.approx(0.75)
    assert "Range fade" in d["reason"]


def test_fade_short_at_resistance(gate_on):
    d = get_official_decision(_ranging_regime(0.90))
    assert d["direction"] == "SHORT"


def test_mid_range_is_no_trade(gate_on):
    assert get_official_decision(_ranging_regime(0.50))["direction"] == "NO TRADE"


def test_no_falling_knife_long_in_downtrend(gate_on):
    d = get_official_decision(_ranging_regime(0.10, lt_trend="DOWNTREND"))
    assert d["direction"] == "NO TRADE"


def test_no_fade_short_against_uptrend(gate_on):
    d = get_official_decision(_ranging_regime(0.90, lt_trend="UPTREND"))
    assert d["direction"] == "NO TRADE"


def test_range_fade_is_reduced_grade(gate_on):
    d = get_official_decision(_ranging_regime(0.10, confidence="MEDIUM"))
    assert d["conviction"] <= 55
    assert d["grade"] in ("B", "B+", "C")


def test_range_trade_needs_bounds(gate_on):
    regime = _ranging_regime(0.10)
    del regime["range_position"]
    assert get_official_decision(regime)["direction"] == "NO TRADE"
