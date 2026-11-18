"""ccd1_prototype.py — report-only prototype of the CCD-1 detector definition
(docs/specs/configuration_detector_spec.md, PROPOSED, commit bcc444a plus
amendment 1 of 2026-11-17, before any data run: every
threshold below is copied from that file and nothing here changes one).

Not the live module: the live `config_detector.py` is built only after the
owner signs the spec. This file exists to (1) run the §9 worked example once,
and (2) count the configuration on gold's STUDY and USED bars for Track B's B1
screen. Counts only: no outcome, no R, nothing after the event bar is read
except to space episodes.

usage:
  python3 ccd1_prototype.py example            # live OANDA bars, read-only (run via reality_run.py)
  python3 ccd1_prototype.py counts <archive>   # <archive> = ~/intel_study_archives/research_archive_legs
"""
import bisect, os, sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

W = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, W)
sys.path.insert(0, os.path.dirname(W))
sys.path.insert(0, os.path.join(os.path.dirname(W), "foundation", "tools"))
from regime_detection import _detect_structure, compute_atr_series

PT = ZoneInfo("America/Los_Angeles")

# ── frozen thresholds (spec §1-§6) ───────────────────────────────────────────
K = 3                    # swing: 3 bars each side (§2)
H4_WIN = 120             # 4-hour trend window (§3)
H1_WIN = 72              # hourly trend window, ending at the bar before the event (§3)
RUN_MIN, RUN_MAX = 12, 120      # range length in hourly bars (§4)
W_MIN, W_MAX = 0.30, 1.20       # range width in daily ATR (§4)
ZONE = 0.10              # touch zone in daily ATR (§5)
TOUCHES = 3              # required touches of the tested boundary (§5)
BUFFER = 0.05            # stop buffer beyond the range high, daily ATR (§7.6)
SAME_SESSION = 0.30      # R50 same-session floor, daily ATR (§7.6)
TEN_SESSION = (0.60, 0.84)      # R50 10-session floors, daily ATR (§7.6)


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


def trend(H, L, C):
    """'DOWN' / 'UP' / None on a window, real confirmed swings only (§3):
    at least 2 confirmed swing highs and 2 lows, else not established. The
    verdict itself is regime_detection._detect_structure's, which takes its
    primary path exactly when those counts are met."""
    ph, pl = pivots(H, L)
    ch, cl = confirm_index(H, L, C, ph, pl)
    hs = [H[i] for i in ph if i in ch]
    ls = [L[i] for i in pl if i in cl]
    if len(hs) < 2 or len(ls) < 2:
        return None, hs[-2:], ls[-2:]
    sd = _detect_structure(H, L, C)
    assert (sd["latest_sh"], sd["prior_sh"], sd["latest_sl"], sd["prior_sl"]) == (hs[-1], hs[-2], ls[-1], ls[-2])
    return {"DOWNTREND": "DOWN", "UPTREND": "UP"}.get(sd["structure"]), hs[-2:], ls[-2:]


def find_range(H, L, C, e, atr, ph_set, pl_set, ch, cl):
    """The longest run ending at bar e that meets §4, or None. Swings count
    only if confirmed by a close at or before e and have 3 bars after them
    inside [.., e]."""
    best = None
    rh = rl = None
    nh = nl = 0
    first = None                     # earliest counted swing in the run
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


def visits(H, L, s, e, test):
    """Touches: runs of consecutive bars in [s, e] meeting `test`, each run once.
    Returns the index of each run's last bar."""
    out, inside = [], False
    for i in range(s, e + 1):
        if test(i):
            if inside:
                out[-1] = i
            else:
                out.append(i)
            inside = True
        else:
            inside = False
    return out


def detect(h1, t, h4, d1):
    """Spec §3-§6 for the hourly bar t (index into h1). Each series is a dict of
    lists: 't' (open time, aware UTC), 'H', 'L', 'C'. Returns the detection,
    or {'why': reason}."""
    e = t - 1
    tt = h1["t"][t]
    # daily ATR: closed daily bars before the one containing the event bar
    k = bisect.bisect_right(d1["t"], tt) - 1
    if k < 15:
        return {"why": "not enough daily bars"}
    atr = compute_atr_series(d1["H"][:k], d1["L"][:k], d1["C"][:k])[-1]
    if e - RUN_MAX - K < 0:
        return {"why": "not enough hourly bars"}
    lo = max(0, e - max(RUN_MAX, H1_WIN) - 10)
    H, L, C = h1["H"][lo:e + 1], h1["L"][lo:e + 1], h1["C"][lo:e + 1]
    ph, pl = pivots(H, L)
    ch, cl = confirm_index(H, L, C, ph, pl)
    rng = find_range(H, L, C, len(C) - 1, atr, set(ph), set(pl), ch, cl)
    if rng is None:
        return {"why": "no range", "atr": atr}
    close = h1["C"][t]
    if close < rng["low"]:
        side = "DOWN"
    elif close > rng["high"]:
        side = "UP"
    else:
        return {"why": "no close beyond", "atr": atr, "range": rng}
    # trend, hourly: 72 bars ending at e
    t1, h1hs, h1ls = trend(h1["H"][e - H1_WIN + 1:e + 1], h1["L"][e - H1_WIN + 1:e + 1], h1["C"][e - H1_WIN + 1:e + 1])
    # trend, 4-hour: 120 bars closed by the event bar's close
    close_time = tt + timedelta(hours=1)
    j = bisect.bisect_right(h4["t"], close_time - timedelta(hours=4))
    if j < H4_WIN:
        return {"why": "not enough 4-hour bars", "atr": atr, "range": rng, "side": side}
    t4, h4hs, h4ls = trend(h4["H"][j - H4_WIN:j], h4["L"][j - H4_WIN:j], h4["C"][j - H4_WIN:j])
    out = {"atr": atr, "range": rng, "side": side, "h1_trend": t1, "h4_trend": t4,
           "h1_swings": (h1hs, h1ls), "h4_swings": (h4hs, h4ls), "close": close}
    s0, e0 = rng["first_swing"], rng["e"]   # touches from the first swing on (spec §5, amendment 1)
    z = ZONE * atr
    if side == "DOWN":
        tested = visits(H, L, s0, e0, lambda i: H[i] >= rng["high"] - z)
        broken = visits(H, L, s0, e0, lambda i: L[i] <= rng["low"] + z)
    else:
        tested = visits(H, L, s0, e0, lambda i: L[i] <= rng["low"] + z)
        broken = visits(H, L, s0, e0, lambda i: H[i] >= rng["high"] - z)
    out["tested_touches"] = [h1["t"][lo + i] for i in tested]
    out["broken_touches"] = [h1["t"][lo + i] for i in broken]
    out["range_first_bar"] = h1["t"][lo + rng["s"]]
    if (t1, t4) != (side, side):
        out["why"] = f"trend not aligned (hourly {t1}, 4-hour {t4}, break {side})"
        return out
    if len(tested) < TOUCHES:
        out["why"] = f"tested boundary touched {len(tested)} times (< {TOUCHES})"
        return out
    out["why"] = None
    return out


def stops(det):
    """§7.6 stop prices for a detection (side DOWN: above; UP: below)."""
    a, c, r = det["atr"], det["close"], det["range"]
    sgn = 1 if det["side"] == "DOWN" else -1
    edge = r["high"] + BUFFER * a if sgn == 1 else r["low"] - BUFFER * a
    same = max(SAME_SESSION * a, sgn * (edge - c))
    return {"same_session": (same, c + sgn * same),
            "ten_session": [(m * a, c + sgn * m * a) for m in TEN_SESSION]}


# ── worked example (§9) ──────────────────────────────────────────────────────

def _series(df):
    return {"t": [x.to_pydatetime() for x in df.index], "H": list(map(float, df["High"])),
            "L": list(map(float, df["Low"])), "C": list(map(float, df["Close"])), "O": list(map(float, df["Open"]))}


def example():
    import oanda_feed as F
    h1 = _series(F.get_hourly_bars("XAU_USD", count=500))
    h4 = _series(F.get_h4_bars("XAU_USD", count=400))
    d1 = _series(F.get_daily_bars("XAU_USD", count=260))
    pt = lambda x: x.astimezone(PT).strftime("%a %m-%d %H:%M PT")
    print(f"bars: hourly {len(h1['t'])} (last {pt(h1['t'][-1])}), 4-hour {len(h4['t'])}, daily {len(d1['t'])}")
    start = datetime(2026, 11, 16, 23, 0, tzinfo=timezone.utc)   # Mon 15:00 PT
    hits = []
    for t in range(len(h1["t"])):
        if h1["t"][t] < start:
            continue
        r = detect(h1, t, h4, d1)
        rng = r.get("range")
        rs = (f"range {rng['low']:.2f}-{rng['high']:.2f} ({rng['width_atr']:.2f} ATR, {rng['e'] - rng['s'] + 1} bars, from {pt(r['range_first_bar']) if 'range_first_bar' in r else '?'})"
              if rng else "")
        print(f"{pt(h1['t'][t])} close {h1['C'][t]:.2f} | ATR {r.get('atr', 0):.2f} | {r['why'] or 'DETECTED'} {rs}")
        if r.get("side"):
            print(f"      trend: hourly {r.get('h1_trend')} swings highs {[round(x, 2) for x in r['h1_swings'][0]]} lows {[round(x, 2) for x in r['h1_swings'][1]]};"
                  f" 4-hour {r.get('h4_trend')} highs {[round(x, 2) for x in r['h4_swings'][0]]} lows {[round(x, 2) for x in r['h4_swings'][1]]}")
            print(f"      tested-side touches {len(r['tested_touches'])}: {[pt(x) for x in r['tested_touches']]}")
            print(f"      broken-side touches {len(r['broken_touches'])}: {[pt(x) for x in r['broken_touches']]}")
        if r["why"] is None:
            hits.append((t, r))
    print(f"\nDETECTIONS: {len(hits)}")
    for t, r in hits:
        print(pt(h1["t"][t]), r["side"], stops(r))


# ── B1 counts ────────────────────────────────────────────────────────────────

def counts(root):
    import gold_move_size_study as GM
    import power_check as P
    files = {"D": ("XAU_USD_D.csv", "6202a13d86459d2d3453c31ea9ddf40a3aca44243a6d4ff75bf3d0c165d0e3ca"),
             "H4": ("XAU_USD_H4.csv", "e101117de1af589820a10eb4b5e65b30a4f294e9ee7683ac1baf8a8c02f0011c"),
             "H1": ("XAU_USD_H1.csv", "eabec6652e055540b256aa743971a1a5aa5cbb459e94b4887da6f28b8e02a4be")}
    rows = {k: GM.load(os.path.join(root, f), s) for k, (f, s) in files.items()}

    def ser(rs):
        return {"t": [datetime.fromisoformat(r[0]) for r in rs], "H": [r[2] for r in rs],
                "L": [r[3] for r in rs], "C": [r[4] for r in rs]}

    print("# B1 counts: CCD-1 (spec bcc444a, unsigned) on gold; counts only, no outcome\n")
    for era in ("STUDY", "USED"):
        h1, h4, d1 = ser(rows["H1"][era]), ser(rows["H4"][era]), ser(rows["D"][era])
        why = {}
        dets = []
        for t in range(len(h1["t"])):
            r = detect(h1, t, h4, d1)
            key = r["why"] if r["why"] is None or not r["why"].startswith(("trend", "tested")) else r["why"].split(" (")[0].split(" touched")[0]
            why[key] = why.get(key, 0) + 1
            if r["why"] is None:
                dets.append((h1["t"][t], r["side"]))
        # episodes: non-overlapping 10-session horizons = 60 4-hour bars on the real index (M34)
        def episodes(ds):
            out, nxt = [], None
            for tt, side in ds:
                if nxt is None or tt >= nxt:
                    out.append((tt, side))
                    j = bisect.bisect_right(h4["t"], tt)
                    nxt = h4["t"][j + 59] if j + 59 < len(h4["t"]) else datetime.max.replace(tzinfo=timezone.utc)
            return out
        up = [d for d in dets if d[1] == "UP"]
        dn = [d for d in dets if d[1] == "DOWN"]
        ep_all, ep_up, ep_dn = episodes(dets), episodes(up), episodes(dn)
        print(f"## {era}: hourly bars {len(h1['t'])} ({h1['t'][0]:%Y-%m-%d} -> {h1['t'][-1]:%Y-%m-%d})")
        print(f"- bars by outcome of the test: {dict(sorted(why.items(), key=lambda kv: -kv[1]))}")
        print(f"- detections: {len(dets)} (up {len(up)}, down {len(dn)})")
        print(f"- non-overlapping episodes: pooled {len(ep_all)}; up {len(ep_up)}; down {len(ep_dn)}")
        for sd in (1.25, 1.264, 1.864, 1.896):
            n = len(ep_all)
            print(f"  MDE at N={n}, SD {sd}: {P.min_detectable_edge(sd, n, power=0.8, alpha=0.05):+.3f}R" if n else "  N=0")
        print(f"- detections by year: {dict(sorted({y: sum(1 for d in dets if d[0].year == y) for y in sorted({d[0].year for d in dets})}.items()))}\n")


if __name__ == "__main__":
    if sys.argv[1] == "example":
        example()
    elif sys.argv[1] == "counts":
        counts(sys.argv[2])
