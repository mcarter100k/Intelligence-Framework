"""Weekend-candle conversion for the OANDA STUDY data, exactly as approved in
docs/specs/study_weekend_candle_spec.md §6 (owner ruling 2026-10-22).

Pure functions on {open_time_utc: (o, h, l, c)} dicts; no I/O, no network.
Never imported by the live path (the live feed serves no weekend candles).

  - A candle's session is the New York date of (open + 7 h).
  - Saturday-session candles (open Fri 17:00 NY onward) are DROPPED.
  - Sunday-session candles FOLD into the target session: the first later
    weekday session holding both a D1 and an H4 candle.
      D1: target = (earliest Sunday open, max high, min low, target close)
      H4: target's earliest H4 = (earliest folded open, max high, min low, own close)
    Timestamps stay the target's. No target -> ValueError.
"""
from datetime import date, datetime, timedelta
from typing import Dict, Tuple
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
SAT, SUN = 5, 6
Bar = Tuple[float, float, float, float]


def session_day(t: datetime) -> date:
    return (t.astimezone(NY) + timedelta(hours=7)).date()


def _by_session(bars: Dict[datetime, Bar]) -> Dict[date, list]:
    out: Dict[date, list] = {}
    for t in sorted(bars):
        out.setdefault(session_day(t), []).append(t)
    return out


def _combine(times, bars, keep_close_of) -> Bar:
    first = min(times)
    return (bars[first][0],
            max(bars[t][1] for t in times),
            min(bars[t][2] for t in times),
            bars[keep_close_of][3])


def convert(d1: Dict[datetime, Bar], h4: Dict[datetime, Bar]):
    """Return (d1_out, h4_out, log). Inputs are not modified."""
    d1s, h4s = _by_session(d1), _by_session(h4)
    weekday_targets = sorted(d for d in set(d1s) & set(h4s) if d.weekday() < SAT)
    d1_out, h4_out = dict(d1), dict(h4)
    log = {"saturday_dropped_d1": 0, "saturday_dropped_h4": 0,
           "sunday_folded_d1": 0, "sunday_folded_h4": 0, "folds": []}

    for day in sorted(set(d1s) | set(h4s)):
        if day.weekday() == SAT:
            for t in d1s.get(day, []):
                del d1_out[t]
                log["saturday_dropped_d1"] += 1
            for t in h4s.get(day, []):
                del h4_out[t]
                log["saturday_dropped_h4"] += 1
        elif day.weekday() == SUN:
            target = next((d for d in weekday_targets if d > day), None)
            if target is None:
                raise ValueError(f"Sunday session {day} has no later weekday session to fold into")
            sun_d1, sun_h4 = d1s.get(day, []), h4s.get(day, [])
            if sun_d1:
                tgt = d1s[target][0]
                d1_out[tgt] = _combine(sun_d1 + [tgt], d1, keep_close_of=tgt)
                for t in sun_d1:
                    del d1_out[t]
                log["sunday_folded_d1"] += len(sun_d1)
            if sun_h4:
                tgt = h4s[target][0]
                h4_out[tgt] = _combine(sun_h4 + [tgt], h4, keep_close_of=tgt)
                for t in sun_h4:
                    del h4_out[t]
                log["sunday_folded_h4"] += len(sun_h4)
            log["folds"].append((day.isoformat(), target.isoformat()))
    return d1_out, h4_out, log
