"""
test_completed_periods.py — the standing check for fields derived from a
"completed" period (owner ruling P3, 2026-11-17).

The live OANDA feed leaves out the period in progress (the forming candle is
dropped); historical archives carry every period in full. A field computed
from "the last completed day / week / session / bar" must therefore give the
same answer whichever shape the data arrives in. Twice this boundary has
bitten the project: incident I8 (a forming D1 bar in the indicators, then a
24h-stale price) and the 2026-11-17 prior-session low that was a day stale in
every live hour (foundation/incident_catalogue.md I33).

The rule (foundation/methodology.md M42): every such field is listed in
REGISTRY with the test that proves its in-progress period is handled, and
test_every_completed_period_field_is_registered fails when a new field of
that kind appears in the scanned code without an entry. Nothing here touches
the network.
"""
from _paths import ROOT as _ROOT
import math
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest
import requests

sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "studies"))

import intraday_context
import levels_context
import oanda_feed
import ccd1_arrival_calibration as A


# ── the registry ──────────────────────────────────────────────────────────────
# (field, where, how the in-progress period is handled, test proving it)
REGISTRY = [
    ("every bar series", "oanda_feed._get_bars",
     "the forming candle (complete=False) is dropped", "test_feed_drops_the_forming_candle"),
    ("prev_day_high / prev_day_low", "levels_context.get_key_levels",
     "the last bar of the feed's daily series, which is the last completed day",
     "test_prev_day_is_the_last_completed_day"),
    ("prev_week_high / prev_week_low", "levels_context.get_key_levels",
     "the last bar of the feed's weekly series",
     "tests/test_level_source_repair.py::TestDefect3WeeklySemantics::test_prev_week_is_the_last_closed_week"),
    ("current_week_high / current_week_low", "levels_context.get_key_levels",
     "this week's completed daily bars only; the forming day is the session fields' job",
     "tests/test_level_source_repair.py::TestDefect3WeeklySemantics::test_current_week_is_this_week_to_date"),
    ("asian_high / asian_low", "intraday_context._get_asian_range",
     "the most recent completed 22:00-07:00 UTC session, never the one in progress",
     "test_asian_range_never_uses_the_session_in_progress"),
    ("ATR, ADX, structure, slope (daily, 4-hour, weekly)", "regime_detection.get_regime",
     "computed from the feed's series, so the forming candle never enters (rests on the feed test)",
     "test_feed_drops_the_forming_candle"),
    ("prior session, prior week, simple 14-day ATR, daily swings, 4-hour swings, range edges",
     "studies/ccd1_arrival_calibration.level_sets (the gold alert path)",
     "session_index places an hour past the last daily bar in a session not yet listed; "
     "4-hour bars count only once closed",
     "test_gold_levels_are_the_same_from_live_and_archive_shaped_data"),
    ("session_high / session_low", "levels_context.get_key_levels",
     "the current session to date from the feed's closed hourly bars: the forming hour never enters",
     "test_feed_drops_the_forming_candle"),
    ("prior_sh / prior_sl (and latest_sh / latest_sl)", "regime_detection._detect_structure",
     "swings confirmed by closes of the feed's closed bars only", "test_feed_drops_the_forming_candle"),
    ("last_closed_bar_age_hours", "regime_detection.get_regime",
     "age of the feed's last closed daily bar", "test_feed_drops_the_forming_candle"),
    ("prior_close (price basis)", "regime_detection.get_regime",
     "the last completed daily close, shown labelled only when the live price fails (the I8 repair)",
     "tests/test_data_at_source.py::test_p1_no_live_price_falls_back_to_the_close_labelled_and_reported"),
    ("prior session index", "studies/ccd1_arrival_calibration.session_index",
     "an hour past the last bar's 24-hour span is the session in progress",
     "tests/test_ccd1_arrival.py::test_session_index_treats_an_hour_past_the_last_daily_bar_as_a_new_session"),
]

# Field names in the scanned code that mark a value taken from a completed
# period. A new key matching these, in a scanned file, needs a REGISTRY entry.
MARKERS = re.compile(r'["\'](prev_\w+|prior_\w+|previous_\w+|yesterday_\w+|last_(?:closed|completed)_\w+|'
                     r'current_(?:week|month|day|session)_\w+|(?:asian|session)_(?:high|low)|PDAY|PWEEK)["\']')
SCANNED = ["levels_context.py", "intraday_context.py", "regime_detection.py", "decision_brief.py",
           "entry_confirmation.py", "session_memory.py", "setup_check.py",
           "studies/ccd1_arrival_calibration.py", "studies/ccd1_prototype.py"]
COVERED_NAMES = {"prev_day_high", "prev_day_low", "prev_week_high", "prev_week_low",
                 "current_week_high", "current_week_low", "asian_high", "asian_low",
                 "session_high", "session_low", "prior_sh", "prior_sl",
                 "last_closed_bar_age_hours", "prior_close", "PDAY", "PWEEK"}
# Names the scanner matches that are not market periods (name: reason).
NOT_A_PERIOD = {"prior_timestamp": "session_memory: when the previous run's reading was taken, not a market period"}


def test_every_completed_period_field_is_registered():
    found = {}
    for rel in SCANNED:
        path = os.path.join(_ROOT, rel)
        if os.path.exists(path):
            for m in MARKERS.finditer(open(path, encoding="utf-8").read()):
                found.setdefault(m.group(1), rel)
    unregistered = {k: v for k, v in found.items() if k not in COVERED_NAMES and k not in NOT_A_PERIOD}
    assert not unregistered, (f"completed-period fields with no REGISTRY entry and test: {unregistered} "
                              f"(foundation/methodology.md M42)")
    assert found, "the scan found nothing: the scanner itself is broken"


def test_every_registered_test_exists():
    here = sys.modules[__name__]
    for _, _, _, test in REGISTRY:
        if "::" in test:
            rel, *names = test.split("::")
            src = open(os.path.join(_ROOT, rel), encoding="utf-8").read()
            assert f"def {names[-1]}(" in src, test
        else:
            assert callable(getattr(here, test, None)), test


# ── the feed ──────────────────────────────────────────────────────────────────
class _Resp:
    status_code = 200

    def __init__(self, payload):
        self._p = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._p


def test_feed_drops_the_forming_candle(monkeypatch):
    monkeypatch.setenv("OANDA_API_KEY", "k")
    monkeypatch.setenv("OANDA_ACCOUNT_ID", "a")
    monkeypatch.setattr(oanda_feed, "_breaker_open_until", 0.0)
    c = lambda t, done, px: {"complete": done, "time": t, "volume": 1,
                             "mid": {"o": px, "h": px, "l": px, "c": px}}
    payload = {"candles": [c("2026-11-16T22:00:00.000000000Z", True, "3849.21"),
                           c("2026-11-17T22:00:00.000000000Z", False, "3793.07")]}
    monkeypatch.setattr(oanda_feed.requests, "get", lambda *a, **k: _Resp(payload))
    df = oanda_feed.get_daily_bars("XAU_USD", count=2)
    assert list(df["Close"]) == [3849.21]


# ── levels_context ────────────────────────────────────────────────────────────
def test_prev_day_is_the_last_completed_day(monkeypatch):
    idx = pd.to_datetime(["2026-11-13 22:00", "2026-11-15 22:00", "2026-11-16 22:00"], utc=True)
    daily = pd.DataFrame({"Open": [1, 2, 3], "High": [3884.0, 3901.37, 3891.07],
                          "Low": [3860.0, 3832.46, 3836.96], "Close": [1, 2, 3], "Volume": [1, 1, 1]}, index=idx)
    monkeypatch.setattr(levels_context, "get_daily_bars", lambda *a, **k: daily)
    monkeypatch.setattr(levels_context, "get_weekly_bars", lambda *a, **k: None)
    monkeypatch.setattr(levels_context, "get_hourly_bars", lambda *a, **k: None)
    monkeypatch.setattr(intraday_context, "get_intraday_context", lambda pair="GBPAUD": {})
    lv = levels_context.get_key_levels("XAU_USD")
    # the feed's last daily bar IS the last completed day (the forming one is dropped)
    assert (lv["prev_day_high"], lv["prev_day_low"]) == (3891.07, 3836.96)


# ── intraday_context ──────────────────────────────────────────────────────────
def _hourly(start, hours, high_of):
    idx = pd.date_range(start, periods=hours, freq="h", tz="UTC")
    hi = [high_of(t) for t in idx]
    return pd.DataFrame({"Open": hi, "High": hi, "Low": [h - 1 for h in hi], "Close": hi,
                         "Volume": [1] * hours}, index=idx)


def test_asian_range_never_uses_the_session_in_progress():
    # Sessions 22:00-07:00 UTC. Mark each session's bars with its own level.
    def level(t):
        h = t.hour
        if h >= 22 or h < 7:
            day = (t + timedelta(hours=2)).date()          # session named by the day it ends
            return {17: 100.0, 18: 200.0}.get(day.day, 50.0)
        return 10.0
    df = _hourly("2026-11-15 00:00", 4 * 24, level)
    # 23:00 UTC on the 17th: the session ending on the 18th is in progress -> the 17th's (100)
    hi, _, _ = intraday_context._get_asian_range(df, datetime(2026, 11, 17, 23, 0, tzinfo=timezone.utc))
    assert hi == 100.0
    # 03:00 UTC on the 18th: still in progress -> still the 17th's
    hi, _, _ = intraday_context._get_asian_range(df, datetime(2026, 11, 18, 3, 0, tzinfo=timezone.utc))
    assert hi == 100.0
    # 08:00 UTC on the 18th: the session that ended at 07:00 is complete -> 200
    hi, _, _ = intraday_context._get_asian_range(df, datetime(2026, 11, 18, 8, 0, tzinfo=timezone.utc))
    assert hi == 200.0


# ── the gold alert path: live-shaped and archive-shaped data must agree ───────
def _gold_like(days=45):
    """Continuous synthetic gold: hourly bars, and 4-hour and daily bars built
    from them on OANDA's 22:00 UTC alignment."""
    t0 = datetime(2026, 9, 27, 22, 0, tzinfo=timezone.utc)
    px = lambda h: 3800 + 60 * math.sin(2 * math.pi * h / 90) + 25 * math.sin(2 * math.pi * h / 23) + 0.05 * h
    h1 = {"t": [], "H": [], "L": [], "C": []}
    for h in range(days * 24):
        o, c = px(h), px(h + 1)
        h1["t"].append(t0 + timedelta(hours=h)); h1["H"].append(max(o, c) + 0.3)
        h1["L"].append(min(o, c) - 0.3); h1["C"].append(c)

    def agg(span):
        out = {"t": [], "H": [], "L": [], "C": []}
        for i in range(0, len(h1["t"]), span):
            out["t"].append(h1["t"][i]); out["H"].append(max(h1["H"][i:i + span]))
            out["L"].append(min(h1["L"][i:i + span])); out["C"].append(h1["C"][i + span - 1] if i + span <= len(h1["C"]) else h1["C"][-1])
        return out
    return h1, agg(4), agg(24)


def _cut(series, n):
    return {k: v[:n] for k, v in series.items()}


def test_gold_levels_are_the_same_from_live_and_archive_shaped_data():
    h1, h4, d1 = _gold_like()
    last = len(h1["t"]) - 1 - 12              # 11 hours into the final session, 3 hours into its 4-hour bar
    tt = h1["t"][last]
    hs = _cut(h1, last + 1)
    # archive shape: the session and 4-hour bar holding `tt` are present (complete, with later data in them)
    kd = max(i for i, t in enumerate(d1["t"]) if t <= tt)
    k4 = max(i for i, t in enumerate(h4["t"]) if t <= tt)
    archive = {"H1": hs, "H4": _cut(h4, k4 + 1), "D": _cut(d1, kd + 1)}
    # live shape: OANDA leaves both forming bars out
    live = {"H1": hs, "H4": _cut(h4, k4), "D": _cut(d1, kd)}
    a, l = A.level_sets("XAU_USD", archive), A.level_sets("XAU_USD", live)
    first_live_hour = max(i for i, t in enumerate(hs["t"]) if t <= d1["t"][kd])
    checked = 0
    for t in range(first_live_hour, last + 1):
        assert a[t] == l[t], (hs["t"][t], a[t], l[t])
        checked += 1
    assert checked >= 10
    kinds = {k for k, _, _ in l[last][1]}
    assert {"PDAY", "PWEEK", "D1", "H4"} <= kinds, kinds    # the comparison covers every level type that exists here
