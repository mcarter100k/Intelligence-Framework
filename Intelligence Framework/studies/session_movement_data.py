"""Session movement study, Phase 1: STUDY-partition H1 data and its validation.

usage:
  python3 -I session_movement_data.py fetch <out_dir>
  python3 -I session_movement_data.py validate <out_dir> <h4_dir> <gaps_csv_dir>

fetch     pulls OANDA H1 mid candles for GBP_AUD and GBP_JPY over the STUDY
          partition through the embargo-guarded fetch in
          history_study_gate_s3.py (the SEALED EXAM block is refused before
          sending and after receipt). Credentials come from the environment
          (OANDA_API_KEY, OANDA_ENVIRONMENT), as scripts/reality_run.py
          exports them. Writes <pair>_H1.csv and data_hashes.json to <out_dir>,
          which must be outside the repo.
validate  verifies the stored hashes, aggregates raw H1 into the framework's
          H4 slots (17, 21, 1, 5, 9, 13 New York) and compares every bucket
          against the held raw STUDY H4, lists every gap in the H1 series,
          and counts complete study days after the approved weekend rule.

Verification numbers only: counts, timestamps and differences in pips.
No range, average or other movement statistic is computed here.
"""
import csv
import hashlib
import json
import os
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import history_study_gate_s3 as G  # noqa: E402  guarded STUDY fetch
import history_study_convert as C  # noqa: E402  approved weekend rule

UTC = timezone.utc
NY = ZoneInfo("America/New_York")
PT = ZoneInfo("America/Los_Angeles")
PAIRS = ("GBP_AUD", "GBP_JPY")
PIP = {"GBP_AUD": 0.0001, "GBP_JPY": 0.01}
H4_FIRST_SLOT_NY = 17
DAY_START_UTC = 21                      # study day D = [D-1 21:00Z, D 21:00Z)
STUDY_FIRST_DAY = date(2005, 1, 3)      # first Monday of the STUDY span
STUDY_LAST_DAY = date(2013, 12, 30)     # data_map_spec §11.2 effective STUDY end


# ── pure helpers (pinned by tests/test_session_movement_data.py) ─────────────

def h4_bucket(t):
    """Open time (UTC) of the framework H4 slot containing H1 open time t.
    Slots open at 17, 21, 1, 5, 9, 13 New York wall-clock."""
    tn = t.astimezone(NY)
    back = ((tn.hour - H4_FIRST_SLOT_NY) % 24) % 4
    start = tn.replace(minute=0, second=0, microsecond=0) - timedelta(hours=back)
    return start.astimezone(UTC)


def aggregate(h1, bucket=h4_bucket):
    """{bucket_open: (o, h, l, c, n_h1)} from {h1_open: (o, h, l, c)}."""
    groups = defaultdict(list)
    for t in sorted(h1):
        groups[bucket(t)].append(t)
    return {b: (h1[ts[0]][0], max(h1[t][1] for t in ts), min(h1[t][2] for t in ts),
                h1[ts[-1]][3], len(ts)) for b, ts in groups.items()}


def compare(agg, h4, pip):
    """Per common bucket: |diff| in pips for o, h, l, c (rounded to 1e-6)."""
    out = {}
    for b in sorted(set(agg) & set(h4)):
        a, r = agg[b], h4[b]
        out[b] = tuple(round(abs(a[i] - r[i]) / pip, 6) for i in range(4))
    return out


def market_open(t):
    """True if the H1 slot opening at t is inside the weekly market window
    Sun 17:00 New York -> Fri 17:00 New York."""
    tn = t.astimezone(NY)
    wd, hr = tn.weekday(), tn.hour
    if wd == 5:
        return False
    if wd == 6:
        return hr >= 17
    if wd == 4:
        return hr < 17
    return True


def study_day(t):
    """Study day label: the UTC date of (t + 3 h), so the day runs 21:00Z->21:00Z."""
    return (t.astimezone(UTC) + timedelta(hours=24 - DAY_START_UTC)).date()


def expected_hours(day):
    """UTC open times of every H1 slot of study day `day` inside the market window."""
    start = datetime(day.year, day.month, day.day, tzinfo=UTC) - timedelta(hours=24 - DAY_START_UTC)
    return [start + timedelta(hours=k) for k in range(24)
            if market_open(start + timedelta(hours=k))]


def gaps(times, lo, hi):
    """Runs of missing in-window H1 slots between lo and hi (UTC, inclusive lo,
    exclusive hi): list of (first_missing_open, n_hours)."""
    have = set(times)
    out, run_start, run_len = [], None, 0
    t = lo
    while t < hi:
        if market_open(t) and t not in have:
            if run_start is None:
                run_start, run_len = t, 0
            run_len += 1
        elif market_open(t) and run_start is not None:
            out.append((run_start, run_len))
            run_start = None
        t += timedelta(hours=1)
    if run_start is not None:
        out.append((run_start, run_len))
    return out


# ── I/O ──────────────────────────────────────────────────────────────────────

def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load(path):
    rows = {}
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            rows[datetime.fromisoformat(r["time_utc"])] = (float(r["o"]), float(r["h"]),
                                                          float(r["l"]), float(r["c"]))
    return rows


def pt(t):
    return t.astimezone(PT).strftime("%Y-%m-%d %H:%M %Z")


def fetch(out_dir):
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if os.path.abspath(out_dir).startswith(repo + os.sep):
        raise SystemExit("refused: out_dir must be outside the repo")
    os.makedirs(out_dir, exist_ok=True)
    cl = G.P.Client(dict(os.environ))
    hashes = {}
    for pair in PAIRS:
        rows = G.fetch(cl, pair, "H1")
        p = os.path.join(out_dir, f"{pair}_H1.csv")
        G.save(p, rows)
        hashes[os.path.basename(p)] = sha(p)
        first, last = min(rows), max(rows)
        sealed = sum(1 for t in rows if G.BLOCK_START <= t < G.BLOCK_END)
        print(f"{pair}: H1 candles stored {len(rows)}; first open {first.isoformat()} "
              f"({pt(first)}); last open {last.isoformat()} ({pt(last)}); "
              f"candles inside embargo/sealed block: {sealed}")
    with open(os.path.join(out_dir, "data_hashes.json"), "w") as fh:
        json.dump(hashes, fh, indent=1)
    print("data hashes:", json.dumps(hashes))
    print("requests:", cl.requests)


def _pctiles(xs):
    xs = sorted(xs)
    q = statistics.quantiles(xs, n=100, method="inclusive") if len(xs) > 1 else xs * 99
    return {"p50": q[49], "p90": q[89], "p99": q[98], "max": xs[-1]}


def validate(out_dir, h4_dir, gaps_dir):
    with open(os.path.join(out_dir, "data_hashes.json")) as fh:
        h1_hashes = json.load(fh)
    with open(os.path.join(h4_dir, "data_hashes.json")) as fh:
        h4_hashes = json.load(fh)
    for name, want in h1_hashes.items():
        got = sha(os.path.join(out_dir, name))
        print(f"hash {name}: {'OK' if got == want else 'MISMATCH'}")
        if got != want:
            raise SystemExit(f"hash mismatch: {name}")
    for pair in PAIRS:
        for g in ("H4", "D"):
            name = f"{pair}_{g}.csv"
            got = sha(os.path.join(h4_dir, name))
            print(f"hash {name} (held): {'OK' if got == h4_hashes[name] else 'MISMATCH'}")
            if got != h4_hashes[name]:
                raise SystemExit(f"hash mismatch: {name}")

    verdict_ok = True
    for pair in PAIRS:
        pip = PIP[pair]
        h1 = load(os.path.join(out_dir, f"{pair}_H1.csv"))
        h4 = load(os.path.join(h4_dir, f"{pair}_H4.csv"))
        d1 = load(os.path.join(h4_dir, f"{pair}_D.csv"))
        print(f"\n## {pair}")
        off = sum(1 for t in h1 if t.minute or t.second)
        sealed = sum(1 for t in h1 if G.BLOCK_START <= t < G.BLOCK_END)
        print(f"H1 candles {len(h1)}; first open {pt(min(h1))}; last open {pt(max(h1))}; "
              f"off-the-hour opens {off}; inside embargo/sealed block {sealed}")
        print(f"held H4 candles {len(h4)}; first open {pt(min(h4))}; last open {pt(max(h4))}")

        # 1. aggregation H1 -> H4 on the framework's slots (raw vs raw)
        agg = aggregate(h1)
        cmp_ = compare(agg, h4, pip)
        only_agg = sorted(set(agg) - set(h4))
        only_h4 = sorted(set(h4) - set(agg))
        exact = [b for b, d in cmp_.items() if max(d) == 0]
        full4 = [b for b in cmp_ if agg[b][4] == 4]
        exact_full4 = [b for b in full4 if max(cmp_[b]) == 0]
        print(f"AGGREGATION  buckets compared {len(cmp_)}; exact match (all of o/h/l/c) "
              f"{len(exact)} ({100 * len(exact) / len(cmp_):.3f}%)")
        print(f"  of which built from all 4 H1 bars: {len(full4)} compared, {len(exact_full4)} exact; "
              f"built from 1-3 H1 bars: {len(cmp_) - len(full4)} compared, "
              f"{len(exact) - len(exact_full4)} exact")
        print(f"  H1-built buckets with no held H4 bar: {len(only_agg)}; "
              f"held H4 bars with no H1 inside: {len(only_h4)}")
        for b in only_agg[:20]:
            print(f"    no H4 for bucket {b.isoformat()} ({pt(b)}), H1 bars in it {agg[b][4]}")
        for b in only_h4[:20]:
            print(f"    no H1 inside H4 {b.isoformat()} ({pt(b)})")
        for i, f in enumerate("ohlc"):
            nz = [d[i] for d in cmp_.values() if d[i] > 0]
            line = f"  field {f}: nonzero diffs {len(nz)}"
            if nz:
                line += " | |diff| pips " + ", ".join(f"{k} {v:.3f}" for k, v in _pctiles(nz).items())
            print(line)
        mism = [b for b, d in cmp_.items() if max(d) > 0]
        hist = Counter()
        for b in mism:
            m = max(cmp_[b])
            hist["<=0.1" if m <= 0.1 else "<=0.5" if m <= 0.5 else "<=1" if m <= 1
                 else "<=5" if m <= 5 else ">5"] += 1
        print(f"  mismatching buckets by largest |diff| in pips: {dict(sorted(hist.items()))}")
        for b in sorted(mism, key=lambda b: -max(cmp_[b]))[:15]:
            d = cmp_[b]
            print(f"    {b.isoformat()} ({pt(b)}) H1 bars {agg[b][4]} "
                  f"|diff| o {d[0]:.3f} h {d[1]:.3f} l {d[2]:.3f} c {d[3]:.3f}")
        by_year = Counter(b.year for b in mism)
        print(f"  mismatching buckets per year: {dict(sorted(by_year.items()))}")
        if mism or only_agg or only_h4:
            verdict_ok = False

        # 2. gaps in the raw H1 series inside the weekly market window
        lo = min(h1).replace(minute=0)
        hi = max(h1) + timedelta(hours=1)
        gl = gaps(h1, lo, hi)
        dur = Counter(n for _, n in gl)
        print(f"GAPS  in-window missing-hour runs {len(gl)}; missing hours {sum(n for _, n in gl)}; "
              f"by run length (hours: runs) {dict(sorted(dur.items()))}")
        print(f"  runs per year: {dict(sorted(Counter(t.year for t, _ in gl).items()))}")
        for t, n in gl:
            if n >= 3:
                print(f"    {pt(t)} -> {pt(t + timedelta(hours=n))}  {n} h")
        gp = os.path.join(gaps_dir, f"session_movement_gaps_{pair}.csv")
        with open(gp, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["first_missing_open_utc", "first_missing_open_pacific", "hours_missing"])
            for t, n in gl:
                w.writerow([t.isoformat(), pt(t), n])
        print(f"  every gap listed in {os.path.basename(gp)}")

        # 3. complete study days after the approved weekend rule
        _, h1c, log = C.convert(d1, h1)
        print(f"WEEKEND RULE  Saturday-session H1 dropped {log['saturday_dropped_h4']}; "
              f"Sunday-session H1 folded {log['sunday_folded_h4']} into "
              f"{len(log['folds'])} target sessions")
        byday = defaultdict(list)
        for t in h1c:
            byday[study_day(t)].append(t)
        weekdays = [d for d in byday if STUDY_FIRST_DAY <= d <= STUDY_LAST_DAY and d.weekday() < 5]
        wkend_bars = sum(len(v) for d, v in byday.items() if d.weekday() >= 5
                         and STUDY_FIRST_DAY <= d <= STUDY_LAST_DAY)
        out_bars = sum(len(v) for d, v in byday.items()
                       if not (STUDY_FIRST_DAY <= d <= STUDY_LAST_DAY))
        complete = [d for d in weekdays if set(expected_hours(d)) <= set(byday[d])]
        short = len(weekdays) - len(complete)
        print(f"STUDY DAYS (21:00Z -> 21:00Z, Mon-Fri, {STUDY_FIRST_DAY} -> {STUDY_LAST_DAY}): "
              f"with any bar {len(weekdays)}; complete {len(complete)}; incomplete {short}")
        print(f"  complete per weekday: "
              f"{dict(sorted(Counter(d.strftime('%a') for d in complete).items()))}")
        print(f"  complete per year: {dict(sorted(Counter(d.year for d in complete).items()))}")
        print(f"  converted H1 bars falling in Sat/Sun study days (winter Fri 21:00Z hour): "
              f"{wkend_bars}; outside the STUDY day span: {out_bars}")
    print("\nPHASE 1 VERDICT:", "PASS (every bucket matches exactly)" if verdict_ok
          else "MISMATCH PRESENT (see above)")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "fetch":
        fetch(sys.argv[2])
    elif len(sys.argv) == 5 and sys.argv[1] == "validate":
        validate(*sys.argv[2:])
    else:
        raise SystemExit(__doc__)
