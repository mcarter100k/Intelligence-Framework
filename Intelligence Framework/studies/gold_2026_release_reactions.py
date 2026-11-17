"""gold_2026_release_reactions.py — how gold reacted to the 2026 FOMC decisions,
CPI and jobs reports (descriptive, report-only; learning data, never evidence).

usage: python3 -I gold_2026_release_reactions.py     (run via scripts/reality_run.py)

Release dates and times: studies/us_events_2026.csv (each row sourced).
Prices: OANDA XAU_USD mid candles (M5, H4, D), fetched read-only.

Prints, per release:
- the 30-minute reaction and the move to the next session's close (the Gold
  News Playbook's measures: "kept" = the 30-minute direction equals the
  direction at the next session's close);
- the post-release continuation measure (docs/specs/post_release_continuation_spec.md
  §1): direction = the first H4 close after the release minus the price at the
  release; entry at that close; exit at the next session's close (14:00 PT) and,
  as amended, at 13:00 PT of that session. Gross dollars, no costs.
Also the 2026 year-to-date change and the median daily range in percent.
"""
import csv
import math
import os
import statistics
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from oanda_feed import _base_url, _headers  # noqa: E402

NY, PT, UTC = ZoneInfo("America/New_York"), ZoneInfo("America/Los_Angeles"), timezone.utc


def get(gran, frm, to):
    r = requests.get(f"{_base_url()}/v3/instruments/XAU_USD/candles", headers=_headers(), timeout=60,
                     params={"granularity": gran, "price": "M", "from": frm.strftime("%Y-%m-%dT%H:%M:%SZ"),
                             "to": to.strftime("%Y-%m-%dT%H:%M:%SZ")})
    r.raise_for_status()
    out = []
    for c in r.json()["candles"]:
        if c["complete"]:
            t = datetime.strptime(c["time"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=UTC)
            m = c["mid"]
            out.append((t, float(m["o"]), float(m["h"]), float(m["l"]), float(m["c"])))
    return out


def sgn(v):
    return (v > 0) - (v < 0)


def tstat(xs):
    return statistics.fmean(xs) / (statistics.stdev(xs) / math.sqrt(len(xs))) if len(xs) > 1 else float("nan")


def summary(name, xs):
    if not xs:
        return f"{name}: N 0"
    return f"{name}: N {len(xs)}, mean ${statistics.fmean(xs):+.2f}, t {tstat(xs):+.2f}"


def main():
    events = list(csv.DictReader(open(os.path.join(HERE, "us_events_2026.csv"))))
    rows = []
    for e in events:
        hh, mm = map(int, e["time_et"].split(":"))
        t0 = datetime.fromisoformat(e["date"]).replace(hour=hh, minute=mm, tzinfo=NY).astimezone(UTC)
        m5 = get("M5", t0 - timedelta(minutes=10), t0 + timedelta(minutes=35))
        b0 = next((b for b in m5 if b[0] == t0), None)
        if b0 is None:
            print(f"{e['date']} {e['event']}: no M5 candle at the release (market closed); not measured")
            continue
        p0 = b0[1]
        w30 = [b for b in m5 if t0 <= b[0] < t0 + timedelta(minutes=30)]
        dall = get("D", t0 - timedelta(days=5), t0 + timedelta(days=6))
        k = max(i for i, b in enumerate(dall) if b[0] <= t0)
        nxt = dall[k + 1]
        h4 = get("H4", t0 - timedelta(hours=8), t0 + timedelta(hours=12))
        first = next(b for b in h4 if b[0] + timedelta(hours=4) > t0)      # the H4 bar holding the release
        entry_t, entry = first[0] + timedelta(hours=4), first[4]
        d = sgn(entry - p0)
        exit14 = nxt[4]
        close_13 = (nxt[0] + timedelta(days=1)).astimezone(PT).replace(hour=13, minute=0)
        m5x = get("M5", close_13.astimezone(UTC) - timedelta(minutes=5), close_13.astimezone(UTC))
        exit13 = m5x[-1][4] if m5x and m5x[-1][0] + timedelta(minutes=5) == close_13.astimezone(UTC) else None
        weekend = nxt[0].astimezone(PT).weekday() == 6        # next session opens Sunday: the hold spans a weekend
        rows.append({"event": e["event"], "date": e["date"], "p0": p0, "c30": w30[-1][4] - p0,
                     "next": exit14 - p0, "entry_t": entry_t, "entry": entry, "dir": d,
                     "pnl14": d * (exit14 - entry), "pnl13": None if exit13 is None else d * (exit13 - entry),
                     "weekend": weekend})
    print("| release | price at release | 30-min change | next close change | kept | H4 entry (PT) | entry | dir | P&L to 14:00 PT | P&L to 13:00 PT | weekend |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        kept = "kept" if sgn(r["c30"]) == sgn(r["next"]) else "reversed"
        p13 = "n/a" if r["pnl13"] is None else f"{r['pnl13']:+.2f}"
        print(f"| {r['date']} {r['event']} | {r['p0']:.2f} | {r['c30']:+.2f} | {r['next']:+.2f} | {kept} | "
              f"{r['entry_t'].astimezone(PT):%a %H:%M} | {r['entry']:.2f} | {r['dir']:+d} | {r['pnl14']:+.2f} | {p13} | "
              f"{'yes' if r['weekend'] else 'no'} |")
    print()
    for ev in ("FOMC", "CPI", "NFP"):
        g = [r for r in rows if r["event"] == ev]
        print(f"- {ev}: N {len(g)}; 30-min direction kept to the next close {sum(sgn(r['c30']) == sgn(r['next']) for r in g)}")
    print(f"- all: N {len(rows)}; kept {sum(sgn(r['c30']) == sgn(r['next']) for r in rows)}")
    print()
    print("Post-release continuation (gross dollars, no costs):")
    for label, key in (("exit 14:00 PT (the rollover)", "pnl14"), ("exit 13:00 PT", "pnl13")):
        xs = [r[key] for r in rows if r[key] is not None]
        print(f"- {label}: " + summary("pooled", xs) + "; "
              + summary("same-week", [r[key] for r in rows if r[key] is not None and not r["weekend"]]) + "; "
              + summary("weekend holds", [r[key] for r in rows if r[key] is not None and r["weekend"]]))
    year = get("D", datetime(2025, 12, 29, tzinfo=UTC), datetime(2026, 11, 14, tzinfo=UTC))
    y26 = [b for b in year if (b[0] + timedelta(hours=7)).astimezone(NY).year == 2026]
    trs = [100 * max(b[2] - b[3], abs(b[2] - a[4]), abs(b[3] - a[4])) / a[4] for a, b in zip(y26, y26[1:])]
    print()
    print(f"2026 sessions {y26[0][0].isoformat()[:10]} -> {y26[-1][0].isoformat()[:10]}: first open {y26[0][1]:.2f}, "
          f"last close {y26[-1][4]:.2f}, change {100 * (y26[-1][4] / y26[0][1] - 1):+.1f}%; "
          f"high {max(b[2] for b in y26):.2f}, change from the high {100 * (y26[-1][4] / max(b[2] for b in y26) - 1):+.1f}%; "
          f"median daily range {statistics.median(trs):.2f}% of price (N {len(trs)})")


if __name__ == "__main__":
    main()
