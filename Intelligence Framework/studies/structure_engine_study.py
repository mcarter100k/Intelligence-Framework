"""
structure_engine_study.py  (v2)
─────────────────────────────────────────────────────────────────────────────
Diagnostic: does consolidation → breakout have measurable edge on H4?

v2 changes vs v1:
  1. Three detector variants: RANGE_ONLY, COMPRESSION_ONLY, EITHER
  2. Wider param grid: N ∈ {6,8,12,18}, X ∈ {1.5,2.0,2.5,3.0}
  3. Variable thrust threshold table: 0.5, 0.75, 1.0, 1.25 × ATR
  4. Stacked filter funnel at best params
  5. Acid test: 4 known GBP/AUD moves vs detector output

No framework code changes.
"""
from __future__ import annotations

import os as _os, sys as _sys  # studies path bootstrap (project root)
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
for _p in (_ROOT,):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

import sys
import os
import time
import statistics
import warnings
warnings.filterwarnings("ignore")


import numpy as np
import pandas as pd
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

ATR_PERIOD           = 14
AVG_PERIOD           = 20
D1_WINDOW            = 220
FORWARD_BARS         = 30
MAX_BREAK_WAIT       = 10
PB_WINDOW            = 10
PB_ZONE              = 0.25
FAKEOUT_BARS         = 3
SPREAD_PIPS          = 3.0
MIN_N                = 20
COMPRESSION_THRESHOLD = 0.85   # box_atr_avg < 0.85 * prior_20bar_atr_ma

TOTAL_YEARS  = 3.1
H4_BARS      = 4900
D1_BARS      = 1300

# Widened grid: N ∈ {6,8,12,18}, X ∈ {1.5,2.0,2.5,3.0}
PARAM_GRID = [(N, X) for N in (6, 8, 12, 18) for X in (1.5, 2.0, 2.5, 3.0)]

# Detector variants
DETECTOR_VARIANTS = ("RANGE_ONLY", "COMPRESSION_ONLY", "EITHER")

# For COMPRESSION_ONLY: X is irrelevant — run only once per N
COMPRESSION_ONLY_GRID = [(N, 0.0) for N in (6, 8, 12, 18)]

THRUST_LEVELS = [0.5, 0.75, 1.0, 1.25]

# Known GBP/AUD moves for acid test
ACID_TEST_MOVES = [
    {"date": "2026-05-05", "direction": -1, "pips": 205, "desc": "205-pip DROP"},
    {"date": "2026-05-15", "direction":  1, "pips": 280, "desc": "280-pip RALLY"},
    {"date": "2026-06-22", "direction":  1, "pips": 270, "desc": "270-pip RALLY"},
    {"date": "2026-06-26", "direction":  1, "pips": 195, "desc": "195-pip RALLY"},
]

_W = 80


# ── Date helper ───────────────────────────────────────────────────────────────

def _last_trading_day() -> str:
    # Use the last COMPLETED FX session. Today's session does not close until
    # ~21:00 UTC, so `to = today T22:00Z` would be a FUTURE timestamp and OANDA
    # rejects the request (400 Bad Request). Step back to the most recent
    # completed weekday session (yesterday, or Friday over a weekend).
    d = datetime.now(timezone.utc) - timedelta(days=1)
    while d.weekday() >= 5:          # skip Saturday (5) / Sunday (6)
        d -= timedelta(days=1)
    return d.strftime("%Y-%m-%d")


# ── D1 info helper ────────────────────────────────────────────────────────────

def _d1_info_at_time(
    d1_df: pd.DataFrame,
    d1_h: np.ndarray,
    d1_l: np.ndarray,
    d1_c: np.ndarray,
    h4_ts,
    pair,
) -> Tuple[str, str]:
    end = d1_df.index.searchsorted(h4_ts, side="left")
    if end < D1_WINDOW:
        return "TRANSITIONAL", "TRANSITIONAL"
    start = max(0, end - D1_WINDOW)
    h = list(d1_h[start:end].astype(float))
    l = list(d1_l[start:end].astype(float))
    c = list(d1_c[start:end].astype(float))
    if len(c) < _ADX_PERIOD * 3:
        return "TRANSITIONAL", "TRANSITIONAL"
    atr_s = compute_atr_series(h, l, c)
    if len(atr_s) < AVG_PERIOD:
        return "TRANSITIONAL", "TRANSITIONAL"
    avg_atr   = sum(atr_s[-AVG_PERIOD:]) / AVG_PERIOD
    atr_ratio = atr_s[-1] / avg_atr if avg_atr > 0 else 1.0
    adx       = _compute_adx(h, l, c)
    struct    = _detect_structure(h, l, c)
    sstr      = struct.get("structure", "TRANSITIONAL")
    slope = (1.0  if sstr == "UPTREND"   else
             -1.0 if sstr == "DOWNTREND" else
             (c[-1] - c[-10]) if len(c) >= 10 else 0.0)
    regime = _classify(adx, atr_ratio, slope, pair=pair, instrument=pair.instrument)
    return regime, sstr


# ── Forward measurement ───────────────────────────────────────────────────────

def _measure_forward(
    h4h: np.ndarray,
    h4l: np.ndarray,
    h4c: np.ndarray,
    entry_bar: int,
    entry_price: float,
    stop_price: float,
    direction: int,
    pip_size: float,
    n: int,
) -> Optional[Dict]:
    end_bar = entry_bar + FORWARD_BARS
    if end_bar >= n:
        return None
    risk_pips = abs(entry_price - stop_price) / pip_size
    if risk_pips < 0.1:
        return None
    mfe = mae = 0.0
    stop_hit = False
    for j in range(entry_bar + 1, end_bar + 1):
        if direction == 1:
            fav = (float(h4h[j]) - entry_price) / pip_size
            adv = (entry_price - float(h4l[j])) / pip_size
            if float(h4l[j]) <= stop_price:
                stop_hit = True; break
        else:
            fav = (entry_price - float(h4l[j])) / pip_size
            adv = (float(h4h[j]) - entry_price) / pip_size
            if float(h4h[j]) >= stop_price:
                stop_hit = True; break
        mfe = max(mfe, fav)
        mae = max(mae, adv)
    if stop_hit:
        net_pips = -risk_pips - SPREAD_PIPS
    else:
        net_raw  = direction * (float(h4c[end_bar]) - entry_price) / pip_size
        net_pips = net_raw - SPREAD_PIPS
    r_mult = (mfe - SPREAD_PIPS) / risk_pips if risk_pips > 0 else 0.0
    return {
        "mfe_pips": mfe, "mae_pips": mae, "net_pips": net_pips,
        "stop_hit": stop_hit, "r_multiple": r_mult, "risk_pips": risk_pips,
    }


# ── Pullback scanner ──────────────────────────────────────────────────────────

def _scan_pullback(
    h4h: np.ndarray,
    h4l: np.ndarray,
    h4c: np.ndarray,
    break_bar: int,
    direction: int,
    box_high: float,
    box_low: float,
    atr_at_box: float,
    pip_size: float,
    n: int,
) -> Optional[Tuple[int, float]]:
    pb_zone    = PB_ZONE * atr_at_box
    pb_touched = False
    for j in range(break_bar + 1, min(break_bar + PB_WINDOW + 1, n)):
        close_j = float(h4c[j])
        low_j   = float(h4l[j])
        high_j  = float(h4h[j])
        if direction == 1:
            if low_j <= box_high + pb_zone:
                pb_touched = True
            if pb_touched and close_j > box_high:
                return j, close_j
        else:
            if high_j >= box_low - pb_zone:
                pb_touched = True
            if pb_touched and close_j < box_low:
                return j, close_j
    return None


# ── Core scanner ──────────────────────────────────────────────────────────────

def scan_param_set(
    N: int,
    X: float,
    variant: str,
    h4h: np.ndarray,
    h4l: np.ndarray,
    h4o: np.ndarray,
    h4c: np.ndarray,
    atr_s: List[float],
    h4_df: pd.DataFrame,
    d1_df: Optional[pd.DataFrame],
    d1_h: Optional[np.ndarray],
    d1_l: Optional[np.ndarray],
    d1_c: Optional[np.ndarray],
    pair,
) -> List[Dict]:
    pip_size = pair.pip_size
    n        = len(h4c)
    warmup   = ATR_PERIOD + AVG_PERIOD + max(N, 30) + 1
    events: List[Dict] = []
    has_d1 = d1_df is not None and not d1_df.empty

    i = warmup
    while i + FORWARD_BARS + MAX_BREAK_WAIT < n:
        j_atr = i - ATR_PERIOD
        if j_atr < N or j_atr < AVG_PERIOD or j_atr >= len(atr_s):
            i += 1; continue
        if j_atr - N + 1 < 0 or j_atr - AVG_PERIOD < 0:
            i += 1; continue

        box_h   = float(max(h4h[i - N + 1 : i + 1]))
        box_l   = float(min(h4l[i - N + 1 : i + 1]))
        box_rng = box_h - box_l
        atr_val = float(atr_s[j_atr])

        box_atr_avg  = sum(atr_s[j_atr - N + 1 : j_atr + 1]) / N
        prior_atr_ma = sum(atr_s[j_atr - AVG_PERIOD : j_atr]) / AVG_PERIOD

        range_ok = (atr_val > 0) and (box_rng <= X * atr_val)
        comp_ok  = (prior_atr_ma > 0) and (box_atr_avg < COMPRESSION_THRESHOLD * prior_atr_ma)

        if variant == "RANGE_ONLY":
            box_valid = range_ok
        elif variant == "COMPRESSION_ONLY":
            box_valid = comp_ok
        else:
            box_valid = range_ok or comp_ok

        if not box_valid:
            i += 1; continue

        # Location: compare to 30-bar context
        lb30   = max(0, i - 30)
        high30 = float(max(h4h[lb30 : i + 1]))
        low30  = float(min(h4l[lb30 : i + 1]))
        if abs(box_h - high30) <= atr_val:
            location = "AT_HIGH"
        elif abs(box_l - low30) <= atr_val:
            location = "AT_LOW"
        else:
            location = "MID"

        h4_ts   = h4_df.index[i]
        d1_reg  = "UNAVAILABLE"
        d1_sstr = "TRANSITIONAL"
        if has_d1:
            d1_reg, d1_sstr = _d1_info_at_time(d1_df, d1_h, d1_l, d1_c, h4_ts, pair)

        box = {
            "box_end_i":       i,
            "box_high":        box_h,
            "box_low":         box_l,
            "box_width_pips":  box_rng / pip_size,
            "bars_in_box":     N,
            "atr_at_box":      atr_val,
            "atr_ratio_at_box": box_atr_avg / prior_atr_ma if prior_atr_ma > 0 else 1.0,
            "location":        location,
            "d1_regime":       d1_reg,
            "d1_structure":    d1_sstr,
            "range_ok":        range_ok,
            "comp_ok":         comp_ok,
        }

        # Break scan
        brk = None
        was_outside = False
        for j in range(i + 1, min(i + MAX_BREAK_WAIT + 1, n)):
            close_j = float(h4c[j])
            body_j  = abs(float(h4c[j]) - float(h4o[j]))
            j_atr_j = j - ATR_PERIOD
            atr_j   = float(atr_s[j_atr_j]) if 0 <= j_atr_j < len(atr_s) else atr_val

            if close_j > box_h:
                if body_j >= 0.5 * atr_j:
                    brk = {"direction": 1, "bar": j, "price": close_j,
                           "thrust": body_j / atr_j if atr_j > 0 else 0.0}
                    break
                was_outside = True
            elif close_j < box_l:
                if body_j >= 0.5 * atr_j:
                    brk = {"direction": -1, "bar": j, "price": close_j,
                           "thrust": body_j / atr_j if atr_j > 0 else 0.0}
                    break
                was_outside = True
            else:
                if was_outside:
                    break

        if brk is None:
            events.append({"box": box, "break": None,
                           "model_a": None, "model_b": None,
                           "pb_missed": False, "missed_a_mfe": None})
            i += 1
            continue

        brk_bar   = brk["bar"]
        break_dir = brk["direction"]
        break_prc = brk["price"]
        d1_aligned = ((d1_sstr == "UPTREND"   and break_dir ==  1) or
                      (d1_sstr == "DOWNTREND" and break_dir == -1))

        if   (location == "AT_HIGH" and break_dir == -1): break_type = "REVERSAL"
        elif (location == "AT_LOW"  and break_dir ==  1): break_type = "REVERSAL"
        elif (location == "MID" and break_dir ==  1 and d1_sstr == "UPTREND"):
            break_type = "CONTINUATION"
        elif (location == "MID" and break_dir == -1 and d1_sstr == "DOWNTREND"):
            break_type = "CONTINUATION"
        else:
            break_type = "NEUTRAL"

        fakeout = False
        for k in range(brk_bar + 1, min(brk_bar + FAKEOUT_BARS + 1, n)):
            if box_l <= float(h4c[k]) <= box_h:
                fakeout = True; break

        break_event = {
            "direction":    break_dir,
            "price":        break_prc,
            "bar":          brk_bar,
            "thrust_ratio": brk["thrust"],
            "d1_aligned":   d1_aligned,
            "fakeout":      fakeout,
            "break_type":   break_type,
            "bars_until_break": brk_bar - i,
            "timestamp":    h4_df.index[brk_bar] if brk_bar < len(h4_df) else None,
        }

        stop    = box_l if break_dir == 1 else box_h
        model_a = _measure_forward(h4h, h4l, h4c, brk_bar, break_prc, stop, break_dir, pip_size, n)
        pb_result   = _scan_pullback(h4h, h4l, h4c, brk_bar, break_dir, box_h, box_l, atr_val, pip_size, n)
        model_b     = None
        pb_missed   = False
        missed_a_mfe = None

        if pb_result is None:
            pb_missed    = True
            missed_a_mfe = model_a["mfe_pips"] if model_a else None
        else:
            pb_bar, pb_prc = pb_result
            model_b = _measure_forward(h4h, h4l, h4c, pb_bar, pb_prc, stop, break_dir, pip_size, n)

        events.append({
            "box":          box,
            "break":        break_event,
            "model_a":      model_a,
            "model_b":      model_b,
            "pb_missed":    pb_missed,
            "missed_a_mfe": missed_a_mfe,
        })
        i = brk_bar + 1

    return events


# ── Statistics helpers ────────────────────────────────────────────────────────

def _med(vals):
    return statistics.median(vals) if vals else float("nan")

def _avg(vals):
    return sum(vals) / len(vals) if vals else float("nan")

def _pct(count, total):
    return f"{count/total*100:.1f}%" if total > 0 else "—"

def _isuff(n):
    return "" if n >= MIN_N else f"  INSUFFICIENT(N<{MIN_N})"

def _fmt(v, fmt=".1f", suffix=""):
    if v != v: return "—"
    return f"{v:{fmt}}{suffix}"


# ── TABLE F: parameter ranking for one variant ─────────────────────────────

def _compute_summary(events: List[Dict], N: int, X: float) -> Dict:
    all_brks = [e for e in events if e["break"] is not None]
    real     = [e for e in all_brks if not e["break"]["fakeout"]]
    n_brks   = len(all_brks)
    n_real   = len(real)
    fk_pct   = (n_brks - n_real) / n_brks * 100 if n_brks else 0.0
    mfes     = [e["model_a"]["mfe_pips"] for e in real if e["model_a"]]
    med_mfe  = _med(mfes) if n_real >= MIN_N else 0.0
    score    = (1.0 - fk_pct / 100) * med_mfe
    return {
        "N": N, "X": X,
        "n_boxes":     len(events),
        "n_breaks":    n_brks,
        "n_real":      n_real,
        "fakeout_pct": fk_pct,
        "breaks_yr":   n_brks / TOTAL_YEARS,
        "real_yr":     n_real / TOTAL_YEARS,
        "med_mfe":     med_mfe,
        "score":       score,
    }


def print_variant_table_f(summaries: List[Dict], variant: str, pair_label: str) -> None:
    ranked = sorted(summaries, key=lambda s: s["score"], reverse=True)
    x_col = "X" if variant != "COMPRESSION_ONLY" else " "
    print(f"  {'N':>4}  {x_col:>5}  {'boxes':>6}  {'brks':>5}  "
          f"{'brks/yr':>7}  {'real/yr':>7}  {'fake%':>6}  "
          f"{'realN':>5}  {'medMFE':>7}  {'score':>7}")
    print("  " + "─" * 72)
    for s in ranked[:8]:   # show top 8 rows to keep output manageable
        tag = "  ← BEST" if s == ranked[0] else ""
        x_str = f"{s['X']:.1f}" if variant != "COMPRESSION_ONLY" else "—"
        insuff = "*" if s["n_real"] < MIN_N else " "
        print(f"  {s['N']:>4}  {x_str:>5}  {s['n_boxes']:>6}  {s['n_breaks']:>5}  "
              f"{s['breaks_yr']:>7.1f}  {s['real_yr']:>7.1f}  "
              f"{s['fakeout_pct']:>5.1f}%  {s['n_real']:>5}{insuff} "
              f"{s['med_mfe']:>7.1f}  {s['score']:>7.1f}{tag}")
    if len(ranked) > 8:
        print(f"  ... ({len(ranked) - 8} more rows with lower scores)")


# ── Thrust threshold table ────────────────────────────────────────────────────

def print_thrust_table(events: List[Dict]) -> None:
    all_brks = [e for e in events if e["break"] is not None]
    if not all_brks:
        print("  No breaks to analyse.")
        return
    print(f"  {'Thrust':>9}  {'N kept':>6}  {'fake%':>6}  "
          f"{'realN':>6}  {'avgNetA':>8}  {'medMFE':>7}")
    print("  " + "─" * 52)
    for thr in THRUST_LEVELS:
        filtered = [e for e in all_brks if e["break"]["thrust_ratio"] >= thr]
        n_f      = len(filtered)
        if n_f == 0:
            print(f"  >= {thr:.2f}×    {'0':>6}  {'—':>6}  {'—':>6}  {'—':>8}  {'—':>7}")
            continue
        real     = [e for e in filtered if not e["break"]["fakeout"]]
        n_real   = len(real)
        fk_pct   = (n_f - n_real) / n_f * 100
        nets_a   = [e["model_a"]["net_pips"] for e in filtered if e["model_a"]]
        mfes     = [e["model_a"]["mfe_pips"] for e in real if e["model_a"]]
        avg_net  = _avg(nets_a) if nets_a else float("nan")
        insuff   = "*" if n_real < MIN_N else " "
        print(f"  >= {thr:.2f}×  {n_f:>6}  {fk_pct:>5.1f}%  "
              f"{n_real:>6}{insuff} {avg_net:>+8.1f}  {_fmt(_med(mfes)):>7}")


# ── Stacked filter funnel ─────────────────────────────────────────────────────

def print_stacked_funnel(events: List[Dict]) -> None:
    all_brks = [e for e in events if e["break"] is not None]
    if not all_brks:
        print("  No breaks available for funnel.")
        return

    def _row(label, subset, use_model_b=False):
        n = len(subset)
        if n == 0:
            print(f"  {label:<30}  N=0   no data")
            return
        fakes = sum(1 for e in subset if e["break"]["fakeout"])
        fk_pct = fakes / n * 100
        if use_model_b:
            entries = [e["model_b"] for e in subset if e["model_b"]]
        else:
            entries = [e["model_a"] for e in subset if e["model_a"]]
        if not entries:
            print(f"  {label:<30}  N={n:<4}  fake={fk_pct:.1f}%  no model data")
            return
        nets  = [m["net_pips"]  for m in entries]
        wins  = sum(1 for n_ in nets if n_ > 0)
        rs    = [m["r_multiple"] for m in entries]
        mfes  = [m["mfe_pips"]  for m in entries]
        insuff = "*" if len(entries) < MIN_N else " "
        print(f"  {label:<30}  N={n:<4}{insuff} fake={fk_pct:>4.1f}%  "
              f"win={_pct(wins,len(nets)):>6}  "
              f"avgNet={_avg(nets):>+7.1f}  medMFE={_fmt(_med(mfes)):>6}  medR={_fmt(_med(rs))}")

    print(f"  {'Stage':<30}  {'N':<5}  {'fake%':>6}  {'win%':>6}  "
          f"{'avgNet':>8}  {'medMFE':>7}  {'medR':>5}")
    print("  " + "─" * 74)

    # Stage 0: all breaks, Model A
    _row("All breaks (Model A)", all_brks)

    # Stage 1: thrust >= 0.75
    t75 = [e for e in all_brks if e["break"]["thrust_ratio"] >= 0.75]
    _row("+ thrust >= 0.75 (Model A)", t75)

    # Stage 2: thrust >= 1.0
    t10 = [e for e in all_brks if e["break"]["thrust_ratio"] >= 1.0]
    _row("+ thrust >= 1.0  (Model A)", t10)

    # Stage 3: thrust >= 1.0, real breaks only, Model B (pullback)
    t10_with_pb = [e for e in t10 if not e["break"]["fakeout"] and e["model_b"] is not None]
    _row("+ pullback entry (Model B)", t10_with_pb, use_model_b=True)

    # Stage 4: stage 3 + D1 aligned
    t10_pb_aligned = [e for e in t10_with_pb if e["break"]["d1_aligned"]]
    _row("+ D1 structure aligned     ", t10_pb_aligned, use_model_b=True)

    # Missed-move cost
    t10_real_no_pb = [e for e in t10 if not e["break"]["fakeout"] and e["pb_missed"]]
    if t10_real_no_pb:
        missed_mfes = [e["missed_a_mfe"] for e in t10_real_no_pb if e["missed_a_mfe"] is not None]
        n_total_t10_real = sum(1 for e in t10 if not e["break"]["fakeout"])
        print()
        print(f"  Pullback cost: {len(t10_real_no_pb)}/{n_total_t10_real} real breaks had no pullback"
              f"  (missed avg MFE = {_avg(missed_mfes):.1f} pip)")


# ── Acid test: 4 known GBP/AUD moves ─────────────────────────────────────────

def _find_bar_idx(h4_df: pd.DataFrame, date_str: str) -> int:
    ts  = pd.Timestamp(date_str, tz="UTC")
    idx = h4_df.index.searchsorted(ts, side="left")
    return min(idx, len(h4_df) - 1)


def _diagnose_at_bar(
    h4h, h4l, h4c, h4_df, atr_s, target_idx: int, pair,
) -> str:
    """Return a one-line diagnosis of what condition state looks like at target_idx."""
    pip_size = pair.pip_size
    lines = []
    for N in (6, 8, 12, 18):
        j_atr = target_idx - ATR_PERIOD
        if j_atr < N or j_atr < AVG_PERIOD or j_atr >= len(atr_s):
            lines.append(f"    N={N:>2}: insufficient warmup")
            continue
        if j_atr - N + 1 < 0:
            continue
        box_h   = float(max(h4h[target_idx - N + 1 : target_idx + 1]))
        box_l   = float(min(h4l[target_idx - N + 1 : target_idx + 1]))
        box_rng = box_h - box_l
        atr_val = float(atr_s[j_atr])
        box_atr_avg  = sum(atr_s[j_atr - N + 1 : j_atr + 1]) / N
        prior_atr_ma = sum(atr_s[j_atr - AVG_PERIOD : j_atr]) / AVG_PERIOD if j_atr >= AVG_PERIOD else 0.0
        rng_pips  = box_rng / pip_size
        atr_pips  = atr_val / pip_size
        comp_ratio = box_atr_avg / prior_atr_ma if prior_atr_ma > 0 else 99.0
        range_results = []
        for X in (1.5, 2.0, 2.5, 3.0):
            ok = atr_val > 0 and box_rng <= X * atr_val
            range_results.append(f"X={X:.1f}:{'OK' if ok else f'FAIL({rng_pips:.0f}>{X*atr_pips:.0f}pip)'}")
        comp_ok = prior_atr_ma > 0 and box_atr_avg < COMPRESSION_THRESHOLD * prior_atr_ma
        lines.append(f"    N={N:>2}: range={rng_pips:.0f}pip  ATR={atr_pips:.0f}pip  "
                     f"comp_ratio={comp_ratio:.2f}({'OK' if comp_ok else f'FAIL>={COMPRESSION_THRESHOLD}'})")
        lines.append(f"           range_check: {' | '.join(range_results)}")
    return "\n".join(lines)


def acid_test(
    h4h, h4l, h4o, h4c, h4_df, atr_s,
    best_events: List[Dict], best_variant: str, best_N: int, best_X: float,
    pair,
) -> None:
    pip_size = pair.pip_size
    print(f"\n{'─' * _W}")
    print(f"  ACID TEST — 4 known GBP/AUD moves")
    print(f"  Detector: {best_variant}  N={best_N}  X={best_X:.1f}")
    print(f"  Break window checked: target_date ±6 H4 bars (±1.5 trading days)")
    print(f"{'─' * _W}")

    for move in ACID_TEST_MOVES:
        date_str = move["date"]
        exp_dir  = move["direction"]
        exp_pips = move["pips"]
        desc     = move["desc"]

        target_idx = _find_bar_idx(h4_df, date_str)
        if target_idx >= len(h4_df):
            print(f"\n  {date_str} ({desc}): date beyond data range — skip")
            continue

        target_ts = h4_df.index[target_idx]
        print(f"\n  ─── {date_str}  {desc} ───")
        print(f"  Nearest H4 bar: {target_ts}  (idx={target_idx})")

        # Search for breaks within [-6, +2] bars of target
        LOOK_BEFORE = 6
        LOOK_AFTER  = 2
        nearby_breaks = [
            e for e in best_events
            if e["break"] is not None
            and (target_idx - LOOK_BEFORE) <= e["break"]["bar"] <= (target_idx + LOOK_AFTER)
        ]

        # Also check for boxes that ended near target but had no break
        nearby_boxes_no_break = [
            e for e in best_events
            if e["break"] is None
            and (target_idx - LOOK_BEFORE - best_N) <= e["box"]["box_end_i"] <= (target_idx + 2)
        ]

        if nearby_breaks:
            for ev in nearby_breaks:
                brk     = ev["break"]
                box     = ev["box"]
                dir_str = "UP" if brk["direction"] == 1 else "DOWN"
                match   = "MATCH" if brk["direction"] == exp_dir else "WRONG WAY"
                fk_str  = "FAKEOUT" if brk["fakeout"] else "REAL"
                print(f"  BREAK FOUND ({fk_str})  bar={brk['bar']}  ts={brk['timestamp']}")
                print(f"    direction={dir_str}  expected={('UP' if exp_dir==1 else 'DOWN')}  → {match}")
                print(f"    thrust_ratio={brk['thrust_ratio']:.2f}  "
                      f"box_width={box['box_width_pips']:.0f}pip  "
                      f"comp_ok={box['comp_ok']}  range_ok={box['range_ok']}")
                if not brk["fakeout"] and ev["model_a"]:
                    ma = ev["model_a"]
                    print(f"    Model A: net={ma['net_pips']:+.1f}pip  "
                          f"MFE={ma['mfe_pips']:.0f}pip  stop_hit={ma['stop_hit']}")
                if not brk["fakeout"] and ev["model_b"]:
                    mb = ev["model_b"]
                    print(f"    Model B: net={mb['net_pips']:+.1f}pip  "
                          f"MFE={mb['mfe_pips']:.0f}pip")
                elif not brk["fakeout"] and ev["pb_missed"]:
                    print(f"    Model B: no pullback (missed MFE={ev['missed_a_mfe']:.0f}pip)")
        else:
            print(f"  NO BREAK detected near this date.")
            if nearby_boxes_no_break:
                print(f"  Box(es) found but no break within {MAX_BREAK_WAIT} bars:")
                for ev in nearby_boxes_no_break[:2]:
                    box = ev["box"]
                    print(f"    box_end={box['box_end_i']}  "
                          f"width={box['box_width_pips']:.0f}pip  "
                          f"range_ok={box['range_ok']}  comp_ok={box['comp_ok']}")
            else:
                print(f"  No box detected either. Condition check at target bar:")
                diag = _diagnose_at_bar(h4h, h4l, h4c, h4_df, atr_s, target_idx, pair)
                print(diag)
                # Also check 3 bars before target (box end precedes break by 1+ bars)
                print(f"  Condition check 3 bars before target (box would end ~{date_str} - 12h):")
                diag2 = _diagnose_at_bar(h4h, h4l, h4c, h4_df, atr_s, max(0, target_idx - 3), pair)
                print(diag2)


# ── TABLE B (best params): Model A vs Model B ────────────────────────────────

def print_table_b(events: List[Dict]) -> None:
    real = [e for e in events if e["break"] and not e["break"]["fakeout"]]
    n_real = len(real)
    if n_real < MIN_N:
        print(f"  TABLE B — real N={n_real}  INSUFFICIENT (N<{MIN_N})")
        return

    a_all   = [e["model_a"] for e in real if e["model_a"]]
    b_all   = [e["model_b"] for e in real if e["model_b"]]
    missed  = [e for e in real if e["pb_missed"] and e["missed_a_mfe"] is not None]

    def _stats(entries):
        if not entries: return None
        mfes  = [e["mfe_pips"]  for e in entries]
        maes  = [e["mae_pips"]  for e in entries]
        nets  = [e["net_pips"]  for e in entries]
        rs    = [e["r_multiple"] for e in entries]
        stops = sum(1 for e in entries if e["stop_hit"])
        wins  = sum(1 for e in entries if e["net_pips"] > 0)
        return {"n": len(entries), "win": wins/len(entries)*100, "med_mfe": _med(mfes),
                "med_mae": _med(maes), "stop": stops/len(entries)*100,
                "avg_net": _avg(nets), "med_r": _med(rs)}

    sa = _stats(a_all)
    sb = _stats(b_all)

    print(f"  {'Metric':<18}  {'Model A (break)':>16}  {'Model B (pullback)':>18}")
    print("  " + "─" * 58)
    if sa:
        def _col(sa_val, sb_val):
            return f"{sb_val:>18}" if sb_val is not None else f"{'—':>18}"
        print(f"  {'N entries':<18}  {sa['n']:>16}  {sb['n'] if sb else '—':>18}")
        print(f"  {'Win rate':<18}  {sa['win']:>15.1f}%  {_fmt(sb['win'] if sb else float('nan'),'>.1f','%'):>18}")
        print(f"  {'Median MFE':<18}  {sa['med_mfe']:>16.1f}  {_fmt(sb['med_mfe'] if sb else float('nan'),'>.1f'):>18}")
        print(f"  {'Median MAE':<18}  {sa['med_mae']:>16.1f}  {_fmt(sb['med_mae'] if sb else float('nan'),'>.1f'):>18}")
        print(f"  {'Stop-hit %':<18}  {sa['stop']:>15.1f}%  {_fmt(sb['stop'] if sb else float('nan'),'>.1f','%'):>18}")
        print(f"  {'Avg net':<18}  {sa['avg_net']:>+16.1f}  {_fmt(sb['avg_net'] if sb else float('nan'),'>+.1f'):>18}")
        print(f"  {'Median R':<18}  {sa['med_r']:>16.2f}  {_fmt(sb['med_r'] if sb else float('nan'),'>.2f'):>18}")

    if missed:
        avg_missed = _avg([e["missed_a_mfe"] for e in missed])
        print("  " + "─" * 58)
        print(f"  Model B: NO_PULLBACK = {len(missed)}/{n_real} real breaks"
              f"  (avg missed MFE = {avg_missed:.1f} pip)")


# ── TABLE C: fakeout vs real separation ──────────────────────────────────────

def print_table_c(events: List[Dict]) -> None:
    real    = [e for e in events if e["break"] and not e["break"]["fakeout"]]
    fakeout = [e for e in events if e["break"] and     e["break"]["fakeout"]]

    def _grp(grp, label):
        if not grp: return
        tag    = _isuff(len(grp))
        thrust = [e["break"]["thrust_ratio"] for e in grp]
        width  = [e["box"]["box_width_pips"] for e in grp]
        n_aln  = sum(1 for e in grp if e["break"]["d1_aligned"])
        loc    = {k: sum(1 for e in grp if e["box"]["location"] == k) for k in ("AT_HIGH","AT_LOW","MID")}
        n      = len(grp)
        print(f"  {label} (N={n}){tag}")
        if n >= 3:
            print(f"    thrust_ratio: median={_fmt(_med(thrust))}")
            print(f"    box_width_pip: median={_fmt(_med(width))}")
            print(f"    D1 aligned: {n_aln}/{n} = {_pct(n_aln,n)}")
            print(f"    location: AT_HIGH={loc['AT_HIGH']}  AT_LOW={loc['AT_LOW']}  MID={loc['MID']}")

    _grp(fakeout, "FAKEOUT")
    _grp(real,    "REAL BREAK")
    nr, nf = len(real), len(fakeout)
    if nr >= 3 and nf >= 3:
        tr = _med([e["break"]["thrust_ratio"] for e in real])
        tf = _med([e["break"]["thrust_ratio"] for e in fakeout])
        ar = sum(1 for e in real    if e["break"]["d1_aligned"]) / nr
        af = sum(1 for e in fakeout if e["break"]["d1_aligned"]) / nf
        print(f"  SEPARATION: thrust {tr:.2f}(real) vs {tf:.2f}(fake)  delta={abs(tr-tf):.2f}")
        print(f"             D1 aligned {ar*100:.0f}%(real) vs {af*100:.0f}%(fake)")


# ── TABLE D: break type ───────────────────────────────────────────────────────

def print_table_d(events: List[Dict]) -> None:
    real = [e for e in events if e["break"] and not e["break"]["fakeout"] and e["model_a"]]
    all_brks = [e for e in events if e["break"]]
    for bt in ("REVERSAL", "CONTINUATION", "NEUTRAL"):
        grp  = [e for e in real if e["break"]["break_type"] == bt]
        n_all_bt = sum(1 for e in all_brks if e["break"]["break_type"] == bt)
        fk_rate  = sum(1 for e in all_brks if e["break"]["break_type"] == bt
                       and e["break"]["fakeout"]) / n_all_bt * 100 if n_all_bt else 0.0
        n   = len(grp)
        tag = _isuff(n)
        if n == 0:
            print(f"  {bt:<14}: N=0  all breaks fakeout or no data")
            continue
        nets = [e["model_a"]["net_pips"] for e in grp]
        mfes = [e["model_a"]["mfe_pips"] for e in grp]
        wins = sum(1 for e in grp if e["model_a"]["net_pips"] > 0)
        print(f"  {bt:<14}: realN={n}{tag}  fakeout={fk_rate:.1f}%"
              f"  medMFE={_fmt(_med(mfes))}  win%={_pct(wins,n)}"
              f"  avgNet={_fmt(_avg(nets),'+.1f')}")


# ── TABLE E: D1 context filter ────────────────────────────────────────────────

def print_table_e(events: List[Dict]) -> None:
    all_brks = [e for e in events if e["break"]]
    for aligned, label in [(True, "D1 ALIGNED"), (False, "D1 AGAINST"), ("TRANS", "D1 TRANSITIONAL")]:
        if aligned == "TRANS":
            grp = [e for e in all_brks if e["box"]["d1_structure"] == "TRANSITIONAL"]
        else:
            grp = [e for e in all_brks
                   if e["box"]["d1_structure"] != "TRANSITIONAL"
                   and e["break"]["d1_aligned"] == aligned]
        n = len(grp)
        if n == 0: continue
        tag   = _isuff(n)
        fakes = sum(1 for e in grp if e["break"]["fakeout"])
        real_grp = [e for e in grp if not e["break"]["fakeout"] and e["model_a"]]
        mfes = [e["model_a"]["mfe_pips"] for e in real_grp]
        nets = [e["model_a"]["net_pips"] for e in real_grp]
        print(f"  {label:<20}: N={n}{tag}  fakeout={_pct(fakes,n)}"
              f"  medMFE={_fmt(_med(mfes)) if mfes else '—'}"
              f"  avgNet={_fmt(_avg(nets),'+.1f') if nets else '—'}")


# ── Per-pair runner ───────────────────────────────────────────────────────────

def analyze_pair(pair_key: str) -> None:
    pair      = PAIRS[pair_key]
    label     = pair.display_name
    pair_code = pair.instrument.replace("_", "")
    end_date  = _last_trading_day()
    is_gbpaud = (pair_key == "GBP_AUD")

    print(f"\n{'═' * _W}")
    print(f"  {label}   structure_engine_study  v2")
    print(f"{'═' * _W}")

    t0 = time.perf_counter()

    print(f"  Fetching H4 ({H4_BARS}) ...", end=" ", flush=True)
    h4_df = _fetch_historical(pair_code, "H4", H4_BARS, end_date)
    n_h4  = len(h4_df) if h4_df is not None else 0
    print(f"{n_h4} bars")

    print(f"  Fetching D1 ({D1_BARS}) ...", end=" ", flush=True)
    d1_df = _fetch_historical(pair_code, "D",  D1_BARS, end_date)
    n_d1  = len(d1_df) if d1_df is not None else 0
    print(f"{n_d1} bars")

    if h4_df is None or n_h4 < 200:
        print("  ERROR: insufficient H4 data"); return

    print(f"  H4: {h4_df.index[0].date()} → {h4_df.index[-1].date()}")
    if d1_df is not None and not d1_df.empty:
        print(f"  D1: {d1_df.index[0].date()} → {d1_df.index[-1].date()}")

    h4h = h4_df["High"].values
    h4l = h4_df["Low"].values
    h4o = h4_df["Open"].values
    h4c = h4_df["Close"].values

    atr_s = compute_atr_series(
        list(h4h.astype(float)), list(h4l.astype(float)), list(h4c.astype(float)),
        ATR_PERIOD
    )

    has_d1 = d1_df is not None and not d1_df.empty
    d1_h   = d1_df["High"].values  if has_d1 else None
    d1_l   = d1_df["Low"].values   if has_d1 else None
    d1_c   = d1_df["Close"].values if has_d1 else None

    print(f"\n  Variants: {', '.join(DETECTOR_VARIANTS)}")
    print(f"  RANGE_ONLY/EITHER grid: N∈{{6,8,12,18}} × X∈{{1.5,2.0,2.5,3.0}}  (16 combos)")
    print(f"  COMPRESSION_ONLY grid: N∈{{6,8,12,18}}  (4 combos, X ignored)")
    print(f"  Thrust baseline: 0.5×ATR  |  Spread: {SPREAD_PIPS}pip  |  Fwd: {FORWARD_BARS} H4")

    # ── Run all variants × params ─────────────────────────────────────────────
    all_results: Dict[Tuple, List[Dict]] = {}

    for variant in DETECTOR_VARIANTS:
        pg = COMPRESSION_ONLY_GRID if variant == "COMPRESSION_ONLY" else PARAM_GRID
        for (N, X) in pg:
            key = (variant, N, X)
            all_results[key] = scan_param_set(
                N, X, variant, h4h, h4l, h4o, h4c, atr_s,
                h4_df, d1_df, d1_h, d1_l, d1_c, pair
            )

    elapsed = time.perf_counter() - t0
    print(f"  Scan complete ({elapsed:.1f}s)")

    # ── TABLE F per variant ───────────────────────────────────────────────────
    best_per_variant: Dict[str, Tuple] = {}
    best_score_overall = -1.0
    best_key_overall   = None

    for variant in DETECTOR_VARIANTS:
        pg = COMPRESSION_ONLY_GRID if variant == "COMPRESSION_ONLY" else PARAM_GRID
        summaries = [_compute_summary(all_results[(variant, N, X)], N, X) for (N, X) in pg]

        print(f"\n{'─' * _W}")
        print(f"  TABLE F — {variant}  [{label}]")
        print(f"  Score = (1-fake%) × medMFE  |  * = INSUFFICIENT(N<{MIN_N})")
        print(f"{'─' * _W}")
        print_variant_table_f(summaries, variant, label)

        best_s = max(summaries, key=lambda s: s["score"])
        best_per_variant[variant] = (best_s["N"], best_s["X"])
        if best_s["score"] > best_score_overall:
            best_score_overall = best_s["score"]
            best_key_overall   = (variant, best_s["N"], best_s["X"])

    if best_key_overall is None:
        print("\n  All param sets insufficient — no best candidate."); return

    bv, bN, bX = best_key_overall
    best_events = all_results[best_key_overall]

    print(f"\n{'─' * _W}")
    print(f"  OVERALL BEST: {bv}  N={bN}  X={bX:.1f}  score={best_score_overall:.1f}")
    print(f"  Tables below use this param set.")
    print(f"{'─' * _W}")

    # ── Thrust threshold table ────────────────────────────────────────────────
    all_best_breaks = [e for e in best_events if e["break"] is not None]
    print(f"\n{'─' * _W}")
    print(f"  THRUST THRESHOLD TABLE  [{bv}  N={bN}  X={bX:.1f}]  [{label}]")
    print(f"  Effect of raising minimum thrust. avgNet = Model A, all breaks (incl fakeouts).")
    print(f"{'─' * _W}")
    print_thrust_table(best_events)

    # ── TABLE B ───────────────────────────────────────────────────────────────
    print(f"\n{'─' * _W}")
    print(f"  TABLE B — MODEL A vs MODEL B  [{bv}  N={bN}  X={bX:.1f}]  [{label}]")
    print(f"{'─' * _W}")
    print_table_b(best_events)

    # ── TABLE C ───────────────────────────────────────────────────────────────
    print(f"\n{'─' * _W}")
    print(f"  TABLE C — FAKEOUT vs REAL  [{bv}  N={bN}  X={bX:.1f}]  [{label}]")
    print(f"{'─' * _W}")
    print_table_c(best_events)

    # ── TABLE D ───────────────────────────────────────────────────────────────
    print(f"\n{'─' * _W}")
    print(f"  TABLE D — BREAK TYPE  [{label}]")
    print(f"{'─' * _W}")
    print_table_d(best_events)

    # ── TABLE E ───────────────────────────────────────────────────────────────
    print(f"\n{'─' * _W}")
    print(f"  TABLE E — D1 CONTEXT  [{label}]")
    print(f"{'─' * _W}")
    print_table_e(best_events)

    # ── STACKED FILTER FUNNEL ─────────────────────────────────────────────────
    print(f"\n{'─' * _W}")
    print(f"  STACKED FILTER FUNNEL  [{bv}  N={bN}  X={bX:.1f}]  [{label}]")
    print(f"  Cumulative filters. * = N < {MIN_N}.")
    print(f"{'─' * _W}")
    print_stacked_funnel(best_events)

    # ── ACID TEST (GBP/AUD only) ──────────────────────────────────────────────
    if is_gbpaud:
        acid_test(h4h, h4l, h4o, h4c, h4_df, atr_s,
                  best_events, bv, bN, bX, pair)

    # ── VERDICT ───────────────────────────────────────────────────────────────
    print(f"\n{'─' * _W}")
    print(f"  VERDICT  [{label}]")
    print(f"{'─' * _W}")

    real_best = [e for e in best_events if e["break"] and not e["break"]["fakeout"]]
    all_brks  = [e for e in best_events if e["break"]]
    n_real    = len(real_best)
    n_brks    = len(all_brks)
    fk_pct    = (n_brks - n_real) / n_brks * 100 if n_brks > 0 else 0.0
    mfes_a    = [e["model_a"]["mfe_pips"] for e in real_best if e["model_a"]]
    nets_a    = [e["model_a"]["net_pips"] for e in real_best if e["model_a"]]

    print(f"\n  1. SIGNALS/YEAR (best: {bv}  N={bN}  X={bX:.1f})")
    print(f"     Total breaks: {n_brks} ({n_brks/TOTAL_YEARS:.1f}/yr)"
          f"  Real: {n_real} ({n_real/TOTAL_YEARS:.1f}/yr)"
          f"  {'SUFFICIENT' if n_real >= MIN_N else 'INSUFFICIENT'}")

    print(f"\n  2. BEST VARIANT")
    for variant in DETECTOR_VARIANTS:
        pg = COMPRESSION_ONLY_GRID if variant == "COMPRESSION_ONLY" else PARAM_GRID
        sums = [_compute_summary(all_results[(variant, N, X)], N, X) for (N, X) in pg]
        best_s = max(sums, key=lambda s: s["score"])
        print(f"     {variant:<22}: N={best_s['N']}  X={best_s['X']:.1f}"
              f"  real/yr={best_s['real_yr']:.1f}  fakeout={best_s['fakeout_pct']:.1f}%"
              f"  score={best_s['score']:.1f}{'  ← WINNER' if variant == bv else ''}")

    print(f"\n  3. STACKED FUNNEL ENDPOINT")
    t10_pb_aligned = [
        e for e in best_events
        if e["break"] is not None
        and e["break"]["thrust_ratio"] >= 1.0
        and not e["break"]["fakeout"]
        and e["model_b"] is not None
        and e["break"]["d1_aligned"]
    ]
    if t10_pb_aligned:
        nets_b = [e["model_b"]["net_pips"] for e in t10_pb_aligned if e["model_b"]]
        rs_b   = [e["model_b"]["r_multiple"] for e in t10_pb_aligned if e["model_b"]]
        wins_b = sum(1 for n_ in nets_b if n_ > 0)
        insuff = " INSUFFICIENT" if len(t10_pb_aligned) < MIN_N else ""
        print(f"     thrust>=1.0 + pullback + D1 aligned: N={len(t10_pb_aligned)}{insuff}")
        if nets_b:
            print(f"     avgNet={_avg(nets_b):+.1f}pip  win%={wins_b/len(nets_b)*100:.1f}%  medR={_med(rs_b):.2f}")
    else:
        print(f"     No entries reached all 3 filter stages.")

    print(f"\n  4. FREQUENCY vs 50/yr TARGET")
    print(f"     Best real breaks/yr: {n_real/TOTAL_YEARS:.1f}  (target: 50/yr)")
    gap = 50 - n_real / TOTAL_YEARS
    if gap > 0:
        print(f"     Gap: {gap:.1f}/yr — detector needs {gap:.0f} more real signals/yr to reach target")
    else:
        print(f"     Gap: NONE — target met")

    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"\n{'═' * _W}")
    print("  STRUCTURE ENGINE STUDY  v2")
    print(f"  Date       : {_last_trading_day()}")
    print(f"  Variants   : RANGE_ONLY / COMPRESSION_ONLY / EITHER")
    print(f"  N grid     : 6, 8, 12, 18 bars")
    print(f"  X grid     : 1.5, 2.0, 2.5, 3.0 × ATR  (RANGE/EITHER variants)")
    print(f"  Compression: box_atr_avg < {COMPRESSION_THRESHOLD} × prior_20bar_atr_ma")
    print(f"  Break      : close outside box + body >= 0.5×ATR within {MAX_BREAK_WAIT} bars")
    print(f"  Fakeout    : close back inside box within {FAKEOUT_BARS} bars")
    print(f"  Spread     : {SPREAD_PIPS}pip RT  |  Min N: {MIN_N}  |  Fwd: {FORWARD_BARS} H4 bars")
    print(f"  NOTE       : No framework code changes — diagnosis only.")
    print(f"{'═' * _W}")

    for pair_key in ("GBP_AUD", "GBP_JPY"):
        analyze_pair(pair_key)

    print(f"\n{'═' * _W}")
    print("  RUN COMPLETE — framework unchanged")
    print(f"{'═' * _W}\n")


if __name__ == "__main__":
    main()
