"""gold_program_screen.py — owner rulings E1/E2/E7 (2026-11-17). Report-only.

Part 1 (E1, E2): episode counts on gold's 2006-2013 STUDY bars for every proposed
rule. Counts only: no outcome, no R. GBP-replication rules reuse the original
studies' detectors unchanged; never-tested patterns use provisional mechanical
definitions (stated in the output) that exist only to count.
Part 2 (E7): horizon, on the USED span (2021-2026; learning data), for one
representative rule (GMW-1 B1's direction signal): gross and net R at the
same-day 1:00 PM PT exit and at the 1st, 2nd, 5th and 10th following session
close.
"""
import bisect, math, os, statistics, sys
from collections import Counter
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
W = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, W)
sys.path.insert(0, os.path.join(os.path.dirname(W), "foundation", "tools"))
import gold_move_size_study as GM            # hash- and exam-checked loader
import first_pullback_study as FP            # R37/R38 detector
import breakout_confirmation_study as B1     # R43 detector
import htf_breakout_study as B2              # R44 levels, trend, events
import history_study_convert as C
import power_check as P
from gold_pullback_depth_study import era_bars

PT, NY = ZoneInfo("America/Los_Angeles"), ZoneInfo("America/New_York")
ROOT = sys.argv[1]
FILES = {"D": ("XAU_USD_D.csv", "6202a13d86459d2d3453c31ea9ddf40a3aca44243a6d4ff75bf3d0c165d0e3ca"),
         "H4": ("XAU_USD_H4.csv", "e101117de1af589820a10eb4b5e65b30a4f294e9ee7683ac1baf8a8c02f0011c"),
         "H1": ("XAU_USD_H1.csv", "eabec6652e055540b256aa743971a1a5aa5cbb459e94b4887da6f28b8e02a4be")}
rows = {k: GM.load(os.path.join(ROOT, f), s) for k, (f, s) in FILES.items()}
asdict = lambda rs: {datetime.fromisoformat(r[0]): (r[1], r[2], r[3], r[4]) for r in rs}

def episodes(entries, horizon):
    out = []
    for t in sorted(entries, key=lambda x: (x["bar"], -x["side"])):
        if not out or t["bar"] - out[-1]["bar"] >= horizon:
            out.append(t)
    return out

def neg(b):
    return {"opens": b["opens"], "O": [-x for x in b["O"]], "H": [-x for x in b["L"]], "L": [-x for x in b["H"]], "C": [-x for x in b["C"]]}

result = {}
print("# Part 1: episode counts, gold 2006-03-21 -> 2013-12-30 (STUDY); no outcomes\n")
# ── R37/R38 first pullback (13-week trend), H4, 30-bar episodes ──
bars, atr, trend = era_bars(rows["D"]["STUDY"], rows["H4"]["STUDY"])
n4 = len(bars["O"])
print(f"H4 bars {n4}; ceiling for any 30-bar-episode rule: {n4 // 30}")
for lvl in (0.382, 0.5):
    ents = []
    for side in (1, -1):
        O, H, L, Cl, tr = (bars["O"], bars["H"], bars["L"], bars["C"], trend) if side == 1 else FP.mirrored(bars, trend)
        en, _ = FP.find_entries(O, H, L, atr, tr, lvl)
        ents += [{"bar": e["bar"], "side": side} for e in en if e["bar"] + 30 < n4]
    ep = episodes(ents, 30)
    result[f"R37/R38 first pullback {lvl:.1%}"] = len(ep)
    print(f"- R37/R38 first pullback to {lvl:.1%} with the 13-week trend: entries {len(ents)}, episodes {len(ep)}")

# ── R43 hourly two-close breakout (k=5), H1, 24-bar episodes ──
h1 = asdict(rows["H1"]["STUDY"]); ts = sorted(h1)
hb = {"opens": ts, "O": [h1[t][0] for t in ts], "H": [h1[t][1] for t in ts], "L": [h1[t][2] for t in ts], "C": [h1[t][3] for t in ts]}
n1 = len(ts)
cells = {"A": [], "B": [], "C": []}
for side, b in ((1, hb), (-1, neg(hb))):
    ev, _ = B1.find_events(b["C"], b["H"])
    for e in ev:
        j = e["bar"]
        if e["fake"] is None:
            continue
        if j + 24 < n1:
            cells["A"].append({"bar": j, "side": side})
        if not e["fake"] and j + 1 + 24 < n1:
            cells["B"].append({"bar": j + 1, "side": side})
            f, _px = B1.retest_fill(b["O"], b["L"], j + 1, e["level"])
            if f is not None and f + 24 < n1:
                cells["C"].append({"bar": f, "side": side})
for c, ents in cells.items():
    ep = episodes(ents, 24)
    result[f"R43 hourly breakout cell {c}"] = len(ep)
    print(f"- R43 hourly breakout, cell {c}: entries {len(ents)}, episodes {len(ep)}")

# ── R44 daily/weekly level breaks with the daily trend (upper bound: no obstacle or stop-width filter), H1, 120-bar episodes ──
d1 = asdict(rows["D"]["STUDY"])
b2, sess = B2.prepare(h1, d1)
nk = len(sess["days"])
for entry in ("B", "C"):
    ents = []
    for side in (1, -1):
        bb, ss = (b2, sess) if side == 1 else (dict(neg(b2), k=b2["k"], atr=b2["atr"]), B2.mirror_sess(sess))
        levels = B2.htf_levels(ss)
        tr = B2.trend_by_k(ss, nk)
        ev, _ = B2.find_events(bb["C"], bb["k"], levels)
        for e in ev:
            j = e["bar"]
            if e["fake"] or tr[bb["k"][j]] != 1:
                continue
            if entry == "B" and j + 1 + 120 < len(bb["C"]):
                ents.append({"bar": j + 1, "side": side})
            if entry == "C":
                f, _ = B1.retest_fill(bb["O"], bb["L"], j + 1, e["level"])
                if f is not None and f + 120 < len(bb["C"]):
                    ents.append({"bar": f, "side": side})
    ep = episodes(ents, 120)
    result[f"R44 daily/weekly breaks, entry {entry} (upper bound)"] = len(ep)
    print(f"- R44 daily/weekly level breaks with the daily trend, entry {entry}: entries {len(ents)}, episodes {len(ep)} "
          f"(upper bound: before the obstacle and stop-width filters)")

# ── never-tested patterns on H4, markup swings k=4, 30-bar episodes ──
K = 4
def swings_idx(Hx, Lx, k=K):
    hs, ls = [], []
    for i in range(k, len(Hx) - k):
        win = range(i - k, i + k + 1)
        if all(Hx[i] > Hx[x] for x in win if x != i): hs.append(i)
        if all(Lx[i] < Lx[x] for x in win if x != i): ls.append(i)
    return hs, ls
O, H, L, Cl = bars["O"], bars["H"], bars["L"], bars["C"]
hs, ls = swings_idx(H, L)
rng14 = [None] * n4
for i in range(14, n4):
    rng14[i] = statistics.fmean(H[x] - L[x] for x in range(i - 14, i))

def double(side):
    """Double bottom (side 1) / top (-1): consecutive swing lows within 0.25 daily ATR, neckline
    (highest high between) at least 0.5 ATR above the higher low; break = first close beyond the
    neckline within 60 bars of the second low's confirmation, before a close beyond the lows;
    retest = first touch of the neckline within 12 bars after the break."""
    Hx, Lx, Cx = (H, L, Cl) if side == 1 else ([-x for x in L], [-x for x in H], [-x for x in Cl])
    _, lows = swings_idx(Hx, Lx)
    brk, ret = [], []
    for a, b in zip(lows, lows[1:]):
        A = atr[b]
        if A is None or abs(Lx[a] - Lx[b]) > 0.25 * A:
            continue
        neck = max(Hx[a:b + 1])
        if neck - max(Lx[a], Lx[b]) < 0.5 * A:
            continue
        floor_ = min(Lx[a], Lx[b])
        for j in range(b + K + 1, min(b + K + 61, n4)):
            if Cx[j] < floor_:
                break
            if Cx[j] > neck:
                if j + 30 < n4: brk.append({"bar": j, "side": side})
                for f in range(j + 1, min(j + 13, n4)):
                    if Lx[f] <= neck:
                        if f + 30 < n4: ret.append({"bar": f, "side": side})
                        break
                break
    return brk, ret

def hs_pattern(side):
    """Head and shoulders (side -1, short) / inverse (side 1): three consecutive swing highs, head
    at least 0.25 ATR above both shoulders, shoulders within 0.25 ATR; neckline = the lower of the
    two troughs between; break = first close beyond it within 60 bars of the right shoulder's
    confirmation, before a close beyond the head."""
    Hx, Lx, Cx = (H, L, Cl) if side == -1 else ([-x for x in L], [-x for x in H], [-x for x in Cl])
    highs, _ = swings_idx(Hx, Lx)
    out = []
    for a, h, c in zip(highs, highs[1:], highs[2:]):
        A = atr[c]
        if A is None or Hx[h] - max(Hx[a], Hx[c]) < 0.25 * A or abs(Hx[a] - Hx[c]) > 0.25 * A:
            continue
        neck = min(min(Lx[a:h + 1]), min(Lx[h:c + 1]))
        for j in range(c + K + 1, min(c + K + 61, n4)):
            if Cx[j] > Hx[h]:
                break
            if Cx[j] < neck:
                if j + 30 < n4: out.append({"bar": j, "side": side})
                break
    return out

def last_swing_level(i, side):
    """Latest swing low (side 1) / high (-1) confirmed before bar i."""
    src = ls if side == 1 else hs
    k = bisect.bisect_left([s + K for s in src], i)
    return None if k == 0 else (L if side == 1 else H)[src[k - 1]]

def candles():
    pin, pin_lv, eng, eng_lv = [], [], [], []
    for i in range(15, n4 - 30):
        r = H[i] - L[i]
        if rng14[i] is None or r < rng14[i] or atr[i] is None:
            continue
        body = abs(Cl[i] - O[i])
        for side in (1, -1):
            wick = (min(O[i], Cl[i]) - L[i]) if side == 1 else (H[i] - max(O[i], Cl[i]))
            lvl = last_swing_level(i, side)
            near = lvl is not None and abs((L[i] if side == 1 else H[i]) - lvl) <= 0.15 * atr[i]
            if body <= r / 3 and wick >= 2 * r / 3:
                pin.append({"bar": i + 1, "side": side})
                if near: pin_lv.append({"bar": i + 1, "side": side})
            pb, cb = Cl[i - 1] - O[i - 1], Cl[i] - O[i]
            if side * pb < 0 and side * cb > 0 and max(O[i], Cl[i]) >= max(O[i - 1], Cl[i - 1]) and min(O[i], Cl[i]) <= min(O[i - 1], Cl[i - 1]):
                eng.append({"bar": i + 1, "side": side})
                if near: eng_lv.append({"bar": i + 1, "side": side})
    return pin, pin_lv, eng, eng_lv

def trendlines():
    """Line through two consecutive swing highs (second lower) for a long break; the mirror for
    shorts. Break = first close beyond the projected line within 120 bars of the second swing's
    confirmation; bounce = first bar touching the line (within 0.05 daily ATR) and closing back,
    before any break."""
    brk, bnc = [], []
    for side in (1, -1):
        Hx, Lx, Cx = (H, L, Cl) if side == 1 else ([-x for x in L], [-x for x in H], [-x for x in Cl])
        highs, _ = swings_idx(Hx, Lx)
        for a, b in zip(highs, highs[1:]):
            if Hx[b] >= Hx[a]:
                continue
            slope = (Hx[b] - Hx[a]) / (b - a)
            line = lambda j: Hx[b] + slope * (j - b)
            bounced = False
            for j in range(b + K + 1, min(b + K + 121, n4)):
                if Cx[j] > line(j):
                    if j + 30 < n4: brk.append({"bar": j, "side": side})
                    break
                if not bounced and atr[j] is not None and Hx[j] >= line(j) - 0.05 * atr[j] and Cx[j] < line(j):
                    bounced = True
                    if j + 30 < n4: bnc.append({"bar": j, "side": -side})
    return brk, bnc

db_b, db_r = double(1); dt_b, dt_r = double(-1)
pats = {"double bottom/top: neckline break": db_b + dt_b, "double bottom/top: neckline retest": db_r + dt_r,
        "head and shoulders (and inverse): neckline break": hs_pattern(-1) + hs_pattern(1)}
pin, pin_lv, eng, eng_lv = candles()
pats.update({"pin bar (H4), anywhere": pin, "pin bar at a swing level": pin_lv,
             "engulfing (H4), anywhere": eng, "engulfing at a swing level": eng_lv})
tb, tbo = trendlines()
pats.update({"trendline break": tb, "trendline bounce": tbo})
for name, ents in pats.items():
    ep = episodes(ents, 30)
    result[name] = len(ep)
    print(f"- {name}: events {len(ents)}, episodes {len(ep)}")

print("\n# M41 arithmetic: smallest detectable effect at 80% power, SD 1.2R")
for name, n in result.items():
    vals = [f"K={K_}: {P.min_detectable_edge(1.2, max(n, 2), alpha=1 - 0.95 ** (1 / K_)):+.3f}R" for K_ in (24, 6, 3, 2)]
    print(f"- {name}: N {n}; " + "; ".join(vals))

# ── Part 2: horizon (E7), USED span, GMW-1 B1 direction ──
print("\n# Part 2: horizon, USED 2021-04-27 -> 2026-09-09 (learning data), GMW-1 B1 direction, timed exits (no stop)")
import gold_morning_window_study as G
uh1, ud1 = asdict(rows["H1"]["USED"]), asdict(rows["D"]["USED"])
days, _ = G.build_days(uh1, ud1)
pop = G.population(days)
dts = sorted(ud1); sdays = [C.session_day(t) for t in dts]; closes = [ud1[t][3] for t in dts]
H_ = ("same day 1 PM (GMW-1's exit)", "same session close (2 PM)", "+1 session", "+2 sessions", "+5 sessions", "+10 sessions")
OFF = {H_[1]: 0, H_[2]: 1, H_[3]: 2, H_[4]: 5, H_[5]: 10}
gross = {h: [] for h in H_}; net = {h: [] for h in H_}; drift = {h: [] for h in H_}
for x in pop:
    if 6 not in x["bars"] or 12 not in x["bars"]:
        continue
    e, d, s = x["bars"][6][3], x["d"], x["dir"]
    k = bisect.bisect_left(sdays, x["sday"])
    if k >= len(sdays) or sdays[k] != x["sday"] or k + 10 >= len(closes):
        continue
    exits = {H_[0]: x["bars"][12][3]}
    exits.update({h: closes[k + o] for h, o in OFF.items()})
    for h, px in exits.items():
        gross[h].append(s * (px - e) / d); net[h].append(s * (px - e) / d - 0.5 / d); drift[h].append((px - e) / d)
for h in H_:
    g, n_ = gross[h], net[h]
    m, sd = statistics.fmean(g), statistics.stdev(g)
    print(f"- {h}: N {len(g)}; gross {m:+.4f}R; net of $0.50 {statistics.fmean(n_):+.4f}R; SD {sd:.3f}R; "
          f"t (gross) {m / (sd / math.sqrt(len(g))):+.2f}; mean cost {statistics.fmean(a - b for a, b in zip(g, n_)):.4f}R; "
          f"always-long drift {statistics.fmean(drift[h]):+.4f}R")
