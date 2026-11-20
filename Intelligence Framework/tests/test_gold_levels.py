"""
test_gold_levels.py
───────────────────
gold_levels.py is a port of the study code that chose the ARRIVAL levels
(docs/specs/configuration_detector_spec.md §14.2). The live path never
imports studies/, so the port must give identical output: every hour's level
set, the "levels now" read used by the BRIEFING, and the R1-R3 visit
history. Bars are synthetic, built the way OANDA serves them: hourly bars,
4-hour and daily bars aligned to 5 PM New York, weekends absent, and the
daily session in progress left out.

Run: pytest tests/test_gold_levels.py
"""
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from _paths import ROOT

if os.path.join(ROOT, "studies") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "studies"))

import ccd1_arrival_calibration as A
import ccd1_arrival_lastweek as R
import gold_levels as G

NY = ZoneInfo("America/New_York")


def synthetic(hours=2600, seed=7):
    """Gold-like hourly walk with ranges and trends; returns (bars, hourly list)."""
    rng = random.Random(seed)
    t = datetime(2026, 3, 1, 22, 0, tzinfo=timezone.utc)      # a Sunday evening open
    c, anchor, rows = 3000.0, 3000.0, []
    while len(rows) < hours:
        ny = t.astimezone(NY)
        trading = not ((ny.weekday() == 4 and ny.hour >= 17) or ny.weekday() == 5
                       or (ny.weekday() == 6 and ny.hour < 17))
        if trading:
            if rng.random() < 0.01:
                anchor = c + rng.gauss(0, 60)                   # regime shift: a trend leg, then a range
            o = c
            c = c + 0.04 * (anchor - c) + rng.gauss(0, 6)
            rows.append((t, o, max(o, c) + abs(rng.gauss(0, 3)), min(o, c) - abs(rng.gauss(0, 3)), c))
        t += timedelta(hours=1)
    h1 = {"t": [r[0] for r in rows], "H": [r[2] for r in rows], "L": [r[3] for r in rows], "C": [r[4] for r in rows]}

    def bucket(r, hours_):
        ny = r[0].astimezone(NY)
        start = (ny - timedelta(hours=17)).replace(minute=0)    # sessions start 5 PM New York
        day0 = start.replace(hour=0) + timedelta(hours=17)
        off = (ny - day0).total_seconds() // 3600
        return (day0 + timedelta(hours=hours_ * (off // hours_))).astimezone(timezone.utc)

    def agg(hours_):
        out = {"t": [], "H": [], "L": [], "C": []}
        for r in rows:
            b = bucket(r, hours_)
            if out["t"] and out["t"][-1] == b:
                out["H"][-1] = max(out["H"][-1], r[2]); out["L"][-1] = min(out["L"][-1], r[3]); out["C"][-1] = r[4]
            else:
                out["t"].append(b); out["H"].append(r[2]); out["L"].append(r[3]); out["C"].append(r[4])
        return out

    d1, h4 = agg(24), agg(4)
    for k in d1:                                                 # the live feed omits the session in progress
        d1[k] = d1[k][:-1]
    return {"D": d1, "H4": h4, "H1": h1}


@pytest.fixture(scope="module")
def bars():
    return synthetic()


@pytest.fixture(scope="module")
def sets(bars):
    return G.level_sets(bars)


def test_every_hour_matches_the_studies(bars, sets):
    assert sets == A.level_sets("XAU_USD", bars)


def test_every_level_type_is_exercised(sets):
    kinds = {k for row in sets if row for k, _, _ in row[1]}
    assert kinds == set(G.KINDS_ALL), kinds
    assert sum(row is None for row in sets) < len(sets) // 4     # warm-up only


def test_levels_now_is_the_next_hours_row(bars, sets):
    n = len(bars["H1"]["t"])
    checked = 0
    for t in range(n - 300, n, 7):
        cut = {"D": bars["D"], "H4": bars["H4"],
               "H1": {k: v[:t] for k, v in bars["H1"].items()}}
        now = bars["H1"]["t"][t] + timedelta(minutes=45)
        assert G.levels_now(cut, now) == sets[t], t
        checked += 1
    assert checked > 40


def test_visit_history_matches_the_replay(bars, sets):
    n = len(bars["H1"]["t"])
    prices = sorted({round(p, 2) for row in sets[-200:] if row for _, _, p in row[1]})
    assert len(prices) > 10
    for p in prices:
        assert G.visit_history(bars, sets, p, bars["H1"]["t"][0], n) == \
            R.history(bars, sets, p, bars["H1"]["t"][0], n), p


def test_constants_match_the_studies():
    import ccd1_prototype as P
    assert (G.K, G.RUN_MIN, G.RUN_MAX, G.W_MIN, G.W_MAX) == (P.K, P.RUN_MIN, P.RUN_MAX, P.W_MIN, P.W_MAX)
    assert (G.D1_WIN, G.H4_WIN, G.REARM, G.BREAK_MARGIN) == (A.D1_WIN, A.H4_WIN, A.REARM, A.BREAK_MARGIN)
    assert G.TOL == R.TOL


def test_the_live_module_imports_nothing_from_studies():
    import ast
    tree = ast.parse(open(os.path.join(ROOT, "gold_levels.py")).read())
    names = [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    names += [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert names and not [m for m in names if m.startswith(("ccd1_", "studies"))], names
