"""
calendar_fetch.py
─────────────────
Weekly automatic economic-calendar feed (spec:
docs/specs/calendar_autofetch_spec.md, team approved 2026-07-31).
Primary source for calendar.csv; the manual-entry workflow
(update_calendar.py) remains as fallback. No shadow/ imports.

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

Output schema (exactly what news_gate.py / update_calendar.py read):
    time,currency,event,actual,forecast,previous,impact
    with time as naive-UTC "YYYY-MM-DD HH:MM".

Filter: HIGH-impact events for GBP, AUD, JPY only.
Validation before commit-to-disk: >= 1 parsed event, every event inside
[now - 24h, now + 8 days], currencies a subset of {GBP, AUD, JPY}.
Any failure → keep the existing file, log loudly, exit 0.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

FEED_URL   = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
CURRENCIES = ("GBP", "AUD", "JPY")
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


def _parse_events(raw: str, now: datetime) -> List[Dict]:
    """Parse + filter the feed. Returns rows in calendar.csv schema.
    Raises ValueError on any format violation (fail closed, never guess)."""
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
        if ccy not in CURRENCIES:
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


def _validate(rows: List[Dict], now: datetime) -> Optional[str]:
    """Spec validation before commit-to-disk. Returns an error string, or None."""
    if len(rows) < 1:
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
        if r["currency"] not in CURRENCIES:
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
    try:
        rows = _parse_events(raw, now)
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
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=HEADERS)
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, path)          # atomic — never a half-written file
    except Exception as exc:
        print(f"CALENDAR WRITE FAILED: {exc} — keeping existing calendar.csv.")
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        return False

    print(f"calendar.csv updated: {len(rows)} high-impact GBP/AUD/JPY events "
          f"through {rows[-1]['time']} UTC.")
    return True


def main() -> int:
    fetch_calendar()
    return 0                            # exit-0 discipline: never fail the caller


if __name__ == "__main__":
    sys.exit(main())
