"""
test_outcome_log_hygiene.py

Locks Phase 5.3: the outcome log rejects impossible price scales, so the
synthetic pollution that once put GBP_JPY at 1.91 cannot recur.

Run: pytest test_outcome_log_hygiene.py
"""
import csv
import os

import pytest

import regime_classifier_logger as rcl


@pytest.mark.parametrize("instrument,price,ok", [
    ("GBP_JPY", 1.91, False),    # the historical pollution
    ("GBP_JPY", 217.77, True),
    ("GBP_JPY", 5.0, False),
    ("GBP_AUD", 1.9124, True),
    ("GBP_AUD", 213.0, False),   # AUD priced like a JPY cross
    ("GBP_AUD", 0.0, False),
    ("GBP_JPY", -1.0, False),
])
def test_price_plausible(instrument, price, ok):
    assert rcl._price_plausible(instrument, price) is ok


def test_log_regime_skips_impossible_price(tmp_path, monkeypatch):
    log = tmp_path / "regime_log.csv"
    monkeypatch.setattr(rcl, "LOG_FILE", str(log))
    # GBP_JPY at a GBP/AUD-scale price must not be written.
    rcl.log_regime({"regime": "RANGING", "current_price": 1.91}, "GBP_JPY")
    if os.path.exists(log):
        with open(log, newline="") as f:
            rows = list(csv.DictReader(f))
        assert rows == []
