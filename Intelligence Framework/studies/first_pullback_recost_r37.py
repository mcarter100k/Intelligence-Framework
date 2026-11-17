"""first_pullback_recost_r37.py — declared re-costing of R37 (first pullback,
GBP/AUD) with the corrected financing boundary (owner ruling R1, 2026-11-16).
Report-only; prints. The original R37 figures stay in the record.

usage: python3 -I first_pullback_recost_r37.py <data_dir>   (~/intel_study_archives/us_event_reaction_data)

The only change: a timed exit that closes exactly on the 17:00 New York roll is
no longer charged for that night (studies/gold_rule_costs.held_nights). A
stopped trade is timed at its stop bar's open by the original runner, but the
stop is hit inside that bar, after the open, so a roll at that open was held:
stopped trades keep the original night count. Everything else (data, hashes,
detector, grading, spread, rates, episodes, bootstrap, seed) is the frozen
runner's own code, imported unchanged.

Positive control first: the original costing must reproduce R37's committed
figures exactly, or the script stops.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import first_pullback_study as FP  # noqa: E402
from gold_rule_costs import held_nights  # noqa: E402

COMMITTED = {0.382: {"n": 36, "mean": -0.011, "median": -0.082, "lower": -0.269, "upper": 0.140},
             0.5: {"n": 30, "mean": 0.017, "median": -0.220, "lower": -0.384, "upper": 0.276}}


def cell(prepared, rates, level):
    bars, atr, trend, _, _ = prepared["GBP_AUD"]
    trades, _, _ = FP.cell_trades("GBP_AUD", bars, atr, trend, level, rates)
    eps = FP.episodes(trades)
    return eps, FP.summarize([e["adj"] for e in eps])


def corrected_financed(orig):
    def financed(pair, side, opens, e, exit_bar, stopped, *a, **kw):
        t = orig(pair, side, opens, e, exit_bar, stopped, *a, **kw)
        if stopped:
            return t
        exit_time = opens[exit_bar] + FP.timedelta(hours=4)
        n_new = held_nights(opens[e], exit_time)
        if n_new != t["nights"]:
            t["fin_r"] = t["fin_r"] * n_new / t["nights"] if t["nights"] else 0.0
            t["nights_old"], t["nights"] = t["nights"], n_new
        return t
    return financed


def show(label, eps, s):
    print(f"- {label}: N {s['n']}; mean {s['mean']:+.3f}R; median {s['median']:+.3f}R; "
          f"lower {s['lower']:+.3f}R; upper (90%) {s['upper']:+.3f}R; without best {s['without_best']:+.3f}R; "
          f"verdict {s['verdict']}")


def main(data_dir):
    rates = FP.load_rates()
    prepared = FP._prepare(data_dir)                      # hash-checked, STUDY window enforced
    print("# R37 re-costing (owner ruling R1, 2026-11-16)\n")
    for level in (0.382, 0.5):
        eps, s = cell(prepared, rates, level)
        c = COMMITTED[level]
        got = {k: round(s[k], 3) for k in ("mean", "median", "lower", "upper")}
        ok = s["n"] == c["n"] and all(abs(got[k] - c[k]) < 0.0005 for k in got)
        print(f"## GBP/AUD {level:.1%}")
        show("original costing (positive control)", eps, s)
        print(f"  control vs committed R37 {c}: {'MATCH' if ok else 'MISMATCH'}")
        if not ok:
            raise SystemExit("positive control failed: the original costing does not reproduce R37; stopping")
    orig = FP.financed
    FP.financed = corrected_financed(orig)
    try:
        for level in (0.382, 0.5):
            eps, s = cell(prepared, rates, level)
            changed = [e for e in eps if "nights_old" in e]
            print(f"\n## GBP/AUD {level:.1%}, corrected boundary")
            show("re-costed", eps, s)
            print(f"  episodes whose night count changed: {len(changed)} of {len(eps)}"
                  + ("; " + ", ".join(f"{e['day']} {e['nights_old']}->{e['nights']}" for e in changed) if changed else ""))
    finally:
        FP.financed = orig


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
