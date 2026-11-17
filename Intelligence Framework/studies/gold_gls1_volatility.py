"""GLS-1 ruling H3 input (2026-11-17), 2021-2026 USED only. Report-only.
No trade outcome is computed.

usage: python3 -I gold_gls1_volatility.py <archive_dir> <subhourly_dir>

Volatility at each 4-hour setup (the G1 setups): the daily ATR known at the
setup (first_pullback_study.bar_context), in dollars and as a share of the
setup's close. Prints tercile cut-offs for both, how many setups fall in each
tercile by year, and, as cost arithmetic only, the spread (that year's hour
median) as a share of every structure stop on each timeframe, by tercile of
daily ATR / price at that break.
"""
import bisect
import os
import statistics
import sys
from collections import Counter, defaultdict
from datetime import timedelta
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gold_gls1_inputs as I  # noqa: E402
from gold_move_size_study import load  # noqa: E402
from gold_pullback_depth_study import FILES, era_bars  # noqa: E402

PT = ZoneInfo("America/Los_Angeles")
SPAN = {"H4": timedelta(hours=4), "M30": timedelta(minutes=30), "M15": timedelta(minutes=15),
        "M5": timedelta(minutes=5)}


def terciles(xs):
    xs = sorted(xs)
    return xs[len(xs) // 3], xs[2 * len(xs) // 3]


def tercile(x, cuts):
    return "low" if x < cuts[0] else "mid" if x < cuts[1] else "high"


def main(arch, sub_dir):
    rows = {f: load(os.path.join(arch, name), sha_) for f, (name, sha_) in FILES.items()}
    bars, atr, _ = era_bars(rows["D"]["USED"], rows["H4"]["USED"])
    opens, C = bars["opens"], bars["C"]
    setups = [(j, side) for j, side, _ in I.breaks_and_stops(bars["H"], bars["L"], C) if atr[j] is not None]
    usd = [atr[j] for j, _ in setups]
    pct = [100 * atr[j] / C[j] for j, _ in setups]
    cu, cp = terciles(usd), terciles(pct)
    print("# GLS-1 H3 input: volatility at the 4-hour setups (2021-2026; no outcome)\n")
    print(f"setups with a daily ATR: {len(setups)}")
    print(f"daily ATR in dollars: terciles cut at ${cu[0]:.2f} / ${cu[1]:.2f}; {I.quart(usd)}")
    print(f"daily ATR / price:    terciles cut at {cp[0]:.3f}% / {cp[1]:.3f}%; {I.quart(pct, '{:.3f}%')}")
    for lab, vals, cuts in (("dollars", usd, cu), ("share of price", pct, cp)):
        by = defaultdict(Counter)
        for (j, side), v in zip(setups, vals):
            by[opens[j].year][tercile(v, cuts)] += 1
        print(f"\nsetups by year and tercile ({lab}): low / mid / high")
        for y in sorted(by):
            print(f"  {y}: {by[y]['low']} / {by[y]['mid']} / {by[y]['high']}")
        sides = Counter((tercile(v, cuts), s) for (j, s), v in zip(setups, vals))
        print("  long / short per tercile: " + "; ".join(
            f"{t} {sides[(t, 1)]} / {sides[(t, -1)]}" for t in ("low", "mid", "high")))

    # cost arithmetic by tercile of daily ATR / price at each break
    mid, ba, _ = I.load_sub(sub_dir)
    yh = defaultdict(list)
    for t, s, _ in ba:
        tp = t.astimezone(PT)
        yh[(tp.year, tp.hour)].append(s)
    yhmed = {k: statistics.median(v) for k, v in yh.items() if v}
    d_ix = [t + SPAN["H4"] for t in opens]
    frames = {"H4": (opens, bars["H"], bars["L"], C)}
    for g in ("M30", "M15", "M5"):
        frames[g] = (mid[g]["t"], mid[g]["H"], mid[g]["L"], mid[g]["C"])
    print("\nspread / structure stop (that year's hour median), median, by tercile of daily ATR / price at the break:")
    for g, (ts, H, L, Cg) in frames.items():
        cells = defaultdict(list)
        for j, _, d in I.breaks_and_stops(H, L, Cg):
            te = ts[j] + SPAN[g]
            k = bisect.bisect_right(d_ix, te) - 1            # last 4-hour bar closed by the break
            if k < 0 or atr[k] is None or d <= 0:
                continue
            tp = te.astimezone(PT)
            if tp.hour == 14:
                tp = tp.replace(hour=15)
            if (tp.year, tp.hour) not in yhmed:
                continue
            cells[tercile(100 * atr[k] / Cg[j], cp)].append(100 * yhmed[(tp.year, tp.hour)] / d)
        print(f"- {g}: " + "; ".join(f"{t} {statistics.median(cells[t]):.1f}% (n {len(cells[t])})"
                                     for t in ("low", "mid", "high")))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
