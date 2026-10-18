"""
test_h4_outage.py

Locks Phase 2.4: a silent H4 data outage must NOT inherit D1 and manufacture a
full-size, HIGH-confidence multi-timeframe signal. On outage the regime stands
down and flags h4_available=False.

Run: pytest tests/test_h4_outage.py
"""
import pandas as pd
import pytest
import unittest.mock as mock

import regime_detection as rd
from regime_detection import get_regime


def _clean_uptrend_d1(n=220):
    base = 1.85
    closes = [base + i * 0.0015 for i in range(n)]
    return pd.DataFrame(
        {"High": [c + 0.0025 for c in closes], "Low": [c - 0.0025 for c in closes],
         "Close": closes, "Open": closes, "Volume": [1000] * n},
        index=pd.date_range("2025-01-01", periods=n, freq="B", tz="UTC"),
    )


def _weekly_uptrend(n=110):
    base = 1.85
    closes = [base + i * 0.005 for i in range(n)]
    return pd.DataFrame(
        {"High": [c + 0.010 for c in closes], "Low": [c - 0.010 for c in closes],
         "Close": closes, "Open": closes, "Volume": [2000] * n},
        index=pd.date_range("2023-01-01", periods=n, freq="W", tz="UTC"),
    )


@pytest.mark.parametrize("h4_return", [None, pd.DataFrame()], ids=["fetch_none", "empty_df"])
def test_h4_outage_stands_down(h4_return):
    d1 = _clean_uptrend_d1()
    wk = _weekly_uptrend()
    with mock.patch.object(rd, "_oanda_ok", return_value=True), \
         mock.patch("regime_detection._oanda_daily_bars", lambda *a, count=220, **k: d1.tail(count).copy()), \
         mock.patch("regime_detection._oanda_h4_bars", lambda *a, **k: h4_return), \
         mock.patch("regime_detection._oanda_weekly_bars", lambda *a, count=110, **k: wk.tail(count).copy()):
        regime = get_regime("GBP_AUD")

    # D1 is a clean uptrend, but with no H4 we must NOT claim confirmation.
    assert regime.get("h4_available") is False
    assert regime.get("regime_h4") == "UNAVAILABLE"
    assert regime.get("execution_mode") == "STAND_DOWN"
    assert regime.get("filter_allowed") is False
    # And crucially: not a full-size HIGH-confidence signal.
    assert regime.get("confidence") != "HIGH"
    assert float(regime.get("size_mult", 0.0) or 0.0) == 0.0
