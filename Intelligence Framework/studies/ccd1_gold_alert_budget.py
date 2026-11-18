"""ccd1_gold_alert_budget.py — owner ruling M3 (2026-11-17). Report-only.

Gold only. For each of the four §15 level lists at tolerance 0.10: ARRIVAL fires
per trading week on 2021-04-27 -> 2026-09-09, merged week by week with BREAK
detections (CCD-1 as signed, the same span), giving the measured part of the
ALERT budget (the morning BRIEFING is not counted, ruling M2). Pre-release
warnings have no 2021-2026 calendar history and are added as a stated
estimate, never as a measurement. Counts only, no outcome.

usage: python3 ccd1_gold_alert_budget.py <intel_study_archives root>
"""
import os, statistics, sys
from collections import Counter
from datetime import timedelta

W = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, W)
import ccd1_arrival_calibration as A
import ccd1_prototype as P

TOL = 0.10
RELEASE_EST = 2     # gold pre-release warnings a week: live calendar, week of 2026-11-16 (3 US releases, 1 inside the morning window)


def main(root):
    sub, shas = A.FILES["XAU_USD"]
    s = {k: A.load(os.path.join(root, sub, f"XAU_USD_{k}.csv"), sha) for k, sha in shas.items()}
    sets = A.level_sets("XAU_USD", s)
    h1 = s["H1"]
    breaks = [h1["t"][t] for t in range(len(h1["t"])) if P.detect(h1, t, s["H4"], s["D"])["why"] is None]
    t0, t1 = h1["t"][0], h1["t"][-1]
    weeks = sorted({A.trading_week(t0 + timedelta(days=k)) for k in range((t1 - t0).days + 1)
                    if (t0 + timedelta(days=k)).weekday() < 5})
    print(f"# Gold ALERT budget (ruling M3): {t0:%Y-%m-%d} -> {t1:%Y-%m-%d}, {len(weeks)} trading weeks, tolerance {TOL}\n")
    print(f"BREAK detections (CCD-1 as signed): {len(breaks)} = {len(breaks) / len(weeks):.2f} a week\n")
    print("| Level list | ARRIVAL / week | ARRIVAL + BREAK / week (measured) | median week | 90th-pct week | busiest week "
          f"| + {RELEASE_EST} release warnings (estimate) = total / week | 90th-pct week + {RELEASE_EST} |")
    print("|---|---|---|---|---|---|---|---|")
    for name, kinds in A.LISTS.items():
        arr = A.fires(s, sets, TOL, kinds)
        wk = Counter(A.trading_week(t) for t in arr + breaks)
        counts = sorted(wk.get(w, 0) for w in weeks)
        p90 = counts[int(0.9 * (len(counts) - 1))]
        mean = sum(counts) / len(weeks)
        print(f"| {name} | {len(arr) / len(weeks):.1f} | {mean:.1f} | {statistics.median(counts):.0f} | {p90} | {counts[-1]} "
              f"| {mean + RELEASE_EST:.1f} | {p90 + RELEASE_EST} |")
    print("\nShare of weeks above 10 (measured ARRIVAL + BREAK, + the release estimate):")
    for name, kinds in A.LISTS.items():
        arr = A.fires(s, sets, TOL, kinds)
        wk = Counter(A.trading_week(t) for t in arr + breaks)
        over = sum(1 for w in weeks if wk.get(w, 0) + RELEASE_EST > 10)
        print(f"- {name}: {over} of {len(weeks)} weeks ({100 * over / len(weeks):.0f}%)")


if __name__ == "__main__":
    main(sys.argv[1])
