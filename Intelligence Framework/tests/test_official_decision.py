"""
test_official_decision.py

Locks Phase 2.1 at the source: the official decision is filter-gated. A regime
the no-trade filter blocks (filter_allowed=False) can only ever yield NO TRADE,
so nothing downstream (notify) can surface it as a tradeable alert.

Run: pytest tests/test_official_decision.py
"""
from official_decision import get_official_decision


def test_filter_blocked_regime_is_no_trade():
    d = get_official_decision({
        "filter_allowed": False,
        "filter_reason": "Both timeframes VOLATILE — no edge",
    })
    assert d["direction"] == "NO TRADE"
    assert d["grade"] == "C"
    assert d["conviction"] == 0
    assert d["size_mult"] == 0.0


def test_allowed_trend_regime_is_tradeable():
    d = get_official_decision({
        "filter_allowed": True,
        "filter_mode": "CONTINUATION",
        "execution_mode": "CONTINUATION",
        "filter_size_mult": 1.0,
        "confidence": "HIGH",
        "regime_d1": "TRENDING_UP",
        "regime_h4": "TRENDING_UP",
        "structure": "UPTREND",
        "adx_h4": 28.0,
        "atr_vs_avg": 1.0,
        "resolution_note": "clean continuation",
    })
    assert d["direction"] == "LONG"
    assert d["grade"] in ("A+", "A", "B+", "B")
    assert d["conviction"] > 0


def test_range_mode_issues_no_automated_direction():
    # FADE_EXTREMES / range → direction NONE → NO TRADE (needs manual levels)
    d = get_official_decision({
        "filter_allowed": True,
        "filter_mode": "FADE_EXTREMES",
        "execution_mode": "FADE_EXTREMES",
        "filter_size_mult": 0.0,
        "confidence": "LOW",
        "regime_d1": "RANGING",
        "structure": "TRANSITIONAL",
    })
    assert d["direction"] == "NO TRADE"
