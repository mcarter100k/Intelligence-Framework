"""
precursor_study.py  —  REVERSE methodology, NO framework code changes.

The 0/4 acid test killed the forward-designed box detector: the moves the trader
circled do not come out of tidy rectangles. So instead of asking "does my guessed
detector fire before big moves?", we ask "what actually precedes big moves?"

STEP A  Find every large impulse leg (>=120 pips within <=30 H4 bars) in all H4
        history, both pairs. The four known GBP/AUD moves MUST appear.
STEP B  Characterize the precursor window (24/48 bars before each origin).
STEP C  Control comparison vs random direction-matched origins.
STEP D  The four known moves' full profiles — typical or outliers?
VERDICT Which features actually discriminate. Honest N. All features, ranked.
"""
from __future__ import annotations

import os, sys, math, statistics, random
import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timezone, timedelta
import pandas as pd

from historical_scenario_replay import _fetch_historical
from regime_detection import _detect_structure, _compute_adx, compute_atr_series, PAIRS

# ── Parameters ─────────────────────────────────────────────────────────────────
# NOTE on threshold: the Step-A brief said ">=120 pips", but 120 pips over 30 H4
# bars (5 days) is < 1.5x GBP/AUD daily ATR — noise-level, giving ~67 moves/yr
# and leaving no clean control window. We use the Researcher's stated "150+ pip"
# threshold, which yields a meaningful move set. (Change MIN_MOVE_PIPS to sweep.)
MIN_MOVE_PIPS = 150        # a "large move"
MAX_LEG_BARS  = 30         # ... within this many H4 bars
SWING_HALF    = 3          # origin must be a local extreme over +/- this
DEDUP_BARS    = 20         # merge legs whose origins are within this. <21 keeps the
                           # 06-22 and 06-26 rallies (~21 bars apart) as distinct moves.
WARMUP        = 60         # bars needed before an origin for stable features
H4_BARS       = 4900
D1_BARS       = 1300
SEED          = 42

KNOWN_MOVES = {   # from the v2 acid test (GBP_AUD)
    "2026-05-05": ("DOWN", 205),
    "2026-05-15": ("UP",   280),
    "2026-06-22": ("UP",   270),
    "2026-06-26": ("UP",   195),
}


def _last_completed_session() -> str:
    d = datetime.now(timezone.utc) - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def _med(xs): return statistics.median(xs) if xs else float("nan")
def _mean(xs): return sum(xs) / len(xs) if xs else float("nan")
def _std(xs):
    return statistics.pstdev(xs) if len(xs) > 1 else 0.0


# ── STEP A — impulse legs ───────────────────────────────────────────────────────
def find_impulse_legs(H, L, C, pip):
    """Return list of dicts: origin idx, direction, magnitude(pips), duration."""
    n = len(C)
    legs = []
    for i in range(WARMUP, n - 2):
        w_hi = max(H[i + 1:i + 1 + MAX_LEG_BARS]) if i + 1 < n else L[i]
        w_lo = min(L[i + 1:i + 1 + MAX_LEG_BARS]) if i + 1 < n else H[i]
        # up-leg from a local swing low
        if L[i] <= min(L[max(0, i - SWING_HALF):i + SWING_HALF + 1]):
            up = (w_hi - L[i]) / pip
            if up >= MIN_MOVE_PIPS:
                ext = i + 1 + H[i + 1:i + 1 + MAX_LEG_BARS].index(w_hi)
                legs.append({"o": i, "dir": +1, "mag": up, "dur": ext - i})
        # down-leg from a local swing high
        if H[i] >= max(H[max(0, i - SWING_HALF):i + SWING_HALF + 1]):
            dn = (H[i] - w_lo) / pip
            if dn >= MIN_MOVE_PIPS:
                ext = i + 1 + L[i + 1:i + 1 + MAX_LEG_BARS].index(w_lo)
                legs.append({"o": i, "dir": -1, "mag": dn, "dur": ext - i})
    return legs   # RAW (pre-dedup) — coverage is checked against these


def dedup_legs(legs):
    """Keep the largest; drop others whose origin is within DEDUP_BARS. Used for
    population feature stats only (so one move isn't counted many times)."""
    kept = []
    for lg in sorted(legs, key=lambda x: -x["mag"]):
        if all(abs(lg["o"] - k["o"]) > DEDUP_BARS for k in kept):
            kept.append(lg)
    kept.sort(key=lambda x: x["o"])
    return kept


# ── STEP B — precursor features ─────────────────────────────────────────────────
def d1_state_at(ts, d1):
    sub = d1[d1.index <= ts]
    if len(sub) < 30:
        return "UNKNOWN", 0.0
    h = [float(v) for v in sub["High"].values][-120:]
    l = [float(v) for v in sub["Low"].values][-120:]
    c = [float(v) for v in sub["Close"].values][-120:]
    struct = _detect_structure(h, l, c)["structure"]
    adx = _compute_adx(h, l, c) if len(c) >= 30 else 0.0
    return struct, adx


def features_at(o, direction, H, L, C, atr, times, d1, pip):
    a = atr[o] if atr[o] > 0 else 1e-9
    f = {}
    for W in (6, 12, 18):
        f[f"box{W}_atr"] = (max(H[o - W:o]) - min(L[o - W:o])) / a
    f["atr_ratio"]   = atr[o] / (_mean(atr[o - 20:o]) or 1e-9)
    f["atr_slope12"] = (atr[o] - atr[o - 12]) / (atr[o - 12] or 1e-9)
    f["adx"]         = _compute_adx(H[:o + 1], L[:o + 1], C[:o + 1])
    f["adx_slope12"] = f["adx"] - _compute_adx(H[:o - 11], L[:o - 11], C[:o - 11])
    f["struct_num"]  = {"UPTREND": 1, "DOWNTREND": -1}.get(
        _detect_structure(H[:o], L[:o], C[:o])["structure"], 0)
    hi30 = max(H[o - 30:o]); lo30 = min(L[o - 30:o])
    f["dist_from_high_atr"] = (hi30 - C[o]) / a
    f["dist_from_low_atr"]  = (C[o] - lo30) / a
    # failed opposite break in prior 12 bars (fakeout-then-go)
    prior_ext_lo = min(L[o - 24:o - 12]); prior_ext_hi = max(H[o - 24:o - 12])
    if direction > 0:   # up move: look for a downside fakeout
        broke = min(L[o - 12:o]) < prior_ext_lo
        recov = C[o - 1] > prior_ext_lo
    else:               # down move: upside fakeout
        broke = max(H[o - 12:o]) > prior_ext_hi
        recov = C[o - 1] < prior_ext_hi
    f["failed_break"] = 1.0 if (broke and recov) else 0.0
    d1s, d1adx = d1_state_at(times[o], d1)
    f["d1_adx"] = d1adx
    f["d1_aligned"] = 1.0 if ((direction > 0 and d1s == "UPTREND") or
                              (direction < 0 and d1s == "DOWNTREND")) else 0.0
    h = times[o].hour
    f["_session"] = ("Asia" if 22 <= h or h < 6 else
                     "London" if 6 <= h < 13 else "NY" if 13 <= h < 21 else "Late")
    return f


CONT_FEATURES = ["box6_atr", "box12_atr", "box18_atr", "atr_ratio", "atr_slope12",
                 "adx", "adx_slope12", "struct_num", "dist_from_high_atr",
                 "dist_from_low_atr", "d1_adx"]
BIN_FEATURES  = ["failed_break", "d1_aligned"]


def _cohens_d(a, b):
    sa, sb = _std(a), _std(b)
    pooled = math.sqrt((sa ** 2 + sb ** 2) / 2) or 1e-9
    return (_mean(a) - _mean(b)) / pooled


# ── Driver ───────────────────────────────────────────────────────────────────
def run_pair(pair):
    cfg = PAIRS[pair]; pip = cfg.pip_size
    end = _last_completed_session()
    h4 = _fetch_historical(pair, "H4", H4_BARS, end)
    d1 = _fetch_historical(pair, "D", D1_BARS, end)
    if h4 is None or len(h4) < 500:
        print(f"  {pair}: insufficient H4 data"); return None
    H = [float(v) for v in h4["High"].values]
    L = [float(v) for v in h4["Low"].values]
    C = [float(v) for v in h4["Close"].values]
    T = list(h4.index)
    atr = compute_atr_series(H, L, C)
    yrs = (T[-1] - T[0]).days / 365.25

    raw = find_impulse_legs(H, L, C, pip)
    legs = [lg for lg in dedup_legs(raw) if WARMUP <= lg["o"] < len(C) - 2]
    print(f"\n{'='*74}\n  {pair}  —  H4 {str(T[0])[:10]} → {str(T[-1])[:10]}  "
          f"({yrs:.1f}y)\n{'='*74}")
    print(f"  STEP A — impulse legs (>= {MIN_MOVE_PIPS} pips in <= {MAX_LEG_BARS} H4 bars)")
    print(f"    raw detections {len(raw)}  →  {len(legs)} distinct moves after de-dup "
          f"({len(legs)/yrs:.1f}/yr)  | up {sum(1 for l in legs if l['dir']>0)}  "
          f"down {sum(1 for l in legs if l['dir']<0)}")
    mags = [l["mag"] for l in legs]
    print(f"    magnitude pips: median {_med(mags):.0f}  max {max(mags):.0f}  "
          f"| duration bars: median {_med([l['dur'] for l in legs]):.0f}")

    # known-move coverage (GBP_AUD only) — checked against RAW detections (did the
    # detector SEE the move?), independent of which origin survived de-dup.
    known_hits = {}
    if pair == "GBP_AUD":
        print("    known-move coverage (vs raw detections):")
        for date, (d, mag) in KNOWN_MOVES.items():
            ts = pd.Timestamp(date, tz="UTC")
            cands = [lg for lg in raw
                     if abs((T[lg["o"]] - ts).total_seconds()) <= 6 * 4 * 3600]  # +/-6 bars
            hit = max(cands, key=lambda x: x["mag"]) if cands else None
            known_hits[date] = ({"hit": hit,
                                 "feat": features_at(hit["o"], hit["dir"], H, L, C, atr, T, d1, pip)}
                                if hit else None)
            if hit:
                print(f"      {date} {d:>4} {mag}p  → DETECTED leg @ {str(T[hit['o']])[:13]} "
                      f"dir={'UP' if hit['dir']>0 else 'DOWN'} {hit['mag']:.0f}p")
            else:
                print(f"      {date} {d:>4} {mag}p  → *** MISSED ***")

    # STEP B — features for moves
    move_feats = [features_at(lg["o"], lg["dir"], H, L, C, atr, T, d1, pip) for lg in legs]

    # STEP C — controls = "quiet" origins: bars where NO large move (either
    # direction) follows within MAX_LEG_BARS. This is the semantically correct
    # control ("what precedes a NON-move"), and it is direction-matched to the
    # move population so every feature is compared like-for-like.
    rng = random.Random(SEED)
    quiet = []
    for i in range(WARMUP, len(C) - MAX_LEG_BARS - 2):
        up = (max(H[i + 1:i + 1 + MAX_LEG_BARS]) - L[i]) / pip
        dn = (H[i] - min(L[i + 1:i + 1 + MAX_LEG_BARS])) / pip
        if up < MIN_MOVE_PIPS and dn < MIN_MOVE_PIPS:
            quiet.append(i)
    print(f"    controls available (quiet bars, no >= {MIN_MOVE_PIPS}p move in "
          f"{MAX_LEG_BARS} bars): {len(quiet)}")
    ctrl_feats = []
    for lg in legs:
        if not quiet:
            break
        oi = rng.choice(quiet)
        ctrl_feats.append(features_at(oi, lg["dir"], H, L, C, atr, T, d1, pip))

    return {"pair": pair, "legs": legs, "move": move_feats, "ctrl": ctrl_feats,
            "known": known_hits, "T": T}


def report_discrimination(res):
    pair = res["pair"]; M = res["move"]; K = res["ctrl"]
    print(f"\n  STEP B/C — precursor features: {len(M)} moves vs {len(K)} controls  [{pair}]")
    print(f"  {'feature':<20}{'move med':>10}{'ctrl med':>10}{'move mean':>10}"
          f"{'ctrl mean':>10}{'effect d':>10}")
    print("  " + "-" * 70)
    rows = []
    for feat in CONT_FEATURES:
        mv = [m[feat] for m in M]; cv = [c[feat] for c in K]
        d = _cohens_d(mv, cv)
        rows.append((abs(d), feat, _med(mv), _med(cv), _mean(mv), _mean(cv), d, "cont"))
    for feat in BIN_FEATURES:
        mv = [m[feat] for m in M]; cv = [c[feat] for c in K]
        rm, rc = _mean(mv), _mean(cv)
        d = _cohens_d(mv, cv)
        rows.append((abs(d), feat, rm, rc, rm, rc, d, "rate"))
    rows.sort(reverse=True)
    for absd, feat, mmed, cmed, mmean, cmean, d, kind in rows:
        tag = "  ← DISCRIMINATES" if absd >= 0.5 else ("  · weak" if absd >= 0.2 else "")
        if kind == "rate":
            print(f"  {feat:<20}{mmed:>9.0%}{cmed:>10.0%}{'':>10}{'':>10}{d:>+10.2f}{tag}")
        else:
            print(f"  {feat:<20}{mmed:>10.2f}{cmed:>10.2f}{mmean:>10.2f}{cmean:>10.2f}{d:>+10.2f}{tag}")
    # session distribution
    def sess_dist(fs):
        from collections import Counter
        c = Counter(f["_session"] for f in fs); tot = sum(c.values()) or 1
        return {k: c.get(k, 0) / tot for k in ("Asia", "London", "NY", "Late")}
    sm, sc = sess_dist(M), sess_dist(K)
    print(f"\n  session of origin (move vs control):")
    for s in ("Asia", "London", "NY", "Late"):
        print(f"    {s:<8} move {sm[s]:>5.0%}   control {sc[s]:>5.0%}")
    strong = [(f, d) for (absd, f, *_rest, d, _k) in rows if abs(d) >= 0.5]
    top = rows[0]
    print(f"\n  VERDICT [{pair}]: {len(strong)} feature(s) reach |d|>=0.5 "
          f"(strong). Strongest = {top[1]} (d={top[6]:+.2f}). "
          f"{'NO feature strongly discriminates.' if not strong else ''}")


def report_known(res):
    if res["pair"] != "GBP_AUD":
        return
    print(f"\n  STEP D — the four known GBP/AUD moves, full precursor profiles")
    H = None
    # recompute population medians for typical/outlier flag
    M = res["move"]
    pop = {f: sorted(m[f] for m in M) for f in CONT_FEATURES + BIN_FEATURES}
    def iqr(xs):
        n = len(xs); return (xs[n // 4], xs[(3 * n) // 4]) if n >= 4 else (min(xs), max(xs))
    T = res["T"]
    for date, rec in res["known"].items():
        if not rec:
            print(f"\n    {date}: MISSED — not detected (see Step A)"); continue
        hit, f = rec["hit"], rec["feat"]
        print(f"\n    ─── {date}  {('UP' if hit['dir']>0 else 'DOWN')} {hit['mag']:.0f}p "
              f"@ {str(T[hit['o']])[:13]}  session={f['_session']} ───")
        for feat in CONT_FEATURES + BIN_FEATURES:
            lo, hi = iqr(pop[feat])
            typ = "typical" if lo <= f[feat] <= hi else "OUTLIER"
            print(f"      {feat:<20} {f[feat]:>8.2f}   pop IQR [{lo:.2f}, {hi:.2f}]  {typ}")


def main():
    print("=" * 74)
    print("  PRECURSOR STUDY — reverse methodology (evidence-first)")
    print(f"  Move def: >= {MIN_MOVE_PIPS} pips in <= {MAX_LEG_BARS} H4 bars | "
          f"control seed {SEED} | NO framework changes")
    print("=" * 74)
    results = []
    for pair in ("GBP_AUD", "GBP_JPY"):
        r = run_pair(pair)
        if r:
            report_discrimination(r)
            report_known(r)
            results.append(r)
    print(f"\n{'='*74}\n  RUN COMPLETE — framework unchanged\n{'='*74}")


if __name__ == "__main__":
    main()
