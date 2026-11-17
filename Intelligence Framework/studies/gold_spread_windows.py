"""Gold's quoted spread by Pacific clock window, from OANDA bid/ask M5 candles
(Sep 14 - Nov 13, 2026). Spread = ask minus bid at each 5-minute candle's close
and at its open. Read-only, prints only."""
import os, statistics, sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import requests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from oanda_feed import _base_url, _headers
PT, UTC = ZoneInfo("America/Los_Angeles"), timezone.utc
start, end = datetime(2026, 9, 14, tzinfo=UTC), datetime(2026, 11, 14, tzinfo=UTC)
rows, lo = [], start
while lo < end:
    hi = min(lo + timedelta(days=14), end)
    r = requests.get(f"{_base_url()}/v3/instruments/XAU_USD/candles", headers=_headers(), timeout=60,
                     params={"granularity": "M5", "price": "BA", "from": lo.strftime("%Y-%m-%dT%H:%M:%SZ"),
                             "to": hi.strftime("%Y-%m-%dT%H:%M:%SZ")})
    r.raise_for_status()
    for c in r.json()["candles"]:
        if not c["complete"]:
            continue
        t = datetime.strptime(c["time"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=UTC).astimezone(PT)
        rows.append((t, float(c["ask"]["c"]) - float(c["bid"]["c"]), float(c["ask"]["o"]) - float(c["bid"]["o"])))
    lo = hi
print(f"M5 bid/ask candles: {len(rows)}, {rows[0][0]:%Y-%m-%d %H:%M} -> {rows[-1][0]:%Y-%m-%d %H:%M} PT")
def win(name, f):
    xs = sorted(x for t, x, _ in rows if f(t)); os_ = sorted(o for t, _, o in rows if f(t))
    if not xs:
        print(f"{name}: no candles"); return
    q = statistics.quantiles(xs, n=10)
    print(f"{name}: n {len(xs)}; spread at close median {statistics.median(xs):.3f}, p90 {q[8]:.3f}, max {xs[-1]:.3f}; "
          f"at open median {statistics.median(os_):.3f}")
win("mid-session 06:00-12:00 PT", lambda t: 6 <= t.hour < 12 and t.weekday() < 5)
win("12:00-13:00 PT", lambda t: t.hour == 12 and t.weekday() < 5)
win("13:00-14:00 PT", lambda t: t.hour == 13 and t.weekday() < 5)
win("  13:00-13:30 PT", lambda t: t.hour == 13 and t.minute < 30 and t.weekday() < 5)
win("  13:30-13:55 PT", lambda t: t.hour == 13 and t.minute >= 30 and t.weekday() < 5)
win("  the 12:55 candle (closes 13:00 PT)", lambda t: t.hour == 12 and t.minute == 55 and t.weekday() < 5)
win("  the 13:55 candle (closes 14:00 PT)", lambda t: t.hour == 13 and t.minute == 55 and t.weekday() < 5)
win("14:00-15:00 PT", lambda t: t.hour == 14)
win("15:00-16:00 PT (reopen)", lambda t: t.hour == 15)
for h in range(24):
    xs = [x for t, x, _ in rows if t.hour == h]
    if xs: print(f"hour {h:02d} PT: n {len(xs)} median {statistics.median(xs):.3f}")
