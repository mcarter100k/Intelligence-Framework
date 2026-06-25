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
from typing import Dict, List, Optional
from datetime import datetime

from oanda_feed import get_daily_bars as _oanda_daily_bars, is_configured as _oanda_ok

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
    pair = PAIRS.get(ticker, PAIRS["GBP_AUD"])

    if not _oanda_ok():
        return _error_result("OANDA not configured — set OANDA_API_KEY and OANDA_ACCOUNT_ID")

    oanda_pair = pair.instrument.replace("_", "")
    try:
        raw = _oanda_daily_bars(pair=oanda_pair, count=90)
    except Exception as exc:
        try:
            from oanda_feed import get_daily_bars, is_configured
            raw = get_daily_bars(pair=oanda_pair, count=100) if is_configured() else None
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

    # ── ADX (correct Wilder smoothing) ────────────────────────────────────────
    tr_list = [
        max(highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i]  - closes[i - 1]))
        for i in range(1, n)
    ]

    plus_dm_list  = []
    minus_dm_list = []

    for i in range(1, n):
        up   = highs[i]  - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm_list.append(up   if (up > down and up > 0)   else 0.0)
        minus_dm_list.append(down if (down > up and down > 0) else 0.0)

    if len(plus_dm_list) < _ADX_PERIOD * 2:
        return _error_result("Insufficient DM data for ADX calculation")

    # Wilder-smooth TR, +DM, -DM over ADX_PERIOD
    def wilder_init_and_smooth(values: List[float], period: int) -> List[float]:
        result = [sum(values[:period])]          # initial = sum (not average) per Wilder
        for v in values[period:]:
            result.append(result[-1] - result[-1] / period + v)
        return result

    smooth_tr    = wilder_init_and_smooth(tr_list,       _ADX_PERIOD)
    smooth_plus  = wilder_init_and_smooth(plus_dm_list,  _ADX_PERIOD)
    smooth_minus = wilder_init_and_smooth(minus_dm_list, _ADX_PERIOD)

    # DI+ and DI-
    di_plus  = [100 * p / t if t > 0 else 0.0 for p, t in zip(smooth_plus,  smooth_tr)]
    di_minus = [100 * m / t if t > 0 else 0.0 for m, t in zip(smooth_minus, smooth_tr)]

    # DX
    dx_list = []
    for p, m in zip(di_plus, di_minus):
        denom = p + m
        dx_list.append(100 * abs(p - m) / denom if denom > 0 else 0.0)

    if len(dx_list) < _ADX_PERIOD:
        return _error_result("Insufficient DX data for ADX calculation")

    # ADX = Wilder-smoothed DX (average not sum for init here)
    adx = sum(dx_list[:_ADX_PERIOD]) / _ADX_PERIOD
    adx_series = [adx]
    for dx in dx_list[_ADX_PERIOD:]:
        adx = (adx * (_ADX_PERIOD - 1) + dx) / _ADX_PERIOD
        adx_series.append(adx)

    current_adx = round(adx_series[-1], 1)
    # ADX must be 0-100 — clamp in case of any float drift
    current_adx = max(0.0, min(100.0, current_adx))

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

    # ── Regime classification ─────────────────────────────────────────────────
    regime = _classify(current_adx, atr_ratio, slope, pair=pair,
                       instrument=pair.instrument)

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
        # ── Problem 2 stubs (populated when multi-timeframe analysis is added) ──
        "regime_d1":          regime,
        "regime_h4":          "UNKNOWN",
        "adx_h4":             0.0,
        "timeframe_conflict": False,
        "conflict_type":      "",
        "stand_down":         False,
        "stand_down_reason":  "",
        # ── Structure (Problem 2) ─────────────────────────────────────────────
        "structure":        structure_data["structure"],
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
        "atr_compression":      (
            pair.atr_compression_min > 0 and
            atr_ratio < pair.atr_compression_min
        ),
        "atr_compression_note": (
            f"ATR ratio {atr_ratio:.2f}x is below compression "
            f"threshold {pair.atr_compression_min}x — "
            f"pre-intervention coil detected. Both signals historically fail here."
            if (pair.atr_compression_min > 0 and
                atr_ratio < pair.atr_compression_min)
            else ""
        ),
        "atr_spike_multiplier": pair.atr_spike_multiplier,
        "atr_compression_min":  pair.atr_compression_min,
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
        "adx_exhaustion":      False,
        "adx_exhaustion_note": "",
        "atr_compression":     False,
        "atr_compression_note": "",
        "atr_spike_multiplier": 1.5,
        "atr_compression_min": 0.0,
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
