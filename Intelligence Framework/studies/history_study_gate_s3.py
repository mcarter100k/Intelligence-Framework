"""data_map_spec §3 conversion gate on OANDA STUDY data, run exactly as
declared in §11.4 (commit 340aef0, before any price was fetched).

usage: python3 -I history_study_gate_s3.py <env_file> <out_dir>

Output: counts, pass/fail, and |difference| in pips for item 3 only.
No price level, range or average is printed or written to the summary.
Fetched candles are written to <out_dir> (outside the repo) for re-runs.
"""
import copy
import csv
import json
import os
import random
import statistics
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import history_depth_oanda_probe as P  # noqa: E402  (client, iso, parse)

NY = ZoneInfo("America/New_York")
UTC = timezone.utc
STUDY_FROM = datetime(2005, 1, 1, tzinfo=UTC)
STUDY_TO = datetime(2013, 12, 30, 21, 30, tzinfo=UTC)      # last STUDY session ends 22:00Z
# Embargo (§11.2) + SEALED EXAM as one blocked interval of candle opens.
BLOCK_START = datetime(2013, 12, 30, 22, 0, tzinfo=UTC)
BLOCK_END = datetime(2021, 4, 26, 21, 0, tzinfo=UTC)
PAIRS = ("GBP_AUD", "GBP_JPY")
PIP = {"GBP_AUD": 0.0001, "GBP_JPY": 0.01}
H4_SLOTS = (17, 21, 1, 5, 9, 13)
TOL = 0.5
SPOT = [("2008-10-24", ("GBP_AUD", "GBP_JPY")), ("2010-05-06", ("GBP_AUD", "GBP_JPY")),
        ("2011-03-17", ("GBP_JPY",)), ("2013-04-04", ("GBP_JPY",))]


class Blocked(RuntimeError):
    pass


def guard(frm, to):
    # OANDA returns the candle containing `from`: keep a one-day margin.
    if frm < BLOCK_END + timedelta(days=1) and to > BLOCK_START:
        raise Blocked(f"refused: {frm}..{to} touches embargo/sealed block")


def tday(t):
    return (t.astimezone(NY) + timedelta(hours=7)).date()


def fetch(cl, pair, gran):
    rows = {}
    lo = STUDY_FROM
    while lo < STUDY_TO:
        hi = min(lo + timedelta(days=31), STUDY_TO)
        guard(lo, hi)
        st, p = cl.candles(pair, {"granularity": gran, "price": "M",
                                  "from": P.iso(lo), "to": P.iso(hi)})
        if st != 200:
            raise RuntimeError(f"{pair} {gran}: HTTP {st} {p}")
        for c in p.get("candles", []):
            t = P.parse(c["time"])
            if BLOCK_START <= t < BLOCK_END:
                raise Blocked(f"API returned blocked candle {t}; aborting")
            if not c.get("complete", True) or tday(t) < date(2005, 1, 1):
                continue
            m = c["mid"]
            rows[t] = tuple(float(m[k]) for k in "ohlc")
        lo = hi
    return rows


def save(path, rows):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["time_utc", "o", "h", "l", "c"])
        for t in sorted(rows):
            w.writerow([t.isoformat(), *rows[t]])


def by_session(d1, h4):
    """trading day -> {'d1': ohlc|None, 'h4': [ohlc...], 'h4_aligned': n, 'weekday': bool}"""
    s = defaultdict(lambda: {"d1": None, "h4": [], "h4_aligned": 0})
    for t, v in d1.items():
        tn = t.astimezone(NY)
        if tn.hour == 17 and tn.minute == 0:
            s[tday(t)]["d1"] = v
        else:
            s[tday(t)]["d1_misaligned"] = True
    for t, v in h4.items():
        tn = t.astimezone(NY)
        s[tday(t)]["h4"].append(v)
        if tn.minute == 0 and tn.hour in H4_SLOTS:
            s[tday(t)]["h4_aligned"] += 1
    return s


def items_1_2(sess):
    out = {}
    for yr in range(2005, 2014):
        days = [d for d in sess if d.year == yr and d.weekday() < 5]
        d1 = sum(1 for d in days if sess[d]["d1"] is not None)
        with_bars = [d for d in days if sess[d]["h4"]]
        full = sum(1 for d in with_bars if sess[d]["h4_aligned"] == 6 and len(sess[d]["h4"]) == 6)
        out[yr] = {"d1_weekday": d1, "d1_in_band": 252 <= d1 <= 262,
                   "h4_sessions_with_bars": len(with_bars), "h4_full": full,
                   "h4_full_pct": round(100 * full / len(with_bars), 2),
                   "h4_ok": full / len(with_bars) >= 0.99}
    return out


def consistent(day, pip):
    d1 = day["d1"]
    dh = abs(d1[1] - max(b[1] for b in day["h4"])) / pip
    dl = abs(d1[2] - min(b[2] for b in day["h4"])) / pip
    return dh <= TOL and dl <= TOL, round(dh, 3), round(dl, 3)


def eligible(sess, yr):
    return sorted(d for d in sess if d.year == yr and d.weekday() < 5
                  and sess[d]["d1"] is not None and sess[d]["h4_aligned"] == 6
                  and len(sess[d]["h4"]) == 6)


def item_3(sess, pair):
    pip = PIP[pair]
    res = {"per_year": {}, "sampled_pass": 0, "sampled": 0, "sampled_fail_days": []}
    diffs = []
    for yr in range(2005, 2014):
        el = eligible(sess, yr)
        sample = random.Random(f"data_map_s3_item3:{pair}:{yr}").sample(el, 50)
        ok = 0
        for d in sample:
            good, dh, dl = consistent(sess[d], pip)
            diffs += [dh, dl]
            ok += good
            if not good:
                res["sampled_fail_days"].append((d.isoformat(), dh, dl))
        res["per_year"][yr] = {"eligible": len(el), "sampled": 50, "pass": ok}
        res["sampled"] += 50
        res["sampled_pass"] += ok
    res["sampled_absdiff_pips_max"] = max(diffs)
    res["sampled_absdiff_nonzero"] = sum(1 for x in diffs if x > 0)
    # supplementary: every eligible weekday, and every weekend session vs its own H4
    allw = [d for yr in range(2005, 2014) for d in eligible(sess, yr)]
    allw_ok = sum(consistent(sess[d], pip)[0] for d in allw)
    wk = [d for d in sess if d.weekday() >= 5 and sess[d]["d1"] is not None and sess[d]["h4"]]
    wk_res = [consistent(sess[d], pip) for d in wk]
    wk_fail = [(d.isoformat(), r[1], r[2]) for d, r in zip(wk, wk_res) if not r[0]]
    res["supp_all_weekdays"] = {"n": len(allw), "pass": allw_ok,
                                "fail_days": [(d.isoformat(), *consistent(sess[d], pip)[1:])
                                              for d in allw if not consistent(sess[d], pip)[0]]}
    res["supp_weekend_sessions"] = {"n": len(wk), "pass": len(wk) - len(wk_fail),
                                    "fail_days": wk_fail}
    wk_no_d1 = [d.isoformat() for d in sess if d.weekday() >= 5 and sess[d]["d1"] is None and sess[d]["h4"]]
    wk_no_h4 = [d.isoformat() for d in sess if d.weekday() >= 5 and sess[d]["d1"] is not None and not sess[d]["h4"]]
    res["supp_weekend_unpaired"] = {"h4_without_d1": len(wk_no_d1), "d1_without_h4": len(wk_no_h4)}
    res["pass"] = res["sampled_pass"] == res["sampled"]
    return res


def rng(v):
    return v[1] - v[2]


def elevated(sess, d):
    prior = sorted((x for x in sess if x < d and 1 <= x.weekday() <= 4 and sess[x]["d1"] is not None),
                   reverse=True)[:20]
    base = statistics.median(rng(sess[x]["d1"]) for x in prior)
    return rng(sess[d]["d1"]) > base, len(prior), base


def item_4(sessions):
    out = []
    for ds, range_pairs in SPOT:
        d = date.fromisoformat(ds)
        assert d.weekday() != 0, "declared dates are not Mondays"
        for pair in PAIRS:
            s = sessions[pair]
            exists = d in s and s[d]["d1"] is not None
            row = {"date": ds, "pair": pair, "exists": exists}
            if pair in range_pairs:
                if exists:
                    up, n, _ = elevated(s, d)
                    row.update({"elevated": up, "baseline_days": n})
                else:
                    row["elevated"] = False
            out.append(row)
    ok = all(r["exists"] for r in out) and all(r.get("elevated", True) for r in out)
    return {"checks": out, "pass": ok}


def controls(sessions):
    """Prove each check can fail. Nothing about prices is printed."""
    c = {}
    s = copy.deepcopy(sessions["GBP_JPY"])
    pip = PIP["GBP_JPY"]
    d = random.Random("data_map_s3_item3:GBP_JPY:2009").sample(eligible(s, 2009), 50)[0]
    hi = max(b[1] for b in s[d]["h4"])
    o, h, l, cl = s[d]["d1"]
    s[d]["d1"] = (o, hi + 0.6 * pip, l, cl)
    c["item3_plant_0.6pip_fails"] = not consistent(s[d], pip)[0]
    s[d]["d1"] = (o, hi + 0.4 * pip, l, cl)
    c["item3_plant_0.4pip_passes"] = consistent(s[d], pip)[0]
    s2 = copy.deepcopy(sessions["GBP_JPY"])
    s2[d]["d1"] = (o, hi + 0.6 * pip, l, cl)
    r2 = item_3(s2, "GBP_JPY")
    c["item3_gate_flips_on_one_planted_day"] = (r2["pass"] is False and r2["sampled_pass"] == r2["sampled"] - 1)
    c["item4_known_missing_2012-12-25_absent"] = not (date(2012, 12, 25) in s and s[date(2012, 12, 25)]["d1"] is not None)
    # strict '>' : a target whose range equals its baseline median must fail
    s3 = copy.deepcopy(sessions["GBP_JPY"])
    t = date(2011, 3, 17)
    _, _, base = elevated(s3, t)
    o, h, l, cl = s3[t]["d1"]
    s3[t]["d1"] = (o, l + base - 1e-9, l, cl)
    c["item4_range_just_below_baseline_fails"] = elevated(s3, t)[0] is False
    s3[t]["d1"] = (o, l + base + 1e-6, l, cl)
    c["item4_range_just_above_baseline_passes"] = elevated(s3, t)[0] is True
    return c


def main():
    env_file, out = sys.argv[1:3]
    cl = P.Client(P.load_env(env_file))
    sessions, summary = {}, {"pairs": {}}
    for pair in PAIRS:
        d1, h4 = fetch(cl, pair, "D"), fetch(cl, pair, "H4")
        save(os.path.join(out, f"ohlc_{pair}_D.csv"), d1)
        save(os.path.join(out, f"ohlc_{pair}_H4.csv"), h4)
        sess = by_session(d1, h4)
        sessions[pair] = sess
        first, last = min(d1), max(h4)
        summary["pairs"][pair] = {
            "d1_rows": len(d1), "h4_rows": len(h4),
            "first_d1_utc": min(d1).isoformat(), "last_d1_utc": max(d1).isoformat(),
            "first_h4_utc": min(h4).isoformat(), "last_h4_utc": max(h4).isoformat(),
            "items_1_2": items_1_2(sess), "item_3": item_3(sess, pair)}
    summary["item_4"] = item_4(sessions)
    summary["controls"] = controls(sessions)
    summary["requests"] = cl.requests
    with open(os.path.join(out, "gate_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1, default=str)
    for pair, v in summary["pairs"].items():
        print(f"\n{pair}: D1 {v['d1_rows']} rows {v['first_d1_utc']}..{v['last_d1_utc']}; "
              f"H4 {v['h4_rows']} rows {v['first_h4_utc']}..{v['last_h4_utc']}")
        for yr, x in v["items_1_2"].items():
            print(f"  {yr} item1 D1 weekday={x['d1_weekday']} in_band={x['d1_in_band']}  "
                  f"item2 H4 full {x['h4_full']}/{x['h4_sessions_with_bars']}={x['h4_full_pct']}% ok={x['h4_ok']}")
        i3 = v["item_3"]
        print("  item3 per year:", {y: f"{z['pass']}/{z['sampled']} of {z['eligible']}" for y, z in i3["per_year"].items()})
        print(f"  item3 sampled {i3['sampled_pass']}/{i3['sampled']} PASS={i3['pass']} "
              f"max|diff|={i3['sampled_absdiff_pips_max']} pips nonzero={i3['sampled_absdiff_nonzero']} "
              f"fails={i3['sampled_fail_days']}")
        sa, sw = i3["supp_all_weekdays"], i3["supp_weekend_sessions"]
        print(f"  supp all weekdays {sa['pass']}/{sa['n']} fails={sa['fail_days'][:10]}")
        print(f"  supp weekend sessions {sw['pass']}/{sw['n']} fails={len(sw['fail_days'])} first={sw['fail_days'][:5]} unpaired={i3['supp_weekend_unpaired']}")
    print("\nitem4:", json.dumps(summary["item_4"]))
    print("controls:", summary["controls"])
    print("requests:", cl.requests)


if __name__ == "__main__":
    main()
