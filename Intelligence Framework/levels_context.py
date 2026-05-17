"""
levels_context.py
─────────────────
Computes all key GBP/AUD price levels from OANDA data.
Used by market_brain to store levels in last_run.json,
and by entry_watcher to find valid entry zones and targets.

Levels returned:
  prev_day_high / prev_day_low   — yesterday's high and low (strongest daily levels)
  weekly_high  / weekly_low      — current week's extremes (key swing targets)
  session_high / session_low     — current session's high and low so far
  asian_high   / asian_low       — Asian range (already in intraday_context, mirrored here)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from oanda_feed import get_daily_bars, get_weekly_bars, get_hourly_bars


# ── Session windows (UTC) ─────────────────────────────────────────────────────
# These are the hours each session is active — used to isolate session OHLC

_SESSIONS = {
    "Asian":  (0,  9),   # 00:00 – 09:00 UTC  (Tokyo/Sydney)
    "London": (7,  16),  # 07:00 – 16:00 UTC
    "NY":     (13, 22),  # 13:00 – 22:00 UTC
}


def _current_session(hour_utc: int) -> str:
    if 7 <= hour_utc < 16:
        return "London"
    if 13 <= hour_utc < 22:
        return "NY"
    return "Asian"


def get_key_levels(pair: str = "GBPAUD") -> dict:
    """
    Return all key price levels. Any level that cannot be fetched is None.
    Always returns the dict — never raises.
    """
    result = {
        "prev_day_high":  None,
        "prev_day_low":   None,
        "weekly_high":    None,
        "weekly_low":     None,
        "session_high":   None,
        "session_low":    None,
        "session_name":   None,
        "asian_high":     None,
        "asian_low":      None,
    }

    now_utc   = datetime.now(timezone.utc)
    hour_utc  = now_utc.hour

    # ── Previous day high / low ───────────────────────────────────────────────
    try:
        daily = get_daily_bars(pair, count=3)
        if daily is not None and len(daily) >= 2:
            # Last completed day (index -2 because -1 may be today's incomplete bar,
            # but _get_bars already filters incomplete — so -1 is yesterday's full day)
            prev = daily.iloc[-1]
            result["prev_day_high"] = round(float(prev["High"]), 5)
            result["prev_day_low"]  = round(float(prev["Low"]),  5)
    except Exception:
        pass

    # ── Weekly high / low ─────────────────────────────────────────────────────
    try:
        weekly = get_weekly_bars(pair, count=2)
        if weekly is not None and len(weekly) >= 1:
            wk = weekly.iloc[-1]
            result["weekly_high"] = round(float(wk["High"]), 5)
            result["weekly_low"]  = round(float(wk["Low"]),  5)
    except Exception:
        pass

    # ── Session high / low ────────────────────────────────────────────────────
    try:
        session_name = _current_session(hour_utc)
        start_h, end_h = _SESSIONS[session_name]
        hourly = get_hourly_bars(pair, count=24)

        if hourly is not None:
            # Filter to candles within the current session window today
            today = now_utc.date()
            mask  = hourly.index.map(
                lambda dt: dt.date() == today and start_h <= dt.hour < end_h
            )
            session_bars = hourly[mask]

            if not session_bars.empty:
                result["session_high"] = round(float(session_bars["High"].max()), 5)
                result["session_low"]  = round(float(session_bars["Low"].min()),  5)
                result["session_name"] = session_name
    except Exception:
        pass

    # ── Asian high / low (from intraday_context) ──────────────────────────────
    try:
        from intraday_context import get_intraday_context
        intra = get_intraday_context()
        ah = intra.get("asian_high")
        al = intra.get("asian_low")
        if ah:
            result["asian_high"] = round(float(ah), 5)
        if al:
            result["asian_low"]  = round(float(al), 5)
    except Exception:
        pass

    return result


def levels_as_list(levels: dict) -> list[float]:
    """
    Flatten the levels dict into a sorted list of unique floats.
    Used by entry_watcher to check proximity to any key level.
    """
    vals = []
    for v in levels.values():
        if isinstance(v, (int, float)) and v > 0:
            vals.append(float(v))
    return sorted(set(round(v, 5) for v in vals))


def nearest_resistance(levels: dict, entry: float) -> Optional[float]:
    """Return the nearest key level ABOVE entry (target for LONG trades)."""
    candidates = [
        v for k, v in levels.items()
        if isinstance(v, float) and v > entry
        and k not in ("session_name",)
    ]
    return min(candidates) if candidates else None


def nearest_support(levels: dict, entry: float) -> Optional[float]:
    """Return the nearest key level BELOW entry (target for SHORT trades)."""
    candidates = [
        v for k, v in levels.items()
        if isinstance(v, float) and v < entry
        and k not in ("session_name",)
    ]
    return max(candidates) if candidates else None
