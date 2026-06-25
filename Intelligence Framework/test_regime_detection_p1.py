"""
test_regime_detection_p1.py

Test suite for Problem 1 changes to regime_detection.py.

Sections:
  1. _classify() — all ADX zone boundary conditions
  2. PairConfig  — pip helpers and PAIRS dict
  3. get_regime() output contract (mocked OHLC, no live API)
  4. Regression  — new thresholds produce different output than old logic

Run: python3 test_regime_detection_p1.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unittest.mock as mock
import pandas as pd

import regime_detection as rd
from regime_detection import (
    _classify,
    PAIRS,
    _DEFAULT_PAIR,
    _ADX_RANGING_THRESHOLD,
    _ADX_TRANSITION_HIGH,
    _ADX_EXHAUSTION_THRESHOLD,
    _ADX_JPY_EXHAUSTION,
    get_regime,
)

# ── Test runner ────────────────────────────────────────────────────────────────

_PASS     = 0
_FAIL     = 0
_FAILURES = []


def _check(num: str, desc: str, actual, expected) -> None:
    global _PASS, _FAIL
    if actual == expected:
        _PASS += 1
    else:
        _FAIL += 1
        _FAILURES.append((num, desc, repr(expected), repr(actual)))


def _check_type(num: str, desc: str, actual, expected_type) -> None:
    global _PASS, _FAIL
    if isinstance(actual, expected_type):
        _PASS += 1
    else:
        _FAIL += 1
        _FAILURES.append((num, desc, str(expected_type), type(actual).__name__))


def _check_true(num: str, desc: str, condition: bool) -> None:
    global _PASS, _FAIL
    if condition:
        _PASS += 1
    else:
        _FAIL += 1
        _FAILURES.append((num, desc, "True", "False"))


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — _classify() ADX zone tests
# ═══════════════════════════════════════════════════════════════════════════════

print()
print("SECTION 1: _classify() — ADX zone boundary tests")
print("─" * 62)

# T01 — below ranging threshold, normal ATR → RANGING
_check("T01", "ADX=10, atr=1.0, GBP_AUD → RANGING",
       _classify(10, 1.0, +0.01, "GBP_AUD"), "RANGING")

# T02 — below ranging threshold but ATR spike → VOLATILE
_check("T02", "ADX=10, atr=2.0, GBP_AUD → VOLATILE (ATR spike > 1.5)",
       _classify(10, 2.0, +0.01, "GBP_AUD"), "VOLATILE")

# T03 — mid ranging zone, negative slope → RANGING
_check("T03", "ADX=15, atr=1.0, GBP_AUD, slope<0 → RANGING",
       _classify(15, 1.0, -0.01, "GBP_AUD"), "RANGING")

# T04 — exactly at transition zone lower boundary (18) → VOLATILE
_check("T04", "ADX=18, atr=1.0, GBP_AUD → VOLATILE (transition zone starts at 18)",
       _classify(18, 1.0, +0.01, "GBP_AUD"), "VOLATILE")

# T05 — mid transition zone → VOLATILE
_check("T05", "ADX=22, atr=1.0, GBP_AUD → VOLATILE (mid transition zone)",
       _classify(22, 1.0, +0.01, "GBP_AUD"), "VOLATILE")

# T06 — top of transition zone, negative slope → VOLATILE
_check("T06", "ADX=24, atr=1.0, GBP_AUD, slope<0 → VOLATILE (top of transition zone)",
       _classify(24, 1.0, -0.01, "GBP_AUD"), "VOLATILE")

# T07 — exactly at trending boundary (25), positive slope → TRENDING_UP
_check("T07", "ADX=25, atr=1.0, GBP_AUD → TRENDING_UP",
       _classify(25, 1.0, +0.01, "GBP_AUD"), "TRENDING_UP")

# T08 — mid trending zone, negative slope → TRENDING_DOWN
_check("T08", "ADX=28, atr=1.0, GBP_AUD, slope<0 → TRENDING_DOWN",
       _classify(28, 1.0, -0.01, "GBP_AUD"), "TRENDING_DOWN")

# T09 — just below exhaustion threshold → TRENDING_UP
_check("T09", "ADX=31, atr=1.0, GBP_AUD → TRENDING_UP (below exhaustion)",
       _classify(31, 1.0, +0.01, "GBP_AUD"), "TRENDING_UP")

# T10 — exactly at exhaustion threshold → still TRENDING_UP (exhaustion FLAG only)
_check("T10", "ADX=32, atr=1.0, GBP_AUD → TRENDING_UP (exhaustion flagged by caller)",
       _classify(32, 1.0, +0.01, "GBP_AUD"), "TRENDING_UP")

# T11 — well above exhaustion, GBP_AUD → TRENDING_UP (GBP_AUD never RANGING from exhaustion)
_check("T11", "ADX=40, atr=1.0, GBP_AUD → TRENDING_UP (exhaustion but not ranging)",
       _classify(40, 1.0, +0.01, "GBP_AUD"), "TRENDING_UP")

# T12 — GBP_JPY ADX=34: below _ADX_JPY_EXHAUSTION=35, above _ADX_EXHAUSTION_THRESHOLD=32
#        JPY-specific exhaustion has NOT triggered → general exhaustion path → TRENDING_UP.
#        Note: original spec listed RANGING here, but the note "(JPY exhaustion at 35, not yet)"
#        confirms 34 has not reached the JPY exhaustion threshold. TRENDING_UP is correct.
_check("T12", "ADX=34, GBP_JPY → TRENDING_UP (below JPY exhaustion threshold of 35)",
       _classify(34, 1.0, +0.01, "GBP_JPY"), "TRENDING_UP")

# T13 — GBP_JPY ADX=35: exactly at _ADX_JPY_EXHAUSTION → RANGING
_check("T13", "ADX=35, GBP_JPY → RANGING (JPY exhaustion kicks in at 35)",
       _classify(35, 1.0, +0.01, "GBP_JPY"), "RANGING")

# T14 — GBP_JPY ADX=45: well above exhaustion → RANGING
_check("T14", "ADX=45, GBP_JPY → RANGING (JPY exhaustion confirmed)",
       _classify(45, 1.0, +0.01, "GBP_JPY"), "RANGING")

# T15 — GBP_AUD ADX=35: GBP_AUD exhaustion threshold is 32, not 35 → TRENDING_UP
_check("T15", "ADX=35, GBP_AUD → TRENDING_UP (GBP_AUD exhaustion=32; JPY rule does not apply)",
       _classify(35, 1.0, +0.01, "GBP_AUD"), "TRENDING_UP")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — PairConfig tests
# ═══════════════════════════════════════════════════════════════════════════════

print()
print("SECTION 2: PairConfig — pip helpers and PAIRS dict")
print("─" * 62)

_aud = PAIRS["GBP_AUD"]
_jpy = PAIRS["GBP_JPY"]

# T16-T17 — pip_size
_check("T16", "GBP_AUD pip_size == 0.0001",  _aud.pip_size, 0.0001)
_check("T17", "GBP_JPY pip_size == 0.01",    _jpy.pip_size, 0.01)

# T18-T19 — to_pips
_check("T18", "GBP_AUD to_pips(0.0050) == 50.0", _aud.to_pips(0.0050), 50.0)
_check("T19", "GBP_JPY to_pips(0.50) == 50.0",   _jpy.to_pips(0.50),  50.0)

# T20-T21 — from_pips
_check("T20", "GBP_AUD from_pips(50) == 0.005", _aud.from_pips(50), 0.005)
_check("T21", "GBP_JPY from_pips(50) == 0.50",  _jpy.from_pips(50), 0.50)

# T22 — PAIRS dict keys
_check("T22a", "PAIRS contains 'GBP_AUD'", "GBP_AUD" in PAIRS, True)
_check("T22b", "PAIRS contains 'GBP_JPY'", "GBP_JPY" in PAIRS, True)

# T23 — _DEFAULT_PAIR constant
_check("T23", "_DEFAULT_PAIR == 'GBP_AUD'", _DEFAULT_PAIR, "GBP_AUD")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — get_regime() output contract (mocked OHLC, no live API)
# ═══════════════════════════════════════════════════════════════════════════════

print()
print("SECTION 3: get_regime() output contract (mocked data)")
print("─" * 62)

# Synthetic D1 dataset — 100 bars, clean linear uptrend
# With constant +DM and zero -DM, ADX converges to ~100 (perfect trend).
_closes = [1.8000 + i * 0.0010 for i in range(100)]
_highs  = [c + 0.0020 for c in _closes]
_lows   = [c - 0.0020 for c in _closes]
_mock_df = pd.DataFrame({"High": _highs, "Low": _lows, "Close": _closes})

# Contract: every key the downstream system may read must be present with the right type.
REQUIRED_KEYS = {
    "regime":              str,
    "regime_label":        str,
    "regime_d1":           str,
    "regime_h4":           str,
    "timeframe_conflict":  bool,
    "conflict_type":       str,
    "stand_down":          bool,
    "stand_down_reason":   str,
    "trade_guidance":      str,
    "adx":                 float,
    "adx_h4":              float,
    "atr":                 float,
    "atr_pips":            float,
    "atr_pct":             float,
    "atr_vs_avg":          float,
    "volatility":          str,
    "vol_note":            str,
    "current_price":       float,
    "today_high":          float,
    "today_low":           float,
    "range_used":          (int, float),
    "range_remaining":     (int, float),
    "fuel_pct":            (int, float),
    "fuel_label":          str,
    "pair":                str,
    "instrument":          str,
    "adx_exhaustion":      bool,
    "adx_exhaustion_note": str,
    "error":               type(None),
}

try:
    with mock.patch("regime_detection._oanda_ok", return_value=True), \
         mock.patch("regime_detection._oanda_daily_bars", return_value=_mock_df):
        _result = get_regime("GBP_AUD")

    # T24.* — key presence and type
    for _key, _etype in REQUIRED_KEYS.items():
        if _key not in _result:
            _FAIL += 1
            _FAILURES.append(
                (f"T24.{_key}", f"key '{_key}' present", "present", "MISSING")
            )
        else:
            _check_type(
                f"T24.{_key}",
                f"result['{_key}'] is {_etype}",
                _result[_key],
                _etype,
            )

    # T25 — regime is a valid enum value
    _VALID = {"TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE", "UNKNOWN"}
    _check("T25", "regime is a valid value",
           _result.get("regime") in _VALID, True)

    # T26 — ADX is in range
    _check_true("T26", "0 <= adx <= 100",
                0 <= _result.get("adx", -1) <= 100)

    # T27 — atr_vs_avg is positive
    _check_true("T27", "atr_vs_avg > 0",
                _result.get("atr_vs_avg", 0) > 0)

    # T28 — no error
    _check("T28", "error is None", _result.get("error"), None)

    # T29 — display name
    _check("T29", "pair == 'GBP/AUD'", _result.get("pair"), "GBP/AUD")

except Exception as _exc:
    _FAIL += 1
    _FAILURES.append(("T24-T29", "Integration test raised an exception",
                      "no exception", str(_exc)))


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Regression tests: new thresholds vs old logic
# ═══════════════════════════════════════════════════════════════════════════════

print()
print("SECTION 4: Regression — new thresholds produce correct directional change")
print("─" * 62)

# Test A — ADX=22, GBP_AUD
#   Old logic (ADX 20-25 transition) → TRENDING_UP (weak)
#   New logic (ADX 18-25 = no edge)  → VOLATILE
#   Correct change: do not call trending in a zone with no statistical edge.
_check("T30", "ADX=22, GBP_AUD: transition zone → VOLATILE (old code said TRENDING_UP)",
       _classify(22, 1.0, +0.01, "GBP_AUD"), "VOLATILE")

# Test B — ADX=36, GBP_JPY
#   Old logic (ADX > 25) → TRENDING_UP
#   New logic (ADX >= 35 on JPY = exhaustion) → RANGING
#   Correct change: 82.7% mean reversion at ADX 40+ on GBP/JPY.
_check("T31", "ADX=36, GBP_JPY: exhaustion → RANGING (old code said TRENDING_UP)",
       _classify(36, 1.0, +0.01, "GBP_JPY"), "RANGING")

# Test C — ADX=17, GBP_AUD
#   Old logic (ADX < 20) → RANGING
#   New logic (ADX < 18) → RANGING
#   Consistent: threshold tightened but output unchanged at 17.
_check("T32", "ADX=17, GBP_AUD: below ranging threshold → RANGING (consistent)",
       _classify(17, 1.0, +0.01, "GBP_AUD"), "RANGING")

# Test D — ADX=19, GBP_AUD  ← THE CRITICAL CHANGE
#   Old logic (ADX < 20) → RANGING
#   New logic (ADX 18-25 = transition) → VOLATILE
#   Correct change: 18-20 was incorrectly classified as ranging; empirical data
#   shows no consistent edge in this zone.
_check("T33", "ADX=19, GBP_AUD: 18-25 transition → VOLATILE (old code said RANGING)",
       _classify(19, 1.0, +0.01, "GBP_AUD"), "VOLATILE")


# ═══════════════════════════════════════════════════════════════════════════════
# RESULTS
# ═══════════════════════════════════════════════════════════════════════════════

_TOTAL = _PASS + _FAIL
print()
print("=" * 62)
print(f"  RESULTS  |  {_TOTAL} run  |  {_PASS} passed  |  {_FAIL} failed")
print("=" * 62)

if _FAILURES:
    print()
    for _num, _desc, _exp, _got in _FAILURES:
        print(f"  FAIL [{_num}]")
        print(f"    {_desc}")
        print(f"    expected : {_exp}")
        print(f"    actual   : {_got}")
    print()
    print(f"  {_FAIL} TESTS FAILED — do not proceed")
else:
    print()
    print("  ALL TESTS PASSED")
print()
