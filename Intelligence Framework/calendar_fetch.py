"""
calendar_fetch.py
─────────────────
Weekly automatic economic-calendar feed (spec:
docs/specs/calendar_autofetch_spec.md, team approved 2026-07-31).
Sole writer of calendar.csv (the manual update_calendar.py was removed
in the 2026-09-29 audit). No shadow/ imports.

SOURCE (selected + verified live 2026-07-31):
    https://nfs.faireconomy.media/ff_calendar_thisweek.json
ForexFactory's weekly calendar feed (faireconomy CDN). FORMAT ASSUMPTIONS,
confirmed by live probe:
  * JSON array of event objects with keys:
      title    : str event name
      country  : str CURRENCY CODE ("GBP", "AUD", "JPY", "USD", ...)
      date     : ISO-8601 with UTC offset, e.g. "2026-07-27T04:00:00-04:00"
      impact   : "High" | "Medium" | "Low" (occasionally "Holiday")
      forecast : str (may be empty)
      previous : str (may be empty)
  * No "actual" field — the CSV's actual column is left blank (news_gate
    does not read it).
  * The feed covers the current ForexFactory week (Sun–Sat), so a Sunday
    fetch covers the coming trading week; a mid-week retry re-fetches the
    same week.
If the provider changes any of these assumptions, validation below fails
closed: the existing calendar.csv is kept untouched and the stale-calendar
honest note in the brief is the designed backstop — a failed fetch degrades
to a visible warning, never a silent wrong calendar.

Output schema (exactly what news_gate.py reads):
    time,currency,event,actual,forecast,previous,impact
    with time as naive-UTC "YYYY-MM-DD HH:MM".

Filter: HIGH-impact events for GBP, AUD, JPY, and USD (USD added
2026-11-01, docs/specs/us_events_context_spec.md: shown in the brief as
context only; news_gate still gates on the pair's own currencies only).
A USD row that cannot be read is skipped, never fatal, and USD rows later
than the GBP/AUD/JPY rows' feed week are dropped (Rev 1, team review).
Validation before commit-to-disk: >= 1 parsed GBP/AUD/JPY event (a USD-only
parse is rejected like an empty one), every event inside
[now - 24h, now + 8 days], currencies a subset of {GBP, AUD, JPY, USD}.
Any failure → keep the existing file, log loudly, exit 0.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

FEED_URL   = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
CURRENCIES = ("GBP", "AUD", "JPY")            # the gated currencies
CONTEXT_CURRENCIES = ("USD",)                  # kept for display only
FETCH_CURRENCIES = CURRENCIES + CONTEXT_CURRENCIES
WINDOW_PAST_HOURS  = 24    # tolerate already-passed events from earlier today
WINDOW_FUTURE_DAYS = 8     # spec: all dates within the next 8 days
TIMEOUT_S  = 20

_CALENDAR_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "calendar.csv")
HEADERS = ["time", "currency", "event", "actual", "forecast", "previous", "impact"]


def _fetch_raw(url: str = FEED_URL, timeout: int = TIMEOUT_S) -> str:
    """Network fetch, isolated for testing/monkeypatching."""
    import requests
    resp = requests.get(url, timeout=timeout,
                        headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return resp.text


def _parse_events(raw: str, now: datetime,
                  skipped: Optional[List[str]] = None) -> List[Dict]:
    """Parse + filter the feed. Returns rows in calendar.csv schema.
    Raises ValueError on any format violation in a GBP/AUD/JPY row (fail
    closed, never guess). A context-only (USD) row that cannot be read is
    skipped and noted in `skipped` instead: a row the gate never uses must
    never cost the week's gated calendar (team review 2026-11-01)."""
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("feed root is not a list")

    lo = now - timedelta(hours=WINDOW_PAST_HOURS)
    hi = now + timedelta(days=WINDOW_FUTURE_DAYS)

    rows: List[Dict] = []
    for e in data:
        if not isinstance(e, dict):
            raise ValueError("event entry is not an object")
        if (e.get("impact") or "").strip().lower() != "high":
            continue
        ccy = (e.get("country") or "").strip().upper()
        if ccy not in FETCH_CURRENCIES:
            continue
        if ccy in CONTEXT_CURRENCIES:
            try:
                row = _context_row(e, ccy, lo, hi)
            except Exception as exc:
                if skipped is not None:
                    skipped.append(f"{ccy} {e.get('title')!r}: {exc}")
                continue
            if row is not None:
                rows.append(row)
            continue
        try:
            dt = datetime.fromisoformat(e["date"])
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"unparseable event date: {e.get('date')!r}")
        dt_utc = dt.astimezone(timezone.utc)
        if not (lo <= dt_utc <= hi):
            continue
        rows.append({
            "time":     dt_utc.strftime("%Y-%m-%d %H:%M"),
            "currency": ccy,
            "event":    (e.get("title") or "").strip(),
            "actual":   "",
            "forecast": (e.get("forecast") or "").strip(),
            "previous": (e.get("previous") or "").strip(),
            "impact":   "High",
        })
    return rows


def _context_row(e: Dict, ccy: str, lo: datetime, hi: datetime) -> Optional[Dict]:
    """A USD row in calendar.csv schema, None if outside the window. Raises on
    anything unreadable; the caller skips it. Stricter than the gated path:
    a date without a UTC offset is unreadable, never read as local time."""
    dt = datetime.fromisoformat(e["date"])
    if dt.tzinfo is None:
        raise ValueError(f"date has no UTC offset: {e['date']!r}")
    dt_utc = dt.astimezone(timezone.utc)
    if not (lo <= dt_utc <= hi):
        return None
    text = lambda k: (e.get(k) or "").strip()      # non-text raises → skipped
    return {"time": dt_utc.strftime("%Y-%m-%d %H:%M"), "currency": ccy,
            "event": text("title"), "actual": "", "forecast": text("forecast"),
            "previous": text("previous"), "impact": "High"}


def _confine_context_rows(rows: List[Dict],
                          dropped: Optional[List[str]] = None) -> List[Dict]:
    """Drop USD rows later than the coverage of the newest GBP/AUD/JPY row.
    check_news_gate takes staleness from the newest row of ANY currency, so a
    stray next-week USD row would turn a stale gate active. The real feed is
    one week, so this should never fire; nothing else guarantees it
    (us_events_context_spec §1.1, Rev 1)."""
    from news_gate import covered_through
    own = [datetime.strptime(r["time"], "%Y-%m-%d %H:%M")
           for r in rows if r["currency"] in CURRENCIES]
    if not own:
        return rows                 # _validate rejects a feed with none
    end = covered_through(max(own))
    kept = []
    for r in rows:
        if (r["currency"] in CONTEXT_CURRENCIES
                and datetime.strptime(r["time"], "%Y-%m-%d %H:%M") > end):
            if dropped is not None:
                dropped.append(f"{r['currency']} {r['event']!r}: after this calendar's week")
            continue
        kept.append(r)
    return kept


def _validate(rows: List[Dict], now: datetime) -> Optional[str]:
    """Spec validation before commit-to-disk. Returns an error string, or None."""
    if not any(r["currency"] in CURRENCIES for r in rows):
        return "0 high-impact GBP/AUD/JPY events parsed for the window"
    lo = now - timedelta(hours=WINDOW_PAST_HOURS)
    hi = now + timedelta(days=WINDOW_FUTURE_DAYS)
    for r in rows:
        try:
            dt = datetime.strptime(r["time"], "%Y-%m-%d %H:%M").replace(
                tzinfo=timezone.utc)
        except ValueError:
            return f"invalid time in parsed row: {r['time']!r}"
        if not (lo <= dt <= hi):
            return f"event outside the next-8-days window: {r['time']}"
        if r["currency"] not in FETCH_CURRENCIES:
            return f"unexpected currency: {r['currency']!r}"
    return None


def fetch_calendar(calendar_path: Optional[str] = None,
                   now: Optional[datetime] = None,
                   fetcher=None) -> bool:
    """
    Fetch → parse → validate → atomically replace calendar.csv.
    Returns True on a successful update. On ANY failure the existing file is
    kept untouched and the failure is logged loudly to stdout — the brief's
    stale-calendar note is the designed backstop. Never raises.
    """
    path = calendar_path or _CALENDAR_FILE
    now = now or datetime.now(timezone.utc)
    if fetcher is None:
        fetcher = _fetch_raw     # resolved at call time (test/patch friendly)
    try:
        raw = fetcher()
    except Exception as exc:
        print(f"CALENDAR FETCH FAILED (network): {exc} — keeping existing "
              f"calendar.csv; brief will show the stale-calendar note.")
        return False
    skipped: List[str] = []
    try:
        rows = _parse_events(raw, now, skipped)
        rows = _confine_context_rows(rows, skipped)
    except Exception as exc:
        print(f"CALENDAR FETCH REJECTED (malformed feed): {exc} — keeping "
              f"existing calendar.csv untouched.")
        return False
    err = _validate(rows, now)
    if err:
        print(f"CALENDAR FETCH REJECTED (validation): {err} — keeping "
              f"existing calendar.csv untouched.")
        return False

    rows.sort(key=lambda r: r["time"])
    try:
        from ledger_io import atomic_write_rows   # locked, fsynced, atomic
        atomic_write_rows(path, HEADERS, rows)
    except Exception as exc:
        print(f"CALENDAR WRITE FAILED: {exc} — keeping existing calendar.csv.")
        return False

    n_own = sum(r["currency"] in CURRENCIES for r in rows)
    # Feed text in the note is cut to plain characters: this line lands in the
    # brief day log, which latest_view reads (spec §1.1, Rev 2).
    import re
    detail = re.sub(r"[^A-Za-z0-9 .,()'%+:-]", " ", "; ".join(skipped))
    detail = re.sub(r"\s+", " ", detail).strip()[:200]
    note = (f"; skipped {len(skipped)} US row(s) (unreadable or outside "
            f"this calendar's week): {detail}" if skipped else "")
    print(f"calendar.csv updated: {n_own} high-impact GBP/AUD/JPY events "
          f"and {len(rows) - n_own} US events (context only){note} "
          f"through {rows[-1]['time']} UTC.")
    return True


def main() -> int:
    fetch_calendar()
    return 0                            # exit-0 discipline: never fail the caller


if __name__ == "__main__":
    sys.exit(main())
