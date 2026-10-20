"""Bar-grid regularity check on TIMESTAMP files (time_utc,complete).

usage: python3 -I history_depth_bar_grid.py <times_csv> <D|H4|H1> <json_out>

Modern convention: trading day D (Mon-Fri) is the session (D-1) 17:00 NY ->
D 17:00 NY. Expected starts: D1 17:00; H4 17,21,01,05,09,13; H1 every hour.
Reads timestamps only; no prices exist in the input.
"""
import csv
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
PT = ZoneInfo("America/Los_Angeles")
SLOTS = {"D": [17], "H4": [17, 21, 1, 5, 9, 13], "H1": list(range(17, 24)) + list(range(0, 17))}
HOURS = {"D": 24, "H4": 4, "H1": 1}


def trading_day(t_ny):
    return (t_ny + timedelta(hours=7)).date()


def expected_slots(day, gran):
    out = []
    for h in SLOTS[gran]:
        d = day - timedelta(days=1) if h >= 17 else day
        out.append(datetime(d.year, d.month, d.day, h, tzinfo=NY).astimezone(timezone.utc))
    return out


def fmt_pt(t):
    return t.astimezone(PT).strftime("%Y-%m-%d %H:%M %Z")


def main():
    path, gran, out = sys.argv[1:4]
    times = []
    with open(path) as fh:
        for r in csv.DictReader(fh):
            times.append(datetime.fromisoformat(r["time_utc"]))
    times.sort()
    tset = set(times)
    first_day = trading_day(times[0].astimezone(NY))
    last_day = trading_day(times[-1].astimezone(NY))

    per_year = defaultdict(lambda: defaultdict(int))
    per_day = defaultdict(int)
    for t in times:
        tn = t.astimezone(NY)
        d = trading_day(tn)
        y = per_year[d.year]
        y["rows"] += 1
        aligned = tn.minute == 0 and tn.hour in SLOTS[gran]
        if d.weekday() >= 5:
            y["weekend_rows"] += 1
        elif not aligned:
            y["misaligned_rows"] += 1
        else:
            y["aligned_weekday_rows"] += 1
            per_day[d] += 1

    # expected grid over weekday trading days in [first_day, last_day]
    missing = []
    full, short, weekdays_with_bars, weekday_total = defaultdict(int), defaultdict(list), defaultdict(int), defaultdict(int)
    d = first_day
    n_slots = len(SLOTS[gran])
    while d <= last_day:
        if d.weekday() < 5:
            weekday_total[d.year] += 1
            exp = expected_slots(d, gran)
            got = sum(1 for s in exp if s in tset)
            if got:
                weekdays_with_bars[d.year] += 1
            if got == n_slots:
                full[d.year] += 1
            elif got:
                short[d.year].append(d.isoformat())
            for s in exp:
                if s not in tset and times[0] <= s <= times[-1]:
                    missing.append(s)
        d += timedelta(days=1)

    # collapse missing slots into runs (consecutive expected slots)
    step = timedelta(hours=HOURS[gran])
    runs = []
    for s in missing:
        # same run if no observed bar lies between the previous missing slot and this one
        if runs and not _window(times, runs[-1][1], s):
            runs[-1][1] = s
            runs[-1][2] += 1
            continue
        runs.append([s, s, 1])
    gaps = [{"first_missing_pt": fmt_pt(a), "last_missing_pt": fmt_pt(b),
             "first_missing_utc": a.isoformat(), "slots": n,
             "duration_h": n * HOURS[gran]} for a, b, n in runs]

    years = {}
    for yr in sorted(set(per_year) | set(weekday_total)):
        y = per_year[yr]
        years[yr] = {
            "rows": y["rows"],
            "aligned_weekday_rows": y["aligned_weekday_rows"],
            "weekend_rows": y["weekend_rows"],
            "misaligned_rows": y["misaligned_rows"],
            "weekday_trading_days": weekday_total[yr],
            "weekdays_with_bars": weekdays_with_bars[yr],
            "days_full_grid": full[yr],
            "pct_full_of_days_with_bars": round(100 * full[yr] / weekdays_with_bars[yr], 2) if weekdays_with_bars[yr] else None,
            "short_days": len(short[yr]),
        }
    res = {"file": path, "gran": gran, "first_utc": times[0].isoformat(),
           "last_utc": times[-1].isoformat(), "first_pt": fmt_pt(times[0]),
           "last_pt": fmt_pt(times[-1]), "rows": len(times), "years": years,
           "gap_runs": len(gaps), "gaps": gaps,
           "short_day_dates": {str(k): v for k, v in short.items()}}
    with open(out, "w") as fh:
        json.dump(res, fh, indent=1)
    print(f"{path.rsplit('/',1)[-1]}: rows={len(times)} first={fmt_pt(times[0])} last={fmt_pt(times[-1])} gap_runs={len(gaps)}")
    for yr, v in years.items():
        print(" ", yr, v)


def _window(times, a, b):
    import bisect
    i = bisect.bisect_right(times, a)
    j = bisect.bisect_left(times, b)
    return times[i:j]


if __name__ == "__main__":
    main()
