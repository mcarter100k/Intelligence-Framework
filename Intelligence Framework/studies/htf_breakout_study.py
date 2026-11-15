"""Pre-registered test (BCS-2): breaks of weekly and daily levels, taken only in
the daily trend's direction, only when the first obstacle lies beyond the target,
with fixed 1.5R / 2.5R targets and the framework's management rules
(docs/specs/htf_breakout_study_spec.md).

Cells on GBP_AUD H1, long and short pooled in each:
  B-1.5  B-2.5   enter on the second hourly close beyond the level
  C-1.5  C-2.5   after that, a limit at the level for 12 bars (the retest)
Verdict data: the research archive's STUDY span (2005-2013). A learning-only
replication runs on the USED span (2021-04-27 -> 2026-09-09). This runner never
fetches anything; research_archive.load refuses the sealed block.

usage:
  python3 -I htf_breakout_study.py selftest
  python3 -I htf_breakout_study.py counts <archive_dir>
  python3 -I htf_breakout_study.py full <archive_dir> <report_md>
"""
import bisect
import os
import random
import statistics
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "foundation", "tools"))
import breakout_confirmation_study as B1  # noqa: E402  BCS-1 helpers (frozen, pinned)
import history_study_convert as C  # noqa: E402  session day
from shadow_cost_regrade import rollover_nights  # noqa: E402
from episodes import count_episodes  # noqa: E402
from power_check import (bootstrap_lower_bound, bootstrap_upper_bound,  # noqa: E402
                         min_detectable_edge, n_required, power_at_n)

UTC = timezone.utc
PAIR, BASE, QUOTE, PIP = B1.PAIR, B1.BASE, B1.QUOTE, B1.PIP
K_D, K_W = 3, 2                 # playbook swing k: daily 3, weekly 2 (spec §4.1)
D_AGE, W_AGE = 120, 520         # level life in sessions after the swing (spec §4.1)
ZONE_ATR = 0.25                 # zone depth behind the level, daily ATR (spec §4.4)
BUFFER_PIPS = 15.0              # stop buffer beyond the zone (spec §4.4)
MIN_STOP_ATR, MAX_STOP_ATR = 0.3, 1.5
TARGETS = (1.5, 2.5)            # effective R after spread (spec §4.6)
BE_R, TRAIL_START_R, TRAIL_GAP_R = 1.0, 1.5, 0.5
PARTIAL = 0.5
MAX_HOLD = 120                  # H1 bars after entry (spec §4.7)
RETEST_BARS = B1.RETEST_BARS    # 12
ENTRIES = ("B", "C")
CELLS = tuple((e, m) for e in ENTRIES for m in TARGETS)
ALPHA = 0.05 / len(CELLS)
CONF_LOWER = 1 - ALPHA          # 0.9875
CONF_UPPER = 0.90
REFUTE_BAR = 0.15
RESAMPLES, SEED, MIN_N, SD_ASSUMED = 20000, 7, 20, 1.2
USED_SPREAD = 3.0               # data_map_spec §4, 2021-> row
FLAT_SPREADS = (3.0, 5.1)
BLOCK_END = datetime(2021, 4, 26, 21, 0, tzinfo=UTC)
USED_LAST = date(2026, 9, 9)
STOP_REASONS = ("stop", "breakeven", "trail")


# Data ------------------------------------------------------------------------------

def check_span(times, span):
    if span == "STUDY":
        B1.check_window(times)
        return
    for t in times:
        if t < BLOCK_END or C.session_day(t) > USED_LAST:
            raise RuntimeError(f"bar {t.isoformat()} is outside the USED span: refused")


def load_span(archive_dir, span):
    import research_archive as RA
    B1.verify_hashes(archive_dir)
    h1 = RA.load(archive_dir, PAIR, "H1", {span})
    d1 = RA.load(archive_dir, PAIR, "D", {span})
    check_span(h1, span)
    check_span(d1, span)
    return prepare(h1, d1)


def prepare(h1, d1):
    opens = sorted(h1)
    bars = {"opens": opens, "O": [h1[t][0] for t in opens], "H": [h1[t][1] for t in opens],
            "L": [h1[t][2] for t in opens], "C": [h1[t][3] for t in opens]}
    ts = sorted(d1)
    sess = {"days": [C.session_day(t) for t in ts], "H": [d1[t][1] for t in ts], "L": [d1[t][2] for t in ts]}
    bars["k"] = [bisect.bisect_left(sess["days"], C.session_day(t)) for t in opens]   # completed sessions
    bars["atr"] = B1.bar_atr(opens, B1.session_table(d1))
    return bars, sess


def weeks(sess):
    """Weekly bars from sessions: (high, low, index of the week's last session)."""
    out, cur = [], None
    for i, d in enumerate(sess["days"]):
        key = d - timedelta(days=d.weekday())
        if cur is None or key != cur[0]:
            cur = [key, sess["H"][i], sess["L"][i], i]
            out.append(cur)
        else:
            cur[1], cur[2], cur[3] = max(cur[1], sess["H"][i]), min(cur[2], sess["L"][i]), i
    return [(w[1], w[2], w[3]) for w in out]


def htf_levels(sess):
    """Long-side levels (swing highs): D1 k=3 and weekly k=2, with the completed-session
    count from which each is usable and the count at which it expires (spec §4.1)."""
    lv = []
    for conf, s, p in B1.confirmed_swings(sess["H"], K_D):
        lv.append({"price": p, "src": "D", "usable_k": conf + 1, "expire_k": s + D_AGE})
    wk = weeks(sess)
    for conf, w, p in B1.confirmed_swings([x[0] for x in wk], K_W):
        lv.append({"price": p, "src": "W", "usable_k": wk[conf][2] + 1, "expire_k": wk[w][2] + W_AGE})
    lv.sort(key=lambda x: (x["usable_k"], x["price"]))
    for x in lv:
        x["consumed_bar"] = None
    return lv


def trend_by_k(sess, nk):
    """Daily structure from D1 swings usable at each completed-session count k:
    +1 higher high and higher low, -1 lower high and lower low, 0 otherwise (spec §4.3)."""
    hs = [(c + 1, p) for c, s, p in B1.confirmed_swings(sess["H"], K_D)]
    ls = [(c + 1, -p) for c, s, p in B1.confirmed_swings([-x for x in sess["L"]], K_D)]
    out = []
    for k in range(nk + 1):
        h = [p for u, p in hs if u <= k][-2:]
        l = [p for u, p in ls if u <= k][-2:]
        if len(h) < 2 or len(l) < 2:
            out.append(0)
        elif h[1] > h[0] and l[1] > l[0]:
            out.append(1)
        elif h[1] < h[0] and l[1] < l[0]:
            out.append(-1)
        else:
            out.append(0)
    return out


def mirror_sess(sess):
    return {"days": sess["days"], "H": [-x for x in sess["L"]], "L": [-x for x in sess["H"]]}


# Events (long side; the short side is the mirror) ------------------------------------

def find_events(Cl, kk, levels):
    """Fresh closes above live levels (spec §4.2). Marks consumed_bar on levels."""
    active, li, events, counts = [], 0, [], Counter()
    for j in range(1, len(Cl)):
        k = kk[j]
        while li < len(levels) and levels[li]["usable_k"] <= k:
            lv = levels[li]
            li += 1
            if Cl[j - 1] > lv["price"]:
                lv["consumed_bar"] = j
                counts["levels already exceeded when usable"] += 1
            else:
                active.append(lv)
                counts[f"levels usable ({lv['src']})"] += 1
        keep = [x for x in active if x["expire_k"] > k]
        counts["levels expired unbroken"] += len(active) - len(keep)
        active = keep
        crossed = [x for x in active if Cl[j - 1] <= x["price"] < Cl[j]]
        if not crossed:
            continue
        lv = max(crossed, key=lambda x: x["price"])
        if j + 1 >= len(Cl):
            counts["events on the last bar (not traded)"] += 1
            continue
        fake = Cl[j + 1] <= lv["price"]
        events.append({"bar": j, "level": lv["price"], "src": lv["src"], "fake": fake})
        if not fake:
            for x in active:
                if x["price"] <= Cl[j + 1]:
                    x["consumed_bar"] = j + 1
            counts["levels consumed by confirmations"] += sum(x["price"] <= Cl[j + 1] for x in active)
            active = [x for x in active if x["price"] > Cl[j + 1]]
    return events, counts


def obstacle(levels, k, bar, price):
    """Nearest live level above price at entry: usable, unexpired, not consumed before bar."""
    best = None
    for x in levels:
        if x["usable_k"] <= k < x["expire_k"] and x["price"] > price and \
                (x["consumed_bar"] is None or x["consumed_bar"] > bar):
            best = x["price"] if best is None else min(best, x["price"])
    return best


# Stop, target, management ------------------------------------------------------------

def obstacle_blocks(ob, px, T):
    """The owner's check: no trade when the first obstacle lies before the target (spec §4.5)."""
    return ob is not None and ob < px + T


def stop_for(level, px, atr):
    """Stop below the zone (level - 0.25 ATR) by 15 pips; widened to 0.3 ATR; None if
    wider than 1.5 ATR (spec §4.4)."""
    stop = level - ZONE_ATR * atr - BUFFER_PIPS * PIP
    if px - stop < MIN_STOP_ATR * atr:
        stop = px - MIN_STOP_ATR * atr
    if px - stop > MAX_STOP_ATR * atr:
        return None
    return stop


def target_distance(m, d, sp):
    """TP distance so that (TP - spread) / (risk + spread) = m (spec §4.6)."""
    return m * (d + sp) + sp


def manage(O, H, L, Cl, e, px, stop, T, at_close=True, partial=True, max_hold=MAX_HOLD):
    """Stop first on every bar; then +1R (half off if partial; breakeven from the next bar);
    then the target; trailing 0.5R behind the best high once +1.5R has been reached.
    A and B enter at the close of e; C fills on bar e (stop check only on that bar)."""
    last = e + max_hold
    if last >= len(Cl):
        return None
    d = px - stop
    if not at_close and px <= stop:
        return {"raw": -1.0, "gap_r": -1.0, "exits": [(e, 1.0, "stop")], "reason": "fill through stop"}
    one_r, tgt, trail_at = px + BE_R * d, px + T, px + TRAIL_START_R * d
    cur, size, pnl, gpnl, exits, hi, reached = stop, 1.0, 0.0, 0.0, [], px, False
    for b in range(e + 1 if at_close else e, last + 1):
        if L[b] <= cur:
            kind = "stop" if cur == stop else ("breakeven" if cur == px else "trail")
            g = cur if (not at_close and b == e) else min(O[b], cur)
            pnl += size * (cur - px)
            gpnl += size * (g - px)
            exits.append((b, size, kind))
            size = 0.0
            break
        if not at_close and b == e:
            continue
        if H[b] >= one_r and not reached:
            reached = True
            if partial:
                pnl += PARTIAL * d
                gpnl += PARTIAL * d
                size -= PARTIAL
                exits.append((b, PARTIAL, "1R partial"))
        if H[b] >= tgt:
            pnl += size * T
            gpnl += size * T
            exits.append((b, size, "target"))
            size = 0.0
            break
        hi = max(hi, H[b])
        if reached:
            cur = max(cur, px)
        if hi >= trail_at:
            cur = max(cur, hi - TRAIL_GAP_R * d)
    if size > 0:
        pnl += size * (Cl[last] - px)
        gpnl += size * (Cl[last] - px)
        exits.append((last, size, "time"))
    return {"raw": pnl / d, "gap_r": gpnl / d, "exits": exits, "reason": exits[-1][2]}


def financing_r(side, opens, e, at_close, exits, entry_price, d_pips, rates):
    if rates is None:
        return 0.0, 0.0
    t0 = opens[e] + (timedelta(hours=1) if at_close else timedelta(0))
    day = C.session_day(opens[e])
    net = side * (B1.rate_on(rates, BASE, day) - B1.rate_on(rates, QUOTE, day)) - B1.MARKUP
    pips = nights = 0.0
    for b, size, kind in exits:
        t1 = opens[b] if kind in STOP_REASONS or kind == "fill through stop" else opens[b] + timedelta(hours=1)
        n = rollover_nights(t0, t1)
        nights += size * n
        pips += size * entry_price * net / 100 * n / 365 / PIP
    return pips / d_pips, nights


def spread_pips(mode, day):
    if mode == "era":
        return B1.era_spread(day.year)
    if mode == "used":
        return USED_SPREAD
    return float(mode)


# Trades ------------------------------------------------------------------------------

def side_trades(bars, sess, side, rates, entry, m, mode, use_trend=True, use_obstacle=True, partial=True):
    if side == 1:
        O, H, L, Cl, ss = bars["O"], bars["H"], bars["L"], bars["C"], sess
    else:
        O, H, L, Cl = B1.mirrored(bars)
        ss = mirror_sess(sess)
    levels = htf_levels(ss)
    events, ecounts = find_events(Cl, bars["k"], levels)
    trend = trend_by_k(ss, len(ss["days"]))
    trades, skips = [], Counter()
    for ev in events:
        if ev["fake"]:
            continue
        j, lvl = ev["bar"], ev["level"]
        if entry == "B":
            e, px, at_close = j + 1, Cl[j + 1], True
        else:
            e, px = B1.retest_fill(O, L, j + 1, lvl)
            if e is None:
                skips[f"no retest ({px})"] += 1
                continue
            at_close = False
        k, atr = bars["k"][e], bars["atr"][e]
        if atr is None:
            skips["ATR warm-up"] += 1
            continue
        if use_trend and trend[k] != 1:
            skips["daily trend not aligned"] += 1
            continue
        stop = stop_for(lvl, px, atr)
        if stop is None:
            skips["stop wider than 1.5 ATR"] += 1
            continue
        d = px - stop
        day = C.session_day(bars["opens"][e])
        sp = spread_pips(mode, day) * PIP
        T = target_distance(m, d, sp)
        if use_obstacle:
            ob = obstacle(levels, k, e, px)
            if obstacle_blocks(ob, px, T):
                skips["first obstacle inside the target"] += 1
                continue
        g = manage(O, H, L, Cl, e, px, stop, T, at_close=at_close, partial=partial)
        if g is None:
            skips["ungraded at end of data"] += 1
            continue
        fin_r, nights = financing_r(side, bars["opens"], e, at_close, g["exits"], abs(px), d / PIP, rates)
        spread_r = -(sp / PIP) / (d / PIP)
        trades.append({"bar": e, "side": side, "day": day, "src": ev["src"], "raw": g["raw"],
                       "gap_raw": g["gap_r"], "reason": g["reason"], "risk_pips": d / PIP,
                       "spread_r": spread_r, "fin_r": fin_r, "nights": nights,
                       "adj": g["raw"] + spread_r + fin_r, "gap_adj": g["gap_r"] + spread_r + fin_r})
    return trades, skips, events, ecounts


def cell(bars, sess, rates, entry, m, mode, **kw):
    out, skips, ev, ec = [], Counter(), {}, {}
    for side in (1, -1):
        t, s, e, c = side_trades(bars, sess, side, rates, entry, m, mode, **kw)
        out += t
        skips.update(s)
        ev[side], ec[side] = e, c
    return out, skips, ev, ec


def episodes(trades):
    return B1.episodes(trades, horizon=MAX_HOLD)


# Statistics ------------------------------------------------------------------------

def classify(n, lower, upper, without_best):
    if n < MIN_N:
        return "INSUFFICIENT"
    if lower > 0 and without_best > 0:
        return "SUPPORTED"
    if upper < REFUTE_BAR:
        return "REFUTED"
    return "INCONCLUSIVE"


def summarize(rs, iters=RESAMPLES):
    n = len(rs)
    s = {"n": n, "mean": statistics.fmean(rs) if rs else float("nan"),
         "median": statistics.median(rs) if rs else float("nan"),
         "sd": statistics.stdev(rs) if n > 1 else float("nan"),
         "without_best": statistics.fmean(sorted(rs)[:-1]) if n > 1 else float("nan"),
         "max_dd": B1.max_drawdown(rs), "win": sum(r > 0 for r in rs) / n if n else float("nan"),
         "lower": float("nan"), "upper": float("nan")}
    if n >= 2:
        s["lower"] = bootstrap_lower_bound(rs, conf=CONF_LOWER, iters=iters, seed=SEED)
        s["upper"] = bootstrap_upper_bound(rs, conf=CONF_UPPER, iters=iters, seed=SEED)
    s["verdict"] = classify(n, s["lower"], s["upper"], s["without_best"]) if n >= 2 else "INSUFFICIENT"
    return s


# Self-test ---------------------------------------------------------------------

def _sess(highs, lows, start=date(2008, 1, 7)):
    days, d = [], start
    while len(days) < len(highs):
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return {"days": days, "H": list(highs), "L": list(lows)}


def selftest():
    fails = []

    def check(name, cond):
        print(("ok   " if cond else "FAIL ") + name)
        if not cond:
            fails.append(name)

    # Weekly bars and levels -------------------------------------------------------
    s = _sess([1.0] * 20, [0.9] * 20)
    wk = weeks(s)
    check("weekly bars: 20 sessions -> 4 weeks, last session index of week 1 = 4",
          len(wk) == 4 and wk[0][2] == 4 and wk[1][2] == 9)
    H = [1.00] * 30
    H[10] = 1.05
    s = _sess(H, [0.9] * 30)
    lv = [x for x in htf_levels(s) if x["src"] == "D"]
    check("D1 swing at session 10 usable from 14 completed sessions (k=3), expires at 130",
          [(x["price"], x["usable_k"], x["expire_k"]) for x in lv] == [(1.05, 14, 130)])
    H2 = [1.00] * 30
    H2[10] = H2[13] = 1.05
    check("equal highs 3 sessions apart are not a D1 swing",
          [x for x in htf_levels(_sess(H2, [0.9] * 30)) if x["src"] == "D"] == [])
    Hw = [1.00] * 40
    Hw[12] = 1.08                                       # week 2 (sessions 10-14)
    lvw = [x for x in htf_levels(_sess(Hw, [0.9] * 40)) if x["src"] == "W"]
    check("weekly swing in week 2 usable after week 4 completes (25 sessions), expires 14+520",
          [(x["price"], x["usable_k"], x["expire_k"]) for x in lvw] == [(1.08, 25, 534)])

    # Daily trend --------------------------------------------------------------------
    Hs = [1.0] * 40
    Ls = [0.9] * 40
    Hs[5], Hs[15] = 1.10, 1.20
    Ls[10], Ls[20] = 0.80, 0.85
    st = _sess(Hs, Ls)
    tr = trend_by_k(st, 40)
    check("trend 0 until two highs and two lows are usable; +1 once HH and HL are usable (k 24)",
          tr[23] == 0 and tr[24] == 1)
    Ls2 = list(Ls)
    Ls2[20] = 0.75
    check("higher high with a lower low is 0 (mixed)", trend_by_k(_sess(Hs, Ls2), 40)[30] == 0)
    Hs3 = list(Hs)
    Hs3[15] = 1.05
    check("lower high and lower low is -1", trend_by_k(_sess(Hs3, Ls2), 40)[30] == -1)
    check("the mirror flips the trend", trend_by_k(mirror_sess(st), 40)[30] == -1)

    # Events -------------------------------------------------------------------------
    lv = [{"price": 1.0050, "src": "D", "usable_k": 2, "expire_k": 50, "consumed_bar": None},
          {"price": 1.0080, "src": "W", "usable_k": 2, "expire_k": 50, "consumed_bar": None},
          {"price": 1.0200, "src": "D", "usable_k": 2, "expire_k": 50, "consumed_bar": None}]
    kk = [0, 0, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]
    Cl = [1.0000, 1.0000, 1.0000, 1.0060, 1.0040, 1.0090, 1.0095, 1.0100, 1.0100, 1.0100, 1.0100, 1.0100]
    ev, cnt = find_events(Cl, kk, [dict(x) for x in lv])
    check("level not usable before k reaches usable_k (no event at bar 1)", all(e["bar"] >= 2 for e in ev))
    check("event at 3 is a fake (next close back at/below 1.0050)", ev[0]["bar"] == 3 and ev[0]["fake"])
    check("bar 5 crosses two levels: the event takes the highest (1.0080), confirmed at 6",
          ev[1]["bar"] == 5 and ev[1]["level"] == 1.0080 and not ev[1]["fake"])
    check("the confirmation consumes both crossed levels and keeps 1.0200",
          cnt["levels consumed by confirmations"] == 2 and len(ev) == 2)
    ev_eq, _ = find_events([1.0, 1.0, 1.006, 1.005, 1.0], [0, 2, 2, 2, 2],
                           [{"price": 1.0050, "src": "D", "usable_k": 2, "expire_k": 50, "consumed_bar": None}])
    check("a next close exactly at the level is a fake", ev_eq and ev_eq[0]["fake"] is True)
    lv2 = [{"price": 1.0050, "src": "D", "usable_k": 3, "expire_k": 50, "consumed_bar": None}]
    ev2, cnt2 = find_events([1.0, 1.0, 1.006, 1.007, 1.0, 1.006, 1.007], [0, 0, 0, 3, 3, 3, 3], lv2)
    check("a level already exceeded when it becomes usable is consumed, not traded",
          ev2 == [] and cnt2["levels already exceeded when usable"] == 1)
    lv3 = [{"price": 1.0050, "src": "D", "usable_k": 1, "expire_k": 4, "consumed_bar": None}]
    ev3, cnt3 = find_events([1.0, 1.0, 1.0, 1.0, 1.006, 1.007], [1, 1, 2, 3, 4, 4], lv3)
    check("an expired level gives no event", ev3 == [] and cnt3["levels expired unbroken"] == 1)

    # Obstacle -----------------------------------------------------------------------
    obs = [{"price": 1.0200, "usable_k": 5, "expire_k": 50, "consumed_bar": None},
           {"price": 1.0150, "usable_k": 9, "expire_k": 50, "consumed_bar": None},
           {"price": 1.0120, "usable_k": 1, "expire_k": 50, "consumed_bar": 7},
           {"price": 1.0110, "usable_k": 1, "expire_k": 5, "consumed_bar": None}]
    check("obstacle: usable, unexpired, unconsumed -> 1.0200 at k 6", obstacle(obs, 6, 10, 1.0100) == 1.0200)
    check("obstacle: a level consumed after the entry bar still counts", obstacle(obs, 5, 6, 1.0100) == 1.0120)
    check("obstacle: none above", obstacle(obs, 6, 10, 1.0300) is None)
    check("an obstacle before the target blocks; at or beyond it passes; none passes",
          obstacle_blocks(1.0550, 1.0515, 0.00675) and not obstacle_blocks(1.0515 + 0.00675, 1.0515, 0.00675)
          and not obstacle_blocks(1.0600, 1.0515, 0.00675) and not obstacle_blocks(None, 1.0515, 0.00675))

    # Stop and target ----------------------------------------------------------------
    st_ = stop_for(1.0050, 1.0060, 0.0120)       # zone 1.0050 - 0.0030 = 1.0020, minus 15 pips = 1.0005
    check("stop = level - 0.25 ATR - 15 pips", abs(st_ - 1.0005) < 1e-12)
    st_ = stop_for(1.0050, 1.0060, 0.0040)       # 1.0050-0.0010-0.0015 = 1.0025: 35 pips, floor 12, cap 60
    check("stop kept when wider than 0.3 ATR", abs(st_ - 1.0025) < 1e-12)
    st_ = stop_for(1.0050, 1.0060, 0.0200)       # 1.0050-0.0050-0.0015 = 0.9985: 75 pips >= 60 -> kept
    check("0.3 ATR floor not applied when the stop is already wider", abs(st_ - 0.9985) < 1e-12)
    st_ = stop_for(1.0050, 1.0300, 0.0120)       # 295 pips > 180 -> None
    check("stop wider than 1.5 ATR -> no trade", st_ is None)
    st_ = stop_for(1.0050, 1.0060, 0.0300)       # 1.0050-0.0075-0.0015=0.9960: 100 pips >= 90 ok
    check("stop at 1.0 ATR kept", abs(st_ - 0.9960) < 1e-12)
    st4 = stop_for(1.0100, 1.0100, 0.0200)       # 1.0100-0.0050-0.0015 = 1.0035: 65 pips >= 60, kept
    check("C entry at the level: risk = 0.25 ATR + 15 pips", abs((1.0100 - st4) - 0.0065) < 1e-12)
    st5 = stop_for(1.0100, 1.0100, 0.0040)       # 1.0100-0.0010-0.0015 = 1.0075: 25 pips, floor 12
    st6 = stop_for(1.0100, 1.0160, 0.0040)       # zone stop 1.0075: 85 pips > 60 -> None
    check("a far entry above a small-ATR level is too wide", st6 is None and abs(st5 - 1.0075) < 1e-12)
    st7 = stop_for(1.0100, 1.0101, 0.0400)       # zone stop 0.9985: 116 pips; floor 120 -> widened to 1.0101-0.0120
    check("the 0.3 ATR floor widens a stop of 116 pips to 120", abs(st7 - (1.0101 - 0.0120)) < 1e-12)
    check("TP distance = m(d+sp)+sp: 70-pip stop, 5-pip spread, 1.5R -> 117.5 pips",
          abs(target_distance(1.5, 0.0070, 0.0005) - 0.01175) < 1e-12)

    # Management ---------------------------------------------------------------------
    n = 200
    base = 1.0100

    def flat():
        return [base] * n, [base + 0.0010] * n, [base - 0.0010] * n, [base] * n

    O, H, L, Cl = flat()
    L[5] = 0.9990                                     # stop 1.0000 (d 100 pips)
    g = manage(O, H, L, Cl, 0, base, 1.0000, 0.0150)
    check("full stop-out is -1R", g["raw"] == -1.0 and g["reason"] == "stop")
    O, H, L, Cl = flat()
    H[3] = 1.0205                                     # +1R hit at bar 3
    L[6] = 1.0095                                     # back through breakeven at bar 6
    g = manage(O, H, L, Cl, 0, base, 1.0000, 0.0150)
    check("half off at +1R, rest out at breakeven: +0.5R", abs(g["raw"] - 0.5) < 1e-12 and g["reason"] == "breakeven")
    g = manage(O, H, L, Cl, 0, base, 1.0000, 0.0150, partial=False)
    check("no partial: +1R then breakeven = 0R", abs(g["raw"]) < 1e-12)
    O, H, L, Cl = flat()
    H[3] = 1.0260                                     # +1R and the target (150 pips) on bar 3
    g = manage(O, H, L, Cl, 0, base, 1.0000, 0.0150)
    check("half at +1R and half at target on one bar: 0.5 + 0.5*1.5 = 1.25R",
          abs(g["raw"] - 1.25) < 1e-12 and g["reason"] == "target")
    O, H, L, Cl = flat()
    H[3], L[3] = 1.0260, 0.9990                       # stop and target on one bar
    g = manage(O, H, L, Cl, 0, base, 1.0000, 0.0150)
    check("stop and target on one bar: the stop comes first (-1R)", g["raw"] == -1.0)
    O, H, L, Cl = flat()
    H[3] = 1.0260
    L[3] = 1.0095                                     # BE not active on the bar that reaches +1R
    g = manage(O, H, L, Cl, 0, base, 1.0000, 0.0300)  # target 300 pips: not hit
    check("breakeven starts on the bar after +1R", g["reason"] != "breakeven" or g["exits"][-1][0] > 3)
    O, H, L, Cl = flat()
    H[3] = 1.0300                                     # +2R high: trail at 1.0300 - 0.0050 = 1.0250
    L[4] = 1.0249
    g = manage(O, H, L, Cl, 0, base, 1.0000, 0.0400)
    check("trailing 0.5R behind the best high after +1.5R: 0.5 + 0.5*1.5 = 1.25R",
          abs(g["raw"] - (0.5 + 0.5 * 1.5)) < 1e-9 and g["reason"] == "trail")
    O, H, L, Cl = flat()
    Cl[120] = 1.0150
    g = manage(O, H, L, Cl, 0, base, 1.0000, 0.0400)
    check("time exit at the close of bar entry+120: +0.5R", abs(g["raw"] - 0.5) < 1e-12 and g["reason"] == "time")
    L2 = list(L)
    L2[121] = 0.9
    L3 = list(L)
    L3[120] = 0.9990
    check("a stop touch on bar entry+120 is inside the hold", manage(O, H, L3, Cl, 0, base, 1.0000, 0.04)["reason"] == "stop")
    check("bar 121 is outside the hold", manage(O, H, L2, Cl, 0, base, 1.0000, 0.04)["reason"] == "time")
    check("ungraded when the hold runs past the data", manage(O, H, L, Cl, 80, base, 1.0, 0.04) is None)
    O, H, L, Cl = flat()
    H[0] = 1.0300                                     # fill bar high ignored for C
    g = manage(O, H, L, Cl, 0, base, 1.0000, 0.0150, at_close=False)
    check("C fill bar: favourable moves ignored (no target on the fill bar)", g["reason"] == "time")
    O, H, L, Cl = flat()
    L[0] = 0.9990
    g = manage(O, H, L, Cl, 0, base, 1.0000, 0.0150, at_close=False)
    check("C fill bar stop: -1R, gap -1R", g["raw"] == -1.0 and g["gap_r"] == -1.0)
    O, H, L, Cl = flat()
    O[4], L[4] = 0.9950, 0.9940
    g = manage(O, H, L, Cl, 0, base, 1.0000, 0.0150)
    check("gap through the stop: -1R, gap loss -1.5R", g["raw"] == -1.0 and abs(g["gap_r"] + 1.5) < 1e-9)

    # Costs ---------------------------------------------------------------------------
    rates = {BASE: [(date(2000, 1, 1), 5.0)], QUOTE: [(date(2000, 1, 1), 6.0)]}
    opens = [datetime(2008, 1, 7, 10, tzinfo=UTC) + timedelta(hours=i) for i in range(200)]
    fr, nts = financing_r(1, opens, 0, True, [(10, 0.5, "1R partial"), (30, 0.5, "target")], 2.0, 100.0, rates)
    # half exits Mon 21:00Z (before 17:00 NY? 16:00 NY: 0 nights); half Tue 17:00Z (1 night)
    check("financing weighted by halves: 0.5 night at -2%/yr", abs(nts - 0.5) < 1e-12
          and abs(fr * 100.0 + 0.5 * 2.0 * 0.02 / 365 / PIP) < 1e-9)
    check("USED: no financing (rates None)", financing_r(1, opens, 0, True, [(30, 1.0, "time")], 2.0, 100.0, None)
          == (0.0, 0.0))
    check("spreads: era 2009 10, used 3.0, flat 5.1",
          spread_pips("era", date(2009, 5, 1)) == 10.0 and spread_pips("used", date(2024, 1, 1)) == 3.0
          and spread_pips(5.1, date(2024, 1, 1)) == 5.1)

    # Spans ---------------------------------------------------------------------------
    for t, sp_, name in ((B1.BLOCK_START, "STUDY", "embargo start refused for STUDY"),
                         (BLOCK_END - timedelta(hours=1), "USED", "a sealed bar refused for USED"),
                         (datetime(2026, 9, 10, 12, tzinfo=UTC), "USED", "2026-09-10 refused for USED")):
        try:
            check_span([t], sp_)
            check(name, False)
        except RuntimeError:
            check(name, True)
    check_span([BLOCK_END], "USED")

    # Episodes and verdict ------------------------------------------------------------
    fake = [{"bar": x, "side": 1} for x in (0, 50, 119, 120, 239, 240, 500)]
    got = [t["bar"] for t in episodes(fake)]
    check("episodes collapse on a 120-bar horizon (count_episodes)",
          got == count_episodes([0, 50, 119, 120, 239, 240, 500], 120) == [0, 120, 240, 500])
    check("Bonferroni over 4 cells: 0.9875", abs(CONF_LOWER - 0.9875) < 1e-12 and len(CELLS) == 4)
    check("verdict boundaries", classify(19, 1, 2, 1) == "INSUFFICIENT" and classify(20, 0.01, 1, 0.01) == "SUPPORTED"
          and classify(20, -1, 0.1499, -1) == "REFUTED" and classify(20, -1, 0.15, -1) == "INCONCLUSIVE")
    rng = random.Random(11)
    check("a known +0.6R edge (N 300) is SUPPORTED",
          summarize([max(-1.0, rng.gauss(0.6, 1.2)) for _ in range(300)], iters=2000)["verdict"] == "SUPPORTED")

    # End to end on synthetic data: a D1 swing high broken in an up-trend ---------------
    ok, why = _end_to_end()
    check("end to end: one B trade taken in an up-trend, skipped when the trend filter sees a down-trend" + why, ok)

    print("SELFTEST OK" if not fails else f"SELFTEST FAILED: {len(fails)}")
    return not fails


def _end_to_end():
    """Sessions with HH/HL structure, a D1 swing high at 1.0500, then H1 bars that break it
    with two closes and run 2R. Long side only."""
    Hs = [1.02] * 60
    Ls = [0.995] * 60
    Hs[5], Ls[10], Hs[15], Ls[20] = 1.03, 0.97, 1.05, 0.99     # HH 1.03 -> 1.05, HL 0.97 -> 0.99
    Hs[16:60] = [1.04] * 44
    sess = _sess(Hs, Ls)
    opens, h1 = [], {}
    d1 = {}
    for i, day in enumerate(sess["days"]):
        t0 = datetime(day.year, day.month, day.day, 0, tzinfo=UTC) - timedelta(hours=2)   # 22:00Z prior day
        d1[t0] = (1.0, Hs[i], Ls[i], 1.0)
        for h in range(24):
            opens.append(t0 + timedelta(hours=h))
    rows = []
    for idx, t in enumerate(opens):
        rows.append((1.0400, 1.0410, 1.0390, 1.0400))
    start = 30 * 24                                    # session 30: swing usable (k >= 19), trend up (k >= 24)
    seq = [(1.0480, 1.0498, 1.0470, 1.0490), (1.0490, 1.0515, 1.0485, 1.0510),
           (1.0510, 1.0520, 1.0505, 1.0515)]
    for i, r in enumerate(seq):
        rows[start + i] = r
    for i in range(start + 3, len(rows)):
        rows[i] = (1.0520, 1.0530, 1.0515, 1.0520)
    rows[start + 10] = (1.0520, 1.0800, 1.0515, 1.0700)
    for i, t in enumerate(opens):
        h1[t] = rows[i]
    bars, ss = prepare(h1, d1)
    bars["atr"] = [0.0040] * len(bars["O"])
    t, sk, ev, _ = side_trades(bars, ss, 1, None, "B", 1.5, 3.0)
    ok1 = len(t) == 1 and t[0]["bar"] == start + 2 and t[0]["reason"] == "target"
    ss_down = dict(ss)
    ss_down["L"] = list(ss["L"])
    ss_down["L"][20] = 0.96                            # lower low -> mixed, no trade
    t2, sk2, _, _ = side_trades(bars, ss_down, 1, None, "B", 1.5, 3.0)
    ok2 = t2 == [] and sk2["daily trend not aligned"] == 1
    return ok1 and ok2, "" if ok1 and ok2 else f" [got {len(t)} trades, skips {dict(sk)}; {dict(sk2)}]"


# Stages ------------------------------------------------------------------------

def counts(archive_dir):
    rates = B1.load_rates()
    for span, mode, rt in (("STUDY", "era", rates), ("USED", "used", None)):
        bars, sess = load_span(archive_dir, span)
        print(f"\n# {span}: GBP_AUD H1 bars {len(bars['O'])}, {bars['opens'][0].isoformat()} -> "
              f"{bars['opens'][-1].isoformat()}; sessions {len(sess['days'])}")
        first = True
        for entry, m in CELLS:
            tr, sk, ev, ec = cell(bars, sess, rt, entry, m, mode)
            if first:
                for side, name in ((1, "long"), (-1, "short")):
                    e = ev[side]
                    fk = sum(x["fake"] for x in e)
                    print(f"- {name}: events {len(e)}, fakes {fk} ({fk / len(e):.1%}), confirmations {len(e) - fk}; "
                          + "; ".join(f"{k} {v}" for k, v in sorted(ec[side].items())))
                first = False
            ep = episodes(tr)
            print(f"- cell {entry}-{m}: graded trades {len(tr)}; episodes {len(ep)} (long "
                  f"{sum(x['side'] == 1 for x in ep)}, short {sum(x['side'] == -1 for x in ep)}); skips "
                  + "; ".join(f"{k} {v}" for k, v in sorted(sk.items())))
            if span == "STUDY":
                yr = Counter(x["day"].year for x in ep)
                print("  episodes by year: " + ", ".join(f"{y} {yr[y]}" for y in sorted(yr)))
                print(f"  power at N {len(ep)}: +0.15R {power_at_n(0.15, SD_ASSUMED, len(ep), alpha=ALPHA):.3f}; "
                      f"smallest edge at 80% {min_detectable_edge(SD_ASSUMED, max(len(ep), 1), alpha=ALPHA):.3f}R")
    print(f"\nN required for +0.15R at 80% power (alpha {ALPHA:.4f}): {n_required(0.15, SD_ASSUMED, alpha=ALPHA)}")


def _fmt(s):
    return (f"N {s['n']} | mean {s['mean']:+.3f}R | median {s['median']:+.3f}R | SD {s['sd']:.3f} | "
            f"lower {s['lower']:+.3f} | upper {s['upper']:+.3f} | without best {s['without_best']:+.3f} | "
            f"win {s['win']:.1%} | max DD {s['max_dd']:.1f}R")


def _short(rs):
    if len(rs) < 2:
        return f"N {len(rs)}"
    return f"N {len(rs)} | mean {statistics.fmean(rs):+.3f}R | median {statistics.median(rs):+.3f}R"


def full(archive_dir, report):
    if os.path.exists(report):
        raise SystemExit(f"refused: {report} already exists (the full run happens once)")
    rates = B1.load_rates()
    out = []
    p = out.append
    p("# BCS-2 result: weekly/daily level breaks, daily trend, obstacle check, 1.5R/2.5R targets (GBP/AUD)")
    p("")
    p(f"Spec: docs/specs/htf_breakout_study_spec.md. Verdict on STUDY (2005-2013) episode R after era spread and "
      f"financing. Bonferroni one-sided lower bound at {CONF_LOWER:.4f} (4 cells), 90% upper bound for REFUTED "
      f"(bar +0.15R), {RESAMPLES} resamples, seed {SEED}. USED (2021-2026) is a learning-only replication.")
    p("")
    bars, sess = load_span(archive_dir, "STUDY")
    p("## Verdicts (STUDY, era spread + financing, episodes)")
    p("")
    for entry, m in CELLS:
        tr, sk, ev, ec = cell(bars, sess, rates, entry, m, "era")
        e = episodes(tr)
        s = summarize([t["adj"] for t in e])
        p(f"### Cell {entry}-{m}: **{s['verdict']}**")
        p("")
        p(f"- {_fmt(s)}")
        if e:
            p(f"- exits: " + ", ".join(f"{k} {v}" for k, v in sorted(Counter(t["reason"] for t in e).items()))
              + f"; mean risk {statistics.fmean(t['risk_pips'] for t in e):.1f} pips; mean spread "
              f"{statistics.fmean(t['spread_r'] for t in e):+.3f}R; mean financing {statistics.fmean(t['fin_r'] for t in e):+.4f}R; "
              f"mean nights {statistics.fmean(t['nights'] for t in e):.2f}")
            p(f"- power at this N: +0.15R {power_at_n(0.15, SD_ASSUMED, len(e), alpha=ALPHA):.3f}; smallest edge at "
              f"80% {min_detectable_edge(SD_ASSUMED, len(e), alpha=ALPHA):.3f}R")
            p(f"- before costs: {_short([t['raw'] for t in e])}")
            p(f"- stops at the gap open: {_short([t['gap_adj'] for t in e])}")
            p(f"- long: {_short([t['adj'] for t in e if t['side'] == 1])}; short: "
              f"{_short([t['adj'] for t in e if t['side'] == -1])}")
            p(f"- level source D: {_short([t['adj'] for t in e if t['src'] == 'D'])}; W: "
              f"{_short([t['adj'] for t in e if t['src'] == 'W'])}")
            for name, a, b in B1.SUBPERIODS:
                p(f"- {name}: {_short([t['adj'] for t in e if a <= t['day'] <= b])}")
            yr = defaultdict(list)
            for t in e:
                yr[t["day"].year].append(t["adj"])
            p("- by year: " + "; ".join(f"{y} N {len(v)} {statistics.fmean(v):+.3f}R" for y, v in sorted(yr.items())))
        p("- skips: " + "; ".join(f"{k} {v}" for k, v in sorted(sk.items())))
        for sp in FLAT_SPREADS:
            t2, _, _, _ = cell(bars, sess, rates, entry, m, sp)
            p(f"- flat {sp} pips + financing: {_fmt(summarize([t['adj'] for t in episodes(t2)]))}")
        t3, _, _, _ = cell(bars, sess, rates, entry, m, "era", partial=False)
        p(f"- no partial (full size to target, breakeven at +1R): {_short([t['adj'] for t in episodes(t3)])}")
        t4, _, _, _ = cell(bars, sess, rates, entry, m, "era", use_trend=False)
        p(f"- without the trend filter: {_short([t['adj'] for t in episodes(t4)])}")
        t5, _, _, _ = cell(bars, sess, rates, entry, m, "era", use_obstacle=False)
        p(f"- without the obstacle check: {_short([t['adj'] for t in episodes(t5)])}")
        t6, _, _, _ = cell(bars, sess, rates, entry, m, "era", use_trend=False, use_obstacle=False)
        p(f"- without either filter: {_short([t['adj'] for t in episodes(t6)])}")
        p("")
    p("## Secondary: level-break fake rate (STUDY)")
    p("")
    _, _, ev, _ = cell(bars, sess, rates, "B", 1.5, "era")
    allev = ev[1] + ev[-1]
    fk = sum(x["fake"] for x in allev)
    p(f"- {fk} of {len(allev)} first closes beyond a weekly/daily level were fakes ({fk / len(allev):.1%}); "
      f"D levels {sum(x['fake'] for x in allev if x['src'] == 'D')} of {sum(x['src'] == 'D' for x in allev)}, "
      f"W levels {sum(x['fake'] for x in allev if x['src'] == 'W')} of {sum(x['src'] == 'W' for x in allev)}.")
    p("")
    p("## Replication on USED 2021-04-27 -> 2026-09-09 (learning only, never proof; no financing)")
    p("")
    ub, us = load_span(archive_dir, "USED")
    for entry, m in CELLS:
        for mode in ("used", 5.1):
            tr, _, _, _ = cell(ub, us, None, entry, m, mode)
            p(f"- {entry}-{m}, spread {USED_SPREAD if mode == 'used' else mode}: {_short([t['adj'] for t in episodes(tr)])}")
    text = "\n".join(out) + "\n"
    with open(report, "w") as fh:
        fh.write(text)
    print(text, end="")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "selftest":
        sys.exit(0 if selftest() else 1)
    if len(sys.argv) == 3 and sys.argv[1] == "counts":
        counts(sys.argv[2])
    elif len(sys.argv) == 4 and sys.argv[1] == "full":
        full(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit(__doc__)
