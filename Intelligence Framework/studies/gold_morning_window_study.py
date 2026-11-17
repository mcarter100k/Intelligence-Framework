"""gold_morning_window_study.py — GMW-1, gold's 4-7 AM PT window
(docs/specs/gold_morning_window_spec.md, signed and frozen 2026-11-17 at
sha256 27d6738ccf8dbdda18417aebc8fc89373f5a8926bbdf1cca69f4ecc24d357326).

usage:
  python3 -I gold_morning_window_study.py counts <legs_archive_dir>
  python3 -I gold_morning_window_study.py full <legs_archive_dir> <report_md>

counts prints days, skips and trades per cell, with no R and no outcome.
full runs once: it refuses if the report file exists, if the spec's bytes are
not the signed ones, or if any data or event file's sha256 differs.

Implementation notes (each follows the spec; recorded so the run can be read):
- A trade day is a Pacific calendar date with H1 bars opening at 04:00, 05:00
  and 06:00 PT. Entry is the 06:00 bar's close (7:00 AM PT); the hold is the
  bars opening 07:00-12:00 PT; the exit is the 12:00 bar's close (1:00 PM PT).
- The day's session is history_study_convert.session_day of its 04:00 PT bar
  (the same Pacific date); ATR and the 6-month trend use only sessions before it.
- Release day: a session with NFP or CPI in studies/us_events_2005_2013.csv.
  FOMC day: the session holding any statement date in
  studies/fomc_statement_times_2006_2013.csv (session_day of the statement time,
  2:15 PM ET where the time is blank), whatever the time.
- §4.2 order: the base rule gives the full-sample verdict and the verdict
  without FOMC days; if they differ the cell is INCONCLUSIVE (FOMC condition).
  Otherwise a SUPPORTED verdict must also meet the SUPPORTED conditions on the
  non-release days, or it is INCONCLUSIVE pending GNC-1.
"""
import bisect
import csv
import hashlib
import math
import os
import random
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "foundation", "tools"))
import history_study_convert as C  # noqa: E402
from gold_rule_costs import held_nights  # noqa: E402
from power_check import bootstrap_lower_bound, bootstrap_upper_bound  # noqa: E402

PT, NY = ZoneInfo("America/Los_Angeles"), ZoneInfo("America/New_York")
SPEC = os.path.join(ROOT, "docs", "specs", "gold_morning_window_spec.md")
SPEC_SHA = "27d6738ccf8dbdda18417aebc8fc89373f5a8926bbdf1cca69f4ecc24d357326"
DATA = {"H1": ("XAU_USD_H1.csv", "eabec6652e055540b256aa743971a1a5aa5cbb459e94b4887da6f28b8e02a4be"),
        "D": ("XAU_USD_D.csv", "6202a13d86459d2d3453c31ea9ddf40a3aca44243a6d4ff75bf3d0c165d0e3ca")}
EVENTS = (os.path.join(HERE, "us_events_2005_2013.csv"),
          "0f898806a110f5a4c1c063bd772e93102085eb743b47069d95f788103fed8aa2")
FOMC = (os.path.join(HERE, "fomc_statement_times_2006_2013.csv"),
        "f5601b60c93a1e789c7bd3c41818178ddf50462ae22e054e60b325220ef94981")
ERAS = ("STUDY", "USED")
EXAM = ("2014-01-01", "2021-04-25")
GOLD_START = "2006-03-20T22:00"

WINDOW = (4, 5, 6)
HOLD = (7, 8, 9, 10, 11, 12)
BUFFER_ATR = 0.05
FLOOR_B, FLOOR_A, CAP = 0.30, 0.15, 1.0
ATR_N, TREND_N = 14, 126
SPREAD, SPREAD_STRESS, SPREAD_PCT = 0.50, 1.00, 0.00012
M = 0.05
ALPHA = 1 - (1 - 0.05) ** 0.5            # Šidák, family of two (0.025321)
CONF_LOWER = 1 - ALPHA                   # 0.974679
CONF_UPPER = 0.90
RESAMPLES, SEED, MIN_N = 20000, 7, 20


# ── data ─────────────────────────────────────────────────────────────────────

def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def check(path, want, what):
    got = sha(path)
    if got != want:
        raise SystemExit(f"{what}: sha256 {got} is not the pinned {want}; refusing")


def load(path, want):
    """{era: {utc datetime: (o, h, l, c)}} for STUDY and USED. FORWARD rows are
    skipped by span label; a row dated in the sealed span is refused."""
    check(path, want, path)
    out = {e: {} for e in ERAS}
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            t = r["time_utc"]
            if EXAM[0] <= t[:10] <= EXAM[1]:
                raise SystemExit(f"{path}: row {t} lies in the sealed span {EXAM}; refusing")
            if r["span"] not in out or t < GOLD_START:
                continue
            out[r["span"]][datetime.fromisoformat(t)] = (float(r["o"]), float(r["h"]), float(r["l"]), float(r["c"]))
    return out


def session_table(d1):
    """Sorted session days, closes and true ranges (TR[0] None) of one era's D bars."""
    ts = sorted(d1)
    days = [C.session_day(t) for t in ts]
    closes = [d1[t][3] for t in ts]
    trs = [None] + [max(d1[ts[k]][1] - d1[ts[k]][2], abs(d1[ts[k]][1] - closes[k - 1]),
                        abs(d1[ts[k]][2] - closes[k - 1])) for k in range(1, len(ts))]
    return days, closes, trs


def atr_before(sess, sday):
    days, _, trs = sess
    k = bisect.bisect_left(days, sday)                 # sessions completed before sday
    return statistics.fmean(trs[k - ATR_N:k]) if k - ATR_N >= 1 else None


def trend_before(sess, sday):
    days, closes, _ = sess
    k = bisect.bisect_left(days, sday)
    if k - 1 - TREND_N < 0:
        return None
    d = closes[k - 1] - closes[k - 1 - TREND_N]
    return 1 if d > 0 else -1 if d < 0 else 0


def pt_days(h1):
    """{PT date: {PT hour: (o, h, l, c)}}."""
    out = defaultdict(dict)
    for t, bar in h1.items():
        p = t.astimezone(PT)
        out[p.date()][p.hour] = bar
    return out


def event_sessions(events_csv, fomc_csv):
    rel = set()
    with open(events_csv, newline="") as fh:
        for r in csv.DictReader(fh):
            if r["event"] in ("NFP", "CPI"):
                rel.add(datetime.fromisoformat(r["date"]).date())
    fomc = set()
    with open(fomc_csv, newline="") as fh:
        for r in csv.DictReader(fh):
            hh, mm = map(int, (r["time_et"] or "14:15").split(":"))
            t = datetime.fromisoformat(r["date"]).replace(hour=hh, minute=mm, tzinfo=NY)
            fomc.add(C.session_day(t))
    return rel, fomc


# ── days and trades ──────────────────────────────────────────────────────────

def build_days(h1, d1, rel=frozenset(), fomc=frozenset()):
    """One record per Pacific date with window bars; skip reasons counted."""
    sess = session_table(d1)
    days, skips = [], Counter()
    for day, bars in sorted(pt_days(h1).items()):
        if not any(h in bars for h in WINDOW):
            continue                                    # no morning session that date (weekend, Sunday open)
        if not all(h in bars for h in WINDOW):
            skips["missing window bar"] += 1
            continue
        sday = C.session_day(datetime(day.year, day.month, day.day, 4, tzinfo=PT))
        atr = atr_before(sess, sday)
        if atr is None:
            skips["ATR warm-up"] += 1
            continue
        wh = max(bars[h][1] for h in WINDOW)
        wl = min(bars[h][2] for h in WINDOW)
        move = bars[6][3] - bars[4][0]
        if move == 0:
            skips["zero move"] += 1
            continue
        days.append({"date": day, "sday": sday, "atr": atr, "move": move, "dir": 1 if move > 0 else -1,
                     "d": (wh - wl) + BUFFER_ATR * atr, "bars": bars, "trend": trend_before(sess, sday),
                     "release": sday in rel, "fomc": sday in fomc})
    return days, skips


def population(days, floor=FLOOR_B, cap=CAP):
    return [x for x in days if x["d"] >= floor * x["atr"] and (cap is None or x["d"] <= cap * x["atr"])]


def simulate(day, side, entry_hour=7, exit_hour=12):
    """One trade: side +1 long, -1 short; stop distance d (identical in both cells).
    Returns None if the exit bar is missing. Stop checked on every present bar of
    the hold; a touched stop counts first; a bar opening beyond the stop fills at
    its open."""
    bars, d = day["bars"], day["d"]
    if entry_hour - 1 not in bars or exit_hour not in bars:
        return None
    e = bars[entry_hour - 1][3]
    stop = e - side * d
    missing = [h for h in range(entry_hour, exit_hour + 1) if h not in bars]
    for h in range(entry_hour, exit_hour + 1):
        if h not in bars:
            continue
        o, hi, lo, _ = bars[h]
        if (o <= stop) if side == 1 else (o >= stop):
            return {"R": side * (o - e) / d, "stopped": True, "gap": True, "entry": e, "missing": missing}
        if (lo <= stop) if side == 1 else (hi >= stop):
            return {"R": -1.0, "stopped": True, "gap": False, "entry": e, "missing": missing}
    return {"R": side * (bars[exit_hour][3] - e) / d, "stopped": False, "gap": False, "entry": e, "missing": missing}


def managed(day, side):
    """Side result 7: the owner's management on H1 bars. At +1R stop to breakeven and
    close 50%; from +1.5R trail 0.5R behind the best price (applied from the next
    bar); flat by 1:00 PM PT. Stop checked first within a bar."""
    bars, d = day["bars"], day["d"]
    if 6 not in bars or 12 not in bars:
        return None
    e = bars[6][3]
    stop, pos, banked, be, trail = e - side * d, 1.0, 0.0, False, False
    for h in HOLD:
        if h not in bars:
            continue
        o, hi, lo, _ = bars[h]
        if (o <= stop) if side == 1 else (o >= stop):
            return banked + pos * side * (o - e) / d
        if (lo <= stop) if side == 1 else (hi >= stop):
            return banked + pos * side * (stop - e) / d
        best = hi if side == 1 else lo
        if not be and side * (best - e) >= d:
            banked, pos, be = banked + 0.5, 0.5, True
            stop = e                                    # breakeven
        if side * (best - e) >= 1.5 * d:
            trail = True
        if trail:
            cand = best - side * 0.5 * d
            stop = max(stop, cand) if side == 1 else min(stop, cand)
    return banked + pos * side * (bars[12][3] - e) / d


def trades(days, cell, entry_hour=7, exit_hour=12, spread=SPREAD, pct=False):
    """cell 'B1' (continuation) or 'B2' (fade). Net R after the given spread."""
    out, skipped_exit = [], 0
    for x in days:
        side = x["dir"] if cell == "B1" else -x["dir"]
        s = simulate(x, side, entry_hour, exit_hour)
        if s is None:
            skipped_exit += 1
            continue
        t_in = datetime(x["date"].year, x["date"].month, x["date"].day, entry_hour, tzinfo=PT)
        t_out = datetime(x["date"].year, x["date"].month, x["date"].day, exit_hour + 1, tzinfo=PT)
        nights = held_nights(t_in, t_out)
        assert nights == 0, f"financing nights {nights} on {x['date']}"
        cost = (SPREAD_PCT * s["entry"] if pct else spread) / x["d"]
        out.append({"date": x["date"], "side": side, "gross": s["R"], "cost": cost, "R": s["R"] - cost,
                    "stopped": s["stopped"], "gap": s["gap"], "missing": s["missing"], "release": x["release"],
                    "fomc": x["fomc"], "trend": x["trend"], "move_atr": abs(x["move"]) / x["atr"]})
    return out, skipped_exit


# ── statistics and verdicts ──────────────────────────────────────────────────

def without_best(rs):
    k = math.ceil(0.01 * len(rs))
    return statistics.fmean(sorted(rs)[:len(rs) - k]) if len(rs) > k else float("nan")


def summarize(rs, bounds=True):
    n = len(rs)
    s = {"n": n}
    if n == 0:
        return s
    s.update(mean=statistics.fmean(rs), median=statistics.median(rs),
             sd=statistics.stdev(rs) if n > 1 else float("nan"), wob=without_best(rs))
    if bounds and n >= 2:
        s["lower"] = bootstrap_lower_bound(rs, conf=CONF_LOWER, iters=RESAMPLES, seed=SEED)
        s["upper"] = bootstrap_upper_bound(rs, conf=CONF_UPPER, iters=RESAMPLES, seed=SEED)
    return s


def base_verdict(s):
    """§4.2: one line m for pass and fail. SUPPORTED is tested first; REFUTED uses
    the uncorrected 90% upper bound against the same m."""
    if s["n"] < MIN_N:
        return "INSUFFICIENT"
    if s["lower"] > M and s["wob"] > 0:
        return "SUPPORTED"
    if s["upper"] < M:
        return "REFUTED"
    return "INCONCLUSIVE"


def final_verdict(ts):
    """§4.2 with the FOMC (C10) and release-day (C7) conditions."""
    full = summarize([t["R"] for t in ts])
    nofomc = summarize([t["R"] for t in ts if not t["fomc"]])
    nonrel = summarize([t["R"] for t in ts if not t["release"]])
    v, v_nf = base_verdict(full), base_verdict(nofomc)
    if v != v_nf:
        final = "INCONCLUSIVE (FOMC condition)"
    elif v == "SUPPORTED" and not (nonrel["n"] >= MIN_N and nonrel["lower"] > M and nonrel["wob"] > 0):
        final = "INCONCLUSIVE pending GNC-1 (release-day condition)"
    else:
        final = v
    return {"final": final, "base": v, "base_no_fomc": v_nf, "full": full, "no_fomc": nofomc, "non_release": nonrel}


def exam_rule(finals):
    sup = [c for c, v in finals.items() if v == "SUPPORTED"]
    if len(sup) == 2:
        return "both cells SUPPORTED: a test defect; neither goes to the sealed exam; the run is reviewed (§4.3)"
    if len(sup) == 1:
        return f"{sup[0]} is the cell that would go to the sealed exam (still needs T1 and real venue costs)"
    return "no cell SUPPORTED: nothing goes to the sealed exam"


def block_bounds(ts, iters=RESAMPLES, seed=SEED):
    """Block bootstrap by calendar month (side result): resample months."""
    months = defaultdict(list)
    for t in ts:
        months[(t["date"].year, t["date"].month)].append(t["R"])
    sums = [(sum(v), len(v)) for v in months.values()]
    rng = random.Random(seed)
    means = []
    for _ in range(iters):
        pick = rng.choices(sums, k=len(sums))
        means.append(sum(a for a, _ in pick) / sum(b for _, b in pick))
    means.sort()
    return means[int((1 - CONF_LOWER) * iters)], means[int(CONF_UPPER * iters) - 1]


# ── report ───────────────────────────────────────────────────────────────────

def fmt(s, verdict=None):
    if s["n"] == 0:
        return "N 0"
    out = (f"N {s['n']}; mean {s['mean']:+.4f}R; median {s['median']:+.4f}R; SD {s['sd']:.3f}R; "
           f"mean without best 1% {s['wob']:+.4f}R")
    if "lower" in s:
        out += f"; {100 * CONF_LOWER:.2f}% lower {s['lower']:+.4f}R; 90% upper {s['upper']:+.4f}R"
    if verdict:
        out += f" -> **{verdict}**"
    return out


def short(rs):
    if not rs:
        return "N 0"
    sd = statistics.stdev(rs) if len(rs) > 1 else float("nan")
    return f"N {len(rs)}; mean {statistics.fmean(rs):+.4f}R; median {statistics.median(rs):+.4f}R; SD {sd:.3f}R"


def era_report(era, days, skips, events_on):
    L = []
    pop = population(days)
    L.append(f"## {era}")
    L.append("")
    L.append(f"- Days with a complete window and ATR: {len(days)}; skipped {dict(skips)}")
    L.append(f"- Verdict population (floor B, d >= 0.30 ATR; cap d <= 1.0 ATR): {len(pop)} days; "
             f"floor-B skips {sum(1 for x in days if x['d'] < FLOOR_B * x['atr'])}; "
             f"cap skips {sum(1 for x in days if x['d'] >= FLOOR_B * x['atr'] and x['d'] > CAP * x['atr'])}")
    finals = {}
    cell_ts = {}
    for cell in ("B1", "B2"):
        ts, sk = trades(pop, cell)
        cell_ts[cell] = ts
        L.append("")
        L.append(f"### {era} {cell} ({'continuation' if cell == 'B1' else 'fade'}); missing exit bar skipped {sk}")
        if events_on:
            fv = final_verdict(ts)
            finals[cell] = fv["final"]
            L.append(f"- **Primary (net of $0.50):** {fmt(fv['full'], fv['base'])}")
            L.append(f"- Without the FOMC days: {fmt(fv['no_fomc'], fv['base_no_fomc'])}")
            L.append(f"- Non-release days only: {fmt(fv['non_release'])}")
            L.append(f"- **FINAL VERDICT {cell}: {fv['final']}**")
        else:
            s = summarize([t["R"] for t in ts])
            v = base_verdict(s) if s["n"] else "INSUFFICIENT"
            finals[cell] = v
            L.append(f"- **Learning check only (no event data for this span; conditions not applicable):** {fmt(s, v)}")
        lo, hi = block_bounds(ts) if ts else (float("nan"), float("nan"))
        L.append(f"- Block bootstrap by month: {100 * CONF_LOWER:.2f}% lower {lo:+.4f}R; 90% upper {hi:+.4f}R")
    if events_on:
        L.append("")
        L.append(f"**Exam rule (§4.3):** {exam_rule(finals)}")
    # side results
    L.append("")
    L.append(f"### {era} side results (never change a verdict)")
    for cell in ("B1", "B2"):
        ts = cell_ts[cell]
        g = [t["gross"] for t in ts]
        st_, _ = trades(pop, cell, spread=SPREAD_STRESS)
        pc, _ = trades(pop, cell, pct=True)
        L.append(f"- [1] {cell} before costs: {short(g)}; $1.00 spread: {short([t['R'] for t in st_])}; "
                 f"0.012% spread: {short([t['R'] for t in pc])}")
        unc, _ = trades(population(days, FLOOR_B, None), cell)
        removed = [t for t in unc if t["date"] not in {x['date'] for x in pop}]
        tot = sum(t["R"] for t in unc)
        L.append(f"- [2] {cell} uncapped: {short([t['R'] for t in unc])}; the cap removes {len(removed)} of {len(unc)} "
                 f"trades ({100 * len(removed) / len(unc):.1f}%) carrying total {sum(t['R'] for t in removed):+.2f}R of the "
                 f"uncapped total {tot:+.2f}R")
        fa, _ = trades(population(days, FLOOR_A, CAP), cell)
        sfa = summarize([t["R"] for t in fa])
        L.append(f"- [3] {cell} floor A (d >= 0.15 ATR): {fmt(sfa, base_verdict(sfa))}")
        e8, _ = trades(pop, cell, entry_hour=8)
        L.append(f"- [4] {cell} entry 8:00 AM PT: {short([t['R'] for t in e8])}")
        x10, _ = trades(pop, cell, exit_hour=9)
        x12, _ = trades(pop, cell, exit_hour=11)
        L.append(f"- [5] {cell} exit 10:00 AM PT: {short([t['R'] for t in x10])}; exit 12:00 PM PT: {short([t['R'] for t in x12])}")
        L.append(f"- [6] {cell} window move >= 0.5 ATR: {short([t['R'] for t in ts if t['move_atr'] >= 0.5])}; "
                 f"below: {short([t['R'] for t in ts if t['move_atr'] < 0.5])}")
        mg = []
        for x in pop:
            side = x["dir"] if cell == "B1" else -x["dir"]
            r = managed(x, side)
            if r is not None:
                mg.append(r - SPREAD / x["d"])
        L.append(f"- [7] {cell} owner's management (net $0.50): {short(mg)}")
        L.append(f"- [8] {cell} longs: {short([t['R'] for t in ts if t['side'] == 1])}; shorts: "
                 f"{short([t['R'] for t in ts if t['side'] == -1])}; 6-month trend up: "
                 f"{short([t['R'] for t in ts if t['trend'] == 1])}; down: {short([t['R'] for t in ts if t['trend'] == -1])}")
        years = defaultdict(list)
        for t in ts:
            years[t["date"].year].append(t["R"])
        L.append(f"  - {cell} by year (N, mean R): " + "; ".join(f"{y} {len(v)} {statistics.fmean(v):+.3f}"
                                                              for y, v in sorted(years.items())))
        L.append(f"- [9] {cell} counts: trades {len(ts)}; stopped {sum(t['stopped'] for t in ts)} "
                 f"(gap fills {sum(t['gap'] for t in ts)}); timed exits {sum(not t['stopped'] for t in ts)}; "
                 f"trades with a missing hold bar {sum(1 for t in ts if t['missing'])}")
        costs = [t["cost"] for t in ts]
        L.append(f"- [10] {cell} cost per trade: median {statistics.median(costs):.4f}R, mean {statistics.fmean(costs):.4f}R; "
                 f"share above 0.2R {100 * sum(c > 0.2 for c in costs) / len(costs):.1f}%")
        if events_on:
            L.append(f"- [11] {cell} release days (NFP/CPI; no verdict, outside GNC-1's family): "
                     f"{short([t['R'] for t in ts if t['release']])}; other days: {short([t['R'] for t in ts if not t['release']])}")
            L.append(f"- [12] {cell} FOMC days: {short([t['R'] for t in ts if t['fomc']])}; with/without verdicts in the "
                     f"primary block above")
    miss = sorted({str(t["date"]) for t in cell_ts["B1"] if t["missing"]})
    L.append(f"- Days with a missing bar inside the hold (stop checked on bars present): {len(miss)}"
             + (f": {', '.join(miss[:40])}{' …' if len(miss) > 40 else ''}" if miss else ""))
    return L


def prepare(root):
    rows = {k: load(os.path.join(root, f), s) for k, (f, s) in DATA.items()}
    check(*EVENTS, "us_events_2005_2013.csv")
    check(*FOMC, "fomc_statement_times_2006_2013.csv")
    rel, fomc = event_sessions(EVENTS[0], FOMC[0])
    out = {}
    for era in ERAS:
        on = era == "STUDY"
        days, skips = build_days(rows["H1"][era], rows["D"][era], rel if on else frozenset(), fomc if on else frozenset())
        out[era] = (days, skips, on)
    return out


def counts(root):
    check(SPEC, SPEC_SHA, "spec")
    print("# GMW-1 counts stage (no R, no outcome)\n")
    for era, (days, skips, on) in prepare(root).items():
        pop = population(days)
        noexit = sum(1 for x in pop if 12 not in x["bars"] or 6 not in x["bars"])
        print(f"## {era}")
        print(f"- days with a complete window and ATR: {len(days)}; skipped {dict(skips)}")
        print(f"- floor-B skips {sum(1 for x in days if x['d'] < FLOOR_B * x['atr'])}; cap skips "
              f"{sum(1 for x in days if x['d'] >= FLOOR_B * x['atr'] and x['d'] > CAP * x['atr'])}; "
              f"verdict population {len(pop)}; missing exit bar {noexit}; trades per cell {len(pop) - noexit}")
        print(f"- floor-A population {len(population(days, FLOOR_A, CAP))}; uncapped population "
              f"{len(population(days, FLOOR_B, None))}")
        if on:
            print(f"- in the verdict population: release days {sum(x['release'] for x in pop)}, FOMC days "
                  f"{sum(x['fomc'] for x in pop)}, non-release {sum(not x['release'] for x in pop)}")
        per_year = Counter(x["date"].year for x in pop)
        print(f"- verdict population by year: {dict(sorted(per_year.items()))}")
        print()


def full(root, report):
    if os.path.exists(report):
        raise SystemExit(f"{report} exists: the full run happens once (spec §10)")
    check(SPEC, SPEC_SHA, "spec")
    L = ["# GMW-1 result: gold's 4-7 AM PT window (one pre-registered run)", "",
         f"Spec sha256 {SPEC_SHA} (signed and frozen 2026-11-17). Šidák α {ALPHA:.6f} (family of two), "
         f"lower bound {100 * CONF_LOWER:.2f}%, upper bound 90%, m = +{M:.2f}R, {RESAMPLES} resamples, seed {SEED}.", ""]
    for era, (days, skips, on) in prepare(root).items():
        L += era_report(era, days, skips, on) + [""]
    text = "\n".join(L)
    with open(report, "w") as fh:
        fh.write(text + "\n")
    print(text)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "counts":
        counts(sys.argv[2])
    elif len(sys.argv) == 4 and sys.argv[1] == "full":
        full(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit(__doc__)
