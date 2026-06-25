"""
update_calendar.py

Helper script to update calendar.csv with this week's GBP/AUD events.
Run this manually when the news gate is disabled due to stale data.

Usage:
    python update_calendar.py          — shows current file status
    python update_calendar.py --clear  — wipe existing entries, start fresh
"""

import os
import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path

CALENDAR_FILE = Path(__file__).parent / "calendar.csv"
HEADERS       = ["time", "currency", "event", "actual", "forecast", "previous", "impact"]


def _status() -> None:
    if not CALENDAR_FILE.exists():
        print(f"calendar.csv does not exist — will be created at {CALENDAR_FILE}")
        return

    with open(CALENDAR_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("calendar.csv is empty.")
        return

    try:
        dates = [datetime.strptime(r["time"][:10], "%Y-%m-%d") for r in rows if r.get("time")]
        most_recent = max(dates)
        age = (datetime.now() - most_recent).days
        cutoff = datetime.now() - timedelta(days=7)
        status = "✅ FRESH" if most_recent >= cutoff else f"⚠️  STALE ({age} days old)"
        print(f"\ncalendar.csv — {len(rows)} events, most recent: {most_recent.date()}  {status}")
    except Exception as e:
        print(f"calendar.csv — {len(rows)} events (could not parse dates: {e})")

    print("\nCurrent events:")
    for r in rows:
        act = r.get("actual", "").strip()
        fc  = r.get("forecast", "").strip()
        print(f"  {r.get('time','')[:16]:16}  {r.get('currency',''):4}  "
              f"{r.get('impact',''):6}  {r.get('event','')[:40]:40}  "
              f"actual={act or '—':8}  fc={fc or '—'}")


def _clear() -> None:
    with open(CALENDAR_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
    print(f"Cleared {CALENDAR_FILE}. Ready for new entries.")


def _instructions() -> None:
    today = datetime.now()
    mon   = today - timedelta(days=today.weekday())
    print(f"""
How to add events:
──────────────────
1. Go to https://www.forexfactory.com/calendar (filter: GBP and AUD, High impact)
2. Add rows to {CALENDAR_FILE.name} in this format:

   time,currency,event,actual,forecast,previous,impact

   Example (upcoming — no actual yet):
   {mon.strftime('%Y-%m-%d')} 09:30,GBP,CPI YoY,,2.9%,3.0%,High

   Example (released):
   {mon.strftime('%Y-%m-%d')} 09:30,GBP,CPI YoY,3.1%,2.9%,3.0%,High

3. Save the file and re-run main.py — the news gate will activate.

Tips:
  • Leave "actual" blank for upcoming events
  • Impact values: High | Medium | Low
  • Time is UTC (London time in winter, UTC+0; summer UTC+1)
  • Only GBP and AUD events affect GBP/AUD trades
""")


def main() -> None:
    if "--clear" in sys.argv:
        _clear()
    else:
        _status()
        _instructions()


if __name__ == "__main__":
    main()
