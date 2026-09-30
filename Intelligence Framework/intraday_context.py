"""
intraday_context.py

The most recently completed Asian-session range (high / low) for a pair,
consumed by levels_context.get_key_levels as the asian_high / asian_low
levels.

Trimmed 2026-09-29 (audit): the module also computed Asian/London fakeout
detection, price position, an intraday bias, entry notes and session
warnings. No module read any of them — they were computed and discarded on
every call — and the fakeout-then-go premise they encoded was REFUTED by the
framework's own research (validation_log.md). Recoverable from git history.

Data: 1H bars from OANDA via get_hourly_bars().
"""

from __future__ import annotations
from datetime import datetime, timezone, timedelta, time as dtime
from typing import Dict, Optional, Tuple

from oanda_feed import get_hourly_bars, is_configured

import pandas as pd

# Asian "range-setting" window in UTC
# GBP/AUD: Sydney + Tokyo combined = 22:00 UTC (prev day) to 07:00 UTC
_ASIAN_START_HOUR = 22   # 22:00 UTC previous day
_ASIAN_END_HOUR   = 7    # 07:00 UTC = London open


def get_intraday_context(pair: str = "GBPAUD") -> Dict:
    """
    Fetch 1H bars and return the most recently completed Asian range.
    Fails silently — never breaks the main report.

    `pair` added 2026-09-16 (docs/specs/level_source_repair_spec.md D4):
    this function is pair-specific and its signature said otherwise, so it
    always read GBPAUD. levels_context mirrored the result into
    asian_high/asian_low, making get_key_levels("GBPJPY") return six
    JPY-scale levels beside two GBP/AUD ones. Defaulted for backward
    compatibility — existing callers that want GBPAUD need no change.
    """
    if not is_configured():
        return _unavailable("OANDA not configured")

    try:
        df = get_hourly_bars(pair=pair, count=96)  # 4 days of 1H bars
    except Exception as e:
        return _unavailable(str(e))

    if df is None or df.empty:
        return _unavailable("No 1H bar data returned")

    now_utc = datetime.now(timezone.utc)

    asian_high, asian_low, asian_bars_used = _get_asian_range(df, now_utc)
    return {
        "asian_high":      asian_high,
        "asian_low":       asian_low,
        "asian_bars_used": asian_bars_used,
        "error":           None,
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



def _unavailable(reason: str) -> Dict:
    return {
        "asian_high": None, "asian_low": None, "asian_bars_used": 0,
        "error": reason,
    }
