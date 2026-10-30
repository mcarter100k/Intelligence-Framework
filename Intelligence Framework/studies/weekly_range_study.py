"""Weekly range study (exploratory, report-only): what happens in weeks whose
range is 200+ pips versus under 200, on GBP_AUD and GBP_JPY.

usage: python3 -I weekly_range_study.py <env_file> <out_dir> <report_md>

Span: the USED partition (data_map_spec §1, §11.2), learning only, never
proof. Weeks of 2021-05-03 (after the seal embargo) through the week ending
2026-09-04 (before the FORWARD span). OANDA mid candles with the live
feed's default alignment: trading runs Sunday 17:00 to Friday 17:00 New
York, and OANDA stamps the week at the previous Friday 17:00. Anything this finds is a hypothesis, to be confirmed by a
pre-registered test on the untouched 2005-2013 STUDY data.
"""
import csv
import math
import os
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import history_depth_oanda_probe as P  # noqa: E402  (read-only client)

NY = ZoneInfo("America/New_York")
UTC = timezone.utc
# OANDA stamps a weekly candle at the PREVIOUS Friday 17:00 New York (observed
# 2026-10-29: the week of 2021-05-03 is stamped 2021-04-30T21:00Z).
FROM = datetime(2021, 5, 3, 0, 0, tzinfo=UTC)          # containing week is stamped 2021-04-30 21:00Z
TO = datetime(2026, 9, 4, 20, 0, tzinfo=UTC)           # excludes the week stamped 2026-09-04 (FORWARD)
FIRST_ALLOWED = datetime(2021, 4, 30, 21, 0, tzinfo=UTC)   # after the embargo; the Apr 26 week is stamped Apr 23
PIP = {"GBP_AUD": 0.0001, "GBP_JPY": 0.01}
BIG = 200
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]


def fetch(cl, pair, gran):
    st, p = cl.candles(pair, {"granularity": gran, "price": "M", "from": P.iso(FROM), "to": P.iso(TO)})
    if st != 200:
        raise RuntimeError(f"{pair} {gran}: HTTP {st} {p}")
    out = {}
    for c in p["candles"]:
        t = P.parse(c["time"])
        if t < FIRST_ALLOWED or t >= TO:
            raise RuntimeError(f"{pair} {gran}: candle {t} outside the USED window; aborting")
        if c.get("complete", True):
            out[t] = tuple(float(c["mid"][k]) for k in "ohlc")
    return out


def session_day(t):
    return (t.astimezone(NY) + timedelta(hours=7)).date()


def wilson(k, n):
    if n == 0:
        return "—"
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return f"{100 * p:.0f}% ({k}/{n}; 95% CI {100 * (c - h):.0f}–{100 * (c + h):.0f}%)"


def build_weeks(pair, w, d):
    pip = PIP[pair]
    starts = sorted(w)
    days_by_week = defaultdict(list)
    for t in sorted(d):
        wk = max((s for s in starts if s <= t), default=None)
        if wk is not None:
            days_by_week[wk].append(t)
    weeks, mismatch = [], []
    for i, s in enumerate(starts):
        o, h, l, c = w[s]
        dts = days_by_week[s]
        if not dts:
            mismatch.append((s, "no daily bars"))
            continue
        dh = max(d[t][1] for t in dts)
        dl = min(d[t][2] for t in dts)
        diffs = (abs(h - dh), abs(l - dl), abs(o - d[dts[0]][0]), abs(c - d[dts[-1]][3]))
        if max(diffs) / pip > 0.5:
            mismatch.append((s, f"weekly vs daily differ by {max(diffs) / pip:.1f} pips"))
        hi_t = min(dts, key=lambda t: (-d[t][1], t))
        lo_t = min(dts, key=lambda t: (d[t][2], t))
        mon = [t for t in dts if session_day(t).weekday() == 0]
        rng = (h - l) / pip
        body = (c - o) / pip
        wk = {
            "start": s, "range": rng, "body": body, "dir": "up" if c > o else "down" if c < o else "flat",
            "body_share": abs(body) / rng if rng else 0.0,
            "close_loc": (c - l) / (h - l) if h > l else 0.5,
            "hi_day": DAYS[session_day(hi_t).weekday()], "lo_day": DAYS[session_day(lo_t).weekday()],
            "first": "low first" if lo_t < hi_t else "high first" if hi_t < lo_t else "same day",
            "n_days": len(dts),
        }
        if mon:
            mo, mh, ml, mc = d[mon[0]]
            wk["mon_dir"] = "up" if mc > mo else "down" if mc < mo else "flat"
            wk["mon_share"] = (mh - ml) / pip / rng if rng else 0.0
            wk["extreme_on_mon"] = wk["hi_day"] == "Mon" or wk["lo_day"] == "Mon"
        weeks.append(wk)
    for i, wk in enumerate(weeks):
        wk["prev"] = weeks[i - 1] if i else None
        wk["next"] = weeks[i + 1] if i + 1 < len(weeks) else None
        prior = [x["range"] for x in weeks[max(0, i - 26):i]]
        wk["med26"] = statistics.median(prior) if len(prior) == 26 else None
    return weeks, mismatch


def describe(group):
    n = len(group)
    if n == 0:
        return ["(no weeks)"]
    lines = []
    flag = " — INSUFFICIENT (N < 20)" if n < 20 else ""
    lines.append(f"- Weeks: **{n}**{flag}. Range median {statistics.median(x['range'] for x in group):.0f} pips; "
                 f"net move (open to close) median {statistics.median(abs(x['body']) for x in group):.0f} pips")
    lines.append(f"- Closed up: {wilson(sum(x['dir'] == 'up' for x in group), n)}")
    lines.append(f"- Trend week (open-to-close ≥ 60% of the range): {wilson(sum(x['body_share'] >= 0.6 for x in group), n)}")
    lines.append(f"- Indecision week (open-to-close ≤ 30% of the range): {wilson(sum(x['body_share'] <= 0.3 for x in group), n)}")
    lines.append(f"- Closed in the top or bottom quarter of its range: "
                 f"{wilson(sum(x['close_loc'] >= 0.75 or x['close_loc'] <= 0.25 for x in group), n)}")
    hi = Counter(x["hi_day"] for x in group)
    lo = Counter(x["lo_day"] for x in group)
    lines.append("- Day the week's high was set: " + ", ".join(f"{d} {hi[d]}" for d in DAYS))
    lines.append("- Day the week's low was set: " + ", ".join(f"{d} {lo[d]}" for d in DAYS))
    ends = sum(x["hi_day"] in ("Mon", "Fri") or x["lo_day"] in ("Mon", "Fri") for x in group)
    both_inside = sum(x["hi_day"] not in ("Mon", "Fri") and x["lo_day"] not in ("Mon", "Fri") for x in group)
    lines.append(f"- At least one extreme on Monday or Friday: {wilson(ends, n)}; both extremes Tue–Thu: {wilson(both_inside, n)}")
    withmon = [x for x in group if "mon_dir" in x and x["dir"] != "flat"]
    lines.append(f"- Monday closed the same way as the week: {wilson(sum(x['mon_dir'] == x['dir'] for x in withmon), len(withmon))}")
    lines.append(f"- High or low of the week set on Monday: {wilson(sum(x['extreme_on_mon'] for x in withmon), len(withmon))}")
    if withmon:
        lines.append(f"- Monday's own range as a share of the week's: median {100 * statistics.median(x['mon_share'] for x in withmon):.0f}%")
    nxt = [x for x in group if x["next"] and x["dir"] != "flat" and x["next"]["dir"] != "flat"]
    lines.append(f"- Next week closed the same way (continuation): {wilson(sum(x['next']['dir'] == x['dir'] for x in nxt), len(nxt))}")
    nx = [x for x in group if x["next"]]
    lines.append(f"- Next week was also {BIG}+ pips: {wilson(sum(x['next']['range'] >= BIG for x in nx), len(nx))}")
    pv = [x for x in group if x["prev"]]
    lines.append(f"- Previous week was {BIG}+ pips: {wilson(sum(x['prev']['range'] >= BIG for x in pv), len(pv))}")
    return lines


def weekday_weighted_baseline(day_ranges, n_weeks=40000, steps_per_day=96, seed=7):
    """The random walk again, with each weekday's share of movement set from
    that pair's real median daily range (midweek is busier on some pairs)."""
    import numpy as np
    rng = np.random.default_rng(seed)
    sd = np.repeat(np.array(day_ranges, float) / np.mean(day_ranges), steps_per_day)
    path = np.concatenate([np.zeros((n_weeks, 1)),
                           np.cumsum(rng.standard_normal((n_weeks, 5 * steps_per_day)) * sd, axis=1)], axis=1)
    hd = np.minimum(np.maximum(path.argmax(1) - 1, 0) // steps_per_day, 4)
    ld = np.minimum(np.maximum(path.argmin(1) - 1, 0) // steps_per_day, 4)
    edge = ((hd == 0) | (hd == 4) | (ld == 0) | (ld == 4)).mean()
    mon = (np.sign(path[:, steps_per_day]) == np.sign(path[:, -1])).mean()
    return 100 * (1 - edge), 100 * mon


def random_walk_baseline(n_weeks=20000, steps_per_day=96, seed=20261029):
    """What the same measures read on directionless random-walk weeks (5 equal
    days, no drift, no volatility clustering). Day-of-week and Monday-agreement
    effects that match this are mechanical, not tendencies."""
    import numpy as np
    rng = np.random.default_rng(seed)
    steps = rng.standard_normal((n_weeks, 5 * steps_per_day))
    path = np.concatenate([np.zeros((n_weeks, 1)), np.cumsum(steps, axis=1)], axis=1)
    hi_i, lo_i = path.argmax(axis=1), path.argmin(axis=1)
    hi_day = np.minimum((np.maximum(hi_i - 1, 0)) // steps_per_day, 4)
    lo_day = np.minimum((np.maximum(lo_i - 1, 0)) // steps_per_day, 4)
    rng_w = path.max(axis=1) - path.min(axis=1)
    body = path[:, -1]
    share = np.abs(body) / rng_w
    loc = (path[:, -1] - path.min(axis=1)) / rng_w
    mon_close = path[:, steps_per_day]
    mon_rng = path[:, :steps_per_day + 1].max(axis=1) - path[:, :steps_per_day + 1].min(axis=1)
    out = {}
    for label, m in (("all weeks", np.ones(n_weeks, bool)),
                     ("above-median range", rng_w > np.median(rng_w)),
                     ("at/below-median range", rng_w <= np.median(rng_w))):
        pct = lambda x: f"{100 * x[m].mean():.0f}%"
        edge = (hi_day == 0) | (hi_day == 4) | (lo_day == 0) | (lo_day == 4)
        out[label] = {
            "Trend week": pct(share >= 0.6), "Indecision week": pct(share <= 0.3),
            "Close in top/bottom quarter": pct((loc >= 0.75) | (loc <= 0.25)),
            "High set Mon or Fri": pct((hi_day == 0) | (hi_day == 4)),
            "At least one extreme Mon or Fri": pct(edge),
            "Monday same way as week": pct(np.sign(mon_close) == np.sign(body)),
            "Extreme set on Monday": pct((hi_day == 0) | (lo_day == 0)),
            "Monday range share (median)": f"{100 * np.median((mon_rng / rng_w)[m]):.0f}%",
            "Next week continues (independent weeks)": "50%",
        }
    return out


def main():
    env_file, out_dir, report = sys.argv[1:4]
    cl = P.Client(P.load_env(env_file))
    out = ["# Weekly range study — 200+ pip weeks vs under 200 (exploratory)", "",
           "**Span:** weeks of 2021-05-03 → 2026-08-31 (USED partition: learning only, never proof). "
           "OANDA mid candles; a week runs Sunday 2 PM PDT (5 PM New York) to Friday 2 PM PDT. "
           "Percentages carry 95% confidence intervals; where two groups' intervals overlap heavily, "
           "the difference may be noise. Around 15 comparisons per pair are shown, so about one in "
           "twenty will look different by chance alone. **Nothing here is an edge**; a pattern found "
           "here is a hypothesis to test, pre-registered, on the untouched 2005–2013 data.", ""]
    for pair in ("GBP_AUD", "GBP_JPY"):
        w, d = fetch(cl, pair, "W"), fetch(cl, pair, "D")
        for gran, rows in (("W", w), ("D", d)):
            with open(os.path.join(out_dir, f"{pair}_{gran}.csv"), "w", newline="") as fh:
                cw = csv.writer(fh)
                cw.writerow(["time_utc", "o", "h", "l", "c"])
                for t in sorted(rows):
                    cw.writerow([t.isoformat(), *rows[t]])
        weeks, mismatch = build_weeks(pair, w, d)
        big = [x for x in weeks if x["range"] >= BIG]
        small = [x for x in weeks if x["range"] < BIG]
        rel = [x for x in weeks if x["med26"] is not None]
        rel_big = [x for x in rel if x["range"] > x["med26"]]
        rel_small = [x for x in rel if x["range"] <= x["med26"]]
        name = pair.replace("_", "/")
        by_day = defaultdict(list)
        for t, (o_, h_, l_, c_) in d.items():
            wd = session_day(t).weekday()
            if wd < 5:
                by_day[wd].append((h_ - l_) / PIP[pair])
        day_med = [statistics.median(by_day[i]) for i in range(5)]
        mid_null, mon_null = weekday_weighted_baseline(day_med)
        both_mid = sum(x["hi_day"] not in ("Mon", "Fri") and x["lo_day"] not in ("Mon", "Fri") for x in weeks)
        withmon_all = [x for x in weeks if "mon_dir" in x and x["dir"] != "flat"]
        mon_same = sum(x["mon_dir"] == x["dir"] for x in withmon_all)
        out += [f"## {name}", "",
                f"**Data check:** {len(weeks)} weeks; weekly candles agree with their daily candles "
                f"(high, low, open, close within 0.5 pip) in {len(weeks) - len(mismatch)} of {len(weeks)} weeks."
                + (" Disagreements: " + "; ".join(f"{s.date()} {m}" for s, m in mismatch[:10]) if mismatch else ""),
                f"Weeks with fewer than 5 daily bars (holidays): {sum(x['n_days'] < 5 for x in weeks)}.", "",
                f"**Split:** {len(big)} weeks of {BIG}+ pips ({100 * len(big) / len(weeks):.0f}%), "
                f"{len(small)} under {BIG}.", "",
                "**Against the weekday-weighted random walk** (median daily range Mon–Fri: "
                + ", ".join(f"{DAYS[i]} {day_med[i]:.0f}" for i in range(5)) + " pips):",
                f"- Both extremes Tue–Thu, all weeks: {wilson(both_mid, len(weeks))}; random walk {mid_null:.1f}%",
                f"- Monday closed the same way as the week, all weeks: {wilson(mon_same, len(withmon_all))}; "
                f"random walk {mon_null:.1f}%", "",
                f"### {BIG}+ pip weeks", ""] + describe(big) + [
                "", f"### Under {BIG} pips", ""] + describe(small) + [
                "", "### Second view: big for its time (range above the pair's previous 26-week median)", "",
                f"{len(rel)} weeks have 26 weeks of history before them.", "", "**Above the median:**", ""] + \
            describe(rel_big) + ["", "**At or below the median:**", ""] + describe(rel_small) + [""]
    base = random_walk_baseline()
    out += ["## What pure randomness gives (the baseline)", "",
            "20,000 simulated directionless weeks: five equal days, no drift, no volatility "
            "clustering. A real tendency has to differ from these numbers, not from 50%.", "",
            "| Measure | all weeks | above-median range | at/below-median range |", "|---|---|---|---|"]
    for k in base["all weeks"]:
        out.append(f"| {k} | " + " | ".join(base[g][k] for g in base) + " |")
    out.append("")
    with open(report, "w") as fh:
        fh.write("\n".join(out) + "\n")
    print("\n".join(out))
    print("requests", cl.requests)


if __name__ == "__main__":
    main()
