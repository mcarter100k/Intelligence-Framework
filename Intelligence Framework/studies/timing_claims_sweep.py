"""timing_claims_sweep.py — every time-of-day and session claim against a
chance baseline (docs/reports/timing_claims_sweep.md). Report-only; prints.

usage: python3 -I timing_claims_sweep.py <archive_root>      (~/intel_study_archives)

Observed figures are recomputed with the session study's own code
(session_movement_study: group_days, is_complete, day_stats, q4_shares,
block_pct, same_block_pct) on the same hash-pinned files:
- GBP/AUD and GBP/JPY, 2005-2013 STUDY (session_movement_data + us_event_reaction_data);
- XAU/USD, 2021-04-27 -> 2026-09-09 USED (leg_data/modern), configured exactly as
  gold_session_study.configure() does (gold's 17:00 New York break hour removed).

Chance baselines, computed for every claim:
- "uniform": a driftless random walk, equal variance in every trading hour;
- "vol-shaped": a driftless random walk whose variance in each UTC hour equals
  that hour's observed Parkinson variance (so busy hours stay busy).
Each simulated day reuses an observed day's exact hour list, 20 Gaussian steps
an hour, REPS simulated days per observed day, seed 7, and is scored by the
same day_stats code. Standard errors: binomial for shares of days; bootstrap
(500 resamples, seed 7) for medians; sd/sqrt(n) for hourly means.
"""
import importlib
import math
import os
import random
import statistics
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

REPS = 5
STEPS = 20
SEED = 7
BOOT = 500


def _modules(gold):
    import session_movement_data as D
    import session_movement_study as M
    D = importlib.reload(D)
    M = importlib.reload(M)
    if gold:
        import gold_session_study as G
        G = importlib.reload(G)
        M = G.configure()
        import session_movement_data as D2
        D = D2
    return M, D


def prepare(M, D, pair, h1_dir, held_dir):
    """Exactly session_movement_study.run's preparation for one pair."""
    import history_study_convert as C
    for name, want in M.EXPECTED_HASHES.items():
        if not name.startswith(pair):
            continue
        d = h1_dir if name.endswith("_H1.csv") else held_dir
        got = D.sha(os.path.join(d, name))
        if got != want:
            raise SystemExit(f"hash mismatch: {name}")
    h1 = D.load(os.path.join(h1_dir, f"{pair}_H1.csv"))
    d1 = D.load(os.path.join(held_dir, f"{pair}_D.csv"))
    _, h1c, log = C.convert(d1, h1)
    folds = M.fold_bars(h1, log)
    days = M.group_days(h1c)
    complete = sorted(d for d, ts in days.items() if M.is_complete(d, ts))
    return h1c, folds, days, complete


def hour_profile(h1c, days, folds, pip):
    """Per UTC hour: list of ranges (in pips/dollars) and Parkinson variance of log(H/L)."""
    rng, park = defaultdict(list), defaultdict(list)
    for ts in days.values():
        for t in ts:
            if t in folds:
                continue
            o, h, l, c = h1c[t]
            rng[t.hour].append((h - l) / pip)
            if h > 0 and l > 0:
                park[t.hour].append(math.log(h / l) ** 2 / (4 * math.log(2)))
    return rng, {k: statistics.fmean(v) for k, v in park.items()}


def simulate(days, complete, var, rnd):
    """Simulated bars {(day, rep): {t: (o,h,l,c)}} reusing each day's hour list."""
    sims = []
    for d in complete:
        ts = days[d]
        for _ in range(REPS):
            x, bars = 0.0, {}
            for t in ts:
                sd = math.sqrt(var[t.hour] / STEPS)
                o = hi = lo = x
                for _ in range(STEPS):
                    x += rnd.gauss(0.0, sd)
                    hi, lo = max(hi, x), min(lo, x)
                bars[t] = (o, hi, lo, x)
            sims.append((ts, bars))
    return sims


def stats_of(M, pairs_of_days, pip):
    out = []
    for ts, bars in pairs_of_days:
        s = M.day_stats(ts, bars, pip)
        if s["R"] > 0:
            out.append(s)
    return out


def boot_median_se(xs, rnd):
    n = len(xs)
    meds = [statistics.median(rnd.choices(xs, k=n)) for _ in range(BOOT)]
    return statistics.stdev(meds)


def flag(obs, base, se):
    z = (obs - base) / se if se > 0 else float("inf")
    return z, ("WITHIN 2 SE OF CHANCE" if abs(z) < 2 else "beyond 2 SE")


def report_pair(label, M, D, pair, h1_dir, held_dir, gold):
    rnd = random.Random(SEED)
    pip = M.PIP[pair]
    h1c, folds, days, complete = prepare(M, D, pair, h1_dir, held_dir)
    rng, var = hour_profile(h1c, days, folds, pip)
    obs_pairs = [(d, M.day_stats(days[d], h1c, pip)) for d in complete]
    obs_pairs = [(d, s) for d, s in obs_pairs if s["R"] > 0]
    obs = [s for _, s in obs_pairs]
    n = len(obs)
    mean_var = statistics.fmean(var.values())
    uniform = {h: mean_var for h in var}
    base = {"uniform": stats_of(M, simulate(days, complete, uniform, rnd), 1.0),
            "vol-shaped": stats_of(M, simulate(days, complete, var, rnd), 1.0)}
    print(f"\n## {label}: {pair}\n")
    print(f"Complete days scored: {n} (simulated days per baseline: {len(base['uniform'])}, {len(base['vol-shaped'])})")

    print("\n### Hourly range profile (claims about busy and quiet hours)")
    means = {h: statistics.fmean(v) for h, v in rng.items()}
    ses = {h: statistics.stdev(v) / math.sqrt(len(v)) for h, v in rng.items()}
    allm = statistics.fmean([x for v in rng.values() for x in v])
    hb, hq = max(means, key=means.get), min(means, key=means.get)
    print(f"- all hours mean {allm:.2f}; busiest hour {hb:02d}:00 UTC mean {means[hb]:.2f} (se {ses[hb]:.2f}); "
          f"quietest {hq:02d}:00 UTC mean {means[hq]:.2f} (se {ses[hq]:.2f}); ratio {means[hb] / means[hq]:.2f}")
    print(f"- chance baseline (no time-of-day effect): every hour equals the all-hours mean, ratio 1.00")
    print(f"- busiest hour minus all-hours mean: {(means[hb] - allm) / ses[hb]:.1f} se")
    blk = [12, 13, 14]
    in_blk = [x for h in blk for x in rng[h]]
    out_blk = [x for h in rng if h not in blk for x in rng[h]]
    d = statistics.fmean(in_blk) - statistics.fmean(out_blk)
    se_d = math.sqrt(statistics.variance(in_blk) / len(in_blk) + statistics.variance(out_blk) / len(out_blk))
    print(f"- 12:00-15:00 UTC (04:00-07:00 PST) mean {statistics.fmean(in_blk):.2f} vs other hours "
          f"{statistics.fmean(out_blk):.2f}: difference {d:.2f} = {d / se_d:.1f} se (hours within a day are not independent; se is optimistic)")
    print("- hour means: " + ", ".join(f"{h:02d} {means[h]:.1f}" for h in sorted(means)))

    print("\n### When the day's high and low are already set (Q4)")
    for which, name in (("hbar", "high"), ("lbar", "low")):
        o = M.q4_shares(obs, which)
        bu, bv = M.q4_shares(base["uniform"], which), M.q4_shares(base["vol-shaped"], which)
        for H in M.Q4_HOURS:
            h_utc = (D.DAY_START_UTC + H) % 24
            p = o[H] / 100
            se = math.sqrt(p * (1 - p) / n)
            z, f = flag(p, bv[H] / 100, se)
            print(f"- {name} set by {h_utc:02d}:00 UTC ({M.pacific(h_utc)}): observed {o[H]:.1f}%; "
                  f"uniform {bu[H]:.1f}%; vol-shaped {bv[H]:.1f}%; se {100 * se:.1f} pts; "
                  f"observed minus vol-shaped {o[H] - bv[H]:+.1f} pts ({z:+.1f} se) -> {f}")
    if gold:
        trading_before = 17
        print(f"- analytic arcsine, uniform, {trading_before} of 23 trading hours elapsed: "
              f"{100 * (2 / math.pi) * math.asin(math.sqrt(trading_before / 23)):.2f}%")

    print("\n### Where the day's high and low form, by block (Q3)")
    for which, name in (("hbar", "high"), ("lbar", "low")):
        o = M.block_pct(obs, which)
        bu, bv = M.block_pct(base["uniform"], which), M.block_pct(base["vol-shaped"], which)
        for b in M.BLOCK_NAMES:
            p = o[b] / 100
            se = math.sqrt(p * (1 - p) / n)
            z, f = flag(p, bv[b] / 100, se)
            print(f"- {name} in {b}: observed {o[b]:.1f}%; uniform {bu[b]:.1f}%; vol-shaped {bv[b]:.1f}%; "
                  f"se {100 * se:.1f} pts; {z:+.1f} se -> {f}")
    o = M.same_block_pct(obs) / 100
    bv = M.same_block_pct(base["vol-shaped"]) / 100
    bu = M.same_block_pct(base["uniform"]) / 100
    se = math.sqrt(o * (1 - o) / n)
    z, f = flag(o, bv, se)
    print(f"- high and low in the same block: observed {100 * o:.1f}%; uniform {100 * bu:.1f}%; "
          f"vol-shaped {100 * bv:.1f}%; {z:+.1f} se -> {f}")

    print("\n### Block range as a share of the day's range, medians (Q2)")
    for b in M.BLOCK_NAMES:
        xo = [s["blocks"][b] / s["R"] for s in obs if b in s["blocks"]]
        xu = [s["blocks"][b] / s["R"] for s in base["uniform"] if b in s["blocks"]]
        xv = [s["blocks"][b] / s["R"] for s in base["vol-shaped"] if b in s["blocks"]]
        mo = statistics.median(xo)
        se = boot_median_se(xo, rnd)
        z, f = flag(mo, statistics.median(xv), se)
        print(f"- {b}: observed median {mo:.3f}; uniform {statistics.median(xu):.3f}; vol-shaped "
              f"{statistics.median(xv):.3f}; se {se:.3f}; {z:+.1f} se -> {f}")

    if not gold:
        print("\n### Monday's day-start block holds the high (Q3 by weekday)")
        for wd in range(5):
            o_wd = [s for d, s in obs_pairs if d.weekday() == wd]
            p = M.block_pct(o_wd, "hbar")["SYDNEY"] / 100
            se = math.sqrt(p * (1 - p) / len(o_wd))
            bv = M.block_pct(base["vol-shaped"], "hbar")["SYDNEY"] / 100
            z, f = flag(p, bv, se)
            print(f"- {M.WEEKDAYS[wd]}: high in SYDNEY {100 * p:.1f}% (N {len(o_wd)}); vol-shaped all-days "
                  f"{100 * bv:.1f}%; {z:+.1f} se -> {f}")


def main(root):
    gbp_h1 = os.path.join(root, "session_movement_data")
    gbp_held = os.path.join(root, "us_event_reaction_data")
    gold_dir = os.path.join(root, "leg_data", "modern")
    print(f"Baselines: REPS {REPS}, STEPS {STEPS}, seed {SEED}, bootstrap {BOOT}")
    for pair in ("GBP_AUD", "GBP_JPY"):
        M, D = _modules(gold=False)
        report_pair("STUDY 2005-2013", M, D, pair, gbp_h1, gbp_held, gold=False)
    M, D = _modules(gold=True)
    report_pair("USED 2021-04-27 -> 2026-09-09", M, D, "XAU_USD", gold_dir, gold_dir, gold=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
