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
  * HIGH-impact event for the pair's OWN currencies within the next 2 hours
    → gating (with event name + minutes-until).
    USD events are deliberately out of scope — known v1 boundary.
  * calendar.csv missing or older than 7 days → gate INACTIVE with a
    staleness note. Never block on bad data; never pretend coverage that
    isn't there.
"""
from __future__ import annotations

import csv
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional

# Pair → its own currencies. USD deliberately out of scope (v1 boundary).
PAIR_CURRENCIES = {
    "GBP_AUD": ("GBP", "AUD"),
    "GBP_JPY": ("GBP", "JPY"),
}

WINDOW_MINUTES = 120   # "next 2 hours"
STALE_DAYS     = 7     # calendar older than this → gate INACTIVE

_CALENDAR_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "calendar.csv")

_STALE_NOTE   = "news calendar stale — event risk unchecked"
_MISSING_NOTE = "news calendar missing — event risk unchecked"


def _result(active: bool, gating: bool = False, event: str = "",
            currency: str = "", minutes_until: Optional[int] = None,
            note: str = "") -> Dict:
    return {"active": active, "gating": gating, "event": event,
            "currency": currency, "minutes_until": minutes_until, "note": note}


def check_news_gate(instrument: str, now: Optional[datetime] = None,
                    calendar_path: Optional[str] = None) -> Dict:
    """
    Gate check for one instrument. Returns:
      active        : calendar present and fresh enough to trust
      gating        : a HIGH-impact own-currency event is within 2 hours
      event/currency: the soonest such event
      minutes_until : minutes to that event
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
    if newest < now_naive - timedelta(days=STALE_DAYS):
        return _result(active=False, note=_STALE_NOTE)

    # Fresh calendar — look for the soonest HIGH-impact own-currency event
    # inside the window.
    soonest = None
    for dt, ccy, name, impact in events:
        if impact != "high" or ccy not in currencies:
            continue
        mins = (dt - now_naive).total_seconds() / 60.0
        if 0 <= mins <= WINDOW_MINUTES:
            if soonest is None or mins < soonest[0]:
                soonest = (mins, ccy, name)

    if soonest:
        mins, ccy, name = soonest
        return _result(active=True, gating=True, event=name or "high-impact release",
                       currency=ccy, minutes_until=int(round(mins)))
    return _result(active=True)
