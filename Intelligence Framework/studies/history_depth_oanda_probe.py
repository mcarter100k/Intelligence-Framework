"""OANDA depth probe: earliest candle, API limits, and bar timestamps for
non-sealed spans. Keeps TIMESTAMPS ONLY — prices are dropped on receipt.

usage: python3 -I history_depth_oanda_probe.py <env_file> <out_dir> earliest|limits|count

SEALED EXAM guard: any request window intersecting
[2013-12-31T22:00Z, 2021-04-26T00:00Z) is refused before it is sent.
The lower edge is the start of the 17:00-NY session that trades into
2014-01-01, so no bar of the first sealed trading day can be returned.
"""
import csv
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

SEAL_START = datetime(2013, 12, 31, 22, 0, tzinfo=timezone.utc)
SEAL_END = datetime(2021, 4, 26, 0, 0, tzinfo=timezone.utc)
PAIRS = ("GBP_AUD", "GBP_JPY")
GRANS = ("D", "H4", "H1")
# Non-sealed spans. STUDY ends 30 min before SEAL_START; the 2021 USED
# remainder starts at SEAL_END (excludes the ambiguous Sunday-open candle).
SPANS = {
    "STUDY_2005_2013": (datetime(2005, 1, 1, tzinfo=timezone.utc),
                        datetime(2013, 12, 31, 21, 30, tzinfo=timezone.utc)),
    "USED_2021_remainder": (SEAL_END + timedelta(days=1),
                            datetime(2021, 12, 31, 21, 30, tzinfo=timezone.utc)),
}


try:
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    CTX = ssl.create_default_context()


class SealViolation(RuntimeError):
    pass


def guard(frm, to):
    # OANDA returns the candle CONTAINING `from` (observed 2026-10-20: from=
    # 2021-04-26T00:00Z returned the 2021-04-25T21:00Z open), so the low edge
    # keeps a one-day margin past SEAL_END.
    if frm < SEAL_END + timedelta(days=1) and to > SEAL_START:
        raise SealViolation(f"refused: window {frm}..{to} touches the sealed exam")


def load_env(path):
    env = {}
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip("'\"")
    return env


class Client:
    def __init__(self, env):
        self.key = env["OANDA_API_KEY"]
        host = ("https://api-fxpractice.oanda.com"
                if env.get("OANDA_ENVIRONMENT", "live").lower() == "practice"
                else "https://api-fxtrade.oanda.com")
        self.host = host
        self.requests = 0

    def candles(self, pair, params):
        url = (f"{self.host}/v3/instruments/{pair}/candles?"
               + urllib.parse.urlencode(params))
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {self.key}",
            "Accept-Datetime-Format": "RFC3339"})
        self.requests += 1
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
                    return r.status, json.loads(r.read())
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", "replace")[:300]
                if e.code in (429, 500, 502, 503) and attempt < 3:
                    time.sleep(2 * (attempt + 1))
                    continue
                return e.code, {"errorMessage": body}
            except (urllib.error.URLError, TimeoutError):
                if attempt < 3:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000000000Z")


def parse(ts):
    return datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)


def times_only(payload):
    # Prices are discarded here; only time + completeness survive.
    return [(parse(c["time"]), c.get("complete", True))
            for c in payload.get("candles", [])]


def window_times(cl, pair, gran, frm, to):
    guard(frm, to)
    status, payload = cl.candles(pair, {"granularity": gran, "price": "M",
                                        "from": iso(frm), "to": iso(to)})
    if status != 200:
        raise RuntimeError(f"{pair} {gran} {frm}..{to}: HTTP {status} {payload}")
    out = times_only(payload)
    for t, _ in out:
        if SEAL_START <= t < SEAL_END:
            raise SealViolation(f"API returned sealed bar {t}; aborting")
    return out


def earliest(cl, out_dir):
    rows = []
    for pair in PAIRS:
        for gran in GRANS:
            frm = datetime(2000, 1, 1, tzinfo=timezone.utc)
            to = datetime(2005, 1, 1, tzinfo=timezone.utc)
            step = {"D": 3650, "H4": 600, "H1": 150}[gran]
            first = None
            lo = frm
            while lo < to:  # page forward until the first candle appears
                hi = min(lo + timedelta(days=step), to)
                got = window_times(cl, pair, gran, lo, hi)
                if got:
                    first = got[0][0]
                    break
                lo = hi
            if first is None:
                rows.append((pair, gran, "none before 2005-01-01", "", ""))
                continue
            # Control: nothing older. Ask for the window ending AT the first bar.
            older = window_times(cl, pair, gran,
                                 first - timedelta(days=step), first)
            older_n = len([t for t, _ in older if t < first])
            rows.append((pair, gran, first.isoformat(), len(older), older_n))
    with open(os.path.join(out_dir, "earliest.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["pair", "gran", "earliest_utc", "control_returned", "control_older_than_first"])
        w.writerows(rows)
    for r in rows:
        print(*r)


def limits(cl, out_dir):
    res = {}
    # 1. count above 5000
    for n in (5000, 5001):
        st, p = cl.candles("GBP_AUD", {"granularity": "H1", "price": "M", "count": n,
                                       "to": iso(datetime(2026, 9, 1, tzinfo=timezone.utc))})
        res[f"count={n}"] = (st, len(p.get("candles", [])), p.get("errorMessage", "")[:160])
    # 2. from/to window wider than 5000 candles (H1, ~1 year, all USED span)
    frm, to = datetime(2022, 1, 1, tzinfo=timezone.utc), datetime(2023, 1, 1, tzinfo=timezone.utc)
    guard(frm, to)
    st, p = cl.candles("GBP_AUD", {"granularity": "H1", "price": "M",
                                   "from": iso(frm), "to": iso(to)})
    res["from/to ~6200 H1"] = (st, len(p.get("candles", [])), p.get("errorMessage", "")[:160])
    # 3. burst: 30 back-to-back small requests, record any non-200
    codes = []
    t0 = time.monotonic()
    for _ in range(30):
        st, _p = cl.candles("GBP_AUD", {"granularity": "D", "price": "M", "count": 1})
        codes.append(st)
    res["burst30"] = (sorted(set(codes)), round(time.monotonic() - t0, 2), "")
    with open(os.path.join(out_dir, "limits.json"), "w") as fh:
        json.dump(res, fh, indent=1)
    for k, v in res.items():
        print(k, v)


def count(cl, out_dir):
    only = sys.argv[4] if len(sys.argv) > 4 else None
    for span, (s, e) in SPANS.items():
        if only and span != only:
            continue
        for pair in PAIRS:
            for gran in GRANS:
                times = []
                lo = s
                while lo < e:
                    hi = min(lo + timedelta(days=31), e)
                    times += window_times(cl, pair, gran, lo, hi)
                    lo = hi
                    time.sleep(0.05)
                seen = sorted(set(times))
                path = os.path.join(out_dir, f"times_{span}_{pair}_{gran}.csv")
                with open(path, "w", newline="") as fh:
                    w = csv.writer(fh)
                    w.writerow(["time_utc", "complete"])
                    for t, c in seen:
                        w.writerow([t.isoformat(), c])
                print(span, pair, gran, len(seen), seen[0][0] if seen else "-",
                      seen[-1][0] if seen else "-")


def main():
    env_file, out_dir, mode = sys.argv[1:4]
    cl = Client(load_env(env_file))
    print("host:", cl.host)
    {"earliest": earliest, "limits": limits, "count": count}[mode](cl, out_dir)
    print("requests sent:", cl.requests)


if __name__ == "__main__":
    main()
