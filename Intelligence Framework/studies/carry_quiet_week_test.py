"""Pre-registered test: after a quiet week, hold the carry side for the next
week (docs/specs/carry_quiet_week_spec.md). Cells: GBP_JPY and GBP_AUD.

usage:
  python3 -I carry_quiet_week_test.py selftest
  python3 -I carry_quiet_week_test.py counts <env_file> <out_dir>
  python3 -I carry_quiet_week_test.py full <out_dir> <report_md>

counts fetches the STUDY candles (embargo-guarded), stores them with their
sha256, and prints counts only. full runs once on exactly those files.
"""
import csv
import hashlib
import json
import math
import os
import random
import statistics
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import history_study_convert as C  # noqa: E402  approved weekend rule
import history_study_gate_s3 as G  # noqa: E402  guarded STUDY fetch

NY = ZoneInfo("America/New_York")
PAIRS = {"GBP_JPY": ("GBP", "JPY", 0.01), "GBP_AUD": ("GBP", "AUD", 0.0001)}
SPREAD = {"GBP_AUD": {range(2005, 2010): 10.0, range(2010, 2014): 7.0},   # data_map_spec §4
          "GBP_JPY": {range(2005, 2010): 6.0, range(2010, 2014): 5.0}}
MARKUP = 1.0          # percent a year taken off the carry received
CARRY_DAYS = 6        # Mon, Tue, Wed (x3), Thu rollovers; exit Friday before 17:00 New York
LOOKBACK = 26
MIN_SESSIONS = 3
RESAMPLES = 10000
ALPHA = 0.05          # one-sided; Sidak for two cells at a 90% family level
LAST_STUDY_DAY = date(2013, 12, 30)
SUBPERIODS = [("2005-01 to 2008-06 (before the crisis)", date(2005, 1, 1), date(2008, 6, 30)),
              ("2008-07 to 2009-06 (the crisis)", date(2008, 7, 1), date(2009, 6, 30)),
              ("2009-07 to 2013-12 (after)", date(2009, 7, 1), date(2013, 12, 31))]


# Rates -------------------------------------------------------------------------

def load_rates(path=os.path.join(HERE, "policy_rates_2003_2014.json")):
    with open(path) as fh:
        raw = json.load(fh)
    return {ccy: [(date.fromisoformat(d), v) for d, v in raw[ccy]["changes"]] for ccy in ("GBP", "AUD", "JPY")}


def rate_on(rates, ccy, day):
    val = None
    for d, v in rates[ccy]:
        if d <= day:
            val = v
    if val is None:
        raise ValueError(f"no {ccy} rate on {day}")
    return val


# Weeks and trades --------------------------------------------------------------

def build_weeks(d1):
    """Converted D1 -> weeks of Mon-Fri sessions (ISO week of the session date)."""
    by = defaultdict(list)
    for t in sorted(d1):
        day = C.session_day(t)
        if day.weekday() >= 5:
            raise ValueError(f"weekend session {day} survived conversion")
        by[day.isocalendar()[:2]].append((day, d1[t]))
    weeks = []
    for key in sorted(by):
        days = by[key]
        weeks.append({"iso": key, "monday": days[0][0] - timedelta(days=days[0][0].weekday()),
                      "first_day": days[0][0], "last_day": days[-1][0], "n": len(days),
                      "open": days[0][1][0], "close": days[-1][1][3],
                      "high": max(b[1] for _, b in days), "low": min(b[2] for _, b in days)})
    return weeks


def spread_for(pair, year):
    for yrs, v in SPREAD[pair].items():
        if year in yrs:
            return v
    raise ValueError(f"no spread for {pair} {year}")


def trades(pair, weeks, rates, markup=MARKUP, spread_mult=1.0, which="quiet"):
    """which: 'quiet' (the hypothesis), 'all' or 'not_quiet' (secondary comparisons)."""
    base, quote, pip = PAIRS[pair]
    good = [w for w in weeks if w["n"] >= MIN_SESSIONS]
    rng = [(w["high"] - w["low"]) / pip for w in good]
    out = []
    for i in range(LOOKBACK, len(good) - 1):
        w, nxt = good[i], good[i + 1]
        if nxt["monday"] - w["monday"] != timedelta(days=7):
            continue                              # the next week is missing or excluded
        quiet = rng[i] <= statistics.median(rng[i - LOOKBACK:i])
        if (which == "quiet" and not quiet) or (which == "not_quiet" and quiet):
            continue
        diff = rate_on(rates, base, nxt["first_day"]) - rate_on(rates, quote, nxt["first_day"])
        if diff == 0:
            continue
        side = 1 if diff > 0 else -1
        financing = nxt["open"] * (abs(diff) - markup) / 100 * CARRY_DAYS / 365 / pip
        spread = spread_for(pair, nxt["first_day"].year) * spread_mult
        move = side * (nxt["close"] - nxt["open"]) / pip
        pips = move - spread + financing
        norm_base = statistics.median(rng[i - LOOKBACK + 1:i + 1])
        out.append({"week": nxt["monday"], "side": side, "move": move, "spread": spread,
                    "financing": financing, "pips": pips, "norm": pips / norm_base, "diff": diff})
    return out


# Statistics --------------------------------------------------------------------

def boot_lower(xs, seed, alpha=ALPHA, n=RESAMPLES):
    r = random.Random(seed)
    k = len(xs)
    means = sorted(sum(xs[r.randrange(k)] for _ in range(k)) / k for _ in range(n))
    return means[int(alpha * n)]


def boot_diff_ci(a, b, seed, n=RESAMPLES):
    r = random.Random(seed)
    ds = sorted(sum(a[r.randrange(len(a))] for _ in a) / len(a) - sum(b[r.randrange(len(b))] for _ in b) / len(b)
                for _ in range(n))
    return ds[int(0.05 * n)], ds[int(0.95 * n)]


def t_lower(xs):
    m, s = statistics.fmean(xs), statistics.stdev(xs)
    return m - 1.6449 * s / math.sqrt(len(xs))


def classify(mean, lower, no_best):
    """The pre-registered verdict rule (spec §7)."""
    if mean <= 0:
        return "REFUTED"
    if lower > 0 and no_best > 0:
        return "SUPPORTED"
    return "INCONCLUSIVE"


def verdict(xs, seed):
    mean = statistics.fmean(xs)
    lower = boot_lower(xs, seed)
    best = max(xs)
    rest = list(xs)
    rest.remove(best)
    no_best = statistics.fmean(rest)
    v = classify(mean, lower, no_best)
    return v, {"n": len(xs), "mean": mean, "lower95": lower, "t_lower95": t_lower(xs),
               "median": statistics.median(xs), "mean_without_best": no_best,
               "hit_rate": sum(x > 0 for x in xs) / len(xs)}


def drawdown(xs):
    peak = cum = worst = 0.0
    streak = longest = 0
    for x in xs:
        cum += x
        peak = max(peak, cum)
        worst = min(worst, cum - peak)
        streak = streak + 1 if x <= 0 else 0
        longest = max(longest, streak)
    return worst, longest


# Self-test ---------------------------------------------------------------------

def selftest():
    ok = True

    def check(name, cond):
        nonlocal ok
        ok &= bool(cond)
        print(("PASS " if cond else "FAIL ") + name)

    r = random.Random(1)
    real = [r.gauss(0.3, 0.7) for _ in range(222)]
    check("a real +0.3 edge at N=222 is SUPPORTED", verdict(real, "st1")[0] == "SUPPORTED")
    passes = 0
    for k in range(300):
        null = [r.gauss(0.0, 0.7) for _ in range(222)]
        lower = boot_lower(null, f"st-null-{k}", n=2000)
        passes += lower > 0
    check(f"a zero edge passes the bound in about 5% of runs ({passes}/300)", 5 <= passes <= 28)
    fluke = [r.gauss(-0.02, 0.5) for _ in range(221)] + [40.0]
    v, s = verdict(fluke, "st3")
    check(f"one huge week cannot make a pass (mean {s['mean']:+.3f}, without it {s['mean_without_best']:+.3f}): {v}",
          v != "SUPPORTED" and s["mean"] > 0)
    check("rule: bound just below zero is not a pass", classify(0.1, -0.001, 0.05) == "INCONCLUSIVE")
    check("rule: positive bound but negative without the best week is not a pass",
          classify(0.1, 0.01, -0.001) == "INCONCLUSIVE")
    check("rule: positive bound and positive without the best week passes", classify(0.1, 0.01, 0.001) == "SUPPORTED")
    check("rule: a zero mean is REFUTED", classify(0.0, -0.1, -0.1) == "REFUTED")
    neg = [r.gauss(-0.1, 0.7) for _ in range(222)]
    check("a negative edge is REFUTED", verdict(neg, "st4")[0] == "REFUTED")

    # Hand-computed pipeline: rising week ranges (100 + k pips) never qualify; week 28 is
    # quiet (50 pips); week 29 is the trade week (range 300, open 150.0, close 150.6).
    # Normaliser = median of the 26 ranges ending at the signal week = 114.5 pips
    # (a window shifted one week later would give 115.5).
    rates = {"GBP": [(date(2004, 1, 1), 5.0)], "JPY": [(date(2004, 1, 1), 0.5)], "AUD": [(date(2004, 1, 1), 6.0)]}
    weeks = []
    for k in range(28):
        mon = date(2006, 1, 2) + timedelta(weeks=k)
        half = (100 + k) / 2 * 0.01
        weeks.append({"monday": mon, "first_day": mon, "n": 5, "open": 150.0, "close": 150.0,
                      "high": 150.0 + half, "low": 150.0 - half})
    mon = date(2006, 1, 2) + timedelta(weeks=28)
    weeks.append({"monday": mon, "first_day": mon, "n": 5, "open": 150.0, "close": 150.0, "high": 150.25, "low": 149.75})
    mon += timedelta(weeks=1)
    weeks.append({"monday": mon, "first_day": mon, "n": 5, "open": 150.0, "close": 150.6, "high": 151.5, "low": 148.5})
    t = trades("GBP_JPY", weeks, rates)
    check(f"exactly one trade, into the week after the quiet week ({[x['week'] for x in t]})",
          len(t) == 1 and t[0]["week"] == mon)
    last = t[-1] if t else {"week": None, "side": 0, "move": 0, "spread": 0, "financing": 0, "norm": 0}
    fin = 150.0 * (5.0 - 0.5 - MARKUP) / 100 * CARRY_DAYS / 365 / 0.01
    check(f"long, move +60 pips (side {last['side']}, move {last['move']:.1f})",
          last["side"] == 1 and abs(last["move"] - 60) < 1e-6)
    check(f"spread 6 pips (2006) and financing {fin:.3f} pips", last["spread"] == 6.0 and abs(last["financing"] - fin) < 1e-9)
    check(f"normalised by the median of the 26 weeks ending at the signal week (114.5 pips): {last['norm']:.4f}",
          abs(last["norm"] - (60 - 6 + fin) / 114.5) < 1e-9)
    t_aud = trades("GBP_AUD", [dict(w, open=w["open"] / 100, close=w["close"] / 100, high=w["high"] / 100,
                                    low=w["low"] / 100) for w in weeks], rates)
    check("GBP/AUD takes the short side when AUD pays more", t_aud[-1]["side"] == -1)
    gap = weeks[:-1] + [dict(weeks[-1], monday=weeks[-1]["monday"] + timedelta(weeks=1),
                             first_day=weeks[-1]["first_day"] + timedelta(weeks=1))]
    check("no trade when the next week is missing", all(x["week"] != gap[-1]["monday"] for x in trades("GBP_JPY", gap, rates)))
    print("SELFTEST", "OK" if ok else "FAILED")
    return ok


# Stages ------------------------------------------------------------------------

def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def save(path, rows):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["time_utc", "o", "h", "l", "c"])
        for t in sorted(rows):
            w.writerow([t.isoformat(), *rows[t]])


def load(path):
    with open(path) as fh:
        return {datetime.fromisoformat(r["time_utc"]): tuple(float(r[k]) for k in "ohlc") for r in csv.DictReader(fh)}


def converted_weeks(out_dir, pair):
    d1 = load(os.path.join(out_dir, f"{pair}_D.csv"))
    h4 = load(os.path.join(out_dir, f"{pair}_H4.csv"))
    d1c, _, log = C.convert(d1, h4)
    weeks = build_weeks(d1c)
    if max(w["last_day"] for w in weeks) > LAST_STUDY_DAY:
        raise RuntimeError("a week reaches into the embargo")
    return weeks, log


def counts(env_file, out_dir):
    cl = G.P.Client(G.P.load_env(env_file))
    hashes, rates = {}, load_rates()
    for pair in PAIRS:
        d1, h4 = G.fetch(cl, pair, "D"), G.fetch(cl, pair, "H4")
        for gran, rows in (("D", d1), ("H4", h4)):
            p = os.path.join(out_dir, f"{pair}_{gran}.csv")
            save(p, rows)
            hashes[os.path.basename(p)] = sha(p)
        weeks, log = converted_weeks(out_dir, pair)
        t_q, t_all = trades(pair, weeks, rates), trades(pair, weeks, rates, which="all")
        by_year = defaultdict(int)
        for x in t_q:
            by_year[x["week"].year] += 1
        print(f"{pair}: weeks {len(weeks)} ({weeks[0]['monday']} to {weeks[-1]['monday']}); "
              f"excluded (< {MIN_SESSIONS} sessions) {sum(w['n'] < MIN_SESSIONS for w in weeks)}; "
              f"tradeable weeks with history {len(t_all)}; QUIET-WEEK TRADES {len(t_q)}; "
              f"sides {sorted({x['side'] for x in t_q})}; per year {dict(sorted(by_year.items()))}; "
              f"weekend rule: {log['sunday_folded_d1']} Sunday folded, {log['saturday_dropped_d1']} Saturday dropped")
    with open(os.path.join(out_dir, "data_hashes.json"), "w") as fh:
        json.dump(hashes, fh, indent=1)
    print("data hashes:", json.dumps(hashes))
    print("requests:", cl.requests)


def fmt(s, unit=""):
    return (f"N {s['n']}; mean {s['mean']:+.3f}{unit}; one-sided 95% lower bound {s['lower95']:+.3f}{unit} "
            f"(normal-approximation check {s['t_lower95']:+.3f}); median {s['median']:+.3f}{unit}; "
            f"mean without the best week {s['mean_without_best']:+.3f}{unit}; winning weeks {100 * s['hit_rate']:.0f}%")


def full(out_dir, report):
    with open(os.path.join(out_dir, "data_hashes.json")) as fh:
        recorded = json.load(fh)
    for name, h in recorded.items():
        if sha(os.path.join(out_dir, name)) != h:
            raise RuntimeError(f"{name} changed since the counts stage")
    rates = load_rates()
    lines = ["# Carry after a quiet week — pre-registered test result (2005–2013 STUDY data)", "",
             "Spec: docs/specs/carry_quiet_week_spec.md. Run once, on the candles recorded at the counts stage "
             "(sha256 verified). Units: **typical-week ranges** (a trade's pips divided by the median weekly "
             "range of the 26 weeks before it), the primary measure; pips are secondary.", ""]
    summary = {}
    for pair in PAIRS:
        name = pair.replace("_", "/")
        weeks, _ = converted_weeks(out_dir, pair)
        tq = trades(pair, weeks, rates)
        v, s = verdict([x["norm"] for x in tq], f"cqw:{pair}")
        summary[pair] = (v, s)
        sp = {"n": len(tq), **{k: statistics.fmean(x[k] for x in tq) for k in ("move", "spread", "financing", "pips")}}
        pips_stats = verdict([x["pips"] for x in tq], f"cqw-pips:{pair}")[1]
        lines += [f"## {name}: **{v}**", "",
                  f"- Side held: {'long' if tq[0]['side'] == 1 else 'short'} {name} in "
                  f"{sum(x['side'] == tq[0]['side'] for x in tq)} of {len(tq)} weeks (the higher-yielding currency bought).",
                  f"- **Primary (typical-week units):** {fmt(s)}",
                  f"- Pips: {fmt(pips_stats, ' pips')}",
                  f"- Average trade in pips: price move {sp['move']:+.1f}, spread −{sp['spread']:.1f}, "
                  f"financing {sp['financing']:+.1f}, net {sp['pips']:+.1f}"]
        dd_n, streak = drawdown([x["norm"] for x in tq])
        dd_p, _ = drawdown([x["pips"] for x in tq])
        lines += [f"- Worst drawdown: {dd_n:.2f} typical-week ranges ({dd_p:.0f} pips); worst week "
                  f"{min(x['pips'] for x in tq):.0f} pips; longest losing run {streak} weeks", "",
                  "**Secondary (never changes the verdict):**", ""]
        ta = trades(pair, weeks, rates, which="all")
        tn = trades(pair, weeks, rates, which="not_quiet")
        sa = verdict([x["norm"] for x in ta], f"cqw-all:{pair}")[1]
        sn = verdict([x["norm"] for x in tn], f"cqw-nq:{pair}")[1]
        lo, hi = boot_diff_ci([x["norm"] for x in tq], [x["norm"] for x in tn], f"cqw-diff:{pair}")
        lines += [f"- Carry in every week (no quiet filter): {fmt(sa)}",
                  f"- Carry after non-quiet weeks: {fmt(sn)}",
                  f"- Does 'quiet' add anything? Quiet minus non-quiet mean {s['mean'] - sn['mean']:+.3f}, "
                  f"90% interval {lo:+.3f} to {hi:+.3f}"]
        for label, a, b in SUBPERIODS:
            sub = [x["norm"] for x in tq if a <= x["week"] <= b]
            if sub:
                lines.append(f"- {label}: N {len(sub)}, mean {statistics.fmean(sub):+.3f}, "
                             f"winning weeks {100 * sum(x > 0 for x in sub) / len(sub):.0f}%"
                             + (" — INSUFFICIENT (N < 20)" if len(sub) < 20 else ""))
        per_year = defaultdict(list)
        for x in tq:
            per_year[x["week"].year].append(x["pips"])
        lines.append("- Net pips by year: " + ", ".join(f"{y} {sum(v):+.0f} ({len(v)})" for y, v in sorted(per_year.items())))
        for label, kw in (("financing markup 0%", {"markup": 0.0}), ("financing markup 2%", {"markup": 2.0}),
                          ("spread x1.5", {"spread_mult": 1.5})):
            ss = verdict([x["norm"] for x in trades(pair, weeks, rates, **kw)], f"cqw-sens:{pair}:{label}")[1]
            lines.append(f"- Cost sensitivity, {label}: mean {ss['mean']:+.3f}, lower bound {ss['lower95']:+.3f}")
        lines.append("")
    with open(report, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("VERDICTS:", {p: v for p, (v, _) in summary.items()})


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "selftest":
        sys.exit(0 if selftest() else 1)
    elif mode == "counts":
        counts(sys.argv[2], sys.argv[3])
    elif mode == "full":
        full(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit(f"unknown mode {mode}")
