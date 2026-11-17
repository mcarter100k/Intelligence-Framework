"""GLS-1 inputs fixed before any outcome is measured (rulings F3, F4, F6,
2026-11-17). 2021-2026 USED data only. Report-only, prints only.

usage: python3 -I gold_gls1_inputs.py <archive_dir> <subhourly_dir>

1. F3 scale ratio: daily ATR (the 14-session convention, sessions before the
   bar's own) divided by the 4-hour bar's trailing median range (the prior 14
   bars' high minus low). The screen's daily-ATR thresholds on 4-hour bars
   become multiples of a timeframe's own median range through this measured
   ratio, not through a square-root-of-time assumption.
2. F4 pullback length: R48's legs (first_pullback_study.find_entries,
   unchanged), from the impulse's extreme bar to the bar that touched the
   level, counted in actual 30/15/5-minute bars present in the fetched data.
3. F6 spread: ask minus bid at each 5-minute close, median and p90 by Pacific
   hour, and by year.
4. Cost share: structure stops on daily, 4-hour, 30/15/5-minute bars for
   every structure break (GLS-1 §3 and §4.1 rules), and the measured spread at
   the entry's hour as a share of each stop.
None of these is an outcome: each is known at or before the bar it describes,
except item 2, which is a pullback's duration (descriptive, 2021-2026 only).
"""
import bisect
import csv
import hashlib
import json
import os
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import first_pullback_study as FP  # noqa: E402  R48's detector, unchanged
from gold_move_size_study import load  # noqa: E402  hash- and exam-checked loader
from gold_pullback_depth_study import FILES, era_bars, side_arrays  # noqa: E402

PT = ZoneInfo("America/Los_Angeles")
K = 4                      # swing rule, both sides (GLS-1 §3)
MED_BARS = 14              # trailing window for a timeframe's median range (F3)
LEVELS = (0.382, 0.5, 0.618)
SUB = {"M30": 30, "M15": 15, "M5": 5}


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))]


def quart(xs, fmt="{:.2f}"):
    if not xs:
        return "n 0"
    return (f"n {len(xs)}; p25 {fmt.format(q(xs, .25))}, median {fmt.format(statistics.median(xs))}, "
            f"p75 {fmt.format(q(xs, .75))}, p90 {fmt.format(q(xs, .9))}")


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def load_sub(sub_dir):
    hashes = json.load(open(os.path.join(sub_dir, "data_hashes.json")))
    for name, h in hashes.items():
        if sha(os.path.join(sub_dir, name)) != h:
            raise SystemExit(f"{name}: hash mismatch")
    mid = {}
    for g in SUB:
        rows = list(csv.DictReader(open(os.path.join(sub_dir, f"XAU_USD_{g}_USED.csv"))))
        mid[g] = {"t": [datetime.fromisoformat(r["time_utc"]) for r in rows],
                  **{k.upper(): [float(r[k]) for r in rows] for k in "ohlc"}}
    ba = [(datetime.fromisoformat(r["time_utc"]), float(r["ask_c"]) - float(r["bid_c"]),
           (float(r["ask_c"]) + float(r["bid_c"])) / 2)
          for r in csv.DictReader(open(os.path.join(sub_dir, "XAU_USD_M5_BA_USED.csv")))]
    return mid, ba, hashes


def swings(H, L, k=K):
    """(index, confirmed-at index) of swing highs and lows: strictly beyond k bars each side."""
    hs, ls = [], []
    for i in range(k, len(H) - k):
        w = [x for x in range(i - k, i + k + 1) if x != i]
        if all(H[i] > H[x] for x in w):
            hs.append(i)
        if all(L[i] < L[x] for x in w):
            ls.append(i)
    return hs, ls


def breaks_and_stops(H, L, C):
    """GLS-1 §4.1: long entry = first close above the latest confirmed swing high
    (one per level); stop = the latest confirmed swing low below the entry.
    Shorts mirrored. Returns [(entry bar, side, stop distance)]."""
    out = []
    for side in (1, -1):
        Hx, Lx, Cx = (H, L, C) if side == 1 else ([-x for x in L], [-x for x in H], [-x for x in C])
        hs, ls = swings(Hx, Lx)
        conf_h = [s + K for s in hs]
        conf_l = [s + K for s in ls]
        used = set()
        for j in range(len(Cx)):
            a = bisect.bisect_left(conf_h, j) - 1          # confirmed at a close before bar j
            if a < 0 or hs[a] in used or Cx[j] <= Hx[hs[a]]:
                continue
            used.add(hs[a])
            b = bisect.bisect_left(conf_l, j + 1) - 1      # confirmed by bar j's close
            while b >= 0 and Lx[ls[b]] >= Cx[j]:
                b -= 1
            if b >= 0:
                out.append((j, side, Cx[j] - Lx[ls[b]]))
    return out


def main(arch, sub_dir):
    rows = {f: load(os.path.join(arch, name), sha_) for f, (name, sha_) in FILES.items()}
    bars, atr, trend = era_bars(rows["D"]["USED"], rows["H4"]["USED"])
    H4o, H4h, H4l = bars["opens"], bars["H"], bars["L"]
    print("# GLS-1 inputs (2021-2026 USED only; no outcome measured)\n")

    # 1. F3 ratio
    rho, med_h4 = [], [None] * len(H4h)
    for i in range(MED_BARS, len(H4h)):
        med_h4[i] = statistics.median(H4h[x] - H4l[x] for x in range(i - MED_BARS, i))
        if atr[i] is not None and med_h4[i] > 0:
            rho.append(atr[i] / med_h4[i])
    r = statistics.median(rho)
    print("## 1. F3: daily ATR / 4-hour trailing median range")
    print(f"- {quart(rho, '{:.3f}')}; p10 {q(rho, .1):.3f}")
    print(f"- screen thresholds as multiples of a timeframe's own median range (x {r:.3f}): "
          f"0.15 -> {0.15 * r:.3f}; 0.25 -> {0.25 * r:.3f}; 0.5 -> {0.5 * r:.3f}")
    print(f"- for comparison, the rejected square-root-of-six conversion gave 0.25 -> 0.612, 0.5 -> 1.225 "
          f"(in mean true range, not median range)\n")

    mid, ba, hashes = load_sub(sub_dir)
    print("## data files (sha256)")
    for n, h in sorted(hashes.items()):
        print(f"- {n} {h}")
    print()

    # 2. F4 pullback length
    print("## 2. F4: pullback length, R48 legs (impulse extreme bar open -> touch bar close)")
    for lvl in LEVELS:
        lens = defaultdict(list)
        for side in (1, -1):
            O, H, L, tr = side_arrays(bars, trend, side)
            en, _ = FP.find_entries(O, H, L, atr, tr, lvl, use_trend=False)
            for e in en:
                a, t = e["anchor_bar"], e["bar"]
                seg = range(a + 1, t) if t > a + 1 else range(a + 1, t + 1)
                b = max(seg, key=lambda x: (H[x], -x))
                lo_t, hi_t = H4o[b], H4o[t] + timedelta(hours=4)
                lens["H4"].append(t - b + 1)
                for g in SUB:
                    ts = mid[g]["t"]
                    lens[g].append(bisect.bisect_left(ts, hi_t) - bisect.bisect_left(ts, lo_t))
        print(f"- {lvl:.1%} ({len(lens['H4'])} legs, rallies and falls together):")
        for g in ("H4", "M30", "M15", "M5"):
            print(f"    {g}: {quart(lens[g], '{:.0f}')}")
    print()

    # 3. F6 spread by Pacific hour
    print("## 3. F6: spread (ask - bid at each 5-minute close), 2021-2026")
    byh, byy, byyh, pct = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
    for t, s, m in ba:
        tp = t.astimezone(PT)
        byh[tp.hour].append(s)
        byy[tp.year].append(s)
        byyh[(tp.year, tp.hour)].append(s)
        pct[tp.year].append(100 * s / m)
    allsp = [s for _, s, _ in ba]
    print(f"- all bars: n {len(allsp)}; median ${statistics.median(allsp):.3f}, p90 ${q(allsp, .9):.3f}")
    print("- by Pacific hour (hour: n, median, p90):")
    for h in range(24):
        if byh[h]:
            print(f"    {h:02d}:00  n {len(byh[h])}  median ${statistics.median(byh[h]):.3f}  p90 ${q(byh[h], .9):.3f}")
        else:
            print(f"    {h:02d}:00  no candles")
    print("- by year: " + "; ".join(f"{y} median ${statistics.median(v):.3f} p90 ${q(v, .9):.3f}"
                                    for y, v in sorted(byy.items())))
    print("- by year, as a share of price: " + "; ".join(f"{y} median {statistics.median(v):.4f}% p90 {q(v, .9):.4f}%"
                                                     for y, v in sorted(pct.items())))
    print("- by year and Pacific hour, median (p90) - hours 06, 09, 12, 13, 15, 18:")
    for y in sorted(byy):
        print(f"    {y}: " + "  ".join(f"{h:02d} ${statistics.median(byyh[(y, h)]):.3f} (${q(byyh[(y, h)], .9):.3f})"
                                     for h in (6, 9, 12, 13, 15, 18) if byyh[(y, h)]))
    hmed = {h: statistics.median(v) for h, v in byh.items() if v}
    hp90 = {h: q(v, .9) for h, v in byh.items() if v}
    yhmed = {k: statistics.median(v) for k, v in byyh.items() if v}
    yhp90 = {k: q(v, .9) for k, v in byyh.items() if v}
    print()

    # 4. structure stops and cost share
    print("## 4. Structure stops at every structure break, and spread as a share of the stop")
    d = rows["D"]["USED"]
    frames = {"D": ([datetime.fromisoformat(x[0]) for x in d], [x[2] for x in d], [x[3] for x in d], [x[4] for x in d]),
              "H4": (H4o, H4h, H4l, bars["C"])}
    for g in SUB:
        frames[g] = (mid[g]["t"], mid[g]["H"], mid[g]["L"], mid[g]["C"])
    span = {"D": timedelta(days=1), "H4": timedelta(hours=4), "M30": timedelta(minutes=30),
            "M15": timedelta(minutes=15), "M5": timedelta(minutes=5)}
    for g in ("D", "H4", "M30", "M15", "M5"):
        ts, H, L, C = frames[g]
        br = breaks_and_stops(H, L, C)
        stops = [s for _, _, s in br]
        shr_med, shr_p90, shr_ym, shr_y90, moved = [], [], [], [], 0
        for j, _, s in br:
            tp = (ts[j] + span[g]).astimezone(PT)          # the entry is at the bar's close
            if tp.hour == 14:                              # the daily break: first quote is the reopen
                tp, moved = tp.replace(hour=15), moved + 1
            if s > 0 and (tp.year, tp.hour) in yhmed:
                shr_med.append(100 * hmed[tp.hour] / s)
                shr_p90.append(100 * hp90[tp.hour] / s)
                shr_ym.append(100 * yhmed[(tp.year, tp.hour)] / s)
                shr_y90.append(100 * yhp90[(tp.year, tp.hour)] / s)
        print(f"- {g}: breaks {len(br)}; stop ${quart(stops)}; entries in the 2-3 PM PT break priced at the reopen: {moved}")
        print(f"    spread / stop, hour's median (all years):     {quart(shr_med, '{:.1f}%')}")
        print(f"    spread / stop, hour's p90 (all years):        {quart(shr_p90, '{:.1f}%')}")
        print(f"    spread / stop, that year's hour median:       {quart(shr_ym, '{:.1f}%')}")
        print(f"    spread / stop, that year's hour p90:          {quart(shr_y90, '{:.1f}%')}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
