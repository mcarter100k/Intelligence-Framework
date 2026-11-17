"""GLS-1 inputs for rulings G2 and G4 (2026-11-17), 2021-2026 USED only.
Report-only, prints only. No trade outcome (R) is computed.

usage: python3 -I gold_gls1_window_financing.py <archive_dir> <subhourly_dir> <fred_DFEDTARU.csv>

G2: for every 4-hour structure break (the G1 setup), the time from the setup
    to the first valid 30/15/5-minute entry: the first structure break on that
    timeframe, in the setup's direction, whose swing high was confirmed after
    the setup, before the 4-hour structure stop is touched (checked on 5-minute
    bars) and within 10 sessions. Time is counted in 4-hour bars of trading
    time. Prints the distribution, the p75 window, and the missed rates.
G4: financing as a share of the structure stop, for every structure break on
    each timeframe, held to the close of the session h = 1, 2, 5, 10 after the
    entry's session, by year and side. GNC-1's convention (longs pay the Fed
    upper bound + 2.5% a year, shorts pay 2.5%) and a labelled secondary in
    which shorts receive the upper bound - 2.5%. Actual/365, priced at the
    entry date's rate. Neither is from a broker.
G3: spread and stop as shares of price, by year, to check whether the cost
    share of a stop is roughly constant across the span.
"""
import bisect
import csv
import hashlib
import os
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gold_gls1_inputs as I  # noqa: E402  swings, structure breaks, data loading
from gold_move_size_study import load  # noqa: E402
from gold_pullback_depth_study import FILES, era_bars  # noqa: E402
from gold_rule_costs import held_nights  # noqa: E402

NY, PT = ZoneInfo("America/New_York"), ZoneInfo("America/Los_Angeles")
FRED_PIN = "8bf90ca4b8af7803315cec97a19bc1547e3369212d5dadcb01f4021eda4e8080"
MARKUP = 2.5
MAX_H4 = 60                          # 10 sessions of 4-hour bars
HOLDS = (1, 2, 5, 10)
SPAN = {"M30": timedelta(minutes=30), "M15": timedelta(minutes=15), "M5": timedelta(minutes=5),
        "H4": timedelta(hours=4), "D": timedelta(days=1)}


def session_day(t):
    return (t.astimezone(NY) + timedelta(hours=7)).date()


def session_close(t, h):
    """17:00 New York at the close of the h-th weekday session after t's session."""
    d = session_day(t)
    while h:
        d += timedelta(days=1)
        if d.weekday() < 5:
            h -= 1
    return datetime(d.year, d.month, d.day, 17, 0, tzinfo=NY)


def rates(path):
    if hashlib.sha256(open(path, "rb").read()).hexdigest() != FRED_PIN:
        raise SystemExit("fred_DFEDTARU.csv is not the pinned file")
    out = [(datetime.fromisoformat(d).date(), float(v)) for d, v in csv.reader(open(path))
           if d[:1].isdigit() and v not in (".", "")]
    return [d for d, _ in out], [v for _, v in out]


def rate_on(rt, day):
    return rt[1][bisect.bisect_right(rt[0], day) - 1]


def breaks_with_levels(H, L, C):
    """As gold_gls1_inputs.breaks_and_stops, plus the bar at which the broken
    swing high was confirmed: [(entry bar, side, stop distance, confirmed bar)]."""
    out = []
    for side in (1, -1):
        Hx, Lx, Cx = (H, L, C) if side == 1 else ([-x for x in L], [-x for x in H], [-x for x in C])
        hs, ls = I.swings(Hx, Lx)
        conf_h, conf_l = [s + I.K for s in hs], [s + I.K for s in ls]
        used = set()
        for j in range(len(Cx)):
            a = bisect.bisect_left(conf_h, j) - 1
            if a < 0 or hs[a] in used or Cx[j] <= Hx[hs[a]]:
                continue
            used.add(hs[a])
            b = bisect.bisect_left(conf_l, j + 1) - 1
            while b >= 0 and Lx[ls[b]] >= Cx[j]:
                b -= 1
            if b >= 0:
                out.append((j, side, Cx[j] - Lx[ls[b]], conf_h[a]))
    return out


def first_entry(setup_close, side, stop_px, tf, m5, deadline):
    """G2: the first valid entry on one timeframe. tf = (bar open times, bar length,
    {side: [(entry bar, bar where its swing high was confirmed)] sorted}).
    Returns (entry close time, entry bar) or (None, reason)."""
    ts, span, by_side = tf
    cands = by_side[side]
    k = bisect.bisect_left([j for j, _ in cands], bisect.bisect_left(ts, setup_close - span + timedelta(seconds=1)))
    for j, conf in cands[k:]:
        close_t = ts[j] + span
        if close_t <= setup_close or ts[conf] + span <= setup_close:   # level confirmed before the setup
            continue
        if close_t > deadline:
            return None, "none within 10 sessions"
        if stop_touched(m5, side, stop_px, setup_close, close_t):
            return None, "4-hour stop touched first"
        return close_t, j
    return None, "none within 10 sessions"


def stop_touched(m5, side, stop_px, t_from, t_to):
    """Any 5-minute bar opening in [t_from, t_to) at or beyond the 4-hour stop."""
    ts, lo, hi = m5
    a, b = bisect.bisect_left(ts, t_from), bisect.bisect_left(ts, t_to)
    if side == 1:
        return any(lo[k] <= stop_px for k in range(a, b))
    return any(hi[k] >= stop_px for k in range(a, b))


def q(xs, p):
    return I.q(xs, p)


def main(arch, sub_dir, fred):
    rows = {f: load(os.path.join(arch, name), sha_) for f, (name, sha_) in FILES.items()}
    bars, atr, _ = era_bars(rows["D"]["USED"], rows["H4"]["USED"])
    mid, ba, _ = I.load_sub(sub_dir)
    rt = rates(fred)
    print("# GLS-1 inputs for G2 and G4 (2021-2026 USED only; no trade outcome computed)\n")
    span_rates = [v for d, v in zip(*rt) if datetime(2021, 4, 27).date() <= d <= datetime(2026, 9, 9).date()]
    print(f"Fed upper bound in the span: min {min(span_rates)}%, max {max(span_rates)}%\n")

    H4o, H4c = bars["opens"], [t + SPAN["H4"] for t in bars["opens"]]
    setups = I.breaks_and_stops(bars["H"], bars["L"], bars["C"])
    m5 = (mid["M5"]["t"], mid["M5"]["L"], mid["M5"]["H"])
    tfs = {}
    for g in ("M30", "M15", "M5"):
        ts = mid[g]["t"]
        by_side = {1: [], -1: []}
        for j, side, _, conf in breaks_with_levels(mid[g]["H"], mid[g]["L"], mid[g]["C"]):
            by_side[side].append((j, conf))
        for s in by_side:
            by_side[s].sort()
        tfs[g] = (ts, SPAN[g], by_side)

    # ── G2 ──
    print(f"## G2: time from a 4-hour setup to the first valid entry ({len(setups)} setups; "
          f"long {sum(1 for s in setups if s[1] == 1)}, short {sum(1 for s in setups if s[1] == -1)})")
    print("Time in 4-hour bars of trading time from the setup's close to the entry bar's close.")
    for g in ("M30", "M15", "M5"):
        waits, why = [], defaultdict(int)
        for j, side, dist in setups:
            t0 = H4c[j]
            if j + 1 >= len(H4o) or t0 < mid[g]["t"][0]:
                why["setup before the sub-hourly data starts"] += 1
                continue
            entry_px = bars["C"][j]
            stop_px = entry_px - side * dist
            deadline = H4c[min(j + MAX_H4, len(H4c) - 1)]
            t, res = first_entry(t0, side, stop_px, tfs[g], m5, deadline)
            if t is None:
                why[res] += 1
                continue
            waits.append(bisect.bisect_left(H4c, t) - j)           # 4-hour bars elapsed (1 = within the next bar)
        n = len(waits) + sum(v for k, v in why.items() if k != "setup before the sub-hourly data starts")
        p75 = q(waits, .75)
        within = sum(1 for w in waits if w <= p75)
        print(f"- {g}: setups with data {n}; entered within 10 sessions {len(waits)}; "
              + "; ".join(f"{k} {v}" for k, v in sorted(why.items())))
        print(f"    wait (4-hour bars): {I.quart(waits, '{:.0f}')}")
        print(f"    G2 window = p75 = {p75} four-hour bars: entered within it {within} of {n} "
              f"({100 * within / n:.1f}%); missed {n - within} ({100 * (n - within) / n:.1f}%)")
        print(f"    entered within 1 session (6 bars): {sum(1 for w in waits if w <= 6)} of {n} "
              f"({100 * sum(1 for w in waits if w <= 6) / n:.1f}%)")
        qs = [q(waits, p) for p in (.25, .5, .75)]
        print(f"    time-to-entry buckets (fixed now): <= {qs[0]}, {qs[0] + 1}-{qs[1]}, {qs[1] + 1}-{qs[2]} bars")
    print()

    # ── G3 ──
    print("## G3: spread and structure stop as shares of price, by year")
    pct = defaultdict(list)
    for t, s, m in ba:
        pct[t.astimezone(PT).year].append(100 * s / m)
    print("- spread / price, median: " + "; ".join(f"{y} {statistics.median(v):.4f}%" for y, v in sorted(pct.items())))
    frames = {"H4": (H4o, bars["H"], bars["L"], bars["C"])}
    for g in ("M30", "M15", "M5"):
        frames[g] = (mid[g]["t"], mid[g]["H"], mid[g]["L"], mid[g]["C"])
    allbreaks = {}
    for g, (ts, H, L, C) in frames.items():
        br = I.breaks_and_stops(H, L, C)
        allbreaks[g] = [(ts[j] + SPAN[g], side, d, C[j]) for j, side, d in br]
        by = defaultdict(list)
        for t, _, d, px in allbreaks[g]:
            by[t.astimezone(PT).year].append(100 * d / px)
        print(f"- {g} stop / price, median: " + "; ".join(f"{y} {statistics.median(v):.3f}%" for y, v in sorted(by.items())))
    print()

    # ── G4 ──
    print("## G4: financing as a share of the structure stop (median), by hold, year and side")
    print("Longs pay upper bound + 2.5%; shorts (GNC-1) pay 2.5%; shorts (secondary) receive upper bound - 2.5%")
    print("(a negative share is a credit). Actual/365 at the entry date's rate. Not from any broker.")
    for h in HOLDS:
        print(f"### hold to the close of session +{h}")
        for g in ("H4", "M30", "M15", "M5"):
            cells = defaultdict(list)
            for t, side, d, px in allbreaks[g]:
                if d <= 0:
                    continue
                nights = held_nights(t, session_close(t, h))
                r = rate_on(rt, t.astimezone(NY).date())
                y = t.astimezone(PT).year
                if side == 1:
                    cells[(y, "long")].append(px * (r + MARKUP) / 100 * nights / 365 / d)
                else:
                    cells[(y, "short GNC")].append(px * MARKUP / 100 * nights / 365 / d)
                    cells[(y, "short receive")].append(-px * (r - MARKUP) / 100 * nights / 365 / d)
            for lab in ("long", "short GNC", "short receive"):
                print(f"- {g} {lab}: " + "; ".join(
                    f"{y} {statistics.median(cells[(y, lab)]):+.3f}R" for y in range(2021, 2027) if cells[(y, lab)]))
    print()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
