"""Which sub-hourly XAU_USD candles does OANDA serve? Counts only, plus a feed check.

Every request is a bounded from/to window inside STUDY (2005-2013) or USED/FORWARD
(from 2021-04-27), passed through history_study_gate_s3.guard, so no sealed-block
candle can come back; any that did aborts the run. Prints counts, coverage ratios
against the archive's H1 bars, and |difference| in dollars between aggregated
sub-hourly bars and the archive H1 bar for the same hour. No price levels.
usage: gold_subhourly_probe.py <studies_dir> <archive_dir>
"""
import csv, hashlib, os, sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

sys.path.insert(0, sys.argv[1])
import history_study_gate_s3 as G  # noqa: E402
P = G.P
UTC = timezone.utc
ARCH = os.path.join(sys.argv[2], "XAU_USD_H1.csv")
PIN = "eabec6652e055540b256aa743971a1a5aa5cbb459e94b4887da6f28b8e02a4be"
got = hashlib.sha256(open(ARCH, "rb").read()).hexdigest()
assert got == PIN, f"H1 archive hash {got} != pin"
h1 = {}
for r in csv.DictReader(open(ARCH)):
    t = datetime.fromisoformat(r["time_utc"])
    if G.BLOCK_START <= t < G.BLOCK_END:
        raise G.Blocked("archive row in sealed block")
    h1[t] = tuple(float(r[k]) for k in "ohlc")
cl = P.Client(dict(os.environ))
STEP = {"M30": 2, "M15": 4, "M5": 12}


def fetch(gran, lo, hi):
    out = {}
    while lo < hi:
        nxt = min(lo + timedelta(days=7), hi)
        out.update(fetch1(gran, lo, nxt))
        lo = nxt
    return out


def fetch1(gran, lo, hi):
    G.guard(lo, hi)
    st, p = cl.candles("XAU_USD", {"granularity": gran, "price": "M", "from": P.iso(lo), "to": P.iso(hi)})
    if st != 200:
        raise RuntimeError(f"{gran} {lo:%Y-%m-%d}: HTTP {st} {p}")
    out = {}
    for c in p.get("candles", []):
        t = P.parse(c["time"])
        if G.BLOCK_START <= t < G.BLOCK_END:
            raise G.Blocked(f"API returned blocked candle {t}; aborting")
        if c.get("complete", True):
            out[t] = tuple(float(c["mid"][k]) for k in "ohlc")
    return out


# 1. earliest M30 candle, stepping 14-day windows from 2005-01-03
lo, first = datetime(2005, 1, 3, tzinfo=UTC), None
while first is None and lo < datetime(2007, 1, 1, tzinfo=UTC):
    got = fetch("M30", lo, lo + timedelta(days=14))
    if got:
        first = min(got)
    else:
        lo += timedelta(days=14)
print(f"earliest M30 candle: {first.isoformat() if first else 'none before 2007'}")
for g in ("M15", "M5"):
    w = fetch(g, lo, lo + timedelta(days=14))
    print(f"earliest {g} candle in the same window: {min(w).isoformat() if w else 'none'}")
print(f"earliest archive H1 bar: {min(h1).isoformat()}")

# 2. sampled windows: coverage vs archive H1 and OHLC agreement
wins = []
for y in list(range(2006, 2014)) + list(range(2021, 2027)):
    for m in (1, 4, 7, 10):
        a = datetime(y, m, 15, tzinfo=UTC)
        b = a + timedelta(days=14)
        try:
            G.guard(a, b)
        except G.Blocked:
            continue
        if b > datetime(2026, 11, 14, tzinfo=UTC):
            continue
        wins.append((a, b))
wins.append((datetime(2013, 12, 9, tzinfo=UTC), datetime(2013, 12, 27, tzinfo=UTC)))
wins.append((datetime(2021, 4, 28, tzinfo=UTC), datetime(2021, 5, 12, tzinfo=UTC)))
stats = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0, 0.0, []]))  # n_sub, n_h1, full_hours, cmp, maxdiff, diffs
for a, b in sorted(wins):
    era = "STUDY" if b <= G.BLOCK_START else "USED/FWD"
    arch = {t: v for t, v in h1.items() if a <= t < b - timedelta(hours=1)}
    for g, k in STEP.items():
        sub = fetch(g, a, b)
        s = stats[g][era]
        s[0] += sum(1 for t in sub if a <= t < b - timedelta(hours=1))
        s[1] += len(arch)
        hours = defaultdict(list)
        for t, v in sub.items():
            hours[t.replace(minute=0)].append((t, v))
        for hr, v in arch.items():
            bars = sorted(hours.get(hr, []))
            if len(bars) != k:
                continue
            s[2] += 1
            agg = (bars[0][1][0], max(x[1][1] for x in bars), min(x[1][2] for x in bars), bars[-1][1][3])
            d = max(abs(x - y) for x, y in zip(agg, v))
            s[3] += 1
            s[4] = max(s[4], d)
            s[5].append(d)
print(f"\nsampled windows: {len(wins)} (14-day, quarterly, plus STUDY end and USED start); requests {cl.requests}")
for g in STEP:
    for era, s in stats[g].items():
        ds = sorted(s[5])
        within = sum(1 for d in ds if d <= 0.05)
        print(f"{g} {era}: sub-bars {s[0]} vs archive H1 {s[1]} (ratio {s[0] / max(s[1], 1):.2f}, expect {STEP[g]}); "
              f"hours fully covered {s[2]} of {s[1]} ({100 * s[2] / max(s[1], 1):.1f}%); "
              f"aggregated vs archive OHLC: median |d| ${ds[len(ds) // 2] if ds else float('nan'):.3f}, "
              f"max ${s[4]:.3f}, within $0.05: {100 * within / max(len(ds), 1):.1f}%")
# per-year coverage line for the 5-minute series
print("\nM5 per-window coverage (sub-bars / (12 x archive H1)):")
for a, b in sorted(wins):
    arch = sum(1 for t in h1 if a <= t < b - timedelta(hours=1))
    sub = fetch("M5", a, b)
    n = sum(1 for t in sub if a <= t < b - timedelta(hours=1))
    print(f"  {a:%Y-%m-%d}: {n}/{12 * arch} = {n / max(12 * arch, 1):.3f}")
print(f"requests total {cl.requests}")
