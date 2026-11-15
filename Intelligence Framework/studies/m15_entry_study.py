"""Pre-registered test (BCS-3): do 15-minute entries change the breakout results?
(docs/specs/m15_entry_study_spec.md)

Same levels, stops, filters, targets and management as BCS-1 (R43) and BCS-2
(R44); only the entry moves to the 15-minute chart:
  after the hourly two-close confirmation, wait (up to 48 M15 bars) for price to
  touch the level, then enter at the close of the first M15 bar that closes back
  beyond the level in the trade's direction (a bullish bar for longs).
Cells, GBP_AUD, long and short pooled:
  H1     BCS-1 hourly swing levels, stop level - 0.25 ATR, 24-hour timed exit
  HTF-1.5, HTF-2.5   BCS-2 daily/weekly levels, trend + obstacle filters,
         its stop recipe, 1.5R / 2.5R targets with the management rules
Data: STUDY span only: the research archive (H1, D1) and the verified M15 file.

usage:
  python3 -I m15_entry_study.py selftest
  python3 -I m15_entry_study.py counts <archive_dir> <m15_dir>
  python3 -I m15_entry_study.py full <archive_dir> <m15_dir> <report_md>
"""
import bisect
import os
import random
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "foundation", "tools"))
import breakout_confirmation_study as B1  # noqa: E402  BCS-1 (frozen)
import htf_breakout_study as S  # noqa: E402  BCS-2 (frozen)
import history_study_convert as C  # noqa: E402
import m15_study_data as MD  # noqa: E402
from shadow_cost_regrade import rollover_nights  # noqa: E402
from episodes import count_episodes  # noqa: E402
from power_check import (bootstrap_lower_bound, bootstrap_upper_bound,  # noqa: E402
                         min_detectable_edge, n_required, power_at_n)

UTC = timezone.utc
PAIR, BASE, QUOTE, PIP = B1.PAIR, B1.BASE, B1.QUOTE, B1.PIP
M15_HASH = "83ef82bb1bf885895c8ef33d998d02bc3569a7d02434d21a80e36531b97925b6"
BAR = timedelta(minutes=15)
WINDOW = 48                     # M15 bars after the confirming hourly close (12 hours, as C's window)
H1_STOP_ATR = B1.STOP_ATR       # 0.25 (BCS-1 stop)
H1_HOLD = 4 * B1.HORIZON        # 96 M15 bars = BCS-1's 24 hours
HTF_HOLD = 4 * S.MAX_HOLD       # 480 M15 bars = BCS-2's 120 hours
TIGHT_BUFFER_PIPS = 15.0        # secondary: stop below the M15 retest low
CELLS = (("H1", None), ("HTF", 1.5), ("HTF", 2.5))
ALPHA = 0.05 / len(CELLS)
CONF_LOWER = 1 - ALPHA          # 0.98333...
CONF_UPPER, REFUTE_BAR = 0.90, 0.15
RESAMPLES, SEED, MIN_N, SD_ASSUMED = 20000, 7, 20, 1.2
STOP_KINDS = ("stop", "breakeven", "trail")
REFERENCE = {"H1": "BCS-1 (R43): B −0.106R, C (hourly retest) −0.094R",
             "HTF-1.5": "BCS-2 (R44): B −0.346R, C (hourly retest) −0.280R",
             "HTF-2.5": "BCS-2 (R44): B −0.346R, C (hourly retest) −0.280R"}


# Data ------------------------------------------------------------------------------

def load_all(archive_dir, m15_dir):
    import research_archive as RA
    B1.verify_hashes(archive_dir)
    check_m15(m15_dir)
    h1 = RA.load(archive_dir, PAIR, "H1", {"STUDY"})
    d1 = RA.load(archive_dir, PAIR, "D", {"STUDY"})
    m15 = MD.load(m15_dir)
    for x in (h1, d1, m15):
        B1.check_window(x)
    hb, sess = S.prepare(h1, d1)
    mo = sorted(m15)
    mb = {"opens": mo, "O": [m15[t][0] for t in mo], "H": [m15[t][1] for t in mo],
          "L": [m15[t][2] for t in mo], "C": [m15[t][3] for t in mo],
          "atr": B1.bar_atr(mo, B1.session_table(d1))}
    return hb, sess, mb


def check_m15(m15_dir, pinned=M15_HASH):
    got = MD.sha(os.path.join(m15_dir, MD.NAME))
    if got != pinned:
        raise RuntimeError(f"{MD.NAME}: sha256 {got} differs from the pinned {pinned}: refused")


def h1_index(hb, t):
    """Index of the H1 bar containing time t."""
    return bisect.bisect_right(hb["opens"], t) - 1


def first_m15_after(mb, t):
    return bisect.bisect_left(mb["opens"], t)


# The 15-minute trigger (long side; the short side is the mirror) ----------------------

def trigger(O, H, L, Cl, s, lvl, cancel, window=WINDOW):
    """From M15 bar s, up to `window` bars: cancel if a low reaches the cancel line;
    a touch is a low at or below the level; the trigger is the first bar from the touch on
    that closes above the level and above its own open. Returns (bar, lowest low since the
    touch) or (None, reason)."""
    lo = None
    for b in range(s, s + window):
        if b >= len(Cl):
            return None, "end of data"
        if L[b] <= cancel:
            return None, "went through the stop line first"
        if L[b] <= lvl or lo is not None:
            lo = L[b] if lo is None else min(lo, L[b])
        if lo is not None and Cl[b] > lvl and Cl[b] > O[b]:
            return b, lo
    return None, "no retest trigger in 12 hours"


def financing_r(side, opens, e, exits, entry_price, d_pips, rates):
    """As BCS-1/2, with 15-minute bars: entry at the close of bar e."""
    if rates is None:
        return 0.0, 0.0
    t0 = opens[e] + BAR
    day = C.session_day(opens[e])
    net = side * (B1.rate_on(rates, BASE, day) - B1.rate_on(rates, QUOTE, day)) - B1.MARKUP
    pips = nights = 0.0
    for b, size, kind in exits:
        t1 = opens[b] if kind in STOP_KINDS else opens[b] + BAR
        n = rollover_nights(t0, t1)
        nights += size * n
        pips += size * entry_price * net / 100 * n / 365 / PIP
    return pips / d_pips, nights


def _mirror(b):
    out = dict(b)
    out["O"], out["H"], out["L"], out["C"] = ([-x for x in b["O"]], [-x for x in b["L"]],
                                              [-x for x in b["H"]], [-x for x in b["C"]])
    return out


def side_trades(hb, sess, mb, side, rates, family, m, mode="era", stop_kind="zone", use_filters=True,
                partial=True):
    h, mm = (hb, mb) if side == 1 else (_mirror(hb), _mirror(mb))
    ss = sess if side == 1 else S.mirror_sess(sess)
    if family == "H1":
        events, _ = B1.find_events(h["C"], h["H"])
        levels = trend = None
    else:
        levels = S.htf_levels(ss)
        events, _ = S.find_events(h["C"], h["k"], levels)
        trend = S.trend_by_k(ss, len(ss["days"]))
    O, H, L, Cl = mm["O"], mm["H"], mm["L"], mm["C"]
    trades, skips = [], Counter()
    for ev in events:
        if ev["fake"] is not False:
            continue
        skips["confirmations"] += 1
        j, lvl = ev["bar"], ev["level"]
        s = first_m15_after(mm, h["opens"][j + 1] + timedelta(hours=1))
        if s >= len(Cl) or mm["atr"][s] is None:
            skips["ATR warm-up or end of data"] += 1
            continue
        a0 = mm["atr"][s]
        cancel = lvl - H1_STOP_ATR * a0 if family == "H1" else lvl - S.ZONE_ATR * a0 - S.BUFFER_PIPS * PIP
        e, lo = trigger(O, H, L, Cl, s, lvl, cancel)
        if e is None:
            skips[f"no entry: {lo}"] += 1
            continue
        skips["triggered"] += 1
        px, atr = Cl[e], mm["atr"][e]
        if atr is None:
            skips["ATR warm-up"] += 1
            continue
        hi1 = h1_index(h, mm["opens"][e])
        k = h["k"][hi1]
        if family == "HTF" and use_filters and trend[k] != 1:
            skips["daily trend not aligned"] += 1
            continue
        if stop_kind == "tight":
            stop = lo - TIGHT_BUFFER_PIPS * PIP
            if px - stop > S.MAX_STOP_ATR * atr:
                skips["stop wider than 1.5 ATR"] += 1
                continue
        elif family == "H1":
            stop = lvl - H1_STOP_ATR * atr
        else:
            stop = S.stop_for(lvl, px, atr)
            if stop is None:
                skips["stop wider than 1.5 ATR"] += 1
                continue
        d = px - stop
        day = C.session_day(mm["opens"][e])
        sp = S.spread_pips(mode, day) * PIP
        if family == "H1":
            g = B1.grade_close_entry(O, L, Cl, e, px, stop, horizon=H1_HOLD)
            if g is not None:
                g = {"raw": g["raw"], "gap_r": g["gap_r"], "reason": "stop" if g["stopped"] else "time",
                     "exits": [(g["exit_bar"], 1.0, "stop" if g["stopped"] else "time")]}
        else:
            T = S.target_distance(m, d, sp)
            if use_filters and S.obstacle_blocks(S.obstacle(levels, k, hi1, px), px, T):
                skips["first obstacle inside the target"] += 1
                continue
            g = S.manage(O, H, L, Cl, e, px, stop, T, at_close=True, partial=partial, max_hold=HTF_HOLD)
        if g is None:
            skips["ungraded at end of data"] += 1
            continue
        fin_r, nights = financing_r(side, mm["opens"], e, g["exits"], abs(px), d / PIP, rates)
        spread_r = -(sp / PIP) / (d / PIP)
        trades.append({"bar": e, "side": side, "day": day, "raw": g["raw"], "gap_raw": g["gap_r"],
                       "reason": g["reason"], "risk_pips": d / PIP, "spread_r": spread_r, "fin_r": fin_r,
                       "nights": nights, "wait": e - s, "adj": g["raw"] + spread_r + fin_r,
                       "gap_adj": g["gap_r"] + spread_r + fin_r})
    return trades, skips


def cell(hb, sess, mb, rates, family, m, **kw):
    out, sk = [], Counter()
    for side in (1, -1):
        t, s = side_trades(hb, sess, mb, side, rates, family, m, **kw)
        out += t
        sk.update(s)
    return out, sk


def episodes(trades, family):
    return B1.episodes(trades, horizon=H1_HOLD if family == "H1" else HTF_HOLD)


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

def _hours(rows, start):
    return {start + timedelta(hours=i): r for i, r in enumerate(rows)}


def _split(h1):
    """Four identical M15 bars per H1 bar (their aggregate equals the H1 bar)."""
    return {t + i * BAR: v for t, v in h1.items() for i in range(4)}


def _bars(d):
    ts = sorted(d)
    return {"opens": ts, "O": [d[t][0] for t in ts], "H": [d[t][1] for t in ts], "L": [d[t][2] for t in ts],
            "C": [d[t][3] for t in ts]}


def _h1_case(override):
    """BCS-1 style: hourly swing high 1.0050 at bar 10, event at 16, confirmation at 17,
    then M15 bars after the confirming close with `override` {offset: (o, h, l, c)}."""
    flat = (1.0000, 1.0010, 0.9990, 1.0000)
    rows = [flat] * 10 + [(1.0000, 1.0050, 0.9995, 1.0040)] + [flat] * 4
    rows += [(1.0040, 1.0049, 1.0030, 1.0045), (1.0045, 1.0056, 1.0040, 1.0055),
             (1.0055, 1.0060, 1.0052, 1.0058)]
    rows += [(1.0060, 1.0062, 1.0058, 1.0060)] * 40
    start = datetime(2008, 1, 8, 0, tzinfo=UTC)
    h1 = _hours(rows, start)
    m15 = _split(h1)
    t0 = start + timedelta(hours=18)                     # confirming bar 17 closes at hour 18
    for off, v in override.items():
        m15[t0 + off * BAR] = v
    hb, mb = _bars(h1), _bars(m15)
    hb["k"] = [0] * len(hb["O"])
    hb["atr"] = [0.0040] * len(hb["O"])
    mb["atr"] = [0.0040] * len(mb["O"])
    return hb, mb, {"days": [], "H": [], "L": []}, t0


def selftest():
    fails = []

    def check(name, cond):
        print(("ok   " if cond else "FAIL ") + name)
        if not cond:
            fails.append(name)

    # Trigger --------------------------------------------------------------------------
    O = [1.0060] * 60
    H = [1.0065] * 60
    L = [1.0055] * 60
    Cl = [1.0060] * 60
    O2, L2, Cl2 = list(O), list(L), list(Cl)
    O2[3], L2[3], Cl2[3] = 1.0055, 1.0049, 1.0052                 # touch, bearish close above: no trigger
    O2[5], L2[5], Cl2[5] = 1.0052, 1.0051, 1.0056                 # bullish close above: trigger
    check("touch then the first bullish close above the level triggers; low since touch tracked",
          trigger(O2, H, L2, Cl2, 0, 1.0050, 1.0040) == (5, 1.0049))
    O3, L3, Cl3 = list(O), list(L), list(Cl)
    O3[2], L3[2], Cl3[2] = 1.0052, 1.0048, 1.0055                 # touch and bullish close on one bar
    check("the touch bar itself can trigger (a rejection candle)", trigger(O3, H, L3, Cl3, 0, 1.0050, 1.0040) == (2, 1.0048))
    O4, L4, Cl4 = list(O), list(L), list(Cl)
    O4[1], L4[1], Cl4[1] = 1.0049, 1.0045, 1.0050                 # close exactly at the level: not above
    check("a close exactly at the level is not a trigger", trigger(O4, H, L4, Cl4, 0, 1.0050, 1.0040)[0] is None)
    check("no touch, no trigger (bullish closes above without a retest)",
          trigger(O, H, L, [1.0062] * 60, 0, 1.0050, 1.0040)[0] is None)
    L5 = list(L)
    L5[4] = 1.0040
    check("a low at the stop line before any trigger cancels",
          trigger(O, H, L5, Cl, 0, 1.0050, 1.0040) == (None, "went through the stop line first"))
    O6, L6, Cl6 = list(O), list(L), list(Cl)
    O6[47], L6[47], Cl6[47] = 1.0052, 1.0049, 1.0055
    check("a trigger on bar s+47 is inside the 48-bar window", trigger(O6, H, L6, Cl6, 0, 1.0050, 1.0040)[0] == 47)
    O7, L7, Cl7 = list(O), list(L), list(Cl)
    O7[48], L7[48], Cl7[48] = 1.0052, 1.0049, 1.0055
    check("bar s+48 is outside the window", trigger(O7, H, L7, Cl7, 0, 1.0050, 1.0040)[0] is None)
    check("window running off the data", trigger(O[:10], H[:10], L[:10], Cl[:10], 0, 1.0050, 1.0040)
          == (None, "end of data"))

    # H1 family end to end ---------------------------------------------------------------
    ov = {0: (1.0058, 1.0060, 1.0052, 1.0054), 1: (1.0054, 1.0055, 1.0049, 1.0051),
          2: (1.0051, 1.0056, 1.0050, 1.0055)}
    hb, mb, ss, t0 = _h1_case(ov)
    tr, sk = side_trades(hb, ss, mb, 1, None, "H1", None)
    e_expect = mb["opens"].index(t0 + 2 * BAR)
    check("H1 family: entry at the trigger bar's close (1.0055), first M15 after the confirming close",
          len(tr) == 1 and tr[0]["bar"] == e_expect and tr[0]["wait"] == 2)
    check("H1 family stop = level - 0.25 ATR: risk 15 pips", abs(tr[0]["risk_pips"] - 15.0) < 1e-6)
    check("H1 family timed exit after 96 M15 bars at 1.0060: (1.0060 - 1.0055) / 0.0015 = +0.333R",
          abs(tr[0]["raw"] - (1.0060 - 1.0055) / 0.0015) < 1e-9 and tr[0]["reason"] == "time")
    trt, _ = side_trades(hb, ss, mb, 1, None, "H1", None, stop_kind="tight")
    check("tight stop = lowest low since the touch (1.0049) - 15 pips: risk 21 pips",
          abs(trt[0]["risk_pips"] - 21.0) < 1e-6)
    ov2 = dict(ov)
    ov2[60] = (1.0060, 1.0062, 1.0039, 1.0050)                     # stop 1.0040 hit 58 bars after entry
    hb2, mb2, ss2, _ = _h1_case(ov2)
    tr2, _ = side_trades(hb2, ss2, mb2, 1, None, "H1", None)
    check("H1 family: stop checked on M15 bars inside the 96-bar hold", tr2[0]["raw"] == -1.0)
    ov3 = dict(ov)
    ov3[2 + 97] = (1.0060, 1.0062, 1.0039, 1.0050)                 # entry+97: outside the hold
    hb3, mb3, ss3, _ = _h1_case(ov3)
    check("a stop touch on M15 bar entry+97 is outside the hold",
          side_trades(hb3, ss3, mb3, 1, None, "H1", None)[0][0]["reason"] == "time")
    hbm = {**_mirror_real(hb), "k": hb["k"], "atr": hb["atr"]}
    mbm = {**_mirror_real(mb), "atr": mb["atr"]}
    trm, _ = side_trades(hbm, ss, mbm, -1, None, "H1", None)
    check("the short mirror gives the same raw R", len(trm) == 1 and abs(trm[0]["raw"] - tr[0]["raw"]) < 1e-9)
    hbn, mbn, ssn, _ = _h1_case({k: (1.0060, 1.0062, 1.0055, 1.0060) for k in range(48)})
    trn, skn = side_trades(hbn, ssn, mbn, 1, None, "H1", None)
    check("no trade when no M15 bar retests the level within 48 bars",
          trn == [] and skn["no entry: no retest trigger in 12 hours"] == 1)

    # HTF family end to end ---------------------------------------------------------------
    ok, why = _htf_case()
    check("HTF family: trend + stop recipe + obstacle + target on M15; mixed trend skipped" + why, ok)

    # Costs ---------------------------------------------------------------------------
    rates = {BASE: [(date(2000, 1, 1), 5.0)], QUOTE: [(date(2000, 1, 1), 6.0)]}
    opens = [datetime(2008, 1, 7, 21, 30, tzinfo=UTC) + i * BAR for i in range(20)]
    fr, n = financing_r(1, opens, 0, [(3, 1.0, "time")], 2.0, 50.0, rates)
    # entry at 21:45Z (16:45 NY); exit at the close of 22:15Z bar = 22:30Z: the 17:00 NY rollover is inside
    check("15-minute entry instant: a rollover 15 minutes after entry is charged", n == 1)
    fr2, n2 = financing_r(1, opens, 2, [(3, 1.0, "time")], 2.0, 50.0, rates)
    check("entry at the 22:00Z bar's close (17:15 NY): that rollover is not charged", n2 == 0)
    check("financing by hand: -2%/yr, 1 night, 50-pip risk",
          abs(fr * 50.0 + 2.0 * 0.02 / 365 / PIP) < 1e-9)
    fr3, n3 = financing_r(1, opens, 1, [(3, 1.0, "time")], 2.0, 50.0, rates)
    check("entry at the close of the 21:45Z bar (17:00 NY exactly): that rollover is not charged", n3 == 0)
    fr4, n4 = financing_r(-1, opens, 0, [(3, 1.0, "time")], 2.0, 50.0, rates)
    check("short financing by hand: net -(5-6) - 1 = 0", n4 == 1 and abs(fr4) < 1e-12)

    # Episodes, verdict, data ------------------------------------------------------------
    fake = [{"bar": x, "side": 1} for x in (0, 50, 95, 96, 400, 480)]
    check("H1 episodes on 96 M15 bars, HTF on 480",
          [t["bar"] for t in episodes(fake, "H1")] == count_episodes([0, 50, 95, 96, 400, 480], 96) == [0, 96, 400]
          and [t["bar"] for t in episodes(fake, "HTF")] == [0, 480])
    check("Bonferroni over 3 cells", abs(CONF_LOWER - (1 - 0.05 / 3)) < 1e-12 and len(CELLS) == 3)
    check("verdict boundaries", classify(19, 1, 2, 1) == "INSUFFICIENT" and classify(20, 0.01, 1, 0.01) == "SUPPORTED"
          and classify(20, -1, 0.1499, -1) == "REFUTED" and classify(20, -1, 0.15, -1) == "INCONCLUSIVE")
    rng = random.Random(11)
    check("a known +0.6R edge is SUPPORTED",
          summarize([max(-1.0, rng.gauss(0.6, 1.2)) for _ in range(300)], iters=2000)["verdict"] == "SUPPORTED")
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, MD.NAME), "w") as fh:
            fh.write("tampered")
        try:
            check_m15(td)
            check("a tampered M15 file is refused", False)
        except RuntimeError:
            check("a tampered M15 file is refused", True)
    try:
        MD.keep(B1.BLOCK_START)
        check("an M15 bar in the sealed block is refused", False)
    except Exception:
        check("an M15 bar in the sealed block is refused", True)

    print("SELFTEST OK" if not fails else f"SELFTEST FAILED: {len(fails)}")
    return not fails


def _mirror_real(b):
    """Mirror around 2.0 so prices stay positive (H <-> L)."""
    out = dict(b)
    out["O"], out["H"], out["L"], out["C"] = ([2 - x for x in b["O"]], [2 - x for x in b["L"]],
                                              [2 - x for x in b["H"]], [2 - x for x in b["C"]])
    return out


def _htf_case():
    Hs = [1.02] * 60
    Ls = [0.995] * 60
    Hs[5], Ls[10], Hs[15], Ls[20] = 1.03, 0.97, 1.05, 0.99
    Hs[16:60] = [1.04] * 44
    sess_ = S._sess(Hs, Ls)
    h1, d1 = {}, {}
    for i, day in enumerate(sess_["days"]):
        t0 = datetime(day.year, day.month, day.day, 0, tzinfo=UTC) - timedelta(hours=2)
        d1[t0] = (1.0, Hs[i], Ls[i], 1.0)
        for hr in range(24):
            h1[t0 + timedelta(hours=hr)] = (1.0400, 1.0410, 1.0390, 1.0400)
    opens = sorted(h1)
    start = 30 * 24
    seq = [(1.0480, 1.0498, 1.0470, 1.0490), (1.0490, 1.0515, 1.0485, 1.0510), (1.0510, 1.0520, 1.0505, 1.0515)]
    for i, r in enumerate(seq):
        h1[opens[start + i]] = r
    for i in range(start + 3, len(opens)):
        h1[opens[i]] = (1.0520, 1.0530, 1.0515, 1.0520)
    h1[opens[start + 10]] = (1.0520, 1.0800, 1.0515, 1.0700)
    m15 = _split(h1)
    tc = opens[start + 3]                                      # first M15 after the confirming close
    m15[tc] = (1.0520, 1.0522, 1.0498, 1.0505)                 # touch, bearish
    m15[tc + BAR] = (1.0505, 1.0515, 1.0501, 1.0512)           # bullish close above: entry 1.0512
    hb, ss = S.prepare(h1, d1)
    hb["atr"] = [0.0040] * len(hb["O"])
    mb = _bars(m15)
    mb["atr"] = [0.0040] * len(mb["O"])
    t, sk = side_trades(hb, ss, mb, 1, None, "HTF", 1.5, mode=3.0)
    ok1 = len(t) == 1 and abs(t[0]["risk_pips"] - 37.0) < 1e-6 and t[0]["reason"] == "target"
    ss2 = dict(ss)
    ss2["L"] = list(ss["L"])
    ss2["L"][20] = 0.96
    t2, sk2 = side_trades(hb, ss2, mb, 1, None, "HTF", 1.5, mode=3.0)
    ok2 = t2 == [] and sk2["daily trend not aligned"] == 1
    return ok1 and ok2, "" if ok1 and ok2 else f" [{len(t)} trades {[(x['risk_pips'], x['reason']) for x in t]} {dict(sk)}; {dict(sk2)}]"


# Stages ------------------------------------------------------------------------

def counts(archive_dir, m15_dir):
    hb, sess, mb = load_all(archive_dir, m15_dir)
    rates = B1.load_rates()
    print(f"BCS-3 counts (no R). H1 bars {len(hb['O'])}; M15 bars {len(mb['O'])}, "
          f"{mb['opens'][0].isoformat()} -> {mb['opens'][-1].isoformat()}")
    for fam, m in CELLS:
        tr, sk = cell(hb, sess, mb, rates, fam, m)
        ep = episodes(tr, fam)
        name = fam if m is None else f"{fam}-{m}"
        print(f"\n## cell {name}: graded trades {len(tr)}; episodes {len(ep)} (long {sum(x['side'] == 1 for x in ep)}, "
              f"short {sum(x['side'] == -1 for x in ep)})")
        print("- " + "; ".join(f"{k} {v}" for k, v in sorted(sk.items())))
        if tr:
            print(f"- wait from confirmation to entry, M15 bars: median {statistics.median(x['wait'] for x in tr)}")
        yr = Counter(x["day"].year for x in ep)
        print("- episodes by year: " + ", ".join(f"{y} {yr[y]}" for y in sorted(yr)))
        print(f"- power at N {len(ep)}: +0.15R {power_at_n(0.15, SD_ASSUMED, len(ep), alpha=ALPHA):.3f}; smallest edge at "
              f"80% {min_detectable_edge(SD_ASSUMED, max(len(ep), 1), alpha=ALPHA):.3f}R")
    print(f"\nN required for +0.15R at 80% power (alpha {ALPHA:.5f}): {n_required(0.15, SD_ASSUMED, alpha=ALPHA)}")


def _fmt(s):
    return (f"N {s['n']} | mean {s['mean']:+.3f}R | median {s['median']:+.3f}R | SD {s['sd']:.3f} | "
            f"lower {s['lower']:+.3f} | upper {s['upper']:+.3f} | without best {s['without_best']:+.3f} | "
            f"win {s['win']:.1%} | max DD {s['max_dd']:.1f}R")


def _short(rs):
    if len(rs) < 2:
        return f"N {len(rs)}"
    return f"N {len(rs)} | mean {statistics.fmean(rs):+.3f}R | median {statistics.median(rs):+.3f}R"


def full(archive_dir, m15_dir, report):
    if os.path.exists(report):
        raise SystemExit(f"refused: {report} already exists (the full run happens once)")
    hb, sess, mb = load_all(archive_dir, m15_dir)
    rates = B1.load_rates()
    out = []
    p = out.append
    p("# BCS-3 result: 15-minute entries on the BCS-1 and BCS-2 breakouts (GBP/AUD, 2005-2013 STUDY)")
    p("")
    p(f"Spec: docs/specs/m15_entry_study_spec.md. Verdict on episode R after era spread and financing. "
      f"Bonferroni one-sided lower bound at {CONF_LOWER:.5f} (3 cells), 90% upper bound for REFUTED (bar +0.15R), "
      f"{RESAMPLES} resamples, seed {SEED}.")
    p("")
    for fam, m in CELLS:
        name = fam if m is None else f"{fam}-{m}"
        tr, sk = cell(hb, sess, mb, rates, fam, m)
        e = episodes(tr, fam)
        s = summarize([t["adj"] for t in e])
        p(f"## Cell {name}: **{s['verdict']}**")
        p("")
        p(f"- {_fmt(s)}")
        p(f"- for comparison, same levels with hourly entries: {REFERENCE[name]}")
        if e:
            p(f"- exits: " + ", ".join(f"{k} {v}" for k, v in sorted(Counter(t['reason'] for t in e).items()))
              + f"; mean risk {statistics.fmean(t['risk_pips'] for t in e):.1f} pips; mean spread "
              f"{statistics.fmean(t['spread_r'] for t in e):+.3f}R; mean financing {statistics.fmean(t['fin_r'] for t in e):+.4f}R")
            p(f"- power at this N: +0.15R {power_at_n(0.15, SD_ASSUMED, len(e), alpha=ALPHA):.3f}; smallest edge at 80% "
              f"{min_detectable_edge(SD_ASSUMED, len(e), alpha=ALPHA):.3f}R")
            p(f"- before costs: {_short([t['raw'] for t in e])}")
            p(f"- stops at the gap open: {_short([t['gap_adj'] for t in e])}")
            p(f"- long: {_short([t['adj'] for t in e if t['side'] == 1])}; short: {_short([t['adj'] for t in e if t['side'] == -1])}")
            for nm, a, b in B1.SUBPERIODS:
                p(f"- {nm}: {_short([t['adj'] for t in e if a <= t['day'] <= b])}")
            yr = defaultdict(list)
            for t in e:
                yr[t["day"].year].append(t["adj"])
            p("- by year: " + "; ".join(f"{y} N {len(v)} {statistics.fmean(v):+.3f}R" for y, v in sorted(yr.items())))
        p("- entry funnel: " + "; ".join(f"{k} {v}" for k, v in sorted(sk.items())))
        for sp in S.FLAT_SPREADS:
            t2, _ = cell(hb, sess, mb, rates, fam, m, mode=sp)
            p(f"- flat {sp} pips + financing: {_fmt(summarize([t['adj'] for t in episodes(t2, fam)]))}")
        t3, sk3 = cell(hb, sess, mb, rates, fam, m, stop_kind="tight")
        e3 = episodes(t3, fam)
        p(f"- tight stop (lowest M15 low since the touch − 15 pips, no 0.3 ATR floor): {_fmt(summarize([t['adj'] for t in e3]))}"
          + (f"; mean risk {statistics.fmean(t['risk_pips'] for t in e3):.1f} pips; before costs {_short([t['raw'] for t in e3])}" if e3 else ""))
        if fam == "HTF":
            t4, _ = cell(hb, sess, mb, rates, fam, m, partial=False)
            p(f"- no partial (full size to target, breakeven at +1R): {_short([t['adj'] for t in episodes(t4, fam)])}")
            t5, _ = cell(hb, sess, mb, rates, fam, m, use_filters=False)
            p(f"- without the trend and obstacle filters: {_short([t['adj'] for t in episodes(t5, fam)])}")
        p("")
    text = "\n".join(out) + "\n"
    with open(report, "w") as fh:
        fh.write(text)
    print(text, end="")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "selftest":
        sys.exit(0 if selftest() else 1)
    if len(sys.argv) == 4 and sys.argv[1] == "counts":
        counts(sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 5 and sys.argv[1] == "full":
        full(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        raise SystemExit(__doc__)
