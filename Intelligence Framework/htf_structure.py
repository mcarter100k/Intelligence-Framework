"""
htf_structure.py

Multi-timeframe structure analysis for GBP/AUD.

The key insight this version adds:
  A 4-week uptrend inside a 20-week downtrend is NOT an uptrend.
  It is a counter-trend bounce — and trading it as a trend is dangerous.

Timeframes:
  Long-term  : 20 weekly bars (~5 months) — the DOMINANT trend
  Short-term : 4 weekly bars (~1 month)   — the CURRENT momentum
  Daily      : 10 daily bars              — the entry-level direction

When short-term and long-term conflict:
  Short UP + Long DOWN = COUNTER-TREND BOUNCE (dangerous to buy)
  Short DOWN + Long UP = PULLBACK IN UPTREND (opportunity to buy dip)

Also calculates:
  - Trend age: how many weeks the current move has been running
  - Distance from long-term high/low: how extended the bounce/pullback is
  - 50-day and 200-day moving average context
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from oanda_feed import get_weekly_bars, get_daily_bars, is_configured as _oanda_ok


def get_htf_structure(ticker: str = "GBP_AUD") -> Dict:
    if not _oanda_ok():
        return _error_result("OANDA not configured — set OANDA_API_KEY and OANDA_ACCOUNT_ID")

    try:
        weekly = get_weekly_bars(count=110)
        daily  = get_daily_bars(count=365)
    except Exception as exc:
        return _error_result(f"OANDA unavailable: {exc}")

    if weekly is None or weekly.empty or len(weekly) < 20:
        return _error_result("Not enough weekly data — need at least 20 weeks")
    if daily is None or daily.empty or len(daily) < 50:
        return _error_result("Not enough daily data — need at least 50 days")

    for df in [weekly, daily]:
        if hasattr(df.columns, "levels"):
            df.columns = df.columns.get_level_values(0)

    w_closes = [float(v) for v in weekly["Close"].dropna().values]
    w_highs  = [float(v) for v in weekly["High"].dropna().values]
    w_lows   = [float(v) for v in weekly["Low"].dropna().values]
    d_closes = [float(v) for v in daily["Close"].dropna().values]
    d_highs  = [float(v) for v in daily["High"].dropna().values]
    d_lows   = [float(v) for v in daily["Low"].dropna().values]

    current_price = w_closes[-1]

    # ── Long-term trend (20 weeks = ~5 months) ────────────────────────────────
    lt_trend, lt_pct = _trend_direction(w_closes, lookback=20)

    # ── Short-term trend (4 weeks = ~1 month) ─────────────────────────────────
    st_trend, st_pct = _trend_direction(w_closes, lookback=4)

    # ── Daily trend (10 days) ─────────────────────────────────────────────────
    daily_trend, daily_pct = _trend_direction(d_closes, lookback=10)

    # ── Trend age — how many weeks in the current direction ───────────────────
    trend_age_weeks = _count_trend_age(w_closes, st_trend)

    # ── Long-term high/low (20 weeks) ─────────────────────────────────────────
    lt_high = max(w_highs[-20:])
    lt_low  = min(w_lows[-20:])
    lt_range = lt_high - lt_low

    # Distance from long-term extremes
    dist_from_lt_high = round((lt_high - current_price) / lt_high * 100, 1)
    dist_from_lt_low  = round((current_price - lt_low)  / lt_low  * 100, 1)

    # ── 10-week range for range position ──────────────────────────────────────
    wk_high_10 = max(w_highs[-10:]) if len(w_highs) >= 10 else max(w_highs)
    wk_low_10  = min(w_lows[-10:])  if len(w_lows)  >= 10 else min(w_lows)
    wk_range   = wk_high_10 - wk_low_10
    range_pct  = ((current_price - wk_low_10) / wk_range * 100) if wk_range > 0 else 50.0
    range_pct  = round(max(0, min(100, range_pct)), 1)

    if range_pct >= 75:
        range_label = "top of weekly range (near resistance)"
    elif range_pct >= 50:
        range_label = "upper half of weekly range"
    elif range_pct >= 25:
        range_label = "lower half of weekly range"
    else:
        range_label = "bottom of weekly range (near support)"

    # ── Fibonacci retracement of the dominant move ────────────────────────────
    # The dominant move: from lt_high (the top) to lt_low (the bottom of the drop)
    # The bounce retraces some % of that move. Standard levels: 23.6, 38.2, 50, 61.8, 78.6
    fib_levels = {}
    fib_label  = "Unknown"
    fib_pct    = 0.0

    if lt_high > lt_low and lt_trend == "DOWNTREND":
        total_drop = lt_high - lt_low
        bounce     = current_price - lt_low
        fib_pct    = round(bounce / total_drop * 100, 1) if total_drop > 0 else 0.0

        # Key Fibonacci levels (price)
        fib_levels = {
            "23.6": round(lt_low + total_drop * 0.236, 4),
            "38.2": round(lt_low + total_drop * 0.382, 4),
            "50.0": round(lt_low + total_drop * 0.500, 4),
            "61.8": round(lt_low + total_drop * 0.618, 4),
            "78.6": round(lt_low + total_drop * 0.786, 4),
        }

        # Where is price relative to Fibonacci levels?
        if fib_pct < 23.6:
            fib_label = "below 23.6% retracement — bounce barely started"
        elif fib_pct < 38.2:
            fib_label = "between 23.6% and 38.2% — early stage bounce"
        elif fib_pct < 50.0:
            fib_label = "approaching 38.2% retracement — common bounce target"
        elif fib_pct < 61.8:
            fib_label = "between 38.2% and 61.8% — extended bounce, watch for resistance"
        elif fib_pct < 78.6:
            fib_label = "beyond 61.8% retracement — deep bounce, near danger zone for shorts"
        else:
            fib_label = "beyond 78.6% — bounce this deep often becomes a full reversal"

    elif lt_trend == "UPTREND":
        # Pullback in uptrend — how deep is the pullback?
        total_rise = lt_high - lt_low
        pullback   = lt_high - current_price
        fib_pct    = round(pullback / total_rise * 100, 1) if total_rise > 0 else 0.0

        fib_levels = {
            "23.6": round(lt_high - total_rise * 0.236, 4),
            "38.2": round(lt_high - total_rise * 0.382, 4),
            "50.0": round(lt_high - total_rise * 0.500, 4),
            "61.8": round(lt_high - total_rise * 0.618, 4),
        }

        if fib_pct < 23.6:
            fib_label = "shallow pullback — below 23.6%, trend very strong"
        elif fib_pct < 38.2:
            fib_label = "normal pullback to 23.6-38.2% — healthy correction"
        elif fib_pct < 50.0:
            fib_label = "deeper pullback near 38.2-50% — good long opportunity"
        elif fib_pct < 61.8:
            fib_label = "at 50-61.8% pullback — key decision zone"
        else:
            fib_label = "beyond 61.8% pullback — trend may be weakening"

    # ── Higher-low / major support structure ─────────────────────────────────
    # Check if price has formed a higher low vs the 20-week absolute low
    # Use lowest daily close in the last 15 trading days as the "recent swing low"
    higher_low_formed  = False
    higher_low_note    = ""
    near_major_support = False
    major_support_note = ""

    if len(d_closes) >= 15 and lt_low is not None:
        recent_swing_low = min(d_closes[-15:])
        hl_buffer = 0.0030  # 30 pips — must be meaningfully above the absolute low
        higher_low_formed = recent_swing_low > (lt_low + hl_buffer)

        dist_from_abs_low_pips = round((current_price - lt_low) * 10000)
        near_major_support = dist_from_abs_low_pips < 200  # within 200 pips of absolute low

        if higher_low_formed and lt_trend == "DOWNTREND":
            hl_gap = round((recent_swing_low - lt_low) * 10000)
            higher_low_note = (
                f"A higher low has formed — the recent swing low ({round(recent_swing_low, 4)}) "
                f"is {hl_gap} pips above the {round(lt_low, 4)} absolute low. "
                f"Price is respecting structure. If this holds, the bounce may be more than counter-trend."
            )

        if near_major_support:
            major_support_note = (
                f"Price is within {dist_from_abs_low_pips} pips of the 20-week absolute low "
                f"({round(lt_low, 4)}). This is a MAJOR support zone — the lowest price in months. "
                f"Shorts here carry reversal risk. Wait for a break below {round(lt_low, 4)} "
                f"before committing to the downtrend resuming."
            )

    # ── Moving averages (50-day and 200-day) ──────────────────────────────────
    ma50  = round(sum(d_closes[-50:]) / 50, 4)  if len(d_closes) >= 50  else None
    ma200 = round(sum(d_closes[-200:]) / 200, 4) if len(d_closes) >= 200 else None

    price_vs_ma50  = "above" if ma50  and current_price > ma50  else "below"
    price_vs_ma200 = "above" if ma200 and current_price > ma200 else "below"

    # ── Daily swing pivot structure (150-bar lookback) ────────────────────────
    swings = _identify_swing_pivots(d_highs, d_lows, d_closes, lookback=150)

    # ── Classify the overall market context ───────────────────────────────────
    context, structure_bias, context_note = _classify_context(
        lt_trend, st_trend, daily_trend,
        trend_age_weeks, dist_from_lt_high, dist_from_lt_low,
        current_price, ma50, ma200
    )

    # ── Key structure levels ───────────────────────────────────────────────────
    recent_w_high = max(w_highs[-4:]) if len(w_highs) >= 4 else wk_high_10
    recent_w_low  = min(w_lows[-4:])  if len(w_lows)  >= 4 else wk_low_10

    key_levels = {
        "recent_weekly_high": round(recent_w_high, 4),
        "recent_weekly_low":  round(recent_w_low,  4),
        "20wk_high":          round(lt_high, 4),
        "20wk_low":           round(lt_low,  4),
    }

    # ── Plain-English summaries ───────────────────────────────────────────────
    weekly_summary = _build_summary(
        st_trend, st_pct, lt_trend, lt_pct, trend_age_weeks, context
    )
    daily_summary = _build_daily_summary(daily_trend, daily_pct)

    return {
        "current_price":      round(current_price, 4),
        "weekly_trend":       st_trend,          # short-term (4wk) for backward compat
        "daily_trend":        daily_trend,
        "lt_trend":           lt_trend,           # long-term (20wk)
        "st_trend":           st_trend,           # short-term (4wk)
        "lt_pct":             round(lt_pct, 2),
        "st_pct":             round(st_pct, 2),
        "trend_age_weeks":    trend_age_weeks,
        "context":            context,
        "context_note":       context_note,
        "structure_bias":     structure_bias,
        "weekly_high":        round(wk_high_10, 4),
        "weekly_low":         round(wk_low_10, 4),
        "lt_high":            round(lt_high, 4),
        "lt_low":             round(lt_low, 4),
        "dist_from_lt_high":  dist_from_lt_high,
        "dist_from_lt_low":   dist_from_lt_low,
        "range_position":     range_pct,
        "range_label":        range_label,
        "ma50":               ma50,
        "ma200":              ma200,
        "price_vs_ma50":      price_vs_ma50,
        "price_vs_ma200":     price_vs_ma200,
        "higher_low_formed":  higher_low_formed,
        "higher_low_note":    higher_low_note,
        "near_major_support": near_major_support,
        "major_support_note": major_support_note,
        "key_levels":                  key_levels,
        "weekly_summary":              weekly_summary,
        "daily_summary":               daily_summary,
        "fib_pct":                     fib_pct,
        "fib_label":                   fib_label,
        "fib_levels":                  fib_levels,
        "daily_swing_highs":           swings["swing_highs"],
        "daily_swing_lows":            swings["swing_lows"],
        "nearest_daily_swing_high":    swings["nearest_swing_high"],
        "nearest_daily_swing_low":     swings["nearest_swing_low"],
        "dist_to_swing_high_pips":     swings["dist_to_swing_high_pips"],
        "dist_to_swing_low_pips":      swings["dist_to_swing_low_pips"],
        "daily_structure_type":        swings["structure_type"],
        "daily_structure_note":        swings["structure_note"],
        "error":              None,
    }


def _trend_direction(closes: List[float], lookback: int) -> Tuple[str, float]:
    """Compare recent average to past average. Returns (trend, pct_change)."""
    if len(closes) < lookback + 3:
        return "RANGING", 0.0
    recent_avg = sum(closes[-3:]) / 3
    past_avg   = sum(closes[-(lookback + 3):-(lookback)]) / 3
    if past_avg == 0:
        return "RANGING", 0.0
    pct = (recent_avg - past_avg) / past_avg * 100
    if pct > 0.5:
        return "UPTREND", pct
    elif pct < -0.5:
        return "DOWNTREND", pct
    return "RANGING", pct


def _count_trend_age(closes: List[float], current_trend: str) -> int:
    """
    Count how many consecutive bars the current trend direction has held.
    Walk backwards from the most recent close.
    """
    if len(closes) < 4 or current_trend == "RANGING":
        return 0

    count = 0
    for i in range(len(closes) - 1, 0, -1):
        move = closes[i] - closes[i - 1]
        if current_trend == "UPTREND" and move >= 0:
            count += 1
        elif current_trend == "DOWNTREND" and move <= 0:
            count += 1
        else:
            break
    return count


def _classify_context(
    lt_trend: str, st_trend: str, daily_trend: str,
    age_weeks: int, dist_high: float, dist_low: float,
    price: float, ma50: Optional[float], ma200: Optional[float]
) -> Tuple[str, str, str]:
    """
    Classify the overall market context based on multi-timeframe analysis.

    Returns (context_label, structure_bias, plain_english_note)

    Context labels:
      ESTABLISHED_UPTREND       : long AND short term both up
      ESTABLISHED_DOWNTREND     : long AND short term both down
      PULLBACK_IN_UPTREND       : long-term up, short-term pulling back
      COUNTER_TREND_BOUNCE      : long-term down, short-term bouncing up
      COUNTER_TREND_DROP        : long-term up, short-term dropping sharply
      RANGING                   : no clear direction either timeframe
    """
    if lt_trend == "UPTREND" and st_trend == "UPTREND":
        context = "ESTABLISHED_UPTREND"
        bias = "BULLISH"
        note = (
            f"Both the 5-month trend and the 1-month trend point UP. "
            f"This is the strongest environment for long trades. "
            f"Look for pullbacks to key support levels to enter long."
        )

    elif lt_trend == "DOWNTREND" and st_trend == "DOWNTREND":
        context = "ESTABLISHED_DOWNTREND"
        bias = "BEARISH"
        note = (
            f"Both the 5-month trend and the 1-month trend point DOWN. "
            f"This is the strongest environment for short trades. "
            f"Look for rallies to key resistance levels to enter short."
        )

    elif lt_trend == "DOWNTREND" and st_trend == "UPTREND":
        context = "COUNTER_TREND_BOUNCE"
        bias = "BEARISH"  # dominant trend is down
        note = (
            f"COUNTER-TREND BOUNCE — the 5-month trend is DOWN "
            f"but price has bounced UP over the last 4 weeks "
            f"(bounce is {age_weeks} weeks old). "
            f"This bounce is moving AGAINST the dominant trend. "
            f"Buying here means trading against the bigger picture. "
            f"The dominant trend ({lt_trend}) typically reasserts itself. "
            f"Wait for the bounce to exhaust before considering shorts aligned with the main trend."
        )

    elif lt_trend == "UPTREND" and st_trend == "DOWNTREND":
        context = "PULLBACK_IN_UPTREND"
        bias = "BULLISH"  # dominant trend is up
        note = (
            f"PULLBACK IN UPTREND — the 5-month trend is UP "
            f"but price has pulled back over the last 4 weeks. "
            f"This is typically a buying opportunity, not a reversal. "
            f"Wait for the pullback to show signs of exhaustion, "
            f"then look for long entries at key support levels."
        )

    elif lt_trend == "UPTREND" and st_trend == "RANGING":
        context = "PULLBACK_IN_UPTREND"
        bias = "BULLISH"
        note = (
            f"The 5-month trend is UP but short-term momentum has stalled. "
            f"Price is consolidating — this is typically a pause before the "
            f"uptrend continues. Watch for a breakout higher."
        )

    elif lt_trend == "DOWNTREND" and st_trend == "RANGING":
        context = "ESTABLISHED_DOWNTREND"
        bias = "BEARISH"
        note = (
            f"The 5-month trend is DOWN and short-term momentum has stalled. "
            f"Price is consolidating inside a downtrend — typically a pause "
            f"before selling resumes. Watch for a breakdown lower."
        )

    else:
        context = "RANGING"
        bias = "NEUTRAL"
        note = (
            f"No clear trend on either the 5-month or 1-month timeframe. "
            f"Market is ranging — trade only from the edges of the range, "
            f"not from the middle."
        )

    return context, bias, note


def _build_summary(
    st_trend: str, st_pct: float,
    lt_trend: str, lt_pct: float,
    age_weeks: int, context: str
) -> str:
    """Plain-English weekly structure summary."""

    lt_dir = "UP" if lt_trend == "UPTREND" else "DOWN" if lt_trend == "DOWNTREND" else "FLAT"
    st_dir = "UP" if st_trend == "UPTREND" else "DOWN" if st_trend == "DOWNTREND" else "FLAT"

    if context == "COUNTER_TREND_BOUNCE":
        return (
            f"GBP/AUD has bounced UP {abs(st_pct):.1f}% over the last 4 weeks "
            f"BUT the 5-month dominant trend is DOWN ({abs(lt_pct):.1f}%). "
            f"This is a COUNTER-TREND BOUNCE — "
            f"the bounce is {age_weeks} weeks old. "
            f"Treat with caution: buying here means going against the dominant trend."
        )
    elif context == "PULLBACK_IN_UPTREND":
        return (
            f"GBP/AUD is pulling back ({st_pct:.1f}% over 4 weeks) "
            f"within a larger 5-month UPTREND (+{lt_pct:.1f}%). "
            f"This is a healthy pullback — the dominant trend is still UP. "
            f"Look for support levels to enter long."
        )
    elif context == "ESTABLISHED_UPTREND":
        return (
            f"GBP/AUD is in an UPTREND on both the 5-month (+{lt_pct:.1f}%) "
            f"and 4-week (+{st_pct:.1f}%) timeframes. "
            f"This is the best environment for long trades. "
            f"Look for pullbacks to key levels to buy."
        )
    elif context == "ESTABLISHED_DOWNTREND":
        return (
            f"GBP/AUD is in a DOWNTREND on both the 5-month ({lt_pct:.1f}%) "
            f"and 4-week ({st_pct:.1f}%) timeframes. "
            f"This is the best environment for short trades. "
            f"Look for rallies to key levels to sell."
        )
    else:
        return (
            f"GBP/AUD is ranging — no clear trend. "
            f"5-month: {lt_dir} ({lt_pct:.1f}%), 4-week: {st_dir} ({st_pct:.1f}%)."
        )


def _build_daily_summary(daily_trend: str, daily_pct: float) -> str:
    if daily_trend == "UPTREND":
        return (
            f"Daily chart is pointing UP ({daily_pct:+.2f}% over 10 days). "
            f"Short-term momentum is bullish."
        )
    elif daily_trend == "DOWNTREND":
        return (
            f"Daily chart is pointing DOWN ({daily_pct:+.2f}% over 10 days). "
            f"Short-term momentum is bearish."
        )
    else:
        return (
            f"Daily chart has no clear direction ({daily_pct:+.2f}% over 10 days). "
            f"Price is chopping sideways on the daily."
        )


def _identify_swing_pivots(
    d_highs:  List[float],
    d_lows:   List[float],
    d_closes: List[float],
    lookback: int = 150,
    confirm:  int = 3,
) -> Dict:
    """
    Identify significant daily swing highs and lows using a pivot confirmation
    window. A swing high is a bar whose high is greater than the `confirm`
    bars on each side. A swing low is the mirror.

    Returns the last 5 pivots of each type (most recent first), the nearest
    one above and below current price, and the HH/HL or LH/LL structure label.
    """
    n      = min(lookback, len(d_highs), len(d_lows))
    highs  = d_highs[-n:]
    lows   = d_lows[-n:]
    closes = d_closes[-n:]

    if len(highs) < confirm * 2 + 1:
        return {
            "swing_highs": [], "swing_lows": [],
            "nearest_swing_high": None, "nearest_swing_low": None,
            "dist_to_swing_high_pips": None, "dist_to_swing_low_pips": None,
            "structure_type": "UNKNOWN", "structure_note": "Insufficient data",
        }

    pivot_highs: List[float] = []
    pivot_lows:  List[float] = []

    for i in range(confirm, len(highs) - confirm):
        window_h = highs[i - confirm: i] + highs[i + 1: i + confirm + 1]
        if all(highs[i] > h for h in window_h):
            pivot_highs.append(round(highs[i], 4))

        window_l = lows[i - confirm: i] + lows[i + 1: i + confirm + 1]
        if all(lows[i] < l for l in window_l):
            pivot_lows.append(round(lows[i], 4))

    # Keep last 5 of each (most recent = last in list)
    pivot_highs = pivot_highs[-5:]
    pivot_lows  = pivot_lows[-5:]

    current = closes[-1]

    # Nearest swing high above current price
    above = [p for p in pivot_highs if p > current]
    nearest_high = min(above) if above else (max(pivot_highs) if pivot_highs else None)

    # Nearest swing low below current price
    below = [p for p in pivot_lows if p < current]
    nearest_low = max(below) if below else (min(pivot_lows) if pivot_lows else None)

    dist_high_pips = round((nearest_high - current) * 10000) if nearest_high else None
    dist_low_pips  = round((current - nearest_low)  * 10000) if nearest_low  else None

    # Classify HH/HL or LH/LL using the last two pivot highs and lows
    structure_type = "TRANSITIONAL"
    structure_note = "Mixed swing structure — no clear HH/HL or LH/LL pattern"

    if len(pivot_highs) >= 2 and len(pivot_lows) >= 2:
        hh = pivot_highs[-1] > pivot_highs[-2]  # most recent high > prior high
        hl = pivot_lows[-1]  > pivot_lows[-2]   # most recent low > prior low
        lh = pivot_highs[-1] < pivot_highs[-2]
        ll = pivot_lows[-1]  < pivot_lows[-2]

        if hh and hl:
            structure_type = "HH_HL"
            structure_note = (
                f"Daily structure: Higher High ({pivot_highs[-1]}) + Higher Low ({pivot_lows[-1]}) — "
                f"bullish market structure confirmed"
            )
        elif lh and ll:
            structure_type = "LH_LL"
            structure_note = (
                f"Daily structure: Lower High ({pivot_highs[-1]}) + Lower Low ({pivot_lows[-1]}) — "
                f"bearish market structure confirmed"
            )
        elif hh and ll:
            structure_type = "TRANSITIONAL"
            structure_note = (
                f"Daily structure: Higher High but Lower Low — "
                f"expanding range, no clear directional bias"
            )
        elif lh and hl:
            structure_type = "TRANSITIONAL"
            structure_note = (
                f"Daily structure: Lower High but Higher Low — "
                f"contracting range, potential breakout pending"
            )

    return {
        "swing_highs":           pivot_highs,
        "swing_lows":            pivot_lows,
        "nearest_swing_high":    nearest_high,
        "nearest_swing_low":     nearest_low,
        "dist_to_swing_high_pips": dist_high_pips,
        "dist_to_swing_low_pips":  dist_low_pips,
        "structure_type":        structure_type,
        "structure_note":        structure_note,
    }


def _error_result(msg: str) -> Dict:
    return {
        "current_price":            None,
        "weekly_trend":             "UNKNOWN",
        "daily_trend":              "UNKNOWN",
        "lt_trend":                 "UNKNOWN",
        "st_trend":                 "UNKNOWN",
        "lt_pct":                   0.0,
        "st_pct":                   0.0,
        "trend_age_weeks":          0,
        "context":                  "UNKNOWN",
        "context_note":             msg,
        "structure_bias":           "NEUTRAL",
        "weekly_high":              None,
        "weekly_low":               None,
        "lt_high":                  None,
        "lt_low":                   None,
        "dist_from_lt_high":        None,
        "dist_from_lt_low":         None,
        "range_position":           None,
        "range_label":              "unavailable",
        "ma50":                     None,
        "ma200":                    None,
        "price_vs_ma50":            "unknown",
        "price_vs_ma200":           "unknown",
        "key_levels":               {},
        "weekly_summary":           msg,
        "daily_summary":            msg,
        "fib_pct":                  0.0,
        "fib_label":                "unavailable",
        "fib_levels":               {},
        "daily_swing_highs":        [],
        "daily_swing_lows":         [],
        "nearest_daily_swing_high": None,
        "nearest_daily_swing_low":  None,
        "dist_to_swing_high_pips":  None,
        "dist_to_swing_low_pips":   None,
        "daily_structure_type":     "UNKNOWN",
        "daily_structure_note":     msg,
        "error":                    msg,
    }


if __name__ == "__main__":
    data = get_htf_structure()
    if data["error"]:
        print(f"Error: {data['error']}")
    else:
        print(f"Context        : {data['context']}")
        print(f"5-month trend  : {data['lt_trend']} ({data['lt_pct']:+.2f}%)")
        print(f"4-week trend   : {data['st_trend']} ({data['st_pct']:+.2f}%)")
        print(f"Daily trend    : {data['daily_trend']}")
        print(f"Trend age      : {data['trend_age_weeks']} weeks")
        print(f"MA50           : {data['ma50']}  (price is {data['price_vs_ma50']})")
        print(f"MA200          : {data['ma200']}  (price is {data['price_vs_ma200']})")
        print(f"\n{data['context_note']}")
        print(f"\nWeekly: {data['weekly_summary']}")
