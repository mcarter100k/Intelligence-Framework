"""
hypothesis_volatile_entries.py
──────────────────────────────
Tests whether D1 VOLATILE is a better or worse entry environment than
D1 TRENDING on GBP/AUD and GBP/JPY, and whether H4 + weekly context
can identify which VOLATILE bars to act on.

Method: 5 years OANDA D1 (rolling 220-bar window), H4 (rolling 120-bar
window), W (rolling 110-bar window). Non-overlapping step=5 bars.
Forward measurement: 5 D1 bars in H4-indicated direction.
Spread-adjusted: -3 pips on every net figure. N<15 → INSUFFICIENT.

Framework functions used directly — no reimplementation.
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


import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from historical_scenario_replay import _fetch_historical
from regime_detection import (
    PAIRS,
    _classify,
    _detect_structure,
    _compute_adx,
    compute_atr_series,
    _compute_weekly_context,
    _ADX_PERIOD,
)

# ── Config ────────────────────────────────────────────────────────────────────
SPREAD_PIPS    = 3
THRESHOLD_PIPS = 150   # MFE / MAE threshold for win/loss classification
STEP           = 5     # non-overlapping step (bars)
D1_WINDOW      = 220   # mirrors get_regime() count
H4_WINDOW      = 120   # mirrors get_regime() count
MIN_N          = 15    # below this: INSUFFICIENT


# ── Forward measurement ───────────────────────────────────────────────────────

def _forward(
    d1_h: np.ndarray,
    d1_l: np.ndarray,
    d1_c: np.ndarray,
    i: int,
    direction: int,   # +1 = LONG, -1 = SHORT
    pip_size: float,
) -> Optional[Dict]:
    """
    Measure 5-bar forward outcome from bar i.
    direction = +1 (LONG): favourable = upside, adverse = downside.
    direction = -1 (SHORT): favourable = downside, adverse = upside.

    Within a single bar, if both thresholds are crossed, adverse wins
    (conservative). win_150 = True/False/None (None = neither hit).
    """
    if i + 5 >= len(d1_c):
        return None

    entry  = float(d1_c[i])
    thresh = THRESHOLD_PIPS * pip_size
    mfe = mae = 0.0
    win = None

    for j in range(1, 6):
        k = i + j
        if direction == 1:
            fav = float(d1_h[k]) - entry
            adv = entry - float(d1_l[k])
        else:
            fav = entry - float(d1_l[k])
            adv = float(d1_h[k]) - entry

        prev_mfe, prev_mae = mfe, mae
        mfe = max(mfe, fav)
        mae = max(mae, adv)

        mfe_x = (mfe >= thresh) and (prev_mfe < thresh)
        mae_x = (mae >= thresh) and (prev_mae < thresh)

        if mfe_x and mae_x:
            win = False   # same bar — adverse first
            break
        elif mfe_x:
            win = True
            break
        elif mae_x:
            win = False
            break

    net_raw = direction * (float(d1_c[i + 5]) - entry) / pip_size
    return {
        "mfe_pips":     mfe / pip_size,
        "mae_pips":     mae / pip_size,
        "net_pips":     net_raw - SPREAD_PIPS,
        "win_150":      win,
        "hit_mfe_150":  mfe >= thresh,
        "hit_mae_first": (win is False),
    }


# ── Per-bar regime helpers ────────────────────────────────────────────────────

def _d1_regime(d1_h, d1_l, d1_c, i: int, pair) -> Tuple[Optional[str], float, float, str]:
    end   = i + 1
    start = max(0, end - D1_WINDOW)
    h = list(d1_h[start:end].astype(float))
    l = list(d1_l[start:end].astype(float))
    c = list(d1_c[start:end].astype(float))

    if len(c) < _ADX_PERIOD * 3:
        return None, 0.0, 1.0, "TRANSITIONAL"

    atr_s     = compute_atr_series(h, l, c)
    avg_atr   = sum(atr_s[-20:]) / min(20, len(atr_s))
    atr_ratio = round(atr_s[-1] / avg_atr, 2) if avg_atr > 0 else 1.0
    adx       = _compute_adx(h, l, c)
    struct    = _detect_structure(h, l, c)
    structure = struct["structure"]

    if   structure == "UPTREND":   slope = 1.0
    elif structure == "DOWNTREND": slope = -1.0
    else: slope = c[-1] - c[-10] if len(c) >= 10 else 0.0

    regime = _classify(adx, atr_ratio, slope, pair=pair, instrument=pair.instrument)
    return regime, adx, atr_ratio, structure


def _h4_regime(
    h4_df, h4_h, h4_l, h4_c,
    bar_time, pair,
) -> Tuple[Optional[str], float]:
    h4_end = bar_time + pd.Timedelta(hours=24)
    idx = h4_df.index.searchsorted(h4_end, side="left")
    if idx < _ADX_PERIOD * 3:
        return None, 0.0

    sl  = slice(max(0, idx - H4_WINDOW), idx)
    h4h = list(h4_h[sl].astype(float))
    h4l = list(h4_l[sl].astype(float))
    h4c = list(h4_c[sl].astype(float))

    if len(h4h) < _ADX_PERIOD * 3:
        return None, 0.0

    atr_s    = compute_atr_series(h4h, h4l, h4c)
    avg_atr  = sum(atr_s[-20:]) / min(20, len(atr_s))
    atr_r    = round(atr_s[-1] / avg_atr, 2) if avg_atr > 0 else 1.0
    adx_h4   = _compute_adx(h4h, h4l, h4c)
    struct   = _detect_structure(h4h, h4l, h4c)

    if   struct["structure"] == "UPTREND":   h4_slope = 1.0
    elif struct["structure"] == "DOWNTREND": h4_slope = -1.0
    else: h4_slope = h4c[-1] - h4c[-10] if len(h4c) >= 10 else 0.0

    h4_reg = _classify(adx_h4, atr_r, h4_slope, pair=pair, instrument=pair.instrument)
    return h4_reg, adx_h4


def _weekly_ctx(w_df, w_h, w_l, w_c, bar_time) -> Tuple[str, str]:
    # Include only complete weekly bars: open_time strictly before bar_time
    idx = w_df.index.searchsorted(bar_time, side="left")
    if idx < 20:
        return "RANGING", "RANGING"

    sl  = slice(max(0, idx - 110), idx)
    wh  = list(w_h[sl].astype(float))
    wl  = list(w_l[sl].astype(float))
    wc  = list(w_c[sl].astype(float))

    if len(wh) < 20:
        return "RANGING", "RANGING"

    wd = _compute_weekly_context(wh, wl, wc)
    return wd["weekly_context"], wd["lt_trend"]


# ── Stats helper ──────────────────────────────────────────────────────────────

def _stats(subset: List[Dict]) -> Tuple[int, float, float, float, float]:
    n = len(subset)
    if n == 0:
        return 0, 0.0, 0.0, 0.0, 0.0
    pct_mfe = 100 * sum(1 for r in subset if r["hit_mfe_150"]) / n
    pct_mae = 100 * sum(1 for r in subset if r["hit_mae_first"]) / n
    avg_net = sum(r["net_pips"] for r in subset) / n
    decided = [r for r in subset if r["win_150"] is not None]
    win_pct = (100 * sum(1 for r in decided if r["win_150"]) / len(decided)
               if decided else 0.0)
    return n, pct_mfe, pct_mae, avg_net, win_pct


def _row(label: str, n: int, pct_mfe: float, pct_mae: float,
         avg_net: float, win_pct: float = None, star: bool = False) -> str:
    prefix = "▶ " if star else "  "
    lbl    = f"{prefix}{label}"
    if n < MIN_N:
        return f"  {lbl:<40}  N={n:<4}  INSUFFICIENT (N<{MIN_N})"
    w = f"  Win%:{win_pct:>5.1f}%" if win_pct is not None else ""
    return (f"  {lbl:<40}  N={n:<4}"
            f"  MFE≥150:{pct_mfe:>5.1f}%"
            f"  MAEfirst:{pct_mae:>5.1f}%"
            f"  AvgNet:{avg_net:>+6.1f}{w}")


# ── Main analysis ─────────────────────────────────────────────────────────────

def analyze_pair(instrument: str) -> List[Dict]:
    pair      = PAIRS[instrument]
    pair_code = pair.instrument.replace("_", "")
    # Use most recent completed trading day (not today if weekend/future)
    now = datetime.now(timezone.utc)
    days_back = 0
    if now.weekday() == 5:   days_back = 1   # Saturday → Friday
    elif now.weekday() == 6: days_back = 2   # Sunday   → Friday
    end_dt = now - __import__("datetime").timedelta(days=days_back)
    today  = end_dt.strftime("%Y-%m-%d")

    W = 72
    print(f"\n{'═'*W}")
    print(f"  {pair.display_name}  —  5-year D1 hypothesis test")
    print(f"  Spread: {SPREAD_PIPS}pip  |  threshold: {THRESHOLD_PIPS}pip  "
          f"|  window: 5 bars  |  step: {STEP}  |  D1 window: {D1_WINDOW}")
    print(f"{'═'*W}")

    t0 = time.perf_counter()
    print("  Fetching D1 (1350) ...", end=" ", flush=True)
    d1_df = _fetch_historical(pair_code, "D",  1350, today)
    print(f"{len(d1_df) if d1_df is not None else 0} bars")
    print("  Fetching H4 (4900) ...", end=" ", flush=True)
    h4_df = _fetch_historical(pair_code, "H4", 4900, today)
    print(f"{len(h4_df) if h4_df is not None else 0} bars")
    print("  Fetching W  (300)  ...", end=" ", flush=True)
    w_df  = _fetch_historical(pair_code, "W",  300,  today)
    print(f"{len(w_df) if w_df is not None else 0} bars")

    if d1_df is None or len(d1_df) < 250:
        print("  ERROR: insufficient D1 data"); return []

    n_d1 = len(d1_df)
    d1_h = d1_df["High"].values
    d1_l = d1_df["Low"].values
    d1_c = d1_df["Close"].values
    print(f"  D1: {d1_df.index[0].date()} → {d1_df.index[-1].date()}")

    has_h4 = h4_df is not None and not h4_df.empty
    has_w  = w_df  is not None and not w_df.empty

    if has_h4:
        h4_h = h4_df["High"].values
        h4_l = h4_df["Low"].values
        h4_c = h4_df["Close"].values
    if has_w:
        w_h = w_df["High"].values
        w_l = w_df["Low"].values
        w_c = w_df["Close"].values

    rows = []
    skip_h4 = skip_dir = 0
    n_positions = len(range(220, n_d1 - 5, STEP))
    print(f"\n  Scanning {n_positions} positions ", end="", flush=True)

    for idx_i, i in enumerate(range(220, n_d1 - 5, STEP)):
        if idx_i % 40 == 0:
            print(".", end="", flush=True)

        bar_time = d1_df.index[i]

        reg_d1, adx_d1, atr_ratio, structure = _d1_regime(d1_h, d1_l, d1_c, i, pair)
        if reg_d1 is None:
            continue

        if has_h4:
            reg_h4, adx_h4 = _h4_regime(h4_df, h4_h, h4_l, h4_c, bar_time, pair)
        else:
            reg_h4, adx_h4 = None, 0.0

        if reg_h4 is None:
            skip_h4 += 1
            continue

        if has_w:
            weekly_ctx, lt_trend = _weekly_ctx(w_df, w_h, w_l, w_c, bar_time)
        else:
            weekly_ctx, lt_trend = "RANGING", "RANGING"

        if   reg_h4 == "TRENDING_UP":   direction = 1
        elif reg_h4 == "TRENDING_DOWN": direction = -1
        else:
            skip_dir += 1
            continue

        fwd = _forward(d1_h, d1_l, d1_c, i, direction, pair.pip_size)
        if fwd is None:
            continue

        rows.append({
            "d1_regime":   reg_d1,
            "adx_d1":      adx_d1,
            "h4_regime":   reg_h4,
            "adx_h4":      adx_h4,
            "atr_ratio":   atr_ratio,
            "structure":   structure,
            "weekly_ctx":  weekly_ctx,
            "lt_trend":    lt_trend,
            "direction":   direction,
            **fwd,
        })

    elapsed = time.perf_counter() - t0
    print(f"\n  {len(rows)} H4-trending observations in {elapsed:.1f}s  "
          f"(skipped: {skip_h4} no-H4, {skip_dir} H4-not-trending)")

    if not rows:
        print("  No data to analyze.")
        return []

    vol_rows = [r for r in rows if r["d1_regime"] == "VOLATILE"]
    W2 = 72

    # ── TABLE 1 ──────────────────────────────────────────────────────────────
    print(f"\n{'─'*W2}")
    print("  TABLE 1 — Base rate by D1 regime  (all H4-trending bars)")
    print("  MFE≥150: hit 150 pips in H4 direction at any point in 5 bars")
    print("  MAEfirst: 150 adverse pips hit BEFORE 150 favourable")
    print("  AvgNet: spread-adjusted close-to-close net pips")
    print(f"{'─'*W2}")
    for lbl, reg in [("TRENDING_UP",   "TRENDING_UP"),
                     ("TRENDING_DOWN", "TRENDING_DOWN"),
                     ("RANGING",       "RANGING"),
                     ("VOLATILE",      "VOLATILE")]:
        sub = [r for r in rows if r["d1_regime"] == reg]
        print(_row(f"D1 {lbl}", *_stats(sub)))

    # ── TABLE 2 ──────────────────────────────────────────────────────────────
    print(f"\n{'─'*W2}")
    print("  TABLE 2 — D1 VOLATILE only, by H4 ADX band")
    print(f"{'─'*W2}")
    for lbl, lo, hi in [("<20", 0, 20), ("20-25", 20, 25), ("25-30", 25, 30),
                        ("30-40", 30, 40), ("40+", 40, 200)]:
        sub = [r for r in vol_rows if lo <= r["adx_h4"] < hi]
        print(_row(f"H4 ADX {lbl}", *_stats(sub)))

    # ── TABLE 3 ──────────────────────────────────────────────────────────────
    print(f"\n{'─'*W2}")
    print("  TABLE 3 — D1 VOLATILE + H4 trending, by weekly context")
    print("  Win% = MFE≥150 reached BEFORE MAE≥150 (adverse-first on same-bar tie)")
    print(f"{'─'*W2}")
    for ctx in ["ESTABLISHED_UPTREND", "ESTABLISHED_DOWNTREND",
                "COUNTER_TREND_BOUNCE", "PULLBACK_IN_UPTREND", "RANGING"]:
        sub = [r for r in vol_rows if r["weekly_ctx"] == ctx]
        n, pm, pa, an, wp = _stats(sub)
        print(_row(ctx.replace("_", " "), n, pm, pa, an, win_pct=wp))

    print()
    # The two setups the framework blocked / allowed in the replay
    ctb_up = [r for r in vol_rows
              if r["weekly_ctx"] == "COUNTER_TREND_BOUNCE" and r["h4_regime"] == "TRENDING_UP"]
    n, pm, pa, an, wp = _stats(ctb_up)
    print(_row("CTB + H4 UP  [BLOCKED by override]", n, pm, pa, an, win_pct=wp, star=True))

    ctb_dn = [r for r in vol_rows
              if r["weekly_ctx"] == "COUNTER_TREND_BOUNCE" and r["h4_regime"] == "TRENDING_DOWN"]
    n, pm, pa, an, wp = _stats(ctb_dn)
    print(_row("CTB + H4 DOWN  [ALLOWED if weekly bearish]", n, pm, pa, an, win_pct=wp, star=True))

    put_up = [r for r in vol_rows
              if r["weekly_ctx"] == "PULLBACK_IN_UPTREND" and r["h4_regime"] == "TRENDING_UP"]
    n, pm, pa, an, wp = _stats(put_up)
    print(_row("PULLBACK_IN_UPTREND + H4 UP  [BLOCKED]", n, pm, pa, an, win_pct=wp, star=True))

    # ── TABLE 4 ──────────────────────────────────────────────────────────────
    print(f"\n{'─'*W2}")
    print("  TABLE 4 — Current override condition")
    print("  D1 VOLATILE + H4 trending + weekly ESTABLISHED in H4 direction")
    print("  (Fired 2026-05-15 SHORT — market rose 280 pips)")
    print(f"{'─'*W2}")

    override = [r for r in vol_rows
                if ((r["h4_regime"] == "TRENDING_UP"   and r["weekly_ctx"] == "ESTABLISHED_UPTREND") or
                    (r["h4_regime"] == "TRENDING_DOWN"  and r["weekly_ctx"] == "ESTABLISHED_DOWNTREND"))]
    n, pm, pa, an, wp = _stats(override)
    print(_row("All override-aligned setups", n, pm, pa, an, win_pct=wp))

    for h4_dir, w_ctx, lbl in [
        ("TRENDING_UP",   "ESTABLISHED_UPTREND",  "  LONG  (H4 up + weekly uptrend)"),
        ("TRENDING_DOWN", "ESTABLISHED_DOWNTREND", "  SHORT (H4 down + weekly downtrend)"),
    ]:
        sub = [r for r in vol_rows if r["h4_regime"] == h4_dir and r["weekly_ctx"] == w_ctx]
        n, pm, pa, an, wp = _stats(sub)
        print(_row(lbl, n, pm, pa, an, win_pct=wp))

    return rows


# ── Verdict ───────────────────────────────────────────────────────────────────

def _verdict(aud_rows: List[Dict], jpy_rows: List[Dict]) -> None:
    W = 72
    print(f"\n{'═'*W}")
    print("  VERDICT")
    print(f"{'═'*W}")

    for label, rows in [("GBP/AUD", aud_rows), ("GBP/JPY", jpy_rows)]:
        if not rows:
            print(f"\n  {label}: no data")
            continue
        print(f"\n  {label}")

        # Q1: VOLATILE vs TRENDING as entry environment
        vol  = [r for r in rows if r["d1_regime"] == "VOLATILE"]
        trd  = [r for r in rows if r["d1_regime"] in ("TRENDING_UP", "TRENDING_DOWN")]
        nv, pmv, pav, anv, _ = _stats(vol)
        nt, pmt, pat, ant, _ = _stats(trd)

        print(f"  Q1: D1 VOLATILE vs D1 TRENDING entry environment")
        if nv >= MIN_N and nt >= MIN_N:
            better = "COMPARABLE" if abs(anv - ant) < 5 else ("BETTER" if anv > ant else "WORSE")
            print(f"    D1 VOLATILE  (N={nv}): MFE≥150={pmv:.1f}%  MAEfirst={pav:.1f}%  AvgNet={anv:+.1f}")
            print(f"    D1 TRENDING  (N={nt}): MFE≥150={pmt:.1f}%  MAEfirst={pat:.1f}%  AvgNet={ant:+.1f}")
            print(f"    → D1 VOLATILE is {better} than D1 TRENDING as entry environment")
            if anv < ant - 10:
                print(f"      Stand-down justified: VOLATILE shows {ant-anv:.0f}pip worse avg net than TRENDING")
            elif anv >= ant - 5:
                print(f"      Stand-down too broad: VOLATILE avg net close to TRENDING — move context matters more than D1 ADX")
        else:
            print(f"    Insufficient N for comparison (VOLATILE N={nv}, TRENDING N={nt})")

        # Q2: H4 ADX inside VOLATILE
        print(f"\n  Q2: H4 ADX strength inside D1 VOLATILE")
        bands = [("<20", 0, 20), ("20-25", 20, 25), ("25-30", 25, 30), ("30-40", 30, 40), ("40+", 40, 200)]
        valid_bands = []
        for lbl, lo, hi in bands:
            sub = [r for r in vol if lo <= r["adx_h4"] < hi]
            n, pm, pa, an, _ = _stats(sub)
            if n >= MIN_N:
                valid_bands.append((lbl, n, an, pm))
        if len(valid_bands) >= 2:
            low_band  = valid_bands[0]
            high_band = valid_bands[-1]
            delta = high_band[2] - low_band[2]
            print(f"    H4 ADX {low_band[0]}: AvgNet={low_band[2]:+.1f}  "
                  f"H4 ADX {high_band[0]}: AvgNet={high_band[2]:+.1f}  (delta={delta:+.1f})")
            if delta > 10:
                print(f"    → Strong H4 inside D1 VOLATILE IS predictive (+{delta:.0f}pip improvement)")
            elif delta < -10:
                print(f"    → Stronger H4 inside D1 VOLATILE makes things WORSE — exhaustion signal")
            else:
                print(f"    → H4 ADX strength inside D1 VOLATILE does NOT reliably predict outcome")
        else:
            print(f"    Insufficient N across bands for comparison")

        # Q3: weekly-alignment gate
        print(f"\n  Q3: Weekly-alignment gate (Table 3 CTB+H4 UP vs Table 4 override)")
        ctb_up    = [r for r in vol if r["weekly_ctx"] == "COUNTER_TREND_BOUNCE"
                     and r["h4_regime"] == "TRENDING_UP"]
        override  = [r for r in vol
                     if ((r["h4_regime"] == "TRENDING_UP"   and r["weekly_ctx"] == "ESTABLISHED_UPTREND") or
                         (r["h4_regime"] == "TRENDING_DOWN"  and r["weekly_ctx"] == "ESTABLISHED_DOWNTREND"))]
        nc, _, _, anc, wpc = _stats(ctb_up)
        no, _, _, ano, wpo = _stats(override)

        if nc >= MIN_N and no >= MIN_N:
            print(f"    CTB+H4 UP (blocked):  N={nc}  Win%={wpc:.1f}%  AvgNet={anc:+.1f}")
            print(f"    Override (allowed):   N={no}  Win%={wpo:.1f}%  AvgNet={ano:+.1f}")
            if wpo > wpc + 10:
                print(f"    → Gate is HELPING: override has {wpo-wpc:.0f}pp better win% than blocked setup")
            elif wpc > wpo + 10:
                print(f"    → Gate is HURTING: blocked setup has {wpc-wpo:.0f}pp better win% than what's allowed")
            else:
                print(f"    → Gate is MARGINAL: win% difference < 10pp — weekly alignment adds little")
                if anc > ano:
                    print(f"    → But blocked setup has better AvgNet ({anc:+.1f} vs {ano:+.1f}) — gate may be wrong")
        elif nc >= MIN_N:
            print(f"    CTB+H4 UP (blocked): N={nc} Win%={wpc:.1f}% AvgNet={anc:+.1f}")
            print(f"    Override: N={no} — INSUFFICIENT for comparison")
        elif no >= MIN_N:
            print(f"    CTB+H4 UP: N={nc} — INSUFFICIENT")
            print(f"    Override (allowed): N={no} Win%={wpo:.1f}% AvgNet={ano:+.1f}")
        else:
            print(f"    Both cells INSUFFICIENT (CTB+H4 UP N={nc}, override N={no})")

    print()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    aud_rows = analyze_pair("GBP_AUD")
    jpy_rows = analyze_pair("GBP_JPY")
    _verdict(aud_rows, jpy_rows)
