"""
gold_levels.py
──────────────
The qualifying levels behind the gold BRIEFING, ARRIVAL and LEVEL BREAK
alerts (docs/specs/configuration_detector_spec.md §13.1, §13.2, §14.2, and
the touch and hold rulings R1-R3 of §14.1).

Ported line for line from studies/ccd1_prototype.py (swings and the §4
range) and studies/ccd1_arrival_calibration.py (the level sets, the simple
ATR, the live session index), because the live path never imports
studies/. tests/test_gold_levels.py runs both on the same bars and requires
identical output; any change here that the studies do not share fails it.

Pure functions over bar dicts {"t": [aware datetimes], "H", "L", "C": [floats]}
keyed "D", "H4", "H1". Nothing here fetches, writes or renders.
"""
from __future__ import annotations

import bisect
import statistics
from datetime import timedelta
from zoneinfo import ZoneInfo

from regime_detection import compute_atr_series

NY = ZoneInfo("America/New_York")

# ── frozen thresholds (spec §2, §4, §13) ─────────────────────────────────────
K = 3                    # swing: 3 bars each side (§2)
RUN_MIN, RUN_MAX = 12, 120      # range length in hourly bars (§4)
W_MIN, W_MAX = 0.30, 1.20       # range width in daily ATR (§4)
D1_WIN, H4_WIN = 220, 120       # swing windows (§13.1)
TOL = 0.10               # arrival tolerance and visit band, simple ATR (ruling M3)
REARM = 0.50             # re-arm distance (§13.3)
BREAK_MARGIN = 0.10      # a close this far beyond breaks (§17, ruling Q1; R2)

KINDS_ALL = ("D1", "H4", "RANGE", "PDAY", "PWEEK")


def series(df):
    """An oanda_feed DataFrame as a bar dict."""
    return {"t": [x.to_pydatetime() for x in df.index], "H": [float(v) for v in df["High"]],
            "L": [float(v) for v in df["Low"]], "C": [float(v) for v in df["Close"]]}


# ── swings and the range (ccd1_prototype) ────────────────────────────────────

def pivots(H, L):
    """Indices of swing highs and lows by the 3-each-side rule, ties counting."""
    n = len(H)
    ph = [i for i in range(K, n - K) if H[i] == max(H[i - K:i + K + 1])]
    pl = [i for i in range(K, n - K) if L[i] == min(L[i - K:i + K + 1])]
    return ph, pl


def confirm_index(H, L, C, ph, pl):
    """{pivot index: first later bar whose close confirms it}, absent if never."""
    ch, cl = {}, {}
    n = len(C)
    for i in ph:
        for j in range(i + 1, n):
            if C[j] < H[i]:
                ch[i] = j
                break
    for i in pl:
        for j in range(i + 1, n):
            if C[j] > L[i]:
                cl[i] = j
                break
    return ch, cl


def find_range(H, L, C, e, atr, ph_set, pl_set, ch, cl):
    """The longest run ending at bar e that meets §4, or None. Swings count
    only if confirmed by a close at or before e and have 3 bars after them
    inside [.., e]."""
    best = None
    rh = rl = None
    nh = nl = 0
    first = None
    cmin, cmax = float("inf"), float("-inf")
    for s in range(e, max(e - RUN_MAX, -1), -1):
        cmin, cmax = min(cmin, C[s]), max(cmax, C[s])
        if s in ph_set and s + K <= e and ch.get(s, e + 1) <= e:
            nh += 1
            rh = H[s] if rh is None else max(rh, H[s])
            first = s
        if s in pl_set and s + K <= e and cl.get(s, e + 1) <= e:
            nl += 1
            rl = L[s] if rl is None else min(rl, L[s])
            first = s
        length = e - s + 1
        if length < RUN_MIN or nh < 2 or nl < 2:
            continue
        if not (rl <= cmin and cmax <= rh):
            continue
        width = (rh - rl) / atr
        if W_MIN <= width <= W_MAX:
            best = {"s": s, "e": e, "first_swing": first, "high": rh, "low": rl, "width_atr": width, "nh": nh, "nl": nl}
    return best


# ── sessions, weeks, swing tables (ccd1_arrival_calibration) ─────────────────

def session_index(d1_times, tt):
    """Index of the daily bar whose 24-hour span holds tt. A live feed leaves
    out the session in progress, so an hour past the last bar's span belongs
    to a session not in the list yet: its index is len(d1_times), and every
    bar in the list is then complete (§13.1 live note)."""
    k = bisect.bisect_right(d1_times, tt) - 1
    if k == len(d1_times) - 1 and tt >= d1_times[-1] + timedelta(hours=24):
        return len(d1_times)
    return k


def trading_week(t):
    d = (t.astimezone(NY) + timedelta(hours=7)).date()
    return d.isocalendar()[:2]


class _Table(list):
    pass


def swing_table(s):
    """Per confirmed swing: (pivot i, price, kind, confirm j, broken b)."""
    H, L, C = s["H"], s["L"], s["C"]
    ph, pl = pivots(H, L)
    ch, cl = confirm_index(H, L, C, ph, pl)
    n = len(C)
    out = []
    for i in ph:
        if i in ch:
            b = next((j for j in range(i + 1, n) if C[j] > H[i]), n)
            out.append((i, H[i], "high", max(ch[i], i + K), b))
    for i in pl:
        if i in cl:
            b = next((j for j in range(i + 1, n) if C[j] < L[i]), n)
            out.append((i, L[i], "low", max(cl[i], i + K), b))
    out.sort()
    tab = _Table(out)
    tab.keys = [r[0] for r in out]
    return tab


def active(table, last, win):
    """Swings usable when bars 0..last are complete: confirmed by then, not
    broken by then, pivot within the last `win` bars."""
    lo = bisect.bisect_left(table.keys, last - win + 1)
    hi = bisect.bisect_right(table.keys, last)
    return [(i, p, k) for i, p, k, j, b in table[lo:hi] if j <= last and b > last]


# ── the level sets (§13.1) ───────────────────────────────────────────────────

def _context(s):
    d1 = s["D"]
    trs = [None] + [max(d1["H"][i] - d1["L"][i], abs(d1["H"][i] - d1["C"][i - 1]), abs(d1["L"][i] - d1["C"][i - 1]))
                    for i in range(1, len(d1["C"]))]
    return {"d_tab": swing_table(d1), "h4_tab": swing_table(s["H4"]), "trs": trs,
            "wk": [trading_week(t) for t in d1["t"]],
            "watr": compute_atr_series(d1["H"], d1["L"], d1["C"])}   # watr[m] uses bars 0..m+14


def _row(s, ctx, t, tt):
    """(simple ATR, [(kind, id, price)]) for the hour starting tt, which is
    hourly bar t (t == len(H1) for the hour in progress); None in warm-up."""
    d1, h4, h1 = s["D"], s["H4"], s["H1"]
    kd = session_index(d1["t"], tt)
    if kd < 15:
        return None
    atr = statistics.fmean(ctx["trs"][kd - 14:kd])          # simple 14-day ATR, completed days (§13.2)
    lv = []
    for i, p, k in active(ctx["d_tab"], kd - 1, D1_WIN):
        lv.append(("D1", f"D1{i}", p))
    j4 = bisect.bisect_right(h4["t"], tt - timedelta(hours=4)) - 1   # last 4-hour bar closed by this hour's open
    if j4 >= 0:
        for i, p, k in active(ctx["h4_tab"], j4, H4_WIN):
            lv.append(("H4", f"H4{i}", p))
    lv.append(("PDAY", f"PDH{kd - 1}", d1["H"][kd - 1]))
    lv.append(("PDAY", f"PDL{kd - 1}", d1["L"][kd - 1]))
    wk = ctx["wk"]
    cur_wk = wk[kd] if kd < len(wk) else trading_week(tt)   # live session not in the list
    pw = [i for i in range(max(0, kd - 12), kd) if wk[i] < cur_wk]
    if pw:
        last_wk = wk[pw[-1]]
        idx = [i for i in pw if wk[i] == last_wk]
        lv.append(("PWEEK", f"PWH{last_wk}", max(d1["H"][i] for i in idx)))
        lv.append(("PWEEK", f"PWL{last_wk}", min(d1["L"][i] for i in idx)))
    # range boundaries by §4 on bars up to t-1 (Wilder ATR, as BREAK detection runs)
    if t - 1 - RUN_MAX - K >= 0:
        watr = ctx["watr"][kd - 1 - 14]
        lo = max(0, t - 1 - RUN_MAX - 10)
        H, L, C = h1["H"][lo:t], h1["L"][lo:t], h1["C"][lo:t]
        ph, pl = pivots(H, L)
        ch, cl = confirm_index(H, L, C, ph, pl)
        rng = find_range(H, L, C, len(C) - 1, watr, set(ph), set(pl), ch, cl)
        if rng:
            lv.append(("RANGE", f"RH{rng['high']:.5f}", rng["high"]))
            lv.append(("RANGE", f"RL{rng['low']:.5f}", rng["low"]))
    return atr, lv


def level_sets(s):
    """One row per hourly bar: the levels in force at that bar's open."""
    ctx = _context(s)
    return [_row(s, ctx, t, tt) for t, tt in enumerate(s["H1"]["t"])]


def levels_now(s, now):
    """The levels in force for the hour in progress at `now`, after the last
    complete hourly bar: the BRIEFING's read."""
    hour = now.replace(minute=0, second=0, microsecond=0)
    return _row(s, _context(s), len(s["H1"]["t"]), hour)


# ── touch and hold history (rulings R1-R3, §14.1) ────────────────────────────

def visit_history(s, sets, p, start, t, tol=TOL, margin=BREAK_MARGIN):
    """Visits to p on hourly bars from `start` to t-1. R1: a visit is one
    continuous stay of bars whose range overlaps p +/- tol x that hour's ATR.
    R2: it broke if any close in it went `margin` x ATR or more beyond p (the
    LEVEL BREAK rule); otherwise it held. R3: "beyond" is judged from the
    close before the visit's first bar, and nothing later changes it.
    Returns [(first bar, last bar, side, broke bar or None)]; side +1 means
    price approached from above."""
    h1 = s["H1"]
    C = h1["C"]
    out, cur = [], None
    for i in range(bisect.bisect_left(h1["t"], start), t):
        if sets[i] is None:
            cur = None
            continue
        atr = sets[i][0]
        if not (h1["L"][i] <= p + tol * atr and h1["H"][i] >= p - tol * atr):
            cur = None
            continue
        if cur is None:
            cur = [i, i, 1 if C[max(i - 1, 0)] >= p else -1, None]
            out.append(cur)
        cur[1] = i
        beyond = (p - C[i]) if cur[2] == 1 else (C[i] - p)
        if cur[3] is None and beyond > 0 and beyond >= margin * atr:
            cur[3] = i
    return [tuple(v) for v in out]
