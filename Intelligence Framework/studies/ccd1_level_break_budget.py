"""ccd1_level_break_budget.py — owner ruling P2 (2026-11-17). Report-only.

Gold, 2021-04-27 -> 2026-09-09, the chosen ARRIVAL list (ruling M3: daily
swings, range boundaries, prior session, prior week; tolerance 0.10). Counts
how often a level that produced an ARRIVAL then closed through it (LEVEL
BREAK, spec §17), and the weekly ALERT total with ARRIVAL, CCD-1 BREAK and the
release-warning estimate (3 a week after ruling N2; one live week, not a
measurement). An arrival and a break of the same level in the same hour are
one alert (§17). Counts only, no outcome.

usage: python3 ccd1_level_break_budget.py <intel_study_archives root>
"""
import os, statistics, sys
from collections import Counter
from datetime import timedelta

W = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, W)
import ccd1_arrival_calibration as A
import ccd1_prototype as P

TOL = 0.10
KINDS = A.LISTS["no 4-hour swings"]
RELEASES = 3


def main(root):
    sub, shas = A.FILES["XAU_USD"]
    s = {k: A.load(os.path.join(root, sub, f"XAU_USD_{k}.csv"), sha) for k, sha in shas.items()}
    sets = A.level_sets("XAU_USD", s)
    h1 = s["H1"]
    arr = A.fires_detail(s, sets, TOL, KINDS)
    brk = A.level_breaks(s, sets, arr, KINDS)
    ccd = [t for t in range(len(h1["t"])) if P.detect(h1, t, s["H4"], s["D"])["why"] is None]
    t0, t1 = h1["t"][0], h1["t"][-1]
    weeks = sorted({A.trading_week(t0 + timedelta(days=k)) for k in range((t1 - t0).days + 1)
                    if (t0 + timedelta(days=k)).weekday() < 5})
    n = len(weeks)
    brk_at = {t: {round(p, 2) for p, _, _ in b} for t, b in brk}
    # an ARRIVAL alert is sent for a bar only if some level it arrived at did not also break in that bar
    arr_alert = [t for t, lv in arr if any(round(p, 2) not in brk_at.get(t, set()) for _, _, p in lv)]
    same_bar = sum(1 for t, b in brk for p, _, t0_ in b if t0_ == t)
    gaps = [b_t - t0_ for b_t, b in brk for _, _, t0_ in b]
    n_watched = sum(len({round(p, 2) for _, _, p in lv}) for _, lv in arr)
    n_broken = sum(len(b) for _, b in brk)
    print(f"# LEVEL BREAK budget (ruling P2): gold {t0:%Y-%m-%d} -> {t1:%Y-%m-%d}, {n} trading weeks; "
          f"list 'no 4-hour swings', tolerance {TOL}\n")
    print(f"- ARRIVAL alerts: {len(arr)} bars with an arrival; {len(arr_alert)} sent as ARRIVAL "
          f"(the rest arrived and closed through in the same hour, sent as one LEVEL BREAK) = {len(arr_alert) / n:.2f} a week")
    print(f"- watched prices: {n_watched}; closed through while still qualifying: {n_broken} "
          f"({100 * n_broken / n_watched:.0f}%); the rest stopped qualifying first")
    print(f"- LEVEL BREAK alerts: {len(brk)} bars = {len(brk) / n:.2f} a week; {same_bar} in the arrival's own hour; "
          f"hours from arrival to break: median {statistics.median(gaps):.0f}, 90th pct "
          f"{sorted(gaps)[int(0.9 * (len(gaps) - 1))]}")
    print(f"- CCD-1 BREAK: {len(ccd)} = {len(ccd) / n:.2f} a week")
    print(f"- refactor check: every arrival bar = {len(arr) / n:.1f} a week (the M3 run printed 5.0 for this list)")
    rows = {"ARRIVAL": arr_alert, "ARRIVAL_ALL": [t for t, _ in arr], "LEVEL BREAK": [t for t, _ in brk], "CCD-1 BREAK": ccd}
    wk = {k: Counter(A.trading_week(h1["t"][t]) for t in v) for k, v in rows.items()}
    print("\n| Alerts | Average a week | Median week | 90th-pct week | Busiest week | Weeks over 11 |")
    print("|---|---|---|---|---|---|")
    def line(name, counts):
        c = sorted(counts)
        print(f"| {name} | {sum(c) / n:.1f} | {statistics.median(c):.0f} | {c[int(0.9 * (n - 1))]} | {c[-1]} | "
              f"{sum(1 for x in c if x > 11)} ({100 * sum(1 for x in c if x > 11) / n:.0f}%) |")
    measured_before = [wk["ARRIVAL_ALL"].get(w, 0) + wk["CCD-1 BREAK"].get(w, 0) for w in weeks]
    measured_after = [wk["ARRIVAL"].get(w, 0) + wk["CCD-1 BREAK"].get(w, 0) + wk["LEVEL BREAK"].get(w, 0) for w in weeks]
    line("ARRIVAL + CCD-1 BREAK (measured; before P1)", measured_before)
    line("ARRIVAL + CCD-1 BREAK + LEVEL BREAK (measured)", measured_after)
    line(f"before P1, + {RELEASES} release warnings (estimate)", [m + RELEASES for m in measured_before])
    line(f"**with LEVEL BREAK, + {RELEASES} release warnings (estimate)**", [m + RELEASES for m in measured_after])

    print("\n## Options for the owner (ruling P2: reported, not applied)\n")
    print("| Option | LEVEL BREAK a week | Total a week (with 3 releases) | 90th-pct week | Weeks over 11 |")
    print("|---|---|---|---|---|")
    for label, margin, gap in (("spec as written (any close through)", 0.0, 0), ("close at least 0.05 ATR beyond", 0.05, 0),
                               ("close at least 0.10 ATR beyond (the arrival tolerance)", 0.10, 0),
                               ("close at least 0.20 ATR beyond", 0.20, 0), ("2 or more hours after the arrival", 0.0, 2),
                               ("0.10 ATR beyond and 2+ hours after", 0.10, 2)):
        b = A.level_breaks(s, sets, arr, KINDS, margin=margin, min_gap=gap)
        bat = {t: {round(p, 2) for p, _, _ in x} for t, x in b}
        aa = [t for t, lv in arr if any(round(p, 2) not in bat.get(t, set()) for _, _, p in lv)]
        wb, wa = Counter(A.trading_week(h1["t"][t]) for t, _ in b), Counter(A.trading_week(h1["t"][t]) for t in aa)
        wc = Counter(A.trading_week(h1["t"][t]) for t in ccd)
        tot = sorted(wa.get(w, 0) + wb.get(w, 0) + wc.get(w, 0) + RELEASES for w in weeks)
        print(f"| {label} | {len(b) / n:.2f} | {sum(tot) / n:.1f} | {tot[int(0.9 * (n - 1))]} | "
              f"{sum(1 for x in tot if x > 11)} ({100 * sum(1 for x in tot if x > 11) / n:.0f}%) |")

    print("\n## Each ARRIVAL level list with LEVEL BREAK as written (ruling P2: reported, not applied)\n")
    print("| ARRIVAL list | ARRIVAL sent a week | LEVEL BREAK a week | Total a week (with 3 releases) | 90th-pct week | Weeks over 11 |")
    print("|---|---|---|---|---|---|")
    for name, kinds in A.LISTS.items():
        a2 = A.fires_detail(s, sets, TOL, kinds)
        b2 = A.level_breaks(s, sets, a2, kinds)
        bat = {t: {round(p, 2) for p, _, _ in x} for t, x in b2}
        aa = [t for t, lv in a2 if any(round(p, 2) not in bat.get(t, set()) for _, _, p in lv)]
        wb, wa = Counter(A.trading_week(h1["t"][t]) for t, _ in b2), Counter(A.trading_week(h1["t"][t]) for t in aa)
        wc = Counter(A.trading_week(h1["t"][t]) for t in ccd)
        tot = sorted(wa.get(w, 0) + wb.get(w, 0) + wc.get(w, 0) + RELEASES for w in weeks)
        print(f"| {name} | {len(aa) / n:.2f} | {len(b2) / n:.2f} | {sum(tot) / n:.1f} | {tot[int(0.9 * (n - 1))]} | "
              f"{sum(1 for x in tot if x > 11)} ({100 * sum(1 for x in tot if x > 11) / n:.0f}%) |")


if __name__ == "__main__":
    main(sys.argv[1])
