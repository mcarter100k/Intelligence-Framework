"""Pre-registered test: after a turn off a 20-day range extreme, does the first
H4 pullback to 38.2% (or 50%) of the impulse, taken with the 13-week direction,
have an edge after costs? (docs/specs/first_pullback_study_spec.md)

Cells: {GBP_AUD, GBP_JPY} x {38.2%, 50%}; long and short pooled in each cell.
Data: the 2005-2013 STUDY partition only, the files fetched and hashed by the
US-event study (~/intel_study_archives/us_event_reaction_data/). This runner
never fetches anything and refuses any bar in the embargo / sealed exam.

usage:
  python3 -I first_pullback_study.py selftest
  python3 -I first_pullback_study.py counts <data_dir>
  python3 -I first_pullback_study.py full <data_dir> <report_md>

counts prints entry and episode counts only (no R, no outcome). full runs once:
it refuses if the report file already exists or if any data file's sha256
differs from the pinned value below.
"""
import bisect
import csv
import hashlib
import json
import os
import random
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "foundation", "tools"))
import history_study_convert as C  # noqa: E402  approved weekend rule
from shadow_cost_regrade import rollover_nights  # noqa: E402  17:00 NY, Wednesday x3
from episodes import count_episodes  # noqa: E402  the framework's episode rule
from power_check import (bootstrap_lower_bound, bootstrap_upper_bound,  # noqa: E402
                         min_detectable_edge, n_required, power_at_n)

UTC = timezone.utc
PAIRS = {"GBP_JPY": ("GBP", "JPY", 0.01), "GBP_AUD": ("GBP", "AUD", 0.0001)}
LEVELS = (0.382, 0.5)          # the two cells per pair (spec §4.4)
SECONDARY_STOP = 0.618         # spec §5.2
RANGE_BARS = 120               # 20 sessions x 6 H4 bars: the range extreme (spec §4.1)
MIN_IMPULSE_ATR = 2.0          # impulse size in D1 ATR (spec §4.2)
ATR_SESSIONS = 14              # D1 ATR, completed sessions only (spec §4.2)
TREND_SESSIONS = 65            # 13-week direction, completed sessions only (spec §4.3)
LEG_WINDOW = 60                # H4 bars after the anchor in which the fill may come (spec §4.2)
STOP_BUFFER_ATR = 0.1          # stop beyond the origin / 61.8% level (spec §5.1)
HORIZON = 30                   # H4 bars after the fill bar (spec §5.3)
ERA_SPREAD = {"GBP_AUD": {range(2005, 2010): 10.0, range(2010, 2014): 7.0},   # data_map_spec §4 (frozen)
              "GBP_JPY": {range(2005, 2010): 6.0, range(2010, 2014): 5.0}}
FLAT_SPREAD = 3.0              # secondary: present-day cost (spec §5.4)
MARKUP = 1.0                   # % a year off the carry received / added to carry paid (spec §5.4)
CELLS = len(PAIRS) * len(LEVELS)
ALPHA = 0.05 / CELLS           # Bonferroni, one-sided (spec §7)
CONF_LOWER = 1 - ALPHA         # 0.9875
CONF_UPPER = 0.90              # the futility rule's bound (spec §8)
REFUTE_BAR = 0.15              # smallest edge worth trading, R
RESAMPLES = 20000
SEED = 7
MIN_N = 20
DEVELOPING_N = 60
SD_ASSUMED = 1.2
FIRST_OPEN = datetime(2005, 1, 1, tzinfo=UTC)
BLOCK_START = datetime(2013, 12, 30, 22, 0, tzinfo=UTC)   # embargo + SEALED EXAM start
BLOCK_END = datetime(2021, 4, 26, 21, 0, tzinfo=UTC)
DATA_HASHES = {   # recorded by the US-event counts stage, validation_log 2026-11-01
    "GBP_JPY_D.csv": "ca1602404c5c501dffc0ee8ec5eeb4bee4a2197fe2fc76d3bbf69be2c8fa000a",
    "GBP_JPY_H4.csv": "f06892d1ebf958cc1a52bebf399e6ce10bef8e73e5e2c5b6a7f5634644053764",
    "GBP_AUD_D.csv": "661a9d49c09ed9fbaa7a26a1e3ae60a4fc07860d19ea3ec89342398a9db7d939",
    "GBP_AUD_H4.csv": "a59db9940e8d7a1c4ff02441112390c5d7b7544e764d980943877dee51b0ff77",
}
SUBPERIODS = [("2005-01 to 2008-06 (before the crisis)", date(2005, 1, 1), date(2008, 6, 30)),
              ("2008-07 to 2009-06 (the crisis)", date(2008, 7, 1), date(2009, 6, 30)),
              ("2009-07 to 2013-12 (after)", date(2009, 7, 1), date(2013, 12, 31))]


# Data ------------------------------------------------------------------------------

def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def verify_hashes(data_dir, pinned=DATA_HASHES):
    for name, h in pinned.items():
        got = sha(os.path.join(data_dir, name))
        if got != h:
            raise RuntimeError(f"{name} sha256 {got} differs from the pinned {h}: refused")


def check_window(times):
    """Every bar must open inside the STUDY partition: never the embargo, the sealed
    exam or anything after it, never before 2005."""
    for t in times:
        if t < FIRST_OPEN or t >= BLOCK_START:
            raise RuntimeError(f"bar {t.isoformat()} is outside the STUDY partition: refused")


def load(path):
    with open(path) as fh:
        return {datetime.fromisoformat(r["time_utc"]): tuple(float(r[k]) for k in "ohlc")
                for r in csv.DictReader(fh)}


def load_pair(data_dir, pair):
    """Converted (weekend rule) H4 bars and D1 sessions for a pair."""
    d1 = load(os.path.join(data_dir, f"{pair}_D.csv"))
    h4 = load(os.path.join(data_dir, f"{pair}_H4.csv"))
    check_window(d1)
    check_window(h4)
    d1c, h4c, log = C.convert(d1, h4)
    opens = sorted(h4c)
    bars = {"opens": opens, "O": [h4c[t][0] for t in opens], "H": [h4c[t][1] for t in opens],
            "L": [h4c[t][2] for t in opens], "C": [h4c[t][3] for t in opens]}
    return bars, session_table(d1c), log


def load_rates(path=os.path.join(HERE, "policy_rates_2003_2014.json")):
    with open(path) as fh:
        raw = json.load(fh)
    return {ccy: [(date.fromisoformat(d), v) for d, v in raw[ccy]["changes"]] for ccy in ("GBP", "AUD", "JPY")}


def rate_on(rates, ccy, day):
    val = None
    for d, v in rates[ccy]:
        if d <= day:
            val = v
    if val is None:
        raise ValueError(f"no {ccy} rate on {day}")
    return val


def era_spread(pair, year):
    for yrs, v in ERA_SPREAD[pair].items():
        if year in yrs:
            return v
    raise ValueError(f"no spread for {pair} {year}")


# Context: D1 ATR and the 13-week direction, from COMPLETED sessions only -----------------

def session_table(d1c):
    """Converted D1 {open: (o,h,l,c)} -> (session days, closes, true ranges). TR[0] is None."""
    ts = sorted(d1c)
    days = [C.session_day(t) for t in ts]
    closes = [d1c[t][3] for t in ts]
    trs = [None]
    for k in range(1, len(ts)):
        _, h, l, _ = d1c[ts[k]]
        pc = closes[k - 1]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return days, closes, trs


def bar_context(opens, sess):
    """Per H4 bar: (D1 ATR, trend sign) from sessions strictly before the bar's own session.
    None while warming up."""
    days, closes, trs = sess
    atr, trend = [], []
    for t in opens:
        k = bisect.bisect_left(days, C.session_day(t))   # sessions completed before this bar's session
        atr.append(statistics.fmean(trs[k - ATR_SESSIONS:k]) if k - ATR_SESSIONS >= 1 else None)
        if k - 1 - TREND_SESSIONS >= 0:
            d = closes[k - 1] - closes[k - 1 - TREND_SESSIONS]
            trend.append(1 if d > 0 else -1 if d < 0 else 0)
        else:
            trend.append(None)
    return atr, trend


# The leg detector and the fill (written for the long side; the short side is the mirror) --

def find_entries(O, H, L, atr, trend, level, use_trend=True, window=LEG_WINDOW,
                 range_bars=RANGE_BARS, min_impulse=MIN_IMPULSE_ATR):
    """Long-side first-pullback entries (spec §4).

    Anchor: a bar whose low is strictly below every low of the previous range_bars-1 bars.
    Impulse extreme B: the highest high of the bars AFTER the anchor bar.
    Qualified: B - A >= min_impulse x D1 ATR (ATR fixed at the anchor).
    Order: from each H4 close at which the leg is qualified, a buy limit rests at
    B - level x (B - A) for the next bar. The first bar whose low reaches it is THE
    pullback: filled at min(open, level). It consumes the leg whether or not the trend
    filter lets the trade be taken. Fills are allowed on bars anchor+1 .. anchor+window.
    A new range low replaces the leg."""
    n = len(O)
    out, legs, leg = [], Counter(), None
    for i in range(n):
        if leg and leg["live"] and leg["qualified"] and i - leg["a"] <= window:
            A, B = leg["A"], leg["B"]
            lvl = B - level * (B - A)
            if L[i] <= lvl:
                leg["live"] = False
                legs["first touches"] += 1
                if not use_trend or (trend[i] is not None and trend[i] > 0):
                    out.append({"bar": i, "fill": min(O[i], lvl), "level": lvl, "A": A, "B": B,
                                "atr": leg["atr"], "anchor_bar": leg["a"], "gap_open": O[i] < lvl})
                    legs["entries"] += 1
                else:
                    legs["touches against the 13-week direction (no trade)"] += 1
        if i >= range_bars - 1 and L[i] < min(L[i - range_bars + 1:i]):
            if leg and leg["live"]:
                legs["replaced by a lower low before a touch"] += 1
            if atr[i] is None or trend[i] is None:
                legs["anchors in warm-up (skipped)"] += 1
                leg = None
                continue
            leg = {"a": i, "A": L[i], "atr": atr[i], "B": None, "qualified": False, "live": True}
            legs["anchors"] += 1
            continue
        if leg and leg["live"]:
            if i - leg["a"] >= window:
                leg["live"] = False
                legs["expired qualified" if leg["qualified"] else "expired unqualified"] += 1
                continue
            leg["B"] = H[i] if leg["B"] is None else max(leg["B"], H[i])
            if not leg["qualified"] and leg["B"] - leg["A"] >= min_impulse * leg["atr"]:
                leg["qualified"] = True
                legs["qualified impulses"] += 1
    return out, legs


def grade(O, H, L, C_, e, entry, stop, intended_risk, horizon=HORIZON):
    """Long-side grade on the stop (spec §5). The fill bar e is inside the horizon; the
    timed exit is the close of bar e+horizon. None if the data ends first."""
    if e + horizon >= len(C_):
        return None
    if entry <= stop:   # the fill bar opened at or through the stop: a loss, at the intended risk
        return {"raw": -1.0, "gap_r": -1.0, "exit_bar": e, "stopped": True, "risk": intended_risk,
                "gap_through_at_fill": True}
    risk = entry - stop
    for j in range(e, e + horizon + 1):
        if L[j] <= stop:
            gap_r = (min(O[j], stop) - entry) / risk if j > e else -1.0
            return {"raw": -1.0, "gap_r": gap_r, "exit_bar": j, "stopped": True, "risk": risk,
                    "gap_through_at_fill": False}
    raw = (C_[e + horizon] - entry) / risk
    return {"raw": raw, "gap_r": raw, "exit_bar": e + horizon, "stopped": False, "risk": risk,
            "gap_through_at_fill": False}


def mirrored(bars, trend):
    """The short side as a long side: negate prices (high <-> low) and the trend sign."""
    return ([-x for x in bars["O"]], [-x for x in bars["L"]], [-x for x in bars["H"]],
            [-x for x in bars["C"]], [None if t is None else -t for t in trend])


def side_trades(pair, bars, atr, trend, level, side, rates, stop_kind="origin", use_trend=True,
                flat_spread=None, markup=MARKUP):
    """Graded trades for one side. Returns (trades, leg counts, ungraded count)."""
    _, _, pip = PAIRS[pair]
    if side == 1:
        O, H, L, C_, tr = bars["O"], bars["H"], bars["L"], bars["C"], trend
    else:
        O, H, L, C_, tr = mirrored(bars, trend)
    entries, legs = find_entries(O, H, L, atr, tr, level, use_trend=use_trend)
    trades, ungraded = [], 0
    for en in entries:
        A, B, a = en["A"], en["B"], en["atr"]
        stop = (A if stop_kind == "origin" else B - SECONDARY_STOP * (B - A)) - STOP_BUFFER_ATR * a
        g = grade(O, H, L, C_, en["bar"], en["fill"], stop, en["level"] - stop)
        if g is None:
            ungraded += 1
            continue
        t = financed(pair, side, bars["opens"], en["bar"], g["exit_bar"], g["stopped"],
                     abs(en["fill"]), g["risk"] / pip, rates, flat_spread, markup)
        t.update({"bar": en["bar"], "side": side, "raw": g["raw"], "gap_raw": g["gap_r"],
                  "stopped": g["stopped"], "gap_through_at_fill": g["gap_through_at_fill"],
                  "gap_open": en["gap_open"], "day": C.session_day(bars["opens"][en["bar"]])})
        t["adj"] = t["raw"] + t["spread_r"] + t["fin_r"]
        t["gap_adj"] = t["gap_raw"] + t["spread_r"] + t["fin_r"]
        trades.append(t)
    return trades, legs, ungraded


def financed(pair, side, opens, e, exit_bar, stopped, entry_price, risk_pips, rates,
             flat_spread=None, markup=MARKUP):
    """Spread and financing in R (spec §5.4). Entry at the fill bar's open (a rollover at that
    instant precedes the fill); exit at the stop bar's open or the close of the horizon bar."""
    base, quote, pip = PAIRS[pair]
    entry_time = opens[e]
    exit_time = opens[exit_bar] if stopped else opens[exit_bar] + timedelta(hours=4)
    nights = rollover_nights(entry_time, exit_time)
    day = C.session_day(entry_time)
    net = side * (rate_on(rates, base, day) - rate_on(rates, quote, day)) - markup
    fin_pips = entry_price * net / 100 * nights / 365 / pip
    spread = flat_spread if flat_spread is not None else era_spread(pair, day.year)
    return {"nights": nights, "risk_pips": risk_pips, "spread_r": -spread / risk_pips,
            "fin_r": fin_pips / risk_pips}


def cell_trades(pair, bars, atr, trend, level, rates, **kw):
    trades, legs, ungraded = [], {}, 0
    for side in (1, -1):
        t, lg, u = side_trades(pair, bars, atr, trend, level, side, rates, **kw)
        trades += t
        legs["long" if side == 1 else "short"] = lg
        ungraded += u
    return trades, legs, ungraded


def episodes(trades, horizon=HORIZON):
    """First trade per independent episode on the pair's bar index (episodes.py rule: a trade
    starts a new episode only `horizon` or more bars after the current episode's start).
    Same-bar ties: long first."""
    out = []
    for t in sorted(trades, key=lambda x: (x["bar"], -x["side"])):
        if not out or t["bar"] - out[-1]["bar"] >= horizon:
            out.append(t)
    return out


# Statistics ------------------------------------------------------------------------

def max_drawdown(rs):
    cum = peak = dd = 0.0
    for r in rs:
        cum += r
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    return dd


def classify(n, lower, upper, without_best):
    """The pre-registered verdict rule (spec §8)."""
    if n < MIN_N:
        return "INSUFFICIENT"
    if lower > 0 and without_best > 0:
        return "SUPPORTED"
    if upper < REFUTE_BAR:
        return "REFUTED"
    return "INCONCLUSIVE"


def tier(n):
    if n < MIN_N:
        return "INSUFFICIENT (N<20)"
    if n < DEVELOPING_N:
        return "developing (N 20-59)"
    return "N>=60"


def summarize(rs, iters=RESAMPLES):
    n = len(rs)
    s = {"n": n, "mean": statistics.fmean(rs) if rs else float("nan"),
         "median": statistics.median(rs) if rs else float("nan"),
         "sd": statistics.stdev(rs) if n > 1 else float("nan"),
         "without_best": statistics.fmean(sorted(rs)[:-1]) if n > 1 else float("nan"),
         "max_dd": max_drawdown(rs), "win": sum(r > 0 for r in rs) / n if n else float("nan"),
         "lower": float("nan"), "upper": float("nan")}
    if n >= 2:
        s["lower"] = bootstrap_lower_bound(rs, conf=CONF_LOWER, iters=iters, seed=SEED)
        s["upper"] = bootstrap_upper_bound(rs, conf=CONF_UPPER, iters=iters, seed=SEED)
    s["verdict"] = classify(n, s["lower"], s["upper"], s["without_best"]) if n >= 2 else "INSUFFICIENT"
    return s


# Self-test ---------------------------------------------------------------------

def _owner_bars():
    """A replica of the owner's 2026 GBP/AUD leg on synthetic H4 bars: range low 1.8873,
    rally to 1.9257, D1 ATR 0.0120 (2 ATR = 0.0240; the impulse is 0.0384 = 3.2 ATR)."""
    O, H, L, Cl = [], [], [], []

    def bar(o, h, l, c):
        O.append(o), H.append(h), L.append(l), Cl.append(c)
    for _ in range(125):                      # bars 0-124: a range with lows at 1.8950
        bar(1.9000, 1.9020, 1.8950, 1.9000)
    bar(1.8960, 1.8980, 1.8873, 1.8900)       # 125: the anchor, a new 120-bar low
    for h, l in ((1.8990, 1.8890), (1.9040, 1.8960), (1.9100, 1.9030), (1.9200, 1.9100), (1.9257, 1.9180)):
        bar(l + 0.0010, h, l, h - 0.0010)     # 126-130: the impulse; qualified at 129's close
    bar(1.9240, 1.9250, 1.9105, 1.9150)       # 131: first pullback; 38.2% level 1.9110312
    for _ in range(69):                       # 132-200: drift at 1.9200
        bar(1.9200, 1.9220, 1.9150, 1.9200)
    n = len(O)
    return {"O": O, "H": H, "L": L, "C": Cl}, [0.0120] * n, [1] * n


def selftest():
    ok = True

    def check(name, cond):
        nonlocal ok
        ok &= bool(cond)
        print(("PASS " if cond else "FAIL ") + name)

    def run(b, atr, tr, level=0.382, **kw):
        return find_entries(b["O"], b["H"], b["L"], atr, tr, level, **kw)

    # 1. The leg detector on the owner's leg
    b, atr, tr = _owner_bars()
    lvl = 1.9257 - 0.382 * (1.9257 - 1.8873)
    en, legs = run(b, atr, tr)
    check(f"owner's leg: one entry on bar 131 at the 38.2% level {lvl:.7f} ({en})",
          len(en) == 1 and en[0]["bar"] == 131 and abs(en[0]["fill"] - lvl) < 1e-12
          and en[0]["A"] == 1.8873 and en[0]["B"] == 1.9257 and en[0]["anchor_bar"] == 125)
    en50, legs50 = run(b, atr, tr, level=0.5)
    check(f"owner's leg: the 50% level (1.9065) is never reached, the leg expires ({dict(legs50)})",
          en50 == [] and legs50["expired qualified"] == 1)
    big = [0.0200] * len(atr)                 # 2 ATR = 0.0400 > the 0.0384 impulse
    en_s, legs_s = run(b, big, tr)
    check("an impulse below 2 D1 ATR never qualifies and never trades",
          en_s == [] and legs_s["qualified impulses"] == 0 and legs_s["anchors"] == 1)
    b2 = {k: list(v) for k, v in b.items()}
    b2["L"][10] = 1.8860                      # a lower low 115 bars before the anchor
    check("the anchor must be the lowest low of the previous 119 bars (a lower low 115 bars back blocks it)",
          run(b2, atr, tr)[0] == [])
    b2 = {k: list(v) for k, v in b.items()}
    b2["L"][125] = 1.8950                     # equal to the range lows: not strictly lower
    b2["L"][126] = 1.8960                     # (and the next bar stays above the range)
    check("an anchor must be strictly lower than the range (an equal low is not a new low)",
          run(b2, atr, tr)[0] == [])
    b2 = {k: list(v) for k, v in b.items()}
    b2["H"][125] = 1.9400                     # the anchor bar's own high came before its low
    en2, _ = run(b2, atr, tr)
    check("the anchor bar's own high is not part of the impulse",
          len(en2) == 1 and en2[0]["bar"] == 131 and en2[0]["B"] == 1.9257)
    b2 = {k: list(v) for k, v in b.items()}
    b2["H"][131] = 1.9300                     # the pullback bar first makes a new high
    en2, _ = run(b2, atr, tr)
    check("the resting order uses the extreme as of the previous close (a new high on the fill bar does not move it)",
          len(en2) == 1 and abs(en2[0]["fill"] - lvl) < 1e-12)
    b2 = {k: list(v) for k, v in b.items()}
    b2["O"][131] = 1.9100                     # the bar opens below the level: filled at the open
    en2, _ = run(b2, atr, tr)
    check("a gap below the level fills at the open, not the level",
          len(en2) == 1 and en2[0]["fill"] == 1.9100 and en2[0]["gap_open"])
    b2 = {k: list(v) for k, v in b.items()}
    b2["L"][129] = 1.9070                     # 129 dips while the leg is not yet qualified
    en2, _ = run(b2, atr, tr)
    check("no order rests before the impulse qualifies (a dip on the qualifying bar is not an entry)",
          len(en2) == 1 and en2[0]["bar"] == 131)
    b2 = {k: list(v) for k, v in b.items()}
    b2["L"][140] = 1.9100                     # a second touch later
    tr2 = list(tr)
    tr2[131] = -1                             # the first touch comes against the 13-week direction
    en2, lg2 = run(b2, atr, tr2)
    check(f"the first touch consumes the leg even when the trend filter blocks it ({dict(lg2)})",
          en2 == [] and lg2["touches against the 13-week direction (no trade)"] == 1)
    check("with the trend filter off, the same touch is an entry", len(run(b2, atr, tr2, use_trend=False)[0]) == 1)
    tr3 = list(tr)
    tr3[131] = 0
    check("a flat 13-week direction (0) is not 'with the trend'", run(b, atr, tr3)[0] == [])
    check("the leg window is inclusive: a fill 6 bars after the anchor needs window >= 6",
          run(b, atr, tr, window=5)[0] == [] and len(run(b, atr, tr, window=6)[0]) == 1)
    b2 = {k: list(v) for k, v in b.items()}
    b2["L"][127] = 1.8800                     # a lower low before the impulse qualifies replaces the leg
    _, lg2 = run(b2, atr, tr)
    check(f"a new lower low replaces a live leg ({dict(lg2)})",
          lg2["replaced by a lower low before a touch"] == 1 and lg2["anchors"] == 2)
    atr_w = list(atr)
    atr_w[125] = None
    check("no anchor while the context is warming up", run(b, atr_w, tr)[0] == [])

    # 2. Grading on the stop, horizon and the end of data
    stop = 1.8873 - 0.1 * 0.0120
    risk = lvl - stop
    g = grade(b["O"], b["H"], b["L"], b["C"], 131, lvl, stop, risk)
    want = (1.9200 - lvl) / risk
    check(f"timed exit: close of bar 131+30, R {g['raw']:.5f} = hand {want:.5f}",
          not g["stopped"] and g["exit_bar"] == 161 and abs(g["raw"] - want) < 1e-12)
    for j, stopped in ((161, True), (162, False)):
        L2 = list(b["L"])
        L2[j] = stop - 0.0001
        g = grade(b["O"], b["H"], L2, b["C"], 131, lvl, stop, risk)
        check(f"a stop touch on bar {j} ({j - 131} bars after the fill bar) is {'inside' if stopped else 'outside'} the horizon",
              g["stopped"] == stopped and (g["raw"] == -1.0) == stopped)
    L2 = list(b["L"])
    L2[131] = stop                            # the fill bar itself reaches the stop
    g = grade(b["O"], b["H"], L2, b["C"], 131, lvl, stop, risk)
    check("a stop reached on the fill bar is -1R, exit on that bar", g["stopped"] and g["raw"] == -1.0 and g["exit_bar"] == 131)
    O2, L2 = list(b["O"]), list(b["L"])
    O2[140], L2[140] = 1.8800, 1.8790         # a gap through the stop
    g = grade(O2, b["H"], L2, b["C"], 131, lvl, stop, risk)
    check(f"a gap through the stop is graded -1R; the gap loss {g['gap_r']:.3f}R is kept for the sensitivity",
          g["raw"] == -1.0 and abs(g["gap_r"] - (1.8800 - lvl) / risk) < 1e-12)
    g = grade(b["O"], b["H"], b["L"], b["C"], 131, 1.8850, stop, risk)
    check("a fill at or through the stop is a -1R loss at the intended risk",
          g["raw"] == -1.0 and g["gap_through_at_fill"] and g["risk"] == risk)
    check("a fill within 30 bars of the end of data is ungraded",
          grade(b["O"], b["H"], b["L"], b["C"][:161], 131, lvl, stop, risk) is None
          and grade(b["O"], b["H"], b["L"], b["C"][:162], 131, lvl, stop, risk) is not None)

    # 3. Short side mirrors the long side exactly
    mir = {k: [3.8 - x for x in v] for k, v in b.items()}
    mir["H"], mir["L"] = [3.8 - x for x in b["L"]], [3.8 - x for x in b["H"]]
    opens = [datetime(2006, 3, 6, 22, tzinfo=UTC) + timedelta(hours=4 * k) for k in range(len(b["O"]))]
    rates = {"GBP": [(date(2004, 1, 1), 4.5)], "JPY": [(date(2004, 1, 1), 0.5)], "AUD": [(date(2004, 1, 1), 5.5)]}
    bl = dict(b, opens=opens)
    bs = dict(mir, opens=opens)
    tl, _, _ = side_trades("GBP_AUD", bl, atr, tr, 0.382, 1, rates)
    ts, _, _ = side_trades("GBP_AUD", bs, atr, [-1] * len(tr), 0.382, -1, rates)
    check(f"the short side on mirrored bars gives the same raw R ({[t['raw'] for t in tl]} vs {[t['raw'] for t in ts]})",
          len(tl) == 1 and len(ts) == 1 and abs(tl[0]["raw"] - ts[0]["raw"]) < 1e-9 and ts[0]["side"] == -1
          and abs(tl[0]["risk_pips"] - ts[0]["risk_pips"]) < 1e-6)
    tl2, _, _ = side_trades("GBP_AUD", bl, atr, tr, 0.382, -1, rates)
    check("no short entry on the long-only leg", tl2 == [])
    t61, _, _ = side_trades("GBP_AUD", bl, atr, tr, 0.382, 1, rates, stop_kind="618")
    stop61 = 1.9257 - 0.618 * 0.0384 - 0.0012
    check(f"secondary stop: below the 61.8% level, risk {[round(t['risk_pips'], 1) for t in t61]} pips",
          len(t61) == 1 and abs(t61[0]["risk_pips"] - (lvl - stop61) / 0.0001) < 1e-6)

    # 4. Costs: era spread, financing by side, rollovers
    f = financed("GBP_JPY", 1, opens, 0, 30, False, 150.0, 100.0, rates)
    n = rollover_nights(opens[0], opens[30] + timedelta(hours=4))
    fin = 150.0 * (4.5 - 0.5 - 1.0) / 100 * n / 365 / 0.01 / 100.0
    check(f"GBP_JPY long 2006: spread -6 pips = -0.06R; financing (4.5-0.5-1.0)% over {n} nights = {fin:+.5f}R",
          abs(f["spread_r"] + 0.06) < 1e-12 and abs(f["fin_r"] - fin) < 1e-12 and f["nights"] == n)
    fs = financed("GBP_JPY", -1, opens, 0, 30, False, 150.0, 100.0, rates)
    fin_s = 150.0 * (-(4.5 - 0.5) - 1.0) / 100 * n / 365 / 0.01 / 100.0
    check(f"GBP_JPY short pays the gap plus the markup ({fs['fin_r']:+.5f}R)", abs(fs["fin_r"] - fin_s) < 1e-12 and fs["fin_r"] < 0)
    check("era spreads: GBP_AUD 10 pips in 2009, 7 in 2010; GBP_JPY 6 and 5",
          era_spread("GBP_AUD", 2009) == 10 and era_spread("GBP_AUD", 2010) == 7
          and era_spread("GBP_JPY", 2005) == 6 and era_spread("GBP_JPY", 2013) == 5)
    f3 = financed("GBP_AUD", 1, opens, 0, 30, False, 2.0, 100.0, rates, flat_spread=3.0)
    check("the flat 3.0-pip secondary replaces the era spread", abs(f3["spread_r"] + 0.03) < 1e-12)
    fstop = financed("GBP_JPY", 1, opens, 0, 0, True, 150.0, 100.0, rates)
    check("stopped on the fill bar: no rollover is charged", fstop["nights"] == 0 and fstop["fin_r"] == 0)
    # 2008-03-11 (Tue) 21:00 UTC open (17:00 EDT) to Fri 2008-03-14 21:00 UTC: Tue's rollover is at the
    # entry instant (not charged), Wed (x3), Thu, Fri (at the exit instant, charged) = 5
    check("rollovers: Tue 17:00 NY entry -> Fri 17:00 NY exit = Wed x3 + Thu + Fri = 5",
          rollover_nights(datetime(2008, 3, 11, 21, tzinfo=UTC), datetime(2008, 3, 14, 21, tzinfo=UTC)) == 5)
    check("adjusted R = raw R + spread R + financing R",
          len(tl) == 1 and abs(tl[0]["adj"] - (tl[0]["raw"] + tl[0]["spread_r"] + tl[0]["fin_r"])) < 1e-12)

    # 5. Context: completed sessions only
    d1, start = {}, date(2006, 1, 2)
    days = [start + timedelta(days=k) for k in range(200) if (start + timedelta(days=k)).weekday() < 5][:90]
    for k, d in enumerate(days):
        t = datetime(d.year, d.month, d.day, 17, 0, tzinfo=C.NY) - timedelta(days=1)
        c = 1.0 + 0.001 * k if k < 89 else 0.5   # rising closes; the last session collapses
        h, l = (c + 0.005, c - 0.005) if k < 89 else (1.2, 0.4)
        d1[t.astimezone(UTC)] = (c, h, l, c)
    sess = session_table(d1)
    t_last = sorted(d1)[89]                   # the last session's first H4 bar opens with its D1 candle
    a, trn = bar_context([t_last, t_last + timedelta(days=1)], sess)
    check(f"ATR and trend for a bar use only sessions before its own (ATR {a[0]:.4f}, trend {trn[0]})",
          abs(a[0] - 0.010) < 1e-9 and trn[0] == 1)
    check(f"the next session sees the collapse (ATR {a[1]:.4f}, trend {trn[1]})", a[1] > 0.05 and trn[1] == -1)
    a, trn = bar_context([sorted(d1)[14], sorted(d1)[65]], sess)
    check("warm-up: no ATR before 15 sessions, no trend before 66", a[0] is None and trn[1] is None)

    # 6. Episodes: first trade per 30-bar horizon on the bar index
    bars_at = [0, 10, 29, 30, 45, 59, 60, 61]
    eps = episodes([{"bar": k, "side": 1} for k in bars_at])
    check(f"episodes start at bars 0, 30, 60 ({[e['bar'] for e in eps]}), as episodes.count_episodes",
          [e["bar"] for e in eps] == [0, 30, 60] == count_episodes(bars_at, 30))
    eps = episodes([{"bar": 5, "side": -1}, {"bar": 5, "side": 1}])
    check("a same-bar long and short form one episode, the long first", len(eps) == 1 and eps[0]["side"] == 1)

    # 7. Statistics and the verdict rule
    check("max drawdown of +1 -1 -1 +2 -1 -1 -1 is 3R", max_drawdown([1, -1, -1, 2, -1, -1, -1]) == 3.0)
    check("rule: N<20 is INSUFFICIENT whatever the bound", classify(19, 0.5, 0.9, 0.4) == "INSUFFICIENT")
    check("rule: bound > 0 and without-best > 0 is SUPPORTED", classify(20, 0.001, 0.9, 0.01) == "SUPPORTED")
    check("rule: a bound of exactly 0 is not SUPPORTED", classify(20, 0.0, 0.9, 0.1) == "INCONCLUSIVE")
    check("rule: an outlier-driven mean (without-best <= 0) is not SUPPORTED", classify(40, 0.02, 0.9, 0.0) == "INCONCLUSIVE")
    check("rule: upper bound below +0.15R is REFUTED; at +0.15R it is not",
          classify(30, -0.6, 0.1499, -0.4) == "REFUTED" and classify(30, -0.6, 0.15, -0.4) == "INCONCLUSIVE")
    r = random.Random(11)
    z = [r.gauss(0, 1) for _ in range(100)]
    zm, zs = statistics.fmean(z), statistics.stdev(z)
    exact = [0.24 + 1.2 * (v - zm) / zs for v in z]   # mean +0.24, SD 1.2, N 100
    lo95 = bootstrap_lower_bound(exact, conf=0.95, iters=RESAMPLES, seed=SEED)
    s = summarize(exact)
    check(f"Bonferroni applied: the uncorrected 95% bound {lo95:+.3f} clears 0, the corrected "
          f"{CONF_LOWER:.4f} bound {s['lower']:+.3f} does not ({s['verdict']})",
          lo95 > 0 and s["lower"] < 0 and s["verdict"] == "INCONCLUSIVE")
    real = [max(-1.0, r.gauss(0.6, 1.2)) for _ in range(100)]
    check("a +0.6R edge at N=100 is SUPPORTED", summarize(real)["verdict"] == "SUPPORTED")
    bad = [max(-1.0, r.gauss(-0.4, 1.0)) for _ in range(60)]
    check("a clearly negative cell at N=60 is REFUTED", summarize(bad)["verdict"] == "REFUTED")
    false_pass = 0
    for k in range(150):
        null = [r.gauss(0, 1.2) for _ in range(60)]   # true mean 0
        lo = bootstrap_lower_bound(null, conf=CONF_LOWER, iters=1000, seed=k)
        false_pass += classify(60, lo, 1.0, statistics.fmean(sorted(null)[:-1])) == "SUPPORTED"
    check(f"a zero edge reads SUPPORTED in at most ~1.25% of runs ({false_pass}/150)", false_pass <= 6)

    # 8. Embargo, sealed exam and data integrity
    for t, refused in ((datetime(2013, 12, 30, 18, tzinfo=UTC), False),
                       (BLOCK_START, True), (datetime(2015, 6, 1, tzinfo=UTC), True),
                       (datetime(2021, 5, 3, tzinfo=UTC), True), (datetime(2004, 12, 31, 22, tzinfo=UTC), True)):
        try:
            check_window([t])
            got = False
        except RuntimeError:
            got = True
        check(f"bar opening {t.isoformat()} is {'refused' if refused else 'accepted'}", got == refused)
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "X.csv")
        with open(p, "w") as fh:
            fh.write("time_utc,o,h,l,c\n")
        good = {"X.csv": sha(p)}
        verify_hashes(td, good)
        with open(p, "a") as fh:
            fh.write("2006-01-02T22:00:00+00:00,1,1,1,1\n")
        try:
            verify_hashes(td, good)
            refused = False
        except RuntimeError:
            refused = True
        check("a data file whose sha256 differs from the pinned value is refused", refused)
    print("SELFTEST", "OK" if ok else "FAILED")
    return ok


# Stages ------------------------------------------------------------------------

def _prepare(data_dir):
    verify_hashes(data_dir)
    out = {}
    for pair in PAIRS:
        bars, sess, log = load_pair(data_dir, pair)
        atr, trend = bar_context(bars["opens"], sess)
        out[pair] = (bars, atr, trend, sess, log)
    return out


def counts(data_dir):
    """Counts only: legs, entries and episodes per cell. No R, no outcome, no stop."""
    print(f"Data hashes verified against the pinned values ({len(DATA_HASHES)} files).")
    for pair, (bars, atr, trend, sess, log) in _prepare(data_dir).items():
        o = bars["opens"]
        print(f"{pair}: H4 bars {len(o)} ({o[0].isoformat()} to {o[-1].isoformat()}); D1 sessions {len(sess[0])}; "
              f"weekend rule: {log['sunday_folded_h4']} Sunday H4 folded, {log['saturday_dropped_h4']} Saturday H4 dropped")
        for level in LEVELS:
            entries = {}
            for side, name in ((1, "long"), (-1, "short")):
                O, H, L, _, tr = (bars["O"], bars["H"], bars["L"], None, trend) if side == 1 else mirrored(bars, trend)
                en, legs = find_entries(O, H, L, atr, tr, level)
                graded = [e for e in en if e["bar"] + HORIZON < len(o)]
                entries[name] = [{"bar": e["bar"], "side": side, "day": C.session_day(o[e["bar"]])} for e in graded]
                print(f"  {level:.1%} {name}: {dict(sorted(legs.items()))}; graded entries {len(graded)}; "
                      f"ungraded at data end {len(en) - len(graded)}")
            eps = episodes(entries["long"] + entries["short"])
            per_year = Counter(e["day"].year for e in eps)
            n_long = sum(e["side"] == 1 for e in eps)
            print(f"  CELL {pair} {level:.1%}: entries {len(entries['long']) + len(entries['short'])}; "
                  f"EPISODES N {len(eps)} (long {n_long}, short {len(eps) - n_long}) -> {tier(len(eps))}; "
                  f"per year {dict(sorted(per_year.items()))}; episodes/yr {len(eps) / 9:.1f}")
            nf = []
            for side in (1, -1):
                O, H, L, _, tr = (bars["O"], bars["H"], bars["L"], None, trend) if side == 1 else mirrored(bars, trend)
                en, _ = find_entries(O, H, L, atr, tr, level, use_trend=False)
                nf += [{"bar": e["bar"], "side": side} for e in en if e["bar"] + HORIZON < len(o)]
            print(f"    secondary (no trend filter): episodes {len(episodes(nf))}")


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
        raise RuntimeError(f"{report} exists: the full run happens once (spec §11)")
    rates = load_rates()
    prepared = _prepare(data_dir)
    lines = ["# First pullback after a range turn — pre-registered test result (2005–2013 STUDY data)", "",
             f"Spec: docs/specs/first_pullback_study_spec.md. Verdict on episode R after era spread and "
             f"financing. Bonferroni one-sided lower bound at {CONF_LOWER:.4f} ({CELLS} cells), 90% upper "
             f"bound for REFUTED (bar +{REFUTE_BAR:.2f}R), {RESAMPLES} resamples, seed {SEED}. "
             f"Frame (data_map_spec §5): does this survive conditions it was not designed on.", ""]
    summary = []
    for pair, (bars, atr, trend, _, _) in prepared.items():
        lines += [f"## {pair}", ""]
        for level in LEVELS:
            trades, legs, ungraded = cell_trades(pair, bars, atr, trend, level, rates)
            eps = episodes(trades)
            rs = [e["adj"] for e in eps]
            s = summarize(rs)
            summary.append((pair, level, s))
            win = [x for x in rs if x > 0]
            loss = [x for x in rs if x <= 0]
            lines += [f"### {pair} {level:.1%}: **{s['verdict']}** ({tier(s['n'])})", "",
                      f"- **Primary (episode R after era spread and financing):** {_fmt(s)}; SD {s['sd']:.3f}",
                      f"- Median winner {statistics.median(win) if win else float('nan'):+.3f}R (N {len(win)}); "
                      f"median loser {statistics.median(loss) if loss else float('nan'):+.3f}R (N {len(loss)}); "
                      f"stopped {sum(e['stopped'] for e in eps)} of {len(eps)}",
                      f"- Costs per episode: spread {statistics.fmean(e['spread_r'] for e in eps):+.3f}R, financing "
                      f"{statistics.fmean(e['fin_r'] for e in eps):+.3f}R, mean nights "
                      f"{statistics.fmean(e['nights'] for e in eps):.1f}, mean risk "
                      f"{statistics.fmean(e['risk_pips'] for e in eps):.0f} pips" if eps else "- no episodes",
                      f"- Power at this N (SD {SD_ASSUMED}R assumed, α {ALPHA:.4f}): "
                      f"{100 * power_at_n(0.15, SD_ASSUMED, max(s['n'], 1), ALPHA):.0f}% for +0.15R; smallest edge "
                      f"detectable at 80% power {min_detectable_edge(SD_ASSUMED, max(s['n'], 1), 0.8, ALPHA):+.2f}R",
                      "", "**Secondary (never changes the verdict):**", "",
                      f"- Before costs: {_short([e['raw'] for e in eps])}",
                      f"- Flat {FLAT_SPREAD}-pip spread (present-day cost) + financing: "
                      f"{_fmt(summarize([e['raw'] + e['fin_r'] - FLAT_SPREAD / e['risk_pips'] for e in eps]))}",
                      f"- Stops filled at the gap open: {_short([e['gap_adj'] for e in eps])}; "
                      f"stops that gapped: {sum(e['gap_raw'] < -1 for e in eps)}; fills through the stop: "
                      f"{sum(e['gap_through_at_fill'] for e in eps)}"]
            for mk in (0.0, 2.0):
                t2, _, _ = cell_trades(pair, bars, atr, trend, level, rates, markup=mk)
                lines.append(f"- Financing markup {mk:.0f}%: {_short([e['adj'] for e in episodes(t2)])}")
            t618, _, _ = cell_trades(pair, bars, atr, trend, level, rates, stop_kind="618")
            e618 = episodes(t618)
            lines.append(f"- Secondary stop below the 61.8% level: {_fmt(summarize([e['adj'] for e in e618]))}; "
                         f"stopped {sum(e['stopped'] for e in e618)}")
            for side, name in ((1, "Long"), (-1, "Short")):
                lines.append(f"- {name} episodes: {_short([e['adj'] for e in eps if e['side'] == side])}")
            tnf, _, _ = cell_trades(pair, bars, atr, trend, level, rates, use_trend=False)
            lines.append(f"- No trend filter (every first touch): {_short([e['adj'] for e in episodes(tnf)])}")
            for name, lo, hi in SUBPERIODS:
                lines.append(f"- {name}: {_short([e['adj'] for e in eps if lo <= e['day'] <= hi])}")
            per_year = defaultdict(list)
            for e in eps:
                per_year[e["day"].year].append(e["adj"])
            lines.append("- By year (N, mean R): " + "; ".join(
                f"{y} {len(v)} {statistics.fmean(v):+.2f}" for y, v in sorted(per_year.items())))
            lines.append(f"- Legs: long {dict(sorted(legs['long'].items()))}; short {dict(sorted(legs['short'].items()))}; "
                         f"ungraded at data end {ungraded}")
            lines.append("")
    lines += ["## Summary", "", "| Cell | N | Mean R | Median R | Lower bound | Upper 90% | Without best | Max DD | Verdict |",
              "|---|---|---|---|---|---|---|---|---|"]
    for pair, level, s in summary:
        lines.append(f"| {pair} {level:.1%} | {s['n']} | {s['mean']:+.3f} | {s['median']:+.3f} | {s['lower']:+.3f} | "
                     f"{s['upper']:+.3f} | {s['without_best']:+.3f} | {s['max_dd']:.1f} | {s['verdict']} |")
    pooled = []
    for pair, (bars, atr, trend, _, _) in prepared.items():
        pooled += [e["adj"] for e in episodes(cell_trades(pair, bars, atr, trend, 0.382, rates)[0])]
    lines += ["", f"- Descriptive only: both pairs pooled at 38.2%: {_short(pooled)}; "
              f"N required for +0.15R at 80% power (SD {SD_ASSUMED}, α {ALPHA:.4f}): "
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
