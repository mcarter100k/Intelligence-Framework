"""
validate_h4_thresholds.py
─────────────────────────
Audit: does H4 regime classification have statistical edge?

Data: OANDA H4 (~4900 bars, ~3 years), D1 (~1300 bars, ~5 years), both pairs.

Method — identical rigor to validate_thresholds_v2.py:
  - Direction: _detect_structure() on H4 bars up to i (TRANSITIONAL → skip)
  - Non-overlapping FORWARD_BARS=30 H4 bars (= 5 trading days). Step = FORWARD_BARS.
  - Spread-adjust: 3.0 pips RT on net pips and momentum win
  - Framework functions imported directly: _compute_adx, compute_atr_series,
    _detect_structure, _classify, PAIRS, _ADX_PERIOD
  - MFE/MAE: raw pips (no spread on threshold check), bar-by-bar watermark,
    adverse-first tie-break on same bar

TABLE 1 — H4 ADX bands
TABLE 2 — H4 ATR ratio bands
TABLE 3 — H4 regime × D1 context  (the core cross-timeframe question)

Do NOT change regime_detection.py constants from this run.
"""
from __future__ import annotations

import os as _os, sys as _sys  # studies path bootstrap (root + shadow)
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
for _p in (_ROOT, _os.path.join(_ROOT, 'shadow')):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

import sys
import os
import time
import warnings
warnings.filterwarnings("ignore")


import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from historical_scenario_replay import _fetch_historical
from regime_detection import (
    PAIRS,
    _classify,
    _detect_structure,
    _compute_adx,
    compute_atr_series,
    _ADX_PERIOD,
)

# ── Constants ─────────────────────────────────────────────────────────────────

H4_BARS      = 4900      # max H4 request — ~3.1 years from today
D1_BARS      = 1300      # D1 bars for D1 context in TABLE 3
H4_WINDOW    = 120       # rolling H4 window for classification (mirrors production)
D1_WINDOW    = 220       # rolling D1 window for classification (mirrors production)
ATR_PERIOD   = 14
AVG_PERIOD   = 20
FORWARD_BARS = 30        # non-overlapping step: 30 H4 bars = 5 trading days
MIN_N        = 15        # N < MIN_N → INSUFFICIENT
SPREAD_PIPS  = 3.0       # round-trip spread cost (pips)
MFE_TARGET   = 150.0     # pips — MFE threshold
MAE_THRESH   = 100.0     # pips — MAE-first threshold

ADX_BANDS = [
    (0, 15), (15, 18), (18, 20), (20, 22), (22, 25),
    (25, 28), (28, 32), (32, 40), (40, 100),
]
ADX_LABELS = [
    " 0-15", "15-18", "18-20", "20-22", "22-25",
    "25-28", "28-32", "32-40", "  40+",
]

ATR_BANDS = [
    (0.0, 0.8), (0.8, 1.0), (1.0, 1.2), (1.2, 1.4),
    (1.4, 1.6), (1.6, 2.0), (2.0, 99.0),
]
ATR_LABELS = [
    "0.0-0.8x", "0.8-1.0x", "1.0-1.2x", "1.2-1.4x",
    "1.4-1.6x", "1.6-2.0x", "  2.0x+ ",
]

H4_REGIMES = ["TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE"]
D1_CONTEXTS = ["TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE"]


# ── Date helper ───────────────────────────────────────────────────────────────

def _last_trading_day() -> str:
    """Return last completed trading day as YYYY-MM-DD, skipping weekends."""
    now = datetime.now(timezone.utc)
    days_back = 0
    if now.weekday() == 5:    days_back = 1   # Saturday → Friday
    elif now.weekday() == 6:  days_back = 2   # Sunday   → Friday
    return (now - timedelta(days=days_back)).strftime("%Y-%m-%d")


# ── Per-bar regime classifier ─────────────────────────────────────────────────

def _classify_h4_bar(
    h4h: np.ndarray,
    h4l: np.ndarray,
    h4c: np.ndarray,
    i: int,
    pair,
) -> Tuple[Optional[str], float, float, str, Optional[int]]:
    """
    Classify H4 regime at bar i using up to H4_WINDOW prior bars.
    Returns (regime, adx, atr_ratio, structure_str, direction).
    direction is +1, -1, or None (TRANSITIONAL — caller should skip).
    """
    start = max(0, i - H4_WINDOW + 1)
    h = list(h4h[start : i + 1].astype(float))
    l = list(h4l[start : i + 1].astype(float))
    c = list(h4c[start : i + 1].astype(float))

    if len(c) < _ADX_PERIOD * 3:
        return None, 0.0, 1.0, "TRANSITIONAL", None

    atr_s = compute_atr_series(h, l, c)
    if len(atr_s) < AVG_PERIOD:
        return None, 0.0, 1.0, "TRANSITIONAL", None

    avg_atr   = sum(atr_s[-AVG_PERIOD:]) / AVG_PERIOD
    atr_ratio = atr_s[-1] / avg_atr if avg_atr > 0 else 1.0
    adx       = _compute_adx(h, l, c)
    struct    = _detect_structure(h, l, c)
    sstr      = struct.get("structure", "TRANSITIONAL")

    if sstr == "UPTREND":
        slope = 1.0; direction = 1
    elif sstr == "DOWNTREND":
        slope = -1.0; direction = -1
    else:
        slope = c[-1] - c[-10] if len(c) >= 10 else 0.0
        direction = None   # TRANSITIONAL — skip

    regime = _classify(adx, atr_ratio, slope,
                       pair=pair, instrument=pair.instrument)
    return regime, adx, atr_ratio, sstr, direction


def _d1_context_at_time(
    d1_df: pd.DataFrame,
    d1_h: np.ndarray,
    d1_l: np.ndarray,
    d1_c: np.ndarray,
    h4_ts,
    pair,
) -> str:
    """
    Return D1 regime at the time of h4_ts.
    Uses only D1 bars with timestamp strictly before h4_ts (no lookahead).
    """
    end = d1_df.index.searchsorted(h4_ts, side="left")
    if end < D1_WINDOW:
        return "TRANSITIONAL"

    start = max(0, end - D1_WINDOW)
    h = list(d1_h[start:end].astype(float))
    l = list(d1_l[start:end].astype(float))
    c = list(d1_c[start:end].astype(float))

    if len(c) < _ADX_PERIOD * 3:
        return "TRANSITIONAL"

    atr_s = compute_atr_series(h, l, c)
    if len(atr_s) < AVG_PERIOD:
        return "TRANSITIONAL"

    avg_atr   = sum(atr_s[-AVG_PERIOD:]) / AVG_PERIOD
    atr_ratio = atr_s[-1] / avg_atr if avg_atr > 0 else 1.0
    adx       = _compute_adx(h, l, c)
    struct    = _detect_structure(h, l, c)
    sstr      = struct.get("structure", "TRANSITIONAL")

    if sstr == "UPTREND":
        slope = 1.0
    elif sstr == "DOWNTREND":
        slope = -1.0
    else:
        slope = c[-1] - c[-10] if len(c) >= 10 else 0.0

    return _classify(adx, atr_ratio, slope,
                     pair=pair, instrument=pair.instrument)


# ── Forward metrics ───────────────────────────────────────────────────────────

def _forward_metrics(
    h4h: np.ndarray,
    h4l: np.ndarray,
    h4c: np.ndarray,
    i: int,
    direction: int,   # +1 LONG, -1 SHORT
    pip_size: float,
) -> Optional[Dict]:
    """
    Compute forward metrics from H4 entry bar i over the next FORWARD_BARS bars.

    mom_win:      net close-to-close in structure direction, spread-adjusted > 0
    mr_win:       net close-to-close toward 20-bar mean, spread-adjusted > 0
    net_pips:     direction * (close[i+30] - close[i]) / pip_size - SPREAD_PIPS
    mfe_150_hit:  max favorable excursion over 30 bars (via H/L watermark) >= 150 pips
    mae_100_first: MAE reached 100 pips before MFE reached 100 pips (adverse-first tie)
    """
    n   = len(h4c)
    end = i + FORWARD_BARS
    if end >= n:
        return None

    entry     = float(h4c[i])
    spread_px = SPREAD_PIPS * pip_size

    # Momentum win
    net_price = (float(h4c[end]) - entry) * direction
    net_pips  = net_price / pip_size - SPREAD_PIPS
    mom_win   = 1 if (net_price - spread_px) > 0 else 0

    # Mean reversion win
    mr_win = 0
    lb = max(0, i - 20)
    if i > lb:
        mean_20 = sum(float(h4c[k]) for k in range(lb, i)) / (i - lb)
        mr_gap  = mean_20 - entry
        if mr_gap != 0:
            mr_dir = 1 if mr_gap > 0 else -1
            mr_net = (float(h4c[end]) - entry) * mr_dir
            mr_win = 1 if (mr_net - spread_px) > 0 else 0

    # MFE scan: max favorable excursion over FORWARD_BARS bars
    mfe_pips = 0.0
    for j in range(i + 1, end + 1):
        if direction == 1:
            fav = (float(h4h[j]) - entry) / pip_size
        else:
            fav = (entry - float(h4l[j])) / pip_size
        mfe_pips = max(mfe_pips, fav)
    mfe_150_hit = 1 if mfe_pips >= MFE_TARGET else 0

    # MAE-first scan: did adverse reach 100 pips before favorable reached 100 pips?
    # Bar-by-bar watermark; adverse-first on same-bar tie.
    mfe_run = mae_run = 0.0
    mae_100_first = 0
    for j in range(i + 1, end + 1):
        if direction == 1:
            fav = (float(h4h[j]) - entry) / pip_size
            adv = (entry - float(h4l[j])) / pip_size
        else:
            fav = (entry - float(h4l[j])) / pip_size
            adv = (float(h4h[j]) - entry) / pip_size

        prev_mfe, prev_mae = mfe_run, mae_run
        mfe_run = max(mfe_run, fav)
        mae_run = max(mae_run, adv)

        mfe_x = (mfe_run >= MAE_THRESH) and (prev_mfe < MAE_THRESH)
        mae_x = (mae_run >= MAE_THRESH) and (prev_mae < MAE_THRESH)
        if mae_x and mfe_x:
            mae_100_first = 1; break   # same bar — adverse first
        elif mae_x:
            mae_100_first = 1; break
        elif mfe_x:
            mae_100_first = 0; break

    return {
        "mom_win":       mom_win,
        "mr_win":        mr_win,
        "net_pips":      net_pips,
        "mfe_pips":      mfe_pips,
        "mfe_150_hit":   mfe_150_hit,
        "mae_100_first": mae_100_first,
    }


# ── Observation builder ───────────────────────────────────────────────────────

def _build_observations(
    pair_key: str,
    h4_df: pd.DataFrame,
    d1_df: Optional[pd.DataFrame],
) -> Tuple[List[Dict], int, int]:
    """
    Scan H4 bars non-overlapping (step=FORWARD_BARS), compute regime + forward metrics.
    Returns (records, n_total_slots, n_transitional_skipped).
    """
    pair = PAIRS[pair_key]
    h4h  = h4_df["High"].values
    h4l  = h4_df["Low"].values
    h4c  = h4_df["Close"].values
    n_h4 = len(h4c)

    has_d1 = d1_df is not None and not d1_df.empty
    if has_d1:
        d1_h = d1_df["High"].values
        d1_l = d1_df["Low"].values
        d1_c = d1_df["Close"].values

    records:        List[Dict] = []
    n_total_slots  = 0
    n_transitional = 0

    i = H4_WINDOW   # start after warmup
    while i + FORWARD_BARS < n_h4:
        n_total_slots += 1
        h4_ts = h4_df.index[i]

        regime, adx, atr_r, sstr, direction = _classify_h4_bar(
            h4h, h4l, h4c, i, pair
        )

        if direction is None:
            n_transitional += 1
            i += FORWARD_BARS
            continue

        fwd = _forward_metrics(h4h, h4l, h4c, i, direction, pair.pip_size)
        if fwd is None:
            i += FORWARD_BARS
            continue

        d1_ctx = "UNAVAILABLE"
        if has_d1:
            d1_ctx = _d1_context_at_time(d1_df, d1_h, d1_l, d1_c, h4_ts, pair)

        records.append({
            "h4_regime":    regime,
            "h4_adx":       adx,
            "h4_atr_ratio": atr_r,
            "h4_structure": sstr,
            "direction":    direction,
            "d1_context":   d1_ctx,
            **fwd,
        })
        i += FORWARD_BARS

    return records, n_total_slots, n_transitional


# ── Table formatting helpers ──────────────────────────────────────────────────

_W = 80

_HDR = (f"  {'Band':<12}  {'N':>5}  {'Mom%':>7}  {'MR%':>7}"
        f"  {'AvgNet':>8}  {'MFE≥150%':>9}  {'MAEfirst%':>9}")
_SEP = "  " + "─" * (_W - 2)


def _row_stats(bucket: List[Dict]):
    n = len(bucket)
    if n == 0:
        return n, None, None, None, None, None
    mom = 100 * sum(r["mom_win"]       for r in bucket) / n
    mr  = 100 * sum(r["mr_win"]        for r in bucket) / n
    net = sum(r["net_pips"]            for r in bucket) / n
    mfe = 100 * sum(r["mfe_150_hit"]   for r in bucket) / n
    mae = 100 * sum(r["mae_100_first"] for r in bucket) / n
    return n, mom, mr, net, mfe, mae


def _fmt_row(label: str, n: int, mom, mr, net, mfe, mae) -> str:
    if n == 0:
        return (f"  {label:<12}  {'0':>5}  {'—':>7}  {'—':>7}"
                f"  {'—':>8}  {'—':>9}  {'—':>9}  no data")
    if n < MIN_N:
        return (f"  {label:<12}  {n:>5}  {'—':>7}  {'—':>7}"
                f"  {'—':>8}  {'—':>9}  {'—':>9}  INSUFFICIENT (N<{MIN_N})")
    edge = ("MOMENTUM" if mom >= 55.0
            else "MEAN_REV" if mr  >= 55.0
            else "COIN_FLIP")
    return (f"  {label:<12}  {n:>5}  {mom:>6.1f}%  {mr:>6.1f}%"
            f"  {net:>+7.1f}  {mfe:>8.1f}%  {mae:>8.1f}%  {edge}")


def _print_table1(records: List[Dict]) -> List[Dict]:
    results = []
    print(_HDR); print(_SEP)
    for (lo, hi), lbl in zip(ADX_BANDS, ADX_LABELS):
        bucket = [r for r in records if lo <= r["h4_adx"] < hi]
        n, mom, mr, net, mfe, mae = _row_stats(bucket)
        print(_fmt_row(lbl, n, mom, mr, net, mfe, mae))
        results.append({
            "lo": lo, "hi": hi, "N": n,
            "mom": mom, "mr": mr, "net": net,
            "mfe": mfe, "mae": mae,
            "insufficient": n < MIN_N,
        })
    return results


def _print_table2(records: List[Dict]) -> List[Dict]:
    results = []
    hdr = _HDR.replace("Band       ", "ATR Band   ", 1)
    print(hdr); print(_SEP)
    for (lo, hi), lbl in zip(ATR_BANDS, ATR_LABELS):
        bucket = [r for r in records if lo <= r["h4_atr_ratio"] < hi]
        n, mom, mr, net, mfe, mae = _row_stats(bucket)
        print(_fmt_row(lbl, n, mom, mr, net, mfe, mae))
        results.append({
            "lo": lo, "hi": hi, "N": n,
            "mom": mom, "mr": mr, "net": net,
            "mfe": mfe, "mae": mae,
            "insufficient": n < MIN_N,
        })
    return results


def _print_table3(records: List[Dict]) -> None:
    print(f"  {'H4 Regime':<16}  {'D1 Context':<16}  {'N':>5}  {'Mom%':>7}  {'AvgNet':>8}")
    print("  " + "─" * 60)

    for h4r in H4_REGIMES:
        h4_rows = [r for r in records if r["h4_regime"] == h4r]
        if not h4_rows:
            print(f"  {h4r:<16}  {'(no data)':<16}  {'0':>5}")
            continue

        for d1c in D1_CONTEXTS + ["TRANSITIONAL"]:
            bucket = [r for r in h4_rows if r["d1_context"] == d1c]
            if not bucket:
                continue
            n = len(bucket)
            if n < MIN_N:
                print(f"  {h4r:<16}  {d1c:<16}  {n:>5}  {'—':>7}  {'—':>8}  INSUFFICIENT (N<{MIN_N})")
            else:
                mom = 100 * sum(r["mom_win"] for r in bucket) / n
                net = sum(r["net_pips"]      for r in bucket) / n
                print(f"  {h4r:<16}  {d1c:<16}  {n:>5}  {mom:>6.1f}%  {net:>+7.1f}")

        # Subtotal for this H4 regime
        n = len(h4_rows)
        if n >= MIN_N:
            mom = 100 * sum(r["mom_win"] for r in h4_rows) / n
            net = sum(r["net_pips"]      for r in h4_rows) / n
            print(f"  {'  SUBTOTAL':<16}  {'(all D1)':<16}  {n:>5}  {mom:>6.1f}%  {net:>+7.1f}")
        else:
            print(f"  {'  SUBTOTAL':<16}  {'(all D1)':<16}  {n:>5}  {'—':>7}  {'—':>8}  INSUFFICIENT")
        print("  " + "─" * 60)


# ── Verdict section ───────────────────────────────────────────────────────────

def _print_verdict(
    pair_key: str,
    records: List[Dict],
    t1_results: List[Dict],
    t2_results: List[Dict],
) -> None:
    label   = PAIRS[pair_key].display_name
    n_total = len(records)

    print(f"\n  ── VERDICT [{label}] " + "─" * 52)

    # ── Q1: Total honest N ────────────────────────────────────────────────────
    print(f"\n  1. HONEST N")
    d1_n_ref = "33-43"  # from validate_thresholds_v2.py
    print(f"     H4 directional observations : {n_total}  (non-overlapping, structure-confirmed)")
    print(f"     D1 reference N (v2 audit)   : {d1_n_ref} per pair")
    if n_total < 60:
        print(f"     {n_total} < 60 — BELOW re-evaluation floor.")
        print(f"     Most per-band cells are INSUFFICIENT. All findings = INFORMED PRIORS.")
    elif n_total < 120:
        print(f"     Marginal — sufficient for TABLE 1/2 aggregate bands,"
              f" insufficient for most sub-cell splits.")
    else:
        print(f"     Sufficient for TABLE 1/2 aggregate analysis.")
    print(f"     H4 yields ~{round(n_total / 3)}/yr non-overlapping observations"
          f" vs D1's ~{round(int(d1_n_ref.split('-')[0]) / 5)}/yr."
          f" {round(n_total / 3 / max(1, int(d1_n_ref.split('-')[0]) // 5)):.0f}x more independent data per year.")

    # ── Q2: ADX threshold ─────────────────────────────────────────────────────
    print(f"\n  2. H4 ADX THRESHOLD — WHERE DOES MOMENTUM SEPARATE FROM MEAN REVERSION?")
    valid = [b for b in t1_results if not b["insufficient"] and b["mom"] is not None]
    mom_b = [b for b in valid if b["mom"] >= 55.0]
    mr_b  = [b for b in valid if b["mr"]  >= 55.0]

    if not valid:
        print(f"     All ADX bands INSUFFICIENT. No threshold conclusion possible.")
    elif mom_b:
        lowest_mom = min(mom_b, key=lambda b: b["lo"])
        peak_mom   = max(mom_b, key=lambda b: b["mom"])
        print(f"     Momentum edge (≥55%) first appears at ADX {lowest_mom['lo']}-{lowest_mom['hi']}.")
        print(f"     Peak: ADX {peak_mom['lo']}-{peak_mom['hi']} → "
              f"Mom={peak_mom['mom']:.1f}%, AvgNet={peak_mom['net']:+.1f} pips")
        if lowest_mom["lo"] < 25:
            print(f"     H4 momentum fires below D1 threshold (ADX 25). "
                  f"Expected — H4 trends are shorter-lived.")
        elif lowest_mom["lo"] == 25:
            print(f"     H4 threshold matches D1 (both ADX 25).")
        else:
            print(f"     H4 requires ADX {lowest_mom['lo']}+ — higher than D1 (ADX 25).")
    elif mr_b:
        top_mr = max(mr_b, key=lambda b: b["mr"])
        print(f"     No H4 ADX band achieves momentum edge (≥55%) after spread adjustment.")
        print(f"     Dominant signal: MEAN REVERSION (strongest: ADX {top_mr['lo']}-{top_mr['hi']},"
              f" MR={top_mr['mr']:.1f}%).")
        print(f"     This would indicate H4 is better suited for range-fading than trend-following.")
    else:
        print(f"     No band achieves ≥55% in either direction after spread adjustment.")
        print(f"     H4 shows COIN_FLIP across all ADX bands at this sample size.")

    # Specific check at transition zones
    volatile_band = next((b for b in t1_results if b["lo"] == 18 and b["hi"] == 25), None)
    if volatile_band and not volatile_band["insufficient"]:
        print(f"     ADX 18-25 combined (D1 VOLATILE zone): Mom={volatile_band['mom']:.1f}%,"
              f" AvgNet={volatile_band['net']:+.1f}")
    adx_18_20 = next((b for b in t1_results if b["lo"] == 18 and b["hi"] == 20), None)
    adx_20_22 = next((b for b in t1_results if b["lo"] == 20 and b["hi"] == 22), None)
    adx_22_25 = next((b for b in t1_results if b["lo"] == 22 and b["hi"] == 25), None)
    for b, label2 in [(adx_18_20, "18-20"), (adx_20_22, "20-22"), (adx_22_25, "22-25")]:
        if b and not b["insufficient"]:
            print(f"     ADX {label2}: Mom={b['mom']:.1f}%, AvgNet={b['net']:+.1f}")

    # ── Q3: ATR ratio behavior ────────────────────────────────────────────────
    print(f"\n  3. H4 ATR RATIO BEHAVIOR  (compare: D1 GBP/AUD degrades at 1.2x)")
    valid_atr = [b for b in t2_results if not b["insufficient"] and b["mom"] is not None]

    if not valid_atr:
        print(f"     All ATR bands INSUFFICIENT. No threshold conclusion possible.")
    else:
        deg_b     = [b for b in valid_atr if b["mom"] < 52.0 and b["mr"] < 52.0]
        mom_atr_b = [b for b in valid_atr if b["mom"] >= 55.0]

        norm_band = next((b for b in valid_atr if b["lo"] == 1.0 and b["hi"] == 1.2), None)
        if norm_band:
            print(f"     ATR ratio 1.0-1.2x (normal zone): "
                  f"Mom={norm_band['mom']:.1f}%, AvgNet={norm_band['net']:+.1f}")

        if deg_b:
            first_deg = min(deg_b, key=lambda b: b["lo"])
            print(f"     Signal degrades at {first_deg['lo']:.1f}x+ "
                  f"(mom {first_deg['mom']:.1f}% + MR {first_deg['mr']:.1f}% — both < 52%).")
            if abs(first_deg["lo"] - 1.2) < 0.05:
                print(f"     CONSISTENT with D1 GBP/AUD degradation threshold (1.2x).")
            elif first_deg["lo"] > 1.2:
                print(f"     H4 tolerates higher ATR than D1 — degrades at {first_deg['lo']:.1f}x vs D1's 1.2x.")
            else:
                print(f"     H4 degrades EARLIER than D1 (at {first_deg['lo']:.1f}x vs D1's 1.2x).")
        elif mom_atr_b:
            top = max(mom_atr_b, key=lambda b: b["mom"])
            print(f"     Best ATR band for momentum: {top['lo']:.1f}-{top['hi']:.1f}x → "
                  f"Mom={top['mom']:.1f}%, AvgNet={top['net']:+.1f}")
            print(f"     No degradation zone identified at this sample size.")
        else:
            print(f"     No ATR band shows clear momentum or degradation signal.")

    # ── Q4: D1 VOLATILE degradation ───────────────────────────────────────────
    print(f"\n  4. DOES D1 VOLATILE DEGRADE H4 TRENDING SETUPS? (TABLE 3 findings)")
    trending = [r for r in records
                if r["h4_regime"] in ("TRENDING_UP", "TRENDING_DOWN")]

    if not trending:
        print(f"     No H4 trending observations available.")
    else:
        d1_vol   = [r for r in trending if r["d1_context"] == "VOLATILE"]
        d1_trend = [r for r in trending
                    if r["d1_context"] in ("TRENDING_UP", "TRENDING_DOWN")]
        d1_range = [r for r in trending if r["d1_context"] == "RANGING"]

        def _show(subset, name):
            n = len(subset)
            tag = "INSUFFICIENT" if n < MIN_N else ""
            if n >= MIN_N:
                mom = 100 * sum(r["mom_win"] for r in subset) / n
                net = sum(r["net_pips"]      for r in subset) / n
                print(f"     H4 TRENDING + D1 {name}: N={n}, Mom={mom:.1f}%, AvgNet={net:+.1f}")
            else:
                print(f"     H4 TRENDING + D1 {name}: N={n}  {tag}")

        _show(d1_vol,   "VOLATILE ")
        _show(d1_trend, "TRENDING ")
        _show(d1_range, "RANGING  ")

        all_trending = trending
        if len(all_trending) >= MIN_N:
            mom = 100 * sum(r["mom_win"] for r in all_trending) / len(all_trending)
            net = sum(r["net_pips"]      for r in all_trending) / len(all_trending)
            print(f"     H4 TRENDING (all D1):        N={len(all_trending)}, "
                  f"Mom={mom:.1f}%, AvgNet={net:+.1f}")

        if len(d1_vol) >= MIN_N and len(d1_trend) >= MIN_N:
            net_vol   = sum(r["net_pips"] for r in d1_vol)   / len(d1_vol)
            net_trend = sum(r["net_pips"] for r in d1_trend) / len(d1_trend)
            delta     = net_trend - net_vol
            if delta > 10:
                print(f"\n     FINDING: D1 VOLATILE is {delta:.0f} pips WORSE than D1 TRENDING.")
                print(f"     The D1 stand-down rule IS DEGRADING H4 trending signal.")
                print(f"     Implications: D1 VOLATILE may be blocking profitable H4 entries.")
            elif delta < -10:
                print(f"\n     FINDING: D1 VOLATILE is {abs(delta):.0f} pips BETTER than D1 TRENDING.")
                print(f"     H4 trending setups are STRONGER when D1 is in volatile regime.")
                print(f"     This directly challenges the D1 stand-down rule.")
            else:
                print(f"\n     FINDING: D1 VOLATILE and TRENDING have similar H4 expectancy "
                      f"(delta={delta:+.0f} pips).")
                print(f"     D1 context does NOT degrade H4 trending setups at this N.")
        elif len(d1_vol) >= MIN_N or len(d1_trend) >= MIN_N:
            print(f"\n     FINDING: Cannot compare — only one group meets MIN_N={MIN_N}.")
        else:
            print(f"\n     FINDING: Both groups INSUFFICIENT — comparison deferred.")
            print(f"     Need {MIN_N - len(d1_vol)} more D1 VOLATILE + H4 trending observations.")

    # ── Q5: Recommendation ────────────────────────────────────────────────────
    print(f"\n  5. RECOMMENDATION: IS H4 A VIABLE DECISION TIMEFRAME?")

    valid_any = [b for b in t1_results if not b["insufficient"] and b["mom"] is not None]
    has_edge  = any(b["mom"] >= 55.0 or b["mr"] >= 55.0 for b in valid_any)

    if n_total < 60:
        print(f"     DEFERRED — N={n_total} is below the 60-observation evaluation floor.")
        print(f"     H4 provides ~{round(n_total / 3)}/yr observations vs D1's ~7/yr (step-5).")
        print(f"     On data volume alone, H4 is the stronger validation timeframe.")
        print(f"     Recommendation: re-evaluate after 60 non-overlapping logged outcomes.")
    elif has_edge:
        print(f"     SUPPORTED — H4 shows statistically meaningful signal with N={n_total}.")
        if mom_b:
            print(f"     Momentum edge exists at ADX {min(mom_b, key=lambda b: b['lo'])['lo']}+.")
        print(f"     H4 N is {round(n_total / max(1, 33)):.0f}x the D1 baseline.")
        print(f"     H4 is a VIABLE decision timeframe. Sub-cell analysis needs more data.")
    else:
        print(f"     INCONCLUSIVE — N={n_total} present but no band achieves ≥55% edge.")
        print(f"     H4 signal is not clearly stronger than D1 at this granularity.")
        print(f"     Do not re-anchor decision timeframe based on this run alone.")

    print(f"\n  ⚠  regime_detection.py constants: UNCHANGED.")
    print(f"     Re-evaluation trigger: 60+ non-overlapping logged outcomes per pair.")


# ── Per-pair runner ───────────────────────────────────────────────────────────

def analyze_pair(pair_key: str) -> None:
    pair      = PAIRS[pair_key]
    label     = pair.display_name
    pair_code = pair.instrument.replace("_", "")
    end_date  = _last_trading_day()

    print(f"\n{'═' * _W}")
    print(f"  {label}   validate_h4_thresholds")
    print(f"{'═' * _W}")

    t0 = time.perf_counter()

    print(f"  Fetching H4 ({H4_BARS}) ...", end=" ", flush=True)
    h4_df = _fetch_historical(pair_code, "H4", H4_BARS, end_date)
    n_h4  = len(h4_df) if h4_df is not None else 0
    print(f"{n_h4} bars")

    print(f"  Fetching D1 ({D1_BARS}) ...", end=" ", flush=True)
    d1_df = _fetch_historical(pair_code, "D", D1_BARS, end_date)
    n_d1  = len(d1_df) if d1_df is not None else 0
    print(f"{n_d1} bars")

    if h4_df is None or n_h4 < 200:
        print("  ERROR: insufficient H4 data — pair skipped")
        return

    print(f"  H4 range : {h4_df.index[0].date()} → {h4_df.index[-1].date()}")
    if d1_df is not None and not d1_df.empty:
        print(f"  D1 range : {d1_df.index[0].date()} → {d1_df.index[-1].date()}")
    else:
        print(f"  D1       : unavailable — TABLE 3 D1 context will be UNAVAILABLE")

    print(f"  Spread   : {SPREAD_PIPS} pip RT  |  "
          f"Forward: {FORWARD_BARS} H4 bars  |  "
          f"Step: {FORWARD_BARS} (non-overlapping)")
    print(f"  MFE: ≥{MFE_TARGET:.0f}pip  |  MAE-first: ≥{MAE_THRESH:.0f}pip  |  "
          f"Min N/band: {MIN_N}  |  "
          f"H4 window: {H4_WINDOW}  |  D1 window: {D1_WINDOW}")
    print(f"  Direction: _detect_structure() — P2 pivot, no lookahead")
    print()

    print("  Building observations ...", end=" ", flush=True)
    records, n_slots, n_trans = _build_observations(pair_key, h4_df, d1_df)
    elapsed = time.perf_counter() - t0
    n_used  = len(records)
    print(f"{n_used} directional observations  ({elapsed:.1f}s)")
    print(f"  Total non-overlapping slots : {n_slots}")
    print(f"  TRANSITIONAL skipped        : {n_trans}")
    print(f"  Directional observations    : {n_used}")
    if n_slots > 0:
        print(f"  Skip rate                   : {n_trans / n_slots * 100:.1f}%")

    if not records:
        print("  No directional observations — skipping tables.")
        return

    # ── TABLE 1 ───────────────────────────────────────────────────────────────
    print(f"\n{'─' * _W}")
    print(f"  TABLE 1 — H4 ADX BANDS  "
          f"(spread-adj, _detect_structure direction)")
    print(f"  {FORWARD_BARS}-bar forward  |  "
          f"MFE: max H/L excursion ≥{MFE_TARGET:.0f}pip  |  "
          f"MAE: adverse ≥{MAE_THRESH:.0f}pip before favorable ≥{MAE_THRESH:.0f}pip")
    print(f"{'─' * _W}")
    t1_results = _print_table1(records)

    # ── TABLE 2 ───────────────────────────────────────────────────────────────
    print(f"\n{'─' * _W}")
    print(f"  TABLE 2 — H4 ATR RATIO BANDS  "
          f"(spread-adj, _detect_structure direction)")
    print(f"{'─' * _W}")
    t2_results = _print_table2(records)

    # ── TABLE 3 ───────────────────────────────────────────────────────────────
    print(f"\n{'─' * _W}")
    print(f"  TABLE 3 — H4 REGIME × D1 CONTEXT")
    print(f"  Core question: does D1 VOLATILE degrade H4 trending setups?")
    print(f"  D1 context uses _d1_context_at_time() — no lookahead on D1 bars")
    print(f"{'─' * _W}")
    _print_table3(records)

    # ── VERDICT ───────────────────────────────────────────────────────────────
    print(f"\n{'─' * _W}")
    _print_verdict(pair_key, records, t1_results, t2_results)
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"\n{'═' * _W}")
    print("  VALIDATE H4 THRESHOLDS")
    print(f"  Date        : {_last_trading_day()}")
    print(f"  Data        : OANDA H4 (~{H4_BARS}), D1 (~{D1_BARS}) per pair")
    print(f"  Method      : _detect_structure() P2 pivot, non-overlapping "
          f"{FORWARD_BARS}-bar windows")
    print(f"  Spread      : {SPREAD_PIPS}pip RT on net/momentum metrics")
    print(f"  Min N       : {MIN_N} per band")
    print(f"  MFE target  : {MFE_TARGET:.0f}pip  |  MAE threshold: {MAE_THRESH:.0f}pip")
    print(f"  Framework   : _compute_adx, compute_atr_series, _detect_structure, _classify")
    print(f"  NOTE        : Do NOT change regime_detection.py constants from this run.")
    print(f"{'═' * _W}")

    for pair_key in ("GBP_AUD", "GBP_JPY"):
        analyze_pair(pair_key)

    print(f"\n{'═' * _W}")
    print("  RUN COMPLETE")
    print("  regime_detection.py constants: UNCHANGED")
    print(f"  Re-evaluation trigger: 60+ non-overlapping logged outcomes per pair.")
    print(f"{'═' * _W}\n")


if __name__ == "__main__":
    main()
