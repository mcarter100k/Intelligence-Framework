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
from typing import Dict, List, Optional
from datetime import datetime

from oanda_feed import get_daily_bars as _oanda_daily_bars, is_configured as _oanda_ok

PAIR_TICKER  = "GBPAUD=X"
_ATR_PERIOD  = 14
_ADX_PERIOD  = 14


def get_regime(ticker: str = "GBP_AUD") -> Dict:
    if not _oanda_ok():
        return _error_result("OANDA not configured — set OANDA_API_KEY and OANDA_ACCOUNT_ID")

    try:
        raw = _oanda_daily_bars(count=90)
    except Exception as exc:
        # yfinance failed — try OANDA daily bars as silent fallback
        try:
            from oanda_feed import get_daily_bars, is_configured
            raw = get_daily_bars(count=100) if is_configured() else None
        except Exception:
            raw = None
        if raw is None:
            return _error_result(f"yfinance failed, OANDA unavailable: {exc}")

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

    # ── ATR (correct Wilder smoothing) ────────────────────────────────────────
    tr_list = []
    for i in range(1, n):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i]  - closes[i - 1]),
        )
        tr_list.append(tr)

    # Initial ATR = simple average of first period TRs
    atr = sum(tr_list[:_ATR_PERIOD]) / _ATR_PERIOD
    atr_series = [atr]
    for tr in tr_list[_ATR_PERIOD:]:
        # Wilder: new_ATR = (prev_ATR * (n-1) + TR) / n
        atr = (atr * (_ATR_PERIOD - 1) + tr) / _ATR_PERIOD
        atr_series.append(atr)

    current_atr = atr_series[-1]
    avg_atr_20  = sum(atr_series[-20:]) / min(20, len(atr_series))
    atr_pips    = round(current_atr * 10000, 1)   # 4 decimal places for GBP/AUD
    atr_pct     = round(current_atr / current_price * 100, 3)
    atr_ratio   = round(current_atr / avg_atr_20, 2) if avg_atr_20 > 0 else 1.0

    # ── ADX (correct Wilder smoothing) ────────────────────────────────────────
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

    # ── Regime classification ─────────────────────────────────────────────────
    recent_slope = closes[-1] - closes[-10]

    if current_adx >= 25:
        if recent_slope > 0:
            regime = "TRENDING_UP"
            regime_label = "Strong uptrend in progress"
            trade_guidance = (
                "Market is trending UP strongly. "
                "Best strategy: wait for pullbacks to key support levels, then enter long. "
                "Hold positions longer than usual — trending markets run further than expected. "
                "Do not fight the trend with short trades."
            ).format(adx=current_adx)
        else:
            regime = "TRENDING_DOWN"
            regime_label = "Strong downtrend in progress"
            trade_guidance = (
                "Market is trending DOWN strongly. "
                "Best strategy: wait for rallies to key resistance levels, then enter short. "
                "Hold positions longer than usual. "
                "Do not fight the trend with long trades."
            ).format(adx=current_adx)
    elif current_adx < 20:
        if atr_ratio > 1.3:
            regime = "VOLATILE"
            regime_label = "Choppy and volatile — no clear direction"
            trade_guidance = (
                "Market is volatile with no clear trend. "
                "Reduce position size — moves are unpredictable. "
                "Use tight stops and take profit quickly if you trade at all. "
                "This is the hardest regime — consider waiting for a clearer setup."
            ).format(adx=current_adx)
        else:
            regime = "RANGING"
            regime_label = "Ranging market — price chopping sideways"
            trade_guidance = (
                "Market has no strong trend (ADX {adx}). "
                "Best strategy: trade only from the edges of the range. "
                "Buy near range lows, sell near range highs. "
                "Take profit quickly — do not hold for large moves. "
                "Avoid entering in the middle of the range."
            ).format(adx=current_adx)
    else:
        # Transition zone ADX 20-25
        if recent_slope > 0:
            regime = "TRENDING_UP"
            regime_label = "Weak uptrend developing — watch for confirmation"
            trade_guidance = (
                "A weak uptrend is developing. "
                "Wait for ADX to push above 25 before sizing up. "
                "For now use smaller positions — treat like a ranging market."
            ).format(adx=current_adx)
        else:
            regime = "TRENDING_DOWN"
            regime_label = "Weak downtrend developing — watch for confirmation"
            trade_guidance = (
                "A weak downtrend is developing. "
                "Wait for ADX to push above 25 before sizing up. "
                "For now use smaller positions — treat like a ranging market."
            ).format(adx=current_adx)

    # ── Daily fuel calculation ────────────────────────────────────────────────
    # Today's intraday range vs ATR capacity
    today_high   = highs[-1]
    today_low    = lows[-1]
    range_used   = round((today_high - today_low) * 10000)  # in pips
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
        "fuel_label":     "unavailable",
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
