"""Pre-registered study FCS-1: the three frozen shadow candidates on the 2005-2013
STUDY data, every H4 bar, graded by the live rule, after era spread and financing
(docs/specs/frozen_candidates_study_spec.md; data_map_spec §8).

Cells: MOMENTUM_JOIN x {GBP_AUD, GBP_JPY}, THRUST_PULLBACK x {GBP_AUD, GBP_JPY},
EARLY_MOMENTUM_v2 x GBP_JPY. The candidates are the live functions in
shadow_signals._CANDIDATES, called unmodified on a context built exactly as
shadow_signals._load_ctx builds it. Data: the hashed files of the US-event study
(~/intel_study_archives/us_event_reaction_data/), converted with the approved
weekend rule. This runner never fetches anything and refuses any bar outside the
STUDY partition.

usage:
  python3 -I frozen_candidates_study.py selftest
  python3 -I frozen_candidates_study.py counts <data_dir>
  python3 -I frozen_candidates_study.py full <data_dir> <report_md>

counts prints fires and episodes only (no R, no stop, no outcome). full runs once:
it refuses if the report file already exists or if any data file's sha256 differs
from the pinned value.
"""
import os as _os, sys as _sys  # studies path bootstrap (project root, studies, foundation tools)
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_ROOT = _os.path.dirname(_HERE)
for _p in (_ROOT, _HERE, _os.path.join(_ROOT, "foundation", "tools")):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

import os
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

import first_pullback_study as FP   # noqa: E402  data loading, hashes, window, costs (unchanged)
import history_study_convert as C   # noqa: E402  approved weekend rule, session_day
import shadow_signals as S          # noqa: E402  the frozen candidates, live grading constants
from regime_detection import _compute_adx, _detect_structure, compute_atr_series  # noqa: E402
from power_check import (bootstrap_lower_bound, bootstrap_upper_bound,  # noqa: E402
                         min_detectable_edge, n_required, power_at_n)

UTC = timezone.utc
CELLS = (("MOMENTUM_JOIN", "GBP_AUD"), ("MOMENTUM_JOIN", "GBP_JPY"),
         ("THRUST_PULLBACK", "GBP_AUD"), ("THRUST_PULLBACK", "GBP_JPY"),
         ("EARLY_MOMENTUM_v2", "GBP_JPY"))
PAIRS = ("GBP_AUD", "GBP_JPY")
WINDOW = 300                    # _load_ctx's live fetch (count=300)
HORIZON = S.HORIZON             # 30 H4 bars, the live grading horizon
ALPHA = 0.05 / len(CELLS)       # Bonferroni, one-sided (spec §8)
CONF_LOWER = 1 - ALPHA          # 0.99
CONF_UPPER = 0.90               # the futility rule's bound (spec §8)
REFUTE_BAR = 0.15
RESAMPLES = 20000
SEED = 7
MIN_N = 20
EXAM_SPLIT_PER_YEAR = 8         # data_map_spec §1
STUDY_YEARS = 9
SD_ASSUMED = 1.2
MARKUP = FP.MARKUP              # 1.0 % a year (spec §6)
FLAT_SPREAD = FP.FLAT_SPREAD    # 3.0 pips, secondary
DATA_HASHES = FP.DATA_HASHES
SUBPERIODS = FP.SUBPERIODS


# Context and fires: the live code -----------------------------------------------------

def build_ctx(instrument, bars, i, window=WINDOW):
    """The context shadow_signals._load_ctx builds from a `window`-bar fetch ending at
    bar i, field for field (the self-test proves it)."""
    lo = i - window + 1
    O, H, L, C_ = (bars[k][lo:i + 1] for k in ("O", "H", "L", "C"))
    T = bars["opens"][lo:i + 1]
    atr = compute_atr_series(H, L, C_)
    adx_now = _compute_adx(H, L, C_)
    k = S.MJ_SLOPE_BARS
    adx_prev = _compute_adx(H[:-k], L[:-k], C_[:-k]) if len(C_) > k + 30 else adx_now
    sd = _detect_structure(H, L, C_)
    pip = S.PAIRS[instrument].pip_size if instrument in S.PAIRS else 0.0001
    return {"O": list(O), "H": list(H), "L": list(L), "C": list(C_), "T": list(T), "atr": atr,
            "pip": pip, "adx": adx_now, "adx_slope": adx_now - adx_prev,
            "struct": sd["structure"], "sd": sd}


def replay(instrument, bars, window=WINDOW):
    """Every live candidate on every bar from the first full window. Invalid rows
    (stop on the wrong side) are dropped as the live tally drops them. A candidate
    error aborts the run (spec §4)."""
    fires, dropped = [], Counter()
    for i in range(window - 1, len(bars["C"])):
        ctx = build_ctx(instrument, bars, i, window)
        for fn in S._CANDIDATES:
            s = fn(instrument, ctx)
            if not s:
                continue
            if S.is_invalid_spec(s):
                dropped[s["candidate_id"]] += 1
                continue
            fires.append(dict(s, bar=i))
    return fires, dropped


# Grading: the live rule ---------------------------------------------------------------

def grade_fire(fire, bars, horizon=HORIZON):
    """shadow_signals.grade_pending_shadow's arithmetic: bars i+1..i+30; a touch of
    the stop is -1R, else (close of bar i+30 - entry) / risk. None if the data ends
    first. Also returns the exit bar and the gap-open R of a stop (secondary)."""
    i = fire["bar"]
    O, H, L, C_ = bars["O"], bars["H"], bars["L"], bars["C"]
    if i + horizon >= len(C_):
        return None
    entry, stop = float(fire["entry"]), float(fire["stop"])
    risk = abs(entry - stop) or 1e-9
    long_ = fire["direction"] == "LONG"
    for j in range(i + 1, i + horizon + 1):
        if (L[j] <= stop) if long_ else (H[j] >= stop):
            gapped = (O[j] < stop) if long_ else (O[j] > stop)
            gap_r = ((O[j] - entry) if long_ else (entry - O[j])) / risk if gapped else -1.0
            return {"raw": -1.0, "gap_raw": gap_r, "stopped": True, "exit_bar": j, "risk": risk}
    net = (C_[i + horizon] - entry) if long_ else (entry - C_[i + horizon])
    return {"raw": net / risk, "gap_raw": net / risk, "stopped": False, "exit_bar": i + horizon,
            "risk": risk}


def cell_trades(cid, pair, fires, bars, rates, markup=MARKUP):
    """Graded trades for one cell with costs (spec §6). Entry is at the fire bar's
    close, which is the open of bar i+1 for the financing clock."""
    pip = FP.PAIRS[pair][2]
    trades, ungraded = [], 0
    for f in fires:
        if f["candidate_id"] != cid:
            continue
        g = grade_fire(f, bars)
        if g is None:
            ungraded += 1
            continue
        side = 1 if f["direction"] == "LONG" else -1
        t = FP.financed(pair, side, bars["opens"], f["bar"] + 1, g["exit_bar"], g["stopped"],
                        float(f["entry"]), g["risk"] / pip, rates, None, markup)
        t.update(g)
        t.update({"bar": f["bar"], "side": side, "day": C.session_day(bars["opens"][f["bar"]])})
        t["adj"] = t["raw"] + t["spread_r"] + t["fin_r"]
        t["gap_adj"] = t["gap_raw"] + t["spread_r"] + t["fin_r"]
        trades.append(t)
    return trades, ungraded


def episodes(trades, horizon=HORIZON):
    """shadow_signals.graded_episodes' rule on the bar index (FP.episodes, unchanged)."""
    return FP.episodes(trades, horizon)


# Statistics ---------------------------------------------------------------------------

def classify(n, lower, upper, without_best):
    """The pre-registered verdict rule (spec §8)."""
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
         "max_dd": FP.max_drawdown(rs), "win": sum(r > 0 for r in rs) / n if n else float("nan"),
         "lower": float("nan"), "upper": float("nan")}
    if n >= 2:
        s["lower"] = bootstrap_lower_bound(rs, conf=CONF_LOWER, iters=iters, seed=SEED)
        s["upper"] = bootstrap_upper_bound(rs, conf=CONF_UPPER, iters=iters, seed=SEED)
    s["verdict"] = classify(n, s["lower"], s["upper"], s["without_best"]) if n >= 2 else "INSUFFICIENT"
    return s


# Self-test ----------------------------------------------------------------------------

SELFTEST_SEED = 68


def _synthetic(seed=SELFTEST_SEED, n=480,
               start=datetime(2006, 3, 1, tzinfo=UTC)):
    """A JPY-scale series on the real H4 calendar: quiet spells, tight boxes and
    sharp trends, so that every candidate fires (the self-test asserts it)."""
    import random
    rnd = random.Random(seed)
    opens = S._h4_bar_opens(start, start + timedelta(days=200))[:n]
    O, H, L, Cl = [], [], [], []
    p, drift, vol, left = 150.0, 0.0, 0.10, 0
    for _ in opens:
        if left <= 0:
            mode = rnd.choice(("quiet", "quiet", "up", "down", "chop"))
            drift = {"quiet": 0.0, "chop": 0.0, "up": 0.22, "down": -0.22}[mode]
            vol = {"quiet": 0.05, "chop": 0.25, "up": 0.12, "down": 0.12}[mode]
            left = rnd.randint(15, 45)
        left -= 1
        o = p
        c = o + drift + rnd.gauss(0, vol)
        h = max(o, c) + abs(rnd.gauss(0, vol * 0.6))
        l_ = min(o, c) - abs(rnd.gauss(0, vol * 0.6))
        O.append(round(o, 3)), H.append(round(h, 3)), L.append(round(l_, 3)), Cl.append(round(c, 3))
        p = c
    return {"opens": opens, "O": O, "H": H, "L": L, "C": Cl}


def _frame(bars, lo, hi):
    import pandas as pd
    idx = pd.DatetimeIndex(bars["opens"][lo:hi])
    return pd.DataFrame({"Open": bars["O"][lo:hi], "High": bars["H"][lo:hi], "Low": bars["L"][lo:hi],
                         "Close": bars["C"][lo:hi], "Volume": [0] * (hi - lo)}, index=idx)


def selftest():
    import csv
    import tempfile
    import oanda_feed
    ok = True

    def check(name, cond):
        nonlocal ok
        ok &= bool(cond)
        print(("PASS " if cond else "FAIL ") + name)

    inst = "GBP_JPY"
    bars = _synthetic(SELFTEST_SEED)
    n = len(bars["C"])
    saved = (oanda_feed.get_h4_bars, oanda_feed.is_configured)
    cur = {"i": WINDOW - 1}

    def fake_h4(pair="", count=120, timeout=10):
        hi = cur["i"] + 1
        return _frame(bars, max(0, hi - count), hi)
    oanda_feed.get_h4_bars, oanda_feed.is_configured = fake_h4, (lambda: True)
    cwd = os.getcwd()
    try:
        # 1. The context equals _load_ctx's, field for field
        same = True
        for i in (WINDOW - 1, WINDOW + 40, n - 1):
            cur["i"] = i
            live, mine = S._load_ctx(inst), build_ctx(inst, bars, i)
            for k in ("O", "H", "L", "C", "atr", "pip", "adx", "adx_slope", "struct", "sd"):
                same &= live[k] == mine[k]
            same &= [t.isoformat() for t in live["T"]] == [t.isoformat() for t in mine["T"]]
        check("the context equals shadow_signals._load_ctx on the same bars (3 bars, every field)", same)

        # 2. Fires equal the live entry point, bar by bar, and are not vacuous
        fires, dropped = replay(inst, bars)
        live_fires = []
        with tempfile.TemporaryDirectory() as td:
            os.chdir(td)                                  # no calendar here: no news stamp
            for i in range(WINDOW - 1, n):
                cur["i"] = i
                live_fires += [s for s in S.check_shadow_signals(inst) if not S.is_invalid_spec(s)]
            os.chdir(cwd)
        key = lambda s: (s["candidate_id"], s["timestamp"], s["direction"], s["entry"], s["stop"])
        check(f"fires equal check_shadow_signals on every bar ({len(fires)} fires)",
              [key(f) for f in fires] == [key(f) for f in live_fires])
        per = Counter(f["candidate_id"] for f in fires)
        check(f"every candidate fires on the synthetic series ({dict(per)})",
              all(per[c] >= 1 for c in ("MOMENTUM_JOIN", "THRUST_PULLBACK", "EARLY_MOMENTUM_v2")))

        # 3. Grades equal grade_pending_shadow; episodes equal graded_episodes
        cur["i"] = n - 1
        with tempfile.TemporaryDirectory() as td:
            os.chdir(td)
            S.log_shadow_signals([{k: v for k, v in f.items() if k != "bar"} for f in fires])
            S.grade_pending_shadow(inst)
            with open(S.LOG_FILE, newline="") as fh:
                rows = {(r["candidate_id"], r["timestamp"]): r for r in csv.DictReader(fh)}
            match, graded = True, 0
            for f in fires:
                g = grade_fire(f, bars)
                r = rows[(f["candidate_id"], f["timestamp"])]
                if g is None:
                    match &= r["outcome_filled"] != "True"
                    continue
                graded += 1
                match &= (r["outcome_filled"] == "True" and float(r["r_multiple"]) == round(g["raw"], 2)
                          and (r["hit_stop"] == "True") == g["stopped"])
            check(f"grades equal grade_pending_shadow ({graded} graded rows: R to 2 dp and stop flag)",
                  match and graded >= 3)
            eq = True
            for cid in ("MOMENTUM_JOIN", "THRUST_PULLBACK", "EARLY_MOMENTUM_v2"):
                live_eps = [r["timestamp"] for r in S.graded_episodes(cid, inst)]
                mine = [{"bar": f["bar"], "side": 1 if f["direction"] == "LONG" else -1, "ts": f["timestamp"]}
                        for f in fires if f["candidate_id"] == cid and grade_fire(f, bars) is not None]
                eq &= [e["ts"] for e in episodes(mine)] == live_eps
            check("episodes equal shadow_signals.graded_episodes for every candidate", eq)
            os.chdir(cwd)
    finally:
        os.chdir(cwd)
        oanda_feed.get_h4_bars, oanda_feed.is_configured = saved

    # 4. Hand-computed grades
    hb = {"opens": bars["opens"][:40], "O": [100.0] * 40, "H": [100.5] * 40, "L": [99.5] * 40, "C": [100.0] * 40}
    hb["C"][31] = 101.0
    g = grade_fire({"bar": 1, "entry": 100.0, "stop": 99.0, "direction": "LONG"}, hb)
    check(f"timed exit: (101 - 100) / 1 = +1.0R at bar 31 ({g})", g and not g["stopped"] and g["raw"] == 1.0
          and g["exit_bar"] == 31)
    hb2 = dict(hb, L=list(hb["L"]))
    hb2["L"][1] = 98.0                                         # the fire bar itself: never checked
    hb2["L"][31] = 99.0                                        # bar i+30 touches the stop
    g = grade_fire({"bar": 1, "entry": 100.0, "stop": 99.0, "direction": "LONG"}, hb2)
    check("no stop check on the fire bar; a touch on bar i+30 is -1R", g["stopped"] and g["raw"] == -1.0
          and g["exit_bar"] == 31)
    hb3 = dict(hb, H=list(hb["H"]), O=list(hb["O"]))
    hb3["H"][5], hb3["O"][5] = 101.5, 101.5
    g = grade_fire({"bar": 1, "entry": 100.0, "stop": 101.0, "direction": "SHORT"}, hb3)
    check(f"short stopped on bar 5, gap-open R -1.5 ({g})", g["stopped"] and g["raw"] == -1.0
          and abs(g["gap_raw"] + 1.5) < 1e-12)
    check("a fire with 30 bars not yet elapsed is ungraded",
          grade_fire({"bar": 10, "entry": 100.0, "stop": 99.0, "direction": "LONG"}, hb) is None)

    # 5. Costs
    check("era spreads (data_map_spec §4)", (FP.era_spread("GBP_AUD", 2006), FP.era_spread("GBP_AUD", 2012),
                                              FP.era_spread("GBP_JPY", 2009), FP.era_spread("GBP_JPY", 2010))
          == (10.0, 7.0, 6.0, 5.0))
    rates = FP.load_rates()
    t = FP.financed("GBP_JPY", 1, bars["opens"], 1, 31, False, 150.0, 100.0, rates, None, MARKUP)
    day = C.session_day(bars["opens"][1])
    net = FP.rate_on(rates, "GBP", day) - FP.rate_on(rates, "JPY", day) - MARKUP
    want = 150.0 * net / 100 * t["nights"] / 365 / 0.01 / 100.0
    check(f"financing for a long against hand arithmetic ({t['fin_r']:+.5f}R over {t['nights']} nights)",
          abs(t["fin_r"] - want) < 1e-12 and t["nights"] >= 5 and abs(t["spread_r"] + 0.06) < 1e-12)
    # The fire bar is the session's last (13:00 New York), so the 17:00 rollover sits at
    # the entry instant: counted from the fire bar's open it would add a night.
    from zoneinfo import ZoneInfo
    fb = next(k for k in range(1, 8) if hb["opens"][k + 1].astimezone(ZoneInfo("America/New_York")).hour == 17)
    hb["C"][31] = 100.0
    hb["C"][fb + 30] = 101.0
    fires_h = [{"candidate_id": "MOMENTUM_JOIN", "bar": fb, "entry": 100.0, "stop": 99.0, "direction": "LONG"},
               {"candidate_id": "THRUST_PULLBACK", "bar": fb + 1, "entry": 100.0, "stop": 99.0, "direction": "LONG"}]
    tr, ung = cell_trades("MOMENTUM_JOIN", "GBP_JPY", fires_h, hb, rates)
    t0 = tr[0] if tr else {}
    fin = FP.financed("GBP_JPY", 1, hb["opens"], fb + 1, fb + 30, False, 100.0, 100.0, rates, None, MARKUP)
    early = FP.financed("GBP_JPY", 1, hb["opens"], fb, fb + 30, False, 100.0, 100.0, rates, None, MARKUP)
    check(f"cell_trades: its own candidate only; entry clock at bar i+1 ({fin['nights']} nights, not "
          f"{early['nights']}); adj = raw + spread + financing",
          len(tr) == 1 and ung == 0 and t0["raw"] == 1.0 and t0["nights"] == fin["nights"] != early["nights"]
          and abs(t0["fin_r"] - fin["fin_r"]) < 1e-12 and abs(t0["spread_r"] + 0.06) < 1e-12
          and abs(t0["adj"] - (1.0 - 0.06 + fin["fin_r"])) < 1e-12)
    eps_h = episodes([{"bar": 0, "side": 1}, {"bar": 29, "side": 1}, {"bar": 30, "side": -1}])
    check("episodes: a fire 29 bars on joins the episode; 30 bars on starts a new one",
          [e["bar"] for e in eps_h] == [0, 30])
    saved_c = S._CANDIDATES
    try:
        S._CANDIDATES = [lambda inst, ctx: {"candidate_id": "FAKE", "timestamp": "x", "direction": "LONG",
                                            "entry": ctx["C"][-1], "stop": ctx["C"][-1] + 1.0}]
        f_bad, d_bad = replay(inst, bars)
    finally:
        S._CANDIDATES = saved_c
    check(f"an invalid fire (long stop above entry) is dropped and counted ({d_bad['FAKE']} dropped)",
          f_bad == [] and d_bad["FAKE"] == n - WINDOW + 1)

    # 6. Verdict rule with Bonferroni
    check("Bonferroni level 0.99 over 5 cells", abs(CONF_LOWER - 0.99) < 1e-12 and len(CELLS) == 5)
    check("verdict boundaries", (classify(19, 1, 1, 1), classify(20, 0.01, 1, 0.01), classify(20, 0.01, 1, -0.01),
                                 classify(20, -0.1, 0.149, 0), classify(20, -0.1, 0.15, 0), classify(20, 0.0, 1, 1))
          == ("INSUFFICIENT", "SUPPORTED", "INCONCLUSIVE", "REFUTED", "INCONCLUSIVE", "INCONCLUSIVE"))
    import random
    rnd = random.Random(3)
    edge = summarize([rnd.gauss(0.9, 1.2) for _ in range(150)], iters=4000)
    zero = summarize([rnd.gauss(-0.2, 1.2) for _ in range(150)], iters=4000)
    check(f"a +0.9R edge is SUPPORTED ({edge['verdict']}); a -0.2R cell is REFUTED ({zero['verdict']})",
          edge["verdict"] == "SUPPORTED" and zero["verdict"] == "REFUTED")

    # 7. Refusals
    for t_, refused in ((datetime(2004, 12, 31, 22, tzinfo=UTC), True), (datetime(2013, 12, 30, 18, tzinfo=UTC), False),
                        (datetime(2013, 12, 30, 22, tzinfo=UTC), True)):
        try:
            FP.check_window([t_])
            got = False
        except RuntimeError:
            got = True
        check(f"bar opening {t_.isoformat()} is {'refused' if refused else 'accepted'}", got == refused)
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "X.csv")
        with open(p, "w") as fh:
            fh.write("time_utc,o,h,l,c\n")
        good = {"X.csv": FP.sha(p)}
        with open(p, "a") as fh:
            fh.write("2006-01-02T22:00:00+00:00,1,1,1,1\n")
        try:
            FP.verify_hashes(td, good)
            refused = False
        except RuntimeError:
            refused = True
        check("a data file whose sha256 differs from the pinned value is refused", refused)
        rep = os.path.join(td, "r.md")
        open(rep, "w").close()
        try:
            full(td, rep)
            refused = False
        except RuntimeError:
            refused = True
        check("full refuses when the report already exists", refused)
    print("SELFTEST", "OK" if ok else "FAILED")
    return ok


# Stages -------------------------------------------------------------------------------

def _prepare(data_dir):
    FP.verify_hashes(data_dir, DATA_HASHES)
    out = {}
    for pair in PAIRS:
        bars, sess, log = FP.load_pair(data_dir, pair)
        fires, dropped = replay(pair, bars)
        out[pair] = (bars, fires, dropped, log)
    return out


def counts(data_dir):
    """Counts only (data_map_spec §9): fires and episodes per cell. No R, no stop, no outcome."""
    print(f"Data hashes verified against the pinned values ({len(DATA_HASHES)} files).")
    prepared = _prepare(data_dir)
    for pair, (bars, _, _, log) in prepared.items():
        o = bars["opens"]
        print(f"{pair}: H4 bars {len(o)} ({o[0].isoformat()} to {o[-1].isoformat()}); replayed from bar "
              f"{WINDOW - 1}; weekend rule: {log['sunday_folded_h4']} Sunday H4 folded, "
              f"{log['saturday_dropped_h4']} Saturday H4 dropped")
    for cid, pair in CELLS:
        bars, fires, dropped, _ = prepared[pair]
        mine = [f for f in fires if f["candidate_id"] == cid]
        graded = [{"bar": f["bar"], "side": 1 if f["direction"] == "LONG" else -1,
                   "day": C.session_day(bars["opens"][f["bar"]])}
                  for f in mine if f["bar"] + HORIZON < len(bars["C"])]
        eps = episodes(graded)
        n_long = sum(e["side"] == 1 for e in eps)
        per_year = Counter(e["day"].year for e in eps)
        rate = len(eps) / STUDY_YEARS
        print(f"CELL {cid} {pair}: fires {len(mine)}; invalid dropped {dropped[cid]}; graded fires {len(graded)}; "
              f"ungraded at data end {len(mine) - len(graded)}; EPISODES N {len(eps)} (long {n_long}, short "
              f"{len(eps) - n_long}); episodes/yr {rate:.1f}; exam-split flag (>= {EXAM_SPLIT_PER_YEAR}/yr): "
              f"{'yes' if rate >= EXAM_SPLIT_PER_YEAR else 'no'}; per year {dict(sorted(per_year.items()))}")


def _fmt(s):
    return (f"N {s['n']}; mean {s['mean']:+.3f}R; median {s['median']:+.3f}R; "
            f"Bonferroni lower bound {s['lower']:+.3f}R; 90% upper bound {s['upper']:+.3f}R; "
            f"without best {s['without_best']:+.3f}R; max DD {s['max_dd']:.1f}R; win {100 * s['win']:.0f}%")


def _short(rs):
    if not rs:
        return "N 0"
    return (f"N {len(rs)}; mean {statistics.fmean(rs):+.3f}R; median {statistics.median(rs):+.3f}R"
            + ("  (INSUFFICIENT: N<20)" if len(rs) < MIN_N else ""))


def full(data_dir, report):
    if os.path.exists(report):
        raise RuntimeError(f"{report} exists: the full run happens once (spec §12)")
    rates = FP.load_rates()
    prepared = _prepare(data_dir)
    lines = ["# Frozen shadow candidates on the 2005–2013 STUDY data — pre-registered result (FCS-1)", "",
             f"Spec: docs/specs/frozen_candidates_study_spec.md. Every H4 bar, live candidate code, live "
             f"grading rule. Verdict on episode R after era spread and financing. Bonferroni one-sided lower "
             f"bound at {CONF_LOWER:.2f} ({len(CELLS)} cells), 90% upper bound for REFUTED (bar "
             f"+{REFUTE_BAR:.2f}R), {RESAMPLES} resamples, seed {SEED}. Frame (data_map_spec §5): does this "
             f"survive conditions it was not designed on.", ""]
    summary = []
    for cid, pair in CELLS:
        bars, fires, dropped, _ = prepared[pair]
        trades, ungraded = cell_trades(cid, pair, fires, bars, rates)
        eps = episodes(trades)
        rs = [e["adj"] for e in eps]
        s = summarize(rs)
        summary.append((cid, pair, s))
        win = [x for x in rs if x > 0]
        loss = [x for x in rs if x <= 0]
        lines += [f"## {cid} {pair}: **{s['verdict']}**", "",
                  f"- **Primary (episode R after era spread and financing):** {_fmt(s)}; SD {s['sd']:.3f}",
                  f"- Median winner {statistics.median(win) if win else float('nan'):+.3f}R (N {len(win)}); "
                  f"median loser {statistics.median(loss) if loss else float('nan'):+.3f}R (N {len(loss)}); "
                  f"stopped {sum(e['stopped'] for e in eps)} of {len(eps)}",
                  (f"- Costs per episode: spread {statistics.fmean(e['spread_r'] for e in eps):+.3f}R, financing "
                   f"{statistics.fmean(e['fin_r'] for e in eps):+.3f}R, mean nights "
                   f"{statistics.fmean(e['nights'] for e in eps):.1f}, mean risk "
                   f"{statistics.fmean(e['risk_pips'] for e in eps):.0f} pips") if eps else "- no episodes",
                  f"- Power at this N (SD {SD_ASSUMED}R assumed, α {ALPHA:.3f}): "
                  f"{100 * power_at_n(0.15, SD_ASSUMED, max(s['n'], 1), ALPHA):.0f}% for +0.15R; smallest edge "
                  f"detectable at 80% power {min_detectable_edge(SD_ASSUMED, max(s['n'], 1), 0.8, ALPHA):+.2f}R",
                  "", "**Secondary (never changes the verdict):**", "",
                  f"- Before costs (live rule only): {_short([e['raw'] for e in eps])}",
                  f"- Flat {FLAT_SPREAD}-pip spread + financing: "
                  f"{_short([e['raw'] + e['fin_r'] - FLAT_SPREAD / e['risk_pips'] for e in eps])}",
                  f"- Stops filled at the gap open: {_short([e['gap_adj'] for e in eps])}; stops that gapped: "
                  f"{sum(e['gap_raw'] < -1 for e in eps)}"]
        for mk in (0.0, 2.0):
            t2, _ = cell_trades(cid, pair, fires, bars, rates, markup=mk)
            lines.append(f"- Financing markup {mk:.0f}%: {_short([e['adj'] for e in episodes(t2)])}")
        for side, name in ((1, "Long"), (-1, "Short")):
            lines.append(f"- {name} episodes: {_short([e['adj'] for e in eps if e['side'] == side])}")
        for name, lo, hi in SUBPERIODS:
            lines.append(f"- {name}: {_short([e['adj'] for e in eps if lo <= e['day'] <= hi])}")
        per_year = defaultdict(list)
        for e in eps:
            per_year[e["day"].year].append(e["adj"])
        lines.append("- By year (N, mean R): " + "; ".join(
            f"{y} {len(v)} {statistics.fmean(v):+.2f}" for y, v in sorted(per_year.items())))
        lines.append(f"- Fires: {sum(f['candidate_id'] == cid for f in fires)}; invalid dropped {dropped[cid]}; "
                     f"graded {len(trades)}; ungraded at data end {ungraded}")
        lines.append("")
    lines += ["## Summary", "", "| Cell | N | Mean R | Median R | Lower bound | Upper 90% | Without best | Max DD | Verdict |",
              "|---|---|---|---|---|---|---|---|---|"]
    for cid, pair, s in summary:
        lines.append(f"| {cid} {pair} | {s['n']} | {s['mean']:+.3f} | {s['median']:+.3f} | {s['lower']:+.3f} | "
                     f"{s['upper']:+.3f} | {s['without_best']:+.3f} | {s['max_dd']:.1f} | {s['verdict']} |")
    lines += ["", f"- N required for +0.15R at 80% power (SD {SD_ASSUMED}, α {ALPHA:.3f}): "
              f"{n_required(0.15, SD_ASSUMED, 0.8, ALPHA)}"]
    text = "\n".join(lines)
    with open(report, "w") as fh:
        fh.write(text + "\n")
    print(text)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "selftest":
        sys.exit(0 if selftest() else 1)
    elif mode == "counts":
        counts(sys.argv[2])
    elif mode == "full":
        full(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
