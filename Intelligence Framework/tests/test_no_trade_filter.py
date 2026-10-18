"""
test_no_trade_filter.py

Corruption and safety-gate tests for apply_filter() — the single stand-down
authority. These assert the ACTUAL contract (FilterResult.allowed), unlike the
original fm1 runner which checked a non-existent `.decision` attribute and so
passed every case vacuously.

Core safety invariant: corrupt / degenerate / missing regime data must always
resolve to allowed=False (stand aside), never to a live trade.

Run: pytest tests/test_no_trade_filter.py
"""
import math

import pytest

from no_trade_filter import apply_filter, FilterResult


# A minimal well-formed clean-uptrend regime, used as a base to corrupt one
# field at a time.
def _clean_long(**overrides):
    base = {
        "regime_d1": "TRENDING_UP", "regime_h4": "TRENDING_UP", "adx_h4": 28.0,
        "atr_vs_avg": 1.0, "atr_compression": False, "timeframe_conflict": False,
        "conflict_type": "", "structure": "UPTREND",
        "weekly_context": "ESTABLISHED_UPTREND", "lt_trend": "UPTREND",
        "st_trend": "UPTREND", "execution_mode": "CONTINUATION",
        "size_mult": 1.0, "confidence": "HIGH", "resolution_note": "",
        "atr_compression_note": "",
    }
    base.update(overrides)
    return base


# ── Corrupt / missing structure must never crash and must stand aside ──────────

def test_empty_dict_stands_aside():
    r = apply_filter({})
    assert isinstance(r, FilterResult)
    assert r.allowed is False


def test_all_none_values_stand_aside():
    keys = [
        "regime_d1", "regime_h4", "adx_h4", "atr_vs_avg", "atr_compression",
        "timeframe_conflict", "conflict_type", "structure", "weekly_context",
        "lt_trend", "st_trend", "execution_mode", "size_mult", "confidence",
    ]
    r = apply_filter({k: None for k in keys})
    assert r.allowed is False


# ── ATR sanity: corrupt volatility reads must stand aside (Phase 0.3) ──────────
# A clean-uptrend regime that WOULD trade is corrupted only in atr_vs_avg.

@pytest.mark.parametrize("bad_atr", [-5.0, -0.01, 0.0], ids=["neg5", "neg_small", "zero"])
def test_nonpositive_atr_stands_aside(bad_atr):
    # Negative or zero ATR ratio is physically impossible — corrupt data.
    r = apply_filter(_clean_long(atr_vs_avg=bad_atr))
    assert r.allowed is False, f"atr_vs_avg={bad_atr} must not produce a live trade"


@pytest.mark.parametrize("bad_atr", [math.inf, math.nan], ids=["inf", "nan"])
def test_nonfinite_atr_stands_aside(bad_atr):
    r = apply_filter(_clean_long(atr_vs_avg=bad_atr))
    assert r.allowed is False, f"atr_vs_avg={bad_atr} must not produce a live trade"


def test_extreme_finite_spike_stands_aside():
    # A large but finite spike is a legitimate stand-aside (not "corrupt").
    r = apply_filter(_clean_long(atr_vs_avg=2.5))
    assert r.allowed is False


def test_clean_regime_still_trades():
    # Guard against over-blocking: a normal ATR must remain tradeable.
    r = apply_filter(_clean_long(atr_vs_avg=1.05))
    assert r.allowed is True
