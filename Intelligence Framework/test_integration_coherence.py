"""
test_integration_coherence.py

DEEP / INTEGRATION testing — system-level invariants, not single fixes.

Two tracks:
  * Offline invariant sweeps (default): exhaustive grids through the decision
    core and classifier, asserting properties that must hold for EVERY input.
  * Live coherence (marked `integration`): full build_market_report on both
    instruments, asserting the trader-facing output is internally consistent.

Run offline:  pytest test_integration_coherence.py
Run live:     pytest test_integration_coherence.py -m integration
"""
import itertools

import pytest

from no_trade_filter import apply_filter
from official_decision import get_official_decision
from regime_detection import _classify, PAIRS

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


@pytest.mark.parametrize("adx", list(range(5, 46)))
@pytest.mark.parametrize("atr", [0.5, 0.7, 1.0, 1.3, 1.6, 2.5])
@pytest.mark.parametrize("structure", _STRUCTURES)
def test_classify_never_crashes_and_returns_valid(adx, atr, structure):
    # Exhaustive: classifier must always return a known label, never raise.
    for inst in _INSTRUMENTS:
        for slope in (+0.01, -0.01, 0.0):
            r = _classify(adx, atr, slope, inst, structure=structure)
            assert r in {"TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE"}


# ── LIVE COHERENCE (integration) — full pipeline on both instruments ───────────

@pytest.mark.integration
@pytest.mark.parametrize("instrument", _INSTRUMENTS)
def test_live_report_is_internally_coherent(instrument):
    from market_brain import build_market_report
    report = build_market_report("auto", instrument)
    if report.get("market_closed"):
        pytest.skip("market closed")

    decision = report["decision"]

    # (a) decision internal consistency
    if decision["direction"] == "NO TRADE":
        assert decision["conviction"] == 0
        assert float(decision.get("size_mult", 0) or 0) == 0.0

    # (b) setup/grade no longer defaulted away
    assert "setup" in report and report["setup"]
    assert "primary_state" in report

    # (c) instrument-correct signals — currency strength scores THIS pair
    cs = report["layers"]["currency_strength"]
    if cs.get("error") is None:
        assert {cs.get("base"), cs.get("quote")} == set(instrument.split("_"))

    # (d) cross-market model only applied to GBP/AUD; neutral elsewhere
    xm = report["layers"]["cross_market"]
    if instrument != "GBP_AUD":
        assert xm.get("not_modelled") is True
        assert xm.get("overall_bias") == "NEUTRAL"

    # (e) H4 availability is surfaced
    assert "h4_available" in report["layers"]["regime"]


@pytest.mark.integration
@pytest.mark.parametrize("instrument", _INSTRUMENTS)
def test_live_no_impossible_prices(instrument):
    from market_brain import build_market_report
    report = build_market_report("auto", instrument)
    if report.get("market_closed"):
        pytest.skip("market closed")
    price = report["layers"]["liquidity"].get("current_price")
    if price:
        if "JPY" in instrument:
            assert price > 10, "JPY cross priced like GBP/AUD"
        else:
            assert price < 50, "GBP/AUD priced like a JPY cross"


@pytest.mark.integration
def test_live_notify_surface_matches_official_decision():
    # The alert a trader sees must equal report["decision"] (one source).
    import notify
    from market_brain import build_market_report
    report = build_market_report()  # GBP/AUD production default
    if report.get("market_closed"):
        pytest.skip("market closed")
    result = notify._run_framework()
    assert result["grade"] == report["decision"]["grade"]
    assert result["direction"] == report["decision"]["direction"]
