"""markup_swings.py — exact swing prices for the weekly hand markup
(foundation/chart_reading_method.md §1-§2). Read-only; prints, writes nothing.

usage: python3 -I markup_swings.py <PAIR>          (run via scripts/reality_run.py)

For M, W, D, H4 and H1 mid candles from OANDA it prints the confirmed swing
highs and lows under the method's fixed rule (a swing high is the highest high
of the k bars on each side; confirmed k bars later), labelled HH/LH/HL/LL
against the previous swing of the same kind, plus ATR(14), the latest
complete candle and the current live mid. Same k every week:
M 2, W 2, D 3, H4 4, H1 5.
"""
import os
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from oanda_feed import _account_id, _base_url, _headers  # noqa: E402

PT = ZoneInfo("America/Los_Angeles")
FRAMES = (("M", 2, 150), ("W", 2, 260), ("D", 3, 320), ("H4", 4, 300), ("H1", 5, 300))
SHOW = {"M": 10, "W": 12, "D": 14, "H4": 14, "H1": 14}


def candles(pair, gran, count):
    r = requests.get(f"{_base_url()}/v3/instruments/{pair}/candles", headers=_headers(), timeout=30,
                     params={"granularity": gran, "count": count, "price": "M"})
    r.raise_for_status()
    out = []
    for c in r.json()["candles"]:
        t = datetime.strptime(c["time"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        m = c["mid"]
        out.append((t, float(m["o"]), float(m["h"]), float(m["l"]), float(m["c"]), c["complete"]))
    return out


def swings(bars, k):
    """Confirmed swings among complete bars: list of (time, 'H'|'L', price)."""
    done = [b for b in bars if b[5]]
    out = []
    for i in range(k, len(done) - k):
        win = done[i - k:i + k + 1]
        if done[i][2] == max(b[2] for b in win) and done[i][2] > max(b[2] for b in win if b is not done[i]) - 1e-12:
            out.append((done[i][0], "H", done[i][2]))
        if done[i][3] == min(b[3] for b in win) and done[i][3] < min(b[3] for b in win if b is not done[i]) + 1e-12:
            out.append((done[i][0], "L", done[i][3]))
    return out


def label(sw):
    last = {}
    res = []
    for t, kind, p in sw:
        prev = last.get(kind)
        if prev is None:
            tag = "  "
        elif kind == "H":
            tag = "HH" if p > prev else "LH"
        else:
            tag = "HL" if p > prev else "LL"
        last[kind] = p
        res.append((t, kind, p, tag))
    return res


def atr(bars, n=14):
    done = [b for b in bars if b[5]]
    trs = [max(done[i][2] - done[i][3], abs(done[i][2] - done[i - 1][4]), abs(done[i][3] - done[i - 1][4]))
           for i in range(1, len(done))]
    a = sum(trs[:n]) / n
    for tr in trs[n:]:
        a = (a * (n - 1) + tr) / n
    return a


def main(pair):
    pip = 0.01 if pair.endswith("JPY") else 0.0001
    acct = _account_id()
    p = requests.get(f"{_base_url()}/v3/accounts/{acct}/pricing", headers=_headers(), timeout=30,
                     params={"instruments": pair})
    p.raise_for_status()
    q = p.json()["prices"][0]
    mid = (float(q["bids"][0]["price"]) + float(q["asks"][0]["price"])) / 2
    qt = datetime.strptime(q["time"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    print(f"{pair} live mid {mid:.5f} at {qt.astimezone(PT):%Y-%m-%d %H:%M %Z} (tradeable: {q.get('tradeable')})\n")
    for gran, k, count in FRAMES:
        bars = candles(pair, gran, count)
        sw = label(swings(bars, k))
        last = [b for b in bars if b[5]][-1]
        cur = bars[-1]
        print(f"## {gran} (k={k}) ATR14 {atr(bars) / pip:.1f} pips; last complete candle "
              f"{last[0].astimezone(PT):%Y-%m-%d %H:%M} O {last[1]} H {last[2]} L {last[3]} C {last[4]}; "
              f"forming candle {'H ' + str(cur[2]) + ' L ' + str(cur[3]) if not cur[5] else '(none)'}")
        hi = max(bars, key=lambda b: b[2])
        lo = min(bars, key=lambda b: b[3])
        print(f"  range of the {len(bars)} candles fetched: high {hi[2]} ({hi[0].astimezone(PT):%Y-%m-%d}), "
              f"low {lo[3]} ({lo[0].astimezone(PT):%Y-%m-%d})")
        for t, kind, price, tag in sw[-SHOW[gran]:]:
            print(f"  {t.astimezone(PT):%Y-%m-%d %H:%M}  swing {'high' if kind == 'H' else 'low '} {price:.5f} {tag}")
        print()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
