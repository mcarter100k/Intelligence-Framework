"""Read-only: does a recent Monday D1 candle open at Sunday 17:00 New York and
contain the week's first quote? Prints times and pip differences only.

usage: python3 -I history_monday_open_check.py <env_file> <json_out> <monday> [<monday> ...]
"""
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import history_depth_oanda_probe as P  # noqa: E402

NY, PT, UTC = ZoneInfo("America/New_York"), ZoneInfo("America/Los_Angeles"), timezone.utc
PIP = {"GBP_AUD": 0.0001, "GBP_JPY": 0.01}


def ny(d, h):
    return datetime(d.year, d.month, d.day, h, tzinfo=NY).astimezone(UTC)


def candles(cl, pair, gran, frm, to):
    st, p = cl.candles(pair, {"granularity": gran, "price": "M", "from": P.iso(frm), "to": P.iso(to)})
    if st != 200:
        raise RuntimeError(f"{pair} {gran} HTTP {st} {p}")
    return [(P.parse(c["time"]), tuple(float(c["mid"][k]) for k in "ohlc"))
            for c in p["candles"] if c.get("complete", True)]


def pt(t):
    return t.astimezone(PT).strftime("%a %Y-%m-%d %H:%M %Z")


def main():
    env_file, out, *mondays = sys.argv[1:]
    cl = P.Client(P.load_env(env_file))
    res = []
    for ms in mondays:
        m = date.fromisoformat(ms)
        assert m.weekday() == 0
        fri, sun = m - timedelta(days=3), m - timedelta(days=1)
        sess_start, sess_end, fri_close = ny(sun, 17), ny(m, 17), ny(fri, 17)
        for pair in ("GBP_AUD", "GBP_JPY"):
            pip = PIP[pair]
            d1 = candles(cl, pair, "D", ny(fri - timedelta(days=1), 12), ny(m + timedelta(days=1), 12))
            mon = [c for c in d1 if (c[0].astimezone(NY) + timedelta(hours=7)).date() == m]
            assert len(mon) == 1, (pair, ms, len(mon))
            t0, (o, h, l, c) = mon[0]
            m1 = candles(cl, pair, "M1", ny(fri, 16), sess_end)
            weekend = [x for x in m1 if fri_close <= x[0] < sess_start]
            sess = [x for x in m1 if sess_start <= x[0] < sess_end]
            first = sess[0]
            later = sess[60]  # control: a minute an hour later
            row = {
                "pair": pair, "monday": ms,
                "d1_open_time_pt": pt(t0), "d1_open_time_ny": t0.astimezone(NY).strftime("%a %H:%M"),
                "d1_opens_sunday_17_ny": t0 == sess_start,
                "m1_candles_fri17_to_sun17_ny": len(weekend),
                "last_m1_before_weekend_pt": pt([x for x in m1 if x[0] < fri_close][-1][0]),
                "first_m1_of_week_pt": pt(first[0]),
                "m1_in_session": len(sess),
                "open_vs_first_m1_pips": round(abs(o - first[1][0]) / pip, 3),
                "high_vs_m1_max_pips": round(abs(h - max(x[1][1] for x in sess)) / pip, 3),
                "low_vs_m1_min_pips": round(abs(l - min(x[1][2] for x in sess)) / pip, 3),
                "close_vs_last_m1_pips": round(abs(c - sess[-1][1][3]) / pip, 3),
                "control_open_vs_m1_one_hour_later_pips": round(abs(o - later[1][0]) / pip, 3),
            }
            res.append(row)
            print(json.dumps(row))
    with open(out, "w") as fh:
        json.dump(res, fh, indent=1)
    print("requests", cl.requests)


if __name__ == "__main__":
    main()
