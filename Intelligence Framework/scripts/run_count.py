"""
run_count.py — EXPECTED vs ACTUAL scheduled runs for the weekly heartbeat.

The health channel counts FAILED runs. A run that never happened fails
nothing, so two multi-day scheduler gaps (2026-09-12 -> 09-14, 54.6 h, and
2026-10-06 -> 10-08, 50.5 h) both read "0 consecutive failures".

EXPECTED is derived from the INSTALLED launchd schedule
(~/Library/LaunchAgents/com.quis.intelligence.*.plist), never a hardcoded
number: every StartCalendarInterval slot of each job that runs a counted
wrapper, in the system time zone (launchd fires in local time), inside the
window. ACTUAL is the number of those slots met by a run header within
ON_TIME after the slot (each run meets one slot at most); the total number
of runs is reported beside it. ACTUAL < EXPECTED is a SHORTFALL.

Limits: a manual run that happens to land inside a missed slot's window
meets it; a time-zone change inside the window (travel) shifts the slots
and reads as a shortfall.

Usage: python3 scripts/run_count.py [--days 7]
"""
from __future__ import annotations

import argparse
import glob
import os
import plistlib
import re
from datetime import datetime, timedelta, timezone

# wrapper -> day-log prefix written by that wrapper
JOBS = {"scheduled_brief.sh": "brief", "scheduled_outcome_check.sh": "outcomes"}
PLIST_GLOB = "com.quis.intelligence.*.plist"
GRACE = timedelta(minutes=30)        # a slot this recent may still be running
# A run meets its slot if its header lands within this window. Measured
# 2026-10-17 over 246 brief runs: 223 within 15 min of the slot, 16 at 60+
# min (catch-up runs at wake, travel, manual runs).
ON_TIME = timedelta(minutes=60)
HDR = re.compile(r"^===== (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) ([A-Z]{3,4}) =====$")
TZ_OFFSETS = {"UTC": 0, "PDT": -7, "PST": -8, "MDT": -6, "MST": -7,
              "CDT": -5, "CST": -6, "EDT": -4, "EST": -5}


def agents_dir() -> str:
    return os.path.join(os.path.expanduser("~"), "Library", "LaunchAgents")


def local_zone():
    """The system zone launchd fires in (/etc/localtime), as a tzinfo."""
    from zoneinfo import ZoneInfo
    real = os.path.realpath("/etc/localtime")
    if "zoneinfo/" in real:
        return ZoneInfo(real.split("zoneinfo/", 1)[1])
    return datetime.now().astimezone().tzinfo


def schedule(directory: str | None = None) -> dict:
    """{log prefix: [(plist name, interval dict), ...]} for the counted jobs."""
    out: dict = {}
    for p in sorted(glob.glob(os.path.join(directory or agents_dir(), PLIST_GLOB))):
        with open(p, "rb") as f:
            d = plistlib.load(f)
        # any argument, not the last: the 07:30 job passes "digest" after it
        kinds = [JOBS[b] for b in (os.path.basename(str(a))
                                   for a in d.get("ProgramArguments", [])) if b in JOBS]
        kind = kinds[0] if kinds else None
        if not kind:
            continue
        sci = d.get("StartCalendarInterval")
        if sci is None:
            raise ValueError(f"{os.path.basename(p)}: no StartCalendarInterval")
        for spec in (sci if isinstance(sci, list) else [sci]):
            if "Hour" not in spec or "Minute" not in spec:
                raise ValueError(f"{os.path.basename(p)}: wildcard Hour/Minute "
                                 f"is not supported: {spec}")
            out.setdefault(kind, []).append((os.path.basename(p), spec))
    return out


def slots(specs, start: datetime, end: datetime, tz) -> list[datetime]:
    """Every UTC firing time of `specs` with start <= t <= end."""
    out = []
    day = start.astimezone(tz).date() - timedelta(days=1)
    last = end.astimezone(tz).date() + timedelta(days=1)
    while day <= last:
        for _, s in specs:
            if "Weekday" in s and (day.weekday() + 1) % 7 != s["Weekday"] % 7:
                continue                    # launchd: 0 and 7 are Sunday
            if "Day" in s and day.day != s["Day"]:
                continue
            if "Month" in s and day.month != s["Month"]:
                continue
            t = datetime(day.year, day.month, day.day, s["Hour"], s["Minute"],
                         tzinfo=tz).astimezone(timezone.utc)
            if start <= t <= end:
                out.append(t)
        day += timedelta(days=1)
    return sorted(out)


def matched(due: list[datetime], runs: list[datetime]) -> int:
    """Slots met by a run whose header lands within ON_TIME after the slot,
    each run meeting at most one slot. A plain count let launchd's catch-up
    runs at wake (three at 09-14 09:16) repay the slots missed while asleep,
    so the 09-12 -> 09-14 gap read 21/21 at the 09-20 heartbeat."""
    used, met = set(), 0
    for s in sorted(due):
        for i, r in enumerate(runs):
            if i not in used and s <= r <= s + ON_TIME:
                used.add(i)
                met += 1
                break
    return met


def run_times(logs: str, kind: str) -> list[datetime]:
    out = []
    for p in sorted(glob.glob(os.path.join(logs, f"{kind}_*.log"))):
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = HDR.match(line.rstrip("\n"))
                if not m:
                    continue
                if m[2] not in TZ_OFFSETS:
                    raise ValueError(f"{os.path.basename(p)}: unknown zone {m[2]!r}")
                local = datetime.strptime(m[1], "%Y-%m-%d %H:%M:%S")
                out.append((local - timedelta(hours=TZ_OFFSETS[m[2]]))
                           .replace(tzinfo=timezone.utc))
    return out


def report(project: str = ".", now: datetime | None = None, days: int = 7,
           directory: str | None = None, tz=None) -> list[str]:
    """Heartbeat lines. Never raises: a failure is a loud line."""
    try:
        now = now or datetime.now(timezone.utc)
        tz = tz or local_zone()
        start = now - timedelta(days=days)
        sched = schedule(directory)
        parts, short = [], []
        for kind in sorted(set(JOBS.values())):
            if kind not in sched:
                short.append(f"{kind} schedule MISSING (no installed launchd job "
                             f"runs its wrapper)")
                continue
            due = slots(sched[kind], start, now - GRACE, tz)
            runs = sorted(t for t in run_times(os.path.join(project, "logs"), kind)
                          if start <= t <= now)
            met = matched(due, runs)
            parts.append(f"{kind} {len(due)} expected / {met} on time / {len(runs)} ran")
            if met < len(due):
                short.append(f"{kind} {len(due) - met} of {len(due)} scheduled runs "
                             f"missing or over {int(ON_TIME.total_seconds() // 60)} min late")
        head = f"runs (last {days}d, launchd schedule): " + "; ".join(parts)
        if short:
            return [head, "runs: SHORTFALL — " + "; ".join(short)]
        return [head]
    except Exception as e:                  # loud, never a silent pass
        return [f"runs: RUN COUNT UNAVAILABLE ({e})"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=7)
    print("\n".join(report(days=ap.parse_args().days)))
