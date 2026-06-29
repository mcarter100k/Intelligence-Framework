"""
regime_detection.py

Detects the current market regime for GBP/AUD:
  TRENDING_UP   : strong directional move higher
  TRENDING_DOWN : strong directional move lower
  RANGING       : price chopping sideways in a box
  VOLATILE      : large unpredictable swings, no clear direction

Indicators:
  ATR (Average True Range) — how many pips GBP/AUD moves per day on average
  ADX (Average Directional Index) — how strong the current trend is (0-100)
    > 25 = trending | 20-25 = developing | < 20 = ranging/no trend

Both use Wilder's smoothing — fixed to avoid accumulation overflow.
Data source: yfinance (free, no API key needed)
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from oanda_feed import (
    get_daily_bars  as _oanda_daily_bars,
    get_h4_bars     as _oanda_h4_bars,
    get_weekly_bars as _oanda_weekly_bars,
    is_configured   as _oanda_ok,
)

@dataclass
class PairConfig:
    instrument:           str
    ticker:               str
    pip_size:             float
    display_name:         str
    atr_spike_multiplier: float   # ATR ratio above which = volatile spike
    atr_compression_min:  float   # ATR ratio below which = compression stand-down
                                  # 0.0 = no compression filter (default)

    def to_pips(self, price_move: float) -> float:
        return round(price_move / self.pip_size, 1)

    def from_pips(self, pips: float) -> float:
        return pips * self.pip_size

# VALIDATED 2025-06-25 via validate_atr_threshold.py — 5yr D1 backtest
# GBP/AUD: signal degrades at 1.2x (was 1.5x, delta=-0.30)
# GBP/JPY: compression stand-down at <0.8x, spike filter at 1.5x
PAIRS: Dict[str, PairConfig] = {
    "GBP_AUD": PairConfig(
        instrument="GBP_AUD",
        ticker="GBPAUD=X",
        pip_size=0.0001,
        display_name="GBP/AUD",
        atr_spike_multiplier=1.2,   # validated: signal gone at 1.2x
        atr_compression_min=0.0,    # no compression filter for GBP/AUD
    ),
    "GBP_JPY": PairConfig(
        instrument="GBP_JPY",
        ticker="GBPJPY=X",
        pip_size=0.01,
        display_name="GBP/JPY",
        atr_spike_multiplier=1.5,   # conservative default — spikes post-BoJ
        atr_compression_min=0.8,    # compression stand-down: pre-BoJ coil
    ),
}

_DEFAULT_PAIR = "GBP_AUD"

_ATR_PERIOD  = 14
_ADX_PERIOD  = 14

# VALIDATED 2025-06-25 via validate_adx_threshold.py — 5yr D1 backtest, 1295 bars each
# ADX is a regime STATE indicator, not a trend ENTRY signal.
# Momentum win rates collapse above 25-28 on both pairs.
# GBP/JPY ADX 40+ = 82.7% mean reversion — exhaustion, not trend.
_ADX_RANGING_THRESHOLD    = 18    # below this: mean reversion dominant (was 20)
_ADX_TRANSITION_LOW       = 18    # 18-25: no statistical edge, require structure confirmation
_ADX_TRANSITION_HIGH      = 25    # 25-32: cautious trend, HTF confirmation required
_ADX_EXHAUSTION_THRESHOLD = 32    # above this: late-trend warning, reduce size
_ADX_JPY_EXHAUSTION       = 35    # GBP/JPY specific: mean reversion accelerates here

# Weekly context constants — sourced from htf_structure 5yr analysis
_WEEKLY_LT_LOOKBACK = 20  # 20W long-term trend lookback (~5 months)
_WEEKLY_ST_LOOKBACK = 4   # 4W short-term trend lookback (~1 month)
_MA_SHORT_PERIOD    = 50  # 50-day moving average — medium-term structural bias
_MA_LONG_PERIOD     = 200 # 200-day moving average — long-term structural bias

# Stand-down threshold — ATR ratio above this signals chaotic expansion, hard gate
_ATR_STANDDOWN_THRESHOLD = 2.0

# ── Composite regime resolution table ─────────────────────────────────────────
# Maps every (D1_regime, H4_regime) pair to a deterministic trading instruction.
# All 16 combinations are explicitly defined — no implicit fallbacks inside the
# table itself. Unknown combinations handled by get_composite_regime() default.
# VALIDATED: Table design locked 2025-06-28 based on Problems 1-5 findings.
# Re-evaluate individual cells after 60+ logged outcomes per combination.
RESOLUTION_TABLE: Dict[Tuple[str, str], Dict] = {

    # ── Both timeframes agree — clean alignment ───────────────────────────────
    ("TRENDING_UP",   "TRENDING_UP"): {
        "composite":      "TRENDING_UP",
        "execution_mode": "CONTINUATION",
        "confidence":     "HIGH",
        "size_mult":      1.0,
        "signal_bias":    "MOMENTUM",
        "note": "Both TFs aligned up — strongest trend entry condition",
    },
    ("TRENDING_DOWN", "TRENDING_DOWN"): {
        "composite":      "TRENDING_DOWN",
        "execution_mode": "CONTINUATION",
        "confidence":     "HIGH",
        "size_mult":      1.0,
        "signal_bias":    "MOMENTUM",
        "note": "Both TFs aligned down — strongest trend entry condition",
    },
    ("RANGING",       "RANGING"): {
        "composite":      "RANGING",
        "execution_mode": "FADE_EXTREMES",
        "confidence":     "MEDIUM",
        "size_mult":      0.75,
        "signal_bias":    "MEAN_REVERSION",
        "note": "Clean range on both TFs — trade from edges only",
    },
    ("VOLATILE",      "VOLATILE"): {
        "composite":      "VOLATILE",
        "execution_mode": "STAND_DOWN",
        "confidence":     "NONE",
        "size_mult":      0.0,
        "signal_bias":    "NONE",
        "note": "No edge on either TF — stand aside",
    },

    # ── D1 trending + H4 ranging — pullback structure ─────────────────────────
    ("TRENDING_UP",   "RANGING"): {
        "composite":      "TRENDING_UP",
        "execution_mode": "PULLBACK_ENTRY",
        "confidence":     "MEDIUM",
        "size_mult":      0.75,
        "signal_bias":    "MOMENTUM",
        "note": "D1 trend intact, H4 ranging = pullback. Wait for H4 support hold, enter long in D1 direction",
    },
    ("TRENDING_DOWN", "RANGING"): {
        "composite":      "TRENDING_DOWN",
        "execution_mode": "PULLBACK_ENTRY",
        "confidence":     "MEDIUM",
        "size_mult":      0.75,
        "signal_bias":    "MOMENTUM",
        "note": "D1 trend intact, H4 ranging = pullback. Wait for H4 resistance hold, enter short in D1 direction",
    },

    # ── D1 ranging + H4 trending — suspect H4 trend ───────────────────────────
    ("RANGING",       "TRENDING_UP"): {
        "composite":      "RANGING",
        "execution_mode": "REDUCED_MOMENTUM",
        "confidence":     "LOW",
        "size_mult":      0.5,
        "signal_bias":    "MOMENTUM",
        "note": "H4 trend inside D1 range — suspect. Size down. Treat as range trade with momentum bias",
    },
    ("RANGING",       "TRENDING_DOWN"): {
        "composite":      "RANGING",
        "execution_mode": "REDUCED_MOMENTUM",
        "confidence":     "LOW",
        "size_mult":      0.5,
        "signal_bias":    "MOMENTUM",
        "note": "H4 trend inside D1 range — suspect. Size down. Treat as range trade with momentum bias",
    },

    # ── Opposite trending — hard conflict ─────────────────────────────────────
    ("TRENDING_UP",   "TRENDING_DOWN"): {
        "composite":      "VOLATILE",
        "execution_mode": "STAND_DOWN",
        "confidence":     "NONE",
        "size_mult":      0.0,
        "signal_bias":    "NONE",
        "note": "Structural disagreement — D1 and H4 trend in opposite directions. No edge.",
    },
    ("TRENDING_DOWN", "TRENDING_UP"): {
        "composite":      "VOLATILE",
        "execution_mode": "STAND_DOWN",
        "confidence":     "NONE",
        "size_mult":      0.0,
        "signal_bias":    "NONE",
        "note": "Structural disagreement — D1 and H4 trend in opposite directions. No edge.",
    },

    # ── Volatile D1 — stand-down regardless of H4 ─────────────────────────────
    ("VOLATILE",      "TRENDING_UP"): {
        "composite":      "VOLATILE",
        "execution_mode": "STAND_DOWN",
        "confidence":     "NONE",
        "size_mult":      0.0,
        "signal_bias":    "NONE",
        "note": "D1 VOLATILE overrides H4 trend — transition zone, no D1 edge",
    },
    ("VOLATILE",      "TRENDING_DOWN"): {
        "composite":      "VOLATILE",
        "execution_mode": "STAND_DOWN",
        "confidence":     "NONE",
        "size_mult":      0.0,
        "signal_bias":    "NONE",
        "note": "D1 VOLATILE overrides H4 trend — transition zone, no D1 edge",
    },
    ("VOLATILE",      "RANGING"): {
        "composite":      "VOLATILE",
        "execution_mode": "STAND_DOWN",
        "confidence":     "NONE",
        "size_mult":      0.0,
        "signal_bias":    "NONE",
        "note": "D1 VOLATILE + H4 ranging — no edge on either TF",
    },

    # ── Ranging D1 + Volatile H4 — unstable range ─────────────────────────────
    ("RANGING",       "VOLATILE"): {
        "composite":      "VOLATILE",
        "execution_mode": "STAND_DOWN",
        "confidence":     "NONE",
        "size_mult":      0.0,
        "signal_bias":    "NONE",
        "note": "Range breaking down — H4 volatile inside D1 range. Wait for resolution.",
    },

    # ── Trending D1 + Volatile H4 — noise in trend ────────────────────────────
    ("TRENDING_UP",   "VOLATILE"): {
        "composite":      "TRENDING_UP",
        "execution_mode": "REDUCED_MOMENTUM",
        "confidence":     "LOW",
        "size_mult":      0.5,
        "signal_bias":    "MOMENTUM",
        "note": "D1 trend intact but H4 is noisy. Size down. Wait for H4 to resolve before entering.",
    },
    ("TRENDING_DOWN", "VOLATILE"): {
        "composite":      "TRENDING_DOWN",
        "execution_mode": "REDUCED_MOMENTUM",
        "confidence":     "LOW",
        "size_mult":      0.5,
        "signal_bias":    "MOMENTUM",
        "note": "D1 trend intact but H4 is noisy. Size down. Wait for H4 to resolve before entering.",
    },
}


def get_composite_regime(d1_regime: str, h4_regime: str) -> Dict:
    """
    Look up the composite regime classification for a D1/H4 combination.

    Returns the resolution dict with composite, execution_mode,
    confidence, size_mult, signal_bias, and note.

    All 16 possible combinations are explicitly handled.
    Unknown combinations default to VOLATILE/STAND_DOWN.

    VALIDATED: Table design locked 2025-06-28 based on Problems 1-5
    findings. Re-evaluate cells after 60+ outcomes per combination.
    """
    key = (d1_regime, h4_regime)
    return RESOLUTION_TABLE.get(key, {
        "composite":      "VOLATILE",
        "execution_mode": "STAND_DOWN",
        "confidence":     "NONE",
        "size_mult":      0.0,
        "signal_bias":    "NONE",
        "note":           f"Unknown combination {d1_regime}/{h4_regime} — defaulting to stand-down",
    })


def _detect_structure(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    n: int = 3,
) -> Dict:
    """
    Detect market structure via confirmed pivot highs and lows.

    Replaces the 10-candle slope read which breaks at pullbacks.

    A pivot high at index i requires:
      highs[i] > highs[i-n..i-1] AND highs[i] > highs[i+1..i+n]
      AND a subsequent close below highs[i] (close confirmation)

    A pivot low at index i requires:
      lows[i] < lows[i-n..i-1] AND lows[i] < lows[i+1..i+n]
      AND a subsequent close above lows[i] (close confirmation)

    Returns dict with:
      structure        : "UPTREND" | "DOWNTREND" | "TRANSITIONAL"
      confirmed_highs  : list of confirmed swing high prices (last 5)
      confirmed_lows   : list of confirmed swing low prices (last 5)
      latest_sh        : most recent confirmed swing high price or None
      latest_sl        : most recent confirmed swing low price or None
      prior_sh         : second most recent confirmed swing high or None
      prior_sl         : second most recent confirmed swing low or None
      hh               : bool — latest swing high > prior swing high
      hl               : bool — latest swing low > prior swing low
      lh               : bool — latest swing high < prior swing high
      ll               : bool — latest swing low < prior swing low
      pivot_count_high : int — number of confirmed swing highs found
      pivot_count_low  : int — number of confirmed swing lows found
      slope_fallback   : bool — True if insufficient pivots, fell back to slope
      slope_direction  : 1 or -1 — slope direction used if fallback triggered
    """
    if not closes:
        return {
            "structure": "TRANSITIONAL", "confirmed_highs": [], "confirmed_lows": [],
            "latest_sh": None, "latest_sl": None, "prior_sh": None, "prior_sl": None,
            "hh": False, "hl": False, "lh": False, "ll": False,
            "pivot_count_high": 0, "pivot_count_low": 0,
            "slope_fallback": True, "slope_direction": 0,
        }

    # Sanitize: remove bars where any value is NaN
    # Keeps highs/lows/closes synchronized — same indices dropped from all three
    clean = [
        (h, l, c) for h, l, c in zip(highs, lows, closes)
        if not (math.isnan(h) or math.isnan(l) or math.isnan(c))
    ]
    if not clean:
        return {
            "structure": "TRANSITIONAL", "confirmed_highs": [],
            "confirmed_lows": [], "latest_sh": None, "latest_sl": None,
            "prior_sh": None, "prior_sl": None, "hh": False, "hl": False,
            "lh": False, "ll": False, "pivot_count_high": 0,
            "pivot_count_low": 0, "slope_fallback": True, "slope_direction": 0,
        }
    highs  = [x[0] for x in clean]
    lows   = [x[1] for x in clean]
    closes = [x[2] for x in clean]

    length   = len(closes)
    MIN_BARS = n * 6  # 18 for n=3 — minimum for structural comparison

    # ── Standard pivot detection ───────────────────────────────────────────────
    pivot_highs = []
    pivot_lows  = []

    for i in range(n, length - n):
        if highs[i] == max(highs[i - n : i + n + 1]):
            pivot_highs.append((i, highs[i]))
        if lows[i] == min(lows[i - n : i + n + 1]):
            pivot_lows.append((i, lows[i]))

    confirmed_highs = []
    for idx, price in pivot_highs:
        if any(closes[j] < price for j in range(idx + 1, length)):
            confirmed_highs.append(price)

    confirmed_lows = []
    for idx, price in pivot_lows:
        if any(closes[j] > price for j in range(idx + 1, length)):
            confirmed_lows.append(price)

    confirmed_highs = confirmed_highs[-5:]
    confirmed_lows  = confirmed_lows[-5:]

    # ── Structure determination ────────────────────────────────────────────────
    slope_fallback  = False
    slope_direction = 0

    if len(confirmed_highs) >= 2 and len(confirmed_lows) >= 2:
        # Primary: sufficient confirmed pivots available
        latest_sh = confirmed_highs[-1]
        prior_sh  = confirmed_highs[-2]
        latest_sl = confirmed_lows[-1]
        prior_sl  = confirmed_lows[-2]

    elif length >= MIN_BARS:
        # Secondary: first-half / second-half partition comparison.
        # Handles monotonic data (no local maxima/minima) and low-pivot
        # sequences while still producing meaningful HH/HL/LH/LL flags.
        mid = length // 2
        early_max_h  = max(highs[:mid])
        recent_max_h = max(highs[mid:])
        early_min_l  = min(lows[:mid])
        recent_min_l = min(lows[mid:])

        confirmed_highs = [early_max_h, recent_max_h]
        confirmed_lows  = [early_min_l,  recent_min_l]
        latest_sh = recent_max_h
        prior_sh  = early_max_h
        latest_sl = recent_min_l
        prior_sl  = early_min_l

    else:
        # Insufficient data — slope fallback (safe for any sequence length >= 1)
        slope_fallback  = True
        slope_direction = 1 if closes[-1] > closes[0] else -1
        latest_sh = confirmed_highs[-1] if confirmed_highs else None
        prior_sh  = confirmed_highs[-2] if len(confirmed_highs) >= 2 else None
        latest_sl = confirmed_lows[-1]  if confirmed_lows else None
        prior_sl  = confirmed_lows[-2]  if len(confirmed_lows) >= 2 else None

    hh = (latest_sh is not None and prior_sh is not None and latest_sh > prior_sh)
    hl = (latest_sl is not None and prior_sl is not None and latest_sl > prior_sl)
    lh = (latest_sh is not None and prior_sh is not None and latest_sh < prior_sh)
    ll = (latest_sl is not None and prior_sl is not None and latest_sl < prior_sl)

    if slope_fallback:
        structure = "UPTREND" if slope_direction > 0 else "DOWNTREND"
    elif hh and hl:
        structure = "UPTREND"
    elif lh and ll:
        structure = "DOWNTREND"
    else:
        structure = "TRANSITIONAL"

    return {
        "structure":        structure,
        "confirmed_highs":  confirmed_highs,
        "confirmed_lows":   confirmed_lows,
        "latest_sh":        latest_sh,
        "latest_sl":        latest_sl,
        "prior_sh":         prior_sh,
        "prior_sl":         prior_sl,
        "hh":               hh,
        "hl":               hl,
        "lh":               lh,
        "ll":               ll,
        "pivot_count_high": len(confirmed_highs),
        "pivot_count_low":  len(confirmed_lows),
        "slope_fallback":   slope_fallback,
        "slope_direction":  slope_direction,
    }


def compute_atr_series(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = _ATR_PERIOD,
) -> List[float]:
    n = len(closes)
    tr_list = [
        max(
            highs[i] - lows[i],
            abs(highs[i]  - closes[i - 1]),
            abs(lows[i]   - closes[i - 1]),
        )
        for i in range(1, n)
    ]
    atr = sum(tr_list[:period]) / period
    result = [atr]
    for tr in tr_list[period:]:
        atr = (atr * (period - 1) + tr) / period
        result.append(atr)
    return result


def _compute_adx(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = _ADX_PERIOD,
) -> float:
    """
    Compute ADX using Wilder's smoothing — identical math for D1 and H4 so
    there is zero duplication between timeframes.

    Returns the final ADX value clamped to [0, 100].
    Returns 0.0 if insufficient data (need at least period*2 bars).

    Wilder TR/DM init: sum of first `period` values (not average).
    DX init: simple average of first `period` DX values.
    """
    n = len(closes)
    if n < period * 2:
        return 0.0

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

    if len(tr_list) < period * 2:
        return 0.0

    def _wilder_smooth(values: List[float]) -> List[float]:
        # Wilder init = sum of first `period` values (NOT average); subsequent = Wilder's formula
        result = [sum(values[:period])]
        for v in values[period:]:
            result.append(result[-1] - result[-1] / period + v)
        return result

    s_tr    = _wilder_smooth(tr_list)
    s_plus  = _wilder_smooth(plus_dm)
    s_minus = _wilder_smooth(minus_dm)

    di_plus  = [100 * p / t if t > 0 else 0.0 for p, t in zip(s_plus,  s_tr)]
    di_minus = [100 * m / t if t > 0 else 0.0 for m, t in zip(s_minus, s_tr)]

    dx = [
        100 * abs(p - m) / (p + m) if (p + m) > 0 else 0.0
        for p, m in zip(di_plus, di_minus)
    ]

    if len(dx) < period:
        return 0.0

    # ADX = Wilder-smoothed DX (average for init, Wilder for subsequent)
    adx = sum(dx[:period]) / period
    for d in dx[period:]:
        adx = (adx * (period - 1) + d) / period

    return max(0.0, min(100.0, round(adx, 1)))


def _detect_conflict(d1_regime: str, h4_regime: str) -> Tuple[bool, str]:
    """
    Detect timeframe conflict between D1 and H4 regime classifications.

    A conflict exists when the two timeframes give opposing directional signals.
    Conflict alone does not trigger stand_down — it degrades conviction only.

    Returns (conflict: bool, conflict_type: str).
    """
    if d1_regime == "TRENDING_UP"   and h4_regime == "TRENDING_DOWN":
        return True, "D1_BULLISH_H4_BEARISH"
    if d1_regime == "TRENDING_DOWN" and h4_regime == "TRENDING_UP":
        return True, "D1_BEARISH_H4_BULLISH"
    if d1_regime == "RANGING" and h4_regime == "VOLATILE":
        return True, "RANGING_D1_VOLATILE_H4"
    return False, ""


_OPPOSITE_CONFLICT_TYPES = {"D1_BULLISH_H4_BEARISH", "D1_BEARISH_H4_BULLISH"}


def _stand_down_check(
    d1_regime:    str,
    atr_ratio:    float,
    conflict:     bool,
    conflict_type: str,
) -> Tuple[bool, str]:
    """
    Determine if market conditions warrant a full regime stand-down.

    Stand-down is a hard gate — decision_engine returns NO TRADE immediately.
    Three triggers (empirically validated):
      1. D1 regime is VOLATILE — both momentum and mean-rev fail simultaneously.
      2. Opposite-trend timeframe conflict — D1 and H4 point in opposite directions.
         Fires on conflict_type in {"D1_BULLISH_H4_BEARISH","D1_BEARISH_H4_BULLISH"}
         or when the opposing regime string appears in conflict_type (test format).
      3. Extreme ATR spike >= _ATR_STANDDOWN_THRESHOLD (2.0x) — chaotic expansion.

    Conflict alone (single-timeframe noise) is NOT a stand-down; it is a
    conviction degrader in decision_engine (-20 pts). Stand-down fires only
    on the three conditions above.

    Returns (stand_down: bool, stand_down_reason: str).
    """
    # 1. D1 VOLATILE — no statistical edge on either momentum or mean-reversion
    if d1_regime == "VOLATILE":
        return True, "D1 regime VOLATILE — no statistical edge, stand down"

    # 2. Extreme ATR spike — market in chaotic expansion
    if atr_ratio >= _ATR_STANDDOWN_THRESHOLD:
        return True, (
            f"Extreme ATR spike ({atr_ratio:.1f}x >= {_ATR_STANDDOWN_THRESHOLD}x) "
            "— market in chaotic expansion, stand down"
        )

    # 3. Opposite-trend conflict — D1 and H4 point in genuinely opposite directions
    if conflict and d1_regime in ("TRENDING_UP", "TRENDING_DOWN"):
        opposite = "TRENDING_DOWN" if d1_regime == "TRENDING_UP" else "TRENDING_UP"
        is_opposite = (
            conflict_type in _OPPOSITE_CONFLICT_TYPES or
            opposite in conflict_type
        )
        if is_opposite:
            return True, (
                f"Opposite trend conflict ({conflict_type}) — "
                "D1 and H4 trend in opposite directions, stand down"
            )

    return False, ""


def _compute_weekly_context(
    w_highs:  List[float],
    w_lows:   List[float],
    w_closes: List[float],
) -> Dict:
    """
    Classify weekly multi-timeframe trend context from OANDA weekly bars.

    Returns:
      lt_trend      : "UPTREND" | "DOWNTREND" | "RANGING"
                      20-week dominant trend (_WEEKLY_LT_LOOKBACK)
      st_trend      : "UPTREND" | "DOWNTREND" | "RANGING"
                      4-week short-term trend (_WEEKLY_ST_LOOKBACK)
      weekly_context: "ESTABLISHED_UPTREND" | "ESTABLISHED_DOWNTREND" |
                      "COUNTER_TREND_BOUNCE" | "PULLBACK_IN_UPTREND" | "RANGING"
      context_note  : plain-English explanation of the current context

    Trend direction uses 3-bar recent avg vs 3-bar lookback avg (0.5% threshold).
    Absorbed from htf_structure._trend_direction + _classify_context.
    """
    def _trend_dir(closes: List[float], lookback: int) -> str:
        if len(closes) < lookback + 3:
            return "RANGING"
        recent_avg = sum(closes[-3:]) / 3
        past_avg   = sum(closes[-(lookback + 3) : -(lookback)]) / 3
        if past_avg == 0:
            return "RANGING"
        pct = (recent_avg - past_avg) / past_avg * 100
        if pct > 0.5:
            return "UPTREND"
        if pct < -0.5:
            return "DOWNTREND"
        return "RANGING"

    lt = _trend_dir(w_closes, _WEEKLY_LT_LOOKBACK)
    st = _trend_dir(w_closes, _WEEKLY_ST_LOOKBACK)

    if lt == "UPTREND" and st == "UPTREND":
        ctx  = "ESTABLISHED_UPTREND"
        note = ("Both 5-month and 1-month trends point UP — "
                "strongest environment for longs. Look for pullbacks to key support.")
    elif lt == "DOWNTREND" and st == "DOWNTREND":
        ctx  = "ESTABLISHED_DOWNTREND"
        note = ("Both 5-month and 1-month trends point DOWN — "
                "strongest environment for shorts. Look for rallies to key resistance.")
    elif lt == "DOWNTREND" and st == "UPTREND":
        ctx  = "COUNTER_TREND_BOUNCE"
        note = ("5-month trend is DOWN but price bounced UP over 4 weeks — "
                "counter-trend bounce. Dominant trend typically reasserts.")
    elif lt == "UPTREND" and st == "DOWNTREND":
        ctx  = "PULLBACK_IN_UPTREND"
        note = ("5-month trend is UP, pulling back over 4 weeks — "
                "healthy correction. Look for long entries at key support levels.")
    elif lt == "UPTREND" and st == "RANGING":
        ctx  = "PULLBACK_IN_UPTREND"
        note = ("5-month trend UP, short-term stalling — "
                "pause before continuation. Watch for breakout higher.")
    elif lt == "DOWNTREND" and st == "RANGING":
        ctx  = "ESTABLISHED_DOWNTREND"
        note = ("5-month trend DOWN, short-term stalling — "
                "consolidation before selling resumes. Watch for breakdown lower.")
    else:
        ctx  = "RANGING"
        note = ("No clear trend on either the 5-month or 1-month timeframe — "
                "range-trade only from the extremes of the range.")

    return {"lt_trend": lt, "st_trend": st, "weekly_context": ctx, "context_note": note}


def _compute_ma_context(
    closes: List[float],
    current_price: float,
) -> Dict:
    """
    Compute 50-day and 200-day moving average context.

    Returns:
      ma50          : float or None (None if < _MA_SHORT_PERIOD bars available)
      ma200         : float or None (None if < _MA_LONG_PERIOD bars available)
      price_vs_ma50 : "above" | "below"
      price_vs_ma200: "above" | "below"

    _MA_SHORT_PERIOD = 50  — medium-term structural bias
    _MA_LONG_PERIOD  = 200 — long-term structural bias (absorbed from htf_structure)
    """
    ma50 = (
        round(sum(closes[-_MA_SHORT_PERIOD:]) / _MA_SHORT_PERIOD, 4)
        if len(closes) >= _MA_SHORT_PERIOD else None
    )
    ma200 = (
        round(sum(closes[-_MA_LONG_PERIOD:]) / _MA_LONG_PERIOD, 4)
        if len(closes) >= _MA_LONG_PERIOD else None
    )
    return {
        "ma50":           ma50,
        "ma200":          ma200,
        "price_vs_ma50":  "above" if ma50  and current_price > ma50  else "below",
        "price_vs_ma200": "above" if ma200 and current_price > ma200 else "below",
    }


def _classify(adx: float, atr_ratio: float, slope: float,
              instrument: str = "GBP_AUD",
              pair: "PairConfig" = None) -> str:
    """
    Regime classification using empirically validated ADX zones.

    VALIDATED FINDING (2025-06-25, 5yr D1 backtest):
    - ADX < 18: mean reversion dominant on both pairs — RANGING
    - ADX 18-25: no consistent edge — TRANSITION (size down, require structure)
    - ADX 25-32: narrow momentum window, degrades fast — TRENDING (cautious)
    - ADX 32+ GBP/JPY: 82.7% mean reversion at 40+ — EXHAUSTION → RANGING
    - ADX > 32 general: late-trend, not entry signal — flag in output

    ADX does NOT predict trend continuation. It measures trend strength
    that already occurred. Use structure (Problem 2) for direction confirmation.
    """
    # GBP/JPY compression stand-down (pre-BoJ coil)
    if pair and pair.atr_compression_min > 0:
        if atr_ratio < pair.atr_compression_min:
            return "VOLATILE"  # compression zone — both signals fail

    spike_mult = pair.atr_spike_multiplier if pair else 1.5

    # ATR spike override — fires regardless of ADX zone
    if atr_ratio >= spike_mult:
        return "VOLATILE"

    # GBP/JPY exhaustion regime — high ADX means mean reversion, not trend
    if instrument == "GBP_JPY" and adx >= _ADX_JPY_EXHAUSTION:
        return "RANGING"  # exhaustion: fade, don't follow

    # Late-trend warning for both pairs
    if adx >= _ADX_EXHAUSTION_THRESHOLD:
        # Still classify as trending but caller gets exhaustion flag
        return "TRENDING_UP" if slope > 0 else "TRENDING_DOWN"

    # Validated transition zone — no statistical edge
    if _ADX_RANGING_THRESHOLD <= adx < _ADX_TRANSITION_HIGH:
        return "VOLATILE"  # no edge = treat as untradeable until structure confirms

    # Mean reversion dominant — spike already handled above
    if adx < _ADX_RANGING_THRESHOLD:
        return "RANGING"

    # ADX 25-32: narrow momentum window — require HTF structure (Problem 2)
    return "TRENDING_UP" if slope > 0 else "TRENDING_DOWN"


def get_regime(ticker: str = "GBP_AUD") -> Dict:
    pair = PAIRS.get(ticker)
    if pair is None:
        return _error_result(
            f"Unknown instrument '{ticker}'. "
            f"Valid instruments: {list(PAIRS.keys())}"
        )

    if not _oanda_ok():
        return _error_result("OANDA not configured — set OANDA_API_KEY and OANDA_ACCOUNT_ID")

    oanda_pair = pair.instrument.replace("_", "")
    try:
        raw = _oanda_daily_bars(pair=oanda_pair, count=220)
    except Exception as exc:
        try:
            from oanda_feed import get_daily_bars, is_configured
            raw = get_daily_bars(pair=oanda_pair, count=220) if is_configured() else None
        except Exception:
            raw = None
        if raw is None:
            return _error_result(f"OANDA unavailable for {pair.display_name}: {exc}")

    if raw is None or raw.empty or len(raw) < _ADX_PERIOD * 3:
        return _error_result("Not enough data to calculate regime indicators")

    if hasattr(raw.columns, "levels"):
        raw.columns = raw.columns.get_level_values(0)

    highs  = [float(v) for v in raw["High"].dropna().values]
    lows   = [float(v) for v in raw["Low"].dropna().values]
    closes = [float(v) for v in raw["Close"].dropna().values]

    n = min(len(highs), len(lows), len(closes))
    highs, lows, closes = highs[:n], lows[:n], closes[:n]

    if n < _ADX_PERIOD * 3:
        return _error_result(f"Only {n} data points — need at least {_ADX_PERIOD * 3}")

    current_price = closes[-1]

    # ── ATR ───────────────────────────────────────────────────────────────────
    atr_series  = compute_atr_series(highs, lows, closes)
    current_atr = atr_series[-1]
    avg_atr_20  = sum(atr_series[-20:]) / min(20, len(atr_series))
    atr_pips    = round(current_atr / pair.pip_size, 1)
    atr_pct     = round(current_atr / current_price * 100, 3)
    atr_ratio   = round(current_atr / avg_atr_20, 2) if avg_atr_20 > 0 else 1.0

    # ── ADX ───────────────────────────────────────────────────────────────────
    current_adx = _compute_adx(highs, lows, closes)
    if current_adx == 0.0 and n < _ADX_PERIOD * 2:
        return _error_result("Insufficient data for ADX calculation")

    # ── Volatility level ──────────────────────────────────────────────────────
    if atr_pct > 0.8:
        volatility = "EXTREME"
        vol_note   = "Extremely wide daily ranges — significant risk, size down"
    elif atr_pct > 0.5:
        volatility = "HIGH"
        vol_note   = "Above-average volatility — widen your stops"
    elif atr_pct > 0.25:
        volatility = "NORMAL"
        vol_note   = "Normal volatility for GBP/AUD"
    else:
        volatility = "LOW"
        vol_note   = "Quiet market — moves may be small and slow"

    # ── Structure detection (replaces slope) ──────────────────────────────────
    structure_data = _detect_structure(highs, lows, closes)
    structure      = structure_data["structure"]

    # Direction for _classify(): derived from structure, falls back to slope
    if structure == "UPTREND":
        slope = 1.0
    elif structure == "DOWNTREND":
        slope = -1.0
    else:
        # TRANSITIONAL: use slope as tiebreaker, reduce confidence
        slope = closes[-1] - closes[-10] if len(closes) >= 10 else 0

    # ── D1 regime classification ──────────────────────────────────────────────
    d1_regime = _classify(current_adx, atr_ratio, slope, pair=pair,
                          instrument=pair.instrument)
    regime = d1_regime  # backward compat alias

    # ── H4 multi-timeframe classification ─────────────────────────────────────
    h4_regime = d1_regime   # safe fallback: inherit D1 when H4 unavailable
    adx_h4    = 0.0

    try:
        raw_h4 = _oanda_h4_bars(pair=oanda_pair, count=120)
    except Exception:
        raw_h4 = None

    if raw_h4 is not None and not raw_h4.empty:
        if hasattr(raw_h4.columns, "levels"):
            raw_h4.columns = raw_h4.columns.get_level_values(0)
        h4h = [float(v) for v in raw_h4["High"].dropna().values]
        h4l = [float(v) for v in raw_h4["Low"].dropna().values]
        h4c = [float(v) for v in raw_h4["Close"].dropna().values]
        nh4 = min(len(h4h), len(h4l), len(h4c))
        h4h, h4l, h4c = h4h[:nh4], h4l[:nh4], h4c[:nh4]

        if nh4 >= _ADX_PERIOD * 3:
            h4_atr_s       = compute_atr_series(h4h, h4l, h4c)
            h4_avg_atr     = sum(h4_atr_s[-20:]) / min(20, len(h4_atr_s))
            h4_atr_ratio   = round(h4_atr_s[-1] / h4_avg_atr, 2) if h4_avg_atr > 0 else 1.0
            adx_h4         = _compute_adx(h4h, h4l, h4c)
            h4_struct      = _detect_structure(h4h, h4l, h4c)
            if h4_struct["structure"] == "UPTREND":
                h4_slope = 1.0
            elif h4_struct["structure"] == "DOWNTREND":
                h4_slope = -1.0
            else:
                h4_slope = h4c[-1] - h4c[-10] if len(h4c) >= 10 else 0
            h4_regime = _classify(adx_h4, h4_atr_ratio, h4_slope,
                                  instrument=pair.instrument, pair=pair)

    conflict, conflict_type = _detect_conflict(d1_regime, h4_regime)
    stand_down, stand_down_reason = _stand_down_check(
        d1_regime, atr_ratio, conflict, conflict_type
    )

    # ── Composite regime resolution ───────────────────────────────────────────
    resolution      = get_composite_regime(d1_regime, h4_regime)
    execution_mode  = resolution["execution_mode"]
    confidence      = resolution["confidence"]
    size_mult       = resolution["size_mult"]
    signal_bias     = resolution["signal_bias"]
    resolution_note = resolution["note"]
    # Resolution table is authoritative on stand_down — if it says STAND_DOWN,
    # enforce it even if _stand_down_check() didn't fire independently.
    if execution_mode == "STAND_DOWN":
        stand_down = True
        if not stand_down_reason:
            stand_down_reason = resolution_note

    # ── Weekly context + MA (absorbs htf_structure weekly/MA logic) ────────────
    lt_trend = st_trend = weekly_context = "RANGING"
    context_note = ""

    try:
        raw_w = _oanda_weekly_bars(pair=oanda_pair, count=110)
    except Exception:
        raw_w = None

    if raw_w is not None and not raw_w.empty and len(raw_w) >= _WEEKLY_LT_LOOKBACK:
        if hasattr(raw_w.columns, "levels"):
            raw_w.columns = raw_w.columns.get_level_values(0)
        wh = [float(v) for v in raw_w["High"].dropna().values]
        wl = [float(v) for v in raw_w["Low"].dropna().values]
        wc = [float(v) for v in raw_w["Close"].dropna().values]
        _wctx        = _compute_weekly_context(wh, wl, wc)
        lt_trend     = _wctx["lt_trend"]
        st_trend     = _wctx["st_trend"]
        weekly_context = _wctx["weekly_context"]
        context_note   = _wctx["context_note"]

    _mac           = _compute_ma_context(closes, current_price)
    ma50           = _mac["ma50"]
    ma200          = _mac["ma200"]
    price_vs_ma50  = _mac["price_vs_ma50"]
    price_vs_ma200 = _mac["price_vs_ma200"]

    is_exhaustion = (
        current_adx >= _ADX_EXHAUSTION_THRESHOLD or
        (pair.instrument == "GBP_JPY" and current_adx >= _ADX_JPY_EXHAUSTION)
    )

    if regime == "TRENDING_UP":
        if is_exhaustion:
            regime_label  = "Late uptrend — ADX in exhaustion zone, size down"
            trade_guidance = (
                f"Uptrend is in late stage (ADX {current_adx}). "
                "Mean reversion probability is elevated. "
                "Do not chase — wait for a pullback or sit out. "
                "If holding a long, consider reducing position."
            )
        else:
            regime_label  = "Uptrend in progress — HTF structure confirmation required"
            trade_guidance = (
                "Market trending UP. ADX 25-32 shows momentum but degrades fast. "
                "Wait for pullbacks to key support. "
                "Require higher timeframe structure confirmation before entering. "
                "Do not fight the trend with short trades."
            )
    elif regime == "TRENDING_DOWN":
        if is_exhaustion:
            regime_label  = "Late downtrend — ADX in exhaustion zone, size down"
            trade_guidance = (
                f"Downtrend is in late stage (ADX {current_adx}). "
                "Mean reversion probability is elevated. "
                "Do not chase — wait for a rally or sit out. "
                "If holding a short, consider reducing position."
            )
        else:
            regime_label  = "Downtrend in progress — HTF structure confirmation required"
            trade_guidance = (
                "Market trending DOWN. ADX 25-32 shows momentum but degrades fast. "
                "Wait for rallies to key resistance. "
                "Require higher timeframe structure confirmation before entering. "
                "Do not fight the trend with long trades."
            )
    elif regime == "VOLATILE":
        regime_label  = "Transition zone — no statistical edge (ADX 18-25)"
        trade_guidance = (
            f"ADX {current_adx} is in the transition zone (18-25). "
            "No consistent momentum or mean-reversion edge. "
            "Wait for structural confirmation before entering. "
            "Size down significantly if you trade."
        )
    else:  # RANGING
        if is_exhaustion:
            regime_label  = "Trend exhausted — mean reversion elevated"
            trade_guidance = (
                f"ADX {current_adx} — trend has exhausted. "
                "Mean reversion probability very high. "
                "Fade extended moves from structural extremes. "
                "Do not enter trend trades at this ADX level."
            )
        elif atr_ratio > pair.atr_spike_multiplier:
            regime_label  = "Choppy and volatile — no clear direction"
            trade_guidance = (
                "Market volatile with no clear trend. "
                "Reduce position size — moves are unpredictable. "
                "Use tight stops and take profit quickly if you trade at all. "
                "This is the hardest regime — consider waiting for a clearer setup."
            )
        else:
            regime_label  = "Ranging market — mean reversion dominant"
            trade_guidance = (
                f"Market has no strong trend (ADX {current_adx}). "
                "Best strategy: trade only from the edges of the range. "
                "Buy near range lows, sell near range highs. "
                "Take profit quickly — do not hold for large moves. "
                "Avoid entering in the middle of the range."
            )

    # ── Daily fuel calculation ────────────────────────────────────────────────
    # Today's intraday range vs ATR capacity
    today_high   = highs[-1]
    today_low    = lows[-1]
    range_used   = round((today_high - today_low) / pair.pip_size)
    range_remain = round(max(0, atr_pips - range_used))
    fuel_pct     = min(100, round(range_used / atr_pips * 100)) if atr_pips > 0 else 0

    if fuel_pct < 25:
        fuel_label = "FULL TANK  -  day is young, plenty of range left"
    elif fuel_pct < 50:
        fuel_label = "HALF TANK  -  good range remaining"
    elif fuel_pct < 75:
        fuel_label = "RUNNING LOW  -  limited range left today"
    else:
        fuel_label = "NEAR EMPTY  -  most of today's range already used"

    # ── Pre-compute fields needed by no_trade_filter before return ───────────
    _atr_compression = (
        pair.atr_compression_min > 0 and
        atr_ratio < pair.atr_compression_min
    )
    _atr_compression_note = (
        f"ATR ratio {atr_ratio:.2f}x is below compression "
        f"threshold {pair.atr_compression_min}x — "
        f"pre-intervention coil detected. Both signals historically fail here."
        if _atr_compression else ""
    )
    _d1_structure = structure_data["structure"]

    from no_trade_filter import apply_filter as _apply_filter, get_filter_summary as _get_filter_summary
    _fr = _apply_filter({
        "regime_d1":            d1_regime,
        "regime_h4":            h4_regime,
        "adx_h4":               adx_h4,
        "atr_vs_avg":           atr_ratio,
        "atr_compression":      _atr_compression,
        "atr_compression_note": _atr_compression_note,
        "timeframe_conflict":   conflict,
        "conflict_type":        conflict_type,
        "structure":            _d1_structure,
        "weekly_context":       weekly_context,
        "lt_trend":             lt_trend,
        "st_trend":             st_trend,
        "execution_mode":       execution_mode,
        "size_mult":            size_mult,
        "resolution_note":      resolution_note,
    })
    _fr_summary = _get_filter_summary(_fr)

    return {
        "regime":          regime,
        "regime_label":    regime_label,
        "adx":             current_adx,
        "atr":             round(current_atr, 5),
        "atr_pips":        atr_pips,
        "atr_pct":         atr_pct,
        "atr_vs_avg":      atr_ratio,
        "volatility":      volatility,
        "vol_note":        vol_note,
        "trade_guidance":  trade_guidance,
        "current_price":   round(current_price, 4),
        "today_high":      round(today_high, 4),
        "today_low":       round(today_low, 4),
        "range_used":      range_used,
        "range_remaining": range_remain,
        "fuel_pct":        fuel_pct,
        "fuel_label":      fuel_label,
        "pair":            pair.display_name,
        "instrument":      pair.instrument,
        # ── Multi-timeframe (D1 + H4) ─────────────────────────────────────────
        "regime_d1":          d1_regime,
        "regime_h4":          h4_regime,
        "adx_h4":             adx_h4,
        "timeframe_conflict": conflict,
        "conflict_type":      conflict_type,
        "stand_down":         stand_down,
        "stand_down_reason":  stand_down_reason,
        # ── Composite resolution (Problem 6) ──────────────────────────────────
        "execution_mode":     execution_mode,
        "confidence":         confidence,
        "size_mult":          size_mult,
        "signal_bias":        signal_bias,
        "resolution_note":    resolution_note,
        # ── Weekly context (absorbed from htf_structure) ───────────────────────
        "lt_trend":           lt_trend,
        "st_trend":           st_trend,
        "weekly_context":     weekly_context,
        "context_note":       context_note,
        "ma50":               ma50,
        "ma200":              ma200,
        "price_vs_ma50":      price_vs_ma50,
        "price_vs_ma200":     price_vs_ma200,
        # ── Structure (Problem 2) ─────────────────────────────────────────────
        "structure":        _d1_structure,
        "confirmed_highs":  structure_data["confirmed_highs"],
        "confirmed_lows":   structure_data["confirmed_lows"],
        "latest_sh":        structure_data["latest_sh"],
        "latest_sl":        structure_data["latest_sl"],
        "hh":               structure_data["hh"],
        "hl":               structure_data["hl"],
        "lh":               structure_data["lh"],
        "ll":               structure_data["ll"],
        "slope_fallback":   structure_data["slope_fallback"],
        "pivot_count_high": structure_data["pivot_count_high"],
        "pivot_count_low":  structure_data["pivot_count_low"],
        "adx_exhaustion": (
            (current_adx >= _ADX_EXHAUSTION_THRESHOLD) or
            (pair.instrument == "GBP_JPY" and current_adx >= _ADX_JPY_EXHAUSTION)
        ),
        "adx_exhaustion_note": (
            f"ADX {current_adx} — late trend warning. "
            f"Mean reversion probability elevated. Size down, do not chase."
            if (current_adx >= _ADX_EXHAUSTION_THRESHOLD or
                (pair.instrument == "GBP_JPY" and current_adx >= _ADX_JPY_EXHAUSTION))
            else ""
        ),
        "atr_compression":      _atr_compression,
        "atr_compression_note": _atr_compression_note,
        "atr_spike_multiplier": pair.atr_spike_multiplier,
        "atr_compression_min":  pair.atr_compression_min,
        # ── No-trade filter (Problem 8) ───────────────────────────────────────
        "filter_allowed":      _fr.allowed,
        "filter_mode":         _fr.execution_mode,
        "filter_size_mult":    _fr.size_mult,
        "filter_reason":       _fr.reason,
        "override_fired":      _fr.override_fired,
        "override_conditions": _fr.override_conditions,
        "filter_summary":      _fr_summary,
        "error":           None,
    }


def _error_result(msg: str) -> Dict:
    return {
        "regime":         "UNKNOWN",
        "regime_label":   "Could not determine regime",
        "adx":            0.0,
        "atr":            0.0,
        "atr_pips":       0.0,
        "atr_pct":        0.0,
        "atr_vs_avg":     1.0,
        "volatility":     "UNKNOWN",
        "vol_note":       msg,
        "trade_guidance": "Regime data unavailable — proceed with caution.",
        "current_price":  None,
        "error":          msg,
        "today_high":     None,
        "today_low":      None,
        "range_used":     None,
        "range_remaining":None,
        "fuel_pct":       None,
        "fuel_label":          "unavailable",
        "pair":                "",
        "instrument":          "UNKNOWN",
        "regime_d1":           "UNKNOWN",
        "regime_h4":           "UNKNOWN",
        "adx_h4":              0.0,
        "timeframe_conflict":  False,
        "conflict_type":       "",
        "stand_down":          False,
        "stand_down_reason":   "",
        "execution_mode":      "STAND_DOWN",
        "confidence":          "NONE",
        "size_mult":           0.0,
        "signal_bias":         "NONE",
        "resolution_note":     "",
        "adx_exhaustion":      False,
        "adx_exhaustion_note": "",
        "atr_compression":     False,
        "atr_compression_note": "",
        "atr_spike_multiplier": 1.5,
        "atr_compression_min": 0.0,
        "filter_allowed":      False,
        "filter_mode":         "STAND_DOWN",
        "filter_size_mult":    0.0,
        "filter_reason":       "",
        "override_fired":      False,
        "override_conditions": "",
        "filter_summary":      "",
        "structure":           "TRANSITIONAL",
        "confirmed_highs":     [],
        "confirmed_lows":      [],
        "latest_sh":           None,
        "latest_sl":           None,
        "hh":                  False,
        "hl":                  False,
        "lh":                  False,
        "ll":                  False,
        "slope_fallback":      False,
        "pivot_count_high":    0,
        "pivot_count_low":     0,
        "lt_trend":            "RANGING",
        "st_trend":            "RANGING",
        "weekly_context":      "RANGING",
        "context_note":        "",
        "ma50":                None,
        "ma200":               None,
        "price_vs_ma50":       "unknown",
        "price_vs_ma200":      "unknown",
    }


if __name__ == "__main__":
    data = get_regime()
    if data["error"]:
        print(f"Error: {data['error']}")
    else:
        print(f"Regime      : {data['regime_label']}")
        print(f"ADX         : {data['adx']}  (>25 trending | 20-25 developing | <20 ranging)")
        print(f"ATR         : {data['atr_pips']} pips  ({data['atr_pct']}% of price)")
        print(f"ATR vs avg  : {data['atr_vs_avg']}x  (>1.3 = expanding volatility)")
        print(f"Volatility  : {data['volatility']}  — {data['vol_note']}")
        print(f"\nGuidance: {data['trade_guidance']}")
