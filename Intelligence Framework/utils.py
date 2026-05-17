"""
utils.py

Shared time utilities for the GBP/AUD intelligence framework.

Calendar times (ForexFactory) are stored in US Pacific time.
PST = UTC-8 (Nov–Mar), PDT = UTC-7 (Mar–Nov).
DST transitions are computed automatically.
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Tuple


def pacific_offset() -> Tuple[int, str]:
    """Return (utc_offset_hours, label) for US Pacific time right now."""
    now   = datetime.utcnow()
    year  = now.year
    mar1  = datetime(year, 3, 1)
    nov1  = datetime(year, 11, 1)
    dst_start = mar1 + timedelta(days=(6 - mar1.weekday()) % 7 + 7)
    dst_end   = nov1 + timedelta(days=(6 - nov1.weekday()) % 7)
    return (-7, "PDT") if dst_start <= now < dst_end else (-8, "PST")


def hours_until(dt_str: str) -> float:
    """
    Hours from now until an event whose time is stored in PST/PDT.
    Returns 99.0 on parse failure so callers can safely compare.
    """
    try:
        offset, _ = pacific_offset()
        dt_pst = datetime.strptime(str(dt_str)[:16], "%Y-%m-%d %H:%M")
        dt_utc = dt_pst + timedelta(hours=-offset)
        return (dt_utc - datetime.utcnow()).total_seconds() / 3600
    except Exception:
        return 99.0


def fmt_pst(dt_str: str, style: str = "long") -> str:
    """
    Format a PST/PDT datetime string for terminal display.
    style='long'  -> 'Mon Mar 30  1:30am PDT'
    style='short' -> '1:30am PDT'
    """
    try:
        _, label = pacific_offset()
        dt       = datetime.strptime(str(dt_str)[:16], "%Y-%m-%d %H:%M")
        time_str = dt.strftime("%I:%M%p").lstrip("0").lower()
        if style == "long":
            return f"{dt.strftime('%a %b %d')}  {time_str} {label}"
        return f"{time_str} {label}"
    except Exception:
        return str(dt_str)


def utc_to_pst_12h(utc_str: str) -> str:
    """Convert a UTC datetime string to 12-hour PST/PDT display."""
    try:
        offset, label = pacific_offset()
        dt_local = datetime.strptime(str(utc_str)[:16], "%Y-%m-%d %H:%M") + timedelta(hours=offset)
        return f"{dt_local.strftime('%I:%M%p').lstrip('0').lower()} {label}"
    except Exception:
        return str(utc_str)
