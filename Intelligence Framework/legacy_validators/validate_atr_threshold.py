import warnings
warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import date

PAIRS = {
    "GBP_AUD": {"ticker": "GBPAUD=X", "name": "GBP/AUD", "pip": 0.0001},
    "GBP_JPY": {"ticker": "GBPJPY=X", "name": "GBP/JPY", "pip": 0.01},
}

ATR_PERIOD   = 14
AVG_PERIOD   = 20
FORWARD_BARS = 20
DEGRADED_THRESHOLD = 0.52  # both signals below this = untradeable

ATR_RATIO_BANDS = [
    (0.0, 0.8),   # ATR contracting
    (0.8, 1.0),   # ATR slightly below average
    (1.0, 1.2),   # ATR near average
    (1.2, 1.4),   # ATR slightly elevated
    (1.4, 1.6),   # textbook spike zone starts (current threshold)
    (1.6, 1.8),   # elevated
    (1.8, 2.0),   # high
    (2.0, 2.5),   # very high
    (2.5, 99.0),  # extreme
]

def compute_atr_series(highs, lows, closes, period=ATR_PERIOD):
    """
    Wilder-smoothed ATR. Same implementation as regime_detection.py.
    Returns list of ATR values starting from index period.
    """
    n = len(closes)
    tr_list = [
        max(highs[i]-lows[i],
            abs(highs[i]-closes[i-1]),
            abs(lows[i]-closes[i-1]))
        for i in range(1, n)
    ]
    atr = sum(tr_list[:period]) / period
    atr_series = [atr]
    for tr in tr_list[period:]:
        atr = (atr * (period-1) + tr) / period
        atr_series.append(atr)
    return atr_series

def compute_atr_ratios(atr_series, avg_period=AVG_PERIOD):
    """
    For each bar, compute ATR / rolling_avg(ATR, avg_period).
    Returns list of ratios. First avg_period values are skipped.
    """
    ratios = []
    for i in range(avg_period, len(atr_series)):
        avg = sum(atr_series[i-avg_period:i]) / avg_period
        ratio = atr_series[i] / avg if avg > 0 else 1.0
        ratios.append((i, ratio, atr_series[i]))
    return ratios

def analyze_pair(cfg, period="5y"):
    ticker = cfg["ticker"]
    name   = cfg["name"]
    pip    = cfg["pip"]

    print(f"\nFetching {name} — {period} D1 data...")
    raw = yf.download(ticker, period=period, interval="1d",
                      progress=False, auto_adjust=True)
    if raw is None or len(raw) < 200:
        print(f"  ERROR: insufficient data")
        return {}
    if hasattr(raw.columns, 'levels'):
        raw.columns = raw.columns.get_level_values(0)

    h = raw['High'].values.astype(float)
    l = raw['Low'].values.astype(float)
    c = raw['Close'].values.astype(float)
    n = len(c)

    atr_series = compute_atr_series(h, l, c)
    atr_offset = ATR_PERIOD  # atr_series[0] corresponds to closes[ATR_PERIOD]

    ratio_data = compute_atr_ratios(atr_series)
    # ratio_data[i] = (atr_series_index, ratio, atr_value)
    # atr_series_index + atr_offset = original bar index

    rows = []
    for atr_idx, ratio, atr_val in ratio_data:
        orig_i = atr_idx + atr_offset
        if orig_i + FORWARD_BARS >= n:
            break

        # Direction from 10-bar slope (will be replaced by structure
        # in later problems — using slope here for ATR isolation)
        slope     = c[orig_i] - c[orig_i-10] if orig_i >= 10 else 0
        direction = 1 if slope > 0 else -1

        # Momentum outcome
        future_move  = (c[orig_i + FORWARD_BARS] - c[orig_i]) * direction
        momentum_win = 1 if future_move > 0 else 0

        # Mean reversion outcome
        mean_20  = np.mean(c[max(0, orig_i-20):orig_i])
        mr_gap   = mean_20 - c[orig_i]
        mr_win   = (1 if (c[orig_i+FORWARD_BARS] - c[orig_i]) *
                   np.sign(mr_gap) > 0 else 0) if mr_gap != 0 else 0

        rows.append({
            'atr_ratio':    round(ratio, 3),
            'atr_pips':     round(atr_val / pip, 1),
            'momentum_win': momentum_win,
            'mr_win':       mr_win,
        })

    df = pd.DataFrame(rows)
    print(f"  {len(df)} observations")

    print(f"\n  {'Band':<14} {'N':>5}  {'Mom%':>6}  {'MR%':>6}  "
          f"{'ATR pips':>9}  {'Both<52%?':>10}  Note")
    print("  " + "─" * 72)

    degraded_at = None
    for lo, hi in ATR_RATIO_BANDS:
        sub = df[(df['atr_ratio'] >= lo) & (df['atr_ratio'] < hi)]
        if len(sub) < 15:
            continue
        mom_pct  = sub['momentum_win'].mean() * 100
        mr_pct   = sub['mr_win'].mean() * 100
        avg_pips = sub['atr_pips'].mean()
        both_degraded = mom_pct < DEGRADED_THRESHOLD*100 and mr_pct < DEGRADED_THRESHOLD*100
        note = " <-- DEGRADED" if both_degraded else ""
        if both_degraded and degraded_at is None:
            degraded_at = lo
        print(f"  ATR {lo:.1f}x-{hi:.1f}x  {len(sub):>5}  "
              f"{mom_pct:>5.1f}%  {mr_pct:>5.1f}%  "
              f"{avg_pips:>8.1f}  {'YES' if both_degraded else 'no':>10}  {note}")

    print(f"\n  RESULT FOR {name}:")
    print(f"  {'─'*55}")
    if degraded_at:
        delta = round(degraded_at - 1.5, 2)
        verdict = (
            "higher than textbook — 1.5x fires too early" if delta > 0.1
            else "lower than textbook — volatility damages signals earlier" if delta < -0.1
            else "consistent with textbook"
        )
        print(f"  Empirical degraded threshold: ATR ratio >= {degraded_at}")
        print(f"  Textbook threshold:           ATR ratio >= 1.5")
        print(f"  Delta:                        {'+' if delta >= 0 else ''}{delta}")
        print(f"  Verdict:                      {verdict}")
        print(f"  ACTION: Set _ATR_SPIKE_MULTIPLIER = {degraded_at} for {name}")
    else:
        print(f"  Signal quality never degrades below {DEGRADED_THRESHOLD*100:.0f}% at any ATR level")
        print(f"  ATR ratio alone is insufficient as a stand-down trigger for {name}")
        print(f"  ACTION: Keep 1.5x as conservative default, add secondary filter")

    return {
        'name':         name,
        'degraded_at':  degraded_at,
        'observations': len(df),
    }

def main():
    print("ATR Spike Multiplier Validation")
    print(f"Degraded threshold: both signals < {DEGRADED_THRESHOLD*100:.0f}%")
    print(f"Forward window: {FORWARD_BARS} bars")

    results = [analyze_pair(cfg) for cfg in PAIRS.values()]

    print("\n" + "═"*60)
    print("SUMMARY")
    print("═"*60)
    for r in results:
        if not r:
            continue
        t = r.get('degraded_at')
        if t:
            print(f"  {r['name']:<12}: empirical threshold = {t}x  "
                  f"(delta vs 1.5: {t-1.5:+.2f})")
        else:
            print(f"  {r['name']:<12}: no clean degradation point found")

    thresholds = [r['degraded_at'] for r in results
                  if r and r.get('degraded_at')]
    if len(thresholds) == 2 and thresholds[0] != thresholds[1]:
        print(f"\n  Pairs differ — pair-specific thresholds confirmed required")
    elif len(thresholds) == 2:
        print(f"\n  Both pairs share threshold — single value defensible")

    print(f"\n  Run date: {date.today().isoformat()}")
    print("═"*60)

if __name__ == '__main__':
    main()
