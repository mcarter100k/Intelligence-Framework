from regime_detection import (
    get_composite_regime, _detect_structure,
    _classify, _compute_adx, PAIRS
)
from no_trade_filter import apply_filter
from decision_brief import get_decision_brief, _plain
from unittest.mock import patch
import regime_detection as rd
import pandas as pd
import numpy as np

passed = 0
failed = 0

def check(name, got, expected):
    global passed, failed
    ok = got == expected
    if ok:
        passed += 1
        print(f'  PASS  {name}')
    else:
        failed += 1
        print(f'  FAIL  {name}')
        print(f'        expected: {expected}')
        print(f'        got:      {got}')

def check_true(name, cond, detail=''):
    global passed, failed
    if cond:
        passed += 1
        print(f'  PASS  {name}')
    else:
        failed += 1
        print(f'  FAIL  {name}' + (f' — {detail}' if detail else ''))

print('='*60)
print('FM-7: SIGNAL ACCEPTANCE TESTS')
print('='*60)

print('\n── Resolution table produces tradeable outputs ──────────')
# Verify the resolution table CAN produce tradeable modes
from regime_detection import RESOLUTION_TABLE

tradeable_modes = {'CONTINUATION', 'PULLBACK_ENTRY',
                   'FADE_EXTREMES', 'REDUCED_MOMENTUM'}
stand_down_modes = {'STAND_DOWN'}

tradeable_combos = [
    k for k, v in RESOLUTION_TABLE.items()
    if v['execution_mode'] in tradeable_modes
]
check_true('Resolution table has tradeable combinations',
           len(tradeable_combos) >= 6,
           f'found {len(tradeable_combos)}')

for combo, result in RESOLUTION_TABLE.items():
    if result['execution_mode'] == 'CONTINUATION':
        check_true(f'CONTINUATION combo {combo} has size > 0',
                   result['size_mult'] > 0)
        check_true(f'CONTINUATION combo {combo} has HIGH confidence',
                   result['confidence'] == 'HIGH')
        break

print('\n── Filter passes clean trend ─────────────────────────────')
# A clean aligned trend must pass the filter
clean_long = {
    'regime_d1': 'TRENDING_UP', 'regime_h4': 'TRENDING_UP',
    'adx_h4': 32.0, 'atr_vs_avg': 1.05,
    'atr_compression': False, 'atr_compression_note': '',
    'timeframe_conflict': False, 'conflict_type': '',
    'structure': 'UPTREND', 'weekly_context': 'ESTABLISHED_UPTREND',
    'lt_trend': 'UPTREND', 'st_trend': 'UPTREND',
    'execution_mode': 'CONTINUATION', 'size_mult': 1.0,
    'confidence': 'HIGH', 'resolution_note': '',
}
from no_trade_filter import apply_filter
r = apply_filter(clean_long)
check('Clean uptrend → filter allows', r.allowed, True)
check('Clean uptrend → CONTINUATION', r.execution_mode, 'CONTINUATION')
check('Clean uptrend → 100% size', r.size_mult, 1.0)
check('Clean uptrend → HIGH confidence', r.confidence, 'HIGH')

clean_short = {**clean_long,
    'regime_d1': 'TRENDING_DOWN', 'regime_h4': 'TRENDING_DOWN',
    'structure': 'DOWNTREND',
    'weekly_context': 'ESTABLISHED_DOWNTREND',
    'lt_trend': 'DOWNTREND', 'st_trend': 'DOWNTREND',
}
r = apply_filter(clean_short)
check('Clean downtrend → filter allows', r.allowed, True)
check('Clean downtrend → CONTINUATION', r.execution_mode, 'CONTINUATION')

print('\n── Full brief produces LONG on clean uptrend data ───────')
# Build synthetic clean uptrend OANDA-format dataframe
# 220 D1 bars of steady uptrend — enough for MA200 + ADX warmup
n = 220
base = 1.85
closes = [base + i * 0.0015 for i in range(n)]
highs  = [c + 0.0025 for c in closes]
lows   = [c - 0.0025 for c in closes]
dates  = pd.date_range('2025-01-01', periods=n, freq='B', tz='UTC')
df_d1  = pd.DataFrame({'High': highs, 'Low': lows,
                        'Close': closes, 'Open': closes,
                        'Volume': [1000]*n}, index=dates)

# H4: same direction, strong trend
n_h4 = 120
closes_h4 = [base + i * 0.0005 for i in range(n_h4)]
highs_h4  = [c + 0.0010 for c in closes_h4]
lows_h4   = [c - 0.0010 for c in closes_h4]
dates_h4  = pd.date_range('2025-11-01', periods=n_h4,
                           freq='4h', tz='UTC')
df_h4 = pd.DataFrame({'High': highs_h4, 'Low': lows_h4,
                       'Close': closes_h4, 'Open': closes_h4,
                       'Volume': [500]*n_h4}, index=dates_h4)

# Weekly: same direction
n_w = 110
closes_w = [base + i * 0.005 for i in range(n_w)]
highs_w  = [c + 0.010 for c in closes_w]
lows_w   = [c - 0.010 for c in closes_w]
dates_w  = pd.date_range('2023-01-01', periods=n_w,
                          freq='W', tz='UTC')
df_w = pd.DataFrame({'High': highs_w, 'Low': lows_w,
                      'Close': closes_w, 'Open': closes_w,
                      'Volume': [2000]*n_w}, index=dates_w)

def mock_oanda_ok():
    return True

def mock_daily(pair='GBPAUD', count=220, **kw):
    return df_d1.tail(count).copy()

def mock_h4(pair='GBPAUD', count=120, **kw):
    return df_h4.tail(count).copy()

def mock_weekly(pair='GBPAUD', count=110, **kw):
    return df_w.tail(count).copy()

import oanda_feed as of_

with patch.object(rd, '_oanda_ok', mock_oanda_ok), \
     patch('regime_detection._oanda_daily_bars', mock_daily), \
     patch('regime_detection._oanda_h4_bars', mock_h4), \
     patch('regime_detection._oanda_weekly_bars', mock_weekly):

    regime = rd.get_regime('GBP_AUD')
    print(f'\n  Synthetic uptrend regime output:')
    print(f'    regime_d1:      {regime.get("regime_d1")}')
    print(f'    regime_h4:      {regime.get("regime_h4")}')
    print(f'    adx_d1:         {regime.get("adx")}')
    print(f'    adx_h4:         {regime.get("adx_h4")}')
    print(f'    structure:      {regime.get("structure")}')
    print(f'    weekly_context: {regime.get("weekly_context")}')
    print(f'    lt_trend:       {regime.get("lt_trend")}')
    print(f'    stand_down:     {regime.get("stand_down")}')
    print(f'    execution_mode: {regime.get("execution_mode")}')
    print(f'    filter_allowed: {regime.get("filter_allowed")}')

    check_true('Synthetic uptrend → regime_d1 TRENDING_UP',
               regime.get('regime_d1') == 'TRENDING_UP',
               f'got {regime.get("regime_d1")}')
    check_true('Synthetic uptrend → not stand_down',
               not regime.get('stand_down', True),
               f'stand_down={regime.get("stand_down")}')
    check_true('Synthetic uptrend → filter allows',
               regime.get('filter_allowed', False),
               f'filter_allowed={regime.get("filter_allowed")}')

    # Now get the full brief — get_decision_brief() derives direction
    # from regime filter output directly (not from make_decision)
    brief = get_decision_brief('GBP_AUD')
    print(f'\n  Full brief output:')
    print(f'    decision:   {brief.decision}')
    print(f'    conviction: {brief.conviction}')
    print(f'    grade:      {brief.grade}')
    print(f'    size_pct:   {brief.size_pct}')
    print(f'    reason:     {brief.reason[:60]}')

    check_true('Full brief produces LONG on clean uptrend',
               brief.decision == 'LONG',
               f'got {brief.decision}')
    check_true('Conviction > 50 on clean uptrend',
               brief.conviction > 50,
               f'got {brief.conviction}')

print('\n── FM-7 summary ─────────────────────────────────────────')
print(f'\n{"="*60}')
print(f'FM-7 RESULTS: {passed}/{passed+failed} passed')
if failed == 0:
    print('FRAMEWORK CAN PRODUCE LONG AND SHORT SIGNALS')
    print('Output paralysis: NOT CONFIRMED')
else:
    print(f'{failed} FAILURES — investigate before Phase 1')
print('='*60)
