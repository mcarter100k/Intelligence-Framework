"""
intraday_context.py

Intraday session structure and fakeout detection for GBP/AUD.

THE EDGE THIS PROVIDES:
  Most retail traders see the Asian range break and trade it as a breakout.
  Institutional traders know the break is often engineered — it's a stop hunt.
  Smart money sweeps the liquidity sitting at the Asian range extreme,
  fills their own orders in the opposite direction, then moves price.

  This module identifies when that sweep-and-reversal has happened so you
  can trade WITH institutional flow, not against it.

SETUP TYPES:
  BULLISH FAKEOUT   — London swept below Asian low then closed back inside.
                      Longs below the low got stopped out. Smart money is long.
                      Trade: buy the reversal, stop just below the swept low.

  BEARISH FAKEOUT   — London swept above Asian high then closed back inside.
                      Shorts above the high got stopped out. Smart money is short.
                      Trade: sell the reversal, stop just above the swept high.

  CLEAN BREAK UP    — Price broke above Asian high AND is holding there.
                      No reversal — genuine breakout. Trade the continuation.

  CLEAN BREAK DOWN  — Price broke below Asian low AND is holding there.
                      No reversal — genuine breakdown. Trade the continuation.

  INSIDE RANGE      — Price still inside Asian range.
                      Wait. No signal yet.

Data: 1H bars from OANDA via get_hourly_bars().
"""

from __future__ import annotations
from datetime import datetime, timezone, timedelta, time as dtime
from typing import Dict, List, Optional, Tuple

from oanda_feed import get_hourly_bars, is_configured

import pandas as pd

# Asian "range-setting" window in UTC
# GBP/AUD: Sydney + Tokyo combined = 22:00 UTC (prev day) to 07:00 UTC
_ASIAN_START_HOUR = 22   # 22:00 UTC previous day
_ASIAN_END_HOUR   = 7    # 07:00 UTC = London open

# London "reaction" window: first 3 hours after open
_LONDON_OPEN_HOUR  = 7
_LONDON_WATCH_HOUR = 11  # 07:00-11:00 UTC is the Asian fakeout window

# London "range-setting" window: 07:00–10:00 UTC
# NY sweeps this range in the first 3 hours after NY open
_LONDON_RANGE_END  = 10  # London range is defined by 10:00 UTC
_NY_OPEN_HOUR      = 13  # New York opens 13:00 UTC
_NY_WATCH_HOUR     = 16  # NY fakeout window: 13:00–16:00 UTC


def get_intraday_context() -> Dict:
    """
    Fetch 1H bars, build Asian range, detect fakeout, return setup dict.
    Fails silently — never breaks the main report.
    """
    if not is_configured():
        return _unavailable("OANDA not configured")

    try:
        df = get_hourly_bars(count=96)  # 4 days of 1H bars
    except Exception as e:
        return _unavailable(str(e))

    if df is None or df.empty:
        return _unavailable("No 1H bar data returned")

    now_utc = datetime.now(timezone.utc)

    asian_high, asian_low, asian_bars_used = _get_asian_range(df, now_utc)
    fakeout     = _detect_fakeout(df, now_utc, asian_high, asian_low)
    position    = _price_position(df, asian_high, asian_low)
    optimal_win = _optimal_window(now_utc)
    bias        = _derive_intraday_bias(fakeout, position)
    entry_note  = _build_entry_note(fakeout, position, asian_high, asian_low, bias)
    warning     = _build_warning(now_utc, fakeout)

    # London range fakeout — NY sweeps the London range and reverses
    london_high, london_low, london_bars_used = _get_london_range(df, now_utc)
    london_fakeout = _detect_london_fakeout(df, now_utc, london_high, london_low)

    return {
        # ── Asian session fakeout ──────────────────────────────────────────────
        "asian_high":       asian_high,
        "asian_low":        asian_low,
        "asian_range_pips": round((asian_high - asian_low) * 10000) if asian_high and asian_low else None,
        "asian_bars_used":  asian_bars_used,
        "fakeout_detected": fakeout["detected"],
        "fakeout_type":     fakeout["type"],       # BULLISH / BEARISH / BREAK_UP / BREAK_DOWN / INSIDE / NONE
        "fakeout_note":     fakeout["note"],
        # ── Price position and bias ────────────────────────────────────────────
        "price_position":   position["label"],     # ABOVE_RANGE / INSIDE_RANGE / BELOW_RANGE
        "current_price":    position["price"],
        "pips_from_high":   position["pips_from_high"],
        "pips_from_low":    position["pips_from_low"],
        "intraday_bias":    bias,                  # LONG / SHORT / NEUTRAL / WAIT
        "entry_note":       entry_note,
        "optimal_window":   optimal_win,
        "warning":          warning,
        # ── London range fakeout (NY sweeps London range) ─────────────────────
        "london_high":              london_high,
        "london_low":               london_low,
        "london_range_pips":        round((london_high - london_low) * 10000) if london_high and london_low else None,
        "london_bars_used":         london_bars_used,
        "london_fakeout_detected":  london_fakeout["detected"],
        "london_fakeout_type":      london_fakeout["type"],
        "london_fakeout_note":      london_fakeout["note"],
        "error":            None,
    }


# ── Asian range ───────────────────────────────────────────────────────────────

def _get_asian_range(
    df: pd.DataFrame, now_utc: datetime
) -> Tuple[Optional[float], Optional[float], int]:
    """
    Get the most recently completed Asian session range.
    Asian session = 22:00 UTC (prev day) → 07:00 UTC.

    If we're currently in the Asian session (before 07:00 UTC today),
    we use the previous completed session.
    """
    today = now_utc.date()

    if now_utc.hour < _ASIAN_END_HOUR:
        # We're still in the Asian session — use yesterday's completed range
        asian_start = datetime.combine(today - timedelta(days=2),
                                       dtime(_ASIAN_START_HOUR, 0),
                                       tzinfo=timezone.utc)
        asian_end   = datetime.combine(today - timedelta(days=1),
                                       dtime(_ASIAN_END_HOUR, 0),
                                       tzinfo=timezone.utc)
    else:
        # London/NY/Off-hours — today's Asian session completed
        asian_start = datetime.combine(today - timedelta(days=1),
                                       dtime(_ASIAN_START_HOUR, 0),
                                       tzinfo=timezone.utc)
        asian_end   = datetime.combine(today,
                                       dtime(_ASIAN_END_HOUR, 0),
                                       tzinfo=timezone.utc)

    bars = df[(df.index >= asian_start) & (df.index < asian_end)]

    if bars.empty:
        return None, None, 0

    return (
        round(float(bars["High"].max()), 5),
        round(float(bars["Low"].min()),  5),
        len(bars),
    )


# ── Fakeout detection ─────────────────────────────────────────────────────────

def _detect_fakeout(
    df: pd.DataFrame,
    now_utc: datetime,
    asian_high: Optional[float],
    asian_low:  Optional[float],
) -> Dict:
    """
    Scan the London open window for sweep-and-reversal patterns.

    The fakeout is confirmed when:
      - Price WICK went through the Asian extreme (the sweep)
      - Price CLOSE came back inside the range (the reversal)
    This is the exact moment stop orders were triggered AND the move failed.
    """
    if asian_high is None or asian_low is None:
        return {"detected": False, "type": "NONE", "note": "Asian range not available"}

    today = now_utc.date()

    # London open bars: 07:00–11:00 UTC today
    london_start = datetime.combine(today, dtime(_LONDON_OPEN_HOUR, 0), tzinfo=timezone.utc)
    london_end   = datetime.combine(today, dtime(_LONDON_WATCH_HOUR, 0), tzinfo=timezone.utc)
    cutoff       = min(now_utc, london_end)

    london_bars = df[(df.index >= london_start) & (df.index <= cutoff)]

    if london_bars.empty:
        return {"detected": False, "type": "INSIDE", "note": "London has not opened yet — Asian range intact"}

    last_close   = float(london_bars.iloc[-1]["Close"])
    session_low  = float(london_bars["Low"].min())
    session_high = float(london_bars["High"].max())

    swept_low  = session_low  < asian_low
    swept_high = session_high > asian_high

    # Bullish fakeout: wick below Asian low, close back inside
    if swept_low and last_close > asian_low:
        sweep_depth = round((asian_low - session_low) * 10000)
        return {
            "detected": True,
            "type":     "BULLISH",
            "note": (
                f"BULLISH FAKEOUT — London swept {sweep_depth} pips below Asian low "
                f"({asian_low:.4f}) then closed back inside. Stop hunt confirmed. "
                f"Smart money filled longs below {asian_low:.4f}. Real move is UP."
            ),
        }

    # Bearish fakeout: wick above Asian high, close back inside
    if swept_high and last_close < asian_high:
        sweep_height = round((session_high - asian_high) * 10000)
        return {
            "detected": True,
            "type":     "BEARISH",
            "note": (
                f"BEARISH FAKEOUT — London swept {sweep_height} pips above Asian high "
                f"({asian_high:.4f}) then closed back inside. Stop hunt confirmed. "
                f"Smart money filled shorts above {asian_high:.4f}. Real move is DOWN."
            ),
        }

    # Clean break up (no reversal yet)
    if last_close > asian_high:
        pips_above = round((last_close - asian_high) * 10000)
        return {
            "detected": False,
            "type":     "BREAK_UP",
            "note": (
                f"London broke above Asian high ({asian_high:.4f}) and is holding "
                f"{pips_above} pips above it. Genuine breakout — watch for continuation long."
            ),
        }

    # Clean break down (no reversal yet)
    if last_close < asian_low:
        pips_below = round((asian_low - last_close) * 10000)
        return {
            "detected": False,
            "type":     "BREAK_DOWN",
            "note": (
                f"London broke below Asian low ({asian_low:.4f}) and is holding "
                f"{pips_below} pips below it. Genuine breakdown — watch for continuation short."
            ),
        }

    # Both sweeps happened (rare, chaotic)
    if swept_low and swept_high:
        return {
            "detected": False,
            "type":     "BOTH_SWEPT",
            "note": (
                f"London swept BOTH extremes ({asian_low:.4f} and {asian_high:.4f}) — "
                f"highly volatile, no clean directional signal. Avoid."
            ),
        }

    # Inside range
    return {
        "detected": False,
        "type":     "INSIDE",
        "note":     f"Price inside Asian range ({asian_low:.4f}–{asian_high:.4f}). Wait for breakout or fakeout signal.",
    }


# ── Position and bias ─────────────────────────────────────────────────────────

def _price_position(df: pd.DataFrame, asian_high: Optional[float], asian_low: Optional[float]) -> Dict:
    if df.empty:
        return {"label": "UNKNOWN", "price": None, "pips_from_high": None, "pips_from_low": None}

    price = round(float(df.iloc[-1]["Close"]), 5)

    if asian_high is None or asian_low is None:
        return {"label": "UNKNOWN", "price": price, "pips_from_high": None, "pips_from_low": None}

    pips_from_high = round((price - asian_high) * 10000)
    pips_from_low  = round((price - asian_low)  * 10000)

    if price > asian_high:
        label = "ABOVE_RANGE"
    elif price < asian_low:
        label = "BELOW_RANGE"
    else:
        label = "INSIDE_RANGE"

    return {
        "label":          label,
        "price":          price,
        "pips_from_high": pips_from_high,
        "pips_from_low":  pips_from_low,
    }


def _derive_intraday_bias(fakeout: Dict, position: Dict) -> str:
    ft = fakeout.get("type", "NONE")
    if ft == "BULLISH":    return "LONG"
    if ft == "BEARISH":    return "SHORT"
    if ft == "BREAK_UP":   return "LONG"
    if ft == "BREAK_DOWN": return "SHORT"
    if ft == "BOTH_SWEPT": return "NEUTRAL"
    return "WAIT"


def _build_entry_note(
    fakeout: Dict,
    position: Dict,
    asian_high: Optional[float],
    asian_low:  Optional[float],
    bias:       str,
) -> str:
    ft    = fakeout.get("type", "NONE")
    price = position.get("price")

    if ft == "BULLISH" and asian_low:
        return (
            f"Price is above swept low ({asian_low:.4f}). Wait for pullback to "
            f"{asian_low:.4f}–{asian_low + 0.0010:.4f} zone. Bullish rejection candle + "
            f"close above swept low = entry. Stop: 5–10 pips below session low."
        )
    if ft == "BEARISH" and asian_high:
        return (
            f"Price is below swept high ({asian_high:.4f}). Wait for pullback to "
            f"{asian_high - 0.0010:.4f}–{asian_high:.4f} zone. Bearish rejection candle + "
            f"close below swept high = entry. Stop: 5–10 pips above session high."
        )
    if ft == "BREAK_UP" and asian_high:
        return (
            f"Clean break above {asian_high:.4f}. If price pulls back and holds above "
            f"{asian_high:.4f}, that retest is your entry. Stop: back inside range."
        )
    if ft == "BREAK_DOWN" and asian_low:
        return (
            f"Clean break below {asian_low:.4f}. If price pulls back and holds below "
            f"{asian_low:.4f}, that retest is your entry. Stop: back inside range."
        )
    if ft == "INSIDE" and asian_high and asian_low:
        return (
            f"Still inside range ({asian_low:.4f}–{asian_high:.4f}). No entry yet. "
            f"Watch the extremes — first 1H candle to sweep and reverse a level is the signal."
        )
    return "No intraday setup active. Wait for Asian range interaction."


def _optimal_window(now_utc: datetime) -> str:
    hour = now_utc.hour
    if 7 <= hour < 12:
        return "NOW — London open (07:00–12:00 UTC). Prime fakeout window."
    if 12 <= hour < 16:
        return "London/NY overlap (12:00–16:00 UTC). High-momentum continuation window."
    if 16 <= hour < 21:
        return "NY session (16:00–21:00 UTC). USD-driven moves, watch US data."
    if hour >= 21 or hour < 2:
        return "Sydney/Off-hours. Low volume. Wait for Tokyo range formation."
    return "Tokyo session (00:00–07:00 UTC). Asian range being set. Watch, don't trade."


def _build_warning(now_utc: datetime, fakeout: Dict) -> str:
    warnings = []
    weekday = now_utc.weekday()
    hour    = now_utc.hour

    if weekday == 4 and hour >= 12:
        warnings.append("Friday after 12:00 UTC — avoid new intraday positions, profit-taking in progress")
    if weekday == 0 and hour < 10:
        warnings.append("Monday morning — gap fill behaviour common, wait for London to confirm direction")
    if fakeout.get("type") == "BOTH_SWEPT":
        warnings.append("Both Asian range extremes were swept — highly choppy, stay flat")

    return " | ".join(warnings)


# ── London range fakeout ──────────────────────────────────────────────────────
# London builds its range in the first 3 hours (07:00–10:00 UTC).
# New York opens at 13:00 UTC and frequently sweeps that range before reversing.
# This is the same stop-hunt mechanism as the Asian fakeout — different session.

def _get_london_range(
    df: pd.DataFrame, now_utc: datetime
) -> Tuple[Optional[float], Optional[float], int]:
    """
    Get the London session range (07:00–10:00 UTC today).
    Returns (high, low, bars_used). Returns (None, None, 0) if London hasn't
    completed its range window yet or data is unavailable.
    """
    today = now_utc.date()

    # Only meaningful if we're in or past the NY session (13:00+ UTC)
    if now_utc.hour < _NY_OPEN_HOUR:
        return None, None, 0

    london_start = datetime.combine(today, dtime(_LONDON_OPEN_HOUR, 0), tzinfo=timezone.utc)
    london_end   = datetime.combine(today, dtime(_LONDON_RANGE_END, 0), tzinfo=timezone.utc)

    bars = df[(df.index >= london_start) & (df.index < london_end)]

    if bars.empty:
        return None, None, 0

    return (
        round(float(bars["High"].max()), 5),
        round(float(bars["Low"].min()),  5),
        len(bars),
    )


def _detect_london_fakeout(
    df: pd.DataFrame,
    now_utc: datetime,
    london_high: Optional[float],
    london_low:  Optional[float],
) -> Dict:
    """
    Scan the NY open window (13:00–16:00 UTC) for a sweep-and-reversal of
    the London range. Same logic as the Asian fakeout detector.

    Bullish London fakeout: NY wick broke below London low, close back inside.
    Bearish London fakeout: NY wick broke above London high, close back inside.
    """
    if london_high is None or london_low is None:
        return {
            "detected": False,
            "type":     "NONE",
            "note":     "London range not available — must be past 13:00 UTC",
        }

    today = now_utc.date()

    if now_utc.hour < _NY_OPEN_HOUR:
        return {
            "detected": False,
            "type":     "WAITING",
            "note":     f"NY session opens at {_NY_OPEN_HOUR:02d}:00 UTC — London range is set, watching for NY sweep",
        }

    ny_start = datetime.combine(today, dtime(_NY_OPEN_HOUR, 0), tzinfo=timezone.utc)
    ny_end   = datetime.combine(today, dtime(_NY_WATCH_HOUR, 0), tzinfo=timezone.utc)
    cutoff   = min(now_utc, ny_end)

    ny_bars = df[(df.index >= ny_start) & (df.index <= cutoff)]

    if ny_bars.empty:
        return {
            "detected": False,
            "type":     "INSIDE",
            "note":     "NY session bars not yet available",
        }

    last_close   = float(ny_bars.iloc[-1]["Close"])
    session_low  = float(ny_bars["Low"].min())
    session_high = float(ny_bars["High"].max())

    swept_low  = session_low  < london_low
    swept_high = session_high > london_high

    if swept_low and swept_high:
        return {
            "detected": False,
            "type":     "BOTH_SWEPT",
            "note": (
                f"NY swept BOTH London extremes ({london_low:.4f} and {london_high:.4f}) — "
                f"choppy, no clean directional signal. Avoid."
            ),
        }

    if swept_low and last_close > london_low:
        depth = round((london_low - session_low) * 10000)
        return {
            "detected": True,
            "type":     "BULLISH",
            "note": (
                f"LONDON FAKEOUT (BULLISH) — NY swept {depth} pips below London low "
                f"({london_low:.4f}) then closed back inside. Stop hunt confirmed. "
                f"Smart money filled longs below {london_low:.4f}. Real move is UP."
            ),
        }

    if swept_high and last_close < london_high:
        height = round((session_high - london_high) * 10000)
        return {
            "detected": True,
            "type":     "BEARISH",
            "note": (
                f"LONDON FAKEOUT (BEARISH) — NY swept {height} pips above London high "
                f"({london_high:.4f}) then closed back inside. Stop hunt confirmed. "
                f"Smart money filled shorts above {london_high:.4f}. Real move is DOWN."
            ),
        }

    if last_close > london_high:
        pips_above = round((last_close - london_high) * 10000)
        return {
            "detected": False,
            "type":     "BREAK_UP",
            "note": (
                f"NY broke above London high ({london_high:.4f}) and is holding "
                f"{pips_above} pips above. Genuine continuation — watch for long entries."
            ),
        }

    if last_close < london_low:
        pips_below = round((london_low - last_close) * 10000)
        return {
            "detected": False,
            "type":     "BREAK_DOWN",
            "note": (
                f"NY broke below London low ({london_low:.4f}) and is holding "
                f"{pips_below} pips below. Genuine continuation — watch for short entries."
            ),
        }

    return {
        "detected": False,
        "type":     "INSIDE",
        "note":     f"NY still inside London range ({london_low:.4f}–{london_high:.4f}). No sweep yet.",
    }


def _unavailable(reason: str) -> Dict:
    return {
        "asian_high": None, "asian_low": None, "asian_range_pips": None,
        "asian_bars_used": 0,
        "fakeout_detected": False, "fakeout_type": "NONE", "fakeout_note": "",
        "price_position": "UNKNOWN", "current_price": None,
        "pips_from_high": None, "pips_from_low": None,
        "intraday_bias": "WAIT", "entry_note": "No intraday data available.",
        "optimal_window": "", "warning": "",
        "london_high": None, "london_low": None, "london_range_pips": None,
        "london_bars_used": 0,
        "london_fakeout_detected": False, "london_fakeout_type": "NONE",
        "london_fakeout_note": "",
        "error": reason,
    }
