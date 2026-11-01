"""Pre-registered descriptive test: do scheduled US releases (FOMC statement,
CPI, Employment Situation) widen GBP/JPY and GBP/AUD daily ranges?
(docs/specs/us_event_reaction_spec.md). Cells: 2 pairs x 3 events.

usage:
  python3 -I us_event_reaction_test.py selftest
  python3 -I us_event_reaction_test.py counts <env_file> <out_dir>
  python3 -I us_event_reaction_test.py full <out_dir> <report_md>

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

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import history_study_convert as C  # noqa: E402  approved weekend rule
import history_study_gate_s3 as G  # noqa: E402  guarded STUDY fetch

PAIRS = {"GBP_JPY": 0.01, "GBP_AUD": 0.0001}
EVENTS = ("FOMC", "CPI", "NFP")
EVENTS_FILE = os.path.join(HERE, "us_events_2005_2013.csv")
LOOKBACK = 20          # trading days in the normaliser (spec §3)
MATCH_DAYS = 28        # control window, calendar days either side (spec §3)
ROUND_TRIP_DAYS = 3    # spec §7.2
THRESHOLD = 0.10       # materiality (spec §4)
CELLS = len(PAIRS) * len(EVENTS)
ALPHA = 0.05 / CELLS   # Bonferroni, one-sided (spec §4)
RESAMPLES = 20000
LAST_STUDY_DAY = date(2013, 12, 30)
SUBPERIODS = [("2005-01 to 2008-06 (before the crisis)", date(2005, 1, 1), date(2008, 6, 30)),
              ("2008-07 to 2009-06 (the crisis)", date(2008, 7, 1), date(2009, 6, 30)),
              ("2009-07 to 2013-12 (after)", date(2009, 7, 1), date(2013, 12, 31))]


# Events ------------------------------------------------------------------------

def session_of(release_date, time_et):
    """The trading session holding a release: sessions run 17:00 to 17:00 New York, so a
    release at or after 17:00 ET, or on a weekend, belongs to the next weekday's session."""
    d = release_date
    if time_et and time_et >= "17:00":
        d += timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def load_events(path=EVENTS_FILE):
    """Returns ({event: sorted scheduled session dates}, sorted unscheduled FOMC session dates,
    set of all session dates). Dates are mapped to the session that holds the release."""
    sched, unsched = defaultdict(list), []
    with open(path) as fh:
        for r in csv.DictReader(fh):
            d = session_of(date.fromisoformat(r["date"]), r["time_et"].strip())
            if r["event"] not in EVENTS:
                raise ValueError(f"unknown event {r['event']!r}")
            if r["scheduled"].strip().lower() == "true":
                sched[r["event"]].append(d)
            elif r["event"] == "FOMC":
                unsched.append(d)
            else:
                raise ValueError(f"unscheduled {r['event']} on {d}: only FOMC may be unscheduled")
    all_dates = {d for v in sched.values() for d in v} | set(unsched)
    return {e: sorted(sched[e]) for e in EVENTS}, sorted(unsched), all_dates


# Days --------------------------------------------------------------------------

def daily_table(d1c, pip):
    """Converted D1 {open_time: (o,h,l,c)} -> list of day dicts in session order."""
    days = []
    for t in sorted(d1c):
        o, h, l, c = d1c[t]
        days.append({"day": C.session_day(t), "high": h, "low": l, "close": c,
                     "range": (h - l) / pip})
    if days and max(x["day"] for x in days) > LAST_STUDY_DAY:
        raise RuntimeError("a trading day reaches into the embargo")
    for i, x in enumerate(days):
        x["ratio"] = x["move"] = x["round_trip"] = None
        if i < LOOKBACK:
            continue
        norm = statistics.median(d["range"] for d in days[i - LOOKBACK:i])
        if norm <= 0:
            continue
        x["ratio"] = x["range"] / norm
        prev = days[i - 1]["close"]
        delta = x["close"] - prev
        x["move"] = abs(delta) / pip / norm
        if delta != 0 and i + ROUND_TRIP_DAYS < len(days):
            sign = 1 if delta > 0 else -1
            x["round_trip"] = any((days[i + k]["close"] - prev) * sign <= 0
                                  for k in range(1, ROUND_TRIP_DAYS + 1))
    return days


def controls_for(day, days, all_event_dates):
    return [x for x in days
            if x["ratio"] is not None and x["day"] not in all_event_dates
            and x["day"].weekday() == day.weekday() and x["day"] != day
            and abs((x["day"] - day).days) <= MATCH_DAYS]


def paired_effects(days, event_dates, all_event_dates):
    """Per event: paired range-ratio effect vs same-weekday, event-free controls within ±28 days."""
    by_day = {x["day"]: x for x in days}
    out, drops = [], {"no_session": 0, "warm_up": 0, "no_control": 0}
    for d in event_dates:
        x = by_day.get(d)
        if x is None:
            drops["no_session"] += 1
            continue
        if x["ratio"] is None:
            drops["warm_up"] += 1
            continue
        cs = controls_for(d, days, all_event_dates)
        if not cs:
            drops["no_control"] += 1
            continue
        cm = statistics.fmean(c["ratio"] for c in cs)
        cmove = statistics.fmean(c["move"] for c in cs)
        crt = [c["round_trip"] for c in cs if c["round_trip"] is not None]
        out.append({"day": d, "ratio": x["ratio"], "control_mean": cm, "effect": x["ratio"] - cm,
                    "n_controls": len(cs), "move_effect": x["move"] - cmove,
                    "round_trip": x["round_trip"], "control_round_trips": crt})
    return out, drops


# Statistics ------------------------------------------------------------------------

def boot_bounds(xs, seed, alpha=ALPHA, n=RESAMPLES):
    r = random.Random(seed)
    k = len(xs)
    means = sorted(sum(xs[r.randrange(k)] for _ in range(k)) / k for _ in range(n))
    return means[int(alpha * n)], means[int((1 - alpha) * n) - 1]


def classify(lower, upper):
    """The pre-registered verdict rule (spec §5)."""
    if lower >= THRESHOLD:
        return "MATERIAL"
    if upper < THRESHOLD:
        return "NOT MATERIAL"
    return "INCONCLUSIVE"


def verdict(effects, seed, n=RESAMPLES):
    xs = [e["effect"] for e in effects]
    lower, upper = boot_bounds(xs, seed, n=n)
    return classify(lower, upper), {"n": len(xs), "mean": statistics.fmean(xs), "lower": lower,
                                    "upper": upper, "median": statistics.median(xs),
                                    "sd": statistics.stdev(xs) if len(xs) > 1 else float("nan")}


# Self-test ---------------------------------------------------------------------

def _synthetic(start, n_days, range_of):
    """Weekday sessions from `start`; D1 candles opening 17:00 New York the evening before."""
    d1, day = {}, start
    while len(d1) < n_days:
        if day.weekday() < 5:
            open_ny = datetime(day.year, day.month, day.day, 17, 0, tzinfo=C.NY) - timedelta(days=1)
            r = range_of(day)
            d1[open_ny.astimezone(timezone.utc)] = (150.0, 150.0 + r / 2, 150.0 - r / 2, 150.0)
        day += timedelta(days=1)
    return d1


def selftest():
    ok = True

    def check(name, cond):
        nonlocal ok
        ok &= bool(cond)
        print(("PASS " if cond else "FAIL ") + name)

    # Verdict boundaries
    check("rule: lower bound exactly at the threshold is MATERIAL", classify(0.10, 0.5) == "MATERIAL")
    check("rule: lower bound just below is not MATERIAL", classify(0.0999, 0.5) == "INCONCLUSIVE")
    check("rule: upper bound just below the threshold is NOT MATERIAL", classify(-0.2, 0.0999) == "NOT MATERIAL")
    check("rule: upper bound at the threshold is INCONCLUSIVE", classify(-0.2, 0.10) == "INCONCLUSIVE")

    # Session mapping: a candle opening 17:00 New York on Thu 2006-03-09 is the Fri 2006-03-10 session
    t = datetime(2006, 3, 9, 17, 0, tzinfo=C.NY).astimezone(timezone.utc)
    check(f"17:00 New York candle maps to the next date ({C.session_day(t)})", C.session_day(t) == date(2006, 3, 10))

    # Hand-computed ratio: days 1-10 of 100 pips, days 11-20 of 200, day 21 of 300.
    # Day 21's normaliser is the median of the 20 prior days = 150 -> ratio 2.0. A window that
    # wrongly includes the day itself (days 2-21) has median 200 -> ratio 1.5.
    start = date(2006, 1, 2)
    weekdays = [start + timedelta(days=k) for k in range(60) if (start + timedelta(days=k)).weekday() < 5]
    size = {d: (100.0 if i < 10 else 200.0 if i < 20 else 300.0 if i == 20 else 100.0)
            for i, d in enumerate(weekdays)}
    d1 = _synthetic(start, 40, lambda d: size[d])
    days = daily_table(d1, 0.01)
    check(f"day 21 is 2006-01-30 with ratio 2.0, its own range outside the normaliser ({days[20]['ratio']})",
          days[20]["day"] == date(2006, 1, 30) and abs(days[20]["ratio"] - 2.0) < 1e-12)
    check("the first 20 days are warm-up", all(x["ratio"] is None for x in days[:20]) and days[20]["ratio"] is not None)

    # Event table: an unscheduled FOMC action is never a cell event but always excluded from
    # controls; an unscheduled CPI or NFP row is an error.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "ev.csv")
        with open(p, "w") as fh:
            fh.write("date,event,time_et,scheduled,source_id\n2008-01-22,FOMC,08:20,false,x\n"
                     "2008-01-30,FOMC,14:15,true,x\n2008-01-16,CPI,08:30,true,x\n2008-02-01,NFP,08:30,true,x\n")
        sc, un, alld = load_events(p)
        check(f"unscheduled FOMC kept out of the cell, in the exclusion set ({sc['FOMC']}, {un})",
              sc["FOMC"] == [date(2008, 1, 30)] and un == [date(2008, 1, 22)] and date(2008, 1, 22) in alld)
        with open(p, "a") as fh:
            fh.write("2008-02-05,CPI,08:30,false,x\n")
        try:
            load_events(p)
            raised = False
        except ValueError:
            raised = True
        check("an unscheduled CPI row is refused", raised)
    check("session mapping: Sunday 21:15 ET -> Monday; Friday 14:15 -> Friday; Friday 18:00 -> Monday",
          session_of(date(2010, 5, 9), "21:15") == date(2010, 5, 10)
          and session_of(date(2008, 1, 25), "14:15") == date(2008, 1, 25)
          and session_of(date(2008, 1, 25), "18:00") == date(2008, 1, 28)
          and session_of(date(2008, 1, 25), "") == date(2008, 1, 25))

    # Controls: same weekday, within 28 days, never another event (any type, scheduled or not)
    d1 = _synthetic(start, 140, lambda d: 100.0)
    days = daily_table(d1, 0.01)
    ev = date(2006, 3, 10)                                   # a Friday
    other_event, unsched = date(2006, 3, 17), date(2006, 2, 24)
    cs = controls_for(ev, days, {ev, other_event, unsched})
    got = sorted(c["day"] for c in cs)
    want = [date(2006, 2, 10), date(2006, 2, 17), date(2006, 3, 3), date(2006, 3, 24),
            date(2006, 3, 31), date(2006, 4, 7)]
    check(f"controls are the event-free Fridays within 28 days ({got})", got == want)

    # Paired effect, hand-computed: every Friday-event day is 150 pips amid 100s -> effect +0.5
    fridays = [date(2006, 2, 10) + timedelta(weeks=4 * k) for k in range(5)]
    d1 = _synthetic(start, 160, lambda d: 150.0 if d in fridays else 100.0)
    days = daily_table(d1, 0.01)
    eff, drops = paired_effects(days, fridays, set(fridays))
    check(f"paired effects all +0.5 ({[round(e['effect'], 6) for e in eff]})",
          len(eff) == 5 and all(abs(e["effect"] - 0.5) < 1e-12 for e in eff))
    eff_w, drops_w = paired_effects(days, [date(2006, 1, 6), date(2005, 6, 1)], set(fridays))
    check(f"warm-up and missing sessions are dropped and counted ({drops_w})",
          not eff_w and drops_w["warm_up"] == 1 and drops_w["no_session"] == 1)

    # Round trip: close path prev 150.00 -> 150.50 (d) -> 150.30 -> 149.90 => given back on day d+2
    rows = [{"day": start + timedelta(days=k), "high": 1, "low": 0, "close": c, "range": 100.0}
            for k, c in enumerate([150.0] * 20 + [150.0, 150.5, 150.3, 149.9, 150.2, 150.1, 150.0])]
    d1 = {datetime(2006, 1, 1, tzinfo=timezone.utc) + timedelta(days=k): (r["close"], r["close"] + 0.5,
          r["close"] - 0.5, r["close"]) for k, r in enumerate(rows)}
    days = daily_table(d1, 0.01)
    check(f"round trip: a +50 pip day fully given back by d+2 is a round trip ({days[21]['round_trip']})",
          days[21]["round_trip"] is True)
    check(f"round trip: the next day's -20 pip move, never back above 150.50 in 3 closes, is not ({days[22]['round_trip']})",
          days[22]["round_trip"] is False)

    # Known effect and zero effect, at the scale of the spec's power statement
    r = random.Random(7)
    real = [{"effect": r.gauss(0.40, 0.55)} for _ in range(108)]
    check("a +0.40 effect at N=108 is MATERIAL", verdict(real, "st-real")[0] == "MATERIAL")
    material = 0
    for k in range(300):
        null = [{"effect": r.gauss(0.0, 0.55)} for _ in range(108)]
        material += verdict(null, f"st-null-{k}", n=2000)[0] == "MATERIAL"
    check(f"a zero effect reads MATERIAL in at most ~1% of runs ({material}/300)", material <= 3)
    # The family correction is applied: an exact sample with mean +0.20, SD 0.55, N=108 clears
    # +0.10 at an uncorrected one-sided 5% but not at the Bonferroni level.
    z = [r.gauss(0, 1) for _ in range(108)]
    zm, zs = statistics.fmean(z), statistics.stdev(z)
    exact = [{"effect": 0.20 + 0.55 * (v - zm) / zs} for v in z]
    lo_uncorrected = boot_bounds([e["effect"] for e in exact], "st-fam", alpha=0.05)[0]
    v_fam, s_fam = verdict(exact, "st-fam")
    check(f"Bonferroni applied: uncorrected bound {lo_uncorrected:+.3f} clears +0.10, "
          f"corrected {s_fam['lower']:+.3f} does not ({v_fam})",
          lo_uncorrected >= THRESHOLD and s_fam["lower"] < THRESHOLD and v_fam == "INCONCLUSIVE")
    flat = [{"effect": r.gauss(-0.20, 0.55)} for _ in range(108)]
    check("a -0.20 effect at N=108 is NOT MATERIAL", verdict(flat, "st-flat")[0] == "NOT MATERIAL")

    # Embargo
    late = {datetime(2013, 12, 30, 22, 0, tzinfo=timezone.utc): (1, 1, 1, 1)}
    try:
        daily_table(late, 0.01)
        refused = False
    except RuntimeError:
        refused = True
    check("a session after 2013-12-30 is refused", refused)

    # Event file shape (when present)
    if os.path.exists(EVENTS_FILE):
        sched, unsched, _ = load_events()
        check(f"event table loads: {', '.join(f'{e} {len(sched[e])}' for e in EVENTS)}, "
              f"unscheduled FOMC {len(unsched)}", all(sched[e] for e in EVENTS))
        check("every event date is a weekday inside 2005-2013",
              all(d.weekday() < 5 and date(2005, 1, 1) <= d <= LAST_STUDY_DAY
                  for e in EVENTS for d in sched[e]))
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
        return {datetime.fromisoformat(r["time_utc"]): tuple(float(r[k]) for k in "ohlc")
                for r in csv.DictReader(fh)}


def converted_days(out_dir, pair):
    d1 = load(os.path.join(out_dir, f"{pair}_D.csv"))
    h4 = load(os.path.join(out_dir, f"{pair}_H4.csv"))
    d1c, _, log = C.convert(d1, h4)
    return daily_table(d1c, PAIRS[pair]), log


def counts(env_file, out_dir):
    cl = G.P.Client(G.P.load_env(env_file))
    sched, unsched, all_dates = load_events()
    hashes = {"events": {os.path.basename(EVENTS_FILE): sha(EVENTS_FILE)}}
    for pair in PAIRS:
        d1, h4 = G.fetch(cl, pair, "D"), G.fetch(cl, pair, "H4")
        for gran, rows in (("D", d1), ("H4", h4)):
            p = os.path.join(out_dir, f"{pair}_{gran}.csv")
            save(p, rows)
            hashes[os.path.basename(p)] = sha(p)
        days, log = converted_days(out_dir, pair)
        print(f"{pair}: trading days {len(days)} ({days[0]['day']} to {days[-1]['day']}); "
              f"weekend rule: {log['sunday_folded_d1']} Sunday folded, {log['saturday_dropped_d1']} Saturday dropped")
        for ev in EVENTS:
            eff, drops = paired_effects(days, sched[ev], all_dates)
            per_year = defaultdict(int)
            for e in eff:
                per_year[e["day"].year] += 1
            mean_c = statistics.fmean(e["n_controls"] for e in eff) if eff else 0
            print(f"  {ev}: events in table {len(sched[ev])}; MATCHED {len(eff)}; dropped {drops}; "
                  f"mean controls per event {mean_c:.2f}; per year {dict(sorted(per_year.items()))}")
        print(f"  unscheduled FOMC actions in table: {len(unsched)}")
    with open(os.path.join(out_dir, "data_hashes.json"), "w") as fh:
        json.dump(hashes, fh, indent=1)
    print("data hashes:", json.dumps(hashes))
    print("requests:", cl.requests)


def _rt_share(flags):
    flags = [f for f in flags if f is not None]
    return (sum(flags) / len(flags), len(flags)) if flags else (float("nan"), 0)


def full(out_dir, report):
    with open(os.path.join(out_dir, "data_hashes.json")) as fh:
        recorded = json.load(fh)
    if recorded["events"].get(os.path.basename(EVENTS_FILE)) != sha(EVENTS_FILE):
        raise RuntimeError("event table differs from the counts stage")
    for name, h in recorded.items():
        if name != "events" and sha(os.path.join(out_dir, name)) != h:
            raise RuntimeError(f"{name} differs from the counts stage")
    sched, unsched, all_dates = load_events()
    lines = ["# US release reactions — pre-registered test result (2005–2013 STUDY data)", "",
             f"Spec: docs/specs/us_event_reaction_spec.md. Bonferroni α per cell {ALPHA:.4f} (one-sided), "
             f"threshold +{THRESHOLD:.2f}, {RESAMPLES} resamples.", ""]
    for pair in PAIRS:
        days, _ = converted_days(out_dir, pair)
        lines += [f"## {pair}", ""]
        for ev in EVENTS:
            eff, drops = paired_effects(days, sched[ev], all_dates)
            v, s = verdict(eff, f"uer:{pair}:{ev}")
            mv = [e["move_effect"] for e in eff]
            ev_rt = _rt_share(e["round_trip"] for e in eff)
            c_rt = _rt_share(f for e in eff for f in e["control_round_trips"])
            lines += [f"### {ev}: **{v}**", "",
                      f"- **Primary (range ratio, paired):** N {s['n']}; mean effect {s['mean']:+.3f}; "
                      f"one-sided bounds [{s['lower']:+.3f}, {s['upper']:+.3f}]; median {s['median']:+.3f}; "
                      f"SD {s['sd']:.3f}; dropped {drops}",
                      f"- Event-day mean ratio {statistics.fmean(e['ratio'] for e in eff):.3f} vs "
                      f"control mean {statistics.fmean(e['control_mean'] for e in eff):.3f}",
                      "",
                      "**Secondary (never changes the verdict):**", "",
                      f"- Close-to-close move, paired: mean effect {statistics.fmean(mv):+.3f}, "
                      f"median {statistics.median(mv):+.3f}",
                      f"- Round trip within {ROUND_TRIP_DAYS} days: event days {100 * ev_rt[0]:.0f}% "
                      f"(N {ev_rt[1]}) vs control days {100 * c_rt[0]:.0f}% (N {c_rt[1]})"]
            for name, lo, hi in SUBPERIODS:
                sub = [e["effect"] for e in eff if lo <= e["day"] <= hi]
                if sub:
                    lines.append(f"- {name}: N {len(sub)}, mean effect {statistics.fmean(sub):+.3f}")
            lines.append("")
        by_day = {x["day"]: x for x in days}
        un = [f"{d} ratio {by_day[d]['ratio']:.2f}" for d in unsched
              if d in by_day and by_day[d]["ratio"] is not None]
        lines += [f"- Unscheduled FOMC actions (descriptive): {'; '.join(un) if un else 'none matched'}", ""]
    text = "\n".join(lines)
    with open(report, "w") as fh:
        fh.write(text + "\n")
    print(text)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "selftest":
        sys.exit(0 if selftest() else 1)
    elif mode == "counts":
        counts(sys.argv[2], sys.argv[3])
    elif mode == "full":
        full(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
