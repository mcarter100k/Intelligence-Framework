"""
news_gate.py
────────────
Pre-news stand-down gate — safety infrastructure, same class as the
market-closed gate (spec: docs/specs/news_gate_spec.md, team approved
2026-07-29). No edge claims, no direction prediction: the framework declines
to present its reading as valid inside a pre-release window where its inputs
are guaranteed to be repriced.

Lean by design — reads calendar.csv directly; imports NOTHING from shadow/.

Behavior:
  * HIGH-impact event for the pair's OWN currencies from 2 hours before to
    30 minutes after its release → gating (with event name + minutes-until,
    negative once released). The post-release buffer is risk_config's
    event lockout after = 0.5h (docs/specs/decision_logic_spec.md D5).
    USD events are deliberately out of scope — known v1 boundary.
  * calendar.csv missing, or not covering today → gate INACTIVE with a
    staleness note. The feed is ForexFactory's Sun–Sat week (US Eastern), so
    a calendar covers through 23:59 ET on the Saturday of its newest event's
    week — a last-week file is stale on Monday even though its newest event
    is under 7 days old (D5). Never block on bad data; never pretend
    coverage that isn't there.
"""
from __future__ import annotations

import csv
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from zoneinfo import ZoneInfo

# Pair → its own currencies. USD deliberately out of scope (v1 boundary).
PAIR_CURRENCIES = {
    "GBP_AUD": ("GBP", "AUD"),
    "GBP_JPY": ("GBP", "JPY"),
}

WINDOW_MINUTES = 120   # "next 2 hours"
AFTER_MINUTES  = 30    # still gating this long after a release (risk_config 0.5h)

_FEED_TZ = ZoneInfo("America/New_York")   # ForexFactory's week is Sun–Sat ET

_CALENDAR_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "calendar.csv")

_STALE_NOTE   = "news calendar stale — event risk unchecked"
_MISSING_NOTE = "news calendar missing — event risk unchecked"


def _result(active: bool, gating: bool = False, event: str = "",
            currency: str = "", minutes_until: Optional[int] = None,
            note: str = "", event_time_utc: str = "") -> Dict:
    return {"active": active, "gating": gating, "event": event,
            "currency": currency, "minutes_until": minutes_until,
            "event_time_utc": event_time_utc, "note": note}


def covered_through(newest_event_utc: datetime) -> datetime:
    """The end of the calendar's coverage, naive UTC: 23:59:59 US Eastern on
    the Saturday of the ForexFactory week holding its newest event."""
    et = newest_event_utc.replace(tzinfo=timezone.utc).astimezone(_FEED_TZ)
    sat = et.date() + timedelta(days=(5 - et.weekday()) % 7)
    end = datetime(sat.year, sat.month, sat.day, 23, 59, 59, tzinfo=_FEED_TZ)
    return end.astimezone(timezone.utc).replace(tzinfo=None)


def when_phrase(minutes) -> str:
    """How far the gating event is from now, for every renderer: "90 minutes"
    before it, "released 5 minutes ago" after it. Callers keep their own
    "in"/"due in" wording for the pre-release case, so it reads unchanged."""
    if minutes is None:
        return "under 2 hours"
    m = int(minutes)
    if m < 0:
        return f"released {-m} minutes ago"
    return f"{m} minutes"


def check_news_gate(instrument: str, now: Optional[datetime] = None,
                    calendar_path: Optional[str] = None) -> Dict:
    """
    Gate check for one instrument. Returns:
      active        : calendar present and fresh enough to trust
      gating        : a HIGH-impact own-currency event is within 2 hours,
                      or was released under 30 minutes ago
      event/currency: the nearest such event
      minutes_until : minutes to that event (negative once released)
      note          : staleness/missing note when the gate is INACTIVE
    Never raises. Unknown instruments and bad rows are skipped silently
    (never block on bad data).
    """
    currencies = PAIR_CURRENCIES.get(instrument or "")
    if not currencies:
        return _result(active=False, note="instrument not covered by news gate")

    path = calendar_path or _CALENDAR_FILE
    if not os.path.exists(path):
        return _result(active=False, note=_MISSING_NOTE)

    if now is None:
        now = datetime.now(timezone.utc)
    now_naive = now.astimezone(timezone.utc).replace(tzinfo=None)

    events = []          # (event_dt, currency, name, impact)
    newest: Optional[datetime] = None
    try:
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                try:
                    dt = datetime.strptime(row["time"].strip()[:16],
                                           "%Y-%m-%d %H:%M")
                except (KeyError, ValueError, AttributeError):
                    continue
                if newest is None or dt > newest:
                    newest = dt
                events.append((dt, (row.get("currency") or "").strip().upper(),
                               (row.get("event") or "").strip(),
                               (row.get("impact") or "").strip().lower()))
    except Exception:
        return _result(active=False, note=_MISSING_NOTE)

    if newest is None:
        return _result(active=False, note=_MISSING_NOTE)
    if now_naive > covered_through(newest):
        return _result(active=False, note=_STALE_NOTE)

    # Calendar covers now — look for the nearest HIGH-impact own-currency
    # event inside the window (a just-released event outranks a later one:
    # its repricing is under way now).
    soonest = None
    for dt, ccy, name, impact in events:
        if impact != "high" or ccy not in currencies:
            continue
        mins = (dt - now_naive).total_seconds() / 60.0
        if -AFTER_MINUTES <= mins <= WINDOW_MINUTES:
            if soonest is None or mins < soonest[0]:
                soonest = (mins, ccy, name, dt)

    if soonest:
        mins, ccy, name, dt = soonest
        return _result(active=True, gating=True, event=name or "high-impact release",
                       currency=ccy, minutes_until=int(round(mins)),
                       event_time_utc=dt.strftime("%Y-%m-%dT%H:%M:%SZ"))
    return _result(active=True)
