"""gold_breakout_study.py — do gold's breaks of a daily swing hold?
(docs/specs/gold_breakout_study_spec.md, gold plan C2). Descriptive; prints only.

usage: python3 -I gold_breakout_study.py <archive_root>

<archive_root> is ~/intel_study_archives. Reads the gold and GBP/AUD daily
files named in the spec (hash-pinned), per era (STUDY, USED), and reports how
often a break of the latest confirmed daily swing (markup rule, k = 3) is back
inside within a few days: definition W (a wick beyond, R24's) and definition
C (a close beyond, the markup's "last break"). No entries, no R, no costs.
"""
import csv
import hashlib
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from markup_swings import swings  # noqa: E402  (the markup's own swing rule)

K = 3
ATR_N = 14
MIN_N = 20
ERAS = ("STUDY", "USED")
EXAM = ("2014-01-01", "2021-04-25")          # never read (data_map_spec)
GOLD_START = "2006-03-20T22:00"              # the 2006-03-21 session (leg study start)
FILES = {
    "XAU_USD": ("research_archive_legs/XAU_USD_D.csv",
                "6202a13d86459d2d3453c31ea9ddf40a3aca44243a6d4ff75bf3d0c165d0e3ca", GOLD_START),
    "GBP_AUD": ("research_archive/GBP_AUD_D.csv",
                "24e4bbe9065a1c463464a174162fab38be6b5f583aef71e7e2306554680bf7f6", None),
}
BUCKETS = ((0.0, 0.25, "< 0.25"), (0.25, 0.5, "0.25-0.5"), (0.5, 1.0, "0.5-1.0"),
           (1.0, math.inf, ">= 1.0"))


# ── data ─────────────────────────────────────────────────────────────────────

def load(path, sha, start=None):
    """{era: [(time, o, h, l, c, True), ...]} for STUDY and USED. Refuses a
    file whose bytes are not the pinned ones, and any row in the exam span."""
    raw = open(path, "rb").read()
    got = hashlib.sha256(raw).hexdigest()
    if got != sha:
        raise SystemExit(f"{path}: sha256 {got} is not the pinned {sha}")
    out = {e: [] for e in ERAS}
    for r in csv.DictReader(raw.decode().splitlines()):
        t = r["time_utc"]
        if EXAM[0] <= t[:10] <= EXAM[1]:
            raise SystemExit(f"{path}: row {t} lies in the sealed span {EXAM}; refusing")
        if r["span"] not in out or (start and t < start):
            continue
        out[r["span"]].append((t, float(r["o"]), float(r["h"]), float(r["l"]), float(r["c"]), True))
    return out


def atr_series(bars, n=ATR_N):
    """a[i] = Wilder ATR including bar i; None before the first value. The
    last value equals markup_swings.atr(bars)."""
    a = [None] * len(bars)
    trs = [None] + [max(bars[i][2] - bars[i][3], abs(bars[i][2] - bars[i - 1][4]),
                        abs(bars[i][3] - bars[i - 1][4])) for i in range(1, len(bars))]
    if len(bars) <= n:
        return a
    cur = sum(trs[1:n + 1]) / n
    a[n] = cur
    for i in range(n + 1, len(bars)):
        cur = (cur * (n - 1) + trs[i]) / n
        a[i] = cur
    return a


# ── events ───────────────────────────────────────────────────────────────────

def events(bars):
    """Every W and C event in one era's bars (spec §3)."""
    atr = atr_series(bars)
    at = {b[0]: i for i, b in enumerate(bars)}
    conf = sorted((at[t] + K, kind, price, at[t]) for t, kind, price in swings(bars, K))
    latest = {"H": None, "L": None}
    used = {"W": set(), "C": set()}
    out, p = [], 0
    for d in range(1, len(bars)):
        while p < len(conf) and conf[p][0] <= d - 1:      # confirmed by the close of d - 1
            _, kind, price, si = conf[p]
            latest[kind] = (price, si)
            p += 1
        a = atr[d - 1]
        _, _, h, l, c, _ = bars[d]
        for kind, side in (("H", "up"), ("L", "down")):
            if latest[kind] is None:
                continue
            level, si = latest[kind]
            up = side == "up"

            def inside(x):
                return bars[x][4] < level if up else bars[x][4] > level

            if (kind, si) not in used["W"] and (h > level if up else l < level):
                used["W"].add((kind, si))
                ev = {"def": "W", "side": side, "day": bars[d][0], "level": level}
                if a is None:
                    ev["status"] = "warm-up"
                elif d + 2 >= len(bars):
                    ev["status"] = "ungraded"
                else:
                    ev["status"] = "failed" if any(inside(x) for x in (d, d + 1, d + 2)) else "held"
                    if d + 4 < len(bars):
                        w = bars[d:d + 5]
                        ev["overshoot_atr"] = ((max(b[2] for b in w) - level) if up
                                               else (level - min(b[3] for b in w))) / a
                out.append(ev)
            if (kind, si) not in used["C"] and (c > level if up else c < level):
                used["C"].add((kind, si))
                ev = {"def": "C", "side": side, "day": bars[d][0], "level": level}
                if a is None:
                    ev["status"] = "warm-up"
                elif d + 3 >= len(bars):
                    ev["status"] = "ungraded"
                else:
                    ev["status"] = "failed" if any(inside(x) for x in (d + 1, d + 2, d + 3)) else "held"
                    ev["distance_atr"] = abs(c - level) / a
                out.append(ev)
    return out


# ── statistics ───────────────────────────────────────────────────────────────

def wilson(x, n, z=1.96):
    if n == 0:
        return (None, None)
    p = x / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, mid - half), min(1.0, mid + half))


def newcombe(x1, n1, x2, n2):
    """Difference p1 - p2 with Newcombe's hybrid score interval (method 10)."""
    p1, p2 = x1 / n1, x2 / n2
    l1, u1 = wilson(x1, n1)
    l2, u2 = wilson(x2, n2)
    d = p1 - p2
    return (d, d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2),
            d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2))


def pctl(vals, q):
    v = sorted(vals)
    if not v:
        return None
    k = (len(v) - 1) * q / 100.0
    f = int(k)
    return v[f] + (v[min(f + 1, len(v) - 1)] - v[f]) * (k - f)


def reading(x, n):
    """Spec §5 rule 2."""
    if n < MIN_N:
        return "INSUFFICIENT"
    lo, hi = wilson(x, n)
    return "most breaks fail" if lo > 0.5 else "most breaks hold" if hi < 0.5 else "about even"


def tally(evs):
    g = [e for e in evs if e["status"] in ("failed", "held")]
    f = sum(1 for e in g if e["status"] == "failed")
    return {"n": len(g), "failed": f, "held": len(g) - f,
            "ungraded": sum(1 for e in evs if e["status"] == "ungraded"),
            "warmup": sum(1 for e in evs if e["status"] == "warm-up")}


def pick(evs, d, side=None):
    return [e for e in evs if e["def"] == d and (side is None or e["side"] == side)]


# ── report ───────────────────────────────────────────────────────────────────

def fmt_share(t):
    if t["n"] == 0:
        return "no graded events"
    lo, hi = wilson(t["failed"], t["n"])
    return (f"N {t['n']}: failed {t['failed']}, held {t['held']} -> failed {100 * t['failed'] / t['n']:.1f}% "
            f"[{100 * lo:.1f}, {100 * hi:.1f}]  {reading(t['failed'], t['n'])}"
            f"  (ungraded {t['ungraded']}, warm-up {t['warmup']})")


def fmt_diff(a, b):
    if a["n"] < MIN_N or b["n"] < MIN_N:
        return "INSUFFICIENT (a cell has fewer than 20 graded events)"
    d, lo, hi = newcombe(a["failed"], a["n"], b["failed"], b["n"])
    verdict = "differs" if lo > 0 or hi < 0 else "no clear difference"
    return f"{100 * d:+.1f} points [{100 * lo:+.1f}, {100 * hi:+.1f}]  {verdict}"


def report(data):
    """data: {instrument: {era: [bars]}} -> list of output lines."""
    L = []
    emit = L.append
    ev = {(ins, era): events(bars) for ins, eras in data.items() for era, bars in eras.items()}
    emit("# Gold breakout study (C2): output")
    emit("")
    emit("## Data")
    for (ins, era), bars in ((k, data[k[0]][k[1]]) for k in ev):
        emit(f"- {ins} {era}: {len(bars)} daily bars, {bars[0][0][:10]} -> {bars[-1][0][:10]}")
    for d, name in (("W", "Definition W (a wick beyond; failed = a close back inside on days d..d+2)"),
                    ("C", "Definition C (a close beyond; failed = a close back inside on days d+1..d+3)")):
        emit("")
        emit(f"## {name}")
        for (ins, era), evs in ev.items():
            emit(f"### {ins} {era}")
            for side in ("up", "down", None):
                emit(f"- {side or 'both'}: {fmt_share(tally(pick(evs, d, side)))}")
            if d == "W":
                for st in ("failed", "held"):
                    o = [e["overshoot_atr"] for e in pick(evs, "W") if e["status"] == st and "overshoot_atr" in e]
                    if o:
                        emit(f"- overshoot (ATR), {st}: N {len(o)}, p50 {pctl(o, 50):.2f} / p75 {pctl(o, 75):.2f}"
                             f" / p90 {pctl(o, 90):.2f}")
            else:
                g = [e for e in pick(evs, "C") if e["status"] in ("failed", "held")]
                for lo, hi, lab in BUCKETS:
                    b = [e for e in g if lo <= e["distance_atr"] < hi]
                    held = sum(1 for e in b if e["status"] == "held")
                    flag = "" if len(b) >= MIN_N else "  INSUFFICIENT"
                    emit(f"- close {lab} ATR beyond: N {len(b)}, held {held}"
                         + (f" ({100 * held / len(b):.1f}%)" if b else "") + flag)
        emit("")
        emit(f"## Comparisons, definition {d} (failed share; 95% Newcombe interval)")
        for era in ERAS:
            if ("XAU_USD", era) in ev and ("GBP_AUD", era) in ev:
                for side in ("up", "down", None):
                    emit(f"- {era} gold minus GBP/AUD, {side or 'both'}: "
                         f"{fmt_diff(tally(pick(ev[('XAU_USD', era)], d, side)), tally(pick(ev[('GBP_AUD', era)], d, side)))}")
            if ("XAU_USD", era) in ev:
                g = ev[("XAU_USD", era)]
                emit(f"- {era} gold up minus gold down: {fmt_diff(tally(pick(g, d, 'up')), tally(pick(g, d, 'down')))}")
        for ins in data:
            r = [reading(tally(pick(ev[(ins, era)], d))["failed"], tally(pick(ev[(ins, era)], d))["n"])
                 for era in ERAS if (ins, era) in ev]
            stable = ("stable across eras" if len(set(r)) == 1 and "INSUFFICIENT" not in r
                      else "not stable across eras" if "INSUFFICIENT" not in r else "INSUFFICIENT")
            emit(f"- {ins} era readings (both sides): {' / '.join(r)} -> {stable}")
    emit("")
    emit("## Failed share by calendar year (both sides)")
    for (ins, era), evs in ev.items():
        for d in ("W", "C"):
            years = {}
            for e in pick(evs, d):
                if e["status"] in ("failed", "held"):
                    y = years.setdefault(e["day"][:4], [0, 0])
                    y[0] += e["status"] == "failed"
                    y[1] += 1
            emit(f"- {ins} {era} {d}: " + "; ".join(
                f"{y} {100 * f / n:.0f}% (N {n}{'' if n >= MIN_N else ', INSUFFICIENT'})"
                for y, (f, n) in sorted(years.items())))
    emit("")
    emit("Intervals assume independent events; breaks a few days apart are not fully")
    emit("independent, so the intervals are approximate and somewhat too narrow (spec §5.5).")
    emit("Descriptive only: no entries, no R, no costs. Not evidence of an edge (spec §5.6).")
    return L


def main(root):
    data = {}
    for ins, (rel, sha, start) in FILES.items():
        data[ins] = load(os.path.join(root, rel), sha, start)
    print("\n".join(report(data)))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
