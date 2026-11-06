"""Side-by-side comparison of two session movement runs
(docs/specs/session_movement_replication_spec.md §4-§6). Computes nothing
the spec does not name.

usage: python3 -I session_movement_compare.py <earlier_report_md> <modern_stdout>

<earlier_report_md>  studies/session_movement_report.md (stdout read from its §7)
<modern_stdout>      stdout of `session_movement_replication.py modern`
"""
import math
import os
import re
import sys
from statistics import NormalDist

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "foundation", "tools"))
from power_check import sidak_alpha  # noqa: E402

PAIRS = ("GBP_AUD", "GBP_JPY")
BLOCKS = ("SYDNEY", "TOKYO", "LONDON", "LDN_NY", "NY_PM")
N_COMPARISONS = 20
ALPHA = 0.05
ALPHA_SIDAK = sidak_alpha(ALPHA, N_COMPARISONS)
SHARE_PP = 5.0
RATIO_DIFF = 0.5
PRE_RATIO, PRE_SHARE = 2.5, 35.0
CONSISTENT = "CONSISTENT WITH THE EARLIER PERIOD"
MATERIAL = "MATERIAL"


# ── parsing the runner's stdout ──────────────────────────────────────────────

def stdout_from_report(text):
    i = text.index("## 7. Full output")
    j = text.index("```\n", i) + 4
    return text[j:text.rindex("```")]


def _rows(lines, start):
    """Table rows (lists of cells) after the line index `start`, to the first blank after the table."""
    out, seen = [], False
    for ln in lines[start + 1:]:
        if ln.startswith("|"):
            seen = True
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if not set("".join(cells)) <= set("-"):
                out.append(cells)
        elif seen:
            break
    return out[1:]                                   # drop the header row


def parse(text):
    lines = text.splitlines()
    res = {p: {} for p in PAIRS}
    pair = None
    for k, ln in enumerate(lines):
        m = re.match(r"^## (GBP_AUD|GBP_JPY)$", ln)
        if m:
            pair = m.group(1)
            continue
        if pair is None:
            continue
        r = res[pair]
        if ln.startswith(f"**Q1 {pair}, all weekdays**"):
            r["q1"] = {int(c[0][:2]): (float(c[3]), float(c[4])) for c in _rows(lines, k)}
        elif ln.startswith(f"**Q2 {pair}, all weekdays**"):
            r["q2"] = {c[0]: float(c[5]) for c in _rows(lines, k)}
        elif ln.startswith(f"**Q3 {pair}, all weekdays**"):
            r["q3_n"] = int(re.search(r"N days (\d+)", ln).group(1))
            r["q3"] = {c[0]: (float(c[1].rstrip("%")), float(c[2].rstrip("%"))) for c in _rows(lines, k)}
            same = next(x for x in lines[k:] if x.startswith("High and low in the same block"))
            r["q3_same"] = float(re.search(r"([\d.]+)%", same).group(1))
        elif ln.startswith(f"**Q4 {pair}, all weekdays**"):
            r["q4"] = {c[0]: (float(c[3].rstrip("%")), float(c[4].rstrip("%"))) for c in _rows(lines, k)}
        elif ln.startswith("### Q5."):
            r["q5"] = {c[0]: float(c[1].split()[0]) for c in _rows(lines, k)}
    for ln in lines:
        m = re.match(r"^(GBP_AUD|GBP_JPY): largest hourly mean ([\d.]+) at (\d\d):00 UTC; "
                     r"smallest ([\d.]+) at (\d\d):00 UTC; ratio ([\d.]+)$", ln)
        if m:
            res[m.group(1)]["ratio"] = (float(m.group(6)), int(m.group(3)), int(m.group(5)))
    for p in PAIRS:
        missing = {"q1", "q2", "q3", "q3_n", "q3_same", "q4", "q5", "ratio"} - set(res[p])
        if missing:
            raise ValueError(f"{p}: could not parse {sorted(missing)}")
    return res


# ── tests and verdicts (spec §5, §6) ─────────────────────────────────────────

def two_prop_z(pct1, n1, pct2, n2):
    """Pooled two-sided two-proportion z-test on percentages. Returns (z, p)."""
    p1, p2 = pct1 / 100, pct2 / 100
    p = (p1 * n1 + p2 * n2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return 0.0, 1.0
    z = (p2 - p1) / se
    return z, 2 * (1 - NormalDist().cdf(abs(z)))


def share_verdict(diff_pp, pval):
    stat, prac = pval < ALPHA_SIDAK, abs(diff_pp) >= SHARE_PP
    if stat and prac:
        return MATERIAL
    if stat:
        return CONSISTENT + " (statistical gate only)"
    if prac:
        return CONSISTENT + " (practical gate only)"
    return CONSISTENT


def ratio_verdict(diff):
    return (MATERIAL if abs(diff) >= RATIO_DIFF else CONSISTENT) + " — SINGLE-GATE"


def precondition(ratio, q3):
    top = max(max(h, l) for h, l in q3.values())
    return ("PASS" if ratio > PRE_RATIO and top >= PRE_SHARE else "FAIL"), top


# ── report ───────────────────────────────────────────────────────────────────

def pacific(h):
    return f"{(h - 8) % 24:02d}:00 PST / {(h - 7) % 24:02d}:00 PDT"


def report(old, new):
    print("# Side by side: 2005–2013 (STUDY) against 2021-04-27 → 2026-09-09 (USED)\n")
    print(f"Šidák per-comparison α for {N_COMPARISONS} comparisons: {ALPHA_SIDAK:.4f} "
          f"(family-wise rate at a naive {ALPHA} each: {1 - (1 - ALPHA) ** N_COMPARISONS:.0%}).\n")
    material = []
    for pair in PAIRS:
        o, n = old[pair], new[pair]
        print(f"\n## {pair}\n")
        print("### Q1. Hourly range (pips; levels differ with each era's volatility — compare shapes)\n")
        print("| UTC hour | Pacific | 2005–2013 mean | median | 2021–2026 mean | median |")
        print("|---|---|---|---|---|---|")
        for h in list(range(21, 24)) + list(range(0, 21)):
            print(f"| {h:02d}:00 | {pacific(h)} | {o['q1'][h][0]:.1f} | {o['q1'][h][1]:.1f} | "
                  f"{n['q1'][h][0]:.1f} | {n['q1'][h][1]:.1f} |")
        ro, rn = o["ratio"], n["ratio"]
        d = rn[0] - ro[0]
        v = ratio_verdict(d)
        print(f"\nBusiest ÷ quietest hour: 2005–2013 {ro[0]:.2f} (busiest {ro[1]:02d}:00, quietest "
              f"{ro[2]:02d}:00 UTC); 2021–2026 {rn[0]:.2f} (busiest {rn[1]:02d}:00, quietest "
              f"{rn[2]:02d}:00 UTC); difference {d:+.2f} → **{v}**")
        if v.startswith(MATERIAL):
            material.append(f"{pair} ratio")

        print("\n### Q2. Median share of the day's range, per block\n")
        print("| block | 2005–2013 | 2021–2026 |")
        print("|---|---|---|")
        for b in BLOCKS:
            print(f"| {b} | {o['q2'][b]:.3f} | {n['q2'][b]:.3f} |")

        print(f"\n### Q3. Where the daily high and low form (N days {o['q3_n']} and {n['q3_n']})\n")
        print("| block | extreme | 2005–2013 | 2021–2026 | difference (pts) | z | p (two-sided) "
              f"| p < 0.05 | p < {ALPHA_SIDAK:.4f} | verdict |")
        print("|---|---|---|---|---|---|---|---|---|---|")
        for b in BLOCKS:
            for i, ext in enumerate(("high", "low")):
                a, c = o["q3"][b][i], n["q3"][b][i]
                z, p = two_prop_z(a, o["q3_n"], c, n["q3_n"])
                v = share_verdict(c - a, p)
                if v == MATERIAL:
                    material.append(f"{pair} {b} {ext}")
                print(f"| {b} | {ext} | {a:.1f}% | {c:.1f}% | {c - a:+.1f} | {z:+.2f} | {p:.4f} | "
                      f"{'yes' if p < ALPHA else 'no'} | {'yes' if p < ALPHA_SIDAK else 'no'} | {v} |")
        print(f"\nHigh and low in the same block: 2005–2013 {o['q3_same']:.1f}%, 2021–2026 {n['q3_same']:.1f}% "
              "(shown, not tested)")

        print("\n### Q4. Share of days with the extreme already in place\n")
        print("| by | 2005–2013 high | 2021–2026 high | 2005–2013 low | 2021–2026 low |")
        print("|---|---|---|---|---|")
        for k in o["q4"]:
            print(f"| {k} | {o['q4'][k][0]:.1f}% | {n['q4'][k][0]:.1f}% | {o['q4'][k][1]:.1f}% | {n['q4'][k][1]:.1f}% |")

        print("\n### Q5. Mean ATR(14), pips (numbers only)\n")
        print("| timeframe | 2005–2013 | 2021–2026 |")
        print("|---|---|---|")
        for tf in ("H1", "H4", "D1"):
            print(f"| {tf} | {o['q5'][tf]:.1f} | {n['q5'][tf]:.1f} |")

    print("\n## Day-trading precondition (USED span; ratio > 2.5 AND a block ≥ 35% of highs or lows)\n")
    print("| pair | busiest ÷ quietest | largest block share of highs or lows | result |")
    print("|---|---|---|---|")
    for pair in PAIRS:
        res, top = precondition(new[pair]["ratio"][0], new[pair]["q3"])
        print(f"| {pair} | {new[pair]['ratio'][0]:.2f} | {top:.1f}% | **{res}** |")

    print(f"\n## Materiality summary\n\nMATERIAL differences: {len(material)} of {N_COMPARISONS} Q3 "
          f"comparisons and 2 ratio comparisons" + (": " + ", ".join(material) if material else "."))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    with open(sys.argv[1]) as fh:
        old = parse(stdout_from_report(fh.read()))
    with open(sys.argv[2]) as fh:
        new = parse(fh.read())
    report(old, new)
