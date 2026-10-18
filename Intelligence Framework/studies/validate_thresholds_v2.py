"""
validate_thresholds_v2.py
─────────────────────────
Audit Item 2: re-run threshold validation with corrected methodology.

Corrections vs v1:
  1. Direction from _detect_structure() (P2 pivot method), NOT 10-bar slope
  2. Data from OANDA (count=1260 D1 bars), fallback to yfinance — source labelled
  3. Non-overlapping 20-bar forward windows — step = FORWARD_BARS, not 1
     Reports the honest sample size, not the inflated overlapping count.
  4. Spread-adjusted outcomes: subtract round-trip cost before scoring win
     GBP_AUD: 3.0 pips RT  |  GBP_JPY: 3.0 pips RT
     momentum_win = 1 if (future_move - spread_cost_in_price) > 0

Run A: ADX bands (same 9 bands as v1)
Run B: ATR ratio bands (same bands as validate_atr_threshold.py)

Do NOT update regime_detection.py constants — team review first.
"""

from __future__ import annotations

import os as _os, sys as _sys  # studies path bootstrap (project root)
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
for _p in (_ROOT,):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

import warnings
warnings.filterwarnings("ignore")

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple

from regime_detection import _detect_structure, compute_atr_series


# ── Constants ─────────────────────────────────────────────────────────────────

ADX_PERIOD   = 14
ATR_PERIOD   = 14
AVG_PERIOD   = 20   # rolling window for ATR ratio denominator
FORWARD_BARS = 20   # non-overlapping window step
MIN_BAND_N   = 15   # minimum N to report win%; below this = INSUFFICIENT

SPREAD_PIPS = {"GBP_AUD": 3.0, "GBP_JPY": 3.0}   # round-trip pip cost

PAIRS = {
    "GBP_AUD": {
        "oanda_pair": "GBPAUD",
        "yf_ticker":  "GBPAUD=X",
        "label":      "GBP/AUD",
        "pip_size":   0.0001,
    },
    "GBP_JPY": {
        "oanda_pair": "GBPJPY",
        "yf_ticker":  "GBPJPY=X",
        "label":      "GBP/JPY",
        "pip_size":   0.01,
    },
}

ADX_BANDS = [
    ( 0, 15), (15, 18), (18, 20), (20, 22), (22, 25),
    (25, 28), (28, 32), (32, 40), (40, 100),
]
ADX_BAND_LABELS = [
    " 0-15 ", "15-18 ", "18-20 ", "20-22 ", "22-25 ",
    "25-28 ", "28-32 ", "32-40 ", "  40+ ",
]

ATR_RATIO_BANDS = [
    (0.0, 0.8), (0.8, 1.0), (1.0, 1.2), (1.2, 1.4),
    (1.4, 1.6), (1.6, 1.8), (1.8, 2.0), (2.0, 2.5), (2.5, 99.0),
]
ATR_BAND_LABELS = [
    "0.0-0.8x", "0.8-1.0x", "1.0-1.2x", "1.2-1.4x",
    "1.4-1.6x", "1.6-1.8x", "1.8-2.0x", "2.0-2.5x", "  2.5x+ ",
]

DEGRADED_THRESHOLD = 52.0   # both signals below this = untradeable


# ── ADX series (Wilder — identical algorithm to regime_detection._compute_adx) ─

def _compute_adx_series(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = ADX_PERIOD,
) -> Tuple[List[float], int]:
    """
    Full ADX series for backtesting.
    adx_series[j] aligns to closes[offset + j]  where offset = 2*period - 1.
    Algorithm is identical to regime_detection._compute_adx (same Wilder init).
    """
    n = len(closes)
    if n < period * 2:
        return [], 0

    tr_list = [
        max(highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i]  - closes[i - 1]))
        for i in range(1, n)
    ]
    plus_dm = [
        (highs[i] - highs[i - 1])
        if (highs[i] - highs[i - 1]) > (lows[i - 1] - lows[i])
           and (highs[i] - highs[i - 1]) > 0
        else 0.0
        for i in range(1, n)
    ]
    minus_dm = [
        (lows[i - 1] - lows[i])
        if (lows[i - 1] - lows[i]) > (highs[i] - highs[i - 1])
           and (lows[i - 1] - lows[i]) > 0
        else 0.0
        for i in range(1, n)
    ]

    def _ws(vals: List[float]) -> List[float]:
        r = [sum(vals[:period])]
        for v in vals[period:]:
            r.append(r[-1] - r[-1] / period + v)
        return r

    s_tr    = _ws(tr_list)
    s_plus  = _ws(plus_dm)
    s_minus = _ws(minus_dm)

    di_plus  = [100 * p / t if t > 0 else 0.0 for p, t in zip(s_plus,  s_tr)]
    di_minus = [100 * m / t if t > 0 else 0.0 for m, t in zip(s_minus, s_tr)]

    dx = [
        100 * abs(p - m) / (p + m) if (p + m) > 0 else 0.0
        for p, m in zip(di_plus, di_minus)
    ]
    if len(dx) < period:
        return [], 0

    adx = sum(dx[:period]) / period
    series = [adx]
    for d in dx[period:]:
        adx = (adx * (period - 1) + d) / period
        series.append(adx)

    return series, 2 * period - 1


# ── Data fetch ────────────────────────────────────────────────────────────────

def _fetch_oanda(oanda_pair: str, count: int = 1260):
    try:
        from oanda_feed import get_daily_bars
        df = get_daily_bars(pair=oanda_pair, count=count)
        if df is not None and len(df) >= 100:
            return df, True
    except Exception:
        pass
    return None, False


def _fetch_yfinance(ticker: str):
    try:
        import yfinance as yf
        end   = datetime.today()
        start = end - timedelta(days=5 * 365 + 60)
        df = yf.download(
            ticker,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            interval="1d",
            auto_adjust=True,
            progress=False,
        )
        if hasattr(df.columns, "levels"):
            df.columns = df.columns.get_level_values(0)
        if df is not None and len(df) >= 100:
            return df, True
    except Exception:
        pass
    return None, False


def fetch_data(pair_key: str) -> Tuple[Optional[object], str]:
    """Returns (df, source_label). OANDA first, yfinance fallback."""
    cfg = PAIRS[pair_key]
    df, ok = _fetch_oanda(cfg["oanda_pair"], count=1260)
    if ok:
        return df, f"OANDA (count=1260 D1)"
    df, ok = _fetch_yfinance(cfg["yf_ticker"])
    if ok:
        return df, "yfinance fallback (~5yr D1)"
    return None, "UNAVAILABLE"


# ── Observation builders ──────────────────────────────────────────────────────

def _structure_direction(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    up_to: int,
) -> Optional[int]:
    """
    Call _detect_structure on bars[0 : up_to+1] (no lookahead).
    Returns 1 (LONG), -1 (SHORT), or None (TRANSITIONAL — skip this bar).
    """
    r = _detect_structure(highs[: up_to + 1], lows[: up_to + 1], closes[: up_to + 1])
    s = r.get("structure", "TRANSITIONAL")
    if s == "UPTREND":
        return 1
    if s == "DOWNTREND":
        return -1
    return None   # TRANSITIONAL — no directional claim


def _build_adx_obs(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    pip_size: float,
    spread_pips: float,
) -> Tuple[List[Dict], int, int]:
    """
    Returns (records, n_used, n_transitional_skipped).
    Non-overlapping windows stepped by FORWARD_BARS.
    Direction from _detect_structure (P2, no lookahead).
    """
    adx_series, offset = _compute_adx_series(highs, lows, closes, ADX_PERIOD)
    if not adx_series:
        return [], 0, 0

    n            = len(closes)
    spread_price = spread_pips * pip_size
    records: List[Dict] = []
    n_transitional = 0

    i = offset
    while i + FORWARD_BARS < n:
        j = i - offset
        if j < 0 or j >= len(adx_series):
            i += FORWARD_BARS
            continue

        direction = _structure_direction(highs, lows, closes, i)
        if direction is None:
            n_transitional += 1
            i += FORWARD_BARS
            continue

        adx_val      = adx_series[j]
        future_dir   = (closes[i + FORWARD_BARS] - closes[i]) * direction
        spread_price = spread_pips * pip_size
        mom_win      = 1 if (future_dir - spread_price) > 0 else 0

        lb = max(0, i - 20)
        if i > lb:
            mean_20  = sum(closes[lb:i]) / (i - lb)
            mr_gap   = mean_20 - closes[i]
            if mr_gap != 0:
                mr_dir  = 1 if mr_gap > 0 else -1
                mr_fut  = (closes[i + FORWARD_BARS] - closes[i]) * mr_dir
                mr_win  = 1 if (mr_fut - spread_price) > 0 else 0
            else:
                mr_win = 0
        else:
            mr_win = 0

        net_pips = future_dir / pip_size - spread_pips

        records.append({"adx": adx_val, "mom_win": mom_win,
                        "mr_win": mr_win, "net_pips": net_pips})
        i += FORWARD_BARS

    return records, len(records), n_transitional


def _build_atr_obs(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    pip_size: float,
    spread_pips: float,
) -> Tuple[List[Dict], int, int]:
    """
    Returns (records, n_used, n_transitional_skipped).
    """
    atr_series   = compute_atr_series(highs, lows, closes, ATR_PERIOD)
    atr_offset   = ATR_PERIOD
    n            = len(closes)
    spread_price = spread_pips * pip_size
    records: List[Dict] = []
    n_transitional = 0

    # First bar with valid ratio: need AVG_PERIOD ATR values
    first_i = atr_offset + AVG_PERIOD   # 14 + 20 = 34

    i = first_i
    while i + FORWARD_BARS < n:
        j = i - atr_offset
        if j < AVG_PERIOD or j >= len(atr_series):
            i += FORWARD_BARS
            continue

        avg_atr = sum(atr_series[j - AVG_PERIOD : j]) / AVG_PERIOD
        ratio   = atr_series[j] / avg_atr if avg_atr > 0 else 1.0

        direction = _structure_direction(highs, lows, closes, i)
        if direction is None:
            n_transitional += 1
            i += FORWARD_BARS
            continue

        future_dir = (closes[i + FORWARD_BARS] - closes[i]) * direction
        mom_win    = 1 if (future_dir - spread_price) > 0 else 0

        lb = max(0, i - 20)
        if i > lb:
            mean_20 = sum(closes[lb:i]) / (i - lb)
            mr_gap  = mean_20 - closes[i]
            if mr_gap != 0:
                mr_dir = 1 if mr_gap > 0 else -1
                mr_fut = (closes[i + FORWARD_BARS] - closes[i]) * mr_dir
                mr_win = 1 if (mr_fut - spread_price) > 0 else 0
            else:
                mr_win = 0
        else:
            mr_win = 0

        net_pips  = future_dir / pip_size - spread_pips
        atr_pips_ = atr_series[j] / pip_size

        records.append({"atr_ratio": ratio, "atr_pips": atr_pips_,
                        "mom_win": mom_win, "mr_win": mr_win, "net_pips": net_pips})
        i += FORWARD_BARS

    return records, len(records), n_transitional


# ── Band table printers ───────────────────────────────────────────────────────

def _print_adx_table(records: List[Dict]) -> List[Dict]:
    print(f"\n  {'Band':<8}  {'N':>5}  {'Mom%':>7}  {'MR%':>7}  {'AvgNetPip':>10}  Edge")
    print("  " + "─" * 58)
    results = []
    for (lo, hi), lbl in zip(ADX_BANDS, ADX_BAND_LABELS):
        bucket = [r for r in records if lo <= r["adx"] < hi]
        N = len(bucket)
        if N == 0:
            print(f"  {lbl}  {'0':>5}  {'—':>7}  {'—':>7}  {'—':>10}  no data")
            results.append({"lo": lo, "hi": hi, "lbl": lbl, "N": 0, "insufficient": True})
            continue
        if N < MIN_BAND_N:
            print(f"  {lbl}  {N:>5}  {'—':>7}  {'—':>7}  {'—':>10}  INSUFFICIENT (N<{MIN_BAND_N})")
            results.append({"lo": lo, "hi": hi, "lbl": lbl, "N": N, "insufficient": True})
            continue
        mom  = sum(r["mom_win"] for r in bucket) / N * 100
        mr   = 100.0 - mom
        netP = sum(r["net_pips"] for r in bucket) / N
        edge = ("MOMENTUM" if mom >= 55.0
                else "MEAN_REV" if mr >= 55.0
                else "COIN_FLIP")
        print(f"  {lbl}  {N:>5}  {mom:>6.1f}%  {mr:>6.1f}%  {netP:>9.1f}  {edge}")
        results.append({"lo": lo, "hi": hi, "lbl": lbl, "N": N,
                        "mom_pct": mom, "mr_pct": mr,
                        "avg_net_pips": netP, "edge": edge, "insufficient": False})
    return results


def _print_atr_table(records: List[Dict]) -> List[Dict]:
    print(f"\n  {'Band':<10}  {'N':>5}  {'Mom%':>7}  {'MR%':>7}  "
          f"{'AvgATRpip':>10}  {'AvgNetPip':>10}  Both<52%?")
    print("  " + "─" * 70)
    results = []
    for (lo, hi), lbl in zip(ATR_RATIO_BANDS, ATR_BAND_LABELS):
        bucket = [r for r in records if lo <= r["atr_ratio"] < hi]
        N = len(bucket)
        if N == 0:
            print(f"  {lbl}  {'0':>5}  {'—':>7}  {'—':>7}  {'—':>10}  {'—':>10}  —")
            results.append({"lo": lo, "hi": hi, "lbl": lbl, "N": 0, "insufficient": True})
            continue
        if N < MIN_BAND_N:
            print(f"  {lbl}  {N:>5}  {'—':>7}  {'—':>7}  {'—':>10}  {'—':>10}  INSUFFICIENT (N<{MIN_BAND_N})")
            results.append({"lo": lo, "hi": hi, "lbl": lbl, "N": N, "insufficient": True})
            continue
        mom   = sum(r["mom_win"] for r in bucket) / N * 100
        mr    = 100.0 - mom
        atrP  = sum(r["atr_pips"] for r in bucket) / N
        netP  = sum(r["net_pips"] for r in bucket) / N
        both  = mom < DEGRADED_THRESHOLD and mr < DEGRADED_THRESHOLD
        deg   = "YES <-- DEGRADED" if both else "no"
        print(f"  {lbl}  {N:>5}  {mom:>6.1f}%  {mr:>6.1f}%  "
              f"{atrP:>9.1f}  {netP:>9.1f}  {deg}")
        results.append({"lo": lo, "hi": hi, "lbl": lbl, "N": N,
                        "mom_pct": mom, "mr_pct": mr,
                        "avg_atr_pips": atrP, "avg_net_pips": netP,
                        "both_degraded": both, "insufficient": False})
    return results


# ── V1 findings registry ──────────────────────────────────────────────────────
# v1_value is in the units of the metric column (mom_pct or mr_pct as labelled)

V1_ADX_FINDINGS = {
    "GBP_AUD": [
        {"desc": "Momentum window at ADX 22-25 (55.8% momentum)",
         "lo": 22, "hi": 25, "v1_mom": 55.8, "v1_mr": 44.2, "exp": "momentum"},
        {"desc": "Collapse at ADX 25-28 (momentum fails)",
         "lo": 25, "hi": 28, "v1_mom": None, "v1_mr": None, "exp": "no_momentum"},
        {"desc": "Inversion at ADX 28-32 (31.7% momentum → 68.3% MR)",
         "lo": 28, "hi": 32, "v1_mom": 31.7, "v1_mr": 68.3, "exp": "mean_rev"},
    ],
    "GBP_JPY": [
        {"desc": "ADX 40+ = 82.7% mean reversion",
         "lo": 40, "hi": 100, "v1_mom": 17.3, "v1_mr": 82.7, "exp": "mean_rev"},
    ],
}

V1_ATR_FINDINGS = {
    "GBP_AUD": [
        {"desc": "Both signals degrade at ATR ratio >= 1.2x",
         "lo": 1.2, "hi": 1.4, "exp": "degraded"},
    ],
    "GBP_JPY": [
        {"desc": "Compression < 0.8x shows signal degradation",
         "lo": 0.0, "hi": 0.8, "exp": "degraded"},
    ],
}


def _find_band(results: List[Dict], lo: float, hi: float) -> Optional[Dict]:
    for b in results:
        if abs(b.get("lo", -999) - lo) < 0.001 and abs(b.get("hi", -999) - hi) < 0.001:
            return b
    return None


def _verdict(f: Dict, band: Optional[Dict]) -> Tuple[str, str]:
    """Return (verdict_str, detail_str) for one v1 finding."""
    if band is None:
        return "NOT SUPPORTED", "band not present in v2 results"
    N = band.get("N", 0)
    if N == 0:
        return "NOT SUPPORTED", "no observations in this band"
    if band.get("insufficient"):
        return f"NOT SUPPORTED at this sample size", f"N={N} < {MIN_BAND_N}"

    exp = f["exp"]
    v1_mom = f.get("v1_mom")
    v1_mr  = f.get("v1_mr")
    v2_mom = band.get("mom_pct", 0)
    v2_mr  = band.get("mr_pct", 0)

    if exp == "momentum":
        if v2_mom >= 55.0:
            v1s = f" (v1={v1_mom:.1f}%)" if v1_mom else ""
            return "CONFIRMED", f"v2 momentum={v2_mom:.1f}%{v1s}"
        else:
            v1s = f" (v1={v1_mom:.1f}%)" if v1_mom else ""
            return "NOT SUPPORTED", (
                f"v2 momentum={v2_mom:.1f}% < 55% after spread adj{v1s}"
            )

    elif exp == "no_momentum":
        if v2_mom < 55.0:
            return "CONFIRMED", f"v2 momentum={v2_mom:.1f}% — no momentum edge confirmed"
        else:
            return "NOT SUPPORTED", (
                f"v2 momentum={v2_mom:.1f}% — momentum persists, v1 collapse not reproduced"
            )

    elif exp == "mean_rev":
        if v2_mr >= 55.0:
            if v1_mr is not None:
                delta = abs(v2_mr - v1_mr)
                if delta <= 10.0:
                    return "CONFIRMED", (
                        f"v2 MR={v2_mr:.1f}% vs v1 MR={v1_mr:.1f}% — within 10 ppts"
                    )
                else:
                    return f"CONFIRMED (magnitude shifted)", (
                        f"v2 MR={v2_mr:.1f}% vs v1 MR={v1_mr:.1f}% — "
                        f"direction same, spread adj reduced magnitude by {delta:.1f} ppts"
                    )
            return "CONFIRMED", f"v2 MR={v2_mr:.1f}% ≥ 55%"
        else:
            v1s = f" (v1 MR={v1_mr:.1f}%)" if v1_mr else ""
            return "NOT SUPPORTED", (
                f"v2 MR={v2_mr:.1f}% — no clear MR edge after spread adj{v1s}"
            )

    elif exp == "degraded":
        both = band.get("both_degraded", False)
        if both:
            return "CONFIRMED", (
                f"v2 mom={v2_mom:.1f}% MR={v2_mr:.1f}% — both < {DEGRADED_THRESHOLD:.0f}%"
            )
        else:
            return "NOT SUPPORTED", (
                f"v2 mom={v2_mom:.1f}% MR={v2_mr:.1f}% — "
                f"at least one signal ≥ {DEGRADED_THRESHOLD:.0f}% after spread adj"
            )

    return "UNKNOWN", ""


def _print_v1_comparison(
    pair_key: str,
    adx_results: List[Dict],
    atr_results: List[Dict],
) -> None:
    print("\n  ── V1 vs V2 COMPARISON " + "─" * 46)

    for f in V1_ADX_FINDINGS.get(pair_key, []):
        band = _find_band(adx_results, f["lo"], f["hi"])
        v, detail = _verdict(f, band)
        print(f"\n  [ADX {f['lo']}-{f['hi']}]  {f['desc']}")
        print(f"    v2:  {v}")
        if detail:
            print(f"         {detail}")

    for f in V1_ATR_FINDINGS.get(pair_key, []):
        band = _find_band(atr_results, f["lo"], f["hi"])
        v, detail = _verdict(f, band)
        print(f"\n  [ATR {f['lo']:.1f}-{f['hi']:.1f}x]  {f['desc']}")
        print(f"    v2:  {v}")
        if detail:
            print(f"         {detail}")


# ── Recommendation block ──────────────────────────────────────────────────────

def _print_recommendation(
    pair_key: str,
    adx_results: List[Dict],
    atr_results: List[Dict],
) -> None:
    print("\n  ── RECOMMENDATION " + "─" * 50)
    label = PAIRS[pair_key]["label"]

    # -- ADX --
    valid = [b for b in adx_results if not b.get("insufficient") and "mom_pct" in b]
    mom_bands = [b for b in valid if b["mom_pct"] >= 55.0]
    mr_bands  = [b for b in valid if b.get("mr_pct", 0) >= 55.0]

    print(f"\n  ADX constants [{label}]:")
    if not valid:
        print("    No bands with N ≥ 15 — all findings at INSUFFICIENT sample size.")
        print("    → RECLASSIFY as informed priors. Retain current thresholds.")
        print("      Re-evaluate when 60+ non-overlapping logged outcomes available.")
    elif mom_bands:
        lowest = min(mom_bands, key=lambda b: b["lo"])
        if lowest["lo"] < 25:
            print(f"    Momentum edge seen from ADX {lowest['lo']}+ but N is small.")
            print(f"    Current threshold (STAND_DOWN below 25) is conservative.")
            print(f"    → KEEP current threshold of 25 pending 60+ validated outcomes.")
            print(f"      Lower threshold candidate ({lowest['lo']}) noted — revisit v3.")
        elif lowest["lo"] == 25:
            print(f"    Momentum edge confirmed from ADX 25+ with spread adjustment.")
            print(f"    → KEEP current ADX_TRANSITION_HIGH = 25.")
        else:
            print(f"    No momentum edge below ADX {lowest['lo']} in v2 (spread-adjusted).")
            print(f"    → REVIEW: consider raising threshold from 25 to {lowest['lo']}.")
            print(f"      Pending team review — do not change yet.")
    elif mr_bands:
        print(f"    No ADX band achieves momentum edge (≥55%) after spread adjustment.")
        top_mr = max(mr_bands, key=lambda b: b.get("mr_pct", 0))
        print(f"    Strongest MR edge: ADX {top_mr['lo']}-{top_mr['hi']} "
              f"({top_mr.get('mr_pct',0):.1f}% MR).")
        print(f"    → RECLASSIFY: current ADX thresholds are informed priors.")
        print(f"      Mean reversion is the empirically dominant strategy at this sample size.")
    else:
        print(f"    No clear edge in either direction after spread adjustment.")
        print(f"    → RECLASSIFY as informed priors. Retain current thresholds.")

    # -- ATR --
    valid_atr = [b for b in atr_results if not b.get("insufficient") and "both_degraded" in b]
    deg_bands = [b for b in valid_atr if b["both_degraded"]]

    print(f"\n  ATR constants [{label}]:")
    if not valid_atr:
        print(f"    No ATR bands with N ≥ 15 — all INSUFFICIENT.")
        print(f"    → RECLASSIFY as informed priors. Retain current multiplier.")
    elif deg_bands:
        first = min(deg_bands, key=lambda b: b["lo"])
        if abs(first["lo"] - 1.2) < 0.05:
            print(f"    Degradation confirmed at {first['lo']}x — consistent with v1 (1.2x).")
            print(f"    → KEEP current ATR spike multiplier.")
        elif first["lo"] > 1.2:
            print(f"    Degradation starts at {first['lo']}x (v1: 1.2x).")
            print(f"    Spread adjustment raised the threshold — 1.2x fires too conservatively.")
            print(f"    → REVIEW: consider raising to {first['lo']}x after team review.")
        else:
            print(f"    Degradation starts at {first['lo']}x (v1: 1.2x) — fires earlier.")
            print(f"    → REVIEW: current 1.2x threshold may not fire early enough.")
    else:
        print(f"    No ATR band shows both signals < {DEGRADED_THRESHOLD:.0f}% after spread adjustment.")
        print(f"    → RECLASSIFY as informed priors. Retain current multiplier.")
        print(f"      ATR ratio alone may not be a reliable stand-down trigger at this sample size.")

    print(f"\n  ⚠  Do NOT update regime_detection.py constants from this run.")
    print(f"     Team review required. Re-trigger: 60+ logged non-overlapping outcomes.")


# ── Per-pair runner ───────────────────────────────────────────────────────────

def analyze_pair(pair_key: str) -> None:
    cfg    = PAIRS[pair_key]
    label  = cfg["label"]
    W      = 72

    print(f"\n{'='*W}")
    print(f"  {label}   validate_thresholds_v2")
    print(f"{'='*W}")

    df, source = fetch_data(pair_key)
    print(f"  Data source  : {source}")

    if df is None:
        print("  ERROR: data unavailable — pair skipped")
        return

    df = df.dropna(subset=["High", "Low", "Close"])
    highs  = df["High"].tolist()
    lows   = df["Low"].tolist()
    closes = df["Close"].tolist()
    n_bars = len(closes)
    spread = SPREAD_PIPS[pair_key]

    print(f"  Bars loaded  : {n_bars}")
    print(f"  Spread cost  : {spread} pips round-trip ({spread * cfg['pip_size']:.4f} price units)")
    print(f"  Window step  : {FORWARD_BARS} bars non-overlapping")
    print(f"  Direction    : _detect_structure() — P2 pivot method, no lookahead")
    print(f"  Min N/band   : {MIN_BAND_N}  (below = INSUFFICIENT, no win% reported)")

    # ── RUN A ─────────────────────────────────────────────────────────────────
    print(f"\n{'─'*W}")
    print(f"  RUN A — ADX BANDS  (spread-adjusted, structure-directed)")
    print(f"{'─'*W}")

    adx_obs, n_adx, n_adx_trans = _build_adx_obs(highs, lows, closes,
                                                   cfg["pip_size"], spread)
    n_adx_total = n_adx + n_adx_trans
    print(f"  Total non-overlapping slots evaluated : {n_adx_total}")
    print(f"  TRANSITIONAL (skipped — no direction) : {n_adx_trans}")
    print(f"  Directional observations used         : {n_adx}")

    adx_results = _print_adx_table(adx_obs)

    # ── RUN B ─────────────────────────────────────────────────────────────────
    print(f"\n{'─'*W}")
    print(f"  RUN B — ATR RATIO BANDS  (spread-adjusted, structure-directed)")
    print(f"{'─'*W}")

    atr_obs, n_atr, n_atr_trans = _build_atr_obs(highs, lows, closes,
                                                   cfg["pip_size"], spread)
    n_atr_total = n_atr + n_atr_trans
    print(f"  Total non-overlapping slots evaluated : {n_atr_total}")
    print(f"  TRANSITIONAL (skipped — no direction) : {n_atr_trans}")
    print(f"  Directional observations used         : {n_atr}")

    atr_results = _print_atr_table(atr_obs)

    # ── V1 COMPARISON ─────────────────────────────────────────────────────────
    _print_v1_comparison(pair_key, adx_results, atr_results)

    # ── RECOMMENDATION ────────────────────────────────────────────────────────
    _print_recommendation(pair_key, adx_results, atr_results)
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    W = 72
    print(f"\n{'='*W}")
    print("  VALIDATE THRESHOLDS V2")
    print(f"  Date       : {date.today().isoformat()}")
    print(f"  Method     : P2 pivot structure-direction, non-overlapping windows")
    print(f"  ADX        : Wilder(14) — identical to regime_detection._compute_adx")
    print(f"  ATR        : Wilder(14) imported from regime_detection.compute_atr_series")
    print(f"  Windows    : {FORWARD_BARS}-bar non-overlapping forward")
    print(f"  Spread adj : round-trip pip cost subtracted from every outcome")
    print(f"  Min N      : {MIN_BAND_N} per band")
    print(f"  Note       : overlapping v1 inflated N by ~{FORWARD_BARS}x; honest N is small")
    print(f"{'='*W}")

    for pair_key in PAIRS:
        analyze_pair(pair_key)

    print(f"\n{'='*W}")
    print("  RUN COMPLETE")
    print("  Constants in regime_detection.py: unchanged.")
    print("  Re-evaluation trigger: 60+ non-overlapping logged outcomes per regime per pair.")
    print(f"{'='*W}\n")


if __name__ == "__main__":
    main()
