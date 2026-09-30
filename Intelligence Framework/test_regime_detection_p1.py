"""
test_regime_detection_p1.py

Pytest suite for Problem 1 regime_detection.py behaviour. All cases here are
offline (pure logic + mocked OHLC) and preserve the exact T-numbered
expectations from the original hand-rolled runner (78 checks, all passing).

Sections:
  1. _classify()          — ADX zone boundary conditions
  2. PairConfig           — pip helpers and PAIRS dict
  3. get_regime()         — output contract (mocked OHLC, no live API)
  4. Regression           — new thresholds vs old logic
  5. Stand-down matrix    — apply_filter() as single stand-down authority

Run: pytest test_regime_detection_p1.py
"""
from datetime import timedelta

import pandas as pd
import pytest
import unittest.mock as mock

import regime_detection as rd
from regime_detection import (
    _classify,
    PAIRS,
    _DEFAULT_PAIR,
    get_regime,
)
from no_trade_filter import apply_filter


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 + 4 — _classify() ADX zone tests  (id, adx, atr, slope, instrument, expected)
# ═══════════════════════════════════════════════════════════════════════════════

# Fields: (id, adx, atr, slope, instrument, structure, expected)
# Cases outside the 25-32 band are structure-independent (TRANSITIONAL default).
# In the 25-32 band (Phase 1.4) TRENDING now requires structure confirmation.
CLASSIFY_CASES = [
    # T01 — below ranging threshold, normal ATR → RANGING
    ("T01", 10, 1.0, +0.01, "GBP_AUD", "TRANSITIONAL", "RANGING"),
    # T02 — below ranging threshold but ATR spike → VOLATILE
    ("T02", 10, 2.0, +0.01, "GBP_AUD", "TRANSITIONAL", "VOLATILE"),
    # T03 — mid ranging zone, negative slope → RANGING
    ("T03", 15, 1.0, -0.01, "GBP_AUD", "TRANSITIONAL", "RANGING"),
    # T04 — transition zone lower boundary (18) → VOLATILE
    ("T04", 18, 1.0, +0.01, "GBP_AUD", "TRANSITIONAL", "VOLATILE"),
    # T05 — mid transition zone → VOLATILE
    ("T05", 22, 1.0, +0.01, "GBP_AUD", "TRANSITIONAL", "VOLATILE"),
    # T06 — top of transition zone, negative slope → VOLATILE
    ("T06", 24, 1.0, -0.01, "GBP_AUD", "TRANSITIONAL", "VOLATILE"),
    # T07 — trending boundary (25) with CONFIRMED up-structure → TRENDING_UP
    ("T07", 25, 1.0, +0.01, "GBP_AUD", "UPTREND", "TRENDING_UP"),
    # T08 — mid trending zone, CONFIRMED down-structure → TRENDING_DOWN
    ("T08", 28, 1.0, -0.01, "GBP_AUD", "DOWNTREND", "TRENDING_DOWN"),
    # T09 — just below exhaustion, CONFIRMED up-structure → TRENDING_UP
    ("T09", 31, 1.0, +0.01, "GBP_AUD", "UPTREND", "TRENDING_UP"),
    # T10 — at exhaustion threshold → still TRENDING_UP (>=32 band, structure-independent)
    ("T10", 32, 1.0, +0.01, "GBP_AUD", "TRANSITIONAL", "TRENDING_UP"),
    # T11 — well above exhaustion, GBP_AUD → TRENDING_UP (never RANGING from exhaustion)
    ("T11", 40, 1.0, +0.01, "GBP_AUD", "TRANSITIONAL", "TRENDING_UP"),
    # T12 — GBP_JPY ADX=34: below JPY exhaustion (35), >=32 exhaustion band → TRENDING_UP
    ("T12", 34, 1.0, +0.01, "GBP_JPY", "TRANSITIONAL", "TRENDING_UP"),
    # T13 — GBP_JPY ADX=35: at JPY exhaustion → RANGING
    ("T13", 35, 1.0, +0.01, "GBP_JPY", "TRANSITIONAL", "RANGING"),
    # T14 — GBP_JPY ADX=45: above exhaustion → RANGING
    ("T14", 45, 1.0, +0.01, "GBP_JPY", "TRANSITIONAL", "RANGING"),
    # T15 — GBP_AUD ADX=35: AUD exhaustion is 32 not 35, JPY rule N/A → TRENDING_UP
    ("T15", 35, 1.0, +0.01, "GBP_AUD", "TRANSITIONAL", "TRENDING_UP"),
    # T30 — regression: ADX=22 GBP_AUD → VOLATILE (old code said TRENDING_UP)
    ("T30", 22, 1.0, +0.01, "GBP_AUD", "TRANSITIONAL", "VOLATILE"),
    # T31 — regression: ADX=36 GBP_JPY → RANGING (old code said TRENDING_UP)
    ("T31", 36, 1.0, +0.01, "GBP_JPY", "TRANSITIONAL", "RANGING"),
    # T32 — regression: ADX=17 GBP_AUD → RANGING (consistent)
    ("T32", 17, 1.0, +0.01, "GBP_AUD", "TRANSITIONAL", "RANGING"),
    # T33 — regression (critical): ADX=19 GBP_AUD → VOLATILE (old code said RANGING)
    ("T33", 19, 1.0, +0.01, "GBP_AUD", "TRANSITIONAL", "VOLATILE"),
    # ── Phase 1.4 structure gate in the 25-32 band ────────────────────────────
    # T42 — 25-32 with TRANSITIONAL structure → VOLATILE (no slope-only trend)
    ("T42", 28, 1.0, +0.01, "GBP_AUD", "TRANSITIONAL", "VOLATILE"),
    # T43 — 25-32 conflict: up-structure but down-slope → VOLATILE
    ("T43", 28, 1.0, -0.01, "GBP_AUD", "UPTREND", "VOLATILE"),
    # T44 — 25-32 conflict: down-structure but up-slope → VOLATILE
    ("T44", 28, 1.0, +0.01, "GBP_AUD", "DOWNTREND", "VOLATILE"),
]


@pytest.mark.parametrize(
    "cid,adx,atr,slope,inst,structure,expected",
    CLASSIFY_CASES,
    ids=[c[0] for c in CLASSIFY_CASES],
)
def test_classify_adx_zones(cid, adx, atr, slope, inst, structure, expected):
    assert _classify(adx, atr, slope, inst, structure=structure) == expected


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — PairConfig tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_pip_size_aud():
    assert PAIRS["GBP_AUD"].pip_size == pytest.approx(0.0001)


def test_pip_size_jpy():
    assert PAIRS["GBP_JPY"].pip_size == pytest.approx(0.01)


def test_to_pips_aud():
    assert PAIRS["GBP_AUD"].to_pips(0.0050) == pytest.approx(50.0)


def test_to_pips_jpy():
    assert PAIRS["GBP_JPY"].to_pips(0.50) == pytest.approx(50.0)


def test_from_pips_aud():
    assert PAIRS["GBP_AUD"].from_pips(50) == pytest.approx(0.005)


def test_from_pips_jpy():
    assert PAIRS["GBP_JPY"].from_pips(50) == pytest.approx(0.50)


def test_pairs_dict_keys():
    assert "GBP_AUD" in PAIRS
    assert "GBP_JPY" in PAIRS


def test_default_pair():
    assert _DEFAULT_PAIR == "GBP_AUD"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — get_regime() output contract (mocked OHLC, no live API)
# ═══════════════════════════════════════════════════════════════════════════════

REQUIRED_KEYS = {
    "regime": str, "regime_label": str, "regime_d1": str, "regime_h4": str,
    "timeframe_conflict": bool, "conflict_type": str, "stand_down": bool,
    "stand_down_reason": str, "trade_guidance": str, "adx": float,
    "adx_h4": float, "atr": float, "atr_pips": float, "atr_pct": float,
    "atr_vs_avg": float, "volatility": str, "vol_note": str,
    "current_price": float, "today_high": float, "today_low": float,
    "range_used": (int, float), "range_remaining": (int, float),
    "fuel_pct": (int, float), "fuel_label": str, "pair": str,
    "instrument": str, "adx_exhaustion": bool, "adx_exhaustion_note": str,
    "error": type(None),
}


def _uptrend(n, step, end_offset):
    closes = [1.8000 + i * 0.0010 for i in range(n)]
    end = pd.Timestamp.now(tz="UTC").floor("h") - end_offset
    # Fixed steps, not date_range(freq="W"): anchored weekly ranges snap to
    # Sundays and silently drop a bar.
    idx = pd.DatetimeIndex([end - (n - 1 - i) * step for i in range(n)])
    return pd.DataFrame({"High": [c + 0.0020 for c in closes],
                         "Low": [c - 0.0020 for c in closes],
                         "Close": closes}, index=idx)


@pytest.fixture(scope="module")
def mocked_regime():
    """get_regime('GBP_AUD') over a synthetic clean uptrend on EVERY timeframe.

    D1, H4 and weekly are all mocked. Before 2026-09-29 only D1 was, so the H4
    and weekly fetches reached live OANDA from the unit suite (the audit
    found 2 authenticated calls per run), and the contract cases asserted on
    synthetic D1 mixed with whatever the live market was doing.
    """
    with mock.patch("regime_detection._oanda_ok", return_value=True), \
         mock.patch("regime_detection._oanda_daily_bars",
                    return_value=_uptrend(100, timedelta(days=1), timedelta(days=5))), \
         mock.patch("regime_detection._oanda_h4_bars",
                    return_value=_uptrend(120, timedelta(hours=4), timedelta(hours=8))), \
         mock.patch("regime_detection._oanda_weekly_bars",
                    return_value=_uptrend(110, timedelta(weeks=1), timedelta(days=14))):
        return get_regime("GBP_AUD")


def test_mocked_regime_never_touched_the_network(mocked_regime):
    """Every timeframe was served by the mocks, so nothing is UNAVAILABLE:
    a real fetch would be blocked by conftest and show up here."""
    assert mocked_regime["regime_h4"] != "UNAVAILABLE"
    assert mocked_regime["lt_trend"] != "RANGING" or \
        mocked_regime["weekly_context"] != "RANGING"


@pytest.mark.parametrize("key,etype", list(REQUIRED_KEYS.items()), ids=list(REQUIRED_KEYS))
def test_regime_contract_keys(mocked_regime, key, etype):
    assert key in mocked_regime, f"key '{key}' missing from get_regime output"
    assert isinstance(mocked_regime[key], etype)


def test_regime_is_valid_enum(mocked_regime):
    assert mocked_regime.get("regime") in {
        "TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE", "UNKNOWN"
    }


def test_regime_adx_in_range(mocked_regime):
    assert 0 <= mocked_regime.get("adx", -1) <= 100


def test_regime_atr_vs_avg_positive(mocked_regime):
    assert mocked_regime.get("atr_vs_avg", 0) > 0


def test_regime_no_error(mocked_regime):
    assert mocked_regime.get("error") is None


def test_regime_display_name(mocked_regime):
    assert mocked_regime.get("pair") == "GBP/AUD"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Stand-down consistency matrix (apply_filter as single authority)
# ═══════════════════════════════════════════════════════════════════════════════

_CLEAN_LONG = {
    "regime_d1": "TRENDING_UP", "regime_h4": "TRENDING_UP", "adx_h4": 28.0,
    "atr_vs_avg": 1.0, "atr_compression": False, "timeframe_conflict": False,
    "conflict_type": "", "structure": "UPTREND",
    "weekly_context": "ESTABLISHED_UPTREND", "lt_trend": "UPTREND",
    "st_trend": "UPTREND", "execution_mode": "CONTINUATION",
    "size_mult": 1.0, "confidence": "HIGH",
}

FILTER_MATRIX = [
    ("T34", "Clean long — TRENDING_UP aligned", _CLEAN_LONG, True),
    ("T35", "D1 VOLATILE no override", {
        "regime_d1": "VOLATILE", "regime_h4": "RANGING", "adx_h4": 15.0,
        "atr_vs_avg": 1.0, "atr_compression": False, "timeframe_conflict": False,
        "conflict_type": "", "structure": "TRANSITIONAL",
        "weekly_context": "RANGING", "lt_trend": "RANGING", "st_trend": "RANGING",
        "execution_mode": "STAND_DOWN", "size_mult": 0.0, "confidence": "NONE",
    }, False),
    ("T36", "Counter-trend override", {
        "regime_d1": "VOLATILE", "regime_h4": "TRENDING_UP", "adx_h4": 28.0,
        "atr_vs_avg": 1.0, "atr_compression": False, "timeframe_conflict": False,
        "conflict_type": "", "structure": "UPTREND",
        "weekly_context": "ESTABLISHED_UPTREND", "lt_trend": "UPTREND",
        "st_trend": "UPTREND", "execution_mode": "STAND_DOWN",
        "size_mult": 0.0, "confidence": "NONE",
    }, True),
    ("T37", "Opposite trend conflict (D1_UP + H4_DOWN)", {
        "regime_d1": "TRENDING_UP", "regime_h4": "TRENDING_DOWN", "adx_h4": 26.0,
        "atr_vs_avg": 1.0, "atr_compression": False, "timeframe_conflict": True,
        "conflict_type": "TRENDING_UP__TRENDING_DOWN", "structure": "UPTREND",
        "weekly_context": "ESTABLISHED_UPTREND", "lt_trend": "UPTREND",
        "st_trend": "UPTREND", "execution_mode": "CONTINUATION",
        "size_mult": 1.0, "confidence": "HIGH",
    }, False),
    ("T38", "Extreme ATR spike 2.5x", {
        **_CLEAN_LONG, "atr_vs_avg": 2.5,
    }, False),
    ("T39", "ATR compression flag", {
        "regime_d1": "TRENDING_UP", "regime_h4": "TRENDING_UP", "adx_h4": 28.0,
        "atr_vs_avg": 0.7, "atr_compression": True,
        "atr_compression_note": "ATR compression — pre-intervention coil",
        "timeframe_conflict": False, "conflict_type": "", "structure": "UPTREND",
        "weekly_context": "ESTABLISHED_UPTREND", "lt_trend": "UPTREND",
        "st_trend": "UPTREND", "execution_mode": "CONTINUATION",
        "size_mult": 1.0, "confidence": "HIGH",
    }, False),
    ("T40", "Clean short — TRENDING_DOWN aligned", {
        "regime_d1": "TRENDING_DOWN", "regime_h4": "TRENDING_DOWN", "adx_h4": 27.0,
        "atr_vs_avg": 1.0, "atr_compression": False, "timeframe_conflict": False,
        "conflict_type": "", "structure": "DOWNTREND",
        "weekly_context": "ESTABLISHED_DOWNTREND", "lt_trend": "DOWNTREND",
        "st_trend": "DOWNTREND", "execution_mode": "CONTINUATION",
        "size_mult": 1.0, "confidence": "HIGH",
    }, True),
    ("T41", "Weekly misalignment — SHORT vs 20wk UPTREND", {
        "regime_d1": "TRENDING_DOWN", "regime_h4": "TRENDING_DOWN", "adx_h4": 27.0,
        "atr_vs_avg": 1.0, "atr_compression": False, "timeframe_conflict": False,
        "conflict_type": "", "structure": "DOWNTREND",
        "weekly_context": "ESTABLISHED_UPTREND", "lt_trend": "UPTREND",
        "st_trend": "UPTREND", "execution_mode": "CONTINUATION",
        "size_mult": 1.0, "confidence": "HIGH",
    }, False),
]


@pytest.mark.parametrize(
    "cid,label,scenario,expected_allowed",
    FILTER_MATRIX,
    ids=[c[0] for c in FILTER_MATRIX],
)
def test_filter_matrix(cid, label, scenario, expected_allowed):
    fr = apply_filter(scenario)
    assert fr.allowed is expected_allowed, label
    # stand_down is the exact inverse of allowed — anti-drift lock
    assert (not fr.allowed) is (not expected_allowed)
