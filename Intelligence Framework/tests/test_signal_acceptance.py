"""
test_signal_acceptance.py

Acceptance tests proving the framework CAN produce tradeable long/short
signals (guards against "output paralysis"). Migrated from fm7.

Split by dependency:
  * Offline unit tests   — resolution table shape + apply_filter on clean
    trends + get_regime over fully-mocked OHLC.
  * Integration test     — the full get_decision_brief pipeline, which reaches
    live cross-market / currency-strength feeds; marked `integration` and
    deselected by default.

Run offline:      pytest test_signal_acceptance.py
Run everything:   pytest test_signal_acceptance.py -m integration
"""
import pandas as pd
import pytest
import unittest.mock as mock

import regime_detection as rd
from regime_detection import RESOLUTION_TABLE, get_regime
from no_trade_filter import apply_filter

_TRADEABLE_MODES = {"CONTINUATION", "PULLBACK_ENTRY", "FADE_EXTREMES", "REDUCED_MOMENTUM"}


# ── Resolution table can produce tradeable outputs ─────────────────────────────

def test_resolution_table_has_tradeable_combos():
    tradeable = [k for k, v in RESOLUTION_TABLE.items()
                 if v["execution_mode"] in _TRADEABLE_MODES]
    assert len(tradeable) >= 6


def test_continuation_combos_are_full_conviction():
    continuation = [v for v in RESOLUTION_TABLE.values()
                    if v["execution_mode"] == "CONTINUATION"]
    assert continuation, "no CONTINUATION combos in resolution table"
    for v in continuation:
        assert v["size_mult"] > 0
        assert v["confidence"] == "HIGH"


# ── Filter passes clean aligned trends ─────────────────────────────────────────

_CLEAN_LONG = {
    "regime_d1": "TRENDING_UP", "regime_h4": "TRENDING_UP", "adx_h4": 32.0,
    "atr_vs_avg": 1.05, "atr_compression": False, "atr_compression_note": "",
    "timeframe_conflict": False, "conflict_type": "", "structure": "UPTREND",
    "weekly_context": "ESTABLISHED_UPTREND", "lt_trend": "UPTREND",
    "st_trend": "UPTREND", "execution_mode": "CONTINUATION", "size_mult": 1.0,
    "confidence": "HIGH", "resolution_note": "",
}


def test_clean_uptrend_allowed():
    r = apply_filter(_CLEAN_LONG)
    assert r.allowed is True
    assert r.execution_mode == "CONTINUATION"
    assert r.size_mult == pytest.approx(1.0)
    assert r.confidence == "HIGH"


def test_clean_downtrend_allowed():
    clean_short = {
        **_CLEAN_LONG,
        "regime_d1": "TRENDING_DOWN", "regime_h4": "TRENDING_DOWN",
        "structure": "DOWNTREND", "weekly_context": "ESTABLISHED_DOWNTREND",
        "lt_trend": "DOWNTREND", "st_trend": "DOWNTREND",
    }
    r = apply_filter(clean_short)
    assert r.allowed is True
    assert r.execution_mode == "CONTINUATION"


# ── get_regime over synthetic clean uptrend (fully mocked feeds) ───────────────

def _mock_feeds():
    base = 1.85
    n = 220
    closes = [base + i * 0.0015 for i in range(n)]
    df_d1 = pd.DataFrame(
        {"High": [c + 0.0025 for c in closes], "Low": [c - 0.0025 for c in closes],
         "Close": closes, "Open": closes, "Volume": [1000] * n},
        index=pd.date_range("2025-01-01", periods=n, freq="B", tz="UTC"),
    )
    n_h4 = 120
    closes_h4 = [base + i * 0.0005 for i in range(n_h4)]
    df_h4 = pd.DataFrame(
        {"High": [c + 0.0010 for c in closes_h4], "Low": [c - 0.0010 for c in closes_h4],
         "Close": closes_h4, "Open": closes_h4, "Volume": [500] * n_h4},
        index=pd.date_range("2025-11-01", periods=n_h4, freq="4h", tz="UTC"),
    )
    n_w = 110
    closes_w = [base + i * 0.005 for i in range(n_w)]
    df_w = pd.DataFrame(
        {"High": [c + 0.010 for c in closes_w], "Low": [c - 0.010 for c in closes_w],
         "Close": closes_w, "Open": closes_w, "Volume": [2000] * n_w},
        index=pd.date_range("2023-01-01", periods=n_w, freq="W", tz="UTC"),
    )
    return df_d1, df_h4, df_w


def test_synthetic_uptrend_regime_tradeable():
    df_d1, df_h4, df_w = _mock_feeds()
    with mock.patch.object(rd, "_oanda_ok", return_value=True), \
         mock.patch("regime_detection._oanda_daily_bars", lambda *a, count=220, **k: df_d1.tail(count).copy()), \
         mock.patch("regime_detection._oanda_h4_bars", lambda *a, count=120, **k: df_h4.tail(count).copy()), \
         mock.patch("regime_detection._oanda_weekly_bars", lambda *a, count=110, **k: df_w.tail(count).copy()):
        regime = get_regime("GBP_AUD")

    assert regime.get("regime_d1") == "TRENDING_UP"
    assert not regime.get("stand_down", True)
    assert regime.get("filter_allowed", False)


# ── Full brief pipeline (reaches live feeds) — integration only ────────────────

@pytest.mark.integration
def test_full_brief_produces_long_on_clean_uptrend():
    from decision_brief import get_decision_brief

    df_d1, df_h4, df_w = _mock_feeds()
    with mock.patch.object(rd, "_oanda_ok", return_value=True), \
         mock.patch("regime_detection._oanda_daily_bars", lambda *a, count=220, **k: df_d1.tail(count).copy()), \
         mock.patch("regime_detection._oanda_h4_bars", lambda *a, count=120, **k: df_h4.tail(count).copy()), \
         mock.patch("regime_detection._oanda_weekly_bars", lambda *a, count=110, **k: df_w.tail(count).copy()):
        brief = get_decision_brief("GBP_AUD")

    assert brief.decision == "LONG"
    assert brief.conviction > 50
