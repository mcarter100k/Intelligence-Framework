"""gold_pullback_depth_study.py — how deep gold's first pullback goes
(docs/specs/gold_pullback_depth_study_spec.md, gold plan C3). Descriptive; prints only.

usage: python3 -I gold_pullback_depth_study.py <legs_archive_dir>

<legs_archive_dir> is ~/intel_study_archives/research_archive_legs. Reads the
gold D and H4 files (hash-pinned), per era (STUDY, USED), and runs R39's leg
detector (first_pullback_study.find_entries, unchanged, any 13-week direction)
at each depth, for rallies and, mirrored, for falls. No entries, no R, no costs.
"""
import os
import sys
from collections import Counter
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import first_pullback_study as FP  # noqa: E402  R39's detector and context, unchanged
from gold_breakout_study import newcombe, wilson  # noqa: E402  (C2's tested intervals)
from gold_move_size_study import ERAS, load  # noqa: E402  (C1's hash- and exam-checked loader)

DEPTHS = (0.236, 0.382, 0.5, 0.618)
SECONDARY = (0.786, 1.0)
MIN_N = 20
FILES = {
    "D": ("XAU_USD_D.csv", "6202a13d86459d2d3453c31ea9ddf40a3aca44243a6d4ff75bf3d0c165d0e3ca"),
    "H4": ("XAU_USD_H4.csv", "e101117de1af589820a10eb4b5e65b30a4f294e9ee7683ac1baf8a8c02f0011c"),
}
SIDES = (("rallies", 1), ("falls", -1))
R39_GBP = {"GBP/JPY": {0.382: "89.6% (121/135)", 0.5: "74.1% (100/135)"},
           "GBP/AUD": {0.382: "81.0% (98/121)", 0.5: "66.1% (80/121)"}}


# ── data ─────────────────────────────────────────────────────────────────────

def era_bars(d_rows, h4_rows):
    """One era's (bars, atr, trend) for the detector: H4 bars as FP.load_pair
    returns them, context from this era's own daily sessions only."""
    d1 = {datetime.fromisoformat(t): (o, h, l, c) for t, o, h, l, c, _ in d_rows}
    opens = [datetime.fromisoformat(r[0]) for r in h4_rows]
    bars = {"opens": opens, "O": [r[1] for r in h4_rows], "H": [r[2] for r in h4_rows],
            "L": [r[3] for r in h4_rows], "C": [r[4] for r in h4_rows]}
    atr, trend = FP.bar_context(opens, FP.session_table(d1))
    return bars, atr, trend


# ── legs ─────────────────────────────────────────────────────────────────────

def side_arrays(bars, trend, side):
    if side == 1:
        return bars["O"], bars["H"], bars["L"], trend
    O, H, L, _, tr = FP.mirrored(bars, trend)
    return O, H, L, tr


def depth_counts(bars, atr, trend, side, depth):
    """{'qualified', 'reached', 'expired', 'cut', 'legs'} at one depth (spec §3-§4).
    'cut' = qualified legs neither reached nor expired: only the last leg can
    still be open at the era's end, so it is 0 or 1."""
    O, H, L, tr = side_arrays(bars, trend, side)
    _, legs = FP.find_entries(O, H, L, atr, tr, depth, use_trend=False)
    q, r, e = legs["qualified impulses"], legs["first touches"], legs["expired qualified"]
    return {"qualified": q, "reached": r, "expired": e, "cut": q - r - e, "legs": legs}


def qualified_anchor_years(bars, atr, trend, side):
    """Calendar year of each qualified leg's anchor. A depth of minus infinity puts
    the level above every price, so the unchanged detector touches every qualified
    leg on the bar after it qualifies; those touches carry the anchor."""
    O, H, L, tr = side_arrays(bars, trend, side)
    en, _ = FP.find_entries(O, H, L, atr, tr, float("-inf"), use_trend=False)
    return Counter(bars["opens"][x["anchor_bar"]].year for x in en)


def monotonic(shares):
    """Spec §4.5: [(depth, reached, n)] in increasing depth -> True if no share rises."""
    s = [r / n for _, r, n in shares if n]
    return all(a >= b - 1e-12 for a, b in zip(s, s[1:]))


# ── report ───────────────────────────────────────────────────────────────────

def reading(x, n):
    """Spec §5 rule 2."""
    if n < MIN_N:
        return "INSUFFICIENT"
    lo, hi = wilson(x, n)
    return "most reach it" if lo > 0.5 else "most don't" if hi < 0.5 else "about even"


def fmt_cell(c):
    n = c["reached"] + c["expired"]
    head = f"qualified {c['qualified']}; reached {c['reached']}, expired {c['expired']}, cut off {c['cut']}"
    if n == 0:
        return head + " -> no legs"
    lo, hi = wilson(c["reached"], n)
    return (f"{head} -> reached {100 * c['reached'] / n:.1f}% [{100 * lo:.1f}, {100 * hi:.1f}] "
            f"{reading(c['reached'], n)}")


def fmt_diff(a, b):
    na, nb = a["reached"] + a["expired"], b["reached"] + b["expired"]
    if na < MIN_N or nb < MIN_N:
        return "INSUFFICIENT (a cell has fewer than 20 legs)"
    d, lo, hi = newcombe(a["reached"], na, b["reached"], nb)
    verdict = "differ" if lo > 0 or hi < 0 else "no clear difference"
    return f"{100 * d:+.1f} points [{100 * lo:+.1f}, {100 * hi:+.1f}]  {verdict}"


def both(a, b):
    return {k: a[k] + b[k] for k in ("qualified", "reached", "expired", "cut")}


def report(eras):
    """eras: {era: (bars, atr, trend)} -> list of output lines."""
    L = []
    emit = L.append
    depths = DEPTHS + SECONDARY
    cells = {(era, s, d): depth_counts(*eras[era], side, d)
             for era in eras for s, side in SIDES for d in depths}
    emit("# Gold pullback-depth study (C3): output")
    emit("")
    for era, (bars, atr, trend) in eras.items():
        o = bars["opens"]
        emit(f"## {era}: {len(o)} H4 bars, {o[0].isoformat()[:16]} -> {o[-1].isoformat()[:16]}")
        for s, side in SIDES:
            lg = cells[(era, s, DEPTHS[0])]["legs"]
            emit(f"### {s} ({'pullbacks in a rally' if side == 1 else 'bounces in a fall'})")
            emit(f"- legs: anchors {lg['anchors']}, warm-up {lg['anchors in warm-up (skipped)']}, "
                 f"replaced {lg['replaced by a lower low before a touch']}, "
                 f"expired before qualifying {lg['expired unqualified']}")
            for d in depths:
                tag = "" if d in DEPTHS else "  (secondary)"
                emit(f"- {d:.1%}: {fmt_cell(cells[(era, s, d)])}{tag}")
            years = qualified_anchor_years(bars, atr, trend, side)
            emit(f"- qualified legs by anchor year: {dict(sorted(years.items()))}")
        emit("### both")
        for d in depths:
            emit(f"- {d:.1%}: {fmt_cell(both(cells[(era, 'rallies', d)], cells[(era, 'falls', d)]))}")
        emit("")
    emit("## Rallies minus falls (reached share; 95% Newcombe interval)")
    for era in eras:
        for d in depths:
            emit(f"- {era} {d:.1%}: {fmt_diff(cells[(era, 'rallies', d)], cells[(era, 'falls', d)])}")
    emit("")
    emit("## Stable across eras (rule-2 readings, STUDY / USED)")
    for s in ("rallies", "falls", "both"):
        for d in DEPTHS:
            r = []
            for era in eras:
                c = (both(cells[(era, "rallies", d)], cells[(era, "falls", d)]) if s == "both"
                     else cells[(era, s, d)])
                r.append(reading(c["reached"], c["reached"] + c["expired"]))
            stable = ("INSUFFICIENT" if "INSUFFICIENT" in r
                      else "stable across eras" if len(set(r)) == 1 else "not stable across eras")
            emit(f"- {s} {d:.1%}: {' / '.join(r)} -> {stable}")
    emit("")
    emit("## Check: shares never rise with depth")
    ok = True
    for era in eras:
        for s, _ in SIDES:
            sh = [(d, cells[(era, s, d)]["reached"], cells[(era, s, d)]["reached"] + cells[(era, s, d)]["expired"])
                  for d in depths]
            good = monotonic(sh)
            ok &= good
            emit(f"- {era} {s}: {'ok' if good else 'FAILED: A SHARE ROSE WITH DEPTH; THIS RUN IS NOT USABLE'}")
        for s, _ in SIDES:
            cut = [cells[(era, s, d)]["cut"] for d in depths]
            if any(c not in (0, 1) for c in cut):
                ok = False
                emit(f"- {era} {s}: FAILED: cut-off counts {cut} are not 0 or 1; THIS RUN IS NOT USABLE")
    emit(f"- overall: {'ok' if ok else 'FAILED'}")
    emit("")
    emit("## Context, not a test: R39's GBP figures (2005-2013, quoted from research_findings)")
    for pair, v in R39_GBP.items():
        emit(f"- {pair}: 38.2% {v[0.382]}; 50% {v[0.5]}")
    emit("")
    emit("Legs overlap (a rally leg and a fall leg can run at once), so the intervals are")
    emit("approximate and somewhat too narrow (spec §5.5). Shares are lower bounds for")
    emit("'eventually' (spec §5.6). Descriptive only: no entries, no R, no costs (spec §5.7).")
    return L


def build(rows):
    """rows: {'D': {era: rows}, 'H4': {era: rows}} -> {era: (bars, atr, trend)}, each
    era from its own rows only (spec §2)."""
    return {era: era_bars(rows["D"][era], rows["H4"][era]) for era in ERAS}


def main(root):
    rows = {f: load(os.path.join(root, name), sha) for f, (name, sha) in FILES.items()}
    print("\n".join(report(build(rows))))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
