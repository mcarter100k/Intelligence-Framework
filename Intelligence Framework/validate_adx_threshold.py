"""
validate_adx_threshold.py

Empirically derives the ADX trending threshold from 5 years of D1 data
for GBPAUD=X and GBPJPY=X instead of using Wilder's textbook value of 25.

Method:
  - Compute Wilder ADX(14) matching regime_detection.py exactly
  - For each bar: record ADX, 10-bar slope direction, 20-bar forward outcome
  - Bucket into ADX bands; measure momentum vs mean-reversion win rate per band
  - Find lowest ADX level where momentum win rate >= 55% for two consecutive bands
"""

from __future__ import annotations
from datetime import datetime, timedelta

import yfinance as yf

# ── Config ─────────────────────────────────────────────────────────────────────
ADX_PERIOD         = 14
SLOPE_LOOKBACK     = 10    # bars back for slope direction
OUTCOME_BARS       = 20    # bars forward for outcome
TEXTBOOK_ADX       = 25.0
MOMENTUM_THRESHOLD = 55.0  # win% required to call it a momentum edge

PAIRS = {
    "GBPAUD=X": {"pip_mult": 10_000, "label": "GBP/AUD"},
    "GBPJPY=X": {"pip_mult": 100,    "label": "GBP/JPY"},
}

BANDS = [
    ( 0, 15),
    (15, 18),
    (18, 20),
    (20, 22),
    (22, 25),
    (25, 28),
    (28, 32),
    (32, 40),
    (40, 999),
]
BAND_LABELS = [
    " 0-15 ",
    "15-18 ",
    "18-20 ",
    "20-22 ",
    "22-25 ",
    "25-28 ",
    "28-32 ",
    "32-40 ",
    "  40+ ",
]


# ── ADX computation (exact match to regime_detection.py) ──────────────────────

def _wilder_sum_smooth(values: list[float], period: int) -> list[float]:
    """Wilder smoothing with sum initialisation — used for TR, +DM, -DM."""
    if len(values) < period:
        return []
    result = [sum(values[:period])]
    for v in values[period:]:
        result.append(result[-1] - result[-1] / period + v)
    return result


def compute_adx_series(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = ADX_PERIOD,
) -> tuple[list[float], int]:
    """
    Returns (adx_series, offset).
    adx_series[j] aligns to closes[offset + j].
    Offset = 2*period - 1  (27 for period=14).
    """
    n = len(closes)

    tr_list, plus_dm, minus_dm = [], [], []
    for i in range(1, n):
        tr = max(
            highs[i]  - lows[i],
            abs(highs[i]  - closes[i - 1]),
            abs(lows[i]   - closes[i - 1]),
        )
        tr_list.append(tr)
        up   = highs[i]    - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm.append(up   if (up > down   and up   > 0) else 0.0)
        minus_dm.append(down if (down > up  and down > 0) else 0.0)

    smooth_tr    = _wilder_sum_smooth(tr_list,  period)
    smooth_plus  = _wilder_sum_smooth(plus_dm,  period)
    smooth_minus = _wilder_sum_smooth(minus_dm, period)

    if not smooth_tr:
        return [], 0

    di_plus  = [100 * p / t if t > 0 else 0.0 for p, t in zip(smooth_plus,  smooth_tr)]
    di_minus = [100 * m / t if t > 0 else 0.0 for m, t in zip(smooth_minus, smooth_tr)]

    dx_list = []
    for p, m in zip(di_plus, di_minus):
        s = p + m
        dx_list.append(100 * abs(p - m) / s if s > 0 else 0.0)

    if len(dx_list) < period:
        return [], 0

    # ADX: average init then Wilder smoothing (matches regime_detection.py exactly)
    adx = sum(dx_list[:period]) / period
    adx_series = [adx]
    for dx in dx_list[period:]:
        adx = (adx * (period - 1) + dx) / period
        adx_series.append(adx)

    # Alignment derivation:
    #   tr_list[i]      -> bar i+1
    #   smooth_tr[0]    -> incorporates tr_list[0..period-1] -> bar period
    #   smooth_tr[k]    -> bar period + k
    #   dx_list[k]      -> bar period + k
    #   adx_series[0]   -> average of dx_list[0..period-1], latest at bar period + period - 1
    #   adx_series[j]   -> closes index: 2*period - 1 + j
    offset = 2 * period - 1
    return adx_series, offset


# ── Per-pair analysis ─────────────────────────────────────────────────────────

def analyze_pair(ticker: str, pip_mult: int, label: str) -> dict | None:
    bar = "=" * 72
    print(f"\n{bar}")
    print(f"  {label}  ({ticker})   5-Year D1 ADX Threshold Validation")
    print(bar)

    end   = datetime.today()
    start = end - timedelta(days=5 * 365 + 60)
    print(f"  Downloading {start.date()} -> {end.date()} ...")

    try:
        df = yf.download(
            ticker,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            interval="1d",
            auto_adjust=True,
            progress=False,
        )
    except Exception as exc:
        print(f"  ERROR: {exc}")
        return None

    if df.empty:
        print("  ERROR: no data returned")
        return None

    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)

    df = df.dropna(subset=["High", "Low", "Close"])
    highs  = df["High"].tolist()
    lows   = df["Low"].tolist()
    closes = df["Close"].tolist()
    n = len(closes)
    print(f"  Bars loaded : {n}")

    adx_series, offset = compute_adx_series(highs, lows, closes, ADX_PERIOD)
    if not adx_series:
        print("  ERROR: ADX computation failed")
        return None
    print(f"  ADX series  : {len(adx_series)} values  (aligned from bar index {offset})")

    # ── Build per-bar records ──────────────────────────────────────────────────
    records = []
    for j, adx_val in enumerate(adx_series):
        i = offset + j
        # Need slope lookback behind and outcome window ahead
        if i < SLOPE_LOOKBACK or i + OUTCOME_BARS >= n:
            continue

        slope        = closes[i] - closes[i - SLOPE_LOOKBACK]
        price_change = closes[i + OUTCOME_BARS] - closes[i]
        pip_move     = abs(price_change) * pip_mult

        if slope == 0:
            continue  # indeterminate direction — skip

        mom_win = (price_change > 0) if slope > 0 else (price_change < 0)

        records.append({
            "adx":     adx_val,
            "mom_win": mom_win,
            "pip":     pip_move,
        })

    if not records:
        print("  ERROR: no valid records")
        return None
    print(f"  Valid bars  : {len(records)}")

    # ── Band table ─────────────────────────────────────────────────────────────
    print()
    print(f"  {'Band':<8}  {'N':>5}  {'Mom%':>7}  {'RevM%':>7}  {'AvgPips':>9}  Edge")
    print("  " + "-" * 60)

    band_results: list[dict | None] = []

    for (lo, hi), lbl in zip(BANDS, BAND_LABELS):
        bucket = [r for r in records if lo <= r["adx"] < hi]
        N = len(bucket)

        if N == 0:
            print(f"  {lbl:<8}  {'0':>5}  {'—':>7}  {'—':>7}  {'—':>9}  insufficient data")
            band_results.append(None)
            continue

        mom_pct  = sum(r["mom_win"] for r in bucket) / N * 100
        rev_pct  = 100.0 - mom_pct
        avg_pips = sum(r["pip"] for r in bucket) / N

        if mom_pct >= MOMENTUM_THRESHOLD:
            edge = "MOMENTUM"
        elif rev_pct >= MOMENTUM_THRESHOLD:
            edge = "MEAN_REV"
        else:
            edge = "COIN_FLIP"

        print(
            f"  {lbl:<8}  {N:>5}  {mom_pct:>6.1f}%  {rev_pct:>6.1f}%"
            f"  {avg_pips:>8.1f}  {edge}"
        )
        band_results.append(
            dict(lo=lo, hi=hi, lbl=lbl, N=N,
                 mom_pct=mom_pct, rev_pct=rev_pct,
                 avg_pips=avg_pips, edge=edge)
        )

    # ── Find empirical threshold ───────────────────────────────────────────────
    # Lowest band where momentum >= 55% AND the next populated band also >= 55%
    empirical_threshold: int | None = None
    valid = [(idx, b) for idx, b in enumerate(band_results) if b is not None]

    for k, (_, b) in enumerate(valid):
        if b["mom_pct"] >= MOMENTUM_THRESHOLD:
            rest = [bb for _, bb in valid[k + 1:]]
            if not rest or rest[0]["mom_pct"] >= MOMENTUM_THRESHOLD:
                empirical_threshold = b["lo"]
                break

    # ── Threshold report ───────────────────────────────────────────────────────
    print()
    print("  -- Threshold Analysis " + "-" * 49)

    if empirical_threshold is not None:
        delta     = empirical_threshold - int(TEXTBOOK_ADX)
        direction = "LOWER" if delta < 0 else ("HIGHER" if delta > 0 else "SAME AS")
        print(f"  Empirical threshold : ADX >= {empirical_threshold}")
        print(f"  Textbook threshold  : ADX >= {TEXTBOOK_ADX:.0f}")
        print(f"  Delta               : {delta:+d}  ({direction} than Wilder's textbook value)")

        if delta < 0:
            action = (
                f"ACTION [{label}]: Lower trending threshold from {TEXTBOOK_ADX:.0f} "
                f"to {empirical_threshold}. Bars with ADX {empirical_threshold}-"
                f"{TEXTBOOK_ADX:.0f} already show momentum edge -- treating them "
                f"as ranging leaves alpha on the table."
            )
        elif delta > 0:
            action = (
                f"ACTION [{label}]: Raise trending threshold from {TEXTBOOK_ADX:.0f} "
                f"to {empirical_threshold}. ADX {TEXTBOOK_ADX:.0f}-{empirical_threshold} "
                f"does NOT yet show reliable momentum -- wait for stronger confirmation."
            )
        else:
            action = (
                f"ACTION [{label}]: Wilder's textbook value of {TEXTBOOK_ADX:.0f} is "
                f"empirically validated. No change required."
            )

        print(f"\n  {action}")
    else:
        print(
            f"  WARNING: No ADX band consistently reaches "
            f"{MOMENTUM_THRESHOLD:.0f}% momentum win rate."
        )
        print(
            f"\n  ACTION [{label}]: Momentum edge is unreliable on this pair. "
            f"Mean-reversion is the empirically dominant strategy."
        )

    return dict(
        label=label,
        ticker=ticker,
        n_records=len(records),
        band_results=band_results,
        empirical_threshold=empirical_threshold,
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    bar = "=" * 72
    print(f"\n{bar}")
    print("  ADX EMPIRICAL THRESHOLD VALIDATION")
    print(f"  Date      : {datetime.today().strftime('%Y-%m-%d')}")
    print(f"  Pairs     : GBP/AUD, GBP/JPY  |  Timeframe: D1  |  Lookback: 5 yr")
    print(f"  ADX       : Wilder(14), sum-init for TR/DM, avg-init for ADX smoothing")
    print(f"  Slope     : {SLOPE_LOOKBACK}-bar close delta for direction")
    print(f"  Outcome   : {OUTCOME_BARS}-bar forward close vs current close")
    print(
        f"  Threshold : momentum win rate >= {MOMENTUM_THRESHOLD:.0f}%  "
        f"(2 consecutive qualifying bands)"
    )
    print(bar)

    all_results: dict[str, dict] = {}
    for ticker, cfg in PAIRS.items():
        res = analyze_pair(ticker, cfg["pip_mult"], cfg["label"])
        if res:
            all_results[ticker] = res

    # ── Summary ────────────────────────────────────────────────────────────────
    print(f"\n{bar}")
    print("  SUMMARY -- EMPIRICAL vs TEXTBOOK ADX THRESHOLDS")
    print(bar)
    print(
        f"  {'Pair':<10}  {'Bars':>6}  {'Empirical':>10}  {'Textbook':>9}"
        f"  {'Delta':>7}  Recommendation"
    )
    print("  " + "-" * 68)

    for ticker, res in all_results.items():
        emp = res["empirical_threshold"]
        if emp is not None:
            delta     = emp - int(TEXTBOOK_ADX)
            delta_str = f"{delta:+d}"
            if delta < 0:
                rec = f"Use {emp} -- trends start earlier than Wilder assumed"
            elif delta > 0:
                rec = f"Use {emp} -- require stronger trend signal"
            else:
                rec = "Textbook value validated"
        else:
            delta_str = "  N/A"
            rec = "No momentum edge -- favour mean-reversion"

        print(
            f"  {res['label']:<10}  {res['n_records']:>6}  "
            f"{str(emp) if emp is not None else 'none':>10}  "
            f"{TEXTBOOK_ADX:>9.0f}  {delta_str:>7}  {rec}"
        )

    print()
    print(f"  Textbook baseline : ADX >= {TEXTBOOK_ADX:.0f} (J. Welles Wilder, 1978)")
    print(
        f"  Momentum criterion: >= {MOMENTUM_THRESHOLD:.0f}% win rate, "
        f"{OUTCOME_BARS}-bar forward window, 2 consecutive bands"
    )
    print(bar + "\n")


if __name__ == "__main__":
    main()
