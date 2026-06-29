from decision_brief import get_decision_brief
from regime_detection import get_regime
from no_trade_filter import apply_filter

passed = 0
failed = 0

def check_safe(name, fn):
    global passed, failed
    try:
        result = fn()
        # Must not crash
        # If it returns a brief, must be STAND ASIDE
        if hasattr(result, 'decision'):
            if result.decision not in ('STAND DOWN', 'STAND ASIDE'):
                failed += 1
                print(f'  FAIL  {name}')
                print(f'        Got decision: {result.decision}')
                print(f'        Expected: STAND ASIDE on corrupted input')
                return
        passed += 1
        print(f'  PASS  {name}')
        if hasattr(result, 'reason'):
            print(f'        Reason: {result.reason[:70]}')
    except Exception as e:
        failed += 1
        print(f'  FAIL  {name} — unhandled exception')
        print(f'        {type(e).__name__}: {e}')

print('='*60)
print('FM-1: INPUT CORRUPTION TESTS')
print('='*60)

print('\n── Empty and None inputs ────────────────────────────────')
check_safe('Empty string instrument',
           lambda: get_decision_brief(''))
check_safe('None instrument',
           lambda: get_decision_brief(None))
check_safe('Invalid instrument',
           lambda: get_decision_brief('EUR_USD'))
check_safe('Garbage string',
           lambda: get_decision_brief('XXXXXXXXXXX'))

print('\n── Corrupted regime dict through filter ─────────────────')
# Missing all keys
check_safe('Empty regime dict',
           lambda: apply_filter({}))
# All None values
check_safe('All None values',
           lambda: apply_filter({k: None for k in [
               'regime_d1','regime_h4','adx_h4','atr_vs_avg',
               'atr_compression','timeframe_conflict','conflict_type',
               'structure','weekly_context','lt_trend','st_trend',
               'execution_mode','size_mult','confidence',
           ]}))
# Negative ATR
check_safe('Negative ATR ratio',
           lambda: apply_filter({'atr_vs_avg': -5.0,
               'atr_compression': False,
               'timeframe_conflict': False, 'conflict_type': '',
               'regime_d1': 'TRENDING_UP', 'regime_h4': 'TRENDING_UP',
               'execution_mode': 'CONTINUATION', 'size_mult': 1.0,
               'confidence': 'HIGH', 'lt_trend': 'UPTREND',
               'weekly_context': 'ESTABLISHED_UPTREND',
               'structure': 'UPTREND', 'st_trend': 'UPTREND',
               'resolution_note': '', 'atr_compression_note': ''}))
# Infinite ATR
import math
check_safe('Infinite ATR ratio',
           lambda: apply_filter({'atr_vs_avg': math.inf,
               'atr_compression': False,
               'timeframe_conflict': False, 'conflict_type': '',
               'regime_d1': 'TRENDING_UP', 'regime_h4': 'TRENDING_UP',
               'execution_mode': 'CONTINUATION', 'size_mult': 1.0,
               'confidence': 'HIGH', 'lt_trend': 'UPTREND',
               'weekly_context': 'ESTABLISHED_UPTREND',
               'structure': 'UPTREND', 'st_trend': 'UPTREND',
               'resolution_note': '', 'atr_compression_note': ''}))

print('\n── Extreme price data through regime detection ───────────')
from regime_detection import _detect_structure, compute_atr_series
import math

# All zeros
check_safe('All-zero price data',
           lambda: _detect_structure([0]*30, [0]*30, [0]*30))
# All identical prices
check_safe('All identical prices',
           lambda: _detect_structure([1.9]*50, [1.91]*50, [1.9]*50))
# Extreme spike — one bar at 1000x normal
closes = [1.9 + i*0.001 for i in range(50)]
highs = closes[:]
highs[25] = 1900.0  # 1000x spike
lows = [c - 0.001 for c in closes]
check_safe('Single 1000x price spike',
           lambda: _detect_structure(highs, lows, closes))
# NaN throughout
check_safe('All NaN prices',
           lambda: _detect_structure(
               [math.nan]*30, [math.nan]*30, [math.nan]*30))
# Negative prices
check_safe('Negative prices',
           lambda: _detect_structure(
               [-1.9]*30, [-1.91]*30, [-1.9]*30))

print('\n── get_decision_brief() error handling ──────────────────')
# Brief must return STAND ASIDE on any internal error
from unittest.mock import patch
import regime_detection as rd

# OANDA returns empty dataframe
import pandas as pd
with patch.object(rd, '_oanda_ok', return_value=True):
    with patch.object(rd, '_oanda_daily_bars',
                      return_value=pd.DataFrame()):
        check_safe('OANDA returns empty dataframe',
                   lambda: get_decision_brief('GBP_AUD'))

# OANDA raises exception
def raise_error(*args, **kwargs):
    raise ConnectionError("OANDA timeout")

with patch.object(rd, '_oanda_ok', return_value=True):
    with patch.object(rd, '_oanda_daily_bars',
                      side_effect=raise_error):
        check_safe('OANDA connection timeout',
                   lambda: get_decision_brief('GBP_AUD'))

# get_regime returns error result
error_regime = rd._error_result("Test error injection")
with patch.object(rd, 'get_regime', return_value=error_regime):
    check_safe('get_regime returns error result',
               lambda: get_decision_brief('GBP_AUD'))

print(f'\n{"="*60}')
print(f'FM-1 RESULTS: {passed}/{passed+failed} passed')
if failed == 0:
    print('ALL CORRUPTION TESTS PASSED — framework fails gracefully')
else:
    print(f'{failed} FAILURES — fix before Phase 1')
print('='*60)
