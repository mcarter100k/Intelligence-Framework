"""
test_decision_invariants.py — system-level invariants over the live decision core.

Moved verbatim from shadow/test_integration_coherence.py when shadow/ was
removed (2026-09-29 audit): invariants 1-3 exercise LIVE modules
(apply_filter, get_official_decision, _classify), so they belong in the live
suite. The 738-case crash sweep is collapsed into one looped test — same
coverage, one reported result instead of an inflated count.
"""
import itertools

import pytest

from no_trade_filter import apply_filter
from official_decision import get_official_decision
from regime_detection import _classify


_REGIMES    = ["TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE", "UNAVAILABLE"]
_STRUCTURES = ["UPTREND", "DOWNTREND", "TRANSITIONAL"]
_INSTRUMENTS = ["GBP_AUD", "GBP_JPY"]


def _regime_dict(d1, h4, structure, adx_h4=28.0, atr=1.0,
                 lt_trend="RANGING", weekly="RANGING", exec_mode="CONTINUATION"):
    return {
        "regime_d1": d1, "regime_h4": h4, "adx_h4": adx_h4, "atr_vs_avg": atr,
        "atr_compression": False, "timeframe_conflict": False, "conflict_type": "",
        "structure": structure, "weekly_context": weekly, "lt_trend": lt_trend,
        "st_trend": lt_trend, "execution_mode": exec_mode, "size_mult": 1.0,
        "confidence": "HIGH",
    }


# ── INVARIANT 1: filter ↔ official decision are consistent for EVERY state ─────

@pytest.mark.parametrize("d1,h4,structure", itertools.product(_REGIMES, _REGIMES, _STRUCTURES))
def test_blocked_filter_always_means_no_trade(d1, h4, structure):
    regime = _regime_dict(d1, h4, structure)
    fr = apply_filter(regime)
    regime["filter_allowed"]   = fr.allowed
    regime["filter_mode"]      = fr.execution_mode
    regime["filter_size_mult"] = fr.size_mult
    regime["filter_reason"]    = fr.reason
    regime["override_fired"]   = fr.override_fired
    decision = get_official_decision(regime)

    # Core invariant: a blocked filter can ONLY produce NO TRADE.
    if not fr.allowed:
        assert decision["direction"] == "NO TRADE"

    # NO TRADE is always fully de-risked.
    if decision["direction"] == "NO TRADE":
        assert decision["conviction"] == 0
        assert decision["size_mult"] == 0.0

    # A tradeable decision is directional and carries real conviction.
    if decision["direction"] in ("LONG", "SHORT"):
        assert fr.allowed is True
        assert decision["conviction"] > 0
        assert decision["grade"] in ("A+", "A", "B+", "B", "C")


# ── INVARIANT 2: corrupt ATR NEVER trades, whatever else is set ────────────────

@pytest.mark.parametrize("bad_atr", [-5.0, 0.0, float("inf"), float("nan")])
@pytest.mark.parametrize("d1", ["TRENDING_UP", "TRENDING_DOWN"])
def test_corrupt_atr_never_trades(bad_atr, d1):
    regime = _regime_dict(d1, d1, "UPTREND" if "UP" in d1 else "DOWNTREND",
                          atr=bad_atr, lt_trend="UPTREND" if "UP" in d1 else "DOWNTREND",
                          weekly="ESTABLISHED_UPTREND" if "UP" in d1 else "ESTABLISHED_DOWNTREND")
    assert apply_filter(regime).allowed is False


# ── INVARIANT 3: classifier never trends on unconfirmed structure in 25–32 ─────

@pytest.mark.parametrize("adx", [25, 26, 28, 30, 31])
@pytest.mark.parametrize("slope", [+0.01, -0.01])
@pytest.mark.parametrize("inst", _INSTRUMENTS)
def test_no_slope_only_trend_in_transition_band(adx, slope, inst):
    # Transitional structure in the 25–32 band must never yield a trend label.
    result = _classify(adx, 1.0, slope, inst, structure="TRANSITIONAL")
    assert result == "VOLATILE"
def test_classify_never_crashes_and_returns_valid():
    # Exhaustive: classifier must always return a known label, never raise.
    valid = {"TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE"}
    for adx, atr, structure, inst, slope in itertools.product(
            range(5, 46), (0.5, 0.7, 1.0, 1.3, 1.6, 2.5), _STRUCTURES,
            _INSTRUMENTS, (+0.01, -0.01, 0.0)):
        r = _classify(adx, atr, slope, inst, structure=structure)
        assert r in valid, (adx, atr, structure, inst, slope, r)
