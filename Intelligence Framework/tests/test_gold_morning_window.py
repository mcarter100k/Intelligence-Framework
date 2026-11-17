"""
test_gold_morning_window.py — studies/gold_morning_window_study.py
(docs/specs/gold_morning_window_spec.md §9). Synthetic H1 and D bars only; no
real gold statistic is computed here.

A standard trade day: ATR 10 (twenty prior sessions, true range 10 each);
window 04:00-06:00 PT opens 1000, high 1004, low 999, closes 1003 (move +3,
range 5), so d = 5 + 0.05 x 10 = 5.5 (0.55 ATR: inside floor B and the cap).
Entry 1003 at 7:00 AM PT; hold bars drift near 1003; the 12:00 bar closes 1004.
"""
import csv
import hashlib
import os
import sys
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "studies"))
import gold_morning_window_study as S  # noqa: E402
from gold_rule_costs import held_nights  # noqa: E402

PT, NY, UTC = ZoneInfo("America/Los_Angeles"), ZoneInfo("America/New_York"), timezone.utc
WIN = {4: (1000, 1002, 999, 1001), 5: (1001, 1004, 1000, 1002), 6: (1002, 1003.5, 1001, 1003)}
FLAT = {h: (1003, 1003.4, 1002.6, 1003) for h in range(7, 12)}
EXIT = {12: (1003, 1004.2, 1002.8, 1004), 13: (1004, 1010, 1003.9, 1009)}   # 13:00 bar = the rollover hour


def at(day, hour, tz=PT):
    return datetime(day.year, day.month, day.day, hour, tzinfo=tz).astimezone(UTC)


def h1_for(day, bars):
    return {at(day, h): v for h, v in bars.items()}


def daily(before, n=20, tr=10.0, base=1000.0, extra=None):
    """n weekday sessions before `before` (true range tr), plus optional {session: tr}."""
    out, s, k = {}, before - timedelta(days=1), 0
    while k < n:
        if s.weekday() < 5:
            t = datetime(s.year, s.month, s.day, 17, tzinfo=NY) - timedelta(days=1)
            out[t.astimezone(UTC)] = (base, base + tr / 2, base - tr / 2, base)
            k += 1
        s -= timedelta(days=1)
    for sday, r in (extra or {}).items():
        t = datetime(sday.year, sday.month, sday.day, 17, tzinfo=NY) - timedelta(days=1)
        out[t.astimezone(UTC)] = (base, base + r / 2, base - r / 2, base)
    return out


def standard(day, hold=None, exit_=None, win=None):
    bars = dict(win or WIN)
    bars.update(hold if hold is not None else FLAT)
    bars.update(exit_ if exit_ is not None else EXIT)
    return h1_for(day, bars)


def one_day(day, **kw):
    days, skips = S.build_days(standard(day, **kw), daily(day))
    assert len(days) == 1, (days, skips)
    return days[0]


# ── window, entry, exit ──────────────────────────────────────────────────────

@pytest.mark.parametrize("day", [date(2007, 1, 10), date(2007, 7, 11)])     # standard time and daylight time
def test_window_in_pacific_time_and_the_1pm_exit(day):
    h1 = standard(day)
    # Decoys at the UTC hours 04-06 of the same date (Pacific evening the day before):
    for h in (4, 5, 6):
        h1[datetime(day.year, day.month, day.day, h, tzinfo=UTC)] = (2000, 2001, 1999, 2000)
    days, _ = S.build_days(h1, daily(day))
    x = [d for d in days if d["date"] == day][0]
    assert x["d"] == pytest.approx(5.5) and x["dir"] == 1
    ts, sk = S.trades([x], "B1")
    assert sk == 0 and ts[0]["gross"] == pytest.approx((1004 - 1003) / 5.5)       # 12:00 bar's close, not 13:00's
    ts2, _ = S.trades([x], "B2")
    assert ts2[0]["gross"] == pytest.approx(-(1004 - 1003) / 5.5)


def test_b1_and_b2_share_days_and_stop_distance():
    day = date(2007, 1, 10)
    # Price rises to entry + 0.6 d: inside B2's stop (entry + d) -> B2 is a timed exit, not stopped.
    hold = dict(FLAT)
    hold[9] = (1003, 1003 + 0.6 * 5.5, 1002.8, 1003)
    x = one_day(day, hold=hold)
    b1, _ = S.trades([x], "B1")
    b2, _ = S.trades([x], "B2")
    assert [t["date"] for t in b1] == [t["date"] for t in b2]
    assert not b2[0]["stopped"] and b2[0]["gross"] == pytest.approx(-(1004 - 1003) / 5.5)
    # ...and at exactly entry + d, B2 is stopped at -1R.
    hold[9] = (1003, 1003 + 5.5, 1002.8, 1003)
    b2s, _ = S.trades([one_day(day, hold=hold)], "B2")
    assert b2s[0]["stopped"] and b2s[0]["gross"] == -1.0


def test_stop_on_the_entry_hour_and_a_gap_through_the_stop():
    day = date(2007, 1, 10)
    hold = dict(FLAT)
    hold[7] = (1003, 1003.2, 1003 - 5.5, 1000)                           # touches the long stop on the first hour
    t, _ = S.trades([one_day(day, hold=hold)], "B1")
    assert t[0]["stopped"] and t[0]["gross"] == -1.0 and not t[0]["gap"]
    hold = dict(FLAT)
    hold[8] = (990, 991, 989, 990)                                         # opens below the stop (997.5)
    t, _ = S.trades([one_day(day, hold=hold)], "B1")
    assert t[0]["gap"] and t[0]["gross"] == pytest.approx((990 - 1003) / 5.5)   # worse than -1R


def test_missing_exit_bar_skips_the_trade():
    day = date(2007, 1, 10)
    x = one_day(day, exit_={13: EXIT[13]})                                 # no 12:00 bar
    ts, sk = S.trades([x], "B1")
    assert ts == [] and sk == 1


def test_missing_window_bar_skips_the_day():
    day = date(2007, 1, 10)
    win = {4: WIN[4], 6: WIN[6]}
    days, skips = S.build_days(standard(day, win=win), daily(day))
    assert days == [] and skips["missing window bar"] == 1


def test_financing_is_zero_for_the_hold():
    assert held_nights(at(date(2007, 1, 10), 7), at(date(2007, 1, 10), 13)) == 0


# ── ATR, floors, cap ─────────────────────────────────────────────────────────

def test_atr_excludes_the_days_own_session():
    day = date(2007, 1, 10)
    days, _ = S.build_days(standard(day), daily(day, extra={day: 1000.0}))
    assert days[0]["atr"] == pytest.approx(10.0)


def test_floor_b_owns_the_verdict_population_and_the_cap():
    day = date(2007, 1, 10)
    x = one_day(day)
    tight = dict(x, d=0.2 * x["atr"])                                      # floor A only
    wide = dict(x, d=1.2 * x["atr"])                                       # beyond the cap
    assert S.population([x, tight, wide]) == [x]
    assert S.population([x, tight, wide], S.FLOOR_A, S.CAP) == [x, tight]
    assert S.population([x, tight, wide], S.FLOOR_B, None) == [x, wide]


# ── verdicts ─────────────────────────────────────────────────────────────────

def test_alpha_and_the_bound_used():
    assert S.ALPHA == pytest.approx(1 - 0.95 ** 0.5) and S.CONF_LOWER == pytest.approx(0.974679, abs=1e-6)
    seen = {}

    def spy(rs, conf, iters, seed):
        seen["conf"] = conf
        return 0.0
    orig = S.bootstrap_lower_bound
    S.bootstrap_lower_bound = spy
    try:
        S.summarize([0.1, 0.2, 0.3])
    finally:
        S.bootstrap_lower_bound = orig
    assert seen["conf"] == pytest.approx(1 - (1 - 0.95 ** 0.5))


def test_one_line_for_pass_and_fail():
    assert S.base_verdict({"n": 100, "lower": 0.07, "upper": 0.12, "wob": 0.1}) == "SUPPORTED"
    assert S.base_verdict({"n": 100, "lower": -0.10, "upper": 0.04, "wob": 0.0}) == "REFUTED"
    assert S.base_verdict({"n": 100, "lower": 0.00, "upper": 0.10, "wob": 0.0}) == "INCONCLUSIVE"
    assert S.base_verdict({"n": 100, "lower": 0.06, "upper": 0.20, "wob": -0.01}) == "INCONCLUSIVE"
    assert S.base_verdict({"n": 19}) == "INSUFFICIENT"


def _trades(rs, release=(), fomc=()):
    return [{"R": r, "release": i in release, "fomc": i in fomc} for i, r in enumerate(rs)]


def test_release_day_condition(monkeypatch):
    monkeypatch.setattr(S, "RESAMPLES", 2000)
    rs = [0.5 if i % 2 else -0.5 for i in range(100)] + [1.0] * 100      # release days carry the effect
    fv = S.final_verdict(_trades(rs, release=range(100, 200)))
    assert fv["base"] == "SUPPORTED" and fv["final"] == "INCONCLUSIVE pending GNC-1 (release-day condition)"
    rs2 = [1.0 if i % 2 else 0.2 for i in range(200)]                      # the effect is everywhere
    assert S.final_verdict(_trades(rs2, release=range(100, 200)))["final"] == "SUPPORTED"


def test_fomc_condition(monkeypatch):
    monkeypatch.setattr(S, "RESAMPLES", 2000)
    rs = [0.3 if i % 2 else -0.3 for i in range(100)] + [3.0] * 20       # FOMC days carry the effect
    fv = S.final_verdict(_trades(rs, fomc=range(100, 120)))
    assert fv["base"] == "SUPPORTED" and fv["base_no_fomc"] != "SUPPORTED"
    assert fv["final"] == "INCONCLUSIVE (FOMC condition)"


def test_exam_rule():
    assert "test defect" in S.exam_rule({"B1": "SUPPORTED", "B2": "SUPPORTED"})
    assert S.exam_rule({"B1": "SUPPORTED", "B2": "REFUTED"}).startswith("B1 is the cell")
    assert S.exam_rule({"B1": "INCONCLUSIVE", "B2": "REFUTED"}).startswith("no cell")


def test_without_best_one_percent_rounds_up():
    rs = list(range(150))                                                  # 1% of 150 = 1.5 -> drop 2
    assert S.without_best(rs) == pytest.approx(sum(range(148)) / 148)


# ── data refusals and pins ───────────────────────────────────────────────────

def _write(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time_utc", "o", "h", "l", "c", "span"])
        w.writerows(rows)
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def test_load_skips_forward_and_refuses_the_sealed_span(tmp_path):
    p = str(tmp_path / "x.csv")
    sha = _write(p, [["2007-01-10T12:00:00+00:00", 1, 2, 0.5, 1.5, "STUDY"],
                     ["2022-01-10T12:00:00+00:00", 1, 2, 0.5, 1.5, "USED"],
                     ["2026-10-01T12:00:00+00:00", 1, 2, 0.5, 1.5, "FORWARD"]])
    got = S.load(p, sha)
    assert set(got) == {"STUDY", "USED"} and len(got["STUDY"]) == 1 and len(got["USED"]) == 1
    sha = _write(p, [["2016-05-02T12:00:00+00:00", 1, 2, 0.5, 1.5, "USED"]])
    with pytest.raises(SystemExit, match="sealed span"):
        S.load(p, sha)
    with pytest.raises(SystemExit, match="not the pinned"):
        S.load(p, "0" * 64)


def test_the_frozen_spec_and_pins():
    assert S.sha(S.SPEC) == S.SPEC_SHA == "27d6738ccf8dbdda18417aebc8fc89373f5a8926bbdf1cca69f4ecc24d357326"
    spec = open(S.SPEC).read()
    for name, h in S.DATA.values():
        assert name in spec and h in spec
    assert S.sha(S.EVENTS[0]) == S.EVENTS[1] and S.sha(S.FOMC[0]) == S.FOMC[1]


def test_event_sessions_from_the_real_files():
    rel, fomc = S.event_sessions(S.EVENTS[0], S.FOMC[0])
    assert date(2008, 10, 3) in rel                                        # an NFP Friday
    assert date(2010, 5, 10) in fomc and date(2010, 5, 9) not in fomc     # Sunday-evening statement -> Monday session
    assert len(fomc) == 69
