"""
display_time.py
───────────────
THE one place times become human-readable (docs/specs/
display_timezone_spec.md). Internals everywhere stay UTC; every rendered
timestamp routes through here.

Config: one zone — DEFAULT_DISPLAY_TZ, overridden by the DISPLAY_TZ env
var. Always a 12-hour clock with AM/PM. Pacific is labelled "PT" all year
(owner directive, spec addendum 2026-11-18); any other zone keeps the
zoneinfo abbreviation BY DATE (EDT/EST, …).

    to_display(dt)                      → "Tue 08 Sep 2026 9:07 PM PT"
    to_display(dt, style="time")        → "9:07 PM PT"
    to_display(dt, style="day_time")    → "Sun 2:00 PM PT"
    to_display(dt, style="day_date")    → "Thu 12 Nov 6:00 AM PT"

`dt` may be an aware datetime, a naive datetime (treated as UTC — the
house convention for internals), or an ISO string ("…Z" accepted).
Never raises: unparseable input renders as "" so a display helper can
never break a brief.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Union
from zoneinfo import ZoneInfo

DEFAULT_DISPLAY_TZ = "America/Los_Angeles"
ZONE_LABELS = {"America/Los_Angeles": "PT"}     # owner-chosen; others by date


def display_zone() -> ZoneInfo:
    name = (os.environ.get("DISPLAY_TZ") or "").strip() or DEFAULT_DISPLAY_TZ
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo(DEFAULT_DISPLAY_TZ)


def to_display(dt: Union[datetime, str, None], style: str = "full") -> str:
    try:
        if isinstance(dt, str):
            s = dt.strip()
            if not s:
                return ""
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt is None:
            return ""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)     # naive = UTC internally
        zone = display_zone()
        loc = dt.astimezone(zone)
        hour12 = int(loc.strftime("%I"))             # no leading zero
        label = ZONE_LABELS.get(zone.key) or f"{loc:%Z}"
        clock = f"{hour12}:{loc:%M} {loc:%p} {label}"
        if style == "time":
            return clock
        if style == "day_time":
            return f"{loc:%a} {clock}"
        if style == "day_date":
            return f"{loc:%a %d %b} {clock}"
        return f"{loc:%a %d %b %Y} {clock}"
    except Exception:
        return ""
