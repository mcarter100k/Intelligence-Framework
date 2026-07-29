"""
session_context.py

Identifies the current FX trading session and its implications for GBP/AUD.
No external dependencies beyond the standard library.

Sessions (all UTC):
  Sydney   : 22:00 - 07:00  (AUD liquidity)
  Tokyo    : 00:00 - 09:00  (AUD liquidity)
  London   : 07:00 - 16:00  (GBP primary, highest GBPAUD volume)
  New York : 12:00 - 21:00  (USD-driven)
  London/NY overlap : 12:00 - 16:00 (peak global liquidity)
"""

from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple


_SESSIONS = [
    ("Sydney",    22, 7,  "AUD"),
    ("Tokyo",      0, 9,  "AUD"),
    ("London",     7, 16, "GBP"),
    ("New York",  12, 21, "USD"),
]

_LIQUIDITY = {
    "Sydney":      "Low — AUD pairs active, minimal GBP flow",
    "Tokyo":       "Low to Medium — AUD liquidity, thin GBP",
    "London":      "HIGH — Primary GBP session, best GBP/AUD liquidity all day",
    "New York":    "Medium — USD dominates; GBP/AUD can spike on US data",
    "London/NY":   "HIGHEST — Both major centres open, tightest spreads of the day",
    "Off-hours":   "Very low — avoid new positions, spreads are wide",
}

_TENDENCIES = {
    "Sydney":    "AUD pairs tend to extend the prior New York trend or range",
    "Tokyo":     "AUD range extension possible; watch for any RBA speakers",
    "London":    "GBP momentum session — UK data releases drive the direction",
    "New York":  "USD cross-flows can whipsaw GBP/AUD; watch US releases",
    "London/NY": "Highest follow-through on directional moves — best time to trade",
    "Off-hours": "Low conviction; spreads wide; best to wait for London open",
}

# Priority order — higher index = higher priority when multiple sessions overlap
# London always beats Tokyo, London/NY beats both
_PRIORITY = ["Sydney", "Tokyo", "New York", "London", "London/NY"]


_DOW_CONTEXT = {
    0: {
        "label":     "Monday",
        "character": "Gap fill day. Sunday gaps often close in first London session. Lower conviction on new positions.",
        "best_for":  "Watching Sunday gap behaviour. Confirming weekly direction before committing.",
        "avoid":     "Full size on first entry — liquidity builds through the morning.",
    },
    1: {
        "label":     "Tuesday",
        "character": "Highest quality setup day. Full institutional liquidity, clean price action.",
        "best_for":  "Fakeout setups at Asian range extremes. London open moves are cleanest.",
        "avoid":     "Nothing specific — this is your best day.",
    },
    2: {
        "label":     "Wednesday",
        "character": "Mid-week continuation. Positions established Mon/Tue are being defended.",
        "best_for":  "Continuation in the weekly direction. Trend-following entries.",
        "avoid":     "Counter-trend — institutional trend followers are most active.",
    },
    3: {
        "label":     "Thursday",
        "character": "Often the week's strongest directional move. Institutions push positions ahead of Friday.",
        "best_for":  "Full-size entries if grade is B+ or above. Strong momentum days.",
        "avoid":     "Overtrading — one well-timed position is enough on a Thursday.",
    },
    4: {
        "label":     "Friday",
        "character": "Profit-taking day. London session active but positions close from 12pm UTC onward.",
        "best_for":  "Morning London setups only (07:00–12:00 UTC).",
        "avoid":     "New positions after 12:00 UTC — smart money is booking profits.",
    },
    5: {
        "label":     "Saturday",
        "character": "Market closed. Review your journal and plan next week.",
        "best_for":  "Analysis, journaling, level-marking on charts.",
        "avoid":     "Everything — spreads are extreme if anything is even quoted.",
    },
    6: {
        "label":     "Sunday",
        "character": "Market reopens 21:00 UTC. Pre-open analysis window.",
        "best_for":  "Reviewing weekly structure, marking key levels for Monday.",
        "avoid":     "Trading the Sunday gap open — spreads are wide and liquidity is thin until Monday.",
    },
}


def _market_status(now_utc: datetime) -> Tuple[bool, str, str]:
    """
    Returns (is_closed, reason, next_open_in_local_time).

    The forex week boundary is 5pm New York — close Friday, reopen Sunday. In
    UTC that is 21:00 during US daylight time (EDT) and 22:00 during US standard
    time (EST). It is NOT a fixed 21:00 year-round: hardcoding 21:00 made every
    winter Sunday 21:00–22:00 UTC read as "open" an hour before real liquidity.
    All display times are shown in Pacific (PDT/PST).
    """
    from utils import pacific_offset
    weekday = now_utc.weekday()   # 0=Mon … 6=Sun
    hour    = now_utc.hour

    offset, tz_label = pacific_offset()   # -7 PDT (summer) / -8 PST (winter)

    # New York is 3h ahead of Los Angeles, so eastern_offset = offset + 3, and
    # 5pm NY in UTC = 17 - eastern_offset → 21 (EDT) or 22 (EST).
    boundary_utc = 17 - (offset + 3)

    def _utc_to_pt_str(utc_h: int) -> str:
        """Convert an integer UTC hour to a Pacific 12-hour display string."""
        pt = (utc_h + offset) % 24   # offset is negative (-7 PDT / -8 PST)
        suffix = "am" if pt < 12 else "pm"
        display = pt % 12 or 12
        return f"{display}{suffix} {tz_label}"

    open_pt = _utc_to_pt_str(boundary_utc)

    if weekday == 5:                              # Saturday — always closed
        return True, "Weekend — market closed (Saturday)", f"Sunday {open_pt}"
    if weekday == 6 and hour < boundary_utc:      # Sunday before reopen
        opens_in = boundary_utc - hour
        return True, "Weekend — market closed (Sunday)", f"Today at {open_pt} ({opens_in}h from now)"
    if weekday == 4 and hour >= boundary_utc:     # Friday after close
        return True, "Weekend — market closed (Friday close)", f"Sunday {open_pt}"

    return False, "", ""


def _utc_hour() -> int:
    return datetime.now(timezone.utc).hour


def _active_sessions(utc_hour: int) -> List[str]:
    active = []
    for name, start, end, _ in _SESSIONS:
        if start < end:
            if start <= utc_hour < end:
                active.append(name)
        else:  # wraps midnight
            if utc_hour >= start or utc_hour < end:
                active.append(name)
    return active if active else ["Off-hours"]


def _pick_label(active: List[str]) -> str:
    """
    Pick the single best label for the current session mix.
    London/NY overlap takes top priority, then London, then New York,
    then Tokyo, then Sydney. This prevents Tokyo from overriding London
    during the 07:00-09:00 UTC window when both are technically open.
    """
    if "London" in active and "New York" in active:
        return "London/NY"
    for label in reversed(_PRIORITY):
        if label in active:
            return label
    return active[0] if active else "Off-hours"


def get_session_context() -> Dict:
    now_utc  = datetime.now(timezone.utc)
    utc_hour = now_utc.hour
    weekday  = now_utc.weekday()

    is_closed, close_reason, next_open = _market_status(now_utc)

    dow      = _DOW_CONTEXT.get(weekday, {})
    dow_label = dow.get("label", "")

    if is_closed:
        return {
            "utc_time":        now_utc.strftime("%Y-%m-%d %H:%M UTC"),
            "active_sessions": ["Market closed"],
            "session_label":   "Market closed",
            "session":         "Market closed",
            "liquidity":       "Market closed",
            "tendency":        "Market closed",
            "primary_driver":  "—",
            "alert":           f"{close_reason}. Next open: {next_open}",
            "market_closed":   True,
            "close_reason":    close_reason,
            "next_open":       next_open,
            "day_of_week":     dow_label,
            "dow_character":   dow.get("character", ""),
            "dow_best_for":    dow.get("best_for", ""),
            "dow_avoid":       dow.get("avoid", ""),
        }

    active   = _active_sessions(utc_hour)
    label    = _pick_label(active)
    liquidity = _LIQUIDITY.get(label, "Unknown")
    tendency  = _TENDENCIES.get(label, "No data")

    driver_map = {
        "London":    "GBP",
        "New York":  "USD",
        "Tokyo":     "AUD",
        "Sydney":    "AUD",
        "London/NY": "GBP and USD",
    }
    primary = driver_map.get(label, "Mixed")
    alert   = _timing_alert(utc_hour)

    return {
        "utc_time":        now_utc.strftime("%Y-%m-%d %H:%M UTC"),
        "active_sessions": active,
        "session_label":   label,
        "session":         label,
        "liquidity":       liquidity,
        "tendency":        tendency,
        "primary_driver":  primary,
        "alert":           alert,
        "market_closed":   False,
        "close_reason":    "",
        "next_open":       "",
        "day_of_week":     dow_label,
        "dow_character":   dow.get("character", ""),
        "dow_best_for":    dow.get("best_for", ""),
        "dow_avoid":       dow.get("avoid", ""),
    }


def _timing_alert(utc_hour: int) -> str:
    alerts = {
        6:  "London open in ~1 hour — expect volatility spike at 07:00 UTC",
        7:  "London just opened — GBP/AUD liquidity is now at its peak",
        11: "London/NY overlap starts in ~1 hour — busiest window approaching",
        12: "London/NY overlap — highest global liquidity right now",
        16: "London closing — GBP/AUD volume dropping off",
        20: "New York closing soon — watch for gaps on reopen",
        21: "New York closed — market going into off-hours",
        22: "Sydney opening — AUD pairs coming alive",
    }
    return alerts.get(utc_hour, "")


if __name__ == "__main__":
    ctx = get_session_context()
    for k, v in ctx.items():
        print(f"{k}: {v}")
