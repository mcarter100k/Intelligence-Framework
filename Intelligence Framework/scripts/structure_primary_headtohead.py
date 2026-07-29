"""
structure_primary_headtohead.py

Settles "do we need ADX for confirmation?" with numbers.

Compares two regime classifiers through the FULL real pipeline (get_regime →
get_official_decision, incl. range trading), by swapping only _classify:

  * ADX-primary   (current live): trend only when ADX >= 25 (+structure in 25-32);
                  18-25 → VOLATILE (no edge).
  * Structure-primary (variant):  structure (pivots) LEADS — confirmed HH/HL →
                  tradeable trend; ADX drops to a light `<15 = dead` floor. ATR
                  spike/compression + JPY exhaustion safety filters kept.

For every actionable signal it simulates a trade (1.5·ATR stop, 2R target, 20-bar
max hold, spread-adjusted) and reports win% / avg-R / total-R. Critically it
isolates the MARGINAL trades — those structure-primary takes but ADX-primary
vetoes — because their expectancy is the whole answer.

Usage: python scripts/structure_primary_headtohead.py
"""
import os
import sys
from collections import defaultdict
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import regime_detection as rd
from regime_detection import _ADX_JPY_EXHAUSTION
from official_decision import get_official_decision
from oanda_feed import get_daily_bars, get_h4_bars, get_weekly_bars, is_configured

WARMUP    = 250
D1_MAX    = 1450
H4_MAX    = 6000
W_MAX     = 320
STOP_MULT = 1.5     # stop = 1.5 * ATR (risk_config.RISK_RULES.stop_atr_multiplier)
TARGET_R  = 2.0     # 2R target
MAX_BARS  = 20
SPREAD_PIPS = {"GBP_AUD": 3.0, "GBP_JPY": 3.0}


def classify_structure_primary(adx, atr_ratio, slope, instrument="GBP_AUD",
                               pair=None, structure="TRANSITIONAL"):
    """Structure leads; ADX is only a light 'dead market' floor. Safety filters kept."""
    if pair and pair.atr_compression_min > 0 and atr_ratio < pair.atr_compression_min:
        return "VOLATILE"
    spike_mult = pair.atr_spike_multiplier if pair else 1.5
    if atr_ratio >= spike_mult:
        return "VOLATILE"
    if instrument == "GBP_JPY" and adx >= _ADX_JPY_EXHAUSTION:
        return "RANGING"
    if adx < 15:                       # truly directionless — stand aside
        return "RANGING"
    if structure == "UPTREND":
        return "TRENDING_UP"
    if structure == "DOWNTREND":
        return "TRENDING_DOWN"
    return "VOLATILE"                  # no confirmed structure → stand aside


def _norm(df):
    if df is not None and hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)
    return df


def simulate(direction, entry, atr_price, fh, fl, fc, spread_price):
    """Return the trade's R-multiple outcome (spread-adjusted), or None."""
    R = STOP_MULT * atr_price
    if R <= 0 or not fc:
        return None
    spread_r = spread_price / R
    if direction == "LONG":
        stop, target = entry - R, entry + TARGET_R * R
    else:
        stop, target = entry + R, entry - TARGET_R * R
    for i in range(min(MAX_BARS, len(fc))):
        hi, lo = fh[i], fl[i]
        if direction == "LONG":
            if lo <= stop:   return -1.0 - spread_r          # stop first (conservative)
            if hi >= target: return TARGET_R - spread_r
        else:
            if hi >= stop:   return -1.0 - spread_r
            if lo <= target: return TARGET_R - spread_r
    exit_px = fc[min(MAX_BARS, len(fc)) - 1]
    move = (exit_px - entry) if direction == "LONG" else (entry - exit_px)
    return move / R - spread_r


def _decide(instrument, d1_slice, h4_slice, wk_slice, variant):
    def _d1(*a, count=100, **k): return d1_slice.tail(count).copy()
    def _h4(*a, count=120, **k): return h4_slice.tail(count).copy() if h4_slice is not None else None
    def _wk(*a, count=110, **k): return wk_slice.tail(count).copy() if wk_slice is not None else None
    patches = [patch.object(rd, "_oanda_ok", return_value=True),
               patch("regime_detection._oanda_daily_bars", _d1),
               patch("regime_detection._oanda_h4_bars", _h4),
               patch("regime_detection._oanda_weekly_bars", _wk)]
    if variant == "SP":
        patches.append(patch("regime_detection._classify", classify_structure_primary))
    import contextlib
    with contextlib.ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        regime = rd.get_regime(instrument)
    return regime, get_official_decision(regime)


def _stats(rlist):
    if not rlist:
        return "     0 trades"
    n = len(rlist)
    wins = sum(1 for r in rlist if r > 0)
    total = sum(rlist)
    return (f"{n:>5} trades  win {wins/n:>5.1%}  avgR {total/n:>+5.2f}  "
            f"totalR {total:>+7.1f}")


def run(instrument):
    op = instrument.replace("_", "")
    d1 = _norm(get_daily_bars(pair=op, count=D1_MAX))
    h4 = _norm(get_h4_bars(pair=op, count=H4_MAX))
    wk = _norm(get_weekly_bars(pair=op, count=W_MAX))
    if d1 is None or len(d1) < WARMUP + MAX_BARS + 5:
        print(f"{instrument}: insufficient history"); return

    dates = d1.index
    H = [float(v) for v in d1["High"].values]
    L = [float(v) for v in d1["Low"].values]
    C = [float(v) for v in d1["Close"].values]
    spread_price = SPREAD_PIPS[instrument] * (0.01 if "JPY" in instrument else 0.0001)

    R = {"ADX": [], "SP": []}                 # all actionable trade R-outcomes
    R_grade = {"ADX": defaultdict(list), "SP": defaultdict(list)}
    marginal = []                             # SP takes, ADX vetoes
    counter_veto = []                         # ADX takes, SP vetoes
    days = 0

    for i in range(WARMUP, len(d1) - MAX_BARS - 1):
        as_of = dates[i]
        d1_s = d1.iloc[: i + 1]
        h4_s = h4[h4.index <= as_of] if h4 is not None else None
        wk_s = wk[wk.index <= as_of] if wk is not None else None

        try:
            reg_a, dec_a = _decide(instrument, d1_s, h4_s, wk_s, "ADX")
            if reg_a.get("h4_available") is False:
                continue
            reg_s, dec_s = _decide(instrument, d1_s, h4_s, wk_s, "SP")
        except Exception:
            continue

        days += 1
        fh, fl, fc = H[i + 1:i + 1 + MAX_BARS], L[i + 1:i + 1 + MAX_BARS], C[i + 1:i + 1 + MAX_BARS]

        def actionable(dec):
            return dec["direction"] in ("LONG", "SHORT") and dec["grade"] != "C"

        a_ok, s_ok = actionable(dec_a), actionable(dec_s)
        entry = reg_a["current_price"]
        atr_p = reg_a.get("atr", 0.0)

        if a_ok:
            r = simulate(dec_a["direction"], entry, atr_p, fh, fl, fc, spread_price)
            if r is not None:
                R["ADX"].append(r); R_grade["ADX"][dec_a["grade"]].append(r)
        if s_ok:
            r = simulate(dec_s["direction"], entry, reg_s.get("atr", atr_p), fh, fl, fc, spread_price)
            if r is not None:
                R["SP"].append(r); R_grade["SP"][dec_s["grade"]].append(r)
                if not a_ok:
                    marginal.append(r)
        if a_ok and not s_ok:
            r = simulate(dec_a["direction"], entry, atr_p, fh, fl, fc, spread_price)
            if r is not None:
                counter_veto.append(r)

    print(f"\n{'='*68}\n  {instrument}  —  {days} complete-data days "
          f"({str(dates[WARMUP])[:10]} → {str(dates[len(d1)-MAX_BARS-1])[:10]})\n{'='*68}")
    print(f"  ADX-primary       : {_stats(R['ADX'])}")
    print(f"  Structure-primary : {_stats(R['SP'])}")
    print(f"\n  MARGINAL trades (SP takes, ADX vetoes) : {_stats(marginal)}")
    print(f"  Reverse (ADX takes, SP vetoes)         : {_stats(counter_veto)}")
    print("\n  By grade:")
    for variant in ("ADX", "SP"):
        label = "ADX-primary" if variant == "ADX" else "Structure-primary"
        for g in ("A+", "A", "B+", "B"):
            rl = R_grade[variant].get(g)
            if rl:
                print(f"    {label:<18} {g:>2}: {_stats(rl)}")


def main():
    if not is_configured():
        print("OANDA not configured"); return
    print("Exit model: 1.5·ATR stop, 2R target, 20-bar max hold, spread-adjusted.")
    print("Marginal-trade expectancy is the answer: >0 → ADX vetoes GOOD trades; "
          "<0 → ADX earns its keep.")
    for inst in ("GBP_AUD", "GBP_JPY"):
        run(inst)


if __name__ == "__main__":
    main()
