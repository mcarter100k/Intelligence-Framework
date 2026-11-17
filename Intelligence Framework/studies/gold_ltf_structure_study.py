"""GLS-1 runner: gold's lower-timeframe structure, a descriptive catalogue
(docs/specs/gold_ltf_structure_spec.md v5, commit af63c76). 2021-2026 USED only.

usage:
  python3 -I gold_ltf_structure_study.py counts <archive_dir> <subhourly_dir> <fred_DFEDTARU.csv>
  python3 -I gold_ltf_structure_study.py full   <archive_dir> <subhourly_dir> <fred_DFEDTARU.csv>

counts prints population sizes only (setups, entries, missed, wait buckets,
volatility terciles, pattern occurrences, swing points, pullback legs): nothing
that depends on how a trade or a swing turned out. full prints part A (no
costs: §4 before costs, §5, §6) and then part B (§4.5: the four entries under
the CFD and futures cost structures, and the ranking-flip check).

DESCRIPTIVE, not tradeable. 2021-2026 only, a regime-specific description.
Structures counted on history; none is a signal. Hindsight tables add
"Selected on the outcome".
"""
import bisect
import os
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import first_pullback_study as FP  # noqa: E402  R48's detector and daily context, unchanged
import gold_gls1_inputs as I  # noqa: E402  swings, structure breaks, sub-hourly loader (tested)
import gold_gls1_window_financing as WF  # noqa: E402  first valid entry, sessions, rates (tested)
from gold_breakout_study import newcombe, wilson  # noqa: E402
from gold_move_size_study import load  # noqa: E402  hash- and exam-checked loader
from gold_pullback_depth_study import FILES, era_bars, side_arrays  # noqa: E402
from gold_rule_costs import held_nights  # noqa: E402

NY, PT, UTC = ZoneInfo("America/New_York"), ZoneInfo("America/Los_Angeles"), timezone.utc
SEED, B = 20261117, 2000
HOLDS = (1, 2, 5, 10)
WORK_ATR = 1.0                                   # §4.1 a setup worked: +1.0 daily ATR before its stop
MAX_SESSIONS = 10                                # §4.2 entries within 10 sessions (H1)
ONE_SESSION = 6                                  # §4.2 secondary cut, in 4-hour bars (H1)
BUCKETS = ((1, 1), (2, 2), (3, 6), (7, 12), (13, 10 ** 6))   # §4.2 wait buckets, 4-hour bars (H1)
VOL_CUTS = (1.206, 1.480)                        # §1.4 daily ATR / price, % (H3, primary)
USD_CUTS = (23.89, 34.78)                        # §1.4 daily ATR in dollars (secondary)
MIN_STOP_ATR = 0.3                               # risk_and_execution.md minimum stop
RHO = 3.130                                      # §1.2 daily ATR / 4-hour median range (F3)
M15, M25, M50 = 0.15 * RHO, 0.25 * RHO, 0.5 * RHO
MED_BARS, CONS_N, CONS_X, RETEST, PAT_WIN = 14, 12, 2.0, 12, 60
SWING_RUN_BARS, IMPULSE_ATR, PB_BARS = 60, 1.5, 60   # §5.1, §6.1, §6.2
LEVELS = (0.382, 0.5, 0.618)
MARKUP = 2.5                                     # CFD financing markup, % a year (GNC-1 §3.3)
TICK, COMM, ROLL, LEASE = 0.10, 0.05, 0.20, 0.0  # §4.5 futures placeholders, $ an ounce / %
ROLL_MONTHS, ROLL_DAY = (1, 3, 5, 7, 9, 11), 25
SPAN = {"D": timedelta(days=1), "H4": timedelta(hours=4), "M30": timedelta(minutes=30),
        "M15": timedelta(minutes=15), "M5": timedelta(minutes=5)}
LTF = ("M30", "M15", "M5")
STAMP = ("DESCRIPTIVE, not tradeable. 2021-2026 only, a regime-specific description. "
         "Structures counted on history; none is a signal.")
HINDSIGHT = "Selected on the outcome"


# ── small helpers ────────────────────────────────────────────────────────────

def bucket(w):
    for lo, hi in BUCKETS:
        if lo <= w <= hi:
            return f"{lo}" if lo == hi else (f"{lo}-{hi}" if hi < 10 ** 6 else f"{lo}+")
    return None


def tercile(x, cuts):
    return "low" if x < cuts[0] else "mid" if x < cuts[1] else "high"


def nth_session_day(d, h):
    while h:
        d += timedelta(days=1)
        if d.weekday() < 5:
            h -= 1
    return d


def boot_ci(vals, clusters, rng, b=B):
    """95% interval for the mean, resampling clusters (sessions) with replacement."""
    vals = np.asarray(vals, float)
    if len(vals) < 2:
        return (float("nan"), float("nan"))
    keys, inv = np.unique(np.asarray(clusters), return_inverse=True)
    sums = np.bincount(inv, weights=vals)
    cnts = np.bincount(inv).astype(float)
    idx = rng.integers(0, len(keys), size=(b, len(keys)))
    means = sums[idx].sum(1) / cnts[idx].sum(1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def summ(vals, clusters, rng):
    v = np.asarray(vals, float)
    if len(v) == 0:
        return "n 0"
    lo, hi = boot_ci(v, clusters, rng)
    srt = np.sort(v)
    k = max(1, int(round(0.01 * len(v))))
    wo = srt[:-k].mean() if len(v) > k else float("nan")
    return (f"n {len(v)}; mean {v.mean():+.3f} [{lo:+.3f}, {hi:+.3f}]; median {np.median(v):+.3f}; "
            f"SD {v.std(ddof=1) if len(v) > 1 else 0:.3f}; mean w/o best 1% {wo:+.3f}; "
            f"positive {100 * (v > 0).mean():.1f}%")


def share(x, n):
    if n == 0:
        return "n 0"
    lo, hi = wilson(x, n)
    return f"{x}/{n} = {100 * x / n:.1f}% [{100 * lo:.1f}, {100 * hi:.1f}]"


def quarts(xs, fmt="{:.2f}"):
    return I.quart(list(xs), fmt)


# ── price path on 5-minute bars ──────────────────────────────────────────────

class Path:
    """5-minute bars: every stop, target and exit is checked here, for every entry."""

    def __init__(self, ts, O, H, L, C):
        self.ts = ts
        self.O, self.H, self.L, self.C = (np.asarray(x, float) for x in (O, H, L, C))
        self.span = SPAN["M5"]

    def rng(self, t_from, t_to):
        return bisect.bisect_left(self.ts, t_from), bisect.bisect_left(self.ts, t_to)

    def price_at(self, t):
        """Close of the last bar opening before t (the price at t)."""
        k = bisect.bisect_left(self.ts, t) - 1
        return None if k < 0 else float(self.C[k])


def simulate(path, side, entry_t, entry_px, stop_px, exit_t):
    """§4.2: from entry_t to exit_t on 5-minute bars. A touch of the stop exits at the stop;
    a gap through it fills at the bar's open. Returns None if no bar lies in the hold."""
    a, b = path.rng(entry_t, exit_t)
    if b <= a:
        return None
    dist = side * (entry_px - stop_px)
    xo = side * path.O[a:b]
    xlo = side * path.L[a:b] if side == 1 else -path.H[a:b]
    xe, xs = side * entry_px, side * stop_px
    mae = max(0.0, xe - float(xlo.min()))
    hit = np.nonzero(xlo <= xs)[0]
    if len(hit):
        k = int(hit[0])
        fill = min(float(xo[k]), xs)
        return {"r": (fill - xe) / dist, "stopped": True, "exit_t": path.ts[a + k] + path.span,
                "stop_k": a + k, "mae": mae, "dist": dist}
    xc = side * float(path.C[b - 1])
    return {"r": (xc - xe) / dist, "stopped": False, "exit_t": exit_t, "stop_k": None, "mae": mae, "dist": dist}


def worked(path, side, entry_t, entry_px, stop_px, target_px, deadline):
    """§4.1: the target is reached before the stop is touched, by the deadline. A bar that
    touches both counts the stop first."""
    a, b = path.rng(entry_t, deadline)
    xs, xt = side * stop_px, side * target_px
    xlo = side * path.L[a:b] if side == 1 else -path.H[a:b]
    xhi = side * path.H[a:b] if side == 1 else -path.L[a:b]
    s = np.nonzero(xlo <= xs)[0]
    t = np.nonzero(xhi >= xt)[0]
    if not len(t):
        return False
    return not len(s) or t[0] < s[0]


def run_after(path, side, entry_px, dist, k_from, t_to):
    """How far a stopped trade's direction went after the stop, in R of that stop."""
    a, b = k_from + 1, bisect.bisect_left(path.ts, t_to)
    if b <= a:
        return 0.0
    xhi = side * path.H[a:b] if side == 1 else -path.L[a:b]
    return max(0.0, (float(xhi.max()) - side * entry_px) / dist)


# ── costs (§4.5, part B) ─────────────────────────────────────────────────────

def spread_at(table, t):
    tp = t.astimezone(PT)
    hr = 15 if tp.hour == 14 else tp.hour             # the daily break: the first quote is the reopen
    return table.get((tp.year, hr))


def cfd_cost(side, entry_t, exit_t, entry_px, rate, sp_entry, sp_exit, short_receives=False):
    """Dollars an ounce: half the spread each way, plus financing (GNC-1; H2 both-pay primary)."""
    nights = held_nights(entry_t, exit_t)
    if side == 1:
        annual = rate + MARKUP
    else:
        annual = -(rate - MARKUP) if short_receives else MARKUP
    return 0.5 * sp_entry + 0.5 * sp_exit + entry_px * annual / 100 * nights / 365


def rolls_between(entry_t, exit_t):
    n, y, m = 0, entry_t.astimezone(NY).year, 1
    while True:
        for mm in ROLL_MONTHS:
            r = datetime(y, mm, ROLL_DAY, 17, 0, tzinfo=NY)
            if r >= exit_t:
                return n
            if r > entry_t:
                n += 1
        y += 1


def futures_cost(side, entry_t, exit_t, entry_px, rate, carry=True):
    """Dollars an ounce (placeholders): one tick of spread, a commission each way, a roll fee
    per roll spanned, and basis decay (a long pays the carry, a short receives it)."""
    c = TICK + 2 * COMM + ROLL * rolls_between(entry_t, exit_t)
    if carry:
        days = (exit_t - entry_t).total_seconds() / 86400
        c += side * entry_px * (rate - LEASE) / 100 * days / 365
    return c


# ── structures (§5.2), detected on the bullish side; bearish = the mirror ────

def median_range(H, L, n=MED_BARS):
    r = np.asarray(H, float) - np.asarray(L, float)
    out = np.full(len(r), np.nan)
    if len(r) > n:
        w = np.lib.stride_tricks.sliding_window_view(r, n)[:-1]
        out[n:] = np.median(w, axis=1)
    return out


def latest_confirmed(ls, i, k=I.K):
    """Most recent swing low confirmed by bar i's close (index into ls), or -1."""
    return bisect.bisect_right([s + k for s in ls], i) - 1


def detect(O, H, L, C, mr):
    """Bullish completions on one side's arrays: {structure: [completion bar]}."""
    n = len(C)
    hs, ls = I.swings(H, L)
    conf_l = [s + I.K for s in ls]
    out = defaultdict(list)
    for i in range(1, n):
        pbh, pbl = max(O[i - 1], C[i - 1]), min(O[i - 1], C[i - 1])
        b = bisect.bisect_right(conf_l, i) - 1
        near = b >= 0 and not np.isnan(mr[i]) and abs(L[i] - L[ls[b]]) <= M15 * mr[i]
        if C[i] > O[i] and C[i] >= pbh and O[i] <= pbl:
            out["engulfing"].append(i)
            if near:
                out["engulfing at a level"].append(i)
        r = H[i] - L[i]
        if not np.isnan(mr[i]) and r > 0 and r >= mr[i] and abs(C[i] - O[i]) <= r / 3 \
                and min(O[i], C[i]) - L[i] >= 2 * r / 3:
            out["pin bar"].append(i)
            if near:
                out["pin bar at a level"].append(i)
    # break and retest
    conf_h = [s + I.K for s in hs]
    used = set()
    for j in range(n):
        a = bisect.bisect_left(conf_h, j) - 1
        if a < 0 or hs[a] in used or C[j] <= H[hs[a]]:
            continue
        used.add(hs[a])
        lvl = H[hs[a]]
        for f in range(j + 1, min(j + 1 + RETEST, n)):
            if L[f] <= lvl:
                out["retest held" if C[f] > lvl else "retest failed"].append(f)
                break
    # double bottom
    for a, b in zip(ls, ls[1:]):
        m = mr[b]
        if np.isnan(m) or abs(L[a] - L[b]) > M25 * m:
            continue
        neck = max(H[a:b + 1])
        if neck - max(L[a], L[b]) < M50 * m:
            continue
        floor_ = min(L[a], L[b])
        for j in range(b + I.K + 1, min(b + I.K + 1 + PAT_WIN, n)):
            if C[j] < floor_:
                break
            if C[j] > neck:
                out["double bottom / top"].append(j)
                break
    # inverse head and shoulders
    for a, h, c in zip(ls, ls[1:], ls[2:]):
        m = mr[c]
        if np.isnan(m) or L[h] > min(L[a], L[c]) - M25 * m or abs(L[a] - L[c]) > M25 * m:
            continue
        neck = max(max(H[a:h + 1]), max(H[h:c + 1]))
        for j in range(c + I.K + 1, min(c + I.K + 1 + PAT_WIN, n)):
            if C[j] < L[h]:
                break
            if C[j] > neck:
                out["head and shoulders"].append(j)
                break
    return out


def consolidations(H, L, C, mr):
    """§5.2: 12 bars spanning <= 2.0 median ranges (taken at the bar before the 12), resolved
    by the first later close outside; non-overlapping. Returns [(resolving bar, side)]."""
    out, k, n = [], CONS_N, len(C)
    while k < n:
        m = mr[k - CONS_N]
        hi, lo = max(H[k - CONS_N:k]), min(L[k - CONS_N:k])
        if np.isnan(m) or hi - lo > CONS_X * m:
            k += 1
            continue
        res = None
        for j in range(k, n):
            if C[j] > hi or C[j] < lo:
                res = (j, 1 if C[j] > hi else -1)
                break
        if res is None:
            break
        out.append(res)
        k = res[0] + 1
    return out


_CACHE = {}


def structures(arr):
    """{(structure, side): [completion bar]} on one timeframe's arrays."""
    key = id(arr)
    if key not in _CACHE:
        _CACHE[key] = _structures(arr)
    return _CACHE[key]


def _structures(arr):
    O, H, L, C = (np.asarray(arr[k], float) for k in "OHLC")
    mr = median_range(H, L)
    occ = {}
    for side in (1, -1):
        if side == 1:
            d = detect(O, H, L, C, mr)
        else:
            d = detect(-O, -L, -H, -C, mr)
        for k, v in d.items():
            occ[(k, side)] = v
    cons = consolidations(H, L, C, mr)
    for side in (1, -1):
        occ[("consolidation", side)] = [j for j, s in cons if s == side]
    return occ


# ── pullbacks (§6) ───────────────────────────────────────────────────────────

def pullback_outcome(H, L, A, B_, t, n_bars=PB_BARS):
    """§6.2 from the touch bar: 'reversed' if price retraced 100% (low <= A) first, 'continued'
    if it made a new extreme (high > B) first, else 'unresolved'. A bar doing both: reversed."""
    for k in range(t, min(t + n_bars + 1, len(H))):
        if L[k] <= A:
            return "reversed"
        if H[k] > B_:
            return "continued"
    return "unresolved"


def swing_legs(H, L, atr, level):
    """§6.1 4-hour swing legs on one side's arrays: impulse from a confirmed swing low to the
    next swing high, >= 1.5 daily ATR; the touch of the level within 60 bars, before any new
    high. Returns [(touch bar, A, B, B bar)]."""
    hs, ls = I.swings(H, L)
    out = []
    for a in ls:
        k = bisect.bisect_right(hs, a)
        if k >= len(hs):
            break
        b = hs[k]
        if atr[b] is None or H[b] - L[a] < IMPULSE_ATR * atr[b]:
            continue
        lvl = H[b] - level * (H[b] - L[a])
        for t in range(b + 1, min(b + 1 + PB_BARS, len(H))):
            if H[t] > H[b]:
                break
            if L[t] <= lvl:
                out.append((t, L[a], H[b], b))
                break
    return out


# ── the run ──────────────────────────────────────────────────────────────────

def load_all(arch, sub_dir):
    rows = {f: load(os.path.join(arch, name), sha_) for f, (name, sha_) in FILES.items()}
    bars, atr, trend = era_bars(rows["D"]["USED"], rows["H4"]["USED"])
    mid, ba, hashes = I.load_sub(sub_dir)
    return rows, bars, atr, trend, mid, ba, hashes


def spread_tables(ba):
    yh = defaultdict(list)
    for t, s, _ in ba:
        tp = t.astimezone(PT)
        yh[(tp.year, tp.hour)].append(s)
    med = {k: statistics.median(v) for k, v in yh.items() if v}
    p90 = {k: I.q(v, .9) for k, v in yh.items() if v}
    return med, p90


def build_setups(kind, rows, bars, atr):
    """4-hour (G1) or daily (side result) structure breaks with a daily ATR."""
    if kind == "H4":
        ts, H, L, C, atr_ = bars["opens"], bars["H"], bars["L"], bars["C"], atr
    else:
        d = rows["D"]["USED"]
        ts = [datetime.fromisoformat(x[0]) for x in d]
        H, L, C = [x[2] for x in d], [x[3] for x in d], [x[4] for x in d]
        d1 = {t: (x[1], x[2], x[3], x[4]) for t, x in zip(ts, d)}
        atr_, _ = FP.bar_context(ts, FP.session_table(d1))
    out, dropped = [], 0
    for j, side, dist in I.breaks_and_stops(H, L, C):
        if atr_[j] is None:
            dropped += 1
            continue
        t0 = ts[j] + SPAN[kind]
        out.append({"t0": t0, "side": side, "px": C[j], "stop": C[j] - side * dist, "dist": dist,
                    "atr": atr_[j], "vol": tercile(100 * atr_[j] / C[j], VOL_CUTS),
                    "volusd": tercile(atr_[j], USD_CUTS), "year": t0.astimezone(PT).year,
                    "sess": WF.session_day(t0)})
    return out, dropped


def ltf_index(mid):
    tfs, stops = {}, {}
    for g in LTF:
        ts = mid[g]["t"]
        by_side = {1: [], -1: []}
        for j, side, d, conf in WF.breaks_with_levels(mid[g]["H"], mid[g]["L"], mid[g]["C"]):
            by_side[side].append((j, conf))
            stops[(g, side, j)] = d
        for s in by_side:
            by_side[s].sort()
        tfs[g] = (ts, SPAN[g], by_side)
    return tfs, stops


def entries_for(setups, base, mid, tfs, stops, path, m5tuple, h4_close):
    """Attach the four entries to each setup (§4.2). Wait is in 4-hour bars of trading time."""
    for s in setups:
        s["entries"] = {base: {"t": s["t0"], "px": s["px"], "stop": s["stop"], "dist": s["dist"], "wait": 0}}
        s["missed"] = {}
        deadline = WF.session_close(s["t0"], MAX_SESSIONS)
        for g in LTF:
            t, res = WF.first_entry(s["t0"], s["side"], s["stop"], tfs[g], m5tuple, deadline)
            if t is None:
                s["missed"][g] = res
                continue
            d = stops[(g, s["side"], res)]
            px = mid[g]["C"][res]
            wait = bisect.bisect_left(h4_close, t) - bisect.bisect_left(h4_close, s["t0"])
            s["entries"][g] = {"t": t, "px": px, "stop": px - s["side"] * d, "dist": d, "wait": wait}
        s["worked"] = worked(path, s["side"], s["t0"], s["px"], s["stop"],
                             s["px"] + s["side"] * WORK_ATR * s["atr"], deadline)


def trades_for(setups, path):
    for s in setups:
        s["trades"] = {}
        for e, en in s["entries"].items():
            for h in HOLDS:
                ex = WF.session_close(s["t0"], h)
                if en["t"] >= ex:
                    continue                                  # the entry would come after the exit: missed
                tr = simulate(path, s["side"], en["t"], en["px"], en["stop"], ex)
                if tr is None:
                    continue
                if tr["stopped"]:
                    tr["after"] = run_after(path, s["side"], en["px"], en["dist"], tr["stop_k"],
                                            WF.session_close(s["t0"], MAX_SESSIONS))
                s["trades"][(e, h)] = tr


def counts(arch, sub_dir, fred):
    rows, bars, atr, trend, mid, ba, hashes = load_all(arch, sub_dir)
    WF.rates(fred)
    print(f"# GLS-1 counts stage. {STAMP}\n")
    print("data sha256: " + "; ".join(f"{k} {v}" for k, v in sorted(hashes.items())))
    path = Path(mid["M5"]["t"], mid["M5"]["O"], mid["M5"]["H"], mid["M5"]["L"], mid["M5"]["C"])
    m5t = (mid["M5"]["t"], mid["M5"]["L"], mid["M5"]["H"])
    tfs, stops = ltf_index(mid)
    h4c = [t + SPAN["H4"] for t in bars["opens"]]
    for kind, base in (("H4", "H4"), ("D", "D")):
        setups, dropped = build_setups(kind, rows, bars, atr)
        setups = [s for s in setups if s["t0"] >= mid["M5"]["t"][0]]
        for s in setups:
            s["entries"], s["missed"] = {}, {}
            deadline = WF.session_close(s["t0"], MAX_SESSIONS)
            for g in LTF:
                t, res = WF.first_entry(s["t0"], s["side"], s["stop"], tfs[g], m5t, deadline)
                if t is None:
                    s["missed"][g] = res
                else:
                    s["entries"][g] = bisect.bisect_left(h4c, t) - bisect.bisect_left(h4c, s["t0"])
        lab = "4-hour setups (G1)" if kind == "H4" else "daily setups (side result)"
        print(f"\n## {lab}: {len(setups)} (long {sum(s['side'] == 1 for s in setups)}, "
              f"short {sum(s['side'] == -1 for s in setups)}); dropped in daily-ATR warm-up {dropped}")
        print("- volatility tercile (ATR / price): " + str(dict(Counter((s['vol'], s['side']) for s in setups))))
        print("- volatility tercile (ATR in $):   " + str(dict(Counter((s['volusd'], s['side']) for s in setups))))
        for g in LTF:
            w = [s["entries"][g] for s in setups if g in s["entries"]]
            miss = Counter(s["missed"][g] for s in setups if g in s["missed"])
            print(f"- {g}: entered within 10 sessions {len(w)}; missed {dict(miss)}; "
                  f"wait buckets {dict(Counter(bucket(x) for x in w))}; within 1 session {sum(x <= ONE_SESSION for x in w)}")
    print("\n## catalogue occurrences (completions), per timeframe")
    for g in LTF:
        occ = structures(mid[g])
        print(f"- {g} ({len(mid[g]['C'])} bars): " + "; ".join(
            f"{k} {'up' if s == 1 else 'down'} {len(v)}" for (k, s), v in sorted(occ.items())))
    hs, ls = I.swings(bars["H"], bars["L"])
    print(f"\n## 4-hour swing points: highs {len(hs)}, lows {len(ls)} (swing starts and failed swings are outcomes; "
          f"not split here)")
    print("\n## pullback legs reaching each level (outcomes not computed)")
    for lvl in LEVELS:
        r48, sw = 0, 0
        for side in (1, -1):
            O, H, L, tr = side_arrays(bars, trend, side)
            en, _ = FP.find_entries(O, H, L, atr, tr, lvl, use_trend=False)
            r48 += len(en)
            sw += len(swing_legs(H, L, atr, lvl))
        print(f"- {lvl:.1%}: R48 legs {r48}; 4-hour swing legs {sw}")


def full(arch, sub_dir, fred):
    rng = np.random.default_rng(SEED)
    rows, bars, atr, trend, mid, ba, hashes = load_all(arch, sub_dir)
    rt = WF.rates(fred)
    sp_med, sp_p90 = spread_tables(ba)
    path = Path(mid["M5"]["t"], mid["M5"]["O"], mid["M5"]["H"], mid["M5"]["L"], mid["M5"]["C"])
    m5t = (mid["M5"]["t"], mid["M5"]["L"], mid["M5"]["H"])
    tfs, stops = ltf_index(mid)
    h4o = bars["opens"]
    h4c = [t + SPAN["H4"] for t in h4o]
    print(f"# GLS-1 full run. {STAMP}\n")
    print("data sha256: " + "; ".join(f"{k} {v}" for k, v in sorted(hashes.items())))
    pops = {}
    for kind in ("H4", "D"):
        setups, _ = build_setups(kind, rows, bars, atr)
        setups = [s for s in setups if s["t0"] >= mid["M5"]["t"][0]]
        entries_for(setups, kind, mid, tfs, stops, path, m5t, h4c)
        trades_for(setups, path)
        pops[kind] = setups

    print("\n" + "=" * 78 + "\n# PART A: venue-independent (no costs)\n" + "=" * 78)
    for kind in ("H4", "D"):
        part_a_entries(pops[kind], kind, rng)
    part_a_catalogue(mid, bars, atr, path, rng)
    part_a_pullbacks(bars, atr, trend, mid)

    print("\n" + "=" * 78 + "\n# PART B: the four entries under two cost structures (§4.5)\n" + "=" * 78)
    part_b(pops["H4"], rt, sp_med, sp_p90, rng)
    part_b_catalogue_costs(mid, bars, atr, path, sp_med, rt, rng)


ENTRY_NAMES = {"H4": "4-hour", "D": "daily", "M30": "30-minute", "M15": "15-minute", "M5": "5-minute"}


def part_a_entries(setups, base, rng):
    lab = "4-hour setups (G1; headline)" if base == "H4" else "daily setups (side result, no verdict)"
    order = (base,) + LTF
    print(f"\n## §4 {lab}: {len(setups)} setups")
    for side in (1, -1):
        S = [s for s in setups if s["side"] == side]
        W = [s for s in S if s["worked"]]
        sn = "long" if side == 1 else "short"
        print(f"\n### {sn}: {len(S)} setups; {HINDSIGHT}: {len(W)} worked")
        for e in order:
            got = sum(e in s["entries"] for s in S)
            miss = Counter(s["missed"].get(e) for s in S if e not in s["entries"])
            print(f"- {ENTRY_NAMES[e]}: entered {got}; missed {dict(miss)}")
        print("\n#### R before costs, per trade (all setups)")
        for h in HOLDS:
            for e in order:
                tr = [(s["trades"][(e, h)], s) for s in S if (e, h) in s["trades"]]
                print(f"- +{h} {ENTRY_NAMES[e]}: {summ([t['r'] for t, _ in tr], [s['sess'] for _, s in tr], rng)}; "
                      f"stopped {sum(t['stopped'] for t, _ in tr)}")
        print("\n#### R before costs, per setup (a missed entry counts 0R), and paired difference from the "
              f"{ENTRY_NAMES[base]} entry")
        for h in HOLDS:
            for e in order:
                v = [s["trades"][(e, h)]["r"] if (e, h) in s["trades"] else 0.0 for s in S]
                line = f"- +{h} {ENTRY_NAMES[e]}: {summ(v, [s['sess'] for s in S], rng)}"
                if e != base:
                    both = [s for s in S if (e, h) in s["trades"] and (base, h) in s["trades"]]
                    dv = [s["trades"][(e, h)]["r"] - s["trades"][(base, h)]["r"] for s in both]
                    lo, hi = boot_ci(dv, [s["sess"] for s in both], rng)
                    line += (f" | paired vs {ENTRY_NAMES[base]} (both traded, n {len(both)}): "
                             f"{np.mean(dv) if dv else float('nan'):+.3f} [{lo:+.3f}, {hi:+.3f}]")
                print(line)
        print(f"\n#### The deciding number ({HINDSIGHT}): worked setups whose entry was stopped before the exit")
        for h in HOLDS:
            for e in order:
                tr = [s["trades"][(e, h)] for s in W if (e, h) in s["trades"]]
                st = [t for t in tr if t["stopped"]]
                after = [t["after"] for t in st]
                print(f"- +{h} {ENTRY_NAMES[e]}: stopped {share(len(st), len(tr))}; "
                      f"after the stop the move ran (R of the stop hit) {quarts(after)}")
        print(f"\n#### Adverse excursion to the exit ({HINDSIGHT}, worked setups): dollars; daily ATR")
        for h in HOLDS:
            for e in order:
                tr = [(s["trades"][(e, h)], s) for s in W if (e, h) in s["trades"]]
                print(f"- +{h} {ENTRY_NAMES[e]}: ${quarts(t['mae'] for t, _ in tr)} | "
                      f"{quarts((t['mae'] / s['atr'] for t, s in tr), '{:.3f}')}")
        print("\n#### Stop sizes (all entries taken): dollars; daily ATR; share under 0.3 daily ATR")
        for e in order:
            ds = [(s["entries"][e]["dist"], s["atr"]) for s in S if e in s["entries"]]
            under = sum(d < MIN_STOP_ATR * a for d, a in ds)
            print(f"- {ENTRY_NAMES[e]}: ${quarts(d for d, _ in ds)} | {quarts((d / a for d, a in ds), '{:.3f}')} | "
                  f"under 0.3 ATR {share(under, len(ds))}")
        print("\n#### Hindsight ratio (F2): share of trades with R before costs > 0, worked setups / all setups")
        for h in HOLDS:
            cells = []
            for e in order:
                a_ = [s["trades"][(e, h)]["r"] > 0 for s in S if (e, h) in s["trades"]]
                w_ = [s["trades"][(e, h)]["r"] > 0 for s in W if (e, h) in s["trades"]]
                if a_ and w_ and sum(a_):
                    cells.append(f"{ENTRY_NAMES[e]} {100 * np.mean(w_):.1f}% / {100 * np.mean(a_):.1f}% = "
                                 f"{np.mean(w_) / np.mean(a_):.2f}")
            print(f"- +{h}: " + "; ".join(cells))
        print("\n#### By wait bucket (4-hour bars), R before costs per trade")
        for h in HOLDS:
            for e in LTF:
                by = defaultdict(list)
                for s in S:
                    if (e, h) in s["trades"]:
                        by[bucket(s["entries"][e]["wait"])].append(s["trades"][(e, h)]["r"])
                print(f"- +{h} {ENTRY_NAMES[e]}: " + "; ".join(
                    f"{b} n {len(by[b])} mean {np.mean(by[b]):+.3f}" for b in
                    [bucket(lo) for lo, _ in BUCKETS] if by[b]))
        print("\n#### Secondary: the 1-session cut (waits of 6 bars or fewer), R before costs per setup (missed 0R)")
        for h in HOLDS:
            for e in LTF:
                v = [s["trades"][(e, h)]["r"] if (e, h) in s["trades"] and s["entries"][e]["wait"] <= ONE_SESSION
                     else 0.0 for s in S]
                print(f"- +{h} {ENTRY_NAMES[e]}: {summ(v, [s['sess'] for s in S], rng)}")
        print("\n#### Volatility split (H3; daily ATR / price at the setup): R before costs per setup (missed 0R); "
              "deciding number")
        for key, lab2 in (("vol", "ATR / price (primary)"), ("volusd", "ATR in dollars (secondary)")):
            print(f"- {lab2}")
            for t in ("low", "mid", "high"):
                St = [s for s in S if s[key] == t]
                for h in (1, 5):
                    for e in order:
                        v = [s["trades"][(e, h)]["r"] if (e, h) in s["trades"] else 0.0 for s in St]
                        tw = [s["trades"][(e, h)] for s in St if s["worked"] and (e, h) in s["trades"]]
                        print(f"    {t} +{h} {ENTRY_NAMES[e]}: {summ(v, [s['sess'] for s in St], rng)} | "
                              f"worked stopped {share(sum(x['stopped'] for x in tw), len(tw))}")


def session_close_prices(path):
    """{session day: price at its 17:00 New York close}."""
    out = {}
    for k, t in enumerate(path.ts):
        out[WF.session_day(t + path.span - timedelta(seconds=1))] = float(path.C[k])
    return out


def resolution_moves(ts, span, C, idx, side, scp, h4o, atr):
    """§5.3 item 3: signed move from each completion close to the session close +h, in daily ATR.
    Returns {h: (moves, sessions, atrs, completion times)}."""
    out = {h: ([], [], [], []) for h in HOLDS}
    for i in idx:
        tc = ts[i] + span
        k = bisect.bisect_right(h4o, ts[i]) - 1
        if k < 0 or atr[k] is None:
            continue
        d0 = WF.session_day(tc)
        for h in HOLDS:
            px = scp.get(nth_session_day(d0, h))
            if px is None:
                continue
            o = out[h]
            o[0].append(side * (px - C[i]) / atr[k])
            o[1].append(d0)
            o[2].append(atr[k])
            o[3].append(tc)
    return out


def part_a_catalogue(mid, bars, atr, path, rng):
    print(f"\n## §5 catalogue. {STAMP}")
    h4o, H4, L4 = bars["opens"], bars["H"], bars["L"]
    scp = session_close_prices(path)
    starts = {1: [], -1: []}
    failed = {1: [], -1: []}
    for side in (1, -1):
        Hx, Lx = (H4, L4) if side == 1 else ([-x for x in L4], [-x for x in H4])
        _, ls = I.swings(Hx, Lx)
        for s in ls:
            if atr[s] is None:
                continue
            tgt, ok = Lx[s] + atr[s], None
            for k in range(s + 1, min(s + 1 + SWING_RUN_BARS, len(Hx))):
                if Lx[k] < Lx[s]:
                    ok = False
                    break
                if Hx[k] >= tgt:
                    ok = True
                    break
            (starts if ok else failed)[side].append(h4o[s])
    print(f"4-hour swing starts ({HINDSIGHT}): up {len(starts[1])}, down {len(starts[-1])}; "
          f"failed swings: up {len(failed[1])}, down {len(failed[-1])}; base windows {len(h4o)}")
    for g in LTF:
        arr = mid[g]
        ts, C = arr["t"], np.asarray(arr["C"], float)
        occ = structures(arr)
        nb = len(C)
        print(f"\n### {g}: {nb} bars")
        base_v = {h: {} for h in HOLDS}
        all_idx = range(nb)
        up = resolution_moves(ts, SPAN[g], C, all_idx, 1, scp, h4o, atr)
        for h in HOLDS:
            base_v[h][1] = up[h]
            base_v[h][-1] = ([-x for x in up[h][0]],) + tuple(up[h][1:])   # the same moves, other direction
        for (name, side), idx in sorted(occ.items()):
            sn = "up" if side == 1 else "down"
            ct_sorted = sorted(ts[i] for i in idx)

            def contains(t_open):
                a = bisect.bisect_left(ct_sorted, t_open)
                return a < len(ct_sorted) and ct_sorted[a] < t_open + timedelta(hours=8)
            sw = [contains(t) for t in starts[side]]
            fw = [contains(t) for t in failed[side]]
            bw = [contains(t) for t in h4o]
            lo_b, hi_b = wilson(sum(bw), len(bw))
            ps = sum(sw) / len(sw) if sw else float("nan")
            flag = "OUTSIDE the base interval" if sw and (ps < lo_b or ps > hi_b) else "inside the base interval"
            print(f"- {name} {sn}: {len(idx)} ({1000 * len(idx) / nb:.1f} per 1,000 bars) | windows with one: "
                  f"swing starts ({HINDSIGHT}) {share(sum(sw), len(sw))}; failed ({HINDSIGHT}) "
                  f"{share(sum(fw), len(fw))}; base {share(sum(bw), len(bw))} -> {flag}")
            res = resolution_moves(ts, SPAN[g], C, idx, side, scp, h4o, atr)
            for h in HOLDS:
                mv, ss, _, _ = res[h]
                bv, bs, _, _ = base_v[h][side]
                print(f"    +{h}: {summ(mv, ss, rng)} | drift baseline mean {np.mean(bv):+.3f} (n {len(bv)}); "
                      f"minus baseline {np.mean(mv) - np.mean(bv) if mv else float('nan'):+.3f}")


def part_a_pullbacks(bars, atr, trend, mid):
    print(f"\n## §6 pullback continuation versus reversal. {STAMP} Not a classifier.")
    m15 = sorted((mid["M15"]["t"][j] + SPAN["M15"], side)
                 for j, side, _ in I.breaks_and_stops(mid["M15"]["H"], mid["M15"]["L"], mid["M15"]["C"]))
    m15_t = [t for t, _ in m15]
    h4o = bars["opens"]
    for pop in ("R48 legs", "4-hour swing legs"):
        print(f"\n### {pop}")
        for lvl in LEVELS:
            rows_ = []
            for side in (1, -1):
                O, H, L, tr = side_arrays(bars, trend, side)
                if pop == "R48 legs":
                    en, _ = FP.find_entries(O, H, L, atr, tr, lvl, use_trend=False)
                    legs = []
                    for e in en:
                        a, t = e["anchor_bar"], e["bar"]
                        seg = range(a + 1, t) if t > a + 1 else range(a + 1, t + 1)
                        b = max(seg, key=lambda x: (H[x], -x))
                        legs.append((t, e["A"], e["B"], b))
                else:
                    legs = swing_legs(H, L, atr, lvl)
                for t, A, B_, b in legs:
                    out = pullback_outcome(H, L, A, B_, t)
                    k = bisect.bisect_left(m15_t, h4o[t]) - 1
                    ltf = None if k < 0 or m15_t[k] < mid["M15"]["t"][0] else ("with" if m15[k][1] == side else "against")
                    rows_.append({"out": out, "speed": t - b, "ltf": ltf, "side": side})
            res = [r for r in rows_ if r["out"] != "unresolved"]
            cont = sum(r["out"] == "continued" for r in res)
            oc = Counter(r["out"] for r in rows_)
            print(f"- {lvl:.1%}: legs {len(rows_)} ({dict(oc)}); continued among resolved {share(cont, len(res))}"
                  + (" INSUFFICIENT (fewer than 20 resolved)" if len(res) < 20 else ""))
            if len(res) >= 2:
                med = statistics.median(r["speed"] for r in res)
                for lab, f in (("speed: fast (<= median %g bars) vs slow" % med, lambda r: r["speed"] <= med),
                               ("15-minute structure: with vs against", lambda r: r["ltf"] == "with")):
                    pool = res if lab.startswith("speed") else [r for r in res if r["ltf"] is not None]
                    a_ = [r for r in pool if f(r)]
                    b_ = [r for r in pool if not f(r)]
                    ca, cb = sum(r["out"] == "continued" for r in a_), sum(r["out"] == "continued" for r in b_)
                    if len(a_) < 20 or len(b_) < 20:
                        print(f"    {lab}: {share(ca, len(a_))} vs {share(cb, len(b_))} -> INSUFFICIENT (a side has "
                              f"fewer than 20)")
                        continue
                    d, lo, hi = newcombe(ca, len(a_), cb, len(b_))
                    verdict = "separates" if lo > 0 or hi < 0 else "does not separate"
                    print(f"    {lab}: {share(ca, len(a_))} vs {share(cb, len(b_))}; difference {100 * d:+.1f} "
                          f"[{100 * lo:+.1f}, {100 * hi:+.1f}] -> {verdict}")


STRUCTS = ("CFD primary (both pay)", "CFD stress (hour p90 spread)", "CFD side: shorts receive",
           "futures primary (basis carry)", "futures side: no carry")


def costs_for(s, e, tr, rt, sp_med, sp_p90):
    en = s["entries"][e]
    r = WF.rate_on(rt, en["t"].astimezone(NY).date())
    se, sx = spread_at(sp_med, en["t"]), spread_at(sp_med, tr["exit_t"])
    pe, px = spread_at(sp_p90, en["t"]), spread_at(sp_p90, tr["exit_t"])
    if None in (se, sx, pe, px):
        return None
    side, t1, P = s["side"], tr["exit_t"], en["px"]
    return {
        STRUCTS[0]: cfd_cost(side, en["t"], t1, P, r, se, sx),
        STRUCTS[1]: cfd_cost(side, en["t"], t1, P, r, pe, px),
        STRUCTS[2]: cfd_cost(side, en["t"], t1, P, r, se, sx, short_receives=True),
        STRUCTS[3]: futures_cost(side, en["t"], t1, P, r, carry=True),
        STRUCTS[4]: futures_cost(side, en["t"], t1, P, r, carry=False),
        "financing": cfd_cost(side, en["t"], t1, P, r, 0.0, 0.0),
    }


def per_setup(S, e, h, struct, net):
    """Net R per setup; a missed entry counts 0R."""
    return [net[(id(s), e, h)][struct] if (id(s), e, h) in net else 0.0 for s in S]


def part_b(setups, rt, sp_med, sp_p90, rng):
    order = ("H4",) + LTF
    net, costed_out = {}, 0
    for s in setups:
        for (e, h), tr in s["trades"].items():
            c = costs_for(s, e, tr, rt, sp_med, sp_p90)
            if c is None:
                costed_out += 1
                continue
            d = s["entries"][e]["dist"]
            net[(id(s), e, h)] = {k: tr["r"] - v / d for k, v in c.items() if k != "financing"}
            net[(id(s), e, h)]["usd"] = tr["r"] * d
            net[(id(s), e, h)]["fin_share"] = c["financing"] / d
            net[(id(s), e, h)]["usd_net_cfd"] = tr["r"] * d - c[STRUCTS[0]]
            net[(id(s), e, h)]["usd_net_fut"] = tr["r"] * d - c[STRUCTS[3]]
            net[(id(s), e, h)]["atr_net_cfd"] = (tr["r"] * d - c[STRUCTS[0]]) / s["atr"]
    print(f"\n## §4.5 part B, 4-hour setups. Every cost is a labelled placeholder except the measured spread. "
          f"Trades without a spread quote: {costed_out}")
    for side in (1, -1):
        S = [s for s in setups if s["side"] == side]
        sn = "long" if side == 1 else "short"
        print(f"\n### {sn}: {len(S)} setups")
        for struct in STRUCTS:
            print(f"\n#### {struct}: net R per setup (missed 0R); paired vs 4-hour")
            for h in HOLDS:
                for e in order:
                    v = per_setup(S, e, h, struct, net)
                    line = f"- +{h} {ENTRY_NAMES[e]}: {summ(v, [s['sess'] for s in S], rng)}"
                    if e != "H4":
                        both = [s for s in S if (id(s), e, h) in net and (id(s), "H4", h) in net]
                        dv = [net[(id(s), e, h)][struct] - net[(id(s), "H4", h)][struct] for s in both]
                        lo, hi = boot_ci(dv, [s["sess"] for s in both], rng)
                        line += f" | paired {np.mean(dv) if dv else float('nan'):+.3f} [{lo:+.3f}, {hi:+.3f}]"
                    print(line)
        print("\n#### Position-size-free: net dollars an ounce per trade (CFD primary; futures primary); "
              "net daily ATR (CFD primary)")
        for h in HOLDS:
            for e in order:
                ks = [(id(s), e, h) for s in S if (id(s), e, h) in net]
                cl = [s["sess"] for s in S if (id(s), e, h) in net]
                print(f"- +{h} {ENTRY_NAMES[e]}: CFD ${summ([net[k]['usd_net_cfd'] for k in ks], cl, rng)} | "
                      f"futures ${summ([net[k]['usd_net_fut'] for k in ks], cl, rng)} | "
                      f"CFD ATR {summ([net[k]['atr_net_cfd'] for k in ks], cl, rng)}")
        print("\n#### Financing as a share of risk (G4; CFD, both pay), median by year")
        for h in HOLDS:
            for e in order:
                by = defaultdict(list)
                for s in S:
                    if (id(s), e, h) in net:
                        by[s["year"]].append(net[(id(s), e, h)]["fin_share"])
                print(f"- +{h} {ENTRY_NAMES[e]}: " + "; ".join(f"{y} {np.median(v):+.3f}R (n {len(v)})"
                                                            for y, v in sorted(by.items())))
        print("\n#### Volatility split (H3, required): net R per setup (missed 0R), CFD primary and futures primary")
        for t in ("low", "mid", "high"):
            St = [s for s in S if s["vol"] == t]
            for h in HOLDS:
                for e in order:
                    print(f"    {t} +{h} {ENTRY_NAMES[e]}: CFD {summ(per_setup(St, e, h, STRUCTS[0], net), [s['sess'] for s in St], rng)} | "
                          f"futures {summ(per_setup(St, e, h, STRUCTS[3], net), [s['sess'] for s in St], rng)}")
        print("\n#### Ranking flip (J2): entries ranked by mean net R per setup, CFD primary vs futures primary")
        for h in HOLDS:
            means = {st: {e: float(np.mean(per_setup(S, e, h, st, net))) for e in order} for st in (STRUCTS[0], STRUCTS[3])}
            rk = {st: sorted(order, key=lambda e: -means[st][e]) for st in means}
            flip = rk[STRUCTS[0]] != rk[STRUCTS[3]]
            line = (f"- +{h}: CFD {' > '.join(ENTRY_NAMES[e] for e in rk[STRUCTS[0]])}; futures "
                    f"{' > '.join(ENTRY_NAMES[e] for e in rk[STRUCTS[3]])} -> {'FLIP' if flip else 'same order'}")
            if flip:
                notes = []
                for i_, x in enumerate(order):
                    for y in order[i_ + 1:]:
                        if (rk[STRUCTS[0]].index(x) < rk[STRUCTS[0]].index(y)) != (rk[STRUCTS[3]].index(x) < rk[STRUCTS[3]].index(y)):
                            sig = []
                            for st in (STRUCTS[0], STRUCTS[3]):
                                dv = [a - b for a, b in zip(per_setup(S, x, h, st, net), per_setup(S, y, h, st, net))]
                                lo, hi = boot_ci(dv, [s["sess"] for s in S], rng)
                                sig.append(lo > 0 or hi < 0)
                            notes.append(f"{ENTRY_NAMES[x]} vs {ENTRY_NAMES[y]}: "
                                         f"{'a finding' if all(sig) else 'within noise'}")
                line += " (" + "; ".join(notes) + ")"
            print(line)
        if side == -1:
            print("\n#### H2 flags: short cells positive only with a carry credit")
            for h in HOLDS:
                for e in order:
                    fp = np.mean(per_setup(S, e, h, STRUCTS[3], net))
                    fn = np.mean(per_setup(S, e, h, STRUCTS[4], net))
                    cr = np.mean(per_setup(S, e, h, STRUCTS[2], net))
                    cp = np.mean(per_setup(S, e, h, STRUCTS[0], net))
                    flags = []
                    if cr > 0 >= cp:
                        flags.append("CFD: positive only if shorts receive -> both-pay stands (H2)")
                    if fp > 0 >= fn:
                        flags.append("futures: positive only with the placeholder carry credit")
                    if flags:
                        print(f"- +{h} {ENTRY_NAMES[e]}: " + "; ".join(flags))
            print("- (no line above = no flagged cell)")


def part_b_catalogue_costs(mid, bars, atr, path, sp_med, rt, rng):
    print("\n## §5.3 catalogue net of costs (mean move in daily ATR minus round-trip cost in daily ATR; "
          "CFD = measured spread only, futures = tick + commissions; no financing or carry)")
    h4o = bars["opens"]
    scp = session_close_prices(path)
    for g in LTF:
        arr = mid[g]
        ts, C = arr["t"], np.asarray(arr["C"], float)
        for (name, side), idx in sorted(structures(arr).items()):
            res = resolution_moves(ts, SPAN[g], C, idx, side, scp, h4o, atr)
            cells = []
            for h in HOLDS:
                mv, _, at, tcs = res[h]
                if not mv:
                    continue
                cfd = [((spread_at(sp_med, t) or 0.0)) / a for t, a in zip(tcs, at)]
                fut = [(TICK + 2 * COMM) / a for a in at]
                cells.append(f"+{h} CFD {np.mean(mv) - np.mean(cfd):+.3f} futures {np.mean(mv) - np.mean(fut):+.3f}")
            print(f"- {g} {name} {'up' if side == 1 else 'down'}: " + "; ".join(cells))


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode not in ("counts", "full"):
        raise SystemExit("mode must be counts or full")
    (counts if mode == "counts" else full)(sys.argv[2], sys.argv[3], sys.argv[4])
