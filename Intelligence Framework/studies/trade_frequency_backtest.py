"""
trade_frequency_backtest.py

Deep-test track: how often does the framework actually issue a tradeable signal,
and at what grade? Runs the REAL decision pipeline (get_regime →
get_official_decision, incl. the ADX 25-32 structure gate, H4 confirmation, and
the weekly gate) for each historical day, by feeding it sliced data — no network
per iteration, no logic re-implemented.

Usage: python scripts/trade_frequency_backtest.py
"""

import os as _os, sys as _sys  # studies path bootstrap (project root)
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
for _p in (_ROOT,):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
import os
import sys
from collections import Counter
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import regime_detection as rd
from official_decision import get_official_decision
from oanda_feed import get_daily_bars, get_h4_bars, get_weekly_bars, is_configured

WARMUP   = 250     # D1 bars needed before the framework can classify
D1_MAX   = 1450    # ~5.5 years of daily bars
H4_MAX   = 6000
W_MAX    = 320


def _norm(df):
    if df is not None and hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)
    return df


def backtest(instrument: str) -> None:
    oanda_pair = instrument.replace("_", "")
    d1 = _norm(get_daily_bars(pair=oanda_pair, count=D1_MAX))
    h4 = _norm(get_h4_bars(pair=oanda_pair, count=H4_MAX))
    wk = _norm(get_weekly_bars(pair=oanda_pair, count=W_MAX))
    if d1 is None or len(d1) < WARMUP + 20:
        print(f"{instrument}: insufficient history"); return

    dates = d1.index
    by_grade   = Counter()
    directions = Counter()
    standaside = Counter()
    n = 0
    no_h4 = 0   # days excluded because H4 history doesn't reach back that far

    for i in range(WARMUP, len(d1)):
        as_of    = dates[i]
        d1_slice = d1.iloc[: i + 1]
        h4_slice = h4[h4.index <= as_of] if h4 is not None else None
        wk_slice = wk[wk.index <= as_of] if wk is not None else None

        # Patched fetchers return the last `count` bars AS OF this day — exactly
        # what production would have fetched on that date.
        def _d1(*a, count=100, **k): return d1_slice.tail(count).copy()
        def _h4(*a, count=120, **k): return h4_slice.tail(count).copy() if h4_slice is not None else None
        def _wk(*a, count=110, **k): return wk_slice.tail(count).copy() if wk_slice is not None else None

        try:
            with patch.object(rd, "_oanda_ok", return_value=True), \
                 patch("regime_detection._oanda_daily_bars", _d1), \
                 patch("regime_detection._oanda_h4_bars", _h4), \
                 patch("regime_detection._oanda_weekly_bars", _wk):
                regime = rd.get_regime(instrument)
            decision = get_official_decision(regime)
        except Exception as e:
            standaside[f"ERROR: {type(e).__name__}"] += 1
            continue

        # Exclude days where H4 history simply isn't available (OANDA H4 only
        # reaches back ~2.7y) — the framework correctly stands aside, but that's
        # a data gap, not a selectivity decision. Measure frequency on complete
        # data only.
        if regime.get("h4_available") is False:
            no_h4 += 1
            continue

        n += 1
        d = decision["direction"]
        directions[d] += 1
        if d in ("LONG", "SHORT"):
            by_grade[decision["grade"]] += 1
        else:
            reason = (regime.get("filter_reason")
                      or regime.get("resolution_note")
                      or regime.get("stand_down_reason") or "unspecified")
            standaside[reason.split("—")[0].strip()[:44]] += 1

    tradeable = directions["LONG"] + directions["SHORT"]
    print(f"\n{'='*60}\n  {instrument}  —  {n} days with COMPLETE data evaluated "
          f"(+{no_h4} excluded: no H4 history)\n{'='*60}")
    print(f"  NO TRADE : {directions['NO TRADE']:>5}  ({directions['NO TRADE']/n:.1%})")
    print(f"  LONG     : {directions['LONG']:>5}")
    print(f"  SHORT    : {directions['SHORT']:>5}")
    print(f"  TRADEABLE: {tradeable:>5}  ({tradeable/n:.1%} of days)")
    if by_grade:
        print("  Grade distribution of tradeable days:")
        for g in ("A+", "A", "B+", "B", "C"):
            if by_grade.get(g):
                print(f"      {g:>2}: {by_grade[g]}")
    print("  Top stand-aside reasons:")
    for reason, c in standaside.most_common(6):
        print(f"      {c:>5}  {reason}")


def main():
    if not is_configured():
        print("OANDA not configured"); return
    for inst in ("GBP_AUD", "GBP_JPY"):
        backtest(inst)


if __name__ == "__main__":
    main()
