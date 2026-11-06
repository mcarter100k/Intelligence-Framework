"""Session movement study, Phase 2: the five frozen questions.

Implements docs/specs/session_movement_study_spec.md (frozen at commit 85e5c19,
before this file existed) and nothing else. Descriptive only: no direction,
no returns, no strategy.

usage: python3 -I session_movement_study.py <h1_dir> <held_dir>

<h1_dir>   ~/intel_study_archives/session_movement_data   (Phase 1 H1 + hashes)
<held_dir> ~/intel_study_archives/us_event_reaction_data  (held STUDY D1/H4 + hashes)

No network. Reads only; stdout is the report body.
"""
import os
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import history_study_convert as C  # noqa: E402  approved weekend rule
import session_movement_data as D  # noqa: E402  Phase 1 helpers (study day, window, load)

UTC = timezone.utc
PAIRS = D.PAIRS
PIP = D.PIP
ATR_PERIOD = 14
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri")
# spec §3: fixed UTC blocks, (name, first UTC hour, end UTC hour exclusive)
BLOCKS = (("SYDNEY", 21, 24), ("TOKYO", 0, 7), ("LONDON", 7, 12),
          ("LDN_NY", 12, 16), ("NY_PM", 16, 21))
BLOCK_NAMES = tuple(b[0] for b in BLOCKS)
BOUNDARIES = (21, 0, 7, 12, 16)                     # first hour of each block
DST_EXPOSED = {7, 12, 16, 21}                       # spec §5; 00:00 UTC is not
Q4_HOURS = (6, 12, 18)
STEP_HI, STEP_LO = 1.5, 1 / 1.5                     # spec §5
EVEN_RATIO = 1.5                                    # spec §6
INSUFFICIENT_N = 20

EXPECTED_HASHES = {
    "GBP_AUD_H1.csv": "9f9303621542ec5e66546132d24be79525054e8d69b483a461954ec2df82f4c3",
    "GBP_JPY_H1.csv": "e00361f23f416b3479d49f08901beb02a943ae3cb759b23e93a3c533c53399cf",
    "GBP_AUD_H4.csv": "a59db9940e8d7a1c4ff02441112390c5d7b7544e764d980943877dee51b0ff77",
    "GBP_AUD_D.csv": "661a9d49c09ed9fbaa7a26a1e3ae60a4fc07860d19ea3ec89342398a9db7d939",
    "GBP_JPY_H4.csv": "f06892d1ebf958cc1a52bebf399e6ce10bef8e73e5e2c5b6a7f5634644053764",
    "GBP_JPY_D.csv": "ca1602404c5c501dffc0ee8ec5eeb4bee4a2197fe2fc76d3bbf69be2c8fa000a",
}


# ── pure helpers (pinned by tests/test_session_movement_study.py) ────────────

def block_of(t):
    h = t.astimezone(UTC).hour
    for name, lo, hi in BLOCKS:
        if lo <= h < hi:
            return name
    raise ValueError(h)


def hour_index(t):
    return (t.astimezone(UTC).hour - D.DAY_START_UTC) % 24


def pacific(h_utc):
    return f"{(h_utc - 8) % 24:02d}:00 PST / {(h_utc - 7) % 24:02d}:00 PDT"


def fold_bars(h1_raw, log):
    """Open times of the H1 bars that absorbed Sunday-session candles."""
    by = C._by_session(h1_raw)
    out = set()
    for sunday, target in log["folds"]:
        sd, td = datetime.fromisoformat(sunday).date(), datetime.fromisoformat(target).date()
        if by.get(sd) and by.get(td):
            out.add(by[td][0])
    return out


def group_days(h1c):
    """study day -> sorted bar open times, Mon-Fri STUDY days only."""
    days = defaultdict(list)
    for t in sorted(h1c):
        d = D.study_day(t)
        if D.STUDY_FIRST_DAY <= d <= D.STUDY_LAST_DAY and d.weekday() < 5:
            days[d].append(t)
    return days


def is_complete(day, times):
    return set(D.expected_hours(day)) <= set(times)


def day_stats(times, bars, pip):
    """Daily range, per-block range, and the bar where the high and low formed
    (earliest on ties) for one complete day."""
    hi = max(bars[t][1] for t in times)
    lo = min(bars[t][2] for t in times)
    hbar = next(t for t in times if bars[t][1] == hi)
    lbar = next(t for t in times if bars[t][2] == lo)
    blk = {}
    for name in BLOCK_NAMES:
        ts = [t for t in times if block_of(t) == name]
        if ts:
            blk[name] = (max(bars[t][1] for t in ts) - min(bars[t][2] for t in ts)) / pip
    return {"R": (hi - lo) / pip, "blocks": blk, "hbar": hbar, "lbar": lbar}


def dist(xs):
    xs = sorted(xs)
    q = statistics.quantiles(xs, n=20, method="inclusive")
    return {"n": len(xs), "mean": statistics.fmean(xs), "p10": q[1], "p25": q[4],
            "p50": q[9], "p75": q[14], "p90": q[17]}


def atr_series(highs, lows, closes, period=ATR_PERIOD):
    """Copy of regime_detection.compute_atr_series (pinned equal by test)."""
    n = len(closes)
    tr_list = [max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
               for i in range(1, n)]
    atr = sum(tr_list[:period]) / period
    result = [atr]
    for tr in tr_list[period:]:
        atr = (atr * (period - 1) + tr) / period
        result.append(atr)
    return result


def atr_by_bar(bars, period=ATR_PERIOD):
    """{bar open: ATR} with value j belonging to bar index period + j (spec Q5)."""
    ts = sorted(bars)
    vals = atr_series([bars[t][1] for t in ts], [bars[t][2] for t in ts],
                      [bars[t][3] for t in ts], period)
    return {ts[period + j]: v for j, v in enumerate(vals)}


def q4_shares(stats, which):
    n = len(stats)
    return {H: 100 * sum(1 for s in stats if hour_index(s[which]) < H) / n for H in Q4_HOURS}


def block_pct(stats, which):
    n = len(stats)
    return {b: 100 * sum(1 for s in stats if block_of(s[which]) == b) / n for b in BLOCK_NAMES}


def same_block_pct(stats):
    return 100 * sum(1 for s in stats if block_of(s["hbar"]) == block_of(s["lbar"])) / len(stats)


def steps(hour_means):
    """spec §5: step at each block boundary b = mean(hour b) / mean(hour b-1)."""
    return {b: hour_means[b] / hour_means[(b - 1) % 24] for b in BOUNDARIES}


def even_ratio(hour_means):
    return max(hour_means.values()) / min(hour_means.values())


# ── report ───────────────────────────────────────────────────────────────────

def flag(n):
    return " INSUFFICIENT" if n < INSUFFICIENT_N else ""


def emit_q1(rows_by_hour, label):
    print(f"\n**Q1 {label}** (pips per hour bar)\n")
    print("| UTC hour | Pacific | N | mean | median |")
    print("|---|---|---|---|---|")
    means = {}
    for h in list(range(21, 24)) + list(range(0, 21)):
        xs = rows_by_hour.get(h, [])
        if not xs:
            print(f"| {h:02d}:00 | {pacific(h)} | 0 | – | – |")
            continue
        means[h] = statistics.fmean(xs)
        print(f"| {h:02d}:00 | {pacific(h)} | {len(xs)}{flag(len(xs))} | "
              f"{means[h]:.1f} | {statistics.median(xs):.1f} |")
    return means


def emit_q2(stats, label):
    print(f"\n**Q2 {label}**: block range ÷ day range (shares do not sum to 1)\n")
    print("| block | N days | mean | p10 | p25 | median | p75 | p90 |")
    print("|---|---|---|---|---|---|---|---|")
    for b in BLOCK_NAMES:
        xs = [s["blocks"][b] / s["R"] for s in stats if b in s["blocks"]]
        d = dist(xs)
        print(f"| {b} | {d['n']}{flag(d['n'])} | {d['mean']:.3f} | {d['p10']:.3f} | {d['p25']:.3f} | "
              f"{d['p50']:.3f} | {d['p75']:.3f} | {d['p90']:.3f} |")


def emit_q3(stats, label):
    hp, lp = block_pct(stats, "hbar"), block_pct(stats, "lbar")
    print(f"\n**Q3 {label}** (N days {len(stats)}{flag(len(stats))})\n")
    print("| block | % of days the HIGH formed here | % of days the LOW formed here |")
    print("|---|---|---|")
    for b in BLOCK_NAMES:
        print(f"| {b} | {hp[b]:.1f}% | {lp[b]:.1f}% |")
    print(f"\nHigh and low in the same block: {same_block_pct(stats):.1f}% of days")


def emit_q4(stats, label):
    hs, ls = q4_shares(stats, "hbar"), q4_shares(stats, "lbar")
    print(f"\n**Q4 {label}** (N days {len(stats)}{flag(len(stats))})\n")
    print("| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |")
    print("|---|---|---|---|---|")
    for H in Q4_HOURS:
        h = (D.DAY_START_UTC + H) % 24
        print(f"| hour {H} | {h:02d}:00 | {pacific(h)} | {hs[H]:.1f}% | {ls[H]:.1f}% |")


def run(h1_dir, held_dir):
    print(f"run start (UTC): {datetime.now(UTC).isoformat(timespec='seconds')}")
    for name, want in EXPECTED_HASHES.items():
        d = h1_dir if name.endswith("_H1.csv") else held_dir
        got = D.sha(os.path.join(d, name))
        if got != want:
            raise SystemExit(f"hash mismatch: {name}")
        print(f"hash {name}: OK")
    print(f"first computation start (UTC): {datetime.now(UTC).isoformat(timespec='seconds')}")

    summary = {}
    for pair in PAIRS:
        pip = PIP[pair]
        h1 = D.load(os.path.join(h1_dir, f"{pair}_H1.csv"))
        h4 = D.load(os.path.join(held_dir, f"{pair}_H4.csv"))
        d1 = D.load(os.path.join(held_dir, f"{pair}_D.csv"))
        _, h1c, log = C.convert(d1, h1)
        d1c, h4c, _ = C.convert(d1, h4)
        folds = fold_bars(h1, log)
        days = group_days(h1c)
        complete = sorted(d for d, ts in days.items() if is_complete(d, ts))

        print(f"\n\n## {pair}\n")
        print(f"Study days with bars {len(days)}; complete {len(complete)}; "
              f"fold bars excluded from Q1 {sum(1 for ts in days.values() for t in ts if t in folds)}")

        # Q1
        q1_all, q1_wd = defaultdict(list), defaultdict(lambda: defaultdict(list))
        for d, ts in days.items():
            for t in ts:
                if t in folds:
                    continue
                r = (h1c[t][1] - h1c[t][2]) / pip
                q1_all[t.hour].append(r)
                q1_wd[d.weekday()][t.hour].append(r)
        print("\n### Q1. Hourly range profile")
        means = emit_q1(q1_all, f"{pair}, all weekdays")
        for wd in range(5):
            emit_q1(q1_wd[wd], f"{pair}, {WEEKDAYS[wd]}")

        st_all = []
        st_wd = defaultdict(list)
        zero_r = 0
        for d in complete:
            s = day_stats(days[d], h1c, pip)
            if s["R"] == 0:
                zero_r += 1
                continue
            st_all.append(s)
            st_wd[d.weekday()].append(s)

        print("\n### Q2. Share of daily range by block")
        print(f"\nDays with zero range excluded: {zero_r}. Winter Mondays' SYDNEY block holds 2 bars, not 3.")
        emit_q2(st_all, f"{pair}, all weekdays")
        for wd in range(5):
            emit_q2(st_wd[wd], f"{pair}, {WEEKDAYS[wd]}")

        print("\n### Q3. Where the daily high and low form")
        emit_q3(st_all, f"{pair}, all weekdays")
        for wd in range(5):
            emit_q3(st_wd[wd], f"{pair}, {WEEKDAYS[wd]}")

        print("\n### Q4. How early the extremes are set")
        emit_q4(st_all, f"{pair}, all weekdays")
        for wd in range(5):
            emit_q4(st_wd[wd], f"{pair}, {WEEKDAYS[wd]}")

        print("\n### Q5. Mean ATR(14) by timeframe (pips; numbers only)\n")
        print("| timeframe | all weekdays (N) | " + " | ".join(WEEKDAYS) + " |")
        print("|---|---|" + "---|" * 5)
        for tf, bars in (("H1", h1c), ("H4", h4c), ("D1", d1c)):
            atr = atr_by_bar(bars)
            sel = defaultdict(list)
            for t, v in atr.items():
                sd = C.session_day(t)
                if D.STUDY_FIRST_DAY <= sd <= D.STUDY_LAST_DAY and sd.weekday() < 5:
                    sel[sd.weekday()].append(v / pip)
            allv = [v for wd in sel for v in sel[wd]]
            cells = " | ".join(f"{statistics.fmean(sel[wd]):.1f} ({len(sel[wd])}{flag(len(sel[wd]))})"
                               for wd in range(5))
            print(f"| {tf} | {statistics.fmean(allv):.1f} ({len(allv)}) | {cells} |")

        summary[pair] = means

    print("\n\n## Reading rules fixed in the spec (§5, §6)\n")
    print("| pair | boundary (UTC) | step = mean(hour b) ÷ mean(hour b−1) | sharp (≥1.5 or ≤0.667)? | DST-exposed? |")
    print("|---|---|---|---|---|")
    for pair in PAIRS:
        for b, s in steps(summary[pair]).items():
            sharp = s >= STEP_HI or s <= STEP_LO
            print(f"| {pair} | {b:02d}:00 | {s:.2f} | {'SHARP STEP' if sharp else 'no'} | "
                  f"{'yes' if b in DST_EXPOSED else 'no'} |")
    print()
    for pair in PAIRS:
        m = summary[pair]
        hmax, hmin = max(m, key=m.get), min(m, key=m.get)
        print(f"{pair}: largest hourly mean {m[hmax]:.1f} at {hmax:02d}:00 UTC; smallest {m[hmin]:.1f} "
              f"at {hmin:02d}:00 UTC; ratio {even_ratio(m):.2f}")
    even = all(even_ratio(summary[p]) < EVEN_RATIO for p in PAIRS)
    print(f"\nPhase 3 gate (§6): {'EVENLY SPREAD — Phase 3 question moot' if even else 'CONCENTRATED — Phase 3 question not moot (team decides)'}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    run(sys.argv[1], sys.argv[2])
