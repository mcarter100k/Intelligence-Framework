"""Pre-registered test (BCS-1): does a second hourly close confirm a breakout?
(docs/specs/breakout_confirmation_study_spec.md)

Cells on GBP_AUD H1, long and short pooled in each:
  A  enter on the first close beyond the latest confirmed hourly swing (k = 5)
  B  enter on the second close beyond, if the first is not a fake
  C  after B confirms, a limit at the level for 12 bars (the retest)
Data: the research archive's STUDY span only (2005-2013), read through
research_archive.load. This runner never fetches anything and refuses any bar
in the embargo / sealed exam.

usage:
  python3 -I breakout_confirmation_study.py selftest
  python3 -I breakout_confirmation_study.py counts <archive_dir>
  python3 -I breakout_confirmation_study.py full <archive_dir> <report_md>

counts prints swing, event, fake, confirmation, retest, entry and episode
counts only (no R, no stop outcome). full runs once: it refuses if the report
file already exists or if any data file's sha256 differs from the pinned value.
"""
import bisect
import hashlib
import json
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
import history_study_convert as C  # noqa: E402  session day (17:00 New York)
from shadow_cost_regrade import rollover_nights  # noqa: E402  17:00 NY, Wednesday x3
from episodes import count_episodes  # noqa: E402  the framework's episode rule
from power_check import (bootstrap_lower_bound, bootstrap_upper_bound,  # noqa: E402
                         min_detectable_edge, n_required, power_at_n)

UTC = timezone.utc
PAIR, BASE, QUOTE, PIP = "GBP_AUD", "GBP", "AUD", 0.0001
K = 5                          # hourly swing: strict max of bars i-5 .. i+5 (spec §4.1)
STOP_ATR = 0.25                # stop beyond the level, in D1 ATR (spec §4.4)
ATR_SESSIONS = 14              # completed sessions only (spec §4.4)
HORIZON = 24                   # H1 bars after entry (spec §4.5)
RETEST_BARS = 12               # C limit rests on bars j+2 .. j+13 (spec §4.3)
ERA_SPREAD = {range(2005, 2010): 10.0, range(2010, 2014): 7.0}   # data_map_spec §4 (frozen)
FLAT_SPREADS = (3.0, 5.1)      # secondaries (spec §5)
MARKUP = 1.0                   # % a year (spec §5)
CELLS = ("A", "B", "C")
ALPHA = 0.05 / len(CELLS)      # Bonferroni, one-sided (spec §7)
CONF_LOWER = 1 - ALPHA         # 0.98333...
CONF_UPPER = 0.90              # the futility rule's bound (spec §7)
REFUTE_BAR = 0.15
RESAMPLES = 20000
SEED = 7
MIN_N = 20
SD_ASSUMED = 1.2
FIRST_OPEN = datetime(2005, 1, 1, tzinfo=UTC)
BLOCK_START = datetime(2013, 12, 30, 22, 0, tzinfo=UTC)   # embargo + SEALED EXAM start
DATA_HASHES = {   # research archive files, manifest built 2026-11-06 (spec §3)
    "GBP_AUD_H1.csv": "f170a0403ac306de24f3b5ca4910a6b66fec009da5de335e9f4f1a1ff8b36768",
    "GBP_AUD_D.csv": "24e4bbe9065a1c463464a174162fab38be6b5f583aef71e7e2306554680bf7f6",
}
SUBPERIODS = [("2005-01 to 2008-06 (before the crisis)", date(2005, 1, 1), date(2008, 6, 30)),
              ("2008-07 to 2009-06 (the crisis)", date(2008, 7, 1), date(2009, 6, 30)),
              ("2009-07 to 2013-12 (after)", date(2009, 7, 1), date(2013, 12, 31))]
SESSIONS = (("Asia 22-07 UTC", (22, 23, 0, 1, 2, 3, 4, 5, 6)), ("London 07-12 UTC", (7, 8, 9, 10, 11)),
            ("London/New York 12-17 UTC", (12, 13, 14, 15, 16)), ("late New York 17-22 UTC", (17, 18, 19, 20, 21)))


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
    for t in times:
        if t < FIRST_OPEN or t >= BLOCK_START:
            raise RuntimeError(f"bar {t.isoformat()} is outside the STUDY partition: refused")


def load_data(archive_dir):
    import research_archive as RA
    verify_hashes(archive_dir)
    h1 = RA.load(archive_dir, PAIR, "H1", {"STUDY"})
    d1 = RA.load(archive_dir, PAIR, "D", {"STUDY"})
    check_window(h1)
    check_window(d1)
    opens = sorted(h1)
    bars = {"opens": opens, "O": [h1[t][0] for t in opens], "H": [h1[t][1] for t in opens],
            "L": [h1[t][2] for t in opens], "C": [h1[t][3] for t in opens]}
    return bars, bar_atr(opens, session_table(d1))


def load_rates(path=os.path.join(HERE, "policy_rates_2003_2014.json")):
    with open(path) as fh:
        raw = json.load(fh)
    return {ccy: [(date.fromisoformat(d), v) for d, v in raw[ccy]["changes"]] for ccy in (BASE, QUOTE)}


def rate_on(rates, ccy, day):
    val = None
    for d, v in rates[ccy]:
        if d <= day:
            val = v
    if val is None:
        raise ValueError(f"no {ccy} rate on {day}")
    return val


def era_spread(year):
    for yrs, v in ERA_SPREAD.items():
        if year in yrs:
            return v
    raise ValueError(f"no spread for {year}")


def session_table(d1):
    """D1 {open: (o,h,l,c)} -> (session days, true ranges). TR[0] is None."""
    ts = sorted(d1)
    days = [C.session_day(t) for t in ts]
    trs = [None]
    for k in range(1, len(ts)):
        _, h, l, _ = d1[ts[k]]
        pc = d1[ts[k - 1]][3]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return days, trs


def bar_atr(opens, sess):
    """Per H1 bar: D1 ATR from the ATR_SESSIONS sessions completed before the bar's own
    session. None while warming up."""
    days, trs = sess
    out = []
    for t in opens:
        k = bisect.bisect_left(days, C.session_day(t))
        out.append(statistics.fmean(trs[k - ATR_SESSIONS:k]) if k - ATR_SESSIONS >= 1 else None)
    return out


# Levels, events and entries (written for the long side; the short side is the mirror) --

def confirmed_swings(H, k=K):
    """Swing highs as (confirm_bar, swing_bar, price), in confirmation order."""
    out = []
    for i in range(k, len(H) - k):
        if all(H[i] > H[x] for x in range(i - k, i + k + 1) if x != i):
            out.append((i + k, i, H[i]))
    return out


def find_events(C_, H, k=K):
    """Events (fresh closes above the live level) and confirmations (spec §4.1-4.3)."""
    sw = confirmed_swings(H, k)
    events, counts = [], Counter()
    level, si, n = None, 0, len(C_)
    for j in range(n):
        while si < len(sw) and sw[si][0] < j:       # confirmed at a close before bar j
            if level is not None and level["live"]:
                counts["levels replaced unbroken"] += 1
            level = {"price": sw[si][2], "first": sw[si][0] + 1, "live": True}
            counts["swings confirmed"] += 1
            si += 1
        if level is None or not level["live"] or j < level["first"]:
            continue
        lvl = level["price"]
        if C_[j] > lvl and C_[j - 1] <= lvl:
            ev = {"bar": j, "level": lvl, "fake": None}
            if j + 1 < n:
                ev["fake"] = C_[j + 1] <= lvl
                if not ev["fake"]:
                    level["live"] = False
                    counts["levels broken (confirmed)"] += 1
            else:
                counts["events on the last bar (not traded)"] += 1
            events.append(ev)
    return events, counts


def retest_fill(O, L, conf_bar, lvl, window=RETEST_BARS):
    """The C limit: bars conf_bar+1 .. conf_bar+window. Returns (fill bar, price) or
    (None, 'expired' | 'end of data')."""
    for f in range(conf_bar + 1, conf_bar + 1 + window):
        if f >= len(O):
            return None, "end of data"
        if L[f] <= lvl:
            return f, min(O[f], lvl)
    return None, "expired"


def grade_close_entry(O, L, C_, e, entry, stop, horizon=HORIZON):
    """Entry at the close of bar e; the stop is checked on e+1 .. e+horizon (spec §4.5)."""
    if e + horizon >= len(C_):
        return None
    risk = entry - stop
    for b in range(e + 1, e + horizon + 1):
        if L[b] <= stop:
            return {"raw": -1.0, "gap_r": (min(O[b], stop) - entry) / risk, "exit_bar": b,
                    "stopped": True, "gapped": O[b] <= stop, "risk": risk}
    return {"raw": (C_[e + horizon] - entry) / risk, "gap_r": (C_[e + horizon] - entry) / risk,
            "exit_bar": e + horizon, "stopped": False, "gapped": False, "risk": risk}


def grade_limit_fill(O, L, C_, f, entry, stop, intended_risk, horizon=HORIZON):
    """C: the fill bar f is bar 0; the stop is checked on f .. f+horizon (spec §4.5)."""
    if f + horizon >= len(C_):
        return None
    if entry <= stop:
        return {"raw": -1.0, "gap_r": -1.0, "exit_bar": f, "stopped": True, "gapped": True,
                "risk": intended_risk}
    risk = entry - stop
    for b in range(f, f + horizon + 1):
        if L[b] <= stop:
            gap_r = (min(O[b], stop) - entry) / risk if b > f else -1.0
            return {"raw": -1.0, "gap_r": gap_r, "exit_bar": b, "stopped": True,
                    "gapped": b > f and O[b] <= stop, "risk": risk}
    raw = (C_[f + horizon] - entry) / risk
    return {"raw": raw, "gap_r": raw, "exit_bar": f + horizon, "stopped": False, "gapped": False,
            "risk": risk}


def mirrored(bars):
    """The short side as a long side: negate prices (high <-> low)."""
    return ([-x for x in bars["O"]], [-x for x in bars["L"]], [-x for x in bars["H"]],
            [-x for x in bars["C"]])


def costs(side, opens, entry_bar, at_close, exit_bar, stopped, entry_price, risk_pips, rates,
          markup=MARKUP):
    """Era spread and financing in R (spec §5)."""
    entry_time = opens[entry_bar] + (timedelta(hours=1) if at_close else timedelta(0))
    exit_time = opens[exit_bar] if stopped else opens[exit_bar] + timedelta(hours=1)
    nights = rollover_nights(entry_time, exit_time)
    day = C.session_day(opens[entry_bar])
    net = side * (rate_on(rates, BASE, day) - rate_on(rates, QUOTE, day)) - markup
    fin_pips = entry_price * net / 100 * nights / 365 / PIP
    return {"nights": nights, "risk_pips": risk_pips, "spread_r": -era_spread(day.year) / risk_pips,
            "fin_r": fin_pips / risk_pips, "day": day}


def side_trades(bars, atr, side, rates):
    """Graded trades per cell for one side, plus event records and counts."""
    if side == 1:
        O, H, L, C_ = bars["O"], bars["H"], bars["L"], bars["C"]
    else:
        O, H, L, C_ = mirrored(bars)
    events, counts = find_events(C_, H)
    trades = {c: [] for c in CELLS}

    def record(cell, e, at_close, px, g, ev, extra=None):
        """px is the entry on the side's own (possibly negated) scale; stored as a real price."""
        t = costs(side, bars["opens"], e, at_close, g["exit_bar"], g["stopped"], abs(px), g["risk"] / PIP, rates)
        t.update({"cell": cell, "bar": e, "side": side, "event_bar": ev["bar"], "fake": ev["fake"],
                  "entry_px": side * px, "raw": g["raw"], "gap_raw": g["gap_r"], "stopped": g["stopped"],
                  "gapped": g["gapped"], "hour": (bars["opens"][ev["bar"]] + timedelta(hours=1)).hour})
        t.update(extra or {})
        t["adj"] = t["raw"] + t["spread_r"] + t["fin_r"]
        t["gap_adj"] = t["gap_raw"] + t["spread_r"] + t["fin_r"]
        trades[cell].append(t)

    for ev in events:
        if ev["fake"] is None:
            continue
        j, lvl = ev["bar"], ev["level"]
        if atr[j] is None:
            counts["A: events in ATR warm-up (no trade)"] += 1
        else:
            g = grade_close_entry(O, L, C_, j, C_[j], lvl - STOP_ATR * atr[j])
            if g is None:
                counts["A: ungraded at end of data"] += 1
            else:
                record("A", j, True, C_[j], g, ev)
        if ev["fake"]:
            continue
        e = j + 1
        f, px = retest_fill(O, L, e, lvl)
        counts["C: retest filled" if f is not None else f"C: {px}"] += 1
        if atr[e] is None:
            counts["B: confirmations in ATR warm-up (no trade)"] += 1
        else:
            g = grade_close_entry(O, L, C_, e, C_[e], lvl - STOP_ATR * atr[e])
            if g is None:
                counts["B: ungraded at end of data"] += 1
            else:
                record("B", e, True, C_[e], g, ev, {"retested": f is not None, "a_entry_px": side * C_[j],
                                                    "atr": atr[e]})
        if f is None:
            continue
        if atr[f] is None:
            counts["C: fills in ATR warm-up (no trade)"] += 1
            continue
        stop = lvl - STOP_ATR * atr[f]
        g = grade_limit_fill(O, L, C_, f, px, stop, lvl - stop)
        if g is None:
            counts["C: ungraded at end of data"] += 1
        else:
            record("C", f, False, px, g, ev)
    return trades, events, counts


def all_trades(bars, atr, rates):
    trades = {c: [] for c in CELLS}
    events, counts = {}, {}
    for side in (1, -1):
        t, ev, cnt = side_trades(bars, atr, side, rates)
        for c in CELLS:
            trades[c] += t[c]
        events[side], counts[side] = ev, cnt
    return trades, events, counts


def episodes(trades, horizon=HORIZON):
    """First trade per independent episode on the H1 bar index (spec §6). Ties: long first."""
    out = []
    for t in sorted(trades, key=lambda x: (x["bar"], -x["side"])):
        if not out or t["bar"] - out[-1]["bar"] >= horizon:
            out.append(t)
    return out


def ties(trades):
    by = Counter(t["bar"] for t in trades)
    return sum(1 for b, n in by.items() if n > 1 and len({t["side"] for t in trades if t["bar"] == b}) > 1)


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


def with_spread(t, spread):
    return t["raw"] - spread / t["risk_pips"] + t["fin_r"]


# Self-test ---------------------------------------------------------------------

def _bars(rows, start=datetime(2008, 1, 7, 10, tzinfo=UTC)):
    """rows of (o, h, l, c) -> bars dict on consecutive hours."""
    return {"opens": [start + timedelta(hours=i) for i in range(len(rows))],
            "O": [r[0] for r in rows], "H": [r[1] for r in rows], "L": [r[2] for r in rows],
            "C": [r[3] for r in rows]}


def _friday_rows():
    """The 2026-11-13 shape on one level: swing high 1.0050 at bar 10 (confirmed at 15,
    usable from 16), four fakes, then a confirmation at bars 28-29."""
    flat = (1.0000, 1.0010, 0.9990, 1.0000)
    rows = [flat] * 10 + [(1.0000, 1.0050, 0.9995, 1.0040)] + [flat] * 9
    closes = (1.0055, 1.0045, 1.0052, 1.0049, 1.0053, 1.0048, 1.0054, 1.0047)   # bars 20-27
    rows += [(1.0045, 1.0060, 1.0042, c) for c in closes]                     # equal highs: no swing
    rows += [(1.0050, 1.0062, 1.0045, 1.0060), (1.0058, 1.0062, 1.0052, 1.0058)]   # 28 event, 29 confirms
    rows += [(1.0050, 1.0055, 1.0035, 1.0040), (1.0040, 1.0066, 1.0040, 1.0065)]   # 30-31: level ended
    rows += [(1.0060, 1.0062, 1.0055, 1.0060)] * 30
    return rows


def selftest():
    fails = []

    def check(name, cond):
        print(("ok   " if cond else "FAIL ") + name)
        if not cond:
            fails.append(name)

    flat = (1.0000, 1.0010, 0.9990, 1.0000)
    rates = {BASE: [(date(2000, 1, 1), 5.0)], QUOTE: [(date(2000, 1, 1), 6.0)]}

    # Swings: strict, k = 5, confirmation delay -------------------------------------
    H = [1.0010] * 30
    H[10] = 1.0050
    check("swing found at bar 10, confirmed at bar 15", confirmed_swings(H) == [(15, 10, 1.0050)])
    H2 = list(H)
    H2[12] = 1.0050
    check("equal highs inside the window are not a swing", confirmed_swings(H2) == [])
    H3 = list(H)
    H3[15] = 1.0051
    check("a higher high 5 bars right kills the swing", (15, 10, 1.0050) not in confirmed_swings(H3))
    H4 = list(H)
    H4[16] = 1.0051
    check("a higher high 6 bars right does not", (15, 10, 1.0050) in confirmed_swings(H4))

    # Events: confirmation delay, fresh close, replacement ---------------------------
    rows = [flat] * 10 + [(1.0000, 1.0050, 0.9995, 1.0040)] + [flat] * 4
    rows += [(1.0040, 1.0049, 1.0030, 1.0045), (1.0045, 1.0060, 1.0040, 1.0055)] + [flat] * 10
    b = _bars(rows)
    ev, _ = find_events(b["C"], b["H"])
    check("first possible event is bar 16 (usable after the confirming close)",
          [e["bar"] for e in ev] == [16] and ev[0]["level"] == 1.0050)
    rows_eq = list(rows)
    rows_eq[17] = (1.0055, 1.0056, 1.0049, 1.0050)
    b = _bars(rows_eq)
    check("a next close exactly at the level is a fake (back 'at or inside')",
          find_events(b["C"], b["H"])[0][0]["fake"] is True)
    rows_pre = list(rows)
    rows_pre[15] = (1.0045, 1.0049, 1.0040, 1.0049)
    rows_pre[16] = (1.0049, 1.0049, 1.0040, 1.0048)
    b = _bars(rows_pre)
    check("no event when no close goes beyond", find_events(b["C"], b["H"])[0] == [])
    rows_c = [flat] * 10 + [(1.0000, 1.0050, 0.9995, 1.0040)] + [flat] * 9
    rows_c += [(1.0000, 1.0030, 0.9995, 1.0020)] + [flat] * 9          # swing 1.0030 at 20, conf 25
    rows_c += [(1.0030, 1.0040, 1.0025, 1.0035)] + [flat] * 3 + [(1.0040, 1.0055, 1.0040, 1.0052)] + [flat] * 5
    b = _bars(rows_c)
    ev, cnt = find_events(b["C"], b["H"])
    check("a newer swing replaces the live level (event on 1.0030, not 1.0050)",
          ev[0]["bar"] == 30 and ev[0]["level"] == 1.0030 and cnt["levels replaced unbroken"] == 1)

    # The Friday replica: four fakes then a confirmation ------------------------------
    b = _bars(_friday_rows())
    ev, cnt = find_events(b["C"], b["H"])
    check("Friday replica: five events at 20, 22, 24, 26, 28", [e["bar"] for e in ev] == [20, 22, 24, 26, 28])
    check("Friday replica: four fakes, one confirmation", [e["fake"] for e in ev] == [True] * 4 + [False])
    check("Friday replica: the level ends at the confirmation (no event at 31)",
          cnt["levels broken (confirmed)"] == 1 and all(e["bar"] != 31 for e in ev))
    atr = [0.0040] * len(b["O"])
    tr, _, _ = side_trades(b, atr, 1, rates)
    check("Friday replica: A enters five times at the event closes",
          [t["bar"] for t in tr["A"]] == [20, 22, 24, 26, 28] and tr["A"][0]["entry_px"] == 1.0055)
    check("Friday replica: B enters once at bar 29's close 1.0058",
          [(t["bar"], t["entry_px"]) for t in tr["B"]] == [(29, 1.0058)])
    check("Friday replica: C fills at the level on bar 30 (low 1.0035)",
          [(t["bar"], t["entry_px"]) for t in tr["C"]] == [(30, 1.0050)])
    check("stop = level - 0.25 ATR (C risk 10 pips)", abs(tr["C"][0]["risk_pips"] - 10.0) < 1e-6)
    check("C fill bar 30 low 1.0035 is below the stop 1.0040: stopped on the fill bar",
          tr["C"][0]["stopped"] and tr["C"][0]["raw"] == -1.0 and tr["C"][0]["gap_raw"] == -1.0)

    # The C limit ------------------------------------------------------------------
    O = [1.0060] * 40
    L = [1.0055] * 40
    L[13] = 1.0048
    check("retest fills at the level", retest_fill(O, L, 10, 1.0050) == (13, 1.0050))
    O2 = list(O)
    O2[13] = 1.0045
    check("retest fills at the open on a gap below the level", retest_fill(O2, L, 10, 1.0050) == (13, 1.0045))
    L3 = [1.0055] * 40
    L3[22] = 1.0049
    check("bar conf+12 is inside the window", retest_fill(O, L3, 10, 1.0050) == (22, 1.0050))
    L4 = [1.0055] * 40
    L4[23] = 1.0049
    check("bar conf+13 is outside the window", retest_fill(O, L4, 10, 1.0050) == (None, "expired"))
    check("window running off the data", retest_fill(O[:15], L[:15], 10, 1.0040) == (None, "end of data"))
    g = grade_limit_fill([1.0035] + [1.0060] * 30, [1.0030] + [1.0055] * 30, [1.0060] * 31, 0, 1.0035,
                         1.0040, 0.0010)
    check("a fill through the stop is -1R at the intended risk",
          g["raw"] == -1.0 and abs(g["risk"] - 0.0010) < 1e-12)

    # Grading (close entries) ------------------------------------------------------
    n = 30
    O, L, Cl = [1.0100] * n, [1.0060] * n, [1.0100] * n
    Cl[24] = 1.0150
    g = grade_close_entry(O, L, Cl, 0, 1.0100, 1.0050)
    check("timed exit by hand: (1.0150 - 1.0100) / 0.0050 = +1R",
          abs(g["raw"] - 1.0) < 1e-9 and g["exit_bar"] == 24 and not g["stopped"])
    L2 = list(L)
    L2[24] = 1.0050
    g = grade_close_entry(O, L2, Cl, 0, 1.0100, 1.0050)
    check("a stop touch on bar 24 after entry is inside the horizon", g["stopped"] and g["exit_bar"] == 24)
    L3 = list(L)
    L3[25] = 1.0040
    g = grade_close_entry(O, L3, Cl, 0, 1.0100, 1.0050)
    check("a stop touch on bar 25 is outside the horizon", not g["stopped"] and abs(g["raw"] - 1.0) < 1e-9)
    O4, L4 = list(O), list(L)
    O4[5], L4[5] = 1.0030, 1.0020
    g = grade_close_entry(O4, L4, Cl, 0, 1.0100, 1.0050)
    check("a gap through the stop: -1R, gap loss -1.4R", g["raw"] == -1.0 and abs(g["gap_r"] + 1.4) < 1e-9
          and g["gapped"])
    L5 = list(L)
    L5[0] = 1.0000
    g = grade_close_entry(O, L5, Cl, 0, 1.0100, 1.0050)
    check("the entry bar's own low is not checked (entry at its close)", not g["stopped"])
    check("ungraded when the horizon runs past the data", grade_close_entry(O, L, Cl, 6, 1.01, 1.005) is None)

    # The short mirror -------------------------------------------------------------
    b = _bars(_friday_rows())
    mir = _bars([(2 - o, 2 - l, 2 - h, 2 - c) for o, h, l, c in _friday_rows()])
    atr = [0.0040] * len(b["O"])
    lt, _, _ = side_trades(b, atr, 1, rates)
    st, _, _ = side_trades(mir, atr, -1, rates)
    check("the short mirror gives identical raw R in every cell",
          all([round(t["raw"], 9) for t in lt[c]] == [round(t["raw"], 9) for t in st[c]] for c in CELLS)
          and len(st["A"]) == 5)
    check("short trades store real prices (B entry 2 - 1.0058)",
          [round(t["entry_px"], 9) for t in st["B"]] == [round(2 - 1.0058, 9)])

    # Costs ------------------------------------------------------------------------
    check("era spreads: 2009 10.0, 2010 7.0", era_spread(2009) == 10.0 and era_spread(2010) == 7.0)
    check("secondary flat spreads 3.0 and 5.1", FLAT_SPREADS == (3.0, 5.1))
    opens = [datetime(2008, 1, 7, 10, tzinfo=UTC) + timedelta(hours=i) for i in range(30)]
    c = costs(1, opens, 0, True, 24, False, 2.0, 50.0, rates)
    # long: net = (5 - 6) - 1 = -2 % a year; 1 night (Mon 17:00 NY); 2.0 x -0.02 / 365 / 0.0001
    check("long financing by hand: -1.0959 pips over 1 night",
          c["nights"] == 1 and abs(c["fin_r"] * 50.0 + 2.0 * 0.02 / 365 / PIP) < 1e-9)
    c = costs(-1, opens, 0, True, 24, False, 2.0, 50.0, rates)
    check("short financing by hand: net -(5-6) - 1 = 0", c["nights"] == 1 and abs(c["fin_r"]) < 1e-12)
    check("spread in R: -10 / 50 = -0.2 in 2008", abs(c["spread_r"] + 0.2) < 1e-12)
    opens2 = [datetime(2008, 1, 7, 21, tzinfo=UTC) + timedelta(hours=i) for i in range(3)]
    c = costs(1, opens2, 0, True, 1, True, 2.0, 50.0, rates)
    check("A/B entry instant is the bar close: the 17:00 NY rollover at that close is not charged",
          c["nights"] == 0)
    c = costs(1, opens2, 0, False, 1, True, 2.0, 50.0, rates)
    check("C entry instant is the bar open: the same rollover is charged", c["nights"] == 1)

    # Context: ATR from completed sessions only -------------------------------------
    d1 = {}
    t0 = datetime(2008, 1, 6, 22, tzinfo=UTC)          # Monday 2008-01-07 session
    day, k = t0, 0
    while k < 16:
        if C.session_day(day).weekday() < 5:
            d1[day] = (1.0, 1.0 + 0.0010 * (k + 1), 1.0, 1.0)
            k += 1
        day += timedelta(days=1)
    ts = sorted(d1)
    sess = session_table(d1)
    a = bar_atr([ts[15] + timedelta(hours=3)], sess)[0]
    check("ATR for a bar in session 16 = mean TR of sessions 2-15", abs(a - statistics.fmean(
        [0.0010 * (k + 1) for k in range(1, 15)])) < 1e-12)
    check("ATR warm-up: a bar in session 15 has no ATR", bar_atr([ts[14] + timedelta(hours=3)], sess)[0] is None)
    d1b = dict(d1)
    d1b[ts[15]] = (1.0, 1.5, 1.0, 1.0)
    check("the bar's own session does not enter its ATR",
          bar_atr([ts[15] + timedelta(hours=3)], session_table(d1b))[0] == a)

    # Episodes ---------------------------------------------------------------------
    fake = [{"bar": x, "side": 1} for x in (0, 5, 23, 24, 30, 47, 48, 100)]
    got = [t["bar"] for t in episodes(fake)]
    check("episode collapse matches episodes.count_episodes", got == count_episodes([0, 5, 23, 24, 30, 47, 48, 100], 24)
          and got == [0, 24, 48, 100])
    check("same-bar tie: long first", episodes([{"bar": 3, "side": -1}, {"bar": 3, "side": 1}])[0]["side"] == 1)

    # Verdict rule -----------------------------------------------------------------
    check("Bonferroni over 3 cells: 0.98333", abs(CONF_LOWER - (1 - 0.05 / 3)) < 1e-12)
    check("N 19 is INSUFFICIENT", classify(19, 1.0, 2.0, 1.0) == "INSUFFICIENT")
    check("lower > 0 and without-best > 0 is SUPPORTED", classify(20, 0.01, 1.0, 0.01) == "SUPPORTED")
    check("lower > 0 but without-best <= 0 is not SUPPORTED", classify(20, 0.01, 1.0, 0.0) == "INCONCLUSIVE")
    check("upper just under +0.15 is REFUTED", classify(20, -0.5, 0.1499, -0.2) == "REFUTED")
    check("upper at +0.15 is INCONCLUSIVE", classify(20, -0.5, 0.15, -0.2) == "INCONCLUSIVE")
    rng = random.Random(11)
    pos = [max(-1.0, rng.gauss(0.6, 1.2)) for _ in range(400)]
    neg = [max(-1.0, rng.gauss(-0.2, 1.0)) for _ in range(400)]
    check("a known +0.6R edge is SUPPORTED", summarize(pos, iters=2000)["verdict"] == "SUPPORTED")
    check("a -0.2R process (clipped at -1R) is REFUTED", summarize(neg, iters=2000)["verdict"] == "REFUTED")

    # Refusals ---------------------------------------------------------------------
    try:
        check_window([BLOCK_START])
        check("a bar at the embargo start is refused", False)
    except RuntimeError:
        check("a bar at the embargo start is refused", True)
    try:
        check_window([datetime(2004, 12, 31, 22, tzinfo=UTC)])
        check("a bar before 2005 is refused", False)
    except RuntimeError:
        check("a bar before 2005 is refused", True)
    check_window([BLOCK_START - timedelta(hours=1)])
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "x.csv"), "w") as fh:
            fh.write("tampered")
        try:
            verify_hashes(td, {"x.csv": "0" * 64})
            check("a data-hash mismatch is refused", False)
        except RuntimeError:
            check("a data-hash mismatch is refused", True)

    print("SELFTEST OK" if not fails else f"SELFTEST FAILED: {len(fails)}")
    return not fails


# Stages ------------------------------------------------------------------------

def _prepare(archive_dir):
    bars, atr = load_data(archive_dir)
    return bars, atr, load_rates()


def counts(archive_dir):
    bars, atr, rates = _prepare(archive_dir)
    trades, events, cnt = all_trades(bars, atr, rates)
    opens = bars["opens"]
    print(f"BCS-1 counts (no R, no stop outcome). GBP_AUD H1 STUDY bars: {len(opens)}, "
          f"{opens[0].isoformat()} -> {opens[-1].isoformat()}")
    for side, name in ((1, "long (swing highs, closes above)"), (-1, "short (swing lows, closes below)")):
        ev = events[side]
        done = [e for e in ev if e["fake"] is not None]
        fakes = sum(e["fake"] for e in done)
        print(f"\n## {name}")
        for k in sorted(cnt[side]):
            print(f"- {k}: {cnt[side][k]}")
        print(f"- events (first closes beyond): {len(ev)}; fakes {fakes}; confirmations {len(done) - fakes}; "
              f"fake rate {fakes / len(done):.3f}")
    print("\n## Fake rate by year (both sides)")
    by = defaultdict(lambda: [0, 0])
    for side in (1, -1):
        for e in events[side]:
            if e["fake"] is not None:
                y = opens[e["bar"]].year
                by[y][0] += 1
                by[y][1] += e["fake"]
    for y in sorted(by):
        print(f"- {y}: events {by[y][0]}, fakes {by[y][1]}, rate {by[y][1] / by[y][0]:.3f}")
    print("\n## Entries and episodes per cell")
    for c in CELLS:
        ep = episodes(trades[c])
        print(f"- {c}: graded entries {len(trades[c])} (long {sum(t['side'] == 1 for t in trades[c])}, "
              f"short {sum(t['side'] == -1 for t in trades[c])}); episodes {len(ep)} "
              f"(long {sum(t['side'] == 1 for t in ep)}, short {sum(t['side'] == -1 for t in ep)}); "
              f"same-bar long/short ties {ties(trades[c])}")
        yr = Counter(t["day"].year for t in ep)
        print("  episodes by year: " + ", ".join(f"{y} {yr[y]}" for y in sorted(yr)))
        print(f"  power at N {len(ep)}: +0.15R {power_at_n(0.15, SD_ASSUMED, len(ep), alpha=ALPHA):.3f}; "
              f"smallest edge at 80% {min_detectable_edge(SD_ASSUMED, len(ep), alpha=ALPHA):.3f}R")
    print(f"\nN required for +0.15R at 80% power (alpha {ALPHA:.5f}): {n_required(0.15, SD_ASSUMED, alpha=ALPHA)}")


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
    bars, atr, rates = _prepare(archive_dir)
    trades, events, cnt = all_trades(bars, atr, rates)
    out = []
    p = out.append
    p("# BCS-1 result: does a second hourly close confirm a breakout? (GBP/AUD, 2005-2013 STUDY)")
    p("")
    p(f"Spec: docs/specs/breakout_confirmation_study_spec.md. Verdict on episode R after era spread and "
      f"financing. Bonferroni one-sided lower bound at {CONF_LOWER:.5f} (3 cells), 90% upper bound for "
      f"REFUTED (bar +0.15R), {RESAMPLES} resamples, seed {SEED}. Frame (data_map_spec §5): does this "
      f"survive conditions it was not designed on.")
    p("")
    p("## Verdicts (era spread + financing, episodes)")
    p("")
    eps = {c: episodes(trades[c]) for c in CELLS}
    for c in CELLS:
        rs = [t["adj"] for t in eps[c]]
        s = summarize(rs)
        e = eps[c]
        p(f"### Cell {c}: **{s['verdict']}**")
        p("")
        p(f"- {_fmt(s)}")
        p(f"- stop-outs {sum(t['stopped'] for t in e)} ({sum(t['stopped'] for t in e) / len(e):.1%}); "
          f"mean risk {statistics.fmean(t['risk_pips'] for t in e):.1f} pips; mean spread "
          f"{statistics.fmean(t['spread_r'] for t in e):+.3f}R; mean financing "
          f"{statistics.fmean(t['fin_r'] for t in e):+.4f}R; mean nights {statistics.fmean(t['nights'] for t in e):.2f}")
        p(f"- power at this N: +0.15R {power_at_n(0.15, SD_ASSUMED, len(e), alpha=ALPHA):.3f}; smallest "
          f"edge at 80% {min_detectable_edge(SD_ASSUMED, len(e), alpha=ALPHA):.3f}R")
        p(f"- before costs: {_short([t['raw'] for t in e])}")
        for sp in FLAT_SPREADS:
            p(f"- flat {sp} pips + financing: {_fmt(summarize([with_spread(t, sp) for t in e]))}")
        p(f"- stops at the gap open: {_short([t['gap_adj'] for t in e])}; bars opening through the stop "
          f"{sum(t['gapped'] for t in e)}")
        p(f"- long: {_short([t['adj'] for t in e if t['side'] == 1])}; short: "
          f"{_short([t['adj'] for t in e if t['side'] == -1])}")
        for name, a, b in SUBPERIODS:
            p(f"- {name}: {_short([t['adj'] for t in e if a <= t['day'] <= b])}")
        yr = defaultdict(list)
        for t in e:
            yr[t["day"].year].append(t["adj"])
        p("- by year: " + "; ".join(f"{y} N {len(v)} {statistics.fmean(v):+.3f}R" for y, v in sorted(yr.items())))
        p("")
    p("## Secondary (descriptive; never changes a verdict)")
    p("")
    allev = [e for s in (1, -1) for e in events[s] if e["fake"] is not None]
    fk = sum(e["fake"] for e in allev)
    p(f"1. **Fake rate:** {fk} of {len(allev)} first closes were followed by a close back inside: "
      f"**{fk / len(allev):.1%}**. Long {sum(e['fake'] for e in events[1] if e['fake'] is not None)} of "
      f"{sum(e['fake'] is not None for e in events[1])}; short "
      f"{sum(e['fake'] for e in events[-1] if e['fake'] is not None)} of {sum(e['fake'] is not None for e in events[-1])}.")
    a_f = [t["adj"] for t in trades["A"] if t["fake"]]
    a_c = [t["adj"] for t in trades["A"] if not t["fake"]]
    p(f"2. **What the second close filters (cell A, all trades, after era costs):** fakes {_short(a_f)}; "
      f"confirmations {_short(a_c)}.")
    a_by_event = {(t["side"], t["event_bar"]): t for t in trades["A"]}
    pairs = [(a_by_event[(t["side"], t["event_bar"])], t) for t in trades["B"]
             if (t["side"], t["event_bar"]) in a_by_event]
    gives = [(b["entry_px"] - b["a_entry_px"]) * b["side"] / PIP for b in trades["B"]]
    gives_atr = [g * PIP / b["atr"] for g, b in zip(gives, trades["B"])]
    p(f"3. **The price of waiting:** how much worse B's entry is than A's on the same event (positive = "
      f"worse): mean {statistics.fmean(gives):+.1f} pips, median {statistics.median(gives):+.1f} pips "
      f"({statistics.fmean(gives_atr):+.3f} daily ATR). Paired R(B) - R(A) on the same {len(pairs)} confirmed "
      f"events: mean {statistics.fmean(b['adj'] - a['adj'] for a, b in pairs):+.3f}R, median "
      f"{statistics.median(b['adj'] - a['adj'] for a, b in pairs):+.3f}R.")
    rt = [t["adj"] for t in trades["B"] if t["retested"]]
    nrt = [t["adj"] for t in trades["B"] if not t["retested"]]
    p(f"4. **Retest rate:** {len(rt)} of {len(trades['B'])} graded B trades were retested within "
      f"{RETEST_BARS} bars ({len(rt) / len(trades['B']):.1%}). B trades later retested: {_short(rt)}; "
      f"not retested: {_short(nrt)}.")
    p("5. **Session of the first close** (UTC hour of the event bar's close; no DST adjustment):")
    for name, hrs in SESSIONS:
        se = [e for s in (1, -1) for e in events[s] if e["fake"] is not None
              and (bars["opens"][e["bar"]] + timedelta(hours=1)).hour in hrs]
        bs = [t["adj"] for t in trades["B"] if t["hour"] in hrs]
        rate = sum(e["fake"] for e in se) / len(se) if se else float("nan")
        p(f"   - {name}: events {len(se)}, fake rate {rate:.1%}; B trades {_short(bs)}")
    p("6. **Counts:**")
    for side, name in ((1, "long"), (-1, "short")):
        p(f"   - {name}: " + "; ".join(f"{k} {v}" for k, v in sorted(cnt[side].items())))
    for c in CELLS:
        p(f"   - cell {c}: graded entries {len(trades[c])}, episodes {len(eps[c])}, same-bar ties {ties(trades[c])}")
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
