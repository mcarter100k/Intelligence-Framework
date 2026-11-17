"""gold_move_size_study.py — how far gold moves, in percent of price
(docs/specs/gold_move_size_study_spec.md, gold plan C1). Descriptive; prints only.

usage: python3 -I gold_move_size_study.py <legs_archive_dir>

<legs_archive_dir> is ~/intel_study_archives/research_archive_legs. Reads the
gold D, H4 and H1 files (hash-pinned), per era (STUDY, USED), and reports the
true range and the Wilder ATR(14) as a percent of price. No entries, no R, no
costs.
"""
import csv
import hashlib
import os
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gold_breakout_study import atr_series, pctl  # noqa: E402  (C2's tested helpers)

ERAS = ("STUDY", "USED")
FRAMES = ("D", "H4", "H1")
EXAM = ("2014-01-01", "2021-04-25")          # never read (data_map_spec)
GOLD_START = "2006-03-20T22:00"              # the 2006-03-21 session (gold plan T2)
MIN_YEAR_N = 20
FILES = {
    "D": ("XAU_USD_D.csv", "6202a13d86459d2d3453c31ea9ddf40a3aca44243a6d4ff75bf3d0c165d0e3ca"),
    "H4": ("XAU_USD_H4.csv", "e101117de1af589820a10eb4b5e65b30a4f294e9ee7683ac1baf8a8c02f0011c"),
    "H1": ("XAU_USD_H1.csv", "eabec6652e055540b256aa743971a1a5aa5cbb459e94b4887da6f28b8e02a4be"),
}


# ── data ─────────────────────────────────────────────────────────────────────

def load(path, sha, start=GOLD_START):
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
        if r["span"] not in out or t < start:
            continue
        out[r["span"]].append((t, float(r["o"]), float(r["h"]), float(r["l"]), float(r["c"]), True))
    return out


# ── measures ─────────────────────────────────────────────────────────────────

def measures(bars):
    """Per bar of one era: {'t', 'close', 'tr', 'tr_pct', 'atr_pct'}. The first
    bar has no true range (no previous close inside the era); ATR % is None
    during the warm-up."""
    atr = atr_series(bars)
    out = []
    for i, (t, _, h, l, c, _) in enumerate(bars):
        m = {"t": t, "close": c, "tr": None, "tr_pct": None,
             "atr_pct": None if atr[i] is None else 100 * atr[i] / c}
        if i > 0:
            pc = bars[i - 1][4]
            m["tr"] = max(h - l, abs(h - pc), abs(l - pc))
            m["tr_pct"] = 100 * m["tr"] / pc
        out.append(m)
    return out


def overlap_reading(a, b):
    """Spec §5 rule 2: a and b are (p25, p75) ranges."""
    return "overlapping" if a[0] <= b[1] and b[0] <= a[1] else "the eras differ"


def by_year(ms):
    years = defaultdict(list)
    for m in ms:
        if m["tr_pct"] is not None:
            years[m["t"][:4]].append(m)
    return dict(sorted(years.items()))


# ── report ───────────────────────────────────────────────────────────────────

def _q(vals, qs):
    return " / ".join(f"p{q} {pctl(vals, q):.3f}" for q in qs)


def report(data):
    """data: {frame: {era: [bars]}} -> list of output lines."""
    L = []
    emit = L.append
    ms = {(f, e): measures(data[f][e]) for f in FRAMES for e in ERAS}
    med_tr = {}
    iqr = {}
    emit("# Gold move-size study (C1): output")
    emit("")
    for f in FRAMES:
        emit(f"## {f}")
        for e in ERAS:
            m = ms[(f, e)]
            tr = [x["tr_pct"] for x in m if x["tr_pct"] is not None]
            at = [x["atr_pct"] for x in m if x["atr_pct"] is not None]
            usd = [x["tr"] for x in m if x["tr"] is not None]
            med_tr[(f, e)] = pctl(tr, 50)
            iqr[(f, e)] = (pctl(tr, 25), pctl(tr, 75))
            emit(f"### {e}: {len(m)} bars, {m[0]['t'][:16]} -> {m[-1]['t'][:16]}; "
                 f"true range on {len(tr)} (first bar excluded), ATR % on {len(at)} (warm-up excluded)")
            emit(f"- true range % of price: {_q(tr, (10, 25, 50, 75, 90))}; mean {statistics.fmean(tr):.3f}")
            emit(f"- ATR(14) % of price: {_q(at, (25, 50, 75))}; last bar {at[-1]:.3f}")
            emit(f"- dollars: median true range ${pctl(usd, 50):.2f}; median close ${pctl([x['close'] for x in m], 50):.2f}")
        emit("")
    emit("## A 4-hour bar and an hour compared with a day (median true range % / daily median)")
    for e in ERAS:
        emit(f"- {e}: H4 / D {med_tr[('H4', e)] / med_tr[('D', e)]:.3f}; H1 / D {med_tr[('H1', e)] / med_tr[('D', e)]:.3f}")
    emit("")
    emit("## USED compared with STUDY (median true range %)")
    for f in FRAMES:
        emit(f"- {f}: USED / STUDY {med_tr[(f, 'USED')] / med_tr[(f, 'STUDY')]:.3f}; "
             f"p25-p75 STUDY [{iqr[(f, 'STUDY')][0]:.3f}, {iqr[(f, 'STUDY')][1]:.3f}] "
             f"USED [{iqr[(f, 'USED')][0]:.3f}, {iqr[(f, 'USED')][1]:.3f}] -> "
             f"{overlap_reading(iqr[(f, 'STUDY')], iqr[(f, 'USED')])}")
    emit("")
    emit("## By calendar year, daily bars")
    for e in ERAS:
        for y, rows in by_year(ms[("D", e)]).items():
            at = [x["atr_pct"] for x in rows if x["atr_pct"] is not None]
            atr_txt = f"median ATR {pctl(at, 50):.3f}%" if at else "ATR warm-up only"
            flag = "" if len(rows) >= MIN_YEAR_N else "  INSUFFICIENT"
            emit(f"- {e} {y}: N {len(rows)}; median true range {pctl([x['tr_pct'] for x in rows], 50):.3f}%; "
                 f"{atr_txt}; median close ${pctl([x['close'] for x in rows], 50):.2f}{flag}")
    emit("")
    emit("Bars are not independent (volatility clusters), so no interval is given (spec §5.1).")
    emit("Descriptive only: no entries, no R, no costs. Not evidence of an edge (spec §5.4).")
    return L


def main(root):
    data = {f: load(os.path.join(root, name), sha) for f, (name, sha) in FILES.items()}
    print("\n".join(report(data)))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
