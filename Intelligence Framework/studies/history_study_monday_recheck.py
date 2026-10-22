"""Monday re-check of data_map_spec §3 item 3 after the approved weekend rule
(docs/specs/study_weekend_candle_spec.md §6; criterion declared there before
this ran). Runs on the STUDY candles fetched by history_study_gate_s3.py.

usage: python3 -I history_study_monday_recheck.py <ohlc_dir> <json_out>

Output: counts, pass/fail, |D1 - H4| differences in pips. No price level,
range or average.
"""
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import history_study_convert as C  # noqa: E402
import history_study_gate_s3 as G  # noqa: E402  (by_session, consistent, items_1_2)


def load(path):
    with open(path) as fh:
        return {datetime.fromisoformat(r["time_utc"]): tuple(float(r[k]) for k in "ohlc")
                for r in csv.DictReader(fh)}


def rows_per_year(bars):
    out = defaultdict(lambda: {"rows": 0, "weekend": 0})
    for t in bars:
        d = C.session_day(t)
        out[d.year]["rows"] += 1
        out[d.year]["weekend"] += d.weekday() >= 5
    return out


def check_sessions(sess, days, pip):
    res = {"tested": 0, "pass": 0, "ineligible": [], "fails": [], "max_diff": 0.0}
    for d in days:
        s = sess.get(d)
        if not s or s["d1"] is None or s["h4_aligned"] != 6 or len(s["h4"]) != 6:
            res["ineligible"].append(d.isoformat())
            continue
        ok, dh, dl = G.consistent(s, pip)
        res["tested"] += 1
        res["pass"] += ok
        res["max_diff"] = max(res["max_diff"], dh, dl)
        if not ok:
            res["fails"].append((d.isoformat(), dh, dl))
    return res


def mondays(sess):
    return sorted(d for d in sess if d.weekday() == 0)


def run_pair(ohlc_dir, pair):
    pip = G.PIP[pair]
    d1 = load(os.path.join(ohlc_dir, f"ohlc_{pair}_D.csv"))
    h4 = load(os.path.join(ohlc_dir, f"ohlc_{pair}_H4.csv"))
    d1c, h4c, log = C.convert(d1, h4)
    raw, cnv = G.by_session(d1, h4), G.by_session(d1c, h4c)
    targets = sorted({datetime.fromisoformat(t).date() for _, t in log["folds"]})
    non_monday_targets = [d for d in targets if d.weekday() != 0]
    per_year = {}
    for yr in range(2005, 2014):
        mb = check_sessions(raw, [d for d in mondays(raw) if d.year == yr], pip)
        ma = check_sessions(cnv, [d for d in mondays(cnv) if d.year == yr], pip)
        rb_d, rb_h = rows_per_year(d1)[yr], rows_per_year(h4)[yr]
        ra_d, ra_h = rows_per_year(d1c)[yr], rows_per_year(h4c)[yr]
        per_year[yr] = {
            "d1_rows_before": rb_d["rows"], "d1_weekend_before": rb_d["weekend"],
            "d1_rows_after": ra_d["rows"], "d1_weekend_after": ra_d["weekend"],
            "h4_rows_before": rb_h["rows"], "h4_weekend_before": rb_h["weekend"],
            "h4_rows_after": ra_h["rows"], "h4_weekend_after": ra_h["weekend"],
            "mondays_before": mb, "mondays_after": ma,
            "folds_into_year": sum(1 for d in targets if d.year == yr),
        }
    nm = check_sessions(cnv, non_monday_targets, pip)
    # Supplementary, not gated (§6 lists short sessions untested): short
    # Mondays that received a fold, against whatever H4 they have.
    short = [d for d in targets if d.weekday() == 0 and cnv[d]["d1"] is not None
             and len(cnv[d]["h4"]) != 6]
    short_supp = [(d.isoformat(), len(cnv[d]["h4"]), *G.consistent(cnv[d], pip)) for d in short]
    items = G.items_1_2(cnv)

    # Control: a half-built fold (D1 folded, H4 Sunday candles removed but not
    # merged) must be caught by the same check on the same Mondays.
    h4_half = {t: v for t, v in h4.items() if C.session_day(t).weekday() < 5}
    half = G.by_session(d1c, h4_half)
    ctrl = check_sessions(half, mondays(half), pip)

    weekend_after = sum(v["d1_weekend_after"] + v["h4_weekend_after"] for v in per_year.values())
    all_tested_pass = all(v["mondays_after"]["pass"] == v["mondays_after"]["tested"] for v in per_year.values()) \
        and nm["pass"] == nm["tested"]
    items_ok = all(x["d1_in_band"] and x["h4_ok"] for x in items.values())
    return {
        "log": {k: v for k, v in log.items() if k != "folds"}, "folds": len(log["folds"]),
        "non_monday_targets": [d.isoformat() for d in non_monday_targets],
        "non_monday_targets_check": nm, "short_monday_folds_supp": short_supp, "per_year": per_year, "items_1_2_after": items,
        "weekend_candles_after": weekend_after,
        "control_half_fold_failures": len(ctrl["fails"]), "control_half_fold_tested": ctrl["tested"],
        "PASS": all_tested_pass and weekend_after == 0 and items_ok,
    }


def main():
    ohlc_dir, out = sys.argv[1:3]
    res = {pair: run_pair(ohlc_dir, pair) for pair in G.PAIRS}
    with open(out, "w") as fh:
        json.dump(res, fh, indent=1, default=str)
    for pair, r in res.items():
        print(f"\n{pair}: folds={r['folds']} log={r['log']} weekend_after={r['weekend_candles_after']} PASS={r['PASS']}")
        print(f"  non-Monday fold targets {r['non_monday_targets']} -> {r['non_monday_targets_check']['pass']}/{r['non_monday_targets_check']['tested']} ineligible {r['non_monday_targets_check']['ineligible']}")
        print("  yr  D1 before(wkend)->after  H4 before(wkend)->after  Mondays before pass/tested  after pass/tested  max|diff| after  ineligible after")
        for yr, v in r["per_year"].items():
            mb, ma = v["mondays_before"], v["mondays_after"]
            print(f"  {yr} {v['d1_rows_before']}({v['d1_weekend_before']})->{v['d1_rows_after']}({v['d1_weekend_after']})"
                  f"  {v['h4_rows_before']}({v['h4_weekend_before']})->{v['h4_rows_after']}({v['h4_weekend_after']})"
                  f"  {mb['pass']}/{mb['tested']}  {ma['pass']}/{ma['tested']}  {ma['max_diff']}  {ma['ineligible']}")
        it = r["items_1_2_after"]
        print("  items 1-2 after:", {y: (x["d1_weekday"], x["h4_full_pct"]) for y, x in it.items()})
        print(f"  supplementary short Mondays that received a fold (date, H4 bars, pass, dH, dL): {r['short_monday_folds_supp']}")
        print(f"  CONTROL half-built fold: {r['control_half_fold_failures']} of {r['control_half_fold_tested']} Mondays fail")


if __name__ == "__main__":
    main()
