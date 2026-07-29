"""
test_regime_structure.py

Extreme-input robustness for _detect_structure() — the pivot-based structure
detector. Degenerate price data (zeros, NaNs, spikes, negatives) must never
raise and must return a well-formed structure dict. Offline, pure logic.

Migrated from the fm1 corruption runner (which asserted nothing).

Run: pytest test_regime_structure.py
"""
import math

import pytest

from regime_detection import _detect_structure

_VALID_STRUCTURE = {"UPTREND", "DOWNTREND", "TRANSITIONAL"}


def _spike_series():
    closes = [1.9 + i * 0.001 for i in range(50)]
    highs = closes[:]
    highs[25] = 1900.0  # 1000x spike
    lows = [c - 0.001 for c in closes]
    return highs, lows, closes


CORRUPTION_CASES = {
    "all_zero":       ([0.0] * 30, [0.0] * 30, [0.0] * 30),
    "all_identical":  ([1.91] * 50, [1.90] * 50, [1.90] * 50),
    "single_spike":   _spike_series(),
    "all_nan":        ([math.nan] * 30, [math.nan] * 30, [math.nan] * 30),
    "negative":       ([-1.90] * 30, [-1.91] * 30, [-1.90] * 30),
}


@pytest.mark.parametrize("case", list(CORRUPTION_CASES), ids=list(CORRUPTION_CASES))
def test_detect_structure_survives_corrupt_input(case):
    highs, lows, closes = CORRUPTION_CASES[case]
    result = _detect_structure(highs, lows, closes)  # must not raise
    assert isinstance(result, dict)
    assert result.get("structure") in _VALID_STRUCTURE
