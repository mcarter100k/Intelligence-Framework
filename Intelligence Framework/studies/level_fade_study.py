"""
level_fade_study.py  —  reversal-at-level diagnostic. NO framework changes.

QUESTION: turns may be unpredictable in TIMING but knowable in LOCATION.
  (1) Do significant H4 turns cluster at pre-existing levels?
  (2) Does level-touch + rejection-confirmation carry edge at honest N?

Method: build a no-lookahead level map (confirmed swing highs/lows + 30-bar
extremes, expiring 1.0 ATR beyond), detect touches, then rejection triggers,
and measure spread-adjusted outcomes over a 30-bar horizon. Controls isolate
what the trigger, the D1 alignment, and the touch-number contribute.
"""
import os as _os, sys as _sys  # studies path bootstrap (project root)
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
for _p in (_ROOT, _os.path.join(_ROOT, "shadow")):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

import statistics
import warnings
warnings.filterwarnings("ignore")
from collections import Counter

from regime_detection import _detect_structure, compute_atr_series, PAIRS
from entry_confirmation import _detect_engulfing
from historical_scenario_replay import _fetch_historical
from datetime import datetime, timezone, timedelta

# ── Frozen study params ─────────────────────────────────────────────────────────
NEAR_ATR       = 0.15   # touch proximity to a level
REJECT_ATR     = 0.30   # rejection = close back this far from the level
STOP_BUF_ATR   = 0.25   # stop sits this far beyond the level extreme
EXPIRE_ATR     = 1.0    # level expires once a close is this far beyond it
TOUCH_COOLDOWN = 6      # bars since the level was last touched
REJECT_WINDOW  = 2      # bars after a touch to confirm rejection
HORIZON        = 30     # outcome measured over this many H4 bars
PIVOT_N        = 3      # swing pivot half-width
EXTREME_N      = 30     # rolling-extreme lookback
SPREAD_PIPS    = 3.0
BIG_LEG_PIPS   = 100    # a "significant turn" leads to a leg >= this
BIG_LEG_BARS   = 30
NEAR_TURN_ATR  = 0.30   # "near a level" for the location question
MIN_N          = 20
H4_MAX, D1_MAX = 4900, 1300


def _last_completed_session():
    d = datetime.now(timezone.utc) - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def _med(xs): return round(statistics.median(xs), 1) if xs else float("nan")
def _pct(a, b): return f"{a/b:.0%}" if b else "n/a"


def _norm(df):
    if df is not None and hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)
    return df


def _pivots(H, L):
    """Confirmed swing pivots: (born_idx, price, side). born = confirmation bar
    (j + PIVOT_N) so there is no lookahead."""
    out = []
    n = len(H)
    for j in range(PIVOT_N, n - PIVOT_N):
        if H[j] == max(H[j - PIVOT_N:j + PIVOT_N + 1]):
            out.append((j + PIVOT_N, H[j], "high"))
        if L[j] == min(L[j - PIVOT_N:j + PIVOT_N + 1]):
            out.append((j + PIVOT_N, L[j], "low"))
    return out


def _d1_structure_map(pair, end):
    """List of (timestamp, structure) per D1 bar (no lookahead: structure at bar j
    uses bars up to j)."""
    d1 = _norm(_fetch_historical(pair.replace("_", ""), "D", D1_MAX, end))
    if d1 is None or len(d1) < 60:
        return []
    H = [float(v) for v in d1["High"].values]
    L = [float(v) for v in d1["Low"].values]
    C = [float(v) for v in d1["Close"].values]
    T = list(d1.index)
    out = []
    for j in range(30, len(C)):
        s = _detect_structure(H[max(0, j - 120):j + 1], L[max(0, j - 120):j + 1],
                              C[max(0, j - 120):j + 1])["structure"]
        out.append((T[j], s))
    return out


def _d1_at(ts, d1map):
    s = "TRANSITIONAL"
    for t, st in d1map:
        if t <= ts:
            s = st
        else:
            break
    return s


def simulate(direction, entry, stop, fh, fl, fc, pip, spread):
    if not fc:
        return None
    R = abs(entry - stop) or 1e-9
    if direction == "LONG":
        mfe = (max(fh) - entry) / pip; mae = (entry - min(fl)) / pip
        hit = min(fl) <= stop; net = (fc[-1] - entry) / pip
    else:
        mfe = (entry - min(fl)) / pip; mae = (max(fh) - entry) / pip
        hit = max(fh) >= stop; net = (entry - fc[-1]) / pip
    net -= spread
    r = -1.0 if hit else round((net * pip) / R, 2)
    return {"mfe": round(mfe, 1), "mae": round(mae, 1), "net": round(net, 1),
            "hit": hit, "r": r}


def _stats(rows, label):
    if len(rows) < MIN_N:
        return f"  {label:<40} N={len(rows):<4} INSUFFICIENT(N<{MIN_N})"
    n = len(rows)
    wins = sum(1 for x in rows if x["net"] > 0)
    fake = sum(1 for x in rows if x["hit"])
    return (f"  {label:<40} N={n:<4} win {_pct(wins,n):>5}  fake {_pct(fake,n):>5}  "
            f"medR {_med([x['r'] for x in rows]):>5}  medMFE {_med([x['mfe'] for x in rows]):>6}  "
            f"medMAE {_med([x['mae'] for x in rows]):>6}")


def run(pair):
    end = _last_completed_session()
    h4 = _norm(_fetch_historical(pair.replace("_", ""), "H4", H4_MAX, end))
    if h4 is None or len(h4) < 500:
        print(f"  {pair}: insufficient H4"); return
    O = [float(v) for v in h4["Open"].values]
    H = [float(v) for v in h4["High"].values]
    L = [float(v) for v in h4["Low"].values]
    C = [float(v) for v in h4["Close"].values]
    T = list(h4.index)
    atr = compute_atr_series(H, L, C)
    pip = PAIRS[pair].pip_size
    spread = SPREAD_PIPS
    yrs = (T[-1] - T[0]).days / 365.25
    d1map = _d1_structure_map(pair, end)

    piv = _pivots(H, L)
    piv_by_born = {}
    for born, price, side in piv:
        piv_by_born.setdefault(born, []).append((price, side))

    # walk forward, maintain active levels
    active = []          # dicts: price, side, born, touches[list of idx], source
    touches = []         # touch events (with/without rejection)
    rejects = []         # confirmed rejection trades (dicts + context)
    near_level_bars = 0  # base-rate numerator

    def _add_level(price, side, born, source):
        for lv in active:
            if lv["side"] == side and abs(lv["price"] - price) <= 0.10 * atr[born]:
                return  # dedupe against an existing nearby level
        active.append({"price": price, "side": side, "born": born,
                       "touches": [], "source": source})

    for i in range(EXTREME_N + PIVOT_N, len(C) - HORIZON - 1):
        a = atr[i] if atr[i] > 0 else 1e-9
        # born pivots
        for price, side in piv_by_born.get(i, []):
            _add_level(price, side, i, "pivot")
        # 30-bar extremes (known as of i)
        _add_level(max(H[i - EXTREME_N:i]), "high", i, "extreme")
        _add_level(min(L[i - EXTREME_N:i]), "low",  i, "extreme")
        # expire
        active[:] = [lv for lv in active if not (
            (lv["side"] == "high" and C[i] > lv["price"] + EXPIRE_ATR * a) or
            (lv["side"] == "low"  and C[i] < lv["price"] - EXPIRE_ATR * a))]

        # base-rate: is this bar's close within NEAR_TURN_ATR of any active level?
        if any(abs(C[i] - lv["price"]) <= NEAR_TURN_ATR * a for lv in active):
            near_level_bars += 1

        # touch detection
        for lv in active:
            reached = (abs(H[i] - lv["price"]) <= NEAR_ATR * a) if lv["side"] == "high" \
                else (abs(L[i] - lv["price"]) <= NEAR_ATR * a)
            if not reached:
                continue
            if lv["touches"] and (i - lv["touches"][-1]) <= TOUCH_COOLDOWN:
                continue
            touch_no = len(lv["touches"]) + 1
            lv["touches"].append(i)
            d1 = _d1_at(T[i], d1map)
            direction = "SHORT" if lv["side"] == "high" else "LONG"
            aligned = (d1 == "DOWNTREND" and direction == "SHORT") or \
                      (d1 == "UPTREND" and direction == "LONG")
            touch = {"i": i, "side": lv["side"], "dir": direction, "level": lv["price"],
                     "age": i - lv["born"], "touch_no": touch_no, "aligned": aligned}

            # control (a): outcome from the touch bar itself, no trigger
            fh, fl, fc = H[i + 1:i + 1 + HORIZON], L[i + 1:i + 1 + HORIZON], C[i + 1:i + 1 + HORIZON]
            stop_notrig = (lv["price"] + STOP_BUF_ATR * a) if direction == "SHORT" \
                else (lv["price"] - STOP_BUF_ATR * a)
            sim_nt = simulate(direction, C[i], stop_notrig, fh, fl, fc, pip, spread)
            if sim_nt:
                touch["notrigger"] = sim_nt
            touches.append(touch)

            # rejection trigger within REJECT_WINDOW bars
            for k in range(i, min(i + 1 + REJECT_WINDOW, len(C) - HORIZON - 1)):
                eng = _detect_engulfing(H[:k + 1], L[:k + 1], O[:k + 1], C[:k + 1])
                if direction == "SHORT":
                    trig = (C[k] <= lv["price"] - REJECT_ATR * a) or \
                           (eng["detected"] and eng["direction"] == "SHORT")
                    stop = lv["price"] + STOP_BUF_ATR * a
                else:
                    trig = (C[k] >= lv["price"] + REJECT_ATR * a) or \
                           (eng["detected"] and eng["direction"] == "LONG")
                    stop = lv["price"] - STOP_BUF_ATR * a
                if trig:
                    fh2 = H[k + 1:k + 1 + HORIZON]; fl2 = L[k + 1:k + 1 + HORIZON]; fc2 = C[k + 1:k + 1 + HORIZON]
                    sim = simulate(direction, C[k], stop, fh2, fl2, fc2, pip, spread)
                    if sim:
                        rejects.append({**touch, **sim, "trig_bar": k})
                    break

    total_bars = len(C) - HORIZON - 1 - (EXTREME_N + PIVOT_N)

    # ── STEP 5: location of significant turns ─────────────────────────────────
    turns_near = turns_total = 0
    for j in range(EXTREME_N + PIVOT_N, len(C) - BIG_LEG_BARS - 1):
        # significant turn = pivot leading to a >=100-pip leg
        is_hi = H[j] == max(H[max(0, j - PIVOT_N):j + PIVOT_N + 1])
        is_lo = L[j] == min(L[max(0, j - PIVOT_N):j + PIVOT_N + 1])
        leg = 0.0; turn_price = None
        if is_hi:
            leg = (H[j] - min(L[j + 1:j + 1 + BIG_LEG_BARS])) / pip; turn_price = H[j]
        elif is_lo:
            leg = (max(H[j + 1:j + 1 + BIG_LEG_BARS]) - L[j]) / pip; turn_price = L[j]
        if turn_price is None or leg < BIG_LEG_PIPS:
            continue
        turns_total += 1
        a = atr[j] if atr[j] > 0 else 1e-9
        # a level that existed BEFORE j: a prior confirmed pivot (born < j) within range
        pre = any(abs(price - turn_price) <= NEAR_TURN_ATR * a
                  for born, price, side in piv if born < j)
        # or a prior 30-bar extreme
        pre = pre or (abs(max(H[j - EXTREME_N:j]) - turn_price) <= NEAR_TURN_ATR * a) \
                  or (abs(min(L[j - EXTREME_N:j]) - turn_price) <= NEAR_TURN_ATR * a)
        if pre:
            turns_near += 1

    base_rate = near_level_bars / total_bars if total_bars else 0

    print(f"\n{'='*84}\n  {pair}  —  H4 {str(T[0])[:10]} → {str(T[-1])[:10]}  ({yrs:.1f}y)\n{'='*84}")
    print(f"  touch events: {len(touches)} ({len(touches)/yrs:.0f}/yr)  |  "
          f"rejection events: {len(rejects)} ({len(rejects)/yrs:.0f}/yr)")
    print("\n  STEP 3 — rejection entries (spread-adjusted):")
    print(_stats(rejects, "ALL rejections"))
    print("\n  STEP 4a — trigger value (touch WITHOUT rejection):")
    print(_stats([t["notrigger"] for t in touches if "notrigger" in t], "touches, no trigger"))
    print("\n  STEP 4b — rejection WITH vs AGAINST D1 structure:")
    print(_stats([r for r in rejects if r["aligned"]], "aligned with D1"))
    print(_stats([r for r in rejects if not r["aligned"]], "against D1"))
    print("\n  STEP 4c — touch number of the level:")
    print(_stats([r for r in rejects if r["touch_no"] == 1], "1st touch"))
    print(_stats([r for r in rejects if r["touch_no"] == 2], "2nd touch"))
    print(_stats([r for r in rejects if r["touch_no"] >= 3], "3rd+ touch"))
    print(f"\n  STEP 5 — LOCATION: significant turns (>= {BIG_LEG_PIPS}p leg): {turns_total}")
    print(f"    within {NEAR_TURN_ATR} ATR of a PRE-EXISTING level : "
          f"{turns_near}/{turns_total} = {_pct(turns_near, turns_total)}")
    print(f"    base rate (all bars near a level)               : {_pct(near_level_bars, total_bars)}")
    lift = (turns_near / turns_total) / base_rate if base_rate and turns_total else 0
    print(f"    lift over base rate                             : {lift:.2f}x")


def main():
    print("=" * 84)
    print("  LEVEL FADE STUDY — reversal-at-level diagnostic (NO framework changes)")
    print(f"  touch<= {NEAR_ATR}ATR | reject>= {REJECT_ATR}ATR | stop {STOP_BUF_ATR}ATR beyond | "
          f"horizon {HORIZON} | spread {SPREAD_PIPS}p | MIN_N {MIN_N}")
    print("=" * 84)
    from regime_detection import PAIRS as P
    for pair in ("GBP_AUD", "GBP_JPY"):
        run(pair)
    print(f"\n{'='*84}\n  RUN COMPLETE — framework unchanged\n{'='*84}")


if __name__ == "__main__":
    main()
